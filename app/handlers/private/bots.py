"""«Боты»: the owner's own bots. Each has an API key (force-sub checks),
channels to check, and optionally its token + audience (broadcasts).

  keys:list                          all my bots
  keys:new                           ask for a name (FSM) -> create, show key once
  keys:howto                         integration guide
  key:{id}                           one bot's card
  key:{id}:channels                  channels bound to the key
  key:{id}:channels:toggle:{chat_id} flip one binding
  key:{id}:token                     ask for the bot token (FSM)
  key:{id}:token:rm                  forget the token
  key:{id}:rotate                    reissue the API key
  key:{id}:delete                    delete the bot
"""

import logging

from aiogram import Bot, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import ApiKey, BotStatus, User
from app.handlers.private.my_chats import load_admin_chat
from app.services import api_key_service, audience_service, chat_service
from app.texts import ru
from app.ui import Btn, Screen, respond, send
from app.ui.buttons import STYLE_DANGER
from config import settings

logger = logging.getLogger(__name__)
router = Router(name="bots")


class BotCreate(StatesGroup):
    waiting_name = State()
    waiting_token = State()


async def validate_bot_token(token: str) -> TgUser | None:
    """getMe with the given token; None if Telegram rejects it."""
    probe = Bot(token=token, default=DefaultBotProperties())
    try:
        return await probe.get_me()
    except (TelegramAPIError, ValueError):
        return None
    finally:
        await probe.session.close()


async def bots_list_screen(session: AsyncSession, user: User) -> Screen:
    keys = await api_key_service.list_keys(session, user)
    text = ru.BOTS_TITLE
    if not keys:
        text += f"\n\n{ru.BOTS_EMPTY_LINE}"
    rows = [[Btn(ru.BOT_ROW.format(name=k.name), f"key:{k.id}")] for k in keys]
    rows.append([Btn(ru.BTN_BOT_NEW, "keys:new"), Btn(ru.BTN_KEY_HOWTO, "keys:howto")])
    rows.append([Btn(ru.BTN_BACK, "menu:main")])
    return Screen(text, rows=rows)


def _fmt_dt(value) -> str:
    return value.strftime("%d.%m.%Y %H:%M") if value else ru.KEY_NEVER_USED


async def bot_card_screen(session: AsyncSession, key: ApiKey, user: User) -> Screen:
    channels = await api_key_service.list_key_channels(session, key)
    reachable, blocked = await audience_service.audience_size(session, key)
    text = ru.BOT_CARD.format(
        name=key.name,
        prefix=key.key_prefix,
        requests=key.request_count,
        last_used=_fmt_dt(key.last_used_at),
        channels=len(channels),
        token_line=(
            ru.BOT_TOKEN_SET.format(username=key.bot_username or "?")
            if key.has_bot
            else ru.BOT_TOKEN_MISSING
        ),
        audience=reachable,
        blocked_line=ru.BOT_BLOCKED_LINE.format(blocked=blocked) if blocked else "",
        check_url=check_url(key.key_raw, user.telegram_id) if key.key_raw else ru.KEY_RAW_MISSING,
    )
    text += f"\n\n<i>{ru.BOT_AUDIENCE_HINT}</i>"
    token_btn = (
        Btn(ru.BTN_BOT_TOKEN_REMOVE, f"key:{key.id}:token:rm", STYLE_DANGER)
        if key.has_bot
        else Btn(ru.BTN_BOT_TOKEN_ADD, f"key:{key.id}:token")
    )
    rows = [
        [Btn(ru.BTN_KEY_CHANNELS.format(count=len(channels)), f"key:{key.id}:channels")],
        [token_btn],
        [
            Btn(ru.BTN_KEY_ROTATE, f"key:{key.id}:rotate"),
            Btn(ru.BTN_KEY_DELETE, f"key:{key.id}:delete", STYLE_DANGER),
        ],
        [Btn(ru.BTN_KEY_HOWTO, "keys:howto")],
        [Btn(ru.BTN_BACK, "keys:list")],
    ]
    return Screen(text, rows=rows)


