"""A half-composed broadcast is kept: leaving the wizard, a stray tap on
«Отмена» or a restart must never cost an admin the post they wrote."""

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat as TgChat

from app.database.models import AdminStatus, BotStatus, BroadcastDraft, BroadcastKind, ChatAdmin
from app.handlers.private import broadcast as bc
from app.services import broadcast_service, chat_service, user_service
from app.texts import ru
from tests.fakes import FakeBot, make_callback, make_message, tg_user

USER_ID = 42
CHANNEL = -100_71


async def _user(session):
    return await user_service.upsert_user(session, tg_user(USER_ID))


async def _channel(session, user):
    chat = await chat_service.upsert_chat(
        session, TgChat(id=CHANNEL, type="channel", title="Канал", username="chan")
    )
    chat.bot_status = BotStatus.ADMINISTRATOR
    chat.added_by_user_id = user.id
    session.add(ChatAdmin(chat_id=chat.id, user_id=user.id, status=AdminStatus.ADMINISTRATOR))
    await session.commit()
    return chat


def _state() -> FSMContext:
    return FSMContext(
        storage=MemoryStorage(),
        key=StorageKey(bot_id=1, chat_id=USER_ID, user_id=USER_ID),
    )


def _callback(bot: FakeBot, data: str):
    return make_callback(
        make_message(chat_id=USER_ID, chat_type="private", bot=bot),
        data,
        user_id=USER_ID,
        bot=bot,
    )


async def _composed(session, state: FSMContext, chat) -> None:
    """The wizard as it stands right before «Когда отправить?»."""
    await state.set_state(bc.BroadcastNew.schedule)
    await state.set_data({"chats": [chat.id], "content": {"type": "text", "text": "Скидка 20%"}})


# --- keeping it ------------------------------------------------------------


async def test_leaving_the_wizard_keeps_the_draft(session, bot: FakeBot):
    user = await _user(session)
    chat = await _channel(session, user)
    state = _state()
    await _composed(session, state, chat)

    await bc.cb_menu(_callback(bot, "bc:cancel"), session, user, state)

    draft = await session.get(BroadcastDraft, user.id)
    assert draft.step == "schedule"
    assert draft.data["content"]["text"] == "Скидка 20%"
    assert await state.get_state() is None  # the wizard itself is over


async def test_the_menu_offers_the_draft_back(session, bot: FakeBot):
    user = await _user(session)
    chat = await _channel(session, user)
    state = _state()
    await _composed(session, state, chat)
    await bc.cb_menu(_callback(bot, "bc:cancel"), session, user, state)

    screen = await bc.menu_screen(session, user)
    assert "Скидка 20%" in screen.text
    targets = [b.target for row in screen.rows for b in row]
    assert "bc:draft" in targets and "bc:draft:del" in targets


async def test_an_empty_wizard_leaves_no_draft(session, bot: FakeBot):
    user = await _user(session)
    state = _state()
    await state.set_state(bc.BroadcastNew.targets)
    await state.set_data({"chats": []})

    await bc.cb_menu(_callback(bot, "bc:cancel"), session, user, state)
    assert await session.get(BroadcastDraft, user.id) is None


# --- getting it back -------------------------------------------------------


async def test_resuming_shows_the_post_again_and_restores_the_wizard(session, bot: FakeBot):
    user = await _user(session)
    chat = await _channel(session, user)
    await broadcast_service.save_draft(
        session, user, "schedule", {"chats": [chat.id], "content": {"type": "text", "text": "Пост"}}
    )
    state = _state()

    await bc.cb_draft_resume(_callback(bot, "bc:draft"), session, user, state)

    assert await state.get_state() == bc.BroadcastNew.schedule.state
    assert (await state.get_data())["chats"] == [chat.id]
    # The post itself is re-sent above the preview: after a day away
    # nobody remembers what they had written.
    assert any(c["text"] == "Пост" for c in bot.calls_named("send_message"))


