from aiogram.types import Chat as TgChat

from app.services import chat_service, forcesub_service
from app.services.forcesub_service import is_exempt
from tests.fakes import make_message


def test_exempt_matrix():
    plain = make_message(user_id=5)
    assert not is_exempt(plain, is_chat_admin=False, whitelist_ids=set())
    assert is_exempt(plain, is_chat_admin=True, whitelist_ids=set())
    assert is_exempt(plain, is_chat_admin=False, whitelist_ids={5})

    bot_msg = make_message(user_id=6, from_bot=True)
    assert is_exempt(bot_msg, is_chat_admin=False, whitelist_ids=set())

    anonymous = make_message(user_id=1087968824, sender_chat_id=-100_1)
    assert is_exempt(anonymous, is_chat_admin=False, whitelist_ids=set())

    service_account = make_message(user_id=777000)
    assert is_exempt(service_account, is_chat_admin=False, whitelist_ids=set())

    joined = make_message(
        user_id=5,
        text=None,
        content_type_payload={"new_chat_members": [{"id": 5, "is_bot": False, "first_name": "N"}]},
    )
    assert is_exempt(joined, is_chat_admin=False, whitelist_ids=set())


async def test_required_channels_and_cache(session, cache):
    group = await chat_service.upsert_chat(session, TgChat(id=-1, type="supergroup", title="G"))
    channel = await chat_service.upsert_chat(session, TgChat(id=-2, type="channel", title="C"))

    assert await forcesub_service.required_channel_tg_ids(session, cache, group) == []
    assert await forcesub_service.toggle_required_channel(session, cache, group, channel) is True
    assert await forcesub_service.required_channel_tg_ids(session, cache, group) == [-2]
    assert [c.id for c in await forcesub_service.list_required_channels(session, group)] == [
        channel.id
    ]
    assert await forcesub_service.toggle_required_channel(session, cache, group, channel) is False
    assert await forcesub_service.required_channel_tg_ids(session, cache, group) == []


async def test_whitelist_roundtrip(session, cache):
    group = await chat_service.upsert_chat(session, TgChat(id=-1, type="supergroup", title="G"))
    assert await forcesub_service.whitelist_ids(session, cache, group) == set()
    assert await forcesub_service.add_to_whitelist(session, cache, group, 7, None) is True
    assert await forcesub_service.add_to_whitelist(session, cache, group, 7, None) is False
    assert await forcesub_service.whitelist_ids(session, cache, group) == {7}
    await forcesub_service.remove_from_whitelist(session, cache, group, 7)
    assert await forcesub_service.whitelist_ids(session, cache, group) == set()


async def test_comments_gate_binds_channel_in_its_discussion_group(session, cache, bot):
    channel = await chat_service.upsert_chat(session, TgChat(id=-10, type="channel", title="C"))
    group = await chat_service.upsert_chat(session, TgChat(id=-20, type="supergroup", title="G"))
    group.bot_can_delete = True
    await session.commit()

    assert await chat_service.resolve_linked_group(bot, session, channel) is None
    bot.linked_chats[-10] = -20
    linked = await chat_service.resolve_linked_group(bot, session, channel, refresh=True)
    assert linked.id == group.id and channel.linked_chat_tg_id == -20
    assert len(bot.calls_named("get_chat")) == 2
    await chat_service.resolve_linked_group(bot, session, channel)  # cached, no API call
    assert len(bot.calls_named("get_chat")) == 2

    assert not await forcesub_service.comments_gate_enabled(session, channel, group)
    await forcesub_service.set_comments_gate(session, cache, channel, group, True)
    assert group.forcesub_enabled
    assert await forcesub_service.comments_gate_enabled(session, channel, group)
    assert await forcesub_service.required_channel_tg_ids(session, cache, group) == [-10]

    await forcesub_service.set_comments_gate(session, cache, channel, group, False)
    assert not group.forcesub_enabled
    assert await forcesub_service.required_channel_tg_ids(session, cache, group) == []