async def key_channels_screen(session: AsyncSession, user: User, key: ApiKey) -> Screen:
    channels = await chat_service.list_admin_channels(session, user)
    bound = {c.id for c in await api_key_service.list_key_channels(session, key)}
    if not channels:
        return Screen(
            ru.KEY_CHANNELS_EMPTY.format(name=key.name),
            rows=[[Btn(ru.BTN_REFRESH, "chats:refresh")], [Btn(ru.BTN_BACK, f"key:{key.id}")]],
        )
    rows = [
        [
            Btn(
                (ru.CHANNEL_ROW_ON if c.id in bound else ru.CHANNEL_ROW_OFF).format(
                    title=c.title or c.telegram_id
                ),
                f"key:{key.id}:channels:toggle:{c.id}",
            )
        ]
        for c in channels
    ]
    rows.append([Btn(ru.BTN_BACK, f"key:{key.id}")])
    return Screen(ru.KEY_CHANNELS_TITLE.format(name=key.name), rows=rows)


def _api_base() -> str:
    return settings.api_public_url.rstrip("/") or f"http://<host>:{settings.api_port}"


def check_url(raw_key: str | None, user_id: int | str) -> str:
    """The one-line integration for bot constructors: key in the path,
    the admin's own id pre-filled so the link can be tried right away."""
    return f"{_api_base()}/v1/check/{raw_key or 'ВАШ_КЛЮЧ'}?user_id={user_id}"


def channels_url(raw_key: str | None) -> str:
    return f"{_api_base()}/v1/channels/{raw_key or 'ВАШ_КЛЮЧ'}"


def links_block(key: ApiKey, user: User) -> str:
    """Ready links for one bot, each on its own line."""
    if key.key_raw:
        return ru.KEY_LINKS_BLOCK.format(
            name=key.name,
            check_url=check_url(key.key_raw, user.telegram_id),
            channels_url=channels_url(key.key_raw),
            user_id=user.telegram_id,
        )
    return ru.KEY_LINKS_BLOCK_NO_RAW.format(name=key.name)


async def howto_screen(session: AsyncSession, user: User) -> Screen:
    base = _api_base()
    keys = await api_key_service.list_keys(session, user)
    blocks = "\n\n".join(links_block(k, user) for k in keys) or ru.KEY_LINKS_NONE
    text = ru.KEY_HOWTO.format(
        base=base, limit=settings.api_rate_limit_per_minute, links=blocks, user_id=user.telegram_id
    )
    text += ru.KEY_HOWTO_USERS.format(base=base)
    return Screen(text, rows=[[Btn(ru.BTN_BACK, "keys:list")]])


async def _owned_key(callback: CallbackQuery, session: AsyncSession, user: User) -> ApiKey | None:
    key = await api_key_service.get_owned_key(session, user, int(callback.data.split(":")[1]))
    if key is None or not key.is_active:
        await callback.answer(ru.KEY_NOT_FOUND, show_alert=True)
        return None
    return key


def _rich(user: User | None) -> bool:
    return user.rich_buttons_enabled if user else True


@router.message(Command("bots", "keys"))
async def cmd_bots(message: Message, session: AsyncSession, user: User | None) -> None:
    if user is None:
        return
    await send(
        message.bot,
        message.chat.id,
        await bots_list_screen(session, user),
        rich_buttons=_rich(user),
    )


