"""The chat card has to answer «почему ничего не происходит» by itself:
a flag that says ВКЛ while the feature is inert is what sent the admin
looking through logs in the first place."""

from aiogram.types import Chat as TgChat

from app.database.models import BotStatus
from app.handlers.private.my_chats import feature_lines
from app.services import chat_service
from app.texts import ru
from tests.fakes import FakeBot

GROUP = -100_71
CHANNEL = -100_72


async def _group(session, **flags):
    chat = await chat_service.upsert_chat(session, TgChat(id=GROUP, type="supergroup", title="G"))
    chat.bot_status = BotStatus.ADMINISTRATOR
    for key, value in flags.items():
        setattr(chat, key, value)
    await session.commit()
    return chat


def _only(lines: list[str]) -> str:
    assert len(lines) == 1, lines
    return lines[0]


async def test_nothing_enabled_produces_no_lines(session):
    chat = await _group(session)
    assert feature_lines(chat, channels_count=0, comments=None) == []


async def test_join_gate_reports_the_chat_setting_it_cannot_change(session):
    """The switch inside Telegram is invisible to the bot, and without it
    no join request is ever created."""
    chat = await _group(session, join_gate_enabled=True, bot_can_invite=True)
    line = _only(feature_lines(chat, channels_count=1, comments=None))
    assert ru.FEATURE_JOINGATE in line and ru.BLOCK_NOT_BY_REQUEST in line

    chat.join_by_request = True
    line = _only(feature_lines(chat, channels_count=1, comments=None))
    assert line == ru.FEATURE_OK.format(name=ru.FEATURE_JOINGATE)


async def test_join_gate_reports_missing_channels_and_rights_first(session):
    chat = await _group(session, join_gate_enabled=True, join_by_request=True)
    assert ru.BLOCK_NO_CHANNELS in _only(feature_lines(chat, channels_count=0, comments=None))
    assert ru.BLOCK_NO_INVITE in _only(feature_lines(chat, channels_count=1, comments=None))


async def test_forcesub_reports_why_it_does_nothing(session):
    chat = await _group(session, forcesub_enabled=True)
    assert ru.BLOCK_NO_CHANNELS in _only(feature_lines(chat, channels_count=0, comments=None))

    chat.bot_can_delete = False
    assert ru.BLOCK_NO_DELETE in _only(feature_lines(chat, channels_count=2, comments=None))

    chat.bot_can_delete = True
    assert _only(feature_lines(chat, channels_count=2, comments=None)) == ru.FEATURE_OK.format(
        name=ru.FEATURE_FORCESUB
    )


async def test_captcha_without_the_right_is_marked_broken(session):
    chat = await _group(session, captcha_enabled=True, bot_can_restrict=False)
    assert ru.BLOCK_NO_RESTRICT in _only(feature_lines(chat, channels_count=0, comments=None))


async def test_digest_line_shows_when_it_arrives(session):
    chat = await _group(session, digest_enabled=True, digest_time="09:30", digest_period="weekly")
    line = _only(feature_lines(chat, channels_count=0, comments=None))
    assert "09:30" in line and ru.FEATURE_DIGEST_WEEKLY in line


async def test_refresh_chat_flags_picks_up_join_mode_and_discussion_group(session, bot: FakeBot):
    chat = await chat_service.upsert_chat(session, TgChat(id=CHANNEL, type="channel", title="C"))
    assert chat.join_by_request is False

    bot.join_by_request[CHANNEL] = True
    bot.linked_chats[CHANNEL] = -100_99
    await chat_service.refresh_chat_flags(bot, session, chat)
    assert chat.join_by_request is True
    assert chat.linked_chat_tg_id == -100_99

    # Turned off again in Telegram — the card must stop claiming it works.
    bot.join_by_request[CHANNEL] = False
    await chat_service.refresh_chat_flags(bot, session, chat)
    assert chat.join_by_request is False
