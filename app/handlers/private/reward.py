"""«Награда за подписку» on a channel's card (admin side).

chat:{id}:reward          the card: status + deep link
chat:{id}:reward:set      ask for the reward message (FSM)
chat:{id}:reward:show     send the stored reward to the admin
chat:{id}:reward:clear    drop it
chat:{id}:reward:post     ask for a post text, publish it in the channel
                          with a «Получить» button (FSM)
"""

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, User
from app.handlers.private.my_chats import load_admin_chat
from app.services import broadcast_delivery, reward_service
from app.services.broadcast_service import content_from_message
from app.texts import ru
from app.ui import Btn, Screen, respond, send
from app.ui.blocks import strip_tags
from app.ui.buttons import STYLE_DANGER, STYLE_PRIMARY

router = Router(name="reward")


class RewardEdit(StatesGroup):
    waiting_content = State()
    waiting_post = State()


def _rich(user: User | None) -> bool:
    return user.rich_buttons_enabled if user else True


async def reward_screen(bot, session: AsyncSession, channel: Chat) -> Screen:
    await reward_service.ensure_slug(session, channel)
    content = reward_service.reward_of(channel)
    if content is None:
        status = ru.REWARD_STATUS_NONE
    else:
        snippet = strip_tags(content.text or "") or f"[{content.type}]"
        status = ru.REWARD_STATUS_SET.format(snippet=snippet[:60])
    link = await reward_service.deep_link(bot, channel)
    text = ru.REWARD_CARD.format(
        title=channel.title or channel.telegram_id, status=status, link=link
    )
    rows = [[Btn(ru.BTN_REWARD_SET, f"chat:{channel.id}:reward:set", STYLE_PRIMARY)]]
    if content is not None:
        rows.append(
            [
                Btn(ru.BTN_REWARD_SHOW, f"chat:{channel.id}:reward:show"),
                Btn(ru.BTN_REWARD_CLEAR, f"chat:{channel.id}:reward:clear", STYLE_DANGER),
            ]
        )
        rows.append([Btn(ru.BTN_REWARD_POST, f"chat:{channel.id}:reward:post")])
    rows.append([Btn(ru.BTN_BACK, f"chat:{channel.id}")])
    return Screen(text, rows=rows)


async def _channel(callback: CallbackQuery, session: AsyncSession, user: User) -> Chat | None:
    channel = await load_admin_chat(session, user, int(callback.data.split(":")[1]))
    if channel is None or not channel.is_channel:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return None
    return channel


@router.callback_query(F.data.regexp(r"^chat:(\d+):reward$"))
async def cb_reward(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    await state.clear()
    channel = await _channel(callback, session, user)
    if channel is None:
        return
    await respond(
        callback, await reward_screen(callback.bot, session, channel), rich_buttons=_rich(user)
    )


@router.callback_query(F.data.regexp(r"^chat:(\d+):reward:set$"))
async def cb_reward_set(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    channel = await _channel(callback, session, user)
    if channel is None:
        return
    await state.set_state(RewardEdit.waiting_content)
    await state.update_data(chat_id=channel.id)
    screen = Screen(
        ru.REWARD_ASK_CONTENT,
        rows=[[Btn(ru.BTN_CANCEL, f"chat:{channel.id}:reward", STYLE_DANGER)]],
    )
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(RewardEdit.waiting_content)
async def on_reward_content(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    data = await state.get_data()
    channel = await load_admin_chat(session, user, int(data.get("chat_id", 0)))
    if channel is None:
        await state.clear()
        return
    content = content_from_message(message)
    if content is None:
        await send(
            message.bot, message.chat.id, Screen(ru.BROADCAST_UNSUPPORTED), rich_buttons=_rich(user)
        )
        return
    await state.clear()
    await reward_service.set_reward(session, channel, content)
    await message.answer(ru.REWARD_SAVED)
    await send(
        message.bot,
        message.chat.id,
        await reward_screen(message.bot, session, channel),
        rich_buttons=_rich(user),
    )


@router.callback_query(F.data.regexp(r"^chat:(\d+):reward:show$"))
async def cb_reward_show(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    channel = await _channel(callback, session, user)
    if channel is None:
        return
    content = reward_service.reward_of(channel)
    if content is None:
        await callback.answer(ru.REWARD_NEED_CONTENT, show_alert=True)
        return
    await broadcast_delivery._send(callback.bot, callback.message.chat.id, content, content.file_id)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^chat:(\d+):reward:clear$"))
async def cb_reward_clear(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    channel = await _channel(callback, session, user)
    if channel is None:
        return
    await reward_service.clear_reward(session, channel)
    await callback.answer(ru.REWARD_CLEARED)
    await respond(
        callback, await reward_screen(callback.bot, session, channel), rich_buttons=_rich(user)
    )


@router.callback_query(F.data.regexp(r"^chat:(\d+):reward:post$"))
async def cb_reward_post(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    channel = await _channel(callback, session, user)
    if channel is None:
        return
    if reward_service.reward_of(channel) is None:
        await callback.answer(ru.REWARD_NEED_CONTENT, show_alert=True)
        return
    await state.set_state(RewardEdit.waiting_post)
    await state.update_data(chat_id=channel.id)
    screen = Screen(
        ru.REWARD_ASK_POST.format(
            title=channel.title or channel.telegram_id, button=ru.REWARD_POST_BUTTON
        ),
        rows=[[Btn(ru.BTN_CANCEL, f"chat:{channel.id}:reward", STYLE_DANGER)]],
    )
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(RewardEdit.waiting_post)
async def on_reward_post(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    data = await state.get_data()
    channel = await load_admin_chat(session, user, int(data.get("chat_id", 0)))
    if channel is None:
        await state.clear()
        return
    content = content_from_message(message)
    if content is None:
        await send(
            message.bot, message.chat.id, Screen(ru.BROADCAST_UNSUPPORTED), rich_buttons=_rich(user)
        )
        return
    await state.clear()
    link = await reward_service.deep_link(bot=message.bot, channel=channel)
    content.buttons = [[{"text": ru.REWARD_POST_BUTTON, "url": link}]]
    try:
        await broadcast_delivery._send(message.bot, channel.telegram_id, content, content.file_id)
        await message.answer(ru.REWARD_POSTED)
    except (TelegramBadRequest, TelegramForbiddenError):
        await message.answer(ru.REWARD_POST_FAILED)
    await send(
        message.bot,
        message.chat.id,
        await reward_screen(message.bot, session, channel),
        rich_buttons=_rich(user),
    )


# re-exported for tests / other modules building the same markup
def reward_button_markup(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=ru.REWARD_POST_BUTTON, url=link)]]
    )
