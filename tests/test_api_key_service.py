from aiogram.types import Chat as TgChat

from app.database.models import User
from app.services import api_key_service, chat_service


async def _owner(session) -> User:
    user = User(telegram_id=1)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def test_create_find_and_prefix(session):
    owner = await _owner(session)
    key, raw = await api_key_service.create_key(session, owner, "x" * 80)
    assert raw.startswith("sb_") and len(key.name) == 64
    assert key.key_prefix == raw[:10]
    assert key.key_hash == api_key_service.hash_key(raw)
    assert (await api_key_service.find_active_key(session, raw)).id == key.id
    assert await api_key_service.find_active_key(session, "nope") is None
    assert await api_key_service.get_owned_key(session, owner, key.id) is key
    other = User(telegram_id=2)
    session.add(other)
    await session.commit()
    assert await api_key_service.get_owned_key(session, other, key.id) is None


async def test_rotate_keeps_channels_and_revokes_old(session, cache):
    owner = await _owner(session)
    channel = await chat_service.upsert_chat(session, TgChat(id=-1, type="channel", title="C"))
    key, raw = await api_key_service.create_key(session, owner, "bot")
    await api_key_service.toggle_key_channel(session, key, channel)

    new_key, new_raw = await api_key_service.rotate_key(session, cache, key)
    assert new_key.id != key.id and new_raw != raw
    assert key.is_active is False and key.revoked_at is not None
    assert await api_key_service.find_active_key(session, raw) is None
    assert [c.id for c in await api_key_service.list_key_channels(session, new_key)] == [channel.id]
    assert [k.id for k in await api_key_service.list_keys(session, owner)] == [new_key.id]
    assert len(await api_key_service.list_keys(session, owner, include_revoked=True)) == 2


async def test_delete_and_touch(session, cache):
    owner = await _owner(session)
    key, _ = await api_key_service.create_key(session, owner, "bot")
    await api_key_service.touch_key(session, key)
    await session.refresh(key)
    assert key.request_count == 1 and key.last_used_at is not None
    await api_key_service.delete_key(session, cache, key)
    assert await api_key_service.list_keys(session, owner, include_revoked=True) == []
