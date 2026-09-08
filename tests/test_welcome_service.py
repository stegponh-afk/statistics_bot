from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendMessage
from aiogram.types import Chat as TgChat

from app.cache import MemoryCache
from app.database.models import BotStatus
from app.services import chat_service, welcome_service
from app.services.broadcast_service import Content
from tests.fakes import FakeBot

GROUP = -100_31
NEWCOMER = 42


async def _group(session, **flags):
    chat = await chat_service.upsert_chat(
        session, TgChat(id=GROUP, type="supergroup", title="Клуб")
    )
    chat.bot_status = BotStatus.ADMINISTRATOR
    chat.bot_can_restrict = True
    for key, value in flags.items():
        setattr(chat, key, value)
    await session.commit()
    return chat


def _refused(method: str) -> dict:
    return {
        "send_rich_message": TelegramBadRequest(
            method=SendMessage(chat_id=GROUP, text="x"), message="rich not supported"
        ),
        "send_message": TelegramForbiddenError(
            method=SendMessage(chat_id=GROUP, text="x"), message="bot was blocked"
        ),
    }[method]


# --- placeholders ---------------------------------------------------------


def test_render_substitutes_name_and_title():
    content = Content(type="text", text="Привет, {name}! Это {title}.")
    out = welcome_service.render(content, name="Аня", title="Клуб")
    assert out.text == "Привет, Аня! Это Клуб."
    assert content.text == "Привет, {name}! Это {title}."  # the stored copy is untouched


def test_render_escapes_html_only_for_html_content():
    html_content = Content(type="text", text="<b>{name}</b>", parse_mode="HTML")
    assert welcome_service.render(html_content, name="A<b", title="T").text == "<b>A&lt;b</b>"
    plain = Content(type="text", text="{name}")
    assert welcome_service.render(plain, name="A<b", title="T").text == "A<b"


def test_render_leaves_entity_formatted_text_alone():
    """Substituting would shift every entity offset onto wrong characters."""
    content = Content(
        type="text",
        text="Привет, {name}",
        entities=[{"type": "bold", "offset": 0, "length": 6}],
    )
    assert welcome_service.render(content, name="Аня", title="Клуб").text == "Привет, {name}"


# --- the greeting ---------------------------------------------------------


async def test_welcome_is_sent_only_to_the_newcomer(session, bot: FakeBot, cache: MemoryCache):
    chat = await _group(
        session,
        welcome_enabled=True,
        welcome_content=Content(type="text", text="Привет, {name}!").to_json(),
    )
    await welcome_service.on_join(bot, cache, chat, NEWCOMER, "Аня")

    (call,) = bot.calls_named("send_message")
    assert call["text"] == "Привет, Аня!"
    assert call["ephemeral_message_parameters"].receiver_user_id == NEWCOMER
    assert not bot.calls_named("restrict_chat_member")


async def test_public_welcome_carries_no_ephemeral_parameters(
    session, bot: FakeBot, cache: MemoryCache
):
    chat = await _group(
        session,
        welcome_enabled=True,
        welcome_ephemeral=False,
        welcome_content=Content(type="photo", file_id="fid", text="Добро пожаловать").to_json(),
    )
    await welcome_service.on_join(bot, cache, chat, NEWCOMER, "Аня")

    (call,) = bot.calls_named("send_photo")
    assert call["media"] == "fid" and call["ephemeral_message_parameters"] is None


async def test_disabled_welcome_sends_nothing(session, bot: FakeBot, cache: MemoryCache):
    chat = await _group(
        session, welcome_enabled=False, welcome_content=Content(type="text", text="hi").to_json()
    )
    await welcome_service.on_join(bot, cache, chat, NEWCOMER, "Аня")
    assert not bot.calls


# --- the captcha ----------------------------------------------------------


async def test_captcha_mutes_and_challenges_the_newcomer(session, bot: FakeBot, cache: MemoryCache):
    chat = await _group(
        session,
        captcha_enabled=True,
        welcome_enabled=True,
        welcome_content=Content(type="text", text="Привет!").to_json(),
    )
    await welcome_service.on_join(bot, cache, chat, NEWCOMER, "Аня")

    (chat_id, user_id, permissions) = bot.restrictions[0]
    assert (chat_id, user_id) == (GROUP, NEWCOMER)
    assert permissions.can_send_messages is False
    assert len(bot.restrictions) == 1  # muted, not un-muted

    (challenge,) = bot.calls_named("send_rich_message")
    assert challenge["ephemeral_message_parameters"].receiver_user_id == NEWCOMER
    # The greeting waits until they prove they are human.
    assert not bot.calls_named("send_message")
    assert await cache.get(welcome_service.captcha_key(GROUP, NEWCOMER)) == "1"


async def test_captcha_without_the_right_falls_through_to_the_greeting(
    session, bot: FakeBot, cache: MemoryCache
):
    chat = await _group(
        session,
        captcha_enabled=True,
        bot_can_restrict=False,
        welcome_enabled=True,
        welcome_content=Content(type="text", text="Привет!").to_json(),
    )
    await welcome_service.on_join(bot, cache, chat, NEWCOMER, "Аня")
    assert not bot.calls_named("restrict_chat_member")
    assert bot.calls_named("send_message")


async def test_undeliverable_challenge_never_leaves_the_newcomer_muted(
    session, bot: FakeBot, cache: MemoryCache
):
    chat = await _group(session, captcha_enabled=True)
    bot.fail_always["send_rich_message"] = _refused("send_rich_message")
    bot.fail_always["send_message"] = _refused("send_message")

    await welcome_service.on_join(bot, cache, chat, NEWCOMER, "Аня")

    assert len(bot.restrictions) == 2
    assert bot.restrictions[0][2].can_send_messages is False
    assert bot.restrictions[1][2].can_send_messages is True
    assert await cache.get(welcome_service.captcha_key(GROUP, NEWCOMER)) is None


async def test_pass_captcha_only_works_for_a_pending_challenge(
    session, bot: FakeBot, cache: MemoryCache
):
    chat = await _group(session, captcha_enabled=True)
    assert not await welcome_service.pass_captcha(bot, cache, chat, NEWCOMER)
    assert not bot.restrictions

    await welcome_service.on_join(bot, cache, chat, NEWCOMER, "Аня")
    assert await welcome_service.pass_captcha(bot, cache, chat, NEWCOMER)
    assert bot.restrictions[-1][2].can_send_messages is True
    # The key is spent: a second press changes nothing.
    assert not await welcome_service.pass_captcha(bot, cache, chat, NEWCOMER)


async def test_text_screen_is_offered_only_for_a_plain_greeting(session):
    chat = await _group(
        session,
        welcome_enabled=True,
        welcome_content=Content(type="text", text="Привет, {name}").to_json(),
    )
    screen = welcome_service.text_screen(chat, "Аня")
    assert screen is not None and screen.text == "Привет, Аня"

    chat.welcome_content = Content(type="photo", file_id="f", text="hi").to_json()
    assert welcome_service.text_screen(chat, "Аня") is None

    chat.welcome_content = Content(
        type="text", text="hi", buttons=[[{"text": "A", "url": "https://a"}]]
    ).to_json()
    assert welcome_service.text_screen(chat, "Аня") is None
