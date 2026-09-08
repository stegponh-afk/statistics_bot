from aiogram import Bot
from aiohttp import web
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.cache import Cache


async def healthz(_: web.Request) -> web.Response:
    return web.json_response({"ok": True})


def create_api_app(bot: Bot, session_factory: async_sessionmaker, cache: Cache) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app["session_factory"] = session_factory
    app["cache"] = cache
    app.router.add_get("/healthz", healthz)
    return app
