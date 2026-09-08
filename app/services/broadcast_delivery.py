"""Sending a broadcast to the chats (groups and channels) this bot is in,
with the per-post options the admin chose on the preview screen."""

import asyncio
import html
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
)
from aiogram.types import EphemeralMessageParameters, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import Broadcast, Chat, User
from app.services import broadcast_service, channel_stats, comment_control
from app.services.broadcast_service import Content

logger = logging.getLogger(__name__)

DEFAULT_AD_LABEL = "#реклама"
# Telegram's own caps; a post that overruns them is refused outright, so the
# label is dropped rather than the post.
TEXT_LIMIT = 4096
CAPTION_LIMIT = 1024


@dataclass
class RunResult:
    sent: int = 0
    failed: int = 0


def ad_label_of(user: User | None) -> str:
    return (user.ad_label if user and user.ad_label else DEFAULT_AD_LABEL).strip()


def with_ad_label(content: Content, label: str) -> Content:
    """Appends the ad label. Appending is safe for text the admin formatted
    in Telegram: entity offsets all point before the added tail, so nothing
    shifts."""
    if not content.is_ad or not label:
        return content
    text = content.text or ""
    tail = f"\n\n{html.escape(label) if content.parse_mode == 'HTML' else label}"
    limit = CAPTION_LIMIT if content.is_media else TEXT_LIMIT
    if len(text) + len(tail) > limit:
        logger.info("ad label dropped: the post is already at the length limit")
        return content
    return replace(content, text=text + tail)


async def send_content(
    bot: Bot,
    chat_id: int,
    content: Content,
    media=None,
    *,
    ephemeral: EphemeralMessageParameters | None = None,
    thread_id: int | None = None,
) -> Message:
    """Re-sends a stored message (broadcast, reward, welcome). With
    `ephemeral` it goes out visible to that one user only."""
    # parse_mode is passed explicitly either way: our own bot defaults to
    # HTML, which must not apply to text that carries entities.
    kwargs = dict(
        reply_markup=content.reply_markup(),
        parse_mode=content.parse_mode,
        ephemeral_message_parameters=ephemeral,
        message_thread_id=thread_id,
        disable_notification=content.silent or None,
        protect_content=content.protect or None,
    )
    if content.type == "text":
        return await bot.send_message(
            chat_id, content.text or "", entities=content.message_entities(), **kwargs
        )
    caption = dict(caption=content.text, caption_entities=content.message_entities())
    method = {
        "photo": bot.send_photo,
        "video": bot.send_video,
        "animation": bot.send_animation,
        "document": bot.send_document,
        "audio": bot.send_audio,
        "voice": bot.send_voice,
    }[content.type]
    return await method(chat_id, media, **caption, **kwargs)


async def _send_with_retry(bot: Bot, chat_id: int, content: Content, media) -> Message:
    for _ in range(3):
        try:
            return await send_content(bot, chat_id, content, media)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
    return await send_content(bot, chat_id, content, media)


async def _after_publish(
    bot: Bot,
    session: AsyncSession,
    cache: Cache | None,
    chat: Chat,
    content: Content,
    message: Message,
    broadcast_id: int | None,
) -> None:
    """Everything that can only happen once the post has an id. None of it
    may undo a successful publication, so each step swallows its own
    failure."""
    if content.pin:
        try:
            await bot.pin_chat_message(
                chat.telegram_id, message.message_id, disable_notification=True
            )
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.info("can't pin in %s: %s", chat.telegram_id, e)
    if not content.comments and chat.is_channel and cache is not None:
        await comment_control.suppress(bot, cache, chat, message.message_id)
    if content.is_ad:
        await channel_stats.record_ad_post(
            session, chat, message.message_id, broadcast_id=broadcast_id
        )


async def publish(
    bot: Bot,
    session: AsyncSession,
    cache: Cache | None,
    chat: Chat,
    content: Content,
    *,
    ad_label: str = DEFAULT_AD_LABEL,
    broadcast_id: int | None = None,
) -> Message:
    """One post, with the label, the pin, the comment switch and the ad
    bookkeeping applied."""
    body = with_ad_label(content, ad_label)
    message = await _send_with_retry(bot, chat.telegram_id, body, body.file_id)
    await _after_publish(bot, session, cache, chat, content, message, broadcast_id)
    return message


async def deliver_to_chats(
    bot: Bot,
    session: AsyncSession,
    cache: Cache | None,
    chats: list[Chat],
    content: Content,
    *,
    ad_label: str = DEFAULT_AD_LABEL,
    broadcast_id: int | None = None,
) -> RunResult:
    result = RunResult()
    for chat in chats:
        if not chat.is_active:
            result.failed += 1
            continue
        try:
            await publish(
                bot,
                session,
                cache,
                chat,
                content,
                ad_label=ad_label,
                broadcast_id=broadcast_id,
            )
            result.sent += 1
        except (TelegramBadRequest, TelegramForbiddenError, TelegramNotFound) as e:
            logger.info("broadcast to chat %s failed: %s", chat.telegram_id, e)
            result.failed += 1
    return result


async def run_broadcast(
    session: AsyncSession, bot: Bot, broadcast: Broadcast, cache: Cache | None = None
) -> RunResult:
    """Sends one broadcast to all its chats and records the outcome."""
    content = Content.from_json(broadcast.content)
    chats = await broadcast_service.targets(session, broadcast)
    owner = await session.get(User, broadcast.owner_user_id)
    result = await deliver_to_chats(
        bot,
        session,
        cache,
        chats,
        content,
        ad_label=ad_label_of(owner),
        broadcast_id=broadcast.id,
    )
    broadcast.sent_count += result.sent
    broadcast.failed_count += result.failed
    broadcast_service.advance_after_run(broadcast, datetime.now(UTC))
    await session.commit()
    logger.info("broadcast %s run: sent=%d failed=%d", broadcast.id, result.sent, result.failed)
    return result
