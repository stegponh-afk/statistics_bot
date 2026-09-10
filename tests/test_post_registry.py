"""Published posts: the registry behind «изменить», «удалить» and the two
auto-delete triggers."""

from datetime import UTC, datetime, timedelta

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import DeleteMessage
from aiogram.types import Chat as TgChat
from aiogram.types import MessageReactionCountUpdated

from app.database.models import BotStatus, BroadcastKind, BroadcastMessage
from app.handlers.private import broadcast as bc
from app.services import (
    broadcast_delivery,
    broadcast_service,
    channel_stats,
    chat_service,
    user_service,
)
from app.services import post_service as ps
from app.services.broadcast_service import (
    Content,
    format_duration,
    parse_duration,
)
from tests.fakes import FakeBot, make_message, tg_user

CHANNEL = -100_61
OTHER = -100_62


async def _channel(session, tg_id: int = CHANNEL, title: str = "Канал"):
    chat = await chat_service.upsert_chat(session, TgChat(id=tg_id, type="channel", title=title))
    chat.bot_status = BotStatus.ADMINISTRATOR
    chat.timezone = "UTC"
    await session.commit()
    return chat


async def _broadcast(session, content: Content, chats):
    user = await user_service.upsert_user(session, tg_user(7))
    return await broadcast_service.create_broadcast(
        session,
        user,
        kind=BroadcastKind.NOW,
        content=content,
        chat_ids=[c.id for c in chats],
        tz_name="UTC",
    )


def _reaction_update(message_id: int, total: int, chat_id: int = CHANNEL):
    return MessageReactionCountUpdated.model_validate(
        {
            "chat": {"id": chat_id, "type": "channel", "title": "К"},
            "message_id": message_id,
            "date": int(datetime.now(UTC).timestamp()),
            "reactions": [{"type": {"type": "emoji", "emoji": "👍"}, "total_count": total}],
        }
    )


# --- reading the admin's own words ----------------------------------------


def test_duration_accepts_what_an_admin_would_type():
    assert parse_duration("30м") == 30
    assert parse_duration("2ч 30м") == 150
    assert parse_duration("3 дня") == 3 * 24 * 60
    assert parse_duration("1 неделя") == 7 * 24 * 60
    assert parse_duration("90") == 90  # a bare number is minutes
    assert parse_duration("2h") == 120


def test_duration_refuses_nonsense_rather_than_guessing():
    for text in ("", "завтра", "0", "-5", "100 лет"):
        assert parse_duration(text) is None


def test_duration_is_read_back_in_the_same_units():
    assert format_duration(120) == "2 часа"
    assert format_duration(3 * 24 * 60) == "3 дня"
    assert format_duration(90) == "90 минут"
    assert format_duration(None) == "—"


# --- the registry ---------------------------------------------------------


async def test_publishing_records_the_post_and_arms_the_timer(session, bot: FakeBot, cache):
    chat = await _channel(session)
    content = Content(type="text", text="Акция", autodelete_after=60)
    at = datetime(2026, 3, 1, 12, tzinfo=UTC)

    message = await broadcast_delivery.publish(bot, session, cache, chat, content)
    row = await session.get(
        BroadcastMessage, {"chat_tg_id": CHANNEL, "message_id": message.message_id}
    )
    assert row.delete_at is not None and row.deleted_at is None
    assert row.delete_at - row.posted_at == timedelta(minutes=60)
    assert at  # the clock itself is Telegram's; we only check the interval


async def test_a_post_without_autodelete_is_still_recorded(session, bot: FakeBot, cache):
    """It has to be: «изменить» and «удалить» need the id too."""
    chat = await _channel(session)
    message = await broadcast_delivery.publish(
        bot, session, cache, chat, Content(type="text", text="Пост")
    )
    row = await session.get(
        BroadcastMessage, {"chat_tg_id": CHANNEL, "message_id": message.message_id}
    )
    assert row is not None and row.delete_at is None and row.delete_after_reactions is None


# --- auto-delete by time --------------------------------------------------


