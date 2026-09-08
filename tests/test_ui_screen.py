from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage

from app.ui import Btn, Screen, edit_ephemeral, reply_to_command, respond, send, send_ephemeral
from tests.fakes import FakeBot, make_callback, make_message


def _bad_request(msg: str = "Bad Request: nope") -> TelegramBadRequest:
    return TelegramBadRequest(method=SendMessage(chat_id=1, text="x"), message=msg)


def _screen() -> Screen:
    return Screen("📊 <b>Тест</b>\nтело", rows=[[Btn("A", "a")], [Btn("Назад", "back")]])


async def test_send_uses_rich_message_and_embeds_buttons_in_new_style(bot: FakeBot):
    await send(bot, 1, _screen(), rich_buttons=True)
    (call,) = bot.calls_named("send_rich_message")
    assert call["reply_markup"] is None
    assert any(b.type == "buttons" for b in call["rich_message"].blocks)


async def test_send_old_style_keeps_keyboard_below(bot: FakeBot):
    await send(bot, 1, _screen(), rich_buttons=False)
    (call,) = bot.calls_named("send_rich_message")
    assert call["reply_markup"] is not None
    assert not any(b.type == "buttons" for b in call["rich_message"].blocks)


async def test_send_falls_back_to_text_when_rich_is_rejected(bot: FakeBot):
    bot.fail_next["send_rich_message"] = _bad_request()
    await send(bot, 1, _screen(), rich_buttons=True)
    (call,) = bot.calls_named("send_message")
    assert "<b>Тест</b>" in call["text"]
    assert call["reply_markup"] is not None


async def test_send_ephemeral_targets_the_receiver(bot: FakeBot):
    sent = await send_ephemeral(bot, -1, 42, _screen(), rich_buttons=True)
    (call,) = bot.calls_named("send_rich_message")
    params = call["ephemeral_message_parameters"]
    assert params.receiver_user_id == 42
    assert params.callback_query_id is None
    assert sent is not None and sent.ephemeral_message_id == 7


async def test_send_ephemeral_replies_to_an_ephemeral_command(bot: FakeBot):
    incoming = make_message(ephemeral_message_id=55, bot=bot)
    await send_ephemeral(bot, -1, 42, _screen(), rich_buttons=True, reply_to=incoming)
    (call,) = bot.calls_named("send_rich_message")
    assert call["reply_parameters"].ephemeral_message_id == 55


async def test_send_ephemeral_never_raises(bot: FakeBot):
    bot.fail_next["send_rich_message"] = _bad_request()
    bot.fail_next["send_message"] = _bad_request()
    assert await send_ephemeral(bot, -1, 42, _screen(), rich_buttons=True) is None


async def test_edit_ephemeral_falls_back_to_text(bot: FakeBot):
    bot.fail_next["edit_ephemeral_message_text"] = _bad_request()
    assert await edit_ephemeral(bot, -1, 42, 7, _screen(), rich_buttons=True) is True
    calls = bot.calls_named("edit_ephemeral_message_text")
    assert "rich_message" in calls[0] and calls[1]["text"].startswith("📊")


async def test_respond_edits_an_ephemeral_message_in_place(bot: FakeBot):
    message = make_message(ephemeral_message_id=7, receiver_user_id=42, bot=bot)
    callback = make_callback(message, "a", bot=bot)
    await respond(callback, _screen(), rich_buttons=True)
    (call,) = bot.calls_named("edit_ephemeral_message_text")
    assert call["receiver_user_id"] == 42 and call["ephemeral_message_id"] == 7
    assert bot.calls_named("answer_callback_query")


async def test_respond_to_a_public_group_post_sends_a_private_replacement(bot: FakeBot):
    message = make_message(bot=bot)
    callback = make_callback(message, "a", bot=bot)
    await respond(callback, _screen(), rich_buttons=True)
    (call,) = bot.calls_named("send_rich_message")
    params = call["ephemeral_message_parameters"]
    assert params.callback_query_id == "cb1"
    assert params.replace_callback_query_message is True
    # The callback is consumed by the ephemeral send; no separate answer.
    assert not bot.calls_named("answer_callback_query")


async def test_respond_in_private_edits_the_message(bot: FakeBot):
    message = make_message(chat_id=42, chat_type="private", bot=bot)
    callback = make_callback(message, "a", bot=bot)
    await respond(callback, _screen(), rich_buttons=True)
    (call,) = bot.calls_named("edit_message_text")
    assert call["chat_id"] == 42
    assert bot.calls_named("answer_callback_query")


async def test_reply_to_command_is_ephemeral_in_groups_and_deletes_public_command(bot: FakeBot):
    message = make_message(message_id=33, bot=bot)
    await reply_to_command(message, _screen(), rich_buttons=True, delete_public=True)
    (send_call,) = bot.calls_named("send_rich_message")
    assert send_call["ephemeral_message_parameters"].receiver_user_id == 42
    (delete_call,) = bot.calls_named("delete_message")
    assert delete_call["message_id"] == 33


async def test_reply_to_ephemeral_command_does_not_try_to_delete_it(bot: FakeBot):
    message = make_message(ephemeral_message_id=5, bot=bot)
    await reply_to_command(message, _screen(), rich_buttons=True, delete_public=True)
    assert not bot.calls_named("delete_message")


async def test_reply_to_command_in_private_is_a_normal_message(bot: FakeBot):
    message = make_message(chat_id=42, chat_type="private", bot=bot)
    await reply_to_command(message, _screen(), rich_buttons=True)
    (call,) = bot.calls_named("send_rich_message")
    assert call.get("ephemeral_message_parameters") is None
