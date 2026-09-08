"""End-to-end routing through a real aiogram Dispatcher with the project's
routers and middlewares (DB session swapped for the sqlite fixture)."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from aiogram import BaseMiddleware, Dispatcher
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ChatMemberAdministrator,
    ChatMemberLeft,
    ChatMemberOwner,
    TelegramObject,
    Update,
)
from sqlalchemy import select

from app.database.models import BotStatus, Chat, ChatAdmin
from app.handlers import build_router
from app.middlewares.context import ChatContextMiddleware
from tests.fakes import FakeBot, make_message, tg_user

CHANNEL = -100_31
ADMIN_ID = 1


# The project's routers are module-level singletons and can be attached to
# one Dispatcher per process, so the dispatcher is built once and the
# per-test session/cache are swapped in through this holder.
_STATE: dict[str, Any] = {}


class SessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["session"] = _STATE["session"]
        return await handler(event, data)


class CacheProxy:
    def __getattr__(self, name: str):
        return getattr(_STATE["cache"], name)


def _admin_member(user_id: int, *, is_bot: bool = False) -> ChatMemberAdministrator:
    rights = {
        name: False
        for name in (
            "can_be_edited",
            "is_anonymous",
            "can_manage_chat",
            "can_delete_messages",
            "can_manage_video_chats",
            "can_restrict_members",
            "can_promote_members",
            "can_change_info",
            "can_invite_users",
            "can_post_stories",
            "can_edit_stories",
            "can_delete_stories",
            "can_send_welcome_messages",
        )
    }
    return ChatMemberAdministrator(user=tg_user(user_id, "X", is_bot=is_bot), **rights)


_DISPATCHER: Dispatcher | None = None


def _dispatcher(session, cache) -> Dispatcher:
    global _DISPATCHER
    _STATE["session"] = session
    _STATE["cache"] = cache
    if _DISPATCHER is None:
        proxy = CacheProxy()
        _DISPATCHER = Dispatcher(storage=MemoryStorage())
        _DISPATCHER.update.outer_middleware(SessionMiddleware())
        _DISPATCHER.update.outer_middleware(ChatContextMiddleware(proxy))
        _DISPATCHER.include_router(build_router(proxy))
    return _DISPATCHER


async def test_bot_added_to_channel_lands_in_my_chats(session, cache, bot: FakeBot):
    bot.administrators[CHANNEL] = [
        ChatMemberOwner(user=tg_user(ADMIN_ID, "Owner"), is_anonymous=False),
        _admin_member(bot.id, is_bot=True),
    ]
    dp = _dispatcher(session, cache)
    update = Update.model_validate(
        {
            "update_id": 1,
            "my_chat_member": {
                "chat": {"id": CHANNEL, "type": "channel", "title": "News"},
                "from": tg_user(ADMIN_ID, "Owner").model_dump(),
                "date": int(datetime.now(UTC).timestamp()),
                "old_chat_member": ChatMemberLeft(
                    user=tg_user(bot.id, "Bot", is_bot=True)
                ).model_dump(),
                "new_chat_member": _admin_member(bot.id, is_bot=True).model_dump(),
            },
        },
        context={"bot": bot},
    )
    result = await dp.feed_update(bot, update)
    assert result is not UNHANDLED

    chat = await session.scalar(select(Chat).where(Chat.telegram_id == CHANNEL))
    assert chat is not None and chat.bot_status == BotStatus.ADMINISTRATOR
    admins = list(await session.scalars(select(ChatAdmin).where(ChatAdmin.chat_id == chat.id)))
    assert len(admins) == 1


async def test_channel_post_is_recorded_and_discovers_the_chat(session, cache, bot: FakeBot):
    bot.members[(CHANNEL, bot.id)] = _admin_member(bot.id, is_bot=True)
    bot.administrators[CHANNEL] = [ChatMemberOwner(user=tg_user(ADMIN_ID), is_anonymous=False)]
    dp = _dispatcher(session, cache)
    post = make_message(
        chat_id=CHANNEL, chat_type="channel", user_id=None, text="hello world", bot=bot
    )
    update = Update.model_validate(
        {"update_id": 2, "channel_post": post.model_dump(exclude_none=True)}, context={"bot": bot}
    )
    await dp.feed_update(bot, update)

    from app.database.models import MessageEvent

    assert await session.scalar(select(MessageEvent)) is not None
    chat = await session.scalar(select(Chat).where(Chat.telegram_id == CHANNEL))
    assert chat.bot_status == BotStatus.ADMINISTRATOR
    assert (await session.scalar(select(ChatAdmin).where(ChatAdmin.chat_id == chat.id))) is not None
