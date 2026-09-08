"""The copy Telegram drops into a discussion group whenever the channel
posts. It is the thing the «Комментарии» button on the post points at, so
removing it is how a single post ends up without comments."""

import logging

from aiogram import F, Router
from aiogram.types import Message

from app.cache import Cache
from app.services import comment_control

logger = logging.getLogger(__name__)

router = Router(name="auto_forward")


@router.message(F.is_automatic_forward)
async def on_auto_forward(message: Message, cache: Cache) -> None:
    if await comment_control.on_auto_forward(message.bot, cache, message):
        logger.info("comments removed from post in %s", message.chat.id)
