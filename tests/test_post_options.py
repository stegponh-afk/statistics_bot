"""Per-post options: silent, pin, no-forwarding, no-comments, ad label."""

from datetime import UTC, datetime, timedelta

from aiogram.types import Chat as TgChat
from sqlalchemy import select

from app.cache import MemoryCache
from app.database.models import AdPost, BotStatus
from app.services import broadcast_delivery, channel_stats, chat_service, comment_control
from app.services.broadcast_service import Content
from tests.fakes import FakeBot, make_message

CHANNEL = -100_91
GROUP = -100_92  # the channel's discussion group


async def _channel(session):
    chat = await chat_service.upsert_chat(
        session, TgChat(id=CHANNEL, type="channel", title="К", username="chan")
    )
    chat.bot_status = BotStatus.ADMINISTRATOR
    chat.timezone = "UTC"
    await session.commit()
    return chat


# --- the ad label --------------------------------------------------------


def test_ad_label_is_appended_only_to_ad_posts():
    plain = Content(type="text", text="Текст")
    assert broadcast_delivery.with_ad_label(plain, "#реклама").text == "Текст"

    ad = Content(type="text", text="Текст", is_ad=True)
    assert broadcast_delivery.with_ad_label(ad, "#реклама").text == "Текст\n\n#реклама"
    assert ad.text == "Текст"  # the stored content is untouched


def test_ad_label_is_escaped_for_html_content():
    ad = Content(type="text", text="<b>Т</b>", is_ad=True, parse_mode="HTML")
    assert broadcast_delivery.with_ad_label(ad, "<Партнёр>").text.endswith("&lt;Партнёр&gt;")


def test_ad_label_is_dropped_rather_than_breaking_a_full_post():
    """Telegram refuses an over-long post outright; better no label."""
    ad = Content(type="photo", file_id="f", text="x" * 1020, is_ad=True)
    assert broadcast_delivery.with_ad_label(ad, "#реклама").text == "x" * 1020


def test_entity_formatting_survives_the_appended_label():
    """Offsets all point before the tail, so nothing shifts."""
    ad = Content(
        type="text",
        text="Привет",
        entities=[{"type": "bold", "offset": 0, "length": 6}],
        is_ad=True,
    )
    out = broadcast_delivery.with_ad_label(ad, "#реклама")
    assert out.text.startswith("Привет") and out.entities == ad.entities


# --- publishing ----------------------------------------------------------


async def test_options_reach_telegram_and_the_post_is_pinned(session, bot: FakeBot, cache):
    chat = await _channel(session)
    content = Content(type="text", text="Пост", silent=True, protect=True, pin=True)
    message = await broadcast_delivery.publish(bot, session, cache, chat, content)

    (call,) = bot.calls_named("send_message")
    assert call["disable_notification"] is True
    assert call["protect_content"] is True
    (pin,) = bot.calls_named("pin_chat_message")
    assert pin["message_id"] == message.message_id


async def test_a_failed_pin_does_not_undo_the_post(session, bot: FakeBot, cache):
    from aiogram.exceptions import TelegramBadRequest
    from aiogram.methods import PinChatMessage

    chat = await _channel(session)
    bot.fail_next["pin_chat_message"] = TelegramBadRequest(
        method=PinChatMessage(chat_id=CHANNEL, message_id=1), message="not enough rights"
    )
    content = Content(type="text", text="Пост", pin=True)
    assert await broadcast_delivery.publish(bot, session, cache, chat, content) is not None


async def test_an_ad_post_is_recorded_for_statistics(session, bot: FakeBot, cache):
    chat = await _channel(session)
    content = Content(type="text", text="Пост", is_ad=True)
    message = await broadcast_delivery.publish(
        bot, session, cache, chat, content, ad_label="#реклама", broadcast_id=7
    )
    row = await session.scalar(select(AdPost))
    assert (row.chat_tg_id, row.message_id, row.broadcast_id) == (
        CHANNEL,
        message.message_id,
        7,
    )
    assert bot.calls_named("send_message")[0]["text"].endswith("#реклама")


