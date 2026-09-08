"""Puts the per-update context every handler needs into `data`:

- cache          — the shared Cache
- user           — the sender's User row (upserted; None for bots/service)
- chat_row       — the Chat row for group/supergroup/channel events
- is_ephemeral   — the incoming message is an ephemeral command
- is_chat_admin  — the sender administers chat_row (anonymous admins count)
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, TelegramObject, Update
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.services import chat_service
from app.services.user_service import get_user_by_telegram_id, upsert_user

# How long a user's/chat's name is trusted before it's re-checked against
# the update — spares one UPDATE per message in busy groups.
SEEN_TTL = 3600


class ChatContextMiddleware(BaseMiddleware):
    def __init__(self, cache: Cache) -> None:
        self.cache = cache

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data["session"]
        bot: Bot = data["bot"]
        data["cache"] = self.cache

        from_user = data.get("event_from_user")
        tg_chat = data.get("event_chat")
        inner = event.event if isinstance(event, Update) else event
        message = inner if isinstance(inner, Message) else None

        data["user"] = None
        if from_user is not None and not from_user.is_bot:
            if await self.cache.set_if_absent(f"seen:u:{from_user.id}", "1", SEEN_TTL):
                data["user"] = await upsert_user(session, from_user)
            else:
                data["user"] = await get_user_by_telegram_id(
                    session, from_user.id
                ) or await upsert_user(session, from_user)

        data["chat_row"] = None
        if tg_chat is not None and chat_service.is_trackable_chat(tg_chat):
            chat_row = await chat_service.get_chat_by_telegram_id(session, tg_chat.id)
            if chat_row is None or await self.cache.set_if_absent(
                f"seen:c:{tg_chat.id}", "1", SEEN_TTL
            ):
                chat_row = await chat_service.upsert_chat(session, tg_chat)
            data["chat_row"] = chat_row

        data["is_ephemeral"] = bool(message is not None and message.ephemeral_message_id)

        data["is_chat_admin"] = False
        chat_row = data["chat_row"]
        if chat_row is not None and not chat_row.is_channel and from_user is not None:
            if message is not None and message.sender_chat and message.sender_chat.id == tg_chat.id:
                data["is_chat_admin"] = True  # anonymous admin posting as the group
            elif not from_user.is_bot:
                admin_ids = await chat_service.get_admin_telegram_ids(
                    session, self.cache, chat_row, bot
                )
                data["is_chat_admin"] = from_user.id in admin_ids

        return await handler(event, data)
