"""Per-chat whitelist (users the gate never checks).

chat:{id}:whitelist                 the list; 🗑 rows remove
chat:{id}:whitelist:add             ask for an id / forwarded message (FSM)
chat:{id}:whitelist:rm:{user_tg_id} remove one
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, MessageOriginUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import Chat, User
from app.handlers.private.my_chats import load_admin_chat
from app.services import forcesub_service
from app.services.user_service import get_users_by_telegram_ids
from app.texts import ru
from app.ui import Btn, Screen, respond, send
from app.ui.buttons import STYLE_DANGER
from app.utils import display_name

router = Router(name="whitelist")


class WhitelistAdd(StatesGroup):
    waiting = State()


async def whitelist_screen(session: AsyncSession, chat: Chat) -> Screen:
    entries = await forcesub_service.list_whitelist(session, chat)
    users = await get_users_by_telegram_ids(session, [e.user_tg_id for e in entries])
    text = ru.WHITELIST_TITLE.format(title=chat.title or chat.telegram_id)
    if not entries:
        text += f"\n{ru.WHITELIST_EMPTY_LINE}"
    rows = []
    for e in entries:
        u = users.get(e.user_tg_id)
        name = display_name(u.full_name, u.username, e.user_tg_id) if u else f"id:{e.user_tg_id}"
        rows.append(
            [Btn(ru.WHITELIST_ROW.format(name=name), f"chat:{chat.id}:whitelist:rm:{e.user_tg_id}")]
        )
    rows.append([Btn(ru.BTN_WHITELIST_ADD, f"chat:{chat.id}:whitelist:add")])
    rows.append([Btn(ru.BTN_BACK, f"chat:{chat.id}")])
    return Screen(text, rows=rows)


@router.callback_query(F.data.regexp(r"^chat:(\d+):whitelist$"))
async def cb_whitelist(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    await state.clear()
    chat = await load_admin_chat(session, user, int(callback.data.split(":")[1]))
    if chat is None:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return
    await respond(
        callback, await whitelist_screen(session, chat), rich_buttons=user.rich_buttons_enabled
    )


@router.callback_query(F.data.regexp(r"^chat:(\d+):whitelist:rm:(\d+)$"))
async def cb_whitelist_remove(
    callback: CallbackQuery, session: AsyncSession, user: User | None, cache: Cache
) -> None:
    if user is None:
        await callback.answer()
        return
    parts = callback.data.split(":")
    chat = await load_admin_chat(session, user, int(parts[1]))
    if chat is None:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return
    await forcesub_service.remove_from_whitelist(session, cache, chat, int(parts[4]))
    await callback.answer(ru.WHITELIST_REMOVED)
    await respond(
        callback, await whitelist_screen(session, chat), rich_buttons=user.rich_buttons_enabled
    )


@router.callback_query(F.data.regexp(r"^chat:(\d+):whitelist:add$"))
async def cb_whitelist_add(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await load_admin_chat(session, user, int(callback.data.split(":")[1]))
    if chat is None:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return
    await state.set_state(WhitelistAdd.waiting)
    await state.update_data(chat_id=chat.id)
    screen = Screen(
        ru.WHITELIST_ASK, rows=[[Btn(ru.BTN_CANCEL, f"chat:{chat.id}:whitelist", STYLE_DANGER)]]
    )
    await respond(callback, screen, rich_buttons=user.rich_buttons_enabled)


def _user_id_from_message(message: Message) -> int | None:
    if isinstance(message.forward_origin, MessageOriginUser):
        return message.forward_origin.sender_user.id
    if message.text and message.text.strip().lstrip("-").isdigit():
        return int(message.text.strip())
    return None


@router.message(WhitelistAdd.waiting)
async def on_whitelist_input(
    message: Message, session: AsyncSession, user: User | None, cache: Cache, state: FSMContext
) -> None:
    if user is None:
        return
    data = await state.get_data()
    chat = await load_admin_chat(session, user, int(data.get("chat_id", 0)))
    if chat is None:
        await state.clear()
        return
    target = _user_id_from_message(message)
    rich = user.rich_buttons_enabled
    if target is None:
        await send(message.bot, message.chat.id, Screen(ru.WHITELIST_BAD_INPUT), rich_buttons=rich)
        return
    await state.clear()
    added = await forcesub_service.add_to_whitelist(session, cache, chat, target, user)
    await message.answer(ru.WHITELIST_ADDED if added else ru.WHITELIST_ALREADY)
    await send(
        message.bot, message.chat.id, await whitelist_screen(session, chat), rich_buttons=rich
    )
