"""«Награда за подписку»: a channel admin stores a message (text, media,
buttons) that this bot hands to anyone who proves they're subscribed —
via the deep link t.me/<bot>?start=sub_<slug>. No third-party bot, no
code on the admin's side."""

import secrets

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat
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


async def deep_link(bot: Bot, channel: Chat) -> str:
    me = await bot.me()
    return f"https://t.me/{me.username}?start={DEEP_LINK_PREFIX}{channel.reward_slug}"


def slug_from_start_arg(arg: str | None) -> str | None:
    if arg and arg.startswith(DEEP_LINK_PREFIX):
        return arg[len(DEEP_LINK_PREFIX) :]
    return None
