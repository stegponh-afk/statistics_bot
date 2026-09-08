"""Is user X subscribed to channels A, B, C? — with a short cache so the
group gate and the HTTP API don't call getChatMember for every message."""

import asyncio
import logging
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

from app.cache import Cache
from app.database.models import Chat
from config import settings

logger = logging.getLogger(__name__)

_SUBSCRIBED = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}
_CONCURRENCY = asyncio.Semaphore(5)

REASON_BOT_NOT_ADMIN = "bot_not_admin"
REASON_RATE_LIMITED = "rate_limited"


def member_cache_key(channel_tg_id: int, user_id: int) -> str:
    return f"fs:{channel_tg_id}:{user_id}"


@dataclass
class CheckResult:
    subscribed: bool
    missing: list[Chat] = field(default_factory=list)
    # (channel, reason) pairs the check could not be performed for; they do
    # not count against the user (fail-open).
    unavailable: list[tuple[Chat, str]] = field(default_factory=list)
    cached: bool = True


async def _check_one(
    bot: Bot, cache: Cache, user_id: int, channel: Chat, *, force: bool
) -> tuple[bool | None, str | None, bool]:
    """(subscribed | None if unknown, reason if unknown, from_cache)."""
    key = member_cache_key(channel.telegram_id, user_id)
    if not force:
        cached = await cache.get(key)
        if cached is not None:
            return cached == "1", None, True

    async with _CONCURRENCY:
        try:
            member = await bot.get_chat_member(channel.telegram_id, user_id)
        except TelegramRetryAfter as e:
            logger.warning("getChatMember rate limited for %s s", e.retry_after)
            return None, REASON_RATE_LIMITED, False
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            text = str(e).lower()
            if "user not found" in text or "participant_id_invalid" in text:
                subscribed = False
            else:
                # "member list is inaccessible", "chat not found",
                # CHAT_ADMIN_REQUIRED, ... — the bot can't look, so don't
                # punish the user for it.
                logger.info("getChatMember(%s, %s) failed: %s", channel.telegram_id, user_id, e)
                return None, REASON_BOT_NOT_ADMIN, False
        else:
            subscribed = member.status in _SUBSCRIBED or (
                member.status == ChatMemberStatus.RESTRICTED
                and bool(getattr(member, "is_member", False))
            )

    await cache.set(key, "1" if subscribed else "0", ttl=settings.forcesub_cache_ttl_seconds)
    return subscribed, None, False


async def check_user(
    bot: Bot, cache: Cache, user_id: int, channels: list[Chat], *, force: bool = False
) -> CheckResult:
    if not channels:
        return CheckResult(subscribed=True)

    results = await asyncio.gather(
        *(_check_one(bot, cache, user_id, ch, force=force) for ch in channels)
    )
    out = CheckResult(subscribed=True)
    for channel, (subscribed, reason, from_cache) in zip(channels, results, strict=True):
        if not from_cache:
            out.cached = False
        if subscribed is None:
            out.unavailable.append((channel, reason or REASON_BOT_NOT_ADMIN))
        elif not subscribed:
            out.missing.append(channel)
    out.subscribed = not out.missing
    return out
