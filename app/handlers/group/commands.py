"""Slash commands inside groups. Every answer is ephemeral — only the
person who sent the command sees it."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import Chat, User
from app.screens.stats import me_screen, overview_screen
from app.services import forcesub_service
from app.texts import ru
from app.ui import Screen, reply_to_command
from app.utils import display_name

router = Router(name="group_commands")


def _rich(user: User | None) -> bool:
    return user.rich_buttons_enabled if user else True


@router.message(Command("help"))
async def cmd_help(message: Message, user: User | None) -> None:
    await reply_to_command(
        message,
        Screen(ru.HELP_GROUP),
        rich_buttons=_rich(user),
        delete_public=True,
        public_fallback=True,
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
        await reply_to_command(
            message, Screen(ru.ME_NO_USER), rich_buttons=_rich(user), public_fallback=True
        )
        return
    screen = await me_screen(session, chat_row, message.from_user.id)
    await reply_to_command(message, screen, rich_buttons=_rich(user), delete_public=True)


@router.message(Command("whitelist"))
async def cmd_whitelist(
    message: Message,
    session: AsyncSession,
    user: User | None,
    chat_row: Chat | None,
    is_chat_admin: bool,
    cache: Cache,
) -> None:
    if chat_row is None or not is_chat_admin:
        return
    replied = message.reply_to_message
    if replied is None or replied.from_user is None or replied.from_user.is_bot:
        await reply_to_command(
            message,
            Screen(ru.WHITELIST_CMD_NEED_REPLY),
            rich_buttons=_rich(user),
            delete_public=True,
        )
        return
    target = replied.from_user
    await forcesub_service.add_to_whitelist(session, cache, chat_row, target.id, user)
    name = display_name(target.full_name, target.username, target.id)
    # An anonymous admin gets this one in the chat: a confirmation that
    # somebody may now write without subscribing is not a secret, and the
    # command itself was typed in the open.
    await reply_to_command(
        message,
        Screen(ru.WHITELIST_CMD_ADDED.format(name=name)),
        rich_buttons=_rich(user),
        delete_public=True,
        public_fallback=True,
    )
