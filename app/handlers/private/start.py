from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.services.user_service import upsert_user
from app.texts import ru
from app.ui import Btn, Screen, respond, send

router = Router(name="start")


def main_menu_screen() -> Screen:
    return Screen(
        ru.MAIN_MENU_TITLE,
        rows=[
            [Btn(ru.BTN_MY_CHATS, "chats:list"), Btn(ru.BTN_MY_BOTS, "keys:list")],
            [Btn(ru.BTN_BROADCAST, "bc:menu")],
            [Btn(ru.BTN_SETTINGS, "settings:menu"), Btn(ru.BTN_HELP, "menu:help")],
        ],
        has_back_row=False,
    )


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    user = await upsert_user(session, message.from_user, started=True)
    await send(
        message.bot, message.chat.id, main_menu_screen(), rich_buttons=user.rich_buttons_enabled
    )


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, user: User | None) -> None:
    rich = user.rich_buttons_enabled if user else True
    await respond(callback, main_menu_screen(), rich_buttons=rich)
