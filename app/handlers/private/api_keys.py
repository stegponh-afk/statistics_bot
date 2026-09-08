"""API keys for the force-sub bridge.

keys:list                          all my keys
keys:new                           ask for a name (FSM) -> create, show once
keys:howto                         integration guide
key:{id}                           one key's card
key:{id}:channels                  channels bound to the key
key:{id}:channels:toggle:{chat_id} flip one binding
key:{id}:rotate                    revoke + reissue
key:{id}:delete                    delete
"""

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import ApiKey, BotStatus, User
from app.handlers.private.my_chats import load_admin_chat
from app.services import api_key_service, chat_service
from app.texts import ru
from app.ui import Btn, Screen, respond, send
from app.ui.buttons import STYLE_DANGER
from config import settings

router = Router(name="api_keys")


class KeyCreate(StatesGroup):
    waiting_name = State()


async def keys_list_screen(session: AsyncSession, user: User) -> Screen:
    keys = await api_key_service.list_keys(session, user)
    text = ru.KEYS_TITLE
    if not keys:
        text += f"\n\n{ru.KEYS_EMPTY_LINE}"
    rows = [[Btn(ru.KEY_ROW.format(name=k.name, prefix=k.key_prefix), f"key:{k.id}")] for k in keys]
    rows.append([Btn(ru.BTN_KEY_NEW, "keys:new"), Btn(ru.BTN_KEY_HOWTO, "keys:howto")])
    rows.append([Btn(ru.BTN_BACK, "menu:main")])
    return Screen(text, rows=rows)


def _fmt_dt(value) -> str:
    return value.strftime("%d.%m.%Y %H:%M") if value else ru.KEY_NEVER_USED


async def key_card_screen(session: AsyncSession, key: ApiKey) -> Screen:
    channels = await api_key_service.list_key_channels(session, key)
    text = ru.KEY_CARD.format(
        name=key.name,
        prefix=key.key_prefix,
        created=_fmt_dt(key.created_at),
        last_used=_fmt_dt(key.last_used_at),
        requests=key.request_count,
        channels=len(channels),
    )
    rows = [
        [Btn(ru.BTN_KEY_CHANNELS.format(count=len(channels)), f"key:{key.id}:channels")],
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


def howto_screen() -> Screen:
    base = settings.api_public_url.rstrip("/") or f"http://<host>:{settings.api_port}"
    text = ru.KEY_HOWTO.format(base=base, limit=settings.api_rate_limit_per_minute)
    return Screen(text, rows=[[Btn(ru.BTN_BACK, "keys:list")]])


async def _owned_key(callback: CallbackQuery, session: AsyncSession, user: User) -> ApiKey | None:
    key = await api_key_service.get_owned_key(session, user, int(callback.data.split(":")[1]))
    if key is None or not key.is_active:
        await callback.answer(ru.KEY_NOT_FOUND, show_alert=True)
        return None
    return key


@router.message(Command("keys"))
async def cmd_keys(message: Message, session: AsyncSession, user: User | None) -> None:
    if user is None:
        return
    await send(
        message.bot,
        message.chat.id,
        await keys_list_screen(session, user),
        rich_buttons=user.rich_buttons_enabled,
    )


@router.callback_query(F.data == "keys:list")
async def cb_keys_list(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    await state.clear()
    await respond(
        callback, await keys_list_screen(session, user), rich_buttons=user.rich_buttons_enabled
    )


@router.callback_query(F.data == "keys:howto")
async def cb_keys_howto(callback: CallbackQuery, user: User | None) -> None:
    await respond(
        callback, howto_screen(), rich_buttons=user.rich_buttons_enabled if user else True
    )


@router.callback_query(F.data == "keys:new")
async def cb_keys_new(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    if user is None:
        await callback.answer()
        return
    await state.set_state(KeyCreate.waiting_name)
    screen = Screen(ru.KEY_ASK_NAME, rows=[[Btn(ru.BTN_CANCEL, "keys:list", STYLE_DANGER)]])
    await respond(callback, screen, rich_buttons=user.rich_buttons_enabled)


@router.message(KeyCreate.waiting_name, F.text)
async def on_key_name(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    name = message.text.strip()
    if len(name) > 64:
        await message.answer(ru.KEY_NAME_TOO_LONG)
        return
    await state.clear()
    key, raw = await api_key_service.create_key(session, user, name or "Ключ")
    screen = Screen(
        ru.KEY_CREATED.format(name=key.name, raw=raw),
        rows=[
            [Btn(ru.BTN_KEY_CHANNELS.format(count=0), f"key:{key.id}:channels")],
            [Btn(ru.BTN_KEY_HOWTO, "keys:howto")],
            [Btn(ru.BTN_BACK, "keys:list")],
        ],
    )
    await send(message.bot, message.chat.id, screen, rich_buttons=user.rich_buttons_enabled)


@router.callback_query(F.data.regexp(r"^key:(\d+)$"))
async def cb_key_card(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    key = await _owned_key(callback, session, user)
    if key is None:
        return
    await respond(
        callback, await key_card_screen(session, key), rich_buttons=user.rich_buttons_enabled
    )


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
    await respond(
        callback,
        await key_channels_screen(session, user, key),
        rich_buttons=user.rich_buttons_enabled,
    )


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
                callback,
                await key_channels_screen(session, user, key),
                rich_buttons=user.rich_buttons_enabled,
            )
            return

    now_bound = await api_key_service.toggle_key_channel(session, key, channel)
    await callback.answer(ru.CHANNEL_ADDED if now_bound else ru.CHANNEL_REMOVED)
    await respond(
        callback,
        await key_channels_screen(session, user, key),
        rich_buttons=user.rich_buttons_enabled,
    )


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
    new_key, raw = await api_key_service.rotate_key(session, cache, key)
    screen = Screen(ru.KEY_ROTATED.format(raw=raw), rows=[[Btn(ru.BTN_BACK, f"key:{new_key.id}")]])
    await respond(callback, screen, rich_buttons=user.rich_buttons_enabled)


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
    await respond(
        callback, await keys_list_screen(session, user), rich_buttons=user.rich_buttons_enabled
    )