async def test_the_sweep_deletes_only_what_is_due(session, bot: FakeBot):
    now = datetime(2026, 3, 1, 12, tzinfo=UTC)
    chat = await _channel(session)
    await ps.record(session, chat, 1, Content(type="text", autodelete_after=60), at=now)
    await ps.record(session, chat, 2, Content(type="text", autodelete_after=600), at=now)

    assert await ps.delete_due(bot, session, now + timedelta(minutes=61)) == 1
    (call,) = bot.calls_named("delete_message")
    assert call["message_id"] == 1
    assert (
        await session.get(BroadcastMessage, {"chat_tg_id": CHANNEL, "message_id": 1})
    ).deleted_at
    assert not (
        await session.get(BroadcastMessage, {"chat_tg_id": CHANNEL, "message_id": 2})
    ).deleted_at


async def test_a_refused_deletion_is_disarmed_instead_of_retried_forever(session, bot: FakeBot):
    """No delete rights, or a post too old: Telegram will keep saying no,
    and a minute-by-minute retry would keep asking."""
    now = datetime(2026, 3, 1, 12, tzinfo=UTC)
    chat = await _channel(session)
    await ps.record(session, chat, 1, Content(type="text", autodelete_after=1), at=now)
    bot.fail_always["delete_message"] = TelegramBadRequest(
        method=DeleteMessage(chat_id=CHANNEL, message_id=1), message="not enough rights"
    )

    later = now + timedelta(hours=1)
    assert await ps.delete_due(bot, session, later) == 0
    row = await session.get(BroadcastMessage, {"chat_tg_id": CHANNEL, "message_id": 1})
    # Disarmed, and honestly still marked as standing — because it is.
    assert row.delete_at is None and row.deleted_at is None
    assert await ps.delete_due(bot, session, later) == 0
    assert len(bot.calls_named("delete_message")) == 1


# --- auto-delete by reactions ---------------------------------------------


async def test_the_post_goes_when_it_collects_enough_reactions(session, bot: FakeBot):
    chat = await _channel(session)
    await ps.record(session, chat, 5, Content(type="text", autodelete_reactions=100))

    await channel_stats.record_reactions(session, _reaction_update(5, 99))
    assert await ps.on_reactions(bot, session, CHANNEL, 5) is False
    assert not bot.calls_named("delete_message")

    await channel_stats.record_reactions(session, _reaction_update(5, 100))
    assert await ps.on_reactions(bot, session, CHANNEL, 5) is True
    (call,) = bot.calls_named("delete_message")
    assert (call["chat_id"], call["message_id"]) == (CHANNEL, 5)


async def test_reactions_on_an_ordinary_post_delete_nothing(session, bot: FakeBot):
    chat = await _channel(session)
    await ps.record(session, chat, 6, Content(type="text"))
    await channel_stats.record_reactions(session, _reaction_update(6, 5000))
    assert await ps.on_reactions(bot, session, CHANNEL, 6) is False
    assert not bot.calls_named("delete_message")


# --- what the card shows and does -----------------------------------------


async def test_stats_count_standing_posts_and_their_reactions(session, bot: FakeBot, cache):
    first, second = await _channel(session), await _channel(session, OTHER, "Второй")
    broadcast = await _broadcast(session, Content(type="text", text="Пост"), [first, second])
    await broadcast_delivery.run_broadcast(session, bot, broadcast, cache)

    rows = await ps.messages_of(session, broadcast.id)
    assert len(rows) == 2
    await channel_stats.record_reactions(session, _reaction_update(rows[0].message_id, 12))
    await channel_stats.record_reactions(
        session, _reaction_update(rows[1].message_id, 3, chat_id=OTHER)
    )

    stats = await ps.stats(session, broadcast.id)
    assert (stats.published, stats.deleted, stats.reactions) == (2, 0, 15)

    assert (await ps.delete_all(bot, session, broadcast)).done == 2
    stats = await ps.stats(session, broadcast.id)
    assert (stats.published, stats.deleted) == (0, 2)


async def test_editing_rewrites_every_copy(session, bot: FakeBot, cache):
    first, second = await _channel(session), await _channel(session, OTHER, "Второй")
    broadcast = await _broadcast(session, Content(type="text", text="Было"), [first, second])
    await broadcast_delivery.run_broadcast(session, bot, broadcast, cache)

    result = await ps.edit_all(bot, session, broadcast, Content(type="text", text="Стало"))
    assert (result.done, result.failed) == (2, 0)
    assert {c["text"] for c in bot.calls_named("edit_message_text")} == {"Стало"}


