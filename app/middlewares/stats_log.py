"""Records every group message / channel post for statistics, then lets
the event continue to whatever handler (if any) wants it. A logging
failure is logged and never blocks handling."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.services import stats_service

logger = logging.getLogger(__name__)


class StatsLogMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        chat_row = data.get("chat_row")
        if isinstance(event, Message) and chat_row is not None and chat_row.stats_enabled:
            try:
                await stats_service.record_message(data["session"], chat_row, event)
            except Exception:  # noqa: BLE001
                logger.exception("failed to record message %s/%s", event.chat.id, event.message_id)
        return await handler(event, data)
