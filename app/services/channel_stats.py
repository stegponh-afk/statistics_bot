"""What a channel admin can actually learn through the Bot API:
subscriber joins/leaves (chat_member updates), the subscriber count over
time (snapshots), posts per day (message_events) and anonymous reaction
totals per post (message_reaction_count updates). Post views are not
exposed to bots at all."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from aiogram.types import MessageReactionCountUpdated
from sqlalchemy import case, func, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    AdPost,
    Chat,
    MemberEvent,
    MemberSnapshot,
    MessageEvent,
    PostReaction,
)
from app.services import stats_service
from app.utils import ensure_aware, localize

JOIN = "join"
LEAVE = "leave"


def _insert_for(session: AsyncSession):
    dialect = session.bind.dialect.name if session.bind is not None else "postgresql"
    return sqlite.insert if dialect == "sqlite" else postgresql.insert


# --- write path -----------------------------------------------------------------


async def record_member_event(
    session: AsyncSession, chat: Chat, user_tg_id: int, kind: str, at: datetime | None = None
) -> None:
    at = at or datetime.now(UTC)
    local_day, _ = localize(at, chat.timezone)
    session.add(
        MemberEvent(
            chat_tg_id=chat.telegram_id,
            user_tg_id=user_tg_id,
            kind=kind,
            at=at,
            local_day=local_day,
        )
    )
    await session.commit()


async def snapshot_member_count(
    session: AsyncSession, chat: Chat, count: int, at: datetime | None = None
) -> None:
    """Today's subscriber count (last write of the day wins)."""
    local_day, _ = localize(at or datetime.now(UTC), chat.timezone)
    insert = _insert_for(session)
    stmt = insert(MemberSnapshot).values(
        chat_tg_id=chat.telegram_id, local_day=local_day, member_count=count
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["chat_tg_id", "local_day"], set_={"member_count": count}
    )
    await session.execute(stmt)
    await session.commit()


async def record_ad_post(
    session: AsyncSession,
    chat: Chat,
    message_id: int,
    *,
    broadcast_id: int | None = None,
    at: datetime | None = None,
) -> None:
    at = at or datetime.now(UTC)
    local_day, _ = localize(at, chat.timezone)
    insert = _insert_for(session)
    stmt = insert(AdPost).values(
        chat_tg_id=chat.telegram_id,
        message_id=message_id,
        posted_at=at,
        local_day=local_day,
        broadcast_id=broadcast_id,
    )
    await session.execute(stmt.on_conflict_do_nothing(index_elements=["chat_tg_id", "message_id"]))
    await session.commit()


async def record_reactions(session: AsyncSession, update: MessageReactionCountUpdated) -> None:
    total = sum(r.total_count for r in update.reactions)
    insert = _insert_for(session)
    stmt = insert(PostReaction).values(
        chat_tg_id=update.chat.id,
        message_id=update.message_id,
        total=total,
        updated_at=datetime.now(UTC),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["chat_tg_id", "message_id"],
        set_={"total": total, "updated_at": datetime.now(UTC)},
    )
    await session.execute(stmt)
    await session.commit()


# --- read path ---------------------------------------------------------------------


@dataclass(frozen=True)
class DayFlow:
    joins: int
    leaves: int

    @property
    def net(self) -> int:
        return self.joins - self.leaves


async def flow(session: AsyncSession, chat_tg_id: int, day_from: date, day_to: date) -> DayFlow:
    row = (
        await session.execute(
            select(
                func.coalesce(func.sum(case((MemberEvent.kind == JOIN, 1), else_=0)), 0),
                func.coalesce(func.sum(case((MemberEvent.kind == LEAVE, 1), else_=0)), 0),
            ).where(
                MemberEvent.chat_tg_id == chat_tg_id,
                MemberEvent.local_day >= day_from,
                MemberEvent.local_day <= day_to,
            )
        )
    ).one()
    return DayFlow(int(row[0]), int(row[1]))


async def count_on_or_before(session: AsyncSession, chat_tg_id: int, day: date) -> int | None:
    """The latest snapshot taken on `day` or earlier."""
    return await session.scalar(
        select(MemberSnapshot.member_count)
        .where(MemberSnapshot.chat_tg_id == chat_tg_id, MemberSnapshot.local_day <= day)
        .order_by(MemberSnapshot.local_day.desc())
        .limit(1)
    )


async def posts_count(session: AsyncSession, chat_tg_id: int, day_from: date, day_to: date) -> int:
    return await stats_service.messages_count(session, chat_tg_id, day_from, day_to)


@dataclass(frozen=True)
class ReactionStats:
    posts_with_reactions: int
    average: float
    best_message_id: int | None
    best_total: int


async def reactions(
    session: AsyncSession, chat_tg_id: int, day_from: date, day_to: date
) -> ReactionStats:
    """Reaction totals over posts published in the window (posts without
    any reaction count as 0 in the average)."""
    posts = await posts_count(session, chat_tg_id, day_from, day_to)
    rows = (
        await session.execute(
            select(PostReaction.message_id, PostReaction.total)
            .join(
                MessageEvent,
                (MessageEvent.chat_tg_id == PostReaction.chat_tg_id)
                & (MessageEvent.message_id == PostReaction.message_id),
            )
            .where(
                PostReaction.chat_tg_id == chat_tg_id,
                MessageEvent.local_day >= day_from,
                MessageEvent.local_day <= day_to,
            )
            .order_by(PostReaction.total.desc(), PostReaction.message_id.desc())
        )
    ).all()
    total = sum(int(t) for _, t in rows)
    best = rows[0] if rows else (None, 0)
    return ReactionStats(
        posts_with_reactions=len(rows),
        average=(total / posts) if posts else 0.0,
        best_message_id=int(best[0]) if best[0] is not None else None,
        best_total=int(best[1]),
    )


