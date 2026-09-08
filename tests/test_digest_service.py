import itertools
from datetime import UTC, date, datetime, timedelta

from aiogram.types import Chat as TgChat
from aiogram.types import MessageReactionCountUpdated

from app.database.models import AdminStatus, BotStatus, ChatAdmin, User
from app.services import channel_stats, chat_service, digest_service, stats_service
from tests.fakes import FakeBot, make_message

GROUP = -100_41
CHANNEL = -100_42
_message_ids = itertools.count(1000)


async def _chat(session, tg_id: int, kind: str = "supergroup", **flags):
    chat = await chat_service.upsert_chat(session, TgChat(id=tg_id, type=kind, title="Клуб"))
    chat.bot_status = BotStatus.ADMINISTRATOR
    chat.timezone = "UTC"
    chat.digest_enabled = True
    for key, value in flags.items():
        setattr(chat, key, value)
    await session.commit()
    return chat


async def _admin(session, chat, telegram_id: int, *, started: bool = True) -> User:
    user = User(telegram_id=telegram_id, full_name=f"A{telegram_id}", started_bot=started)
    session.add(user)
    await session.flush()
    session.add(ChatAdmin(chat_id=chat.id, user_id=user.id, status=AdminStatus.ADMINISTRATOR))
    await session.commit()
    return user


async def _messages(session, chat, day: date, *, count: int, user_id: int = 1, text: str = "кот"):
    at = datetime(day.year, day.month, day.day, 12, tzinfo=UTC)
    ids = []
    for _ in range(count):
        message_id = next(_message_ids)
        ids.append(message_id)
        await stats_service.record_message(
            session,
            chat,
            make_message(
                chat_id=chat.telegram_id,
                message_id=message_id,
                user_id=user_id,
                text=text,
                date=at,
            ),
        )
    return ids


def _reaction_update(message_id: int, total: int) -> MessageReactionCountUpdated:
    return MessageReactionCountUpdated.model_validate(
        {
            "chat": {"id": CHANNEL, "type": "channel", "title": "Клуб"},
            "message_id": message_id,
            "date": int(datetime.now(UTC).timestamp()),
            "reactions": [{"type": {"type": "emoji", "emoji": "👍"}, "total_count": total}],
        }
    )


# --- the reported window --------------------------------------------------


def test_daily_window_is_yesterday_and_weekly_is_the_last_seven_days():
    today = date(2026, 3, 10)
    daily = digest_service.window(digest_service.DAILY, today)
    assert (daily.day_from, daily.day_to) == (date(2026, 3, 9), date(2026, 3, 9))
    assert (daily.prev_from, daily.prev_to) == (date(2026, 3, 8), date(2026, 3, 8))

    weekly = digest_service.window(digest_service.WEEKLY, today)
    assert (weekly.day_from, weekly.day_to) == (date(2026, 3, 3), date(2026, 3, 9))
    assert (weekly.prev_from, weekly.prev_to) == (date(2026, 2, 24), date(2026, 3, 2))


# --- when it fires --------------------------------------------------------


async def test_is_due_respects_time_period_and_the_last_sent_day(session):
    chat = await _chat(session, GROUP, digest_time="10:00")
    monday = datetime(2026, 3, 9, tzinfo=UTC)  # 2026-03-09 is a Monday

    assert not digest_service.is_due(chat, monday.replace(hour=9, minute=59))
    assert digest_service.is_due(chat, monday.replace(hour=10))
    assert digest_service.is_due(chat, monday.replace(hour=23))

    chat.digest_last_day = date(2026, 3, 9)
    assert not digest_service.is_due(chat, monday.replace(hour=12))
    assert digest_service.is_due(chat, monday.replace(hour=12) + timedelta(days=1))

    chat.digest_last_day = None
    chat.digest_period = digest_service.WEEKLY
    assert digest_service.is_due(chat, monday.replace(hour=12))
    assert not digest_service.is_due(chat, monday.replace(hour=12) + timedelta(days=1))

    chat.digest_enabled = False
    assert not digest_service.is_due(chat, monday.replace(hour=12))


async def test_due_chats_skips_chats_the_bot_has_left(session):
    due = await _chat(session, GROUP, digest_time="00:00")
    gone = await _chat(session, CHANNEL, "channel", digest_time="00:00")
    gone.bot_status = BotStatus.KICKED
    await session.commit()

    now = datetime(2026, 3, 9, 12, tzinfo=UTC)
    assert [c.id for c in await digest_service.due_chats(session, now)] == [due.id]


# --- what it says ---------------------------------------------------------


async def test_group_report_counts_messages_people_and_the_week_over_week_change(session):
    chat = await _chat(session, GROUP)
    today = date(2026, 3, 10)
    await _messages(session, chat, today - timedelta(days=1), count=3, user_id=1, text="кот")
    await _messages(session, chat, today - timedelta(days=1), count=1, user_id=2, text="пёс")
    await _messages(session, chat, today - timedelta(days=2), count=2, user_id=1)
    await channel_stats.record_member_event(
        session, chat, 7, channel_stats.JOIN, datetime(2026, 3, 9, 8, tzinfo=UTC)
    )
    await channel_stats.snapshot_member_count(
        session, chat, 150, datetime(2026, 3, 9, 23, tzinfo=UTC)
    )

    text = (await digest_service.build_screen(session, chat, today)).text
    assert "09.03.2026" in text
    assert "Сообщений: <b>4</b>" in text
    assert "было 2" in text and "▲100%" in text
    assert "Писали: <b>2</b>" in text
    assert "Участников: <b>150</b>" in text and "+1" in text
    assert "кот" in text


async def test_quiet_group_says_so_instead_of_showing_zeros(session):
    chat = await _chat(session, GROUP)
    text = (await digest_service.build_screen(session, chat, date(2026, 3, 10))).text
    assert "тихо" in text


async def test_channel_report_covers_posts_and_reactions(session):
    chat = await _chat(session, CHANNEL, "channel", username="chan")
    today = date(2026, 3, 10)
    message_id, _ = await _messages(session, chat, today - timedelta(days=1), count=2, user_id=None)
    await channel_stats.record_reactions(session, _reaction_update(message_id, 9))

    text = (await digest_service.build_screen(session, chat, today)).text
    assert "Постов: <b>2</b>" in text
    assert "<b>9</b> реакций" in text
    assert f"https://t.me/chan/{message_id}" in text


# --- delivery -------------------------------------------------------------


async def test_digest_goes_to_admins_who_started_the_bot_and_is_marked_sent(session, bot: FakeBot):
    chat = await _chat(session, GROUP)
    await _admin(session, chat, 11)
    await _admin(session, chat, 12, started=False)

    now = datetime(2026, 3, 10, 10, tzinfo=UTC)
    assert await digest_service.send_digest(bot, session, chat, now) == 1
    assert [c["chat_id"] for c in bot.calls_named("send_rich_message")] == [11]
    assert chat.digest_last_day == date(2026, 3, 10)
    assert not digest_service.is_due(chat, now)
