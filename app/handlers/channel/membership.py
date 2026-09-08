"""Channels: the bot being added as an admin (which is what makes
getChatMember possible there), and subscribers coming/going — the latter
feeds the force-sub cache directly so a fresh subscription is seen at once."""

import logging

from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated, Message, MessageReactionCountUpdated
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import Chat, User
from app.filters.chat_type import CHANNEL
from app.services import channel_stats, chat_service
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
        if user is not None:
            await chat_service.remember_admin(session, cache, chat, user)
        await chat_service.sync_admins(event.bot, session, chat, cache, retries=1)
        await chat_service.resolve_invite_link(event.bot, session, chat)


def _is_in(member) -> bool:
    return member.status in SUBSCRIBED_STATUSES or (
        member.status == ChatMemberStatus.RESTRICTED and bool(getattr(member, "is_member", False))
    )


@router.chat_member()
async def on_subscriber_changed(
    event: ChatMemberUpdated, session: AsyncSession, cache: Cache, chat_row: Chat | None
) -> None:
    member = event.new_chat_member
    subscribed = _is_in(member)
    await cache.set(
        member_cache_key(event.chat.id, member.user.id),
        "1" if subscribed else "0",
        ttl=settings.forcesub_cache_ttl_seconds,
    )
    was_in = _is_in(event.old_chat_member)
    if chat_row is not None and was_in != subscribed and not member.user.is_bot:
        await channel_stats.record_member_event(
            session,
            chat_row,
            member.user.id,
            channel_stats.JOIN if subscribed else channel_stats.LEAVE,
            event.date,
        )
        if chat_row.member_count is not None:
            chat_row.member_count = max(0, chat_row.member_count + (1 if subscribed else -1))
            await session.commit()


@router.message_reaction_count()
async def on_reaction_count(event: MessageReactionCountUpdated, session: AsyncSession) -> None:
    await channel_stats.record_reactions(session, event)


@router.channel_post()
async def on_channel_post(post: Message) -> None:
    # Logging happens in StatsLogMiddleware; a handler must exist so
    # channel_post stays in the polled update types.
    return None
