"""Owner-only admin menu (OWNER_IDS): totals across every chat, bot and user.

adm:menu      the overview        adm:refresh   re-count members first
adm:channels  every channel       adm:groups    every group
adm:bots      every registered bot
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, User
from app.services import admin_stats
from app.texts import ru
from app.ui import Btn, Screen, respond, send
from app.utils import display_name
from config import settings

router = Router(name="owner_admin")


def is_owner(user: User | None) -> bool:
    return user is not None and user.telegram_id in settings.owner_ids_list


def _rich(user: User | None) -> bool:
    return user.rich_buttons_enabled if user else True


def _menu_rows() -> list[list[Btn]]:
    return [
        [
            Btn(ru.BTN_ADMIN_CHANNELS, "adm:channels"),
            Btn(ru.BTN_ADMIN_GROUPS, "adm:groups"),
            Btn(ru.BTN_ADMIN_BOTS, "adm:bots"),
        ],
        [Btn(ru.BTN_REFRESH, "adm:refresh")],
        [Btn(ru.BTN_BACK, "menu:main")],
    ]


async def overview_screen(session: AsyncSession) -> Screen:
    o = await admin_stats.overview(session)
    text = ru.ADMIN_OVERVIEW.format(
        users_total=o.users_total,
        users_started=o.users_started,
        users_new_today=o.users_new_today,
        users_new_week=o.users_new_week,
        channels=o.channels,
        channel_members=o.channel_members,
        groups=o.groups,
        group_members=o.group_members,
        bots=o.bots,
        api_requests=o.api_requests,
        broadcasts=o.broadcasts_scheduled,
        events=o.message_events,
    )
    return Screen(text, rows=_menu_rows())


def _owner_label(owner: User | None) -> str:
    if owner is None:
        return "—"
    name = display_name(owner.full_name, owner.username, owner.telegram_id)
    return f"{name} (id:{owner.telegram_id})"


async def chats_screen(session: AsyncSession, *, channels: bool) -> Screen:
    rows = await admin_stats.list_chats(session, channels=channels)
    title = ru.ADMIN_CHANNELS_TITLE if channels else ru.ADMIN_GROUPS_TITLE
    lines = [title, ru.SEPARATOR]
    if not rows:
        lines.append(ru.ADMIN_LIST_EMPTY)
    for r in rows[:50]:
        lines.append(
            ru.ADMIN_CHAT_ROW.format(
                title=r.chat.title or r.chat.telegram_id,
                username=f" @{r.chat.username}" if r.chat.username else "",
                members=r.members if r.members is not None else "?",
                owner=_owner_label(r.owner),
            )
        )
    if len(rows) > 50:
        lines.append(ru.ADMIN_LIST_MORE.format(count=len(rows) - 50))
    return Screen("\n".join(lines), rows=[[Btn(ru.BTN_BACK, "adm:menu")]])


async def bots_screen(session: AsyncSession) -> Screen:
    rows = await admin_stats.list_bots(session)
    lines = [ru.ADMIN_BOTS_TITLE, ru.SEPARATOR]
    if not rows:
        lines.append(ru.ADMIN_LIST_EMPTY)
    for r in rows[:50]:
        lines.append(
            ru.ADMIN_BOT_ROW.format(
                name=r.key.name,
                channels=r.channels,
                requests=r.key.request_count,
                owner=_owner_label(r.owner),
            )
        )
    if len(rows) > 50:
        lines.append(ru.ADMIN_LIST_MORE.format(count=len(rows) - 50))
    return Screen("\n".join(lines), rows=[[Btn(ru.BTN_BACK, "adm:menu")]])


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession, user: User | None) -> None:
    if not is_owner(user):
        return
    await admin_stats.refresh_member_counts(message.bot, session)
    await send(
        message.bot, message.chat.id, await overview_screen(session), rich_buttons=_rich(user)
    )


@router.callback_query(F.data.in_({"adm:menu", "adm:refresh"}))
async def cb_admin_menu(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if not is_owner(user):
        await callback.answer()
        return
    if callback.data == "adm:refresh":
        for chat in await session.scalars(select(Chat)):
            chat.member_count_updated_at = None
        await session.commit()
    await admin_stats.refresh_member_counts(callback.bot, session)
    await respond(callback, await overview_screen(session), rich_buttons=_rich(user))


@router.callback_query(F.data.in_({"adm:channels", "adm:groups"}))
async def cb_admin_chats(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if not is_owner(user):
        await callback.answer()
        return
    screen = await chats_screen(session, channels=callback.data == "adm:channels")
    await respond(callback, screen, rich_buttons=_rich(user))


@router.callback_query(F.data == "adm:bots")
async def cb_admin_bots(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if not is_owner(user):
        await callback.answer()
        return
    await respond(callback, await bots_screen(session), rich_buttons=_rich(user))
