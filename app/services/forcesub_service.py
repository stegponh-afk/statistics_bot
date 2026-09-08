"""Force-sub bindings (which channels a group requires), the whitelist, and
the pure "is this sender exempt from the gate" decision."""

from aiogram.types import Message
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import Chat, ChatWhitelist, GroupRequiredChannel, User
from app.services.chat_service import ANONYMOUS_ADMIN_BOT_ID, TELEGRAM_SERVICE_ID
from config import settings

# Service messages are never gated or deleted.
SERVICE_CONTENT_TYPES = frozenset(
    {
        "new_chat_members",
        "left_chat_member",
        "new_chat_title",
        "new_chat_photo",
        "delete_chat_photo",
        "group_chat_created",
        "supergroup_chat_created",
        "channel_chat_created",
        "migrate_to_chat_id",
        "migrate_from_chat_id",
        "pinned_message",
        "forum_topic_created",
        "forum_topic_edited",
        "forum_topic_closed",
        "forum_topic_reopened",
        "general_forum_topic_hidden",
        "general_forum_topic_unhidden",
        "video_chat_scheduled",
        "video_chat_started",
        "video_chat_ended",
        "video_chat_participants_invited",
        "message_auto_delete_timer_changed",
        "chat_background_set",
        "boost_added",
        "giveaway_created",
        "write_access_allowed",
        "proximity_alert_triggered",
        "chat_shared",
        "users_shared",
        "unknown",
    }
)


def whitelist_cache_key(chat_tg_id: int) -> str:
    return f"wl:{chat_tg_id}"


def channels_cache_key(chat_tg_id: int) -> str:
    return f"fsch:{chat_tg_id}"


def is_exempt(message: Message, *, is_chat_admin: bool, whitelist_ids: set[int]) -> bool:
    """True if the gate must let this message through without checking."""
    if message.content_type in SERVICE_CONTENT_TYPES:
        return True
    if message.from_user is None or message.from_user.is_bot:
        return True
    if message.sender_chat is not None:
        return True  # anonymous admin / channel post on behalf of a chat
    if message.from_user.id in (ANONYMOUS_ADMIN_BOT_ID, TELEGRAM_SERVICE_ID):
        return True
    if is_chat_admin:
        return True
    return message.from_user.id in whitelist_ids


# --- required channels ------------------------------------------------------


async def list_required_channels(session: AsyncSession, chat: Chat) -> list[Chat]:
    result = await session.scalars(
        select(Chat)
        .join(GroupRequiredChannel, GroupRequiredChannel.channel_id == Chat.id)
        .where(GroupRequiredChannel.chat_id == chat.id)
        .order_by(GroupRequiredChannel.position, Chat.id)
    )
    return list(result)


async def required_channel_tg_ids(session: AsyncSession, cache: Cache, chat: Chat) -> list[int]:
    """Telegram ids of the group's required channels, cached."""
    key = channels_cache_key(chat.telegram_id)
    cached = await cache.get(key)
    if cached is not None:
        return [int(x) for x in cached.split(",") if x]
    ids = [c.telegram_id for c in await list_required_channels(session, chat)]
    await cache.set(key, ",".join(str(i) for i in ids), ttl=settings.admin_sync_ttl_seconds)
    return ids


async def toggle_required_channel(
    session: AsyncSession, cache: Cache, chat: Chat, channel: Chat
) -> bool:
    """Adds the binding if absent, removes it if present. Returns the new
    state (True = now required)."""
    row = await session.get(GroupRequiredChannel, {"chat_id": chat.id, "channel_id": channel.id})
    if row is None:
        session.add(GroupRequiredChannel(chat_id=chat.id, channel_id=channel.id))
        now_required = True
    else:
        await session.delete(row)
        now_required = False
    await session.commit()
    await cache.delete(channels_cache_key(chat.telegram_id))
    return now_required


async def set_forcesub_enabled(session: AsyncSession, chat: Chat, enabled: bool) -> Chat:
    chat.forcesub_enabled = enabled
    await session.commit()
    return chat


# --- whitelist ------------------------------------------------------------------


async def list_whitelist(session: AsyncSession, chat: Chat) -> list[ChatWhitelist]:
    result = await session.scalars(
        select(ChatWhitelist)
        .where(ChatWhitelist.chat_id == chat.id)
        .order_by(ChatWhitelist.created_at)
    )
    return list(result)


async def whitelist_ids(session: AsyncSession, cache: Cache, chat: Chat) -> set[int]:
    key = whitelist_cache_key(chat.telegram_id)
    cached = await cache.smembers(key)
    if cached is not None:
        return {int(x) for x in cached}
    ids = {row.user_tg_id for row in await list_whitelist(session, chat)}
    await cache.sadd(key, *(str(i) for i in ids), ttl=settings.admin_sync_ttl_seconds)
    return ids


async def add_to_whitelist(
    session: AsyncSession, cache: Cache, chat: Chat, user_tg_id: int, added_by: User | None
) -> bool:
    if await session.get(ChatWhitelist, {"chat_id": chat.id, "user_tg_id": user_tg_id}):
        return False
    session.add(
        ChatWhitelist(
            chat_id=chat.id,
            user_tg_id=user_tg_id,
            added_by_user_id=added_by.id if added_by else None,
        )
    )
    await session.commit()
    await cache.delete(whitelist_cache_key(chat.telegram_id))
    return True


async def remove_from_whitelist(
    session: AsyncSession, cache: Cache, chat: Chat, user_tg_id: int
) -> None:
    await session.execute(
        delete(ChatWhitelist).where(
            ChatWhitelist.chat_id == chat.id, ChatWhitelist.user_tg_id == user_tg_id
        )
    )
    await session.commit()
    await cache.delete(whitelist_cache_key(chat.telegram_id))
