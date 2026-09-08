"""«Проверить» inside the gate prompt: gate:check:{chat_tg_id}."""

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import Chat, User
from app.screens.gate import gate_ok_screen, gate_prompt_screen
from app.services import forcesub_service
from app.services.subscription_checker import check_user
from app.texts import ru
from app.ui import respond

router = Router(name="gate_callbacks")

RECHECK_COOLDOWN = 3


@router.callback_query(F.data.regexp(r"^gate:check:(-?\d+)$"))
async def cb_gate_check(
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

    if not await cache.set_if_absent(
        f"gate:cd:{chat_row.telegram_id}:{callback.from_user.id}", "1", RECHECK_COOLDOWN
    ):
        await callback.answer(ru.GATE_TOO_FAST)
        return

    channels = await forcesub_service.list_required_channels(session, chat_row)
    result = await check_user(callback.bot, cache, callback.from_user.id, channels, force=True)
    if result.subscribed:
        await respond(callback, gate_ok_screen(), rich_buttons=rich)
        return

    screen = await gate_prompt_screen(callback.bot, session, chat_row, result.missing)
    await respond(callback, screen, rich_buttons=rich)
    await callback.answer(ru.GATE_STILL_MISSING)
