"""«Награда за подписку»: a channel admin stores a message (text, media,
buttons) that this bot hands to anyone who proves they're subscribed —
via the deep link t.me/<bot>?start=sub_<slug>. No third-party bot, no
code on the admin's side."""

import secrets
from datetime import UTC, datetime

from aiogram import Bot
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, RewardClaim
from app.services.broadcast_service import Content

DEEP_LINK_PREFIX = "sub_"


def _new_slug() -> str:
    return secrets.token_urlsafe(6).replace("-", "a").replace("_", "b")[:8]


async def ensure_slug(session: AsyncSession, channel: Chat) -> str:
    if not channel.reward_slug:
        channel.reward_slug = _new_slug()
        await session.commit()
    return channel.reward_slug


async def set_reward(session: AsyncSession, channel: Chat, content: Content) -> None:
    channel.reward_content = content.to_json()
    await ensure_slug(session, channel)
    await session.commit()


async def clear_reward(session: AsyncSession, channel: Chat) -> None:
    channel.reward_content = None
    await session.commit()


def reward_of(channel: Chat) -> Content | None:
    return Content.from_json(channel.reward_content) if channel.reward_content else None


async def channel_by_slug(session: AsyncSession, slug: str) -> Chat | None:
    if not slug:
        return None
    return await session.scalar(select(Chat).where(Chat.reward_slug == slug))


async def claim(session: AsyncSession, channel: Chat, user_tg_id: int) -> RewardClaim | None:
    """Records that the user received the reward now. Returns the earlier
    claim (and records nothing) if they already had it."""
    existing = await session.get(RewardClaim, {"chat_id": channel.id, "user_tg_id": user_tg_id})
    if existing is not None:
        return existing
    session.add(
        RewardClaim(chat_id=channel.id, user_tg_id=user_tg_id, claimed_at=datetime.now(UTC))
    )
    await session.commit()
    return None


async def claims_count(session: AsyncSession, channel: Chat) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(RewardClaim).where(RewardClaim.chat_id == channel.id)
        )
        or 0
    )


async def reset_claims(session: AsyncSession, channel: Chat) -> None:
    for row in await session.scalars(select(RewardClaim).where(RewardClaim.chat_id == channel.id)):
        await session.delete(row)
    await session.commit()


async def deep_link(bot: Bot, channel: Chat) -> str:
    me = await bot.me()
    return f"https://t.me/{me.username}?start={DEEP_LINK_PREFIX}{channel.reward_slug}"


def slug_from_start_arg(arg: str | None) -> str | None:
    if arg and arg.startswith(DEEP_LINK_PREFIX):
        return arg[len(DEEP_LINK_PREFIX) :]
    return None
