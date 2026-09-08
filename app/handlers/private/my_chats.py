"""«Мои чаты»: the list of chats the user administers, and one chat's card.

Callback data:
  chats:list            the list
  chats:refresh         re-sync the bot's rights + admins for every chat
  chat:{id}             one chat's card (id = chats.id)
  chat:{id}:refresh     re-sync that chat
"""

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import BotStatus, Chat, User
from app.services import chat_service
from app.texts import ru
from app.ui import Btn, Screen, respond, send

router = Router(name="my_chats")


def _chat_icon(chat: Chat) -> str:
    return "📣" if chat.is_channel else "👥"


def chats_hub_screen(channels: int, groups: int) -> Screen:
    if not channels and not groups:
        return Screen(
            ru.MY_CHATS_EMPTY,
            rows=[[Btn(ru.BTN_REFRESH, "chats:refresh")], [Btn(ru.BTN_BACK, "menu:main")]],
        )
    return Screen(
        ru.MY_CHATS_HUB.format(channels=channels, groups=groups),
        rows=[
            [
                Btn(ru.BTN_CHATS_CHANNELS.format(count=channels), "chats:list:channels"),
                Btn(ru.BTN_CHATS_GROUPS.format(count=groups), "chats:list:groups"),
            ],
            [Btn(ru.BTN_REFRESH, "chats:refresh")],
            [Btn(ru.BTN_BACK, "menu:main")],
        ],
    )


def chats_list_screen(chats: list[Chat], *, channels: bool) -> Screen:
    title = ru.MY_CHANNELS_TITLE if channels else ru.MY_GROUPS_TITLE
    if not chats:
        text = f"{title}\n{ru.SEPARATOR}\n" + (
            ru.MY_CHANNELS_EMPTY if channels else ru.MY_GROUPS_EMPTY
        )
        return Screen(
            text, rows=[[Btn(ru.BTN_REFRESH, "chats:refresh")], [Btn(ru.BTN_BACK, "chats:list")]]
        )
    rows = [[Btn(f"{_chat_icon(c)} {c.title or c.telegram_id}", f"chat:{c.id}")] for c in chats]
    rows.append([Btn(ru.BTN_BACK, "chats:list")])
    return Screen(f"{title}\n{ru.SEPARATOR}\n{ru.MY_CHATS_HINT}", rows=rows)


def back_target(chat: Chat) -> str:
    return "chats:list:channels" if chat.is_channel else "chats:list:groups"


def _bot_status_line(chat: Chat) -> str:
    if chat.bot_status == BotStatus.ADMINISTRATOR:
        if chat.is_channel or chat.bot_can_delete:
            return ru.CHAT_BOT_ADMIN_FULL
        return ru.CHAT_BOT_ADMIN_NO_DELETE
    if chat.bot_status == BotStatus.MEMBER:
        return ru.CHAT_BOT_MEMBER
    return ru.CHAT_BOT_GONE


def _join_gate_button(chat: Chat) -> Btn:
    label = ru.BTN_CHAT_JOINGATE_ON if chat.join_gate_enabled else ru.BTN_CHAT_JOINGATE_OFF
    return Btn(label, f"chat:{chat.id}:joingate")


def _forcesub_problem(chat: Chat, channels_count: int) -> str | None:
    if not channels_count:
        return ru.BLOCK_NO_CHANNELS
    if not chat.bot_can_delete:
        return ru.BLOCK_NO_DELETE
    return None


def _join_gate_problem(chat: Chat, channels_count: int) -> str | None:
    if not channels_count:
        return ru.BLOCK_NO_CHANNELS
    if not chat.bot_can_invite:
        return ru.BLOCK_NO_INVITE
    if not chat.join_by_request:
        # The switch in Telegram itself, which the bot is never told about.
        return ru.BLOCK_NOT_BY_REQUEST
    return None


def _feature_line(name: str, problem: str | None) -> str:
    if problem is None:
        return ru.FEATURE_OK.format(name=name)
    return ru.FEATURE_BLOCKED.format(name=name, problem=problem)


