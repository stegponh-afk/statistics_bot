"""Tab buttons inside the ephemeral /stats message: gstats:{chat_tg_id}:{tab}."""

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, User
from app.screens.stats import TABS, stats_screen
from app.texts import ru
from app.ui import respond

router = Router(name="group_stats_callbacks")


@router.callback_query(F.data.regexp(r"^gstats:(-?\d+):(\w+)$"))
async def cb_group_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User | None,
    chat_row: Chat | None,
    is_chat_admin: bool,
) -> None:
    _, chat_tg_id, tab = callback.data.split(":")
    if chat_row is None or chat_row.telegram_id != int(chat_tg_id) or tab not in TABS:
        await callback.answer()
        return
    if not is_chat_admin:
        await callback.answer(ru.STATS_ONLY_FOR_ADMINS_TOAST, show_alert=True)
        return
    screen = await stats_screen(
        tab,
        callback.bot,
        session,
        chat_row,
        target=lambda t: f"gstats:{chat_row.telegram_id}:{t}",
        back=None,
    )
    await respond(callback, screen, rich_buttons=user.rich_buttons_enabled if user else True)
