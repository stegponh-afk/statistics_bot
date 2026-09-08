"""Comments under a channel post cannot be switched per post, so the
preview screen explains what will happen instead of pretending to offer
a toggle."""

from aiogram.types import Chat as TgChat

from app.database.models import BotStatus
from app.handlers.private.broadcast import _comments_note
from app.services import chat_service
from app.texts import ru
from tests.fakes import FakeBot

WITH_COMMENTS = -100_81
WITHOUT_COMMENTS = -100_82
GROUP = -100_83


async def _chat(session, tg_id: int, kind: str, title: str):
    chat = await chat_service.upsert_chat(session, TgChat(id=tg_id, type=kind, title=title))
    chat.bot_status = BotStatus.ADMINISTRATOR
    await session.commit()
    return chat


async def test_note_splits_channels_by_whether_a_discussion_group_is_attached(
    session, bot: FakeBot
):
    talkative = await _chat(session, WITH_COMMENTS, "channel", "Болталка")
    silent = await _chat(session, WITHOUT_COMMENTS, "channel", "Молчун")
    bot.linked_chats[WITH_COMMENTS] = -100_90

    note = await _comments_note(bot, session, [talkative.id, silent.id])
    assert "Болталка" in note and "Молчун" in note
    assert ru.BROADCAST_COMMENTS_ON.format(titles="Болталка") in note
    assert "Обсуждение" in note  # the how-to for the channel that has none


async def test_groups_alone_produce_no_note(session, bot: FakeBot):
    group = await _chat(session, GROUP, "supergroup", "Клуб")
    assert await _comments_note(bot, session, [group.id]) == ""
    assert await _comments_note(bot, session, []) == ""
