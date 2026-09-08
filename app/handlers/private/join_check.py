"""«Проверить» inside the prompt an applicant got in their private chat:
jr:check:{chat_tg_id}."""

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import User
from app.screens.join import join_approved_screen, join_prompt_screen
from app.services import chat_service, forcesub_service, join_request_service
from app.services.subscription_checker import check_user
from app.texts import ru
from app.ui import Screen, respond

router = Router(name="join_check")

RECHECK_COOLDOWN = 3


async def _show(callback: CallbackQuery, screen: Screen, *, rich: bool, toast: str) -> None:
    """The prompt lives in the temporary private chat Telegram opened for
    the request; once that window closes, a toast is all that gets through."""
    try:
        await respond(callback, screen, rich_buttons=rich)
    except (TelegramBadRequest, TelegramForbiddenError):
        await callback.answer(toast, show_alert=True)


@router.callback_query(F.data.regexp(r"^jr:check:(-?\d+)$"))
async def cb_join_check(
    callback: CallbackQuery, session: AsyncSession, cache: Cache, user: User | None
) -> None:
    rich = user.rich_buttons_enabled if user else True
    chat = await chat_service.get_chat_by_telegram_id(session, int(callback.data.rsplit(":", 1)[1]))
    if chat is None:
        await callback.answer(ru.JOIN_REQUEST_GONE, show_alert=True)
        return

    if not await cache.set_if_absent(
        f"jr:cd:{chat.telegram_id}:{callback.from_user.id}", "1", RECHECK_COOLDOWN
    ):
        await callback.answer(ru.GATE_TOO_FAST)
        return

    if await join_request_service.recheck(
        callback.bot, session, cache, chat, callback.from_user.id, force=True
    ):
        await _show(callback, join_approved_screen(chat), rich=rich, toast=ru.JOIN_APPROVED_TOAST)
        return

    if await join_request_service.get_pending(session, chat, callback.from_user.id) is None:
        # Nothing is waiting: an admin already answered the request, or it
        # was withdrawn.
        await callback.answer(ru.JOIN_REQUEST_GONE, show_alert=True)
        return

    channels = await forcesub_service.list_required_channels(session, chat)
    result = await check_user(callback.bot, cache, callback.from_user.id, channels)
    screen = await join_prompt_screen(callback.bot, session, chat, result.missing)
    await _show(callback, screen, rich=rich, toast=ru.JOIN_STILL_MISSING)
