"""The bot's own membership in groups (my_chat_member) and admin changes
among members (chat_member) — keeps chats/chat_admins in step."""

import logging

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import ChatMemberUpdatedFilter
from aiogram.filters.chat_member_updated import ADMINISTRATOR, IS_MEMBER, IS_NOT_MEMBER, MEMBER
from aiogram.types import ChatMemberUpdated, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import User
from app.filters.chat_type import GROUP
from app.services import chat_service

logger = logging.getLogger(__name__)

router = Router(name="group_membership")
router.my_chat_member.filter(GROUP)
router.chat_member.filter(GROUP)


@router.my_chat_member()
async def on_bot_membership_changed(
    event: ChatMemberUpdated, session: AsyncSession, user: User | None, cache: Cache
) -> None:
    chat = await chat_service.upsert_chat(session, event.chat, added_by=user)
    await chat_service.apply_bot_membership(session, chat, event.new_chat_member)
    logger.info("bot in %s (%s): %s", event.chat.id, event.chat.title, event.new_chat_member.status)
    if chat.is_active:
        if user is not None:
            await chat_service.remember_admin(session, cache, chat, user)
        await chat_service.sync_admins(event.bot, session, chat, cache, retries=1)
    else:
        await chat_service.invalidate_admin_cache(cache, chat.telegram_id)


@router.chat_member(ChatMemberUpdatedFilter((IS_NOT_MEMBER | MEMBER) >> ADMINISTRATOR))
@router.chat_member(ChatMemberUpdatedFilter(ADMINISTRATOR >> (IS_NOT_MEMBER | MEMBER)))
async def on_member_admin_changed(
    event: ChatMemberUpdated, session: AsyncSession, cache: Cache
) -> None:
    chat = await chat_service.get_chat_by_telegram_id(session, event.chat.id)
    if chat is None:
        chat = await chat_service.upsert_chat(session, event.chat)
    await chat_service.sync_admins(event.bot, session, chat, cache)


@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_member_joined_or_left(event: ChatMemberUpdated, session: AsyncSession) -> None:
    # Keep the cached member count roughly honest between hourly refreshes.
    chat = await chat_service.get_chat_by_telegram_id(session, event.chat.id)
    if chat is None or chat.member_count is None:
        return
    delta = (
        1
        if event.new_chat_member.status
        in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        )
        else -1
    )
    chat.member_count = max(0, chat.member_count + delta)
    await session.commit()


@router.message(F.migrate_to_chat_id)
async def on_migrate(message: Message, session: AsyncSession, cache: Cache) -> None:
    await chat_service.migrate_chat_id(session, message.chat.id, message.migrate_to_chat_id)
    await chat_service.invalidate_admin_cache(cache, message.chat.id)
