import pytest
from aiogram.types import Chat as TgChat
from aiogram.types import ChatMemberLeft, ChatMemberMember
from aiohttp.test_utils import TestClient, TestServer

from app.api.server import create_api_app
from app.database.models import User
from app.services import api_key_service, chat_service
from tests.fakes import FakeBot, tg_user

CHANNEL = -100_9
USER = 42


@pytest.fixture
async def owner(session):
    user = User(telegram_id=1, full_name="Owner")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def key(session, owner):
    channel = await chat_service.upsert_chat(session, TgChat(id=CHANNEL, type="channel", title="C"))
    channel.username = "chan"
    await session.commit()
    key, raw = await api_key_service.create_key(session, owner, "Мой бот")
    await api_key_service.toggle_key_channel(session, key, channel)
    return key, raw


@pytest.fixture
async def client(bot: FakeBot, session_factory, cache):
    app = create_api_app(bot, session_factory, cache)
    async with TestClient(TestServer(app)) as client:
        yield client


async def test_healthz(client):
    resp = await client.get("/healthz")
    assert resp.status == 200 and (await resp.json()) == {"ok": True}


async def test_missing_and_bad_token(client):
    resp = await client.get("/v1/check?user_id=1")
    assert resp.status == 401
    assert (await resp.json())["error"] == "unauthorized"
    resp = await client.get("/v1/check?user_id=1", headers={"Authorization": "Bearer sb_nope"})
    assert resp.status == 401


async def test_bad_user_id(client, key):
    _, raw = key
    resp = await client.get("/v1/check?user_id=abc", headers={"Authorization": f"Bearer {raw}"})
    assert resp.status == 400
    assert (await resp.json())["error"] == "bad_request"


async def test_check_subscribed_and_missing(client, key, bot: FakeBot, session):
    _, raw = key
    headers = {"Authorization": f"Bearer {raw}"}
    bot.members[(CHANNEL, USER)] = ChatMemberLeft(user=tg_user(USER))
    resp = await client.get(f"/v1/check?user_id={USER}", headers=headers)
    assert resp.status == 200
    body = await resp.json()
    assert body["ok"] is True and body["subscribed"] is False
    assert body["missing"] == [
        {"chat_id": CHANNEL, "title": "C", "username": "chan", "invite_link": "https://t.me/chan"}
    ]
    assert body["unavailable"] == [] and body["cached"] is False
    assert body["checked_at"].endswith("Z")

    # Cached for a minute: still "not subscribed" until force=1.
    bot.members[(CHANNEL, USER)] = ChatMemberMember(user=tg_user(USER))
    body = await (await client.get(f"/v1/check?user_id={USER}", headers=headers)).json()
    assert body["subscribed"] is False and body["cached"] is True
    body = await (await client.get(f"/v1/check?user_id={USER}&force=1", headers=headers)).json()
    assert body["subscribed"] is True and body["missing"] == []

    refreshed = await session.get(type(key[0]), key[0].id)
    await session.refresh(refreshed)
    assert refreshed.request_count == 3 and refreshed.last_used_at is not None


async def test_channels_endpoint(client, key):
    _, raw = key
    resp = await client.get("/v1/channels", headers={"Authorization": f"Bearer {raw}"})
    body = await resp.json()
    assert resp.status == 200 and [c["chat_id"] for c in body["channels"]] == [CHANNEL]


async def test_revoked_key_is_rejected(client, key, session, cache):
    api_key, raw = key
    await api_key_service.revoke_key(session, cache, api_key)
    resp = await client.get("/v1/channels", headers={"Authorization": f"Bearer {raw}"})
    assert resp.status == 401


async def test_rate_limit(client, key, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "api_rate_limit_per_minute", 2)
    _, raw = key
    headers = {"Authorization": f"Bearer {raw}"}
    assert (await client.get("/v1/channels", headers=headers)).status == 200
    assert (await client.get("/v1/channels", headers=headers)).status == 200
    resp = await client.get("/v1/channels", headers=headers)
    assert resp.status == 429 and "Retry-After" in resp.headers


async def test_unauthenticated_requests_are_rate_limited_per_ip(client, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "api_unauth_rate_limit_per_minute", 1)
    assert (await client.get("/v1/check?user_id=1")).status == 401
    assert (await client.get("/v1/check?user_id=1")).status == 429
