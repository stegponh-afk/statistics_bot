"""The audience of an owner's bot: user ids seen through the API."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ApiKey, BotAudience

MAX_BATCH = 10_000


async def record_users(session: AsyncSession, key: ApiKey, user_ids: list[int]) -> int:
    """Upserts the ids into the key's audience. Returns how many were given
    (after de-duplication)."""
    ids = list({int(u) for u in user_ids})[:MAX_BATCH]
    if not ids:
        return 0
    dialect = session.bind.dialect.name if session.bind is not None else "postgresql"
    insert = sqlite.insert if dialect == "sqlite" else postgresql.insert
    now = datetime.now(UTC)
    stmt = insert(BotAudience).values(
        [{"api_key_id": key.id, "user_tg_id": uid, "last_seen_at": now} for uid in ids]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["api_key_id", "user_tg_id"], set_={"last_seen_at": now}
    )
    await session.execute(stmt)
    await session.commit()
    return len(ids)


async def audience_size(session: AsyncSession, key: ApiKey) -> tuple[int, int]:
    """(reachable, blocked)."""
    row = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(func.cast(BotAudience.is_blocked, sqlite.INTEGER)), 0),
            ).where(BotAudience.api_key_id == key.id)
        )
    ).one()
    total, blocked = int(row[0]), int(row[1])
    return total - blocked, blocked
