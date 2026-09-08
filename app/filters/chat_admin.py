from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject


class IsChatAdmin(BaseFilter):
    """Passes when ChatContextMiddleware determined the sender administers
    the chat the event came from."""

    async def __call__(self, event: TelegramObject, is_chat_admin: bool = False) -> bool:
        return is_chat_admin
