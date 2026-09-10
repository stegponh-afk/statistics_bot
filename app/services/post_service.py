"""The registry of everything the bot has published.

Without it a post is fire-and-forget: once `sendMessage` returns, the bot
has no idea what is standing in the channel. One row per published message
(`broadcast_messages`) is what makes «изменить», «удалить» and auto-delete
possible at all, and it is also what ties a broadcast to the reactions its
posts collected.

Auto-delete has two triggers, whichever fires first:

- by time — the scheduler sweeps `delete_at`;
- by reactions — the `message_reaction_count` update does the checking,
  so the post goes as soon as the number is reached.

Post *views* are deliberately absent: the Bot API exposes no views field
and no method to ask for one (verified against aiogram 3.31 / Bot API
10.3), so a bot cannot see them at all. Only an MTProto user session can.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Broadcast, BroadcastMessage, Chat, PostReaction
from app.services.broadcast_service import Content

logger = logging.getLogger(__name__)

# Telegram refuses editMessage* on a post that no longer exists and on one
# whose text is identical; neither is worth reporting as a failure.
_NOT_MODIFIED = "message is not modified"


@dataclass(frozen=True)
class PostStats:
    published: int  # still standing
    deleted: int
    reactions: int


@dataclass
class BulkResult:
    done: int = 0
    failed: int = 0


# --- write path -----------------------------------------------------------


async def record(
    session: AsyncSession,
    chat: Chat,
    message_id: int,
    content: Content,
    *,
    broadcast_id: int | None = None,
    at: datetime | None = None,
) -> BroadcastMessage:
    """Remembers one published post and arms its auto-delete triggers."""
    at = at or datetime.now(UTC)
    row = BroadcastMessage(
        chat_tg_id=chat.telegram_id,
        message_id=message_id,
        broadcast_id=broadcast_id,
        posted_at=at,
        delete_at=(
            at + timedelta(minutes=content.autodelete_after) if content.autodelete_after else None
        ),
        delete_after_reactions=content.autodelete_reactions,
    )
    await session.merge(row)
    await session.commit()
    return row


async def _disarm(session: AsyncSession, row: BroadcastMessage) -> None:
    """A trigger Telegram will never let us honour is switched off rather
    than retried every minute — and the post stays listed as published,
    because it is."""
    row.delete_at = None
    row.delete_after_reactions = None
    await session.commit()


async def delete_post(bot: Bot, session: AsyncSession, row: BroadcastMessage) -> bool:
    try:
        await bot.delete_message(row.chat_tg_id, row.message_id)
    except TelegramRetryAfter:
        return False  # a flood wait is temporary: try again next sweep
    except (TelegramBadRequest, TelegramForbiddenError, TelegramNotFound) as e:
        logger.info("auto-delete of %s/%s refused: %s", row.chat_tg_id, row.message_id, e)
        await _disarm(session, row)
        return False
    row.deleted_at = datetime.now(UTC)
    row.delete_at = None
    row.delete_after_reactions = None
    await session.commit()
    return True


async def delete_due(bot: Bot, session: AsyncSession, now: datetime | None = None) -> int:
    """Posts whose time has come. Called by the scheduler."""
    now = now or datetime.now(UTC)
    rows = list(
        await session.scalars(
            select(BroadcastMessage)
            .where(
                BroadcastMessage.deleted_at.is_(None),
                BroadcastMessage.delete_at.is_not(None),
                BroadcastMessage.delete_at <= now,
            )
            .limit(200)
        )
    )
    return sum([await delete_post(bot, session, row) for row in rows])


async def on_reactions(bot: Bot, session: AsyncSession, chat_tg_id: int, message_id: int) -> bool:
    """Called on every message_reaction_count update: deletes the post if
    it was set to go once it collected enough reactions."""
    row = await session.get(BroadcastMessage, {"chat_tg_id": chat_tg_id, "message_id": message_id})
    if row is None or row.deleted_at is not None or not row.delete_after_reactions:
        return False
    total = await session.scalar(
        select(PostReaction.total).where(
            PostReaction.chat_tg_id == chat_tg_id, PostReaction.message_id == message_id
        )
    )
    if (total or 0) < row.delete_after_reactions:
        return False
    return await delete_post(bot, session, row)


# --- a published broadcast ------------------------------------------------


async def messages_of(
    session: AsyncSession, broadcast_id: int, *, standing_only: bool = True
) -> list[BroadcastMessage]:
    query = select(BroadcastMessage).where(BroadcastMessage.broadcast_id == broadcast_id)
    if standing_only:
        query = query.where(BroadcastMessage.deleted_at.is_(None))
    return list(await session.scalars(query.order_by(BroadcastMessage.posted_at)))


async def stats(session: AsyncSession, broadcast_id: int) -> PostStats:
    published, deleted = (
        await session.execute(
            select(
                func.count().filter(BroadcastMessage.deleted_at.is_(None)),
                func.count().filter(BroadcastMessage.deleted_at.is_not(None)),
            )
            .select_from(BroadcastMessage)
            .where(BroadcastMessage.broadcast_id == broadcast_id)
        )
    ).one()
    reactions = await session.scalar(
        select(func.coalesce(func.sum(PostReaction.total), 0))
        .select_from(BroadcastMessage)
        .join(
            PostReaction,
            (PostReaction.chat_tg_id == BroadcastMessage.chat_tg_id)
            & (PostReaction.message_id == BroadcastMessage.message_id),
        )
        .where(BroadcastMessage.broadcast_id == broadcast_id)
    )
    return PostStats(published=published, deleted=deleted, reactions=int(reactions or 0))


async def edit_all(
    bot: Bot, session: AsyncSession, broadcast: Broadcast, content: Content
) -> BulkResult:
    """Rewrites every standing copy of the broadcast. Media itself cannot
    be swapped through editMessage*, so for a media post this replaces the
    caption and leaves the file alone."""
    result = BulkResult()
    for row in await messages_of(session, broadcast.id):
        try:
            if content.is_media:
                await bot.edit_message_caption(
                    chat_id=row.chat_tg_id,
                    message_id=row.message_id,
                    caption=content.text,
                    caption_entities=content.message_entities(),
                    parse_mode=content.parse_mode,
                    reply_markup=content.reply_markup(),
                )
            else:
                await bot.edit_message_text(
                    chat_id=row.chat_tg_id,
                    message_id=row.message_id,
                    text=content.text or "",
                    entities=content.message_entities(),
                    parse_mode=content.parse_mode,
                    reply_markup=content.reply_markup(),
                )
            result.done += 1
        except TelegramBadRequest as e:
            if _NOT_MODIFIED in str(e):
                result.done += 1
                continue
            logger.info("edit of %s/%s failed: %s", row.chat_tg_id, row.message_id, e)
            result.failed += 1
        except (TelegramForbiddenError, TelegramNotFound) as e:
            logger.info("edit of %s/%s failed: %s", row.chat_tg_id, row.message_id, e)
            result.failed += 1
    return result


async def delete_all(bot: Bot, session: AsyncSession, broadcast: Broadcast) -> BulkResult:
    result = BulkResult()
    for row in await messages_of(session, broadcast.id):
        if await delete_post(bot, session, row):
            result.done += 1
        else:
            result.failed += 1
    return result
