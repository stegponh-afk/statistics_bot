"""Slash commands inside groups. Every answer is ephemeral — only the
person who sent the command sees it."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, User
from app.handlers.stats_screens import me_screen, overview_screen
from app.texts import ru
from app.ui import Screen, reply_to_command

router = Router(name="group_commands")


def _rich(user: User | None) -> bool:
    return user.rich_buttons_enabled if user else True


@router.message(Command("help"))
async def cmd_help(message: Message, user: User | None) -> None:
    await reply_to_command(
        message, Screen(ru.HELP_GROUP), rich_buttons=_rich(user), delete_public=True
    )


@router.message(Command("stats"))
async def cmd_stats(
    message: Message,
    session: AsyncSession,
    user: User | None,
    chat_row: Chat | None,
    is_chat_admin: bool,
) -> None:
    if chat_row is None:
        return
    if not is_chat_admin:
        await reply_to_command(
            message, Screen(ru.STATS_ONLY_FOR_ADMINS), rich_buttons=_rich(user), delete_public=True
        )
        return
    screen = await overview_screen(
        message.bot,
        session,
        chat_row,
        target=lambda tab: f"gstats:{chat_row.telegram_id}:{tab}",
        back=None,
    )
    await reply_to_command(message, screen, rich_buttons=_rich(user), delete_public=True)


@router.message(Command("me"))
async def cmd_me(
    message: Message, session: AsyncSession, user: User | None, chat_row: Chat | None
) -> None:
    if chat_row is None:
        return
    if message.from_user is None or message.sender_chat is not None:
        await reply_to_command(message, Screen(ru.ME_NO_USER), rich_buttons=_rich(user))
        return
    screen = await me_screen(session, chat_row, message.from_user.id)
    await reply_to_command(message, screen, rich_buttons=_rich(user), delete_public=True)