def feature_lines(
    chat: Chat, *, channels_count: int, comments: tuple[str, bool] | None
) -> list[str]:
    """One line per switched-on feature, saying whether it actually does
    anything — a flag alone tells an admin nothing about why the chat
    behaves as if the feature were off."""
    lines: list[str] = []
    if chat.forcesub_enabled:
        lines.append(_feature_line(ru.FEATURE_FORCESUB, _forcesub_problem(chat, channels_count)))
    if chat.join_gate_enabled:
        lines.append(_feature_line(ru.FEATURE_JOINGATE, _join_gate_problem(chat, channels_count)))
    if chat.welcome_enabled and chat.welcome_content:
        lines.append(_feature_line(ru.FEATURE_WELCOME, None))
    if chat.captcha_enabled:
        lines.append(
            _feature_line(
                ru.FEATURE_CAPTCHA, None if chat.bot_can_restrict else ru.BLOCK_NO_RESTRICT
            )
        )
    if chat.digest_enabled:
        lines.append(
            ru.FEATURE_DIGEST.format(
                time=chat.digest_time,
                period=ru.FEATURE_DIGEST_WEEKLY
                if chat.digest_period == "weekly"
                else ru.FEATURE_DIGEST_DAILY,
            )
        )
    if chat.is_channel and chat.reward_content:
        lines.append(_feature_line(ru.FEATURE_REWARD, None))
    if comments is not None and comments[1]:
        lines.append(_feature_line(ru.FEATURE_COMMENTS_GATE, None))
    return lines


def chat_card_screen(
    chat: Chat,
    *,
    member_count: int | None,
    channels_count: int,
    whitelist_count: int,
    comments: tuple[str, bool] | None = None,
) -> Screen:
    """`comments` (channels only): (status line, gate on?)."""
    text = ru.CHAT_CARD.format(
        icon=_chat_icon(chat),
        title=chat.title or chat.telegram_id,
        kind=ru.CHAT_KIND_CHANNEL if chat.is_channel else ru.CHAT_KIND_GROUP,
        bot_status=_bot_status_line(chat),
        members_line=(
            ru.CHAT_MEMBERS_LINE.format(count=member_count)
            if member_count is not None
            else ru.CHAT_MEMBERS_UNKNOWN
        ),
    )
    if comments is not None:
        text += ru.CHAT_COMMENTS_LINE.format(value=comments[0])
    lines = feature_lines(chat, channels_count=channels_count, comments=comments)
    text += ru.CHAT_FEATURES.format(lines="\n".join(lines) if lines else ru.CHAT_FEATURES_NONE)
    rows = [[Btn(ru.BTN_CHAT_STATS, f"chat:{chat.id}:stats")]]
    if chat.is_channel:
        rows.append(
            [
                Btn(ru.BTN_CHAT_CHECK_USER, f"chat:{chat.id}:check"),
                Btn(ru.BTN_CHAT_REWARD, f"chat:{chat.id}:reward"),
            ]
        )
        rows.append(
            [
                Btn(
                    ru.BTN_CHAT_COMMENTS_GATE_ON
                    if comments and comments[1]
                    else ru.BTN_CHAT_COMMENTS_GATE_OFF,
                    f"chat:{chat.id}:comments_gate",
                )
            ]
        )
        rows.append(
            [
                Btn(ru.BTN_CHAT_CHANNELS.format(count=channels_count), f"chat:{chat.id}:channels"),
                Btn(ru.BTN_CHAT_DIGEST, f"chat:{chat.id}:digest"),
            ]
        )
        rows.append([_join_gate_button(chat)])
    else:
        rows.append(
            [
                Btn(
                    ru.BTN_CHAT_FORCESUB_ON if chat.forcesub_enabled else ru.BTN_CHAT_FORCESUB_OFF,
                    f"chat:{chat.id}:forcesub",
                )
            ]
        )
        rows.append(
            [
                Btn(ru.BTN_CHAT_CHANNELS.format(count=channels_count), f"chat:{chat.id}:channels"),
                Btn(
                    ru.BTN_CHAT_WHITELIST.format(count=whitelist_count),
                    f"chat:{chat.id}:whitelist",
                ),
            ]
        )
        rows.append([_join_gate_button(chat)])
        rows.append(
            [
                Btn(ru.BTN_CHAT_WELCOME, f"chat:{chat.id}:welcome"),
                Btn(ru.BTN_CHAT_DIGEST, f"chat:{chat.id}:digest"),
            ]
        )
    rows.append([Btn(ru.BTN_REFRESH, f"chat:{chat.id}:refresh")])
    rows.append([Btn(ru.BTN_BACK, back_target(chat))])
    return Screen(text, rows=rows)


async def load_admin_chat(session: AsyncSession, user: User, chat_id: int) -> Chat | None:
    """The chat by primary key, only if `user` administers it."""
    chat = await chat_service.get_chat(session, chat_id)
    if chat is None or not await chat_service.user_administers(session, user, chat):
        return None
    return chat


