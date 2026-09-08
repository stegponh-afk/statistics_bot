from datetime import UTC, datetime, timedelta

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import ApproveChatJoinRequest
from aiogram.types import Chat as TgChat
from aiogram.types import ChatMemberLeft, ChatMemberMember
from sqlalchemy import select

from app.cache import MemoryCache
from app.database.models import BotStatus, JoinRequest
from app.services import chat_service, forcesub_service, join_request_service
from tests.fakes import FakeBot, tg_user

GROUP = -100_61
CHANNEL = -100_62
APPLICANT = 55
# The temporary private chat Telegram opens for a join request.
USER_CHAT = 9_000_000_055


async def _setup(session, cache: MemoryCache, *, gate: bool = True, bind: bool = True):
    group = await chat_service.upsert_chat(
        session, TgChat(id=GROUP, type="supergroup", title="Клуб")
    )
    group.bot_status = BotStatus.ADMINISTRATOR
    group.bot_can_invite = True
    group.join_gate_enabled = gate
    channel = await chat_service.upsert_chat(
        session, TgChat(id=CHANNEL, type="channel", title="Канал", username="chan")
    )
    channel.bot_status = BotStatus.ADMINISTRATOR
    await session.commit()
    if bind:
        await forcesub_service.toggle_required_channel(session, cache, group, channel)
    return group, channel


def _subscribed(bot: FakeBot, yes: bool) -> None:
    bot.members[(CHANNEL, APPLICANT)] = (
        ChatMemberMember(user=tg_user(APPLICANT))
        if yes
        else ChatMemberLeft(user=tg_user(APPLICANT))
    )


async def _pending(session) -> list[JoinRequest]:
    return list(await session.scalars(select(JoinRequest)))


# --- an incoming request --------------------------------------------------


async def test_subscribed_applicant_is_approved_at_once(session, bot: FakeBot, cache):
    group, _ = await _setup(session, cache)
    _subscribed(bot, True)

    assert await join_request_service.handle_request(
        bot, session, cache, group, APPLICANT, USER_CHAT
    )
    assert bot.calls_named("approve_chat_join_request") == [
        {"chat_id": GROUP, "user_id": APPLICANT}
    ]
    assert await _pending(session) == []
    # The confirmation goes to the temporary chat, not the user id.
    assert bot.calls_named("send_rich_message")[-1]["chat_id"] == USER_CHAT


async def test_unsubscribed_applicant_waits_and_is_told_what_to_do(session, bot: FakeBot, cache):
    group, _ = await _setup(session, cache)
    _subscribed(bot, False)

    assert not await join_request_service.handle_request(
        bot, session, cache, group, APPLICANT, USER_CHAT
    )
    assert not bot.calls_named("approve_chat_join_request")

    (row,) = await _pending(session)
    assert (row.chat_id, row.user_tg_id, row.user_chat_id) == (group.id, APPLICANT, USER_CHAT)

    prompt = bot.calls_named("send_rich_message")[-1]
    assert prompt["chat_id"] == USER_CHAT
    buttons = [
        b for blk in prompt["rich_message"].blocks if blk.type == "buttons" for b in blk.buttons
    ]
    assert buttons[0].url == "https://t.me/chan"
    assert buttons[-1].callback_data == f"jr:check:{GROUP}"


async def test_gate_off_or_no_channels_leaves_the_request_alone(session, bot: FakeBot, cache):
    group, _ = await _setup(session, cache, gate=False)
    assert not await join_request_service.handle_request(
        bot, session, cache, group, APPLICANT, USER_CHAT
    )

    group.join_gate_enabled = True
    await session.commit()
    for row in await session.scalars(select(forcesub_service.GroupRequiredChannel)):
        await session.delete(row)
    await session.commit()
    assert not await join_request_service.handle_request(
        bot, session, cache, group, APPLICANT, USER_CHAT
    )
    assert not bot.calls and await _pending(session) == []


async def test_admins_and_the_whitelist_skip_the_check(session, bot: FakeBot, cache):
    group, _ = await _setup(session, cache)
    assert await join_request_service.handle_request(
        bot, session, cache, group, APPLICANT, USER_CHAT, is_chat_admin=True
    )
    assert not bot.calls_named("get_chat_member")

    await forcesub_service.add_to_whitelist(session, cache, group, 66, None)
    assert await join_request_service.handle_request(bot, session, cache, group, 66, None)
    assert len(bot.calls_named("approve_chat_join_request")) == 2


# --- deciding again -------------------------------------------------------


async def test_recheck_approves_once_the_applicant_subscribes(session, bot: FakeBot, cache):
    group, _ = await _setup(session, cache)
    _subscribed(bot, False)
    await join_request_service.handle_request(bot, session, cache, group, APPLICANT, USER_CHAT)

    assert not await join_request_service.recheck(bot, session, cache, group, APPLICANT, force=True)
    assert len(await _pending(session)) == 1

    _subscribed(bot, True)
    assert await join_request_service.recheck(bot, session, cache, group, APPLICANT, force=True)
    assert await _pending(session) == []
    assert bot.calls_named("send_rich_message")[-1]["chat_id"] == USER_CHAT


async def test_recheck_all_lets_in_everyone_waiting_on_that_channel(session, bot: FakeBot, cache):
    group, _ = await _setup(session, cache)
    _subscribed(bot, False)
    await join_request_service.handle_request(bot, session, cache, group, APPLICANT, USER_CHAT)

    _subscribed(bot, True)
    assert await join_request_service.recheck_all(bot, session, cache, APPLICANT) == 1
    assert await _pending(session) == []


async def test_switching_the_gate_off_releases_whoever_is_waiting(session, bot: FakeBot, cache):
    group, _ = await _setup(session, cache)
    _subscribed(bot, False)
    await join_request_service.handle_request(bot, session, cache, group, APPLICANT, USER_CHAT)

    group.join_gate_enabled = False
    await session.commit()
    assert await join_request_service.recheck(bot, session, cache, group, APPLICANT, force=True)
    assert await _pending(session) == []


async def test_a_request_telegram_refuses_stops_being_tracked(session, bot: FakeBot, cache):
    """An admin who answered the request by hand leaves no update behind —
    the row must not stay forever."""
    group, _ = await _setup(session, cache)
    _subscribed(bot, False)
    await join_request_service.handle_request(bot, session, cache, group, APPLICANT, USER_CHAT)

    bot.fail_next["approve_chat_join_request"] = TelegramBadRequest(
        method=ApproveChatJoinRequest(chat_id=GROUP, user_id=APPLICANT),
        message="USER_ALREADY_PARTICIPANT",
    )
    _subscribed(bot, True)
    assert not await join_request_service.recheck(bot, session, cache, group, APPLICANT, force=True)
    assert await _pending(session) == []


async def test_purge_drops_only_stale_rows(session, bot: FakeBot, cache):
    group, _ = await _setup(session, cache)
    await join_request_service.remember(session, group, APPLICANT, USER_CHAT)
    (row,) = await _pending(session)
    row.requested_at = datetime.now(UTC) - timedelta(days=31)
    await session.commit()
    assert await join_request_service.purge_older_than(session) == 1

    await join_request_service.remember(session, group, APPLICANT, USER_CHAT)
    assert await join_request_service.purge_older_than(session) == 0
    assert len(await _pending(session)) == 1