# --- comments off --------------------------------------------------------


def _auto_forward(post_id: int, group_message_id: int = 500):
    """The copy Telegram drops into the discussion group."""
    return make_message(
        chat_id=GROUP,
        message_id=group_message_id,
        user_id=None,
        text="Пост",
        is_automatic_forward=True,
        sender_chat_id=CHANNEL,
        forward_origin={
            "type": "channel",
            "chat": {"id": CHANNEL, "type": "channel", "title": "К"},
            "message_id": post_id,
            "date": int(datetime.now(UTC).timestamp()),
        },
    )


async def test_copy_arriving_after_the_post_is_deleted(session, bot: FakeBot, cache: MemoryCache):
    chat = await _channel(session)
    content = Content(type="text", text="Пост", comments=False)
    message = await broadcast_delivery.publish(bot, session, cache, chat, content)
    assert not bot.calls_named("delete_message")

    assert await comment_control.on_auto_forward(bot, cache, _auto_forward(message.message_id))
    (deleted,) = bot.calls_named("delete_message")
    assert (deleted["chat_id"], deleted["message_id"]) == (GROUP, 500)


async def test_copy_arriving_before_the_post_is_still_deleted(
    session, bot: FakeBot, cache: MemoryCache
):
    """Telegram can deliver the auto-forward while sendMessage is still in
    flight; whoever comes second does the deleting."""
    chat = await _channel(session)
    post_id = 4242
    assert not await comment_control.on_auto_forward(bot, cache, _auto_forward(post_id, 501))
    assert not bot.calls_named("delete_message")

    assert await comment_control.suppress(bot, cache, chat, post_id)
    (deleted,) = bot.calls_named("delete_message")
    assert (deleted["chat_id"], deleted["message_id"]) == (GROUP, 501)


async def test_an_ordinary_post_keeps_its_comments(session, bot: FakeBot, cache: MemoryCache):
    chat = await _channel(session)
    message = await broadcast_delivery.publish(
        bot, session, cache, chat, Content(type="text", text="Пост")
    )
    await comment_control.on_auto_forward(bot, cache, _auto_forward(message.message_id))
    assert not bot.calls_named("delete_message")


# --- ads in the statistics ----------------------------------------------


async def test_ad_summary_compares_reactions_and_counts_the_leavers(session, bot: FakeBot):
    chat = await _channel(session)
    today = datetime(2026, 3, 10, 12, tzinfo=UTC)
    day_from, day_to = (today - timedelta(days=29)).date(), today.date()

    for message_id, is_ad, total in ((10, True, 4), (11, False, 20), (12, False, 8)):
        await stats_record(session, chat, message_id, today)
        await channel_stats.record_reactions(session, _reaction(message_id, total))
        if is_ad:
            await channel_stats.record_ad_post(session, chat, message_id, at=today)

    # Two people left within a day of the ad, one long after.
    for offset in (timedelta(hours=2), timedelta(hours=20), timedelta(days=3)):
        await channel_stats.record_member_event(
            session, chat, 100 + offset.seconds, channel_stats.LEAVE, today + offset
        )

    summary = await channel_stats.ad_summary(session, CHANNEL, day_from, day_to)
    assert summary.posts == 1
    assert summary.avg_reactions == 4.0
    assert summary.avg_reactions_other == 14.0
    assert summary.leaves_after == 2


async def stats_record(session, chat, message_id: int, at):
    from app.services import stats_service

    await stats_service.record_message(
        session,
        chat,
        make_message(
            chat_id=CHANNEL, chat_type="channel", message_id=message_id, user_id=None, date=at
        ),
    )


def _reaction(message_id: int, total: int):
    from aiogram.types import MessageReactionCountUpdated

    return MessageReactionCountUpdated.model_validate(
        {
            "chat": {"id": CHANNEL, "type": "channel", "title": "К"},
            "message_id": message_id,
            "date": int(datetime.now(UTC).timestamp()),
            "reactions": [{"type": {"type": "emoji", "emoji": "👍"}, "total_count": total}],
        }
    )
