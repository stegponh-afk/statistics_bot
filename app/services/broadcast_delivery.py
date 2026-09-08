"""Sending a broadcast to the chats (groups and channels) this bot is in."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
)
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Broadcast, Chat
from app.services import broadcast_service
from app.services.broadcast_service import Content

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    sent: int = 0
    failed: int = 0


async def _send(bot: Bot, chat_id: int, content: Content, media) -> Message:
    # parse_mode is passed explicitly either way: our own bot defaults to
    # HTML, which must not apply to text that carries entities.
    kwargs = dict(reply_markup=content.reply_markup(), parse_mode=content.parse_mode)
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
            return await _send(bot, chat_id, content, media)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
    return await _send(bot, chat_id, content, media)


async def deliver_to_chats(bot: Bot, chats: list[Chat], content: Content) -> RunResult:
    result = RunResult()
    for chat in chats:
        if not chat.is_active:
            result.failed += 1
            continue
        try:
            await _send_with_retry(bot, chat.telegram_id, content, content.file_id)
            result.sent += 1
        except (TelegramBadRequest, TelegramForbiddenError, TelegramNotFound) as e:
            logger.info("broadcast to chat %s failed: %s", chat.telegram_id, e)
            result.failed += 1
    return result


async def run_broadcast(session: AsyncSession, bot: Bot, broadcast: Broadcast) -> RunResult:
    """Sends one broadcast to all its chats and records the outcome."""
    content = Content.from_json(broadcast.content)
    chats = await broadcast_service.targets(session, broadcast)
    result = await deliver_to_chats(bot, chats, content)
    broadcast.sent_count += result.sent
    broadcast.failed_count += result.failed
    broadcast_service.advance_after_run(broadcast, datetime.now(UTC))
    await session.commit()
    logger.info("broadcast %s run: sent=%d failed=%d", broadcast.id, result.sent, result.failed)
    return result
