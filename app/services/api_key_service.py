"""API keys for the force-sub bridge. Only a sha256 of a key is stored;
the raw key is returned exactly once, from create_key / rotate_key."""

import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import ApiKey, ApiKeyChannel, Chat, User

KEY_PREFIX = "sb_"


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_key() -> tuple[str, str, str]:
    """(raw key, sha256 hex, display prefix)."""
    raw = KEY_PREFIX + secrets.token_urlsafe(24)
    return raw, hash_key(raw), raw[:10]


def key_cache_key(key_hash: str) -> str:
    return f"apikey:{key_hash}"


async def create_key(session: AsyncSession, owner: User, name: str) -> tuple[ApiKey, str]:
    raw, digest, prefix = generate_key()
    key = ApiKey(
        owner_user_id=owner.id, name=name[:64], key_hash=digest, key_prefix=prefix, key_raw=raw
    )
    session.add(key)
    await session.commit()
    await session.refresh(key)
    return key, raw


async def list_keys(
    session: AsyncSession, owner: User, *, include_revoked: bool = False
) -> list[ApiKey]:
    stmt = select(ApiKey).where(ApiKey.owner_user_id == owner.id)
    if not include_revoked:
        stmt = stmt.where(ApiKey.is_active.is_(True))
    return list(await session.scalars(stmt.order_by(ApiKey.created_at, ApiKey.id)))


async def get_owned_key(session: AsyncSession, owner: User, key_id: int) -> ApiKey | None:
    key = await session.get(ApiKey, key_id)
    if key is None or key.owner_user_id != owner.id:
        return None
    return key


async def find_active_key(session: AsyncSession, raw: str) -> ApiKey | None:
    if not raw.startswith(KEY_PREFIX):
        return None
    return await session.scalar(
        select(ApiKey).where(ApiKey.key_hash == hash_key(raw), ApiKey.is_active.is_(True))
    )


async def revoke_key(session: AsyncSession, cache: Cache, key: ApiKey) -> None:
    key.is_active = False
    key.revoked_at = datetime.now(UTC)
    await session.commit()
    await cache.delete(key_cache_key(key.key_hash))


async def rotate_key(session: AsyncSession, cache: Cache, key: ApiKey) -> tuple[ApiKey, str]:
    """Replaces the secret of `key` in place — channels stay attached;
    the old secret stops working at once."""
    await cache.delete(key_cache_key(key.key_hash))
    raw, digest, prefix = generate_key()
    key.key_hash = digest
    key.key_prefix = prefix
    key.key_raw = raw
    key.created_at = datetime.now(UTC)
    await session.commit()
    return key, raw


async def delete_key(session: AsyncSession, cache: Cache, key: ApiKey) -> None:
    await cache.delete(key_cache_key(key.key_hash))
    await session.delete(key)
    await session.commit()


async def list_key_channels(session: AsyncSession, key: ApiKey) -> list[Chat]:
    result = await session.scalars(
        select(Chat)
        .join(ApiKeyChannel, ApiKeyChannel.channel_id == Chat.id)
        .where(ApiKeyChannel.api_key_id == key.id)
        .order_by(ApiKeyChannel.position, Chat.id)
    )
    return list(result)


async def toggle_key_channel(session: AsyncSession, key: ApiKey, channel: Chat) -> bool:
    row = await session.get(ApiKeyChannel, {"api_key_id": key.id, "channel_id": channel.id})
    if row is None:
        session.add(ApiKeyChannel(api_key_id=key.id, channel_id=channel.id))
        now_bound = True
    else:
        await session.delete(row)
        now_bound = False
    await session.commit()
    return now_bound


async def clear_key_channels(session: AsyncSession, key: ApiKey) -> None:
    await session.execute(delete(ApiKeyChannel).where(ApiKeyChannel.api_key_id == key.id))
    await session.commit()


async def touch_key(session: AsyncSession, key: ApiKey) -> None:
    """One request happened: bump the counter and last_used_at."""
    await session.execute(
        update(ApiKey)
        .where(ApiKey.id == key.id)
        .values(request_count=ApiKey.request_count + 1, last_used_at=datetime.now(UTC))
    )
    await session.commit()
