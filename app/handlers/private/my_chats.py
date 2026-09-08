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


def chats_list_screen(chats: list[Chat]) -> Screen:
    if not chats:
        return Screen(
            ru.MY_CHATS_EMPTY,
            rows=[[Btn(ru.BTN_REFRESH, "chats:refresh")], [Btn(ru.BTN_BACK, "menu:main")]],
        )
    rows = [[Btn(f"{_chat_icon(c)} {c.title or c.telegram_id}", f"chat:{c.id}")] for c in chats]
    rows.append([Btn(ru.BTN_REFRESH, "chats:refresh")])
    rows.append([Btn(ru.BTN_BACK, "menu:main")])
    return Screen(f"{ru.MY_CHATS_TITLE}\n{ru.SEPARATOR}\n{ru.MY_CHATS_HINT}", rows=rows)


def _bot_status_line(chat: Chat) -> str:
    if chat.bot_status == BotStatus.ADMINISTRATOR:
        if chat.is_channel or chat.bot_can_delete:
            return ru.CHAT_BOT_ADMIN_FULL
        return ru.CHAT_BOT_ADMIN_NO_DELETE
    if chat.bot_status == BotStatus.MEMBER:
        return ru.CHAT_BOT_MEMBER
    return ru.CHAT_BOT_GONE


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
    rows = [[Btn(ru.BTN_CHAT_STATS, f"chat:{chat.id}:stats")]]
    if chat.is_channel:
        rows.append([Btn(ru.BTN_CHAT_CHECK_USER, f"chat:{chat.id}:check")])
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
    rows.append([Btn(ru.BTN_REFRESH, f"chat:{chat.id}:refresh")])
    rows.append([Btn(ru.BTN_BACK, "chats:list")])
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


@router.message(Command("chats"))
async def cmd_chats(message: Message, session: AsyncSession, user: User | None) -> None:
    if user is None:
        return
    chats = await chat_service.list_admin_chats(session, user)
    await send(
        message.bot,
        message.chat.id,
        chats_list_screen(chats),
        rich_buttons=user.rich_buttons_enabled,
    )


@router.callback_query(F.data == "chats:list")
async def cb_chats_list(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    chats = await chat_service.list_admin_chats(session, user)
    await respond(callback, chats_list_screen(chats), rich_buttons=user.rich_buttons_enabled)


@router.callback_query(F.data == "chats:refresh")
async def cb_chats_refresh(
    callback: CallbackQuery, session: AsyncSession, user: User | None, cache: Cache
) -> None:
    if user is None:
        await callback.answer()
        return
    # Re-read every chat the bot knows about where this user is (or was) an
    # admin — a chat the bot was added to before it could record the
    # my_chat_member update shows up only after this.
    for chat in await chat_service.list_admin_chats(session, user):
        await chat_service.refresh_bot_membership(callback.bot, session, chat)
        await chat_service.sync_admins(callback.bot, session, chat, cache)
    chats = await chat_service.list_admin_chats(session, user)
    await callback.answer(ru.MY_CHATS_REFRESHED)
    await respond(callback, chats_list_screen(chats), rich_buttons=user.rich_buttons_enabled)


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
