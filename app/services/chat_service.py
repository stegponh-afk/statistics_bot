"""Chats the bot lives in, and who administers them.

Admin lists are learned from getChatAdministrators — on my_chat_member
(bot added/promoted), lazily when stale, from the «Обновить» button and a
daily job — and mirrored into chat_admins so «Мои чаты» is a plain join.
The set of admin telegram ids per chat is additionally cached (Redis set,
ADMIN_SYNC_TTL) so the per-message gate never touches the database.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Chat as TgChat
from aiogram.types import ChatMember, ChatMemberAdministrator, ChatMemberOwner
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import AdminStatus, BotStatus, Chat, ChatAdmin, ChatKind, User
from app.services.user_service import upsert_user_stub
from config import settings

logger = logging.getLogger(__name__)

MEMBER_COUNT_TTL = timedelta(hours=1)
# Telegram's service accounts: messages "from" these are anonymous admins
# (GroupAnonymousBot) and linked-channel posts (Telegram).
ANONYMOUS_ADMIN_BOT_ID = 1087968824
TELEGRAM_SERVICE_ID = 777000

_CHAT_KINDS = {
    ChatType.GROUP: ChatKind.GROUP,
    ChatType.SUPERGROUP: ChatKind.SUPERGROUP,
    ChatType.CHANNEL: ChatKind.CHANNEL,
}


def admin_cache_key(chat_tg_id: int) -> str:
    return f"admins:{chat_tg_id}"


def is_trackable_chat(tg_chat: TgChat) -> bool:
    return tg_chat.type in _CHAT_KINDS


async def get_chat_by_telegram_id(session: AsyncSession, telegram_id: int) -> Chat | None:
    return await session.scalar(select(Chat).where(Chat.telegram_id == telegram_id))


async def get_chat(session: AsyncSession, chat_id: int) -> Chat | None:
    return await session.get(Chat, chat_id)


async def upsert_chat(
    session: AsyncSession, tg_chat: TgChat, *, added_by: User | None = None
) -> Chat:
    """Creates or refreshes (title/username/type) the row for a group,
    supergroup or channel. Commits."""
    chat = await get_chat_by_telegram_id(session, tg_chat.id)
    kind = _CHAT_KINDS[tg_chat.type]
    if chat is None:
        chat = Chat(
            telegram_id=tg_chat.id,
            type=kind,
            title=tg_chat.title,
            username=tg_chat.username,
            added_by_user_id=added_by.id if added_by else None,
        )
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
        return chat

    changed = False
    for attr, value in (("title", tg_chat.title), ("username", tg_chat.username), ("type", kind)):
        if getattr(chat, attr) != value:
            setattr(chat, attr, value)
            changed = True
    if added_by and chat.added_by_user_id is None:
        chat.added_by_user_id = added_by.id
        changed = True
    if changed:
        await session.commit()
    return chat


async def migrate_chat_id(session: AsyncSession, old_tg_id: int, new_tg_id: int) -> None:
    """group -> supergroup: Telegram assigns a new chat id."""
    chat = await get_chat_by_telegram_id(session, old_tg_id)
    if chat is None:
        return
    existing = await get_chat_by_telegram_id(session, new_tg_id)
    if existing is not None:
        # Both ids seen already (e.g. the supergroup announced itself first):
        # keep the newer row, drop the stale one.
        await session.delete(chat)
    else:
        chat.telegram_id = new_tg_id
        chat.type = ChatKind.SUPERGROUP
    await session.commit()


def bot_membership_fields(member: ChatMember) -> dict:
    """Which chats.bot_* columns a my_chat_member update sets."""
    status = member.status
    if isinstance(member, ChatMemberAdministrator):
        return {
            "bot_status": BotStatus.ADMINISTRATOR,
            "bot_can_delete": bool(member.can_delete_messages),
            "bot_can_invite": bool(member.can_invite_users),
            "bot_can_restrict": bool(member.can_restrict_members),
        }
    if status == ChatMemberStatus.MEMBER or (
        status == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", False)
    ):
        return _no_rights(BotStatus.MEMBER)
    if status == ChatMemberStatus.KICKED:
        return _no_rights(BotStatus.KICKED)
    return _no_rights(BotStatus.LEFT)


def _no_rights(status: BotStatus) -> dict:
    return {
        "bot_status": status,
        "bot_can_delete": False,
        "bot_can_invite": False,
        "bot_can_restrict": False,
    }


async def apply_bot_membership(session: AsyncSession, chat: Chat, member: ChatMember) -> Chat:
    for attr, value in bot_membership_fields(member).items():
        setattr(chat, attr, value)
    if not chat.bot_can_delete:
        # The gate deletes messages; without that right (or in the chat at
        # all) it can't work — don't leave it "on".
        chat.forcesub_enabled = False
    if not chat.bot_can_restrict:
        # Same for the captcha, which mutes the newcomer it challenges.
        chat.captcha_enabled = False
    await session.commit()
    return chat


async def refresh_bot_membership(bot: Bot, session: AsyncSession, chat: Chat) -> Chat:
    """Re-reads the bot's own rights (for chats seen before the bot could
    record its my_chat_member update)."""
    try:
        me = await bot.get_chat_member(chat.telegram_id, bot.id)
    except (TelegramBadRequest, TelegramForbiddenError):
        chat.bot_status = BotStatus.LEFT
        chat.forcesub_enabled = False
        await session.commit()
        return chat
    return await apply_bot_membership(session, chat, me)


# --- admins --------------------------------------------------------------


async def sync_admins(
    bot: Bot,
    session: AsyncSession,
    chat: Chat,
    cache: Cache | None = None,
    *,
    retries: int = 0,
    retry_delay: float = 2.0,
) -> list[ChatAdmin]:
    """getChatAdministrators -> users + chat_admins. Returns the new rows;
    on API failure keeps what's there and returns it.

    Right after the bot is promoted Telegram can still answer "member list
    is inaccessible" for a moment — callers reacting to my_chat_member pass
    retries=1 so a second attempt happens after retry_delay seconds."""
    members = None
    for attempt in range(retries + 1):
        try:
            members = await bot.get_chat_administrators(chat.telegram_id)
            break
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.info("sync_admins(%s) attempt %d failed: %s", chat.telegram_id, attempt + 1, e)
            if attempt < retries:
                await asyncio.sleep(retry_delay)
    if members is None:
        return list(await session.scalars(select(ChatAdmin).where(ChatAdmin.chat_id == chat.id)))

    rows: list[ChatAdmin] = []
    for m in members:
        if m.user.is_bot:
            continue
        user = await upsert_user_stub(session, m.user.id, m.user.username, m.user.full_name)
        status = (
            AdminStatus.CREATOR if isinstance(m, ChatMemberOwner) else AdminStatus.ADMINISTRATOR
        )
        is_anonymous = bool(getattr(m, "is_anonymous", False))
        rows.append(
            ChatAdmin(chat_id=chat.id, user_id=user.id, status=status, is_anonymous=is_anonymous)
        )

    await session.execute(delete(ChatAdmin).where(ChatAdmin.chat_id == chat.id))
    session.add_all(rows)
    chat.admins_synced_at = datetime.now(UTC)
    await session.commit()
    logger.info("sync_admins(%s): %d admins", chat.telegram_id, len(rows))

    if cache is not None:
        await invalidate_admin_cache(cache, chat.telegram_id)
    return rows


async def remember_admin(
    session: AsyncSession, cache: Cache | None, chat: Chat, user: User
) -> None:
    """Records `user` as an admin of `chat` without asking Telegram — for
    whoever added/promoted the bot (only admins can), so the chat reaches
    their «Мои чаты» even while getChatAdministrators is refused."""
    if await session.get(ChatAdmin, {"chat_id": chat.id, "user_id": user.id}) is None:
        session.add(ChatAdmin(chat_id=chat.id, user_id=user.id, status=AdminStatus.ADMINISTRATOR))
        await session.commit()
        if cache is not None:
            await invalidate_admin_cache(cache, chat.telegram_id)


def admins_stale(chat: Chat, now: datetime | None = None) -> bool:
    if chat.admins_synced_at is None:
        return True
    now = now or datetime.now(UTC)
    synced = chat.admins_synced_at
    if synced.tzinfo is None:
        synced = synced.replace(tzinfo=UTC)
    return now - synced > timedelta(seconds=settings.admin_sync_ttl_seconds)


async def ensure_admins_synced(
    bot: Bot, session: AsyncSession, chat: Chat, cache: Cache | None = None
) -> None:
    if chat.is_active and admins_stale(chat):
        await sync_admins(bot, session, chat, cache)


async def invalidate_admin_cache(cache: Cache, chat_tg_id: int) -> None:
    await cache.delete(admin_cache_key(chat_tg_id))


async def get_admin_telegram_ids(
    session: AsyncSession, cache: Cache, chat: Chat, bot: Bot | None = None
) -> set[int]:
    """Telegram ids of the chat's admins, from cache, else chat_admins
    (syncing first via `bot` if never synced)."""
    key = admin_cache_key(chat.telegram_id)
    cached = await cache.smembers(key)
    if cached is not None:
        return {int(x) for x in cached}

    if bot is not None and chat.admins_synced_at is None:
        await sync_admins(bot, session, chat)

    result = await session.execute(
        select(User.telegram_id)
        .join(ChatAdmin, ChatAdmin.user_id == User.id)
        .where(ChatAdmin.chat_id == chat.id)
    )
    ids = {row[0] for row in result}
    await cache.sadd(key, *(str(i) for i in ids), ttl=settings.admin_sync_ttl_seconds)
    return ids


async def list_admin_chats(session: AsyncSession, user: User) -> list[Chat]:
    """Chats where `user` is an admin and the bot is still present."""
    result = await session.scalars(
        select(Chat)
        .join(ChatAdmin, ChatAdmin.chat_id == Chat.id)
        .where(
            ChatAdmin.user_id == user.id,
            Chat.bot_status.in_([BotStatus.MEMBER, BotStatus.ADMINISTRATOR]),
        )
        .order_by(Chat.type, Chat.title)
    )
    return list(result)


async def user_administers(session: AsyncSession, user: User, chat: Chat) -> bool:
    row = await session.get(ChatAdmin, {"chat_id": chat.id, "user_id": user.id})
    return row is not None


async def list_admin_channels(session: AsyncSession, user: User) -> list[Chat]:
    """Channels where `user` is an admin and the bot is an admin (only then
    can getChatMember be called on them)."""
    return [
        c
        for c in await list_admin_chats(session, user)
        if c.is_channel and c.bot_status == BotStatus.ADMINISTRATOR
    ]


async def notify_admins_started(
    bot: Bot, session: AsyncSession, chat: Chat, text: str, *, exclude: set[int] = frozenset()
) -> None:
    """DMs every admin of the chat who has started the bot."""
    result = await session.scalars(
        select(User)
        .join(ChatAdmin, ChatAdmin.user_id == User.id)
        .where(ChatAdmin.chat_id == chat.id, User.started_bot.is_(True))
    )
    for user in result:
        if user.telegram_id in exclude:
            continue
        try:
            await bot.send_message(user.telegram_id, text)
        except (TelegramBadRequest, TelegramForbiddenError):
            pass


# --- misc chat facts ------------------------------------------------------


async def get_member_count(bot: Bot, session: AsyncSession, chat: Chat) -> int | None:
    updated = chat.member_count_updated_at
    if updated is not None and updated.tzinfo is None:
        updated = updated.replace(tzinfo=UTC)
    if (
        chat.member_count is not None
        and updated is not None
        and datetime.now(UTC) - updated < MEMBER_COUNT_TTL
    ):
        return chat.member_count
    try:
        count = await bot.get_chat_member_count(chat.telegram_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return chat.member_count
    chat.member_count = count
    chat.member_count_updated_at = datetime.now(UTC)
    await session.commit()
    from app.services import channel_stats  # local: channel_stats imports models only

    await channel_stats.snapshot_member_count(session, chat, count)
    return count


async def resolve_linked_group(
    bot: Bot, session: AsyncSession, channel: Chat, *, refresh: bool = False
) -> Chat | None:
    """The channel's discussion group (where comments live) as a Chat row —
    only if the bot is in that group; None if the channel has no
    discussion group or the bot hasn't been added to it."""
    if refresh or channel.linked_chat_tg_id is None:
        try:
            info = await bot.get_chat(channel.telegram_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            return None
        if info.linked_chat_id != channel.linked_chat_tg_id:
            channel.linked_chat_tg_id = info.linked_chat_id
            await session.commit()
    if channel.linked_chat_tg_id is None:
        return None
    group = await get_chat_by_telegram_id(session, channel.linked_chat_tg_id)
    if group is None or not group.is_active:
        return None
    return group


async def resolve_invite_link(bot: Bot, session: AsyncSession, chat: Chat) -> str | None:
    """A link users can follow to join/subscribe: t.me/username for public
    chats, else a cached/exported invite link (needs "invite users")."""
    if chat.username:
        return f"https://t.me/{chat.username}"
    if chat.invite_link:
        return chat.invite_link
    try:
        tg_chat = await bot.get_chat(chat.telegram_id)
        link = tg_chat.invite_link
        if not link and chat.bot_can_invite:
            link = await bot.export_chat_invite_link(chat.telegram_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        link = None
    if link:
        chat.invite_link = link
        await session.commit()
    return link


def chat_kind_label(chat: Chat) -> str:
    return "канал" if chat.is_channel else "группа"
