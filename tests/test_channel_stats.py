from datetime import UTC, date, datetime, timedelta

from aiogram.types import Chat as TgChat
from aiogram.types import MessageReactionCountUpdated

from app.services import channel_stats, chat_service, stats_service
from tests.fakes import FakeBot, make_message

CHANNEL = -100_55


async def _channel(session):
    chat = await chat_service.upsert_chat(session, TgChat(id=CHANNEL, type="channel", title="C"))
    chat.timezone = "UTC"
    chat.username = "chan"
    await session.commit()
    return chat


def _reaction_update(message_id: int, total: int) -> MessageReactionCountUpdated:
    return MessageReactionCountUpdated.model_validate(
        {
            "chat": {"id": CHANNEL, "type": "channel", "title": "C"},
            "message_id": message_id,
            "date": int(datetime.now(UTC).timestamp()),
            "reactions": [
                {"type": {"type": "emoji", "emoji": "👍"}, "total_count": total},
            ],
        }
    )


async def test_flow_snapshots_and_growth(session, bot: FakeBot):
    chat = await _channel(session)
    today = date(2026, 3, 10)
    at = datetime(2026, 3, 10, 12, tzinfo=UTC)
    for uid, kind, delta in ((1, "join", 0), (2, "join", 0), (3, "leave", 0), (4, "join", 1)):
        await channel_stats.record_member_event(
            session, chat, uid, kind, at - timedelta(days=delta)
        )
    assert (await channel_stats.flow(session, CHANNEL, today, today)).net == 1
    assert (await channel_stats.flow(session, CHANNEL, today - timedelta(days=1), today)).joins == 3

    await channel_stats.snapshot_member_count(session, chat, 100, at - timedelta(days=8))
    await channel_stats.snapshot_member_count(
        session, chat, 110, at - timedelta(days=8)
    )  # same day
    await channel_stats.snapshot_member_count(session, chat, 120, at)
    assert (
        await channel_stats.count_on_or_before(session, CHANNEL, today - timedelta(days=7)) == 110
    )
    assert (
        await channel_stats.count_on_or_before(session, CHANNEL, today - timedelta(days=30)) is None
    )
    assert channel_stats.growth_label(120, 110) == "+10 (▲9.1%)"
    assert channel_stats.growth_label(100, 110) == "-10 (▼9.1%)"
    assert channel_stats.growth_label(120, None) == "—"

    rows = await channel_stats.daily_rows(session, CHANNEL, today, days=3)
    assert [r.day for r in rows] == [today - timedelta(days=2), today - timedelta(days=1), today]
    assert rows[-1].subscribers == 120 and rows[-1].joins == 2 and rows[-1].leaves == 1


async def test_get_member_count_writes_a_snapshot(session, bot: FakeBot):
    chat = await _channel(session)
    bot.member_counts[CHANNEL] = 777
    assert await chat_service.get_member_count(bot, session, chat) == 777
    today = date.today()
    assert await channel_stats.count_on_or_before(session, CHANNEL, today) == 777


async def test_reactions_and_top_posts(session):
    chat = await _channel(session)
    at = datetime(2026, 3, 10, 9, tzinfo=UTC)
    for mid in (1, 2, 3):
        await stats_service.record_message(
            session,
            chat,
            make_message(
                chat_id=CHANNEL, chat_type="channel", user_id=None, message_id=mid, date=at
            ),
        )
    await channel_stats.record_reactions(session, _reaction_update(1, 5))
    await channel_stats.record_reactions(session, _reaction_update(2, 12))
    await channel_stats.record_reactions(session, _reaction_update(2, 15))  # updated total
    today = date(2026, 3, 10)
    stats = await channel_stats.reactions(session, CHANNEL, today - timedelta(days=29), today)
    assert stats.posts_with_reactions == 2
    assert stats.best_message_id == 2 and stats.best_total == 15
    assert round(stats.average, 2) == round(20 / 3, 2)
    top = await channel_stats.top_posts(session, CHANNEL, today - timedelta(days=29), today)
    assert [(m, t) for m, t, _ in top] == [(2, 15), (1, 5)]
    assert channel_stats.post_link(chat, 2) == "https://t.me/chan/2"
    chat.username = None
    assert channel_stats.post_link(chat, 2) == "https://t.me/c/55/2"
