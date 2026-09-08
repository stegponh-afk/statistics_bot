"""Numbers for the owner's admin menu (OWNER_IDS)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    ApiKey,
    BotAudience,
    BotStatus,
    Broadcast,
    BroadcastStatus,
    Chat,
    ChatAdmin,
    ChatKind,
    MessageEvent,
    User,
)
from app.services import chat_service

# How many chats one overview may refresh member counts for (each stale
# chat costs one getChatMemberCount call).
MAX_REFRESH_PER_VIEW = 200

_ACTIVE = Chat.bot_status.in_([BotStatus.MEMBER, BotStatus.ADMINISTRATOR])


@dataclass(frozen=True)
class Overview:
    users_total: int
    users_started: int
    users_new_today: int
    users_new_week: int
    groups: int
    channels: int
    group_members: int
    channel_members: int
    bots: int
    bots_with_token: int
    audience_total: int  # sum over bots (a user in two bots counts twice)
    audience_distinct: int
    api_requests: int
    broadcasts_scheduled: int
    message_events: int


async def _count(session: AsyncSession, stmt) -> int:
    return int(await session.scalar(stmt) or 0)


async def refresh_member_counts(bot: Bot, session: AsyncSession) -> None:
    chats = list(await session.scalars(select(Chat).where(_ACTIVE).limit(MAX_REFRESH_PER_VIEW)))
    for chat in chats:
        await chat_service.get_member_count(bot, session, chat)


async def overview(session: AsyncSession) -> Overview:
    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    users_row = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(case((User.started_bot.is_(True), 1), else_=0)), 0),
                func.coalesce(func.sum(case((User.created_at >= today, 1), else_=0)), 0),
                func.coalesce(func.sum(case((User.created_at >= week_ago, 1), else_=0)), 0),
            )
        )
    ).one()

    chats_row = (
        await session.execute(
            select(
                func.coalesce(func.sum(case((Chat.type != ChatKind.CHANNEL, 1), else_=0)), 0),
                func.coalesce(func.sum(case((Chat.type == ChatKind.CHANNEL, 1), else_=0)), 0),
                func.coalesce(
                    func.sum(case((Chat.type != ChatKind.CHANNEL, Chat.member_count), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((Chat.type == ChatKind.CHANNEL, Chat.member_count), else_=0)), 0
                ),
            ).where(_ACTIVE)
        )
    ).one()

    bots_row = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(case((ApiKey.bot_token.is_not(None), 1), else_=0)), 0),
                func.coalesce(func.sum(ApiKey.request_count), 0),
            ).where(ApiKey.is_active.is_(True))
        )
    ).one()

    audience_total = await _count(
        session,
        select(func.count())
        .select_from(BotAudience)
        .join(ApiKey, ApiKey.id == BotAudience.api_key_id)
        .where(BotAudience.is_blocked.is_(False), ApiKey.is_active.is_(True)),
    )
    audience_distinct = await _count(
        session,
        select(func.count(func.distinct(BotAudience.user_tg_id)))
        .select_from(BotAudience)
        .join(ApiKey, ApiKey.id == BotAudience.api_key_id)
        .where(BotAudience.is_blocked.is_(False), ApiKey.is_active.is_(True)),
    )
    broadcasts_scheduled = await _count(
        session,
        select(func.count())
        .select_from(Broadcast)
        .where(Broadcast.status == BroadcastStatus.SCHEDULED.value),
    )
    events = await _count(session, select(func.count()).select_from(MessageEvent))

    return Overview(
        users_total=int(users_row[0]),
        users_started=int(users_row[1]),
        users_new_today=int(users_row[2]),
        users_new_week=int(users_row[3]),
        groups=int(chats_row[0]),
        channels=int(chats_row[1]),
        group_members=int(chats_row[2]),
        channel_members=int(chats_row[3]),
        bots=int(bots_row[0]),
        bots_with_token=int(bots_row[1]),
        audience_total=audience_total,
        audience_distinct=audience_distinct,
        api_requests=int(bots_row[2]),
        broadcasts_scheduled=broadcasts_scheduled,
        message_events=events,
    )


@dataclass(frozen=True)
class ChatRow:
    chat: Chat
    members: int | None
    owner: User | None


async def list_chats(session: AsyncSession, *, channels: bool) -> list[ChatRow]:
    """Active chats of one kind with member counts and one admin (the
    creator if known), most members first."""
    kind_filter = Chat.type == ChatKind.CHANNEL if channels else Chat.type != ChatKind.CHANNEL
    chats = list(
        await session.scalars(
            select(Chat)
            .where(_ACTIVE, kind_filter)
            .order_by(Chat.member_count.desc().nulls_last(), Chat.title)
        )
    )
    rows: list[ChatRow] = []
    for chat in chats:
        owner = await session.scalar(
            select(User)
            .join(ChatAdmin, ChatAdmin.user_id == User.id)
            .where(ChatAdmin.chat_id == chat.id)
            .order_by(ChatAdmin.status)  # "creator" sorts before "administrator"
            .limit(1)
        )
        rows.append(ChatRow(chat=chat, members=chat.member_count, owner=owner))
    return rows


@dataclass(frozen=True)
class BotRow:
    key: ApiKey
    owner: User | None
    audience: int
    channels: int


async def list_bots(session: AsyncSession) -> list[BotRow]:
    from app.services import api_key_service, audience_service

    keys = list(
        await session.scalars(
            select(ApiKey).where(ApiKey.is_active.is_(True)).order_by(ApiKey.created_at)
        )
    )
    rows: list[BotRow] = []
    for key in keys:
        owner = await session.get(User, key.owner_user_id)
        reachable, _ = await audience_service.audience_size(session, key)
        channels = await api_key_service.list_key_channels(session, key)
        rows.append(BotRow(key=key, owner=owner, audience=reachable, channels=len(channels)))
    return rows
