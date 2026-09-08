"""Turning comments off for one channel post.

Telegram has no per-post switch: comments exist because a discussion group
is attached, and the «Комментарии» button on a post points at the copy
Telegram auto-forwards into that group. Delete the copy and the button is
gone, while the discussion group stays attached for every other post.

The copy and our own post arrive from two directions, and either can be
first — the bot may still be finishing sendMessage when the auto-forward
update lands. So both sides leave a note in the cache and whoever comes
second does the deleting.
"""

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message, MessageOriginChannel

from app.cache import Cache
from app.database.models import Chat

logger = logging.getLogger(__name__)

# Long enough to cover a slow auto-forward, short enough that the keys for
# ordinary posts (every one of which leaves a note) cost nothing.
RENDEZVOUS_TTL = 600


def pending_key(channel_tg_id: int, message_id: int) -> str:
    """«This post must lose its comments» — left by the publisher."""
    return f"nocmt:{channel_tg_id}:{message_id}"


def seen_key(channel_tg_id: int, message_id: int) -> str:
    """«The copy of this post is group message N» — left by the handler."""
    return f"fwd:{channel_tg_id}:{message_id}"


def origin_of(message: Message) -> tuple[int, int] | None:
    """(channel id, post id) a discussion-group copy came from."""
    origin = message.forward_origin
    if isinstance(origin, MessageOriginChannel):
        return origin.chat.id, origin.message_id
    if message.forward_from_chat is not None and message.forward_from_message_id is not None:
        return message.forward_from_chat.id, message.forward_from_message_id
    return None


async def _delete(bot: Bot, chat_id: int, message_id: int) -> bool:
    try:
        await bot.delete_message(chat_id, message_id)
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.info("comments: can't delete %s/%s: %s", chat_id, message_id, e)
        return False


async def suppress(bot: Bot, cache: Cache, channel: Chat, message_id: int) -> bool:
    """Called right after publishing a post that must have no comments.
    True if the copy was already there and is gone now."""
    key = seen_key(channel.telegram_id, message_id)
    seen = await cache.get(key)
    if seen is not None:
        await cache.delete(key)
        group_id, group_message_id = seen.split(":")
        return await _delete(bot, int(group_id), int(group_message_id))
    await cache.set(pending_key(channel.telegram_id, message_id), "1", RENDEZVOUS_TTL)
    return False


async def on_auto_forward(bot: Bot, cache: Cache, message: Message) -> bool:
    """A channel post has just been copied into its discussion group.
    True if that copy was removed."""
    origin = origin_of(message)
    if origin is None:
        return False
    channel_tg_id, post_id = origin
    key = pending_key(channel_tg_id, post_id)
    if await cache.get(key) is not None:
        await cache.delete(key)
        return await _delete(bot, message.chat.id, message.message_id)
    await cache.set(
        seen_key(channel_tg_id, post_id),
        f"{message.chat.id}:{message.message_id}",
        RENDEZVOUS_TTL,
    )
    return False
