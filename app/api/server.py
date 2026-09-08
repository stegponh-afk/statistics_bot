"""The HTTP bridge for third-party bots.

    GET /healthz
    GET /v1/check?user_id=<int>     Authorization: Bearer sb_...
    GET /v1/channels                Authorization: Bearer sb_...
    POST /v1/users                  Authorization: Bearer sb_...

    The key may also travel in the path — for bot constructors whose
    "HTTP request" action can't set headers:
    GET /v1/check/<key>?user_id=<int>,  GET /v1/channels/<key>

Errors are always JSON: {"ok": false, "error": "<code>", "detail": "..."}.
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from aiogram import Bot
from aiohttp import web
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.cache import Cache
from app.database.models import ApiKey, Chat
from app.services import api_key_service, audience_service, chat_service, rate_limit
from app.services.subscription_checker import check_user
from config import settings

logger = logging.getLogger(__name__)

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]

BOT_KEY = web.AppKey("bot", Bot)
SESSION_FACTORY_KEY = web.AppKey("session_factory", async_sessionmaker)
CACHE_KEY = web.AppKey("cache", object)


def error(status: int, code: str, detail: str, **headers: str) -> web.Response:
    return web.json_response(
        {"ok": False, "error": code, "detail": detail}, status=status, headers=headers or None
    )


def client_ip(request: web.Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote or "unknown"


@web.middleware
async def json_errors(request: web.Request, handler: Handler) -> web.StreamResponse:
    try:
        return await handler(request)
    except web.HTTPException as e:
        return error(e.status, "http_error", e.reason or "")
    except Exception:  # noqa: BLE001
        logger.exception("unhandled API error")
        return error(500, "internal_error", "Internal error")


@web.middleware
async def bearer_auth(request: web.Request, handler: Handler) -> web.StreamResponse:
    """Authenticates /v1/* and stashes the key + a session on the request."""
    if not request.path.startswith("/v1/"):
        return await handler(request)

    cache: Cache = request.app[CACHE_KEY]
    session_factory: async_sessionmaker = request.app[SESSION_FACTORY_KEY]

    header = request.headers.get("Authorization", "")
    scheme, _, raw = header.partition(" ")
    if key_in_path := request.match_info.get("key"):
        scheme, raw = "bearer", key_in_path
    if scheme.lower() != "bearer" or not raw.strip():
        decision = await rate_limit.check(
            cache, f"ip:{client_ip(request)}", settings.api_unauth_rate_limit_per_minute
        )
        if not decision.allowed:
            return error(
                429,
                "rate_limited",
                "Too many requests",
                **{"Retry-After": str(decision.retry_after)},
            )
        return error(401, "unauthorized", "Missing bearer token")

    async with session_factory() as session:
        key = await api_key_service.find_active_key(session, raw.strip())
        if key is None:
            decision = await rate_limit.check(
                cache, f"ip:{client_ip(request)}", settings.api_unauth_rate_limit_per_minute
            )
            if not decision.allowed:
                return error(
                    429,
                    "rate_limited",
                    "Too many requests",
                    **{"Retry-After": str(decision.retry_after)},
                )
            return error(401, "unauthorized", "Invalid or revoked API key")

        decision = await rate_limit.check(cache, f"k:{key.id}", settings.api_rate_limit_per_minute)
        if not decision.allowed:
            return error(
                429,
                "rate_limited",
                "Rate limit exceeded",
                **{"Retry-After": str(decision.retry_after)},
            )

        request["api_key"] = key
        request["session"] = session
        await api_key_service.touch_key(session, key)
        return await handler(request)


def channel_payload(channel: Chat, link: str | None) -> dict:
    return {
        "chat_id": channel.telegram_id,
        "title": channel.title,
        "username": channel.username,
        "invite_link": link,
    }


async def _channels_with_links(bot: Bot, session: AsyncSession, channels: list[Chat]) -> list[dict]:
    out = []
    for channel in channels:
        link = await chat_service.resolve_invite_link(bot, session, channel)
        out.append(channel_payload(channel, link))
    return out


async def healthz(_: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def v1_check(request: web.Request) -> web.Response:
    raw_user_id = request.query.get("user_id", "")
    try:
        user_id = int(raw_user_id)
    except ValueError:
        return error(400, "bad_request", "user_id must be an integer")

    key: ApiKey = request["api_key"]
    session: AsyncSession = request["session"]
    bot: Bot = request.app[BOT_KEY]
    cache: Cache = request.app[CACHE_KEY]

    channels = await api_key_service.list_key_channels(session, key)
    force = request.query.get("force") in ("1", "true")
    # Every checked user is someone the owner's bot talks to: remember them
    # as its broadcast audience.
    await audience_service.record_users(session, key, [user_id])
    result = await check_user(bot, cache, user_id, channels, force=force)
    if channels and len(result.unavailable) == len(channels):
        return error(503, "telegram_unavailable", "None of the channels could be checked")

    return web.json_response(
        {
            "ok": True,
            "user_id": user_id,
            "subscribed": result.subscribed,
            "missing": await _channels_with_links(bot, session, result.missing),
            "unavailable": [
                {"chat_id": c.telegram_id, "reason": reason} for c, reason in result.unavailable
            ],
            "cached": result.cached,
            "checked_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
    )


async def v1_channels(request: web.Request) -> web.Response:
    key: ApiKey = request["api_key"]
    session: AsyncSession = request["session"]
    bot: Bot = request.app[BOT_KEY]
    channels = await api_key_service.list_key_channels(session, key)
    return web.json_response(
        {"ok": True, "channels": await _channels_with_links(bot, session, channels)}
    )


async def v1_users(request: web.Request) -> web.Response:
    """POST {"user_ids": [...]} — registers users of the owner's bot as its
    broadcast audience (up to 10 000 per call)."""
    try:
        body = await request.json()
    except ValueError:
        return error(400, "bad_request", "Body must be JSON")
    ids = body.get("user_ids") if isinstance(body, dict) else None
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return error(400, "bad_request", "user_ids must be a list of integers")
    if len(ids) > audience_service.MAX_BATCH:
        return error(400, "bad_request", f"at most {audience_service.MAX_BATCH} ids per call")
    key: ApiKey = request["api_key"]
    session: AsyncSession = request["session"]
    added = await audience_service.record_users(session, key, ids)
    reachable, blocked = await audience_service.audience_size(session, key)
    return web.json_response(
        {"ok": True, "received": added, "audience": reachable, "blocked": blocked}
    )


def create_api_app(bot: Bot, session_factory: async_sessionmaker, cache: Cache) -> web.Application:
    app = web.Application(middlewares=[json_errors, bearer_auth])
    app[BOT_KEY] = bot
    app[SESSION_FACTORY_KEY] = session_factory
    app[CACHE_KEY] = cache
    app.router.add_get("/healthz", healthz)
    app.router.add_get("/v1/check", v1_check)
    app.router.add_get("/v1/check/{key}", v1_check)
    app.router.add_get("/v1/channels", v1_channels)
    app.router.add_get("/v1/channels/{key}", v1_channels)
    app.router.add_post("/v1/users", v1_users)
    return app
