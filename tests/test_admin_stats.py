from aiogram.types import Chat as TgChat

from app.database.models import BotStatus, User
from app.services import admin_stats, api_key_service, audience_service, chat_service
from tests.fakes import FakeBot


async def test_overview_counts(session, bot: FakeBot):
    owner = User(telegram_id=1, started_bot=True)
    other = User(telegram_id=2)
    session.add_all([owner, other])
    await session.commit()

    channel = await chat_service.upsert_chat(session, TgChat(id=-1, type="channel", title="C"))
    await chat_service.upsert_chat(session, TgChat(id=-2, type="supergroup", title="G"))
    gone = await chat_service.upsert_chat(session, TgChat(id=-3, type="channel", title="X"))
    channel.bot_status = BotStatus.ADMINISTRATOR
    gone.bot_status = BotStatus.KICKED
    await session.commit()
    bot.member_counts = {-1: 1500, -2: 40, -3: 999}
    await admin_stats.refresh_member_counts(bot, session)

    k1, _ = await api_key_service.create_key(session, owner, "bot1")
    k2, _ = await api_key_service.create_key(session, owner, "bot2")
    await api_key_service.set_bot_token(session, k2, "1:t", 1, "bot2")
    await audience_service.record_users(session, k1, [10, 11])
    await audience_service.record_users(session, k2, [11, 12, 13])
    await api_key_service.touch_key(session, k1)

    o = await admin_stats.overview(session)
    assert (o.users_total, o.users_started) == (2, 1)
    assert (o.channels, o.groups) == (1, 1)
    assert (o.channel_members, o.group_members) == (1500, 40)
    assert (o.bots, o.bots_with_token) == (2, 1)
    assert (o.audience_total, o.audience_distinct) == (5, 4)
    assert o.api_requests == 1

    channels = await admin_stats.list_chats(session, channels=True)
    assert [r.chat.telegram_id for r in channels] == [-1] and channels[0].members == 1500
    bots = await admin_stats.list_bots(session)
    assert [(r.key.name, r.audience) for r in bots] == [("bot1", 2), ("bot2", 3)]
    assert bots[0].owner.telegram_id == 1
