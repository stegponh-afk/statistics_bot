import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
)
from aiohttp import web

from app.api.server import create_api_app
from app.cache import RedisCache
from app.database.session import async_session_factory
from app.handlers import build_router
from app.middlewares.context import ChatContextMiddleware
from app.middlewares.db_session import DbSessionMiddleware
from app.redis_client import get_redis
from app.scheduler.jobs import setup_scheduler
from config import settings

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

# Update types the bot must be polled for. Listed explicitly (rather than
# derived from registered handlers) because chat_member is delivered only
# when asked for, and channel_post is consumed by a middleware.
ALLOWED_UPDATES = ["message", "callback_query", "my_chat_member", "chat_member", "channel_post"]


async def setup_commands(bot: Bot) -> None:
    private = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="chats", description="Мои чаты"),
        BotCommand(command="keys", description="API-ключи для ваших ботов"),
        BotCommand(command="help", description="Помощь"),
    ]
    # In groups the answer is visible only to whoever sent the command.
    group = [
        BotCommand(command="me", description="Моя активность в чате", is_ephemeral=True),
        BotCommand(command="help", description="Помощь", is_ephemeral=True),
    ]
    admins = [
        BotCommand(command="stats", description="Статистика чата", is_ephemeral=True),
        *group,
        BotCommand(
            command="whitelist",
            description="Добавить в белый список (ответом на сообщение)",
        ),
    ]
    await bot.set_my_commands(private, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(group, scope=BotCommandScopeAllGroupChats())
    await bot.set_my_commands(admins, scope=BotCommandScopeAllChatAdministrators())
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="help", description="Помощь"),
        ],
        scope=BotCommandScopeDefault(),
    )


async def main() -> None:
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    redis = get_redis()
    cache = RedisCache(redis)
    dp = Dispatcher(storage=RedisStorage(redis=redis))

    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(ChatContextMiddleware(cache))
    dp.include_router(build_router(cache))

    api_app = create_api_app(bot, async_session_factory, cache)
    runner = web.AppRunner(api_app)
    await runner.setup()
    site = web.TCPSite(runner, settings.api_host, settings.api_port)
    await site.start()
    logger.info("API listening on %s:%s", settings.api_host, settings.api_port)

    scheduler = setup_scheduler(bot, cache)

    await setup_commands(bot)
    await bot.delete_webhook(drop_pending_updates=False)
    me = await bot.get_me()
    logger.info("Starting polling as @%s", me.username)
    try:
        await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)
    finally:
        scheduler.shutdown(wait=False)
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
