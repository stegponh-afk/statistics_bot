from aiogram.types import Chat as TgChat

from app.services import chat_service, reward_service
from app.services.broadcast_service import Content


async def test_reward_roundtrip_and_claims(session, bot):
    channel = await chat_service.upsert_chat(session, TgChat(id=-1, type="channel", title="C"))
    assert reward_service.reward_of(channel) is None
    await reward_service.set_reward(session, channel, Content(type="text", text="x"))
    assert reward_service.reward_of(channel).text == "x"
    assert len(channel.reward_slug) == 8
    assert (await reward_service.channel_by_slug(session, channel.reward_slug)).id == channel.id
    assert await reward_service.channel_by_slug(session, "nope") is None
    assert (await reward_service.deep_link(bot, channel)).endswith(
        f"?start=sub_{channel.reward_slug}"
    )
    assert reward_service.slug_from_start_arg("sub_abc") == "abc"
    assert reward_service.slug_from_start_arg("other") is None

    assert await reward_service.claim(session, channel, 5) is None  # first time
    again = await reward_service.claim(session, channel, 5)
    assert again is not None and again.user_tg_id == 5
    await reward_service.claim(session, channel, 6)
    assert await reward_service.claims_count(session, channel) == 2
    await reward_service.reset_claims(session, channel)
    assert await reward_service.claims_count(session, channel) == 0
    assert await reward_service.claim(session, channel, 5) is None

    await reward_service.clear_reward(session, channel)
    assert reward_service.reward_of(channel) is None
    assert channel.reward_slug  # the link stays stable
