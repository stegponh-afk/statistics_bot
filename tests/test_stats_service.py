from datetime import UTC, date, datetime, timedelta

from aiogram.types import Chat as TgChat
from sqlalchemy import func, select

from app.database.models import MessageEvent, WordStatDaily
from app.handlers.stats_screens import hour_rows
from app.services import chat_service, stats_service
from tests.fakes import make_message

CHAT = -100_77


async def _chat(session, tz: str | None = "Europe/Moscow"):
    chat = await chat_service.upsert_chat(session, TgChat(id=CHAT, type="supergroup", title="T"))
    chat.timezone = tz
    await session.commit()
    return chat


def _msg(message_id: int, *, user_id: int | None = 1, text: str = "привет мир", at: datetime, **kw):
    return make_message(
        chat_id=CHAT, message_id=message_id, user_id=user_id, text=text, date=at, **kw
    )


async def test_record_message_stores_local_day_hour_and_words(session):
    chat = await _chat(session, "Europe/Moscow")
    # 22:30 UTC on Jan 1 is 01:30 Jan 2 in Moscow (UTC+3).
    at = datetime(2026, 1, 1, 22, 30, tzinfo=UTC)
    assert await stats_service.record_message(session, chat, _msg(1, at=at, text="Мир мир труд"))

    event = await session.scalar(select(MessageEvent))
    assert event.local_day == date(2026, 1, 2)
    assert event.local_hour == 1
    assert event.user_tg_id == 1
    assert event.text_length == len("Мир мир труд")

    words = {w.word: w.count for w in await session.scalars(select(WordStatDaily))}
    assert words == {"мир": 2, "труд": 1}

    # Same message again (redelivered update) is ignored, words not doubled.
    assert not await stats_service.record_message(session, chat, _msg(1, at=at, text="Мир"))
    words = {w.word: w.count for w in await session.scalars(select(WordStatDaily))}
    assert words == {"мир": 2, "труд": 1}


async def test_word_counts_accumulate_across_messages(session):
    chat = await _chat(session, "UTC")
    at = datetime(2026, 1, 1, 10, tzinfo=UTC)
    await stats_service.record_message(session, chat, _msg(1, at=at, text="кот"))
    await stats_service.record_message(session, chat, _msg(2, at=at, text="кот и собака"))
    words = {w.word: w.count for w in await session.scalars(select(WordStatDaily))}
    assert words == {"кот": 2, "собака": 1}


async def test_ephemeral_and_service_messages_are_skipped(session):
    chat = await _chat(session)
    at = datetime(2026, 1, 1, 10, tzinfo=UTC)
    ephemeral = make_message(chat_id=CHAT, ephemeral_message_id=3, text="/stats", date=at)
    assert not await stats_service.record_message(session, chat, ephemeral)
    joined = make_message(
        chat_id=CHAT,
        message_id=9,
        text=None,
        date=at,
        content_type_payload={"new_chat_members": [{"id": 5, "is_bot": False, "first_name": "N"}]},
    )
    assert not await stats_service.record_message(session, chat, joined)
    assert await session.scalar(select(func.count()).select_from(MessageEvent)) == 0


async def test_sender_chat_messages_have_no_user(session):
    chat = await _chat(session, "UTC")
    at = datetime(2026, 1, 1, 10, tzinfo=UTC)
    anon = _msg(1, at=at, user_id=1087968824, sender_chat_id=CHAT)
    assert await stats_service.record_message(session, chat, anon)
    event = await session.scalar(select(MessageEvent))
    assert event.user_tg_id is None and event.sender_chat_tg_id == CHAT


async def test_overview_and_periods(session):
    chat = await _chat(session, "UTC")
    today = date(2026, 3, 10)
    base = datetime(2026, 3, 10, 12, tzinfo=UTC)
    n = 0
    for days_ago, count, user in (
        (0, 3, 1),
        (1, 2, 2),
        (6, 1, 3),
        (7, 5, 4),
        (29, 1, 5),
        (31, 9, 6),
    ):
        for _ in range(count):
            n += 1
            await stats_service.record_message(
                session, chat, _msg(n, user_id=user, at=base - timedelta(days=days_ago))
            )
    data = await stats_service.overview(session, CHAT, today)
    assert data.today == 3
    assert data.week == 3 + 2 + 1
    assert data.month == 3 + 2 + 1 + 5 + 1
    assert data.active_week == 3


async def test_top_users_and_words_and_hours(session):
    chat = await _chat(session, "UTC")
    at = datetime(2026, 3, 10, 9, tzinfo=UTC)
    n = 0
    for user, count in ((1, 4), (2, 2), (3, 6), (4, 1), (5, 1), (6, 1)):
        for _ in range(count):
            n += 1
            await stats_service.record_message(
                session, chat, _msg(n, user_id=user, at=at, text=f"пользователь x{user}")
            )
    today = date(2026, 3, 10)
    users = await stats_service.top_users(session, CHAT, today - timedelta(days=6), today)
    assert [u for u, _ in users] == [3, 1, 2, 4, 5]
    assert users[0][1] == 6

    words = await stats_service.top_words(session, CHAT, today - timedelta(days=6), today, limit=2)
    assert words[0] == ("пользователь", 15)

    hours = await stats_service.activity_by_hour(session, CHAT, today - timedelta(days=6), today)
    assert len(hours) == 24 and hours[9] == 15 and sum(hours) == 15


async def test_user_stats_rank(session):
    chat = await _chat(session, "UTC")
    at = datetime(2026, 3, 10, 9, tzinfo=UTC)
    n = 0
    for user, count in ((1, 4), (2, 2), (3, 6)):
        for _ in range(count):
            n += 1
            await stats_service.record_message(session, chat, _msg(n, user_id=user, at=at))
    today = date(2026, 3, 10)
    me = await stats_service.user_stats(session, CHAT, 1, today)
    assert (me.today, me.week, me.month) == (4, 4, 4)
    assert me.rank_week == 2 and me.active_week == 3
    nobody = await stats_service.user_stats(session, CHAT, 99, today)
    assert nobody.rank_week is None and nobody.week == 0


async def test_purge_older_than(session):
    chat = await _chat(session, "UTC")
    now = datetime.now(UTC)
    await stats_service.record_message(session, chat, _msg(1, at=now - timedelta(days=100)))
    await stats_service.record_message(session, chat, _msg(2, at=now - timedelta(days=1)))
    events, words = await stats_service.purge_older_than(session, 90, batch=1)
    assert events == 1 and words == 1
    assert await session.scalar(select(func.count()).select_from(MessageEvent)) == 1


def test_hour_rows_scale_bars_to_peak():
    slots = [0] * 24
    slots[10] = 10
    slots[11] = 10
    slots[0] = 1
    rows = hour_rows(slots)
    assert len(rows) == 12
    assert rows[5] == ("10–11", "▇" * 10, 20)
    assert rows[0][2] == 1 and rows[0][1] == "▇"
    assert rows[1] == ("02–03", "·", 0)
