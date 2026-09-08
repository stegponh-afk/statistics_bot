"""Sending a broadcast: to chats from this bot, and to the audience of the
owner's own bot from *that* bot (its token). file_ids are bot-specific, so
media going out through another bot is downloaded once and re-uploaded on
the first send; the file_id that comes back is reused for the rest."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
)
from aiogram.types import BufferedInputFile, Message
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ApiKey, BotAudience, Broadcast, Chat
from app.services import broadcast_service
from app.services.broadcast_service import Content

logger = logging.getLogger(__name__)

# Between sends to individual users from one bot (Telegram allows ~30/s).
PER_USER_DELAY = 0.05

BotFactory = Callable[[str], Bot]


def default_bot_factory(token: str) -> Bot:
    return Bot(token=token)


@dataclass
class RunResult:
    sent: int = 0
    failed: int = 0
    blocked: int = 0


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


def _sent_file_id(message: Message, kind: str) -> str | None:
    if kind == "photo":
        return message.photo[-1].file_id if message.photo else None
    obj = getattr(message, kind, None)
    return obj.file_id if obj is not None else None


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


async def _download_media(bot: Bot, content: Content) -> BufferedInputFile | None:
    if not content.is_media or not content.file_id:
        return None
    buffer = await bot.download(content.file_id)
    if buffer is None:
        return None
    return BufferedInputFile(buffer.read(), filename=f"media.{content.type}")


async def deliver_to_bot_audience(
    session: AsyncSession,
    our_bot: Bot,
    key: ApiKey,
    content: Content,
    *,
    bot_factory: BotFactory = default_bot_factory,
) -> RunResult:
    result = RunResult()
    if not key.bot_token:
        return result
    users = list(
        await session.scalars(
            select(BotAudience.user_tg_id).where(
                BotAudience.api_key_id == key.id, BotAudience.is_blocked.is_(False)
            )
        )
    )
    if not users:
        return result

    their_bot = bot_factory(key.bot_token)
    media = None
    if content.is_media:
        try:
            media = await _download_media(our_bot, content)
        except (TelegramBadRequest, TelegramNotFound) as e:
            logger.warning("broadcast %s: media download failed: %s", key.id, e)
            result.failed = len(users)
            return result
    reusable_file_id: str | None = None
    blocked: list[int] = []
    try:
        for user_id in users:
            try:
                sent = await _send_with_retry(
                    their_bot, user_id, content, reusable_file_id or media
                )
                result.sent += 1
                if content.is_media and reusable_file_id is None:
                    reusable_file_id = _sent_file_id(sent, content.type)
            except TelegramForbiddenError:
                result.blocked += 1
                blocked.append(user_id)
            except (TelegramBadRequest, TelegramNotFound) as e:
                logger.info("broadcast via bot %s to %s failed: %s", key.id, user_id, e)
                result.failed += 1
            await asyncio.sleep(PER_USER_DELAY)
    finally:
        close = getattr(getattr(their_bot, "session", None), "close", None)
        if close is not None:
            await close()

    if blocked:
        await session.execute(
            update(BotAudience)
            .where(BotAudience.api_key_id == key.id, BotAudience.user_tg_id.in_(blocked))
            .values(is_blocked=True)
        )
        await session.commit()
    return result


async def run_broadcast(
    session: AsyncSession,
    bot: Bot,
    broadcast: Broadcast,
    *,
    bot_factory: BotFactory = default_bot_factory,
) -> RunResult:
    """Sends one broadcast to all its targets and records the outcome."""
    content = Content.from_json(broadcast.content)
    chats, keys = await broadcast_service.targets(session, broadcast)
    total = RunResult()

    chat_result = await deliver_to_chats(bot, chats, content)
    total.sent += chat_result.sent
    total.failed += chat_result.failed
    for key in keys:
        r = await deliver_to_bot_audience(session, bot, key, content, bot_factory=bot_factory)
        total.sent += r.sent
        total.failed += r.failed
        total.blocked += r.blocked

    broadcast.sent_count += total.sent
    broadcast.failed_count += total.failed + total.blocked
    broadcast_service.advance_after_run(broadcast, datetime.now(UTC))
    await session.commit()
    logger.info(
        "broadcast %s run: sent=%d failed=%d blocked=%d",
        broadcast.id,
        total.sent,
        total.failed,
        total.blocked,
    )
    return total