async def render_chat_card(
    bot: Bot, session: AsyncSession, chat: Chat, *, refresh: bool = False
) -> Screen:
    # Imported lazily: forcesub_service depends on chat_service, not vice versa.
    from app.services import forcesub_service

    if refresh:
        await chat_service.refresh_bot_membership(bot, session, chat)
        # The admin may have flipped "join by request" (or attached a
        # discussion group) in Telegram, which raises no update at all.
        await chat_service.refresh_chat_flags(bot, session, chat)
    member_count = (
        await chat_service.get_member_count(bot, session, chat) if chat.is_active else None
    )
    channels = await forcesub_service.list_required_channels(session, chat)
    whitelist = await forcesub_service.list_whitelist(session, chat)
    comments = None
    if chat.is_channel and chat.is_active:
        comments = await comments_status(bot, session, chat, refresh=refresh)
    return chat_card_screen(
        chat,
        member_count=member_count,
        channels_count=len(channels),
        whitelist_count=len(whitelist),
        comments=comments,
    )


async def comments_status(
    bot: Bot, session: AsyncSession, channel: Chat, *, refresh: bool = False
) -> tuple[str, bool]:
    from app.services import forcesub_service

    group = await chat_service.resolve_linked_group(bot, session, channel, refresh=refresh)
    if group is None:
        if channel.linked_chat_tg_id is None:
            return ru.CHAT_COMMENTS_NO_DISCUSSION, False
        return ru.CHAT_COMMENTS_BOT_MISSING, False
    enabled = await forcesub_service.comments_gate_enabled(session, channel, group)
    line = ru.CHAT_COMMENTS_GROUP.format(title=group.title or group.telegram_id)
    if enabled:
        line += ru.CHAT_COMMENTS_GATE_ON
    return line, enabled


def _split(chats: list[Chat]) -> tuple[list[Chat], list[Chat]]:
    return [c for c in chats if c.is_channel], [c for c in chats if not c.is_channel]


@router.message(Command("chats"))
async def cmd_chats(message: Message, session: AsyncSession, user: User | None) -> None:
    if user is None:
        return
    channels, groups = _split(await chat_service.list_admin_chats(session, user))
    await send(
        message.bot,
        message.chat.id,
        chats_hub_screen(len(channels), len(groups)),
        rich_buttons=user.rich_buttons_enabled,
    )


@router.callback_query(F.data == "chats:list")
async def cb_chats_hub(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    channels, groups = _split(await chat_service.list_admin_chats(session, user))
    await respond(
        callback,
        chats_hub_screen(len(channels), len(groups)),
        rich_buttons=user.rich_buttons_enabled,
    )


@router.callback_query(F.data.in_({"chats:list:channels", "chats:list:groups"}))
async def cb_chats_list(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    channels, groups = _split(await chat_service.list_admin_chats(session, user))
    want_channels = callback.data.endswith("channels")
    screen = chats_list_screen(channels if want_channels else groups, channels=want_channels)
    await respond(callback, screen, rich_buttons=user.rich_buttons_enabled)


@router.callback_query(F.data == "chats:refresh")
async def cb_chats_refresh(
    callback: CallbackQuery, session: AsyncSession, user: User | None, cache: Cache
) -> None:
    if user is None:
        await callback.answer()
        return
    for chat in await chat_service.list_admin_chats(session, user):
        await chat_service.refresh_bot_membership(callback.bot, session, chat)
        await chat_service.sync_admins(callback.bot, session, chat, cache)
    channels, groups = _split(await chat_service.list_admin_chats(session, user))
    await callback.answer(ru.MY_CHATS_REFRESHED)
    await respond(
        callback,
        chats_hub_screen(len(channels), len(groups)),
        rich_buttons=user.rich_buttons_enabled,
    )


@router.callback_query(F.data.regexp(r"^chat:(\d+)$"))
async def cb_chat_card(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await load_admin_chat(session, user, int(callback.data.split(":")[1]))
    if chat is None:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return
    screen = await render_chat_card(callback.bot, session, chat)
    await respond(callback, screen, rich_buttons=user.rich_buttons_enabled)


@router.callback_query(F.data.regexp(r"^chat:(\d+):refresh$"))
async def cb_chat_refresh(
    callback: CallbackQuery, session: AsyncSession, user: User | None, cache: Cache
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await load_admin_chat(session, user, int(callback.data.split(":")[1]))
    if chat is None:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return
    await chat_service.sync_admins(callback.bot, session, chat, cache)
    chat.member_count_updated_at = None
    screen = await render_chat_card(callback.bot, session, chat, refresh=True)
    await callback.answer(ru.CHAT_REFRESHED)
    await respond(callback, screen, rich_buttons=user.rich_buttons_enabled)
