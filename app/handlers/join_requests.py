"""Incoming «заявки на вступление» for groups and channels alike."""

import logging

from aiogram import Router
from aiogram.types import ChatJoinRequest
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import Chat
from app.services import join_request_service

logger = logging.getLogger(__name__)

router = Router(name="join_requests")


@router.chat_join_request()
async def on_join_request(
    event: ChatJoinRequest,
    session: AsyncSession,
    cache: Cache,
    chat_row: Chat | None,
    is_chat_admin: bool,
) -> None:
    if chat_row is None:
        return
    approved = await join_request_service.handle_request(
        event.bot,
        session,
        cache,
        chat_row,
        event.from_user.id,
        event.user_chat_id,
        is_chat_admin=is_chat_admin,
    )
    logger.info(
        "join request %s -> %s: %s",
        event.from_user.id,
        event.chat.id,
        "approved" if approved else "held",
    )
