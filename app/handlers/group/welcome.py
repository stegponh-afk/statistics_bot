"""«Я не бот» inside the captcha challenge: wc:ok:{chat_tg_id}."""

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import Chat, User
from app.services import welcome_service
from app.texts import ru
from app.ui import Screen, respond
from app.utils import display_name

router = Router(name="welcome_callbacks")


@router.callback_query(F.data.regexp(r"^wc:ok:(-?\d+)$"))
async def cb_captcha_ok(
    callback: CallbackQuery,
    session: AsyncSession,
    cache: Cache,
    user: User | None,
    chat_row: Chat | None,
) -> None:
    if chat_row is None or chat_row.telegram_id != int(callback.data.rsplit(":", 1)[1]):
        await callback.answer()
        return
    rich = user.rich_buttons_enabled if user else True

    if not await welcome_service.pass_captcha(callback.bot, cache, chat_row, callback.from_user.id):
        await callback.answer(ru.CAPTCHA_NOT_PENDING)
        return

    name = (
        display_name(user.full_name, user.username, callback.from_user.id)
        if user
        else callback.from_user.full_name
    )
    # A text-only greeting replaces the challenge in place; anything richer
    # (media, buttons, Telegram formatting) has to be a message of its own.
    inline = welcome_service.text_screen(chat_row, name) if chat_row.welcome_enabled else None
    await respond(callback, inline or Screen(ru.CAPTCHA_OK, has_back_row=False), rich_buttons=rich)
    if chat_row.welcome_enabled and inline is None:
        await welcome_service.deliver_welcome(callback.bot, chat_row, callback.from_user.id, name)
