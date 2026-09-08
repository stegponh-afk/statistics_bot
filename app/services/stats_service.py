"""Chat statistics: the write path (one row per message + per-day word
counts, no text) and every read query behind /stats and /me.

All time arithmetic happens on message_events.local_day / local_hour,
computed at write time in the chat's timezone — so the queries are plain
Date comparisons that behave the same on PostgreSQL and sqlite."""

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from aiogram.types import Message
from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, MessageEvent, WordStatDaily
from app.services.forcesub_service import SERVICE_CONTENT_TYPES
from app.services.tokenizer import tokenize
from app.utils import ensure_aware, localize

WEEK = 7
MONTH = 30


def _insert_for(session: AsyncSession):
    """The dialect-specific insert() that supports ON CONFLICT."""
    dialect = session.bind.dialect.name if session.bind is not None else "postgresql"
    return sqlite.insert if dialect == "sqlite" else postgresql.insert


# --- write path -----------------------------------------------------------------


def _content_type(message: Message) -> str:
    ct = message.content_type
    return str(getattr(ct, "value", ct))[:32]


def should_record(message: Message) -> bool:
    if message.ephemeral_message_id:
        return False  # invisible to the chat, not part of its activity
    if message.content_type in SERVICE_CONTENT_TYPES:
        return False
    return True


async def record_message(session: AsyncSession, chat: Chat, message: Message) -> bool:
    """Inserts the event and bumps word counts. Returns False if skipped.
    Redelivered updates are ignored via the (chat, message_id) unique key."""
    if not should_record(message):
        return False

    text = message.text or message.caption or ""
    local_day, local_hour = localize(message.date, chat.timezone)
    from_user = message.from_user
    counts_as_user = from_user is not None and message.sender_chat is None and not from_user.is_bot

    insert = _insert_for(session)
    stmt = (
        insert(MessageEvent)
        .values(
            chat_tg_id=chat.telegram_id,
            user_tg_id=from_user.id if counts_as_user else None,
            sender_chat_tg_id=message.sender_chat.id if message.sender_chat else None,
            message_id=message.message_id,
            sent_at=ensure_aware(message.date),
            local_day=local_day,
            local_hour=local_hour,
            content_type=_content_type(message),
            text_length=len(text),
            is_forward=message.forward_origin is not None,
            is_reply=message.reply_to_message is not None,
        )
        .on_conflict_do_nothing(index_elements=["chat_tg_id", "message_id"])
    )
    result = await session.execute(stmt)
    if result.rowcount == 0:
        await session.rollback()
        return False

    words = tokenize(text)
    if words:
        await _upsert_words(session, chat.telegram_id, local_day, words)
    await session.commit()
    return True


async def _upsert_words(
    session: AsyncSession, chat_tg_id: int, local_day: date, words: Counter[str]
) -> None:
    insert = _insert_for(session)
    stmt = insert(WordStatDaily).values(
        [
            {"chat_tg_id": chat_tg_id, "local_day": local_day, "word": word, "count": n}
            for word, n in words.items()
        ]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["chat_tg_id", "local_day", "word"],
        set_={"count": WordStatDaily.count + stmt.excluded.count},
    )
    await session.execute(stmt)


# --- read path ------------------------------------------------------------------


@dataclass(frozen=True)
class Overview:
    today: int
    week: int
    month: int
    active_week: int


async def overview(session: AsyncSession, chat_tg_id: int, today: date) -> Overview:
    week_from = today - timedelta(days=WEEK - 1)
    month_from = today - timedelta(days=MONTH - 1)
    row = (
        await session.execute(
            select(
                func.coalesce(func.sum(case((MessageEvent.local_day == today, 1), else_=0)), 0),
                func.coalesce(func.sum(case((MessageEvent.local_day >= week_from, 1), else_=0)), 0),
                func.count(),
                func.count(
                    func.distinct(
                        case((MessageEvent.local_day >= week_from, MessageEvent.user_tg_id))
                    )
                ),
            ).where(MessageEvent.chat_tg_id == chat_tg_id, MessageEvent.local_day >= month_from)
        )
    ).one()
    return Overview(today=int(row[0]), week=int(row[1]), month=int(row[2]), active_week=int(row[3]))