async def top_posts(
    session: AsyncSession, chat_tg_id: int, day_from: date, day_to: date, limit: int = 10
) -> list[tuple[int, int, date]]:
    """[(message_id, reactions, local_day)] best first."""
    rows = (
        await session.execute(
            select(PostReaction.message_id, PostReaction.total, MessageEvent.local_day)
            .join(
                MessageEvent,
                (MessageEvent.chat_tg_id == PostReaction.chat_tg_id)
                & (MessageEvent.message_id == PostReaction.message_id),
            )
            .where(
                PostReaction.chat_tg_id == chat_tg_id,
                MessageEvent.local_day >= day_from,
                MessageEvent.local_day <= day_to,
            )
            .order_by(PostReaction.total.desc(), PostReaction.message_id.desc())
            .limit(limit)
        )
    ).all()
    return [(int(m), int(t), d) for m, t, d in rows]


@dataclass(frozen=True)
class DayRow:
    day: date
    subscribers: int | None
    joins: int
    leaves: int
    posts: int


async def daily_rows(
    session: AsyncSession, chat_tg_id: int, today: date, days: int = 14
) -> list[DayRow]:
    day_from = today - timedelta(days=days - 1)
    snapshots = dict(
        (
            await session.execute(
                select(MemberSnapshot.local_day, MemberSnapshot.member_count).where(
                    MemberSnapshot.chat_tg_id == chat_tg_id, MemberSnapshot.local_day >= day_from
                )
            )
        ).all()
    )
    flows: dict[date, list[int]] = {}
    for day, kind, n in (
        await session.execute(
            select(MemberEvent.local_day, MemberEvent.kind, func.count())
            .where(MemberEvent.chat_tg_id == chat_tg_id, MemberEvent.local_day >= day_from)
            .group_by(MemberEvent.local_day, MemberEvent.kind)
        )
    ).all():
        flows.setdefault(day, [0, 0])[0 if kind == JOIN else 1] += int(n)
    posts = dict(
        (
            await session.execute(
                select(MessageEvent.local_day, func.count())
                .where(MessageEvent.chat_tg_id == chat_tg_id, MessageEvent.local_day >= day_from)
                .group_by(MessageEvent.local_day)
            )
        ).all()
    )
    out = []
    for i in range(days):
        day = day_from + timedelta(days=i)
        j, l_ = flows.get(day, [0, 0])
        out.append(DayRow(day, snapshots.get(day), j, l_, int(posts.get(day, 0))))
    return out


@dataclass(frozen=True)
class AdSummary:
    posts: int
    avg_reactions: float
    avg_reactions_other: float
    # Subscribers who left within LEAVE_WINDOW of an ad going out. Not
    # proof of cause, but it is the number an admin selling ads wants.
    leaves_after: int


LEAVE_WINDOW = timedelta(days=1)


async def ad_summary(
    session: AsyncSession, chat_tg_id: int, day_from: date, day_to: date
) -> AdSummary:
    ads = (
        await session.execute(
            select(AdPost.message_id, AdPost.posted_at).where(
                AdPost.chat_tg_id == chat_tg_id,
                AdPost.local_day >= day_from,
                AdPost.local_day <= day_to,
            )
        )
    ).all()
    if not ads:
        return AdSummary(0, 0.0, 0.0, 0)
    ad_ids = {int(m) for m, _ in ads}

    totals = dict(
        (
            await session.execute(
                select(PostReaction.message_id, PostReaction.total)
                .join(
                    MessageEvent,
                    (MessageEvent.chat_tg_id == PostReaction.chat_tg_id)
                    & (MessageEvent.message_id == PostReaction.message_id),
                )
                .where(
                    PostReaction.chat_tg_id == chat_tg_id,
                    MessageEvent.local_day >= day_from,
                    MessageEvent.local_day <= day_to,
                )
            )
        ).all()
    )
    posts_total = await posts_count(session, chat_tg_id, day_from, day_to)
    ad_reactions = sum(int(t) for m, t in totals.items() if int(m) in ad_ids)
    other_reactions = sum(int(t) for m, t in totals.items() if int(m) not in ad_ids)
    others = max(0, posts_total - len(ad_ids))

    leaves = 0
    for _, posted_at in ads:
        start = ensure_aware(posted_at)
        leaves += int(
            await session.scalar(
                select(func.count()).where(
                    MemberEvent.chat_tg_id == chat_tg_id,
                    MemberEvent.kind == LEAVE,
                    MemberEvent.at >= start,
                    MemberEvent.at <= start + LEAVE_WINDOW,
                )
            )
            or 0
        )
    return AdSummary(
        posts=len(ad_ids),
        avg_reactions=ad_reactions / len(ad_ids),
        avg_reactions_other=(other_reactions / others) if others else 0.0,
        leaves_after=leaves,
    )


def post_link(chat: Chat, message_id: int) -> str:
    if chat.username:
        return f"https://t.me/{chat.username}/{message_id}"
    internal = str(chat.telegram_id)
    if internal.startswith("-100"):
        internal = internal[4:]
    return f"https://t.me/c/{internal}/{message_id}"


def growth_label(now: int | None, before: int | None) -> str:
    """'+12 (▲0.8%)' / '−3 (▼0.2%)' / '—' when unknown."""
    if now is None or before is None:
        return "—"
    delta = now - before
    if before <= 0:
        return f"{delta:+d}"
    pct = delta / before * 100
    arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "＝")
    return f"{delta:+d} ({arrow}{abs(pct):.1f}%)"
