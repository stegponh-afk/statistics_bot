"""On a channel's card: check one specific user's subscription by hand.

chat:{id}:check      ask for a user id / forwarded message (FSM)
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.handlers.private.my_chats import load_admin_chat
from app.handlers.private.whitelist import _user_id_from_message
from app.services.subscription_checker import member_status
from app.services.user_service import get_user_by_telegram_id
from app.texts import ru
from app.ui import Btn, Screen, respond, send
from app.ui.buttons import STYLE_DANGER
from app.utils import display_name

router = Router(name="channel_check")


class ChannelCheck(StatesGroup):
    waiting_user = State()


def _rich(user: User | None) -> bool:
    return user.rich_buttons_enabled if user else True


@router.callback_query(F.data.regexp(r"^chat:(\d+):check$"))
async def cb_check_ask(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    channel = await load_admin_chat(session, user, int(callback.data.split(":")[1]))
    if channel is None or not channel.is_channel:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return
    await state.set_state(ChannelCheck.waiting_user)
    await state.update_data(chat_id=channel.id)
    screen = Screen(
        ru.CHECK_ASK_USER.format(title=channel.title or channel.telegram_id),
        rows=[[Btn(ru.BTN_CANCEL, f"chat:{channel.id}", STYLE_DANGER)]],
    )
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(ChannelCheck.waiting_user)
async def on_check_user(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    data = await state.get_data()
    channel = await load_admin_chat(session, user, int(data.get("chat_id", 0)))
    if channel is None:
        await state.clear()
        return
    target = _user_id_from_message(message)
    if target is None:
        await send(
            message.bot, message.chat.id, Screen(ru.CHECK_BAD_INPUT), rich_buttons=_rich(user)
        )
        return

    known = await get_users_by_id(session, target)
    name = known if known else f"id:{target}"
    status = await member_status(message.bot, channel.telegram_id, target)
    if status is None:
        text = ru.CHECK_UNAVAILABLE.format(title=channel.title or channel.telegram_id)
    else:
        subscribed, label = status
        text = (ru.CHECK_SUBSCRIBED if subscribed else ru.CHECK_NOT_SUBSCRIBED).format(
            name=name, title=channel.title or channel.telegram_id, status=label
        )
    # Stay in the state: the admin can send the next id right away.
    screen = Screen(text, rows=[[Btn(ru.BTN_BACK, f"chat:{channel.id}")]])
    await send(message.bot, message.chat.id, screen, rich_buttons=_rich(user))


async def get_users_by_id(session: AsyncSession, telegram_id: int) -> str | None:
    u = await get_user_by_telegram_id(session, telegram_id)
    if u is None:
        return None
    return display_name(u.full_name, u.username, u.telegram_id)
