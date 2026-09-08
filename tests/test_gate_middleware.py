from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import DeleteMessage
from aiogram.types import Chat as TgChat
from aiogram.types import ChatMemberLeft, ChatMemberMember
from sqlalchemy import select

from app.database.models import User
from app.middlewares.gate import ForceSubGateMiddleware
from app.services import chat_service, forcesub_service
from tests.fakes import FakeBot, FakeClock, make_message, tg_user

GROUP = -100_1
CHANNEL = -100_2
USER = 42


async def _setup(session, cache, *, enabled: bool = True):
    group = await chat_service.upsert_chat(session, TgChat(id=GROUP, type="supergroup", title="G"))
    channel = await chat_service.upsert_chat(session, TgChat(id=CHANNEL, type="channel", title="C"))
    channel.username = "chan"
    group.bot_can_delete = True
    group.forcesub_enabled = enabled
    await session.commit()
    await forcesub_service.toggle_required_channel(session, cache, group, channel)
    return group, channel


class Handler:
    def __init__(self) -> None:
        self.called = 0

    async def __call__(self, event, data):
        self.called += 1
        return "handled"


async def _run(mw, bot, session, group, message, *, is_admin=False, user=None):
    handler = Handler()
    data = {
        "session": session,
        "bot": bot,
        "chat_row": group,
        "is_chat_admin": is_admin,
        "user": user,
    }
    result = await mw(handler, message, data)
    return handler, result


async def test_unsubscribed_message_is_deleted_and_prompted_once(session, cache, bot: FakeBot):
    group, _ = await _setup(session, cache)
    bot.members[(CHANNEL, USER)] = ChatMemberLeft(user=tg_user(USER))
    mw = ForceSubGateMiddleware(cache)

    handler, result = await _run(
        mw, bot, session, group, make_message(chat_id=GROUP, message_id=1, bot=bot)
    )
    assert handler.called == 0 and result is None
    assert bot.calls_named("delete_message")[0]["message_id"] == 1
    (prompt,) = bot.calls_named("send_rich_message")
    assert prompt["ephemeral_message_parameters"].receiver_user_id == USER
    buttons = [
        b for blk in prompt["rich_message"].blocks if blk.type == "buttons" for b in blk.buttons
    ]
    assert buttons[0].url == "https://t.me/chan"
    assert buttons[-1].callback_data == f"gate:check:{GROUP}"

    # Second message within the cooldown: deleted again, no second prompt.
    handler, _ = await _run(
        mw, bot, session, group, make_message(chat_id=GROUP, message_id=2, bot=bot)
    )
    assert handler.called == 0
    assert len(bot.calls_named("delete_message")) == 2
    assert len(bot.calls_named("send_rich_message")) == 1


async def test_prompt_again_after_cooldown(session, cache, bot: FakeBot, clock: FakeClock):
    group, _ = await _setup(session, cache)
    bot.members[(CHANNEL, USER)] = ChatMemberLeft(user=tg_user(USER))
    mw = ForceSubGateMiddleware(cache)
    await _run(mw, bot, session, group, make_message(chat_id=GROUP, message_id=1, bot=bot))
    clock.advance(31)
    await _run(mw, bot, session, group, make_message(chat_id=GROUP, message_id=2, bot=bot))
    assert len(bot.calls_named("send_rich_message")) == 2


async def test_subscribed_admin_and_whitelisted_pass(session, cache, bot: FakeBot):
    group, _ = await _setup(session, cache)
    mw = ForceSubGateMiddleware(cache)

    bot.members[(CHANNEL, USER)] = ChatMemberMember(user=tg_user(USER))
    handler, result = await _run(mw, bot, session, group, make_message(chat_id=GROUP, bot=bot))
    assert handler.called == 1 and result == "handled"

    bot.members[(CHANNEL, 7)] = ChatMemberLeft(user=tg_user(7))
    handler, _ = await _run(
        mw, bot, session, group, make_message(chat_id=GROUP, user_id=7, bot=bot), is_admin=True
    )
    assert handler.called == 1

    await forcesub_service.add_to_whitelist(session, cache, group, 7, None)
    handler, _ = await _run(
        mw, bot, session, group, make_message(chat_id=GROUP, user_id=7, bot=bot)
    )
    assert handler.called == 1
    assert not bot.calls_named("delete_message")


async def test_ephemeral_command_is_not_deleted_but_still_gated(session, cache, bot: FakeBot):
    group, _ = await _setup(session, cache)
    bot.members[(CHANNEL, USER)] = ChatMemberLeft(user=tg_user(USER))
    mw = ForceSubGateMiddleware(cache)
    message = make_message(chat_id=GROUP, ephemeral_message_id=9, text="/me", bot=bot)
    handler, _ = await _run(mw, bot, session, group, message)
    assert handler.called == 0
    assert not bot.calls_named("delete_message")
    assert len(bot.calls_named("send_rich_message")) == 1


async def test_gate_off_or_no_channels_passes_through(session, cache, bot: FakeBot):
    group, channel = await _setup(session, cache, enabled=False)
    mw = ForceSubGateMiddleware(cache)
    handler, _ = await _run(mw, bot, session, group, make_message(chat_id=GROUP, bot=bot))
    assert handler.called == 1 and not bot.calls

    group.forcesub_enabled = True
    await session.commit()
    await forcesub_service.toggle_required_channel(session, cache, group, channel)  # unbind
    handler, _ = await _run(mw, bot, session, group, make_message(chat_id=GROUP, bot=bot))
    assert handler.called == 1 and not bot.calls


async def test_lost_delete_right_disables_gate_and_notifies(session, cache, bot: FakeBot):
    group, _ = await _setup(session, cache)
    admin = User(telegram_id=1, full_name="Admin", started_bot=True)
    session.add(admin)
    await session.flush()
    from app.database.models import AdminStatus, ChatAdmin

    session.add(ChatAdmin(chat_id=group.id, user_id=admin.id, status=AdminStatus.CREATOR))
    await session.commit()

    bot.members[(CHANNEL, USER)] = ChatMemberLeft(user=tg_user(USER))
    bot.fail_next["delete_message"] = TelegramBadRequest(
        method=DeleteMessage(chat_id=GROUP, message_id=1), message="not enough rights"
    )
    mw = ForceSubGateMiddleware(cache)
    handler, _ = await _run(mw, bot, session, group, make_message(chat_id=GROUP, bot=bot))
    assert handler.called == 1  # passed through
    assert group.forcesub_enabled is False and group.bot_can_delete is False
    dm = bot.calls_named("send_message")
    assert dm and dm[0]["chat_id"] == 1
    assert (await session.scalar(select(User).where(User.telegram_id == 1))).started_bot
