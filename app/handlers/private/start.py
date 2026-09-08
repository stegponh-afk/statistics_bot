from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.services.user_service import upsert_user
from app.texts import ru
from app.ui import Btn, Screen, respond, send
from config import settings

router = Router(name="start")


def _is_owner(user: User | None) -> bool:
    return user is not None and user.telegram_id in settings.owner_ids_list


def main_menu_screen(*, owner: bool = False) -> Screen:
    rows = [
        [Btn(ru.BTN_MY_CHATS, "chats:list"), Btn(ru.BTN_MY_BOTS, "keys:list")],
        [Btn(ru.BTN_BROADCAST, "bc:menu")],
        [Btn(ru.BTN_SETTINGS, "settings:menu"), Btn(ru.BTN_HELP, "menu:help")],
    ]
    if owner:
        rows.append([Btn(ru.BTN_ADMIN, "adm:menu")])
    return Screen(ru.MAIN_MENU_TITLE, rows=rows, has_back_row=False)


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    user = await upsert_user(session, message.from_user, started=True)
    await send(
        message.bot,
        message.chat.id,
        main_menu_screen(owner=_is_owner(user)),
        rich_buttons=user.rich_buttons_enabled,
    )


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, user: User | None) -> None:
    rich = user.rich_buttons_enabled if user else True
    await respond(callback, main_menu_screen(owner=_is_owner(user)), rich_buttons=rich)
