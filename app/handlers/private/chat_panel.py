"""Per-chat sections opened from the chat card in private chat:
chat:{id}:stats[:{tab}]."""

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.handlers.private.my_chats import load_admin_chat
from app.handlers.stats_screens import TABS, stats_screen
from app.texts import ru
from app.ui import Btn, respond

router = Router(name="chat_panel")


@router.callback_query(F.data.regexp(r"^chat:(\d+):stats(?::(\w+))?$"))
async def cb_chat_stats(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    parts = callback.data.split(":")
    chat_id, tab = int(parts[1]), (parts[3] if len(parts) > 3 else "overview")
    if tab not in TABS:
        tab = "overview"
    chat = await load_admin_chat(session, user, chat_id)
    if chat is None:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return
    screen = await stats_screen(
        tab,
        callback.bot,
        session,
        chat,
        target=lambda t: f"chat:{chat.id}:stats:{t}",
        back=Btn(ru.BTN_BACK, f"chat:{chat.id}"),
    )
    await respond(callback, screen, rich_buttons=user.rich_buttons_enabled)