async def test_resuming_an_earlier_step_returns_to_that_step(session, bot: FakeBot):
    user = await _user(session)
    chat = await _channel(session, user)
    await broadcast_service.save_draft(session, user, "message", {"chats": [chat.id]})
    state = _state()

    await bc.cb_draft_resume(_callback(bot, "bc:draft"), session, user, state)
    assert await state.get_state() == bc.BroadcastNew.message.state


async def test_a_deleted_draft_says_so_instead_of_failing(session, bot: FakeBot):
    user = await _user(session)
    await _channel(session, user)
    await bc.cb_draft_resume(_callback(bot, "bc:draft"), session, user, _state())
    alert = bot.calls_named("answer_callback_query")[0]
    assert alert["text"] == ru.BROADCAST_DRAFT_GONE and alert["show_alert"] is True


# --- losing it, but only on purpose ---------------------------------------


async def test_a_new_broadcast_asks_before_overwriting_the_draft(session, bot: FakeBot):
    user = await _user(session)
    chat = await _channel(session, user)
    await broadcast_service.save_draft(
        session, user, "schedule", {"chats": [chat.id], "content": {"type": "text", "text": "Пост"}}
    )
    state = _state()

    await bc.cb_new(_callback(bot, "bc:new"), session, user, state)
    assert await session.get(BroadcastDraft, user.id) is not None
    assert await state.get_state() is None  # not started yet — the admin chooses

    await bc.cb_new(_callback(bot, "bc:new:fresh"), session, user, state)
    assert await session.get(BroadcastDraft, user.id) is None
    assert await state.get_state() == bc.BroadcastNew.targets.state


async def test_deleting_the_draft_removes_it(session, bot: FakeBot):
    user = await _user(session)
    await _channel(session, user)
    await broadcast_service.save_draft(session, user, "message", {"chats": [1]})

    await bc.cb_draft_delete(_callback(bot, "bc:draft:del"), session, user, _state())
    assert await session.get(BroadcastDraft, user.id) is None


async def test_a_sent_broadcast_stops_being_a_draft(session, bot: FakeBot):
    user = await _user(session)
    chat = await _channel(session, user)
    state = _state()
    await _composed(session, state, chat)
    await broadcast_service.save_draft(session, user, "schedule", await state.get_data())

    await bc._create(session, user, state, BroadcastKind.NOW)
    assert await session.get(BroadcastDraft, user.id) is None


# --- stepping back ---------------------------------------------------------


async def test_back_moves_one_step_and_keeps_what_was_composed(session, bot: FakeBot):
    user = await _user(session)
    chat = await _channel(session, user)
    state = _state()
    await state.set_state(bc.BroadcastNew.buttons)
    await state.set_data({"chats": [chat.id], "content": {"type": "text", "text": "Пост"}})

    await bc.cb_back(_callback(bot, "bc:b:message"), session, user, state)
    assert await state.get_state() == bc.BroadcastNew.message.state
    assert (await state.get_data())["content"]["text"] == "Пост"

    await bc.cb_back(_callback(bot, "bc:b:targets"), session, user, state)
    assert await state.get_state() == bc.BroadcastNew.targets.state


async def test_back_on_a_stale_screen_lands_in_the_menu(session, bot: FakeBot):
    """After a restart the FSM is empty; the button must not explode."""
    user = await _user(session)
    await _channel(session, user)
    state = _state()

    await bc.cb_back(_callback(bot, "bc:b:schedule"), session, user, state)
    assert await state.get_state() is None


async def test_every_wizard_screen_offers_a_way_back(session, bot: FakeBot):
    user = await _user(session)
    chat = await _channel(session, user)
    screens = [
        await bc.targets_screen(session, user, {chat.id}),
        bc.message_screen(),
        bc.buttons_screen(),
        bc.days_screen({0}),
    ]
    for screen in screens:
        targets = [b.target for row in screen.rows for b in row]
        assert "bc:cancel" in targets
    for screen in screens[1:]:
        assert any(t.startswith("bc:b:") for t in [b.target for row in screen.rows for b in row])
