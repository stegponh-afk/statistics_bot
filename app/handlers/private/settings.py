from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.services.user_service import set_rich_buttons_enabled
from app.texts import ru
from app.ui import Btn, Screen, respond

router = Router(name="settings")


def settings_screen() -> Screen:
    return Screen(
        ru.SETTINGS_TITLE,
        rows=[
            [Btn(ru.BTN_MENU_STYLE, "settings:menu_style")],
            [Btn(ru.BTN_BACK, "menu:main")],
        ],
    )


def menu_style_screen(*, rich_buttons_enabled: bool) -> Screen:
    old_label = ru.BTN_MENU_STYLE_OLD if rich_buttons_enabled else f"✅ {ru.BTN_MENU_STYLE_OLD}"
    new_label = f"✅ {ru.BTN_MENU_STYLE_NEW}" if rich_buttons_enabled else ru.BTN_MENU_STYLE_NEW
    return Screen(
        ru.SETTINGS_MENU_STYLE_TITLE,
        rows=[
            [Btn(old_label, "settings:menu_style:old")],
            [Btn(new_label, "settings:menu_style:new")],
            [Btn(ru.BTN_BACK, "settings:menu")],
        ],
    )


@router.callback_query(F.data == "settings:menu")
async def cb_settings_menu(callback: CallbackQuery, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    await respond(callback, settings_screen(), rich_buttons=user.rich_buttons_enabled)


@router.callback_query(F.data == "settings:menu_style")
async def cb_menu_style(callback: CallbackQuery, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    await respond(
        callback,
        menu_style_screen(rich_buttons_enabled=user.rich_buttons_enabled),
        rich_buttons=user.rich_buttons_enabled,
    )


@router.callback_query(F.data.startswith("settings:menu_style:"))
async def cb_menu_style_set(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    enabled = callback.data.removeprefix("settings:menu_style:") == "new"
    user = await set_rich_buttons_enabled(session, user, enabled)
    await callback.answer(
        ru.SETTINGS_MENU_STYLE_SET_NEW if enabled else ru.SETTINGS_MENU_STYLE_SET_OLD
    )
    await respond(
        callback,
        menu_style_screen(rich_buttons_enabled=user.rich_buttons_enabled),
        rich_buttons=user.rich_buttons_enabled,
    )
