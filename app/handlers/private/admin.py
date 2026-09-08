"""/admin — a one-screen overview for the bot's owners (OWNER_IDS)."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ApiKey, BotStatus, Chat, ChatKind, MessageEvent, User
from app.texts import ru
from app.ui import Btn, Screen, send
from config import settings

router = Router(name="owner_admin")


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession, user: User | None) -> None:
    if message.from_user is None or message.from_user.id not in settings.owner_ids_list:
        return
    active = Chat.bot_status.in_([BotStatus.MEMBER, BotStatus.ADMINISTRATOR])
    users = await session.scalar(select(func.count()).select_from(User))
    groups = await session.scalar(
        select(func.count()).select_from(Chat).where(active, Chat.type != ChatKind.CHANNEL)
    )
    channels = await session.scalar(
        select(func.count()).select_from(Chat).where(active, Chat.type == ChatKind.CHANNEL)
    )
    gated = await session.scalar(
        select(func.count()).select_from(Chat).where(active, Chat.forcesub_enabled.is_(True))
    )
    keys = await session.scalar(
        select(func.count()).select_from(ApiKey).where(ApiKey.is_active.is_(True))
    )
    events = await session.scalar(select(func.count()).select_from(MessageEvent))
    text = ru.ADMIN_OVERVIEW.format(
        users=users,
        chats=(groups or 0) + (channels or 0),
        groups=groups,
        channels=channels,
        gated=gated,
        keys=keys,
        events=events,
    )
    rich = user.rich_buttons_enabled if user else True
    await send(
        message.bot,
        message.chat.id,
        Screen(text, rows=[[Btn(ru.BTN_BACK, "menu:main")]]),
        rich_buttons=rich,
    )
