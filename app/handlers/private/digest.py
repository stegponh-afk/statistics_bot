"""«Отчёты» on a chat's card (admin side).

chat:{id}:digest                 the card
chat:{id}:digest:toggle          reports on/off
chat:{id}:digest:period:{p}      daily | weekly
chat:{id}:digest:time            ask for HH:MM (FSM)
chat:{id}:digest:preview         send the report as it looks right now
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, User
from app.handlers.private.my_chats import load_admin_chat
from app.services import digest_service
from app.services.broadcast_service import parse_time
from app.texts import ru
from app.ui import Btn, Screen, respond, send
from app.ui.buttons import STYLE_DANGER, STYLE_PRIMARY
from config import settings

router = Router(name="digest")


class DigestEdit(StatesGroup):
    waiting_time = State()


def _rich(user: User | None) -> bool:
    return user.rich_buttons_enabled if user else True


def _tz(chat: Chat) -> str:
    return chat.timezone or settings.default_timezone


async def digest_screen(session: AsyncSession, chat: Chat) -> Screen:
    weekly = chat.digest_period == digest_service.WEEKLY
    admins = len(await digest_service.recipients(session, chat))
    text = ru.DIGEST_CARD.format(
        title=chat.title or chat.telegram_id,
        state=ru.WELCOME_ON if chat.digest_enabled else ru.WELCOME_OFF,
        period=ru.DIGEST_PERIOD_WEEKLY_LABEL if weekly else ru.DIGEST_PERIOD_DAILY_LABEL,
        time=chat.digest_time,
        tz=_tz(chat),
        admins=admins,
        admins_note=ru.DIGEST_NO_RECIPIENTS if not admins else "",
    )
    rows = [
        [
            Btn(
                ru.BTN_DIGEST_ON if chat.digest_enabled else ru.BTN_DIGEST_OFF,
                f"chat:{chat.id}:digest:toggle",
                STYLE_PRIMARY if not chat.digest_enabled else None,
            )
        ],
        [
            Btn(
                ru.BTN_DIGEST_DAILY_ON if not weekly else ru.BTN_DIGEST_DAILY,
                f"chat:{chat.id}:digest:period:daily",
            ),
            Btn(
                ru.BTN_DIGEST_WEEKLY_ON if weekly else ru.BTN_DIGEST_WEEKLY,
                f"chat:{chat.id}:digest:period:weekly",
            ),
        ],
        [
            Btn(ru.BTN_DIGEST_TIME.format(time=chat.digest_time), f"chat:{chat.id}:digest:time"),
            Btn(ru.BTN_DIGEST_PREVIEW, f"chat:{chat.id}:digest:preview"),
        ],
        [Btn(ru.BTN_BACK, f"chat:{chat.id}")],
    ]
    return Screen(text, rows=rows)


async def _chat(callback: CallbackQuery, session: AsyncSession, user: User) -> Chat | None:
    chat = await load_admin_chat(session, user, int(callback.data.split(":")[1]))
    if chat is None:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return None
    return chat


@router.callback_query(F.data.regexp(r"^chat:(\d+):digest$"))
async def cb_digest(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    await state.clear()
    chat = await _chat(callback, session, user)
    if chat is None:
        return
    await respond(callback, await digest_screen(session, chat), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^chat:(\d+):digest:toggle$"))
async def cb_digest_toggle(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await _chat(callback, session, user)
    if chat is None:
        return
    chat.digest_enabled = not chat.digest_enabled
    if chat.digest_enabled:
        # Today is already partly gone: start with tomorrow's report rather
        # than firing one the moment the switch is flipped.
        chat.digest_last_day = digest_service.local_now(chat).date()
    await session.commit()
    await callback.answer(ru.DIGEST_ENABLED if chat.digest_enabled else ru.DIGEST_DISABLED)
    await respond(callback, await digest_screen(session, chat), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^chat:(\d+):digest:period:(daily|weekly)$"))
async def cb_digest_period(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await _chat(callback, session, user)
    if chat is None:
        return
    chat.digest_period = callback.data.rsplit(":", 1)[1]
    await session.commit()
    await callback.answer(
        ru.DIGEST_PERIOD_SET_WEEKLY
        if chat.digest_period == digest_service.WEEKLY
        else ru.DIGEST_PERIOD_SET_DAILY
    )
    await respond(callback, await digest_screen(session, chat), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^chat:(\d+):digest:time$"))
async def cb_digest_time(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await _chat(callback, session, user)
    if chat is None:
        return
    await state.set_state(DigestEdit.waiting_time)
    await state.update_data(chat_id=chat.id)
    screen = Screen(
        ru.DIGEST_ASK_TIME.format(tz=_tz(chat)),
        rows=[[Btn(ru.BTN_CANCEL, f"chat:{chat.id}:digest", STYLE_DANGER)]],
    )
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(DigestEdit.waiting_time, F.text)
async def on_digest_time(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    parsed = parse_time(message.text)
    if parsed is None:
        await message.answer(ru.BROADCAST_BAD_TIME)
        return
    data = await state.get_data()
    chat = await load_admin_chat(session, user, int(data.get("chat_id", 0)))
    if chat is None:
        await state.clear()
        return
    await state.clear()
    chat.digest_time = parsed.strftime("%H:%M")
    await session.commit()
    await send(
        message.bot, message.chat.id, await digest_screen(session, chat), rich_buttons=_rich(user)
    )


@router.callback_query(F.data.regexp(r"^chat:(\d+):digest:preview$"))
async def cb_digest_preview(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await _chat(callback, session, user)
    if chat is None:
        return
    screen = await digest_service.build_screen(session, chat, digest_service.local_now(chat).date())
    await callback.answer()
    await send(callback.bot, callback.message.chat.id, screen, rich_buttons=_rich(user))