async def top_users(
    session: AsyncSession, chat_tg_id: int, day_from: date, day_to: date, limit: int = 5
) -> list[tuple[int, int]]:
    """[(user_tg_id, messages)] most active first."""
    result = await session.execute(
        select(MessageEvent.user_tg_id, func.count().label("n"))
        .where(
            MessageEvent.chat_tg_id == chat_tg_id,
            MessageEvent.user_tg_id.is_not(None),
            MessageEvent.local_day >= day_from,
            MessageEvent.local_day <= day_to,
        )
        .group_by(MessageEvent.user_tg_id)
        .order_by(func.count().desc(), MessageEvent.user_tg_id)
        .limit(limit)
    )
    return [(int(uid), int(n)) for uid, n in result]


async def top_words(
    session: AsyncSession, chat_tg_id: int, day_from: date, day_to: date, limit: int = 10
) -> list[tuple[str, int]]:
    result = await session.execute(
        select(WordStatDaily.word, func.sum(WordStatDaily.count).label("n"))
        .where(
            WordStatDaily.chat_tg_id == chat_tg_id,
            WordStatDaily.local_day >= day_from,
            WordStatDaily.local_day <= day_to,
        )
        .group_by(WordStatDaily.word)
        .order_by(func.sum(WordStatDaily.count).desc(), WordStatDaily.word)
        .limit(limit)
    )
    return [(word, int(n)) for word, n in result]


async def activity_by_hour(
    session: AsyncSession, chat_tg_id: int, day_from: date, day_to: date
) -> list[int]:
    """24 message counts, index = local hour."""
    result = await session.execute(
        select(MessageEvent.local_hour, func.count())
        .where(
            MessageEvent.chat_tg_id == chat_tg_id,
            MessageEvent.local_day >= day_from,
            MessageEvent.local_day <= day_to,
        )
        .group_by(MessageEvent.local_hour)
    )
    slots = [0] * 24
    for hour, n in result:
        slots[int(hour)] = int(n)
    return slots


@dataclass(frozen=True)
class UserStats:
    today: int
    week: int
    month: int
    # 1-based place among users active this week; None if no messages.
    rank_week: int | None
    active_week: int


async def user_stats(
    session: AsyncSession, chat_tg_id: int, user_tg_id: int, today: date
) -> UserStats:
    week_from = today - timedelta(days=WEEK - 1)
    month_from = today - timedelta(days=MONTH - 1)
    row = (
        await session.execute(
            select(
                func.coalesce(func.sum(case((MessageEvent.local_day == today, 1), else_=0)), 0),
                func.coalesce(func.sum(case((MessageEvent.local_day >= week_from, 1), else_=0)), 0),
                func.count(),
            ).where(
                MessageEvent.chat_tg_id == chat_tg_id,
                MessageEvent.user_tg_id == user_tg_id,
                MessageEvent.local_day >= month_from,
            )
        )
    ).one()
    today_n, week_n, month_n = int(row[0]), int(row[1]), int(row[2])

    per_user = (
        select(MessageEvent.user_tg_id, func.count().label("n"))
        .where(
            MessageEvent.chat_tg_id == chat_tg_id,
            MessageEvent.user_tg_id.is_not(None),
            MessageEvent.local_day >= week_from,
        )
        .group_by(MessageEvent.user_tg_id)
        .subquery()
    )
    active_week = int(await session.scalar(select(func.count()).select_from(per_user)) or 0)
    rank = None
    if week_n:
        ahead = await session.scalar(
            select(func.count()).select_from(per_user).where(per_user.c.n > week_n)
        )
        rank = int(ahead or 0) + 1
    return UserStats(
        today=today_n, week=week_n, month=month_n, rank_week=rank, active_week=active_week
    )


# --- retention ----------------------------------------------------------------


async def purge_older_than(
    session: AsyncSession, days: int, batch: int = 10_000
) -> tuple[int, int]:
    """Deletes events/word rows older than `days`. Returns (events, words)."""
    cutoff_dt = datetime.now(UTC) - timedelta(days=days)
    cutoff_day = cutoff_dt.date()
    events = 0
    while True:
        ids = select(MessageEvent.id).where(MessageEvent.sent_at < cutoff_dt).limit(batch)
        result = await session.execute(delete(MessageEvent).where(MessageEvent.id.in_(ids)))
        await session.commit()
        events += result.rowcount
        if result.rowcount < batch:
            break
    result = await session.execute(
        delete(WordStatDaily).where(WordStatDaily.local_day < cutoff_day)
    )
    await session.commit()
    return events, result.rowcount
