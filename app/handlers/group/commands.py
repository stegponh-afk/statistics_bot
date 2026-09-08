"""Slash commands inside groups. Every answer is ephemeral — only the
person who sent the command sees it."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.database.models import User
from app.texts import ru
from app.ui import Screen, reply_to_command

router = Router(name="group_commands")


@router.message(Command("help"))
async def cmd_help(message: Message, user: User | None) -> None:
    rich = user.rich_buttons_enabled if user else True
    await reply_to_command(message, Screen(ru.HELP_GROUP), rich_buttons=rich, delete_public=True)
