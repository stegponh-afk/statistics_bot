from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.database.models import User
from app.texts import ru
from app.ui import Btn, Screen, respond, send

router = Router(name="private_help")


def help_screen() -> Screen:
    return Screen(ru.HELP_PRIVATE, rows=[[Btn(ru.BTN_BACK, "menu:main")]])


@router.message(Command("help"))
async def cmd_help(message: Message, user: User | None) -> None:
    rich = user.rich_buttons_enabled if user else True
    await send(message.bot, message.chat.id, help_screen(), rich_buttons=rich)


@router.callback_query(F.data == "menu:help")
async def cb_help(callback: CallbackQuery, user: User | None) -> None:
    rich = user.rich_buttons_enabled if user else True
    await respond(callback, help_screen(), rich_buttons=rich)
