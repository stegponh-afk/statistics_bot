"""«Приветствие» on a group's card (admin side).

chat:{id}:welcome          the card
chat:{id}:welcome:set      ask for the greeting message (FSM)
chat:{id}:welcome:show     send the stored greeting to the admin
chat:{id}:welcome:clear    drop it
chat:{id}:welcome:toggle   greeting on/off
chat:{id}:welcome:mode     only the newcomer sees it / everyone does
chat:{id}:welcome:captcha  mute newcomers until they press «Я не бот»
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, User
from app.handlers.private.my_chats import load_admin_chat
from app.services import broadcast_delivery, welcome_service
from app.services.broadcast_service import content_from_message
from app.texts import ru
from app.ui import Btn, Screen, respond, send
from app.ui.blocks import strip_tags
from app.ui.buttons import STYLE_DANGER, STYLE_PRIMARY

router = Router(name="welcome")


class WelcomeEdit(StatesGroup):
    waiting_content = State()


def _rich(user: User | None) -> bool:
    return user.rich_buttons_enabled if user else True


def welcome_screen(chat: Chat) -> Screen:
    content = welcome_service.welcome_of(chat)
    if content is None:
        status = ru.WELCOME_STATUS_NONE
    else:
        snippet = strip_tags(content.text or "") or f"[{content.type}]"
        status = ru.WELCOME_STATUS_SET.format(snippet=snippet[:60])
    text = ru.WELCOME_CARD.format(
        title=chat.title or chat.telegram_id,
        status=status,
        state=ru.WELCOME_ON if chat.welcome_enabled else ru.WELCOME_OFF,
        mode=ru.WELCOME_MODE_PRIVATE if chat.welcome_ephemeral else ru.WELCOME_MODE_PUBLIC,
        captcha=ru.WELCOME_ON if chat.captcha_enabled else ru.WELCOME_OFF,
        captcha_note="" if chat.bot_can_restrict else ru.CAPTCHA_NO_RIGHT_NOTE,
    )
    rows = [[Btn(ru.BTN_WELCOME_SET, f"chat:{chat.id}:welcome:set", STYLE_PRIMARY)]]
    if content is not None:
        rows.append(
            [
                Btn(ru.BTN_WELCOME_SHOW, f"chat:{chat.id}:welcome:show"),
                Btn(ru.BTN_WELCOME_CLEAR, f"chat:{chat.id}:welcome:clear", STYLE_DANGER),
            ]
        )
        rows.append(
            [
                Btn(
                    ru.BTN_WELCOME_ON if chat.welcome_enabled else ru.BTN_WELCOME_OFF,
                    f"chat:{chat.id}:welcome:toggle",
                )
            ]
        )
        rows.append(
            [
                Btn(
                    ru.BTN_WELCOME_MODE_PRIVATE
                    if chat.welcome_ephemeral
                    else ru.BTN_WELCOME_MODE_PUBLIC,
                    f"chat:{chat.id}:welcome:mode",
                )
            ]
        )
    rows.append(
        [
            Btn(
                ru.BTN_CAPTCHA_ON if chat.captcha_enabled else ru.BTN_CAPTCHA_OFF,
                f"chat:{chat.id}:welcome:captcha",
            )
        ]
    )
    rows.append([Btn(ru.BTN_BACK, f"chat:{chat.id}")])
    return Screen(text, rows=rows)


async def _group(callback: CallbackQuery, session: AsyncSession, user: User) -> Chat | None:
    chat = await load_admin_chat(session, user, int(callback.data.split(":")[1]))
    if chat is None or chat.is_channel:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return None
    return chat


@router.callback_query(F.data.regexp(r"^chat:(\d+):welcome$"))
async def cb_welcome(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    await state.clear()
    chat = await _group(callback, session, user)
    if chat is None:
        return
    await respond(callback, welcome_screen(chat), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^chat:(\d+):welcome:set$"))
async def cb_welcome_set(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await _group(callback, session, user)
    if chat is None:
        return
    await state.set_state(WelcomeEdit.waiting_content)
    await state.update_data(chat_id=chat.id)
    screen = Screen(
        ru.WELCOME_ASK_CONTENT,
        rows=[[Btn(ru.BTN_CANCEL, f"chat:{chat.id}:welcome", STYLE_DANGER)]],
    )
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(WelcomeEdit.waiting_content)
async def on_welcome_content(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    data = await state.get_data()
    chat = await load_admin_chat(session, user, int(data.get("chat_id", 0)))
    if chat is None:
        await state.clear()
        return
    content = content_from_message(message)
    if content is None:
        await send(
            message.bot, message.chat.id, Screen(ru.BROADCAST_UNSUPPORTED), rich_buttons=_rich(user)
        )
        return
    await state.clear()
    await welcome_service.set_welcome(session, chat, content)
    await message.answer(ru.WELCOME_SAVED)
    await send(message.bot, message.chat.id, welcome_screen(chat), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^chat:(\d+):welcome:show$"))
async def cb_welcome_show(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await _group(callback, session, user)
    if chat is None:
        return
    content = welcome_service.welcome_of(chat)
    if content is None:
        await callback.answer(ru.WELCOME_NEED_CONTENT, show_alert=True)
        return
    preview = welcome_service.render(
        content,
        name=user.full_name or ru.WELCOME_SAMPLE_NAME,
        title=str(chat.title or chat.telegram_id),
    )
    await broadcast_delivery.send_content(
        callback.bot, callback.message.chat.id, preview, preview.file_id
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^chat:(\d+):welcome:clear$"))
async def cb_welcome_clear(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await _group(callback, session, user)
    if chat is None:
        return
    await welcome_service.clear_welcome(session, chat)
    await callback.answer(ru.WELCOME_CLEARED)
    await respond(callback, welcome_screen(chat), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^chat:(\d+):welcome:toggle$"))
async def cb_welcome_toggle(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await _group(callback, session, user)
    if chat is None:
        return
    if welcome_service.welcome_of(chat) is None:
        await callback.answer(ru.WELCOME_NEED_CONTENT, show_alert=True)
        return
    chat.welcome_enabled = not chat.welcome_enabled
    await session.commit()
    await callback.answer(ru.WELCOME_ENABLED if chat.welcome_enabled else ru.WELCOME_DISABLED)
    await respond(callback, welcome_screen(chat), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^chat:(\d+):welcome:mode$"))
async def cb_welcome_mode(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await _group(callback, session, user)
    if chat is None:
        return
    chat.welcome_ephemeral = not chat.welcome_ephemeral
    await session.commit()
    await callback.answer(
        ru.WELCOME_MODE_SET_PRIVATE if chat.welcome_ephemeral else ru.WELCOME_MODE_SET_PUBLIC
    )
    await respond(callback, welcome_screen(chat), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^chat:(\d+):welcome:captcha$"))
async def cb_welcome_captcha(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await _group(callback, session, user)
    if chat is None:
        return
    if not chat.captcha_enabled and not chat.bot_can_restrict:
        await callback.answer(ru.CAPTCHA_NEED_RIGHT, show_alert=True)
        return
    chat.captcha_enabled = not chat.captcha_enabled
    await session.commit()
    await callback.answer(ru.CAPTCHA_ENABLED if chat.captcha_enabled else ru.CAPTCHA_DISABLED)
    await respond(callback, welcome_screen(chat), rich_buttons=_rich(user))
