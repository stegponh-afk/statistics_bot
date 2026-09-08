from datetime import UTC, datetime, time, timedelta

from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage
from aiogram.types import Chat as TgChat

from app.database.models import BotStatus, BroadcastKind, BroadcastStatus, User
from app.services import broadcast_delivery, broadcast_service
from app.services.broadcast_service import Content
from app.utils import ensure_aware
from tests.fakes import FakeBot


async def _owner(session) -> User:
    user = User(telegram_id=1)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _chat(session, tg_id: int, kind: str = "supergroup"):
    from app.services import chat_service

    chat = await chat_service.upsert_chat(session, TgChat(id=tg_id, type=kind, title="G"))
    chat.bot_status = BotStatus.ADMINISTRATOR
    await session.commit()
    return chat


async def test_now_broadcast_to_chats(session, bot: FakeBot):
    owner = await _owner(session)
    group = await _chat(session, -100_1)
    channel = await _chat(session, -100_2, "channel")
    gone = await _chat(session, -100_3)
    gone.bot_status = BotStatus.KICKED
    await session.commit()

    bot.fail_next["send_message"] = TelegramForbiddenError(
        method=SendMessage(chat_id=-100_1, text="x"), message="bot was kicked"
    )
    content = Content(type="text", text="hello", buttons=[[{"text": "A", "url": "https://a"}]])
    b = await broadcast_service.create_broadcast(
        session,
        owner,
        kind=BroadcastKind.NOW,
        content=content,
        chat_ids=[group.id, channel.id, gone.id],
        tz_name="UTC",
    )
    result = await broadcast_delivery.run_broadcast(session, bot, b)
    assert (result.sent, result.failed) == (1, 2)  # one forbidden, one inactive
    calls = bot.calls_named("send_message")
    assert {c["chat_id"] for c in calls} == {-100_1, -100_2}
    assert calls[0]["reply_markup"].inline_keyboard[0][0].url == "https://a"
    assert b.status == BroadcastStatus.DONE.value and b.runs_count == 1
    assert b.sent_count == 1 and b.failed_count == 2


async def test_media_broadcast_uses_file_id(session, bot: FakeBot):
    owner = await _owner(session)
    chat = await _chat(session, -100_4, "channel")
    content = Content(type="photo", text="cap", file_id="our-file-id")
    b = await broadcast_service.create_broadcast(
        session, owner, kind=BroadcastKind.NOW, content=content, chat_ids=[chat.id], tz_name="UTC"
    )
    await broadcast_delivery.run_broadcast(session, bot, b)
    (call,) = bot.calls_named("send_photo")
    assert call["media"] == "our-file-id" and call["caption"] == "cap"


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
        tz_name="UTC",
        scheduled_at=past,
    )
    recurring = await broadcast_service.create_broadcast(
        session,
        owner,
        kind=BroadcastKind.RECURRING,
        content=content,
        chat_ids=[],
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


async def test_html_content_is_sent_with_parse_mode_and_entities_without(session, bot: FakeBot):
    owner = await _owner(session)
    chat = await _chat(session, -100_5)
    html = Content(type="text", text="<b>x</b>", parse_mode="HTML")
    b = await broadcast_service.create_broadcast(
        session, owner, kind=BroadcastKind.NOW, content=html, chat_ids=[chat.id], tz_name="UTC"
    )
    await broadcast_delivery.run_broadcast(session, bot, b)
    call = bot.calls_named("send_message")[-1]
    assert call["parse_mode"] == "HTML" and call["entities"] is None

    plain = Content(type="text", text="x", entities=[{"type": "bold", "offset": 0, "length": 1}])
    b = await broadcast_service.create_broadcast(
        session, owner, kind=BroadcastKind.NOW, content=plain, chat_ids=[chat.id], tz_name="UTC"
    )
    await broadcast_delivery.run_broadcast(session, bot, b)
    call = bot.calls_named("send_message")[-1]
    assert call["parse_mode"] is None and call["entities"][0].type == "bold"
