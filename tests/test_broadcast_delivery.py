from datetime import UTC, datetime, time, timedelta

from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage
from aiogram.types import Chat as TgChat
from sqlalchemy import select

from app.database.models import BotAudience, BotStatus, BroadcastKind, BroadcastStatus, User
from app.services import api_key_service, audience_service, broadcast_delivery, broadcast_service
from app.services.broadcast_service import Content
from app.utils import ensure_aware
from tests.fakes import FakeBot


async def _owner(session) -> User:
    user = User(telegram_id=1)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _chat(session, tg_id: int):
    from app.services import chat_service

    chat = await chat_service.upsert_chat(session, TgChat(id=tg_id, type="supergroup", title="G"))
    chat.bot_status = BotStatus.ADMINISTRATOR
    await session.commit()
    return chat


async def test_now_broadcast_to_chats_and_bot_audience(session, bot: FakeBot):
    owner = await _owner(session)
    chat = await _chat(session, -100_1)
    key, _ = await api_key_service.create_key(session, owner, "mybot")
    await api_key_service.set_bot_token(session, key, "111:token", 111, "mybot")
    await audience_service.record_users(session, key, [10, 11, 12])

    their_bot = FakeBot(bot_id=111)
    their_bot.fail_next["send_message"] = TelegramForbiddenError(
        method=SendMessage(chat_id=10, text="x"), message="bot was blocked by the user"
    )
    content = Content(type="text", text="hello", buttons=[[{"text": "A", "url": "https://a"}]])
    b = await broadcast_service.create_broadcast(
        session,
        owner,
        kind=BroadcastKind.NOW,
        content=content,
        chat_ids=[chat.id],
        bot_key_ids=[key.id],
        tz_name="UTC",
    )
    result = await broadcast_delivery.run_broadcast(
        session, bot, b, bot_factory=lambda token: their_bot
    )
    assert (result.sent, result.failed, result.blocked) == (3, 0, 1)
    assert bot.calls_named("send_message")[0]["chat_id"] == -100_1
    assert (
        bot.calls_named("send_message")[0]["reply_markup"].inline_keyboard[0][0].url == "https://a"
    )
    assert len(their_bot.calls_named("send_message")) == 3
    assert b.status == BroadcastStatus.DONE.value and b.runs_count == 1
    assert b.sent_count == 3 and b.failed_count == 1
    blocked = await session.scalar(
        select(BotAudience).where(
            BotAudience.api_key_id == key.id, BotAudience.is_blocked.is_(True)
        )
    )
    assert blocked.user_tg_id == 10
    reachable, blocked_n = await audience_service.audience_size(session, key)
    assert (reachable, blocked_n) == (2, 1)


async def test_media_is_reuploaded_once_for_another_bot(session, bot: FakeBot):
    owner = await _owner(session)
    key, _ = await api_key_service.create_key(session, owner, "mybot")
    await api_key_service.set_bot_token(session, key, "111:token", 111, "mybot")
    await audience_service.record_users(session, key, [10, 11])
    their_bot = FakeBot(bot_id=111)
    content = Content(type="photo", text="cap", file_id="our-file-id")
    b = await broadcast_service.create_broadcast(
        session,
        owner,
        kind=BroadcastKind.NOW,
        content=content,
        chat_ids=[],
        bot_key_ids=[key.id],
        tz_name="UTC",
    )
    await broadcast_delivery.run_broadcast(session, bot, b, bot_factory=lambda token: their_bot)
    assert len(bot.calls_named("download")) == 1
    sends = their_bot.calls_named("send_photo")
    assert len(sends) == 2
    assert not isinstance(sends[0]["media"], str)  # bytes on the first send
    assert sends[1]["media"] == "photo-fid-111"  # reused file_id afterwards
    assert sends[0]["caption"] == "cap"


async def test_due_and_recurring_advance(session):
    owner = await _owner(session)
    content = Content(type="text", text="x")
    past = datetime.now(UTC) - timedelta(minutes=1)
    once = await broadcast_service.create_broadcast(
        session,
        owner,
        kind=BroadcastKind.ONCE,
        content=content,
        chat_ids=[],
        bot_key_ids=[],
        tz_name="UTC",
        scheduled_at=past,
    )
    recurring = await broadcast_service.create_broadcast(
        session,
        owner,
        kind=BroadcastKind.RECURRING,
        content=content,
        chat_ids=[],
        bot_key_ids=[],
        tz_name="UTC",
        recur_days=list(range(7)),
        recur_time=time(0, 0),
    )
    due_ids = {b.id for b in await broadcast_service.due_broadcasts(session)}
    assert once.id in due_ids and recurring.id not in due_ids

    before = ensure_aware(recurring.next_run_at)
    broadcast_service.advance_after_run(recurring, before + timedelta(seconds=1))
    assert recurring.status == BroadcastStatus.SCHEDULED.value
    assert recurring.next_run_at == before + timedelta(days=1)

    broadcast_service.advance_after_run(once)
    assert once.status == BroadcastStatus.DONE.value and once.next_run_at is None

    await broadcast_service.set_status(session, recurring, BroadcastStatus.PAUSED)
    assert recurring.id not in {b.id for b in await broadcast_service.due_broadcasts(session)}
    await broadcast_service.set_status(session, recurring, BroadcastStatus.CANCELLED)
    assert [b.id for b in await broadcast_service.list_broadcasts(session, owner)] == [once.id]
