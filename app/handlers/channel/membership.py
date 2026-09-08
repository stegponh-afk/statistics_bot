"""Channels: the bot being added as an admin (which is what makes
getChatMember possible there), and subscribers coming/going — the latter
feeds the force-sub cache directly so a fresh subscription is seen at once."""

import logging

from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import User
from app.filters.chat_type import CHANNEL
from app.services import chat_service
from app.services.subscription_checker import member_cache_key
from config import settings

logger = logging.getLogger(__name__)

router = Router(name="channel_membership")
router.my_chat_member.filter(CHANNEL)
router.chat_member.filter(CHANNEL)

SUBSCRIBED_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


@router.my_chat_member()
async def on_bot_channel_membership_changed(
    event: ChatMemberUpdated, session: AsyncSession, user: User | None, cache: Cache
) -> None:
    chat = await chat_service.upsert_chat(session, event.chat, added_by=user)
    await chat_service.apply_bot_membership(session, chat, event.new_chat_member)
    logger.info(
        "bot in channel %s (%s): %s",
        event.chat.id,
        event.chat.title,
        event.new_chat_member.status,
    )
    if chat.is_active:
        await chat_service.sync_admins(event.bot, session, chat, cache)
        await chat_service.resolve_invite_link(event.bot, session, chat)


@router.chat_member()
async def on_subscriber_changed(event: ChatMemberUpdated, cache: Cache) -> None:
    member = event.new_chat_member
    subscribed = member.status in SUBSCRIBED_STATUSES or (
        member.status == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", False)
    )
    await cache.set(
        member_cache_key(event.chat.id, member.user.id),
        "1" if subscribed else "0",
        ttl=settings.forcesub_cache_ttl_seconds,
    )


@router.channel_post()
async def on_channel_post(post: Message) -> None:
    # Logging happens in StatsLogMiddleware; a handler must exist so
    # channel_post stays in the polled update types.
    return None
