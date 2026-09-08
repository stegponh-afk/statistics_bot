"""Force-sub gate: an outer middleware on group messages. When the chat
requires channel subscriptions and the sender lacks one, the message is
deleted and the sender gets an ephemeral prompt — and the update goes no
further (it is neither logged nor handled)."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import Chat, User
from app.screens.gate import gate_prompt_screen
from app.services import chat_service, forcesub_service
from app.services.subscription_checker import check_user
from app.texts import ru
from app.ui import send_ephemeral
from config import settings

logger = logging.getLogger(__name__)

LOST_RIGHTS_NOTIFY_TTL = 3600


def prompt_cooldown_key(chat_tg_id: int, user_id: int) -> str:
    return f"gate:p:{chat_tg_id}:{user_id}"


class ForceSubGateMiddleware(BaseMiddleware):
    def __init__(self, cache: Cache) -> None:
        self.cache = cache

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        chat_row: Chat | None = data.get("chat_row")
        if (
            not isinstance(event, Message)
            or chat_row is None
            or chat_row.is_channel
            or not chat_row.forcesub_enabled
            or event.from_user is None
        ):
            return await handler(event, data)

        session: AsyncSession = data["session"]
        bot: Bot = data["bot"]

        channel_ids = await forcesub_service.required_channel_tg_ids(session, self.cache, chat_row)
        if not channel_ids:
            return await handler(event, data)

        whitelist = await forcesub_service.whitelist_ids(session, self.cache, chat_row)
        if forcesub_service.is_exempt(
            event, is_chat_admin=bool(data.get("is_chat_admin")), whitelist_ids=whitelist
        ):
            return await handler(event, data)

        channels = await forcesub_service.list_required_channels(session, chat_row)
        result = await check_user(bot, self.cache, event.from_user.id, channels)
        if result.subscribed:
            return await handler(event, data)

        if not event.ephemeral_message_id:
            try:
                await event.delete()
            except (TelegramBadRequest, TelegramForbiddenError) as e:
                logger.warning("gate: can't delete in %s (%s), disabling", chat_row.telegram_id, e)
                await self._lost_rights(bot, session, chat_row)
                return await handler(event, data)

        if await self.cache.set_if_absent(
            prompt_cooldown_key(chat_row.telegram_id, event.from_user.id),
            "1",
            settings.forcesub_prompt_cooldown_seconds,
        ):
            user: User | None = data.get("user")
            screen = await gate_prompt_screen(bot, session, chat_row, result.missing)
            await send_ephemeral(
                bot,
                chat_row.telegram_id,
                event.from_user.id,
                screen,
                rich_buttons=user.rich_buttons_enabled if user else True,
                thread_id=event.message_thread_id,
            )
        return None  # swallowed: not logged, not handled

    async def _lost_rights(self, bot: Bot, session: AsyncSession, chat: Chat) -> None:
        chat.bot_can_delete = False
        chat.forcesub_enabled = False
        await session.commit()
        if await self.cache.set_if_absent(
            f"notify:lostrights:{chat.telegram_id}", "1", LOST_RIGHTS_NOTIFY_TTL
        ):
            await chat_service.notify_admins_started(
                bot,
                session,
                chat,
                ru.GATE_LOST_RIGHTS_DM.format(title=chat.title or chat.telegram_id),
            )