@router.callback_query(F.data == "keys:list")
async def cb_bots_list(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    await state.clear()
    await respond(callback, await bots_list_screen(session, user), rich_buttons=_rich(user))


@router.callback_query(F.data == "keys:howto")
async def cb_keys_howto(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    await respond(callback, await howto_screen(session, user), rich_buttons=_rich(user))


@router.callback_query(F.data == "keys:new")
async def cb_bot_new(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    if user is None:
        await callback.answer()
        return
    await state.set_state(BotCreate.waiting_name)
    screen = Screen(ru.BOT_ASK_NAME, rows=[[Btn(ru.BTN_CANCEL, "keys:list", STYLE_DANGER)]])
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(BotCreate.waiting_name, F.text)
async def on_bot_name(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    name = message.text.strip()
    if len(name) > 64:
        await message.answer(ru.KEY_NAME_TOO_LONG)
        return
    await state.clear()
    key, raw = await api_key_service.create_key(session, user, name or "Бот")
    screen = Screen(
        ru.BOT_CREATED.format(name=key.name, raw=raw, check_url=check_url(raw, user.telegram_id)),
        rows=[
            [Btn(ru.BTN_KEY_CHANNELS.format(count=0), f"key:{key.id}:channels")],
            [Btn(ru.BTN_BOT_TOKEN_ADD, f"key:{key.id}:token")],
            [Btn(ru.BTN_KEY_HOWTO, "keys:howto")],
            [Btn(ru.BTN_BACK, "keys:list")],
        ],
    )
    await send(message.bot, message.chat.id, screen, rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^key:(\d+)$"))
async def cb_bot_card(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    await state.clear()
    key = await _owned_key(callback, session, user)
    if key is None:
        return
    await respond(callback, await bot_card_screen(session, key, user), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^key:(\d+):channels$"))
async def cb_key_channels(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    key = await _owned_key(callback, session, user)
    if key is None:
        return
    await respond(callback, await key_channels_screen(session, user, key), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^key:(\d+):channels:toggle:(\d+)$"))
async def cb_key_channel_toggle(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    key = await _owned_key(callback, session, user)
    if key is None:
        return
    channel = await load_admin_chat(session, user, int(callback.data.split(":")[4]))
    if channel is None or not channel.is_channel:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return

    bound = {c.id for c in await api_key_service.list_key_channels(session, key)}
    if channel.id not in bound:
        try:
            me = await callback.bot.get_chat_member(channel.telegram_id, callback.bot.id)
            is_admin = me.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
        except (TelegramBadRequest, TelegramForbiddenError):
            is_admin = False
        if not is_admin:
            channel.bot_status = BotStatus.LEFT
            await session.commit()
            await callback.answer(
                ru.CHANNEL_BOT_NOT_ADMIN.format(title=channel.title or channel.telegram_id),
                show_alert=True,
            )
            await respond(
                callback, await key_channels_screen(session, user, key), rich_buttons=_rich(user)
            )
            return

    now_bound = await api_key_service.toggle_key_channel(session, key, channel)
    await callback.answer(ru.CHANNEL_ADDED if now_bound else ru.CHANNEL_REMOVED)
    await respond(callback, await key_channels_screen(session, user, key), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^key:(\d+):token$"))
async def cb_bot_token_ask(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    key = await _owned_key(callback, session, user)
    if key is None:
        return
    await state.set_state(BotCreate.waiting_token)
    await state.update_data(key_id=key.id)
    screen = Screen(ru.BOT_ASK_TOKEN, rows=[[Btn(ru.BTN_CANCEL, f"key:{key.id}", STYLE_DANGER)]])
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(BotCreate.waiting_token, F.text)
async def on_bot_token(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    token = message.text.strip()
    try:
        await message.delete()  # don't leave the secret in the chat history
    except (TelegramBadRequest, TelegramForbiddenError):
        pass
    data = await state.get_data()
    key = await api_key_service.get_owned_key(session, user, int(data.get("key_id", 0)))
    if key is None:
        await state.clear()
        return
    me = await validate_bot_token(token)
    if me is None:
        await send(
            message.bot, message.chat.id, Screen(ru.BOT_TOKEN_INVALID), rich_buttons=_rich(user)
        )
        return
    await state.clear()
    await api_key_service.set_bot_token(session, key, token, me.id, me.username)
    await message.answer(ru.BOT_TOKEN_SAVED.format(username=me.username or me.id))
    await send(
        message.bot,
        message.chat.id,
        await bot_card_screen(session, key, user),
        rich_buttons=_rich(user),
    )


@router.callback_query(F.data.regexp(r"^key:(\d+):token:rm$"))
async def cb_bot_token_remove(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    key = await _owned_key(callback, session, user)
    if key is None:
        return
    await api_key_service.clear_bot_token(session, key)
    await callback.answer(ru.BOT_TOKEN_REMOVED)
    await respond(callback, await bot_card_screen(session, key, user), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^key:(\d+):rotate$"))
async def cb_key_rotate(
    callback: CallbackQuery, session: AsyncSession, user: User | None, cache: Cache
) -> None:
    if user is None:
        await callback.answer()
        return
    key = await _owned_key(callback, session, user)
    if key is None:
        return
    key, raw = await api_key_service.rotate_key(session, cache, key)
    screen = Screen(
        ru.KEY_ROTATED.format(raw=raw, check_url=check_url(raw, user.telegram_id)),
        rows=[[Btn(ru.BTN_BACK, f"key:{key.id}")]],
    )
    await respond(callback, screen, rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^key:(\d+):delete$"))
async def cb_key_delete(
    callback: CallbackQuery, session: AsyncSession, user: User | None, cache: Cache
) -> None:
    if user is None:
        await callback.answer()
        return
    key = await _owned_key(callback, session, user)
    if key is None:
        return
    await api_key_service.delete_key(session, cache, key)
    await callback.answer(ru.KEY_DELETED)
    await respond(callback, await bots_list_screen(session, user), rich_buttons=_rich(user))