async def test_editing_a_media_post_changes_the_caption(session, bot: FakeBot, cache):
    chat = await _channel(session)
    broadcast = await _broadcast(session, Content(type="photo", file_id="f", text="Было"), [chat])
    await broadcast_delivery.run_broadcast(session, bot, broadcast, cache)

    content = Content(type="photo", file_id="f", text="Стало")
    assert (await ps.edit_all(bot, session, broadcast, content)).done == 1
    (call,) = bot.calls_named("edit_message_caption")
    assert call["caption"] == "Стало"
    assert not bot.calls_named("edit_message_text")


async def test_a_deleted_copy_is_reported_but_does_not_stop_the_rest(session, bot: FakeBot, cache):
    first, second = await _channel(session), await _channel(session, OTHER, "Второй")
    broadcast = await _broadcast(session, Content(type="text", text="Было"), [first, second])
    await broadcast_delivery.run_broadcast(session, bot, broadcast, cache)

    bot.fail_next["edit_message_text"] = TelegramBadRequest(
        method=DeleteMessage(chat_id=CHANNEL, message_id=1), message="message to edit not found"
    )
    result = await ps.edit_all(bot, session, broadcast, Content(type="text", text="Стало"))
    assert (result.done, result.failed) == (1, 1)


# --- the screens ----------------------------------------------------------


async def _admin(session):
    return await user_service.upsert_user(session, tg_user(7))


async def test_the_preview_offers_both_triggers_and_spells_out_the_conditions(
    session, bot: FakeBot
):
    user, chat = await _admin(session), await _channel(session)
    content = Content(type="text", text="П", autodelete_after=60, autodelete_reactions=100)
    data = {"chats": [chat.id], "content": content.to_json()}

    screen = await bc.preview_screen(bot, session, user, data, has_channels=True)
    targets = [b.target for row in screen.rows for b in row]
    assert "bc:autodel" in targets and "bc:autodelr" in targets
    # Two triggers, whichever comes first — said in words on the screen.
    assert "через 1 час" in screen.text and "100 реакций" in screen.text


def test_the_reactions_screen_says_plainly_that_views_are_impossible():
    screen = bc.autodelete_reactions_screen(Content(type="text"))
    assert "просмотр" in screen.text


async def test_the_card_offers_edit_and_takedown_only_once_published(session, bot: FakeBot, cache):
    chat = await _channel(session)
    broadcast = await _broadcast(session, Content(type="text", text="Пост"), [chat])

    def targets_of(screen):
        return [b.target for row in screen.rows for b in row]

    assert not any(
        t.endswith(":edit") for t in targets_of(await bc.card_screen(session, broadcast))
    )

    await broadcast_delivery.run_broadcast(session, bot, broadcast, cache)
    screen = await bc.card_screen(session, broadcast)
    assert f"bc:{broadcast.id}:edit" in targets_of(screen)
    assert f"bc:{broadcast.id}:delposts" in targets_of(screen)
    assert "Стоит в чатах" in screen.text


async def test_editing_from_the_card_keeps_the_ad_mark_out_of_the_stored_text(
    session, bot: FakeBot, cache
):
    """The published copy carries the mark; the stored content must not,
    or the next run of a recurring broadcast would append a second one."""
    user, chat = await _admin(session), await _channel(session)
    broadcast = await _broadcast(session, Content(type="text", text="Было", is_ad=True), [chat])
    await broadcast_delivery.run_broadcast(session, bot, broadcast, cache)

    state = FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=7, user_id=7))
    await state.set_state(bc.BroadcastEdit.text)
    await state.set_data({"broadcast_id": broadcast.id})
    message = make_message(chat_id=7, chat_type="private", user_id=7, text="Стало", bot=bot)

    await bc.on_edit_text(message, session, user, state)

    (call,) = bot.calls_named("edit_message_text")
    assert call["text"] == "Стало\n\n#реклама"
    assert broadcast.content["text"] == "Стало"
    assert await state.get_state() is None
