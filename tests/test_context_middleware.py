from aiogram.types import ChatMemberAdministrator, ChatMemberOwner, Update
from sqlalchemy import select

from app.database.models import BotStatus, Chat, ChatAdmin
from app.middlewares.context import ChatContextMiddleware
from app.services import chat_service
from tests.fakes import FakeBot, make_message, tg_user

CHANNEL = -100_5


def _bot_admin(bot_id: int) -> ChatMemberAdministrator:
    rights = {
        name: False
        for name in (
            "can_be_edited",
            "is_anonymous",
            "can_manage_chat",
            "can_delete_messages",
            "can_manage_video_chats",
            "can_restrict_members",
            "can_promote_members",
            "can_change_info",
            "can_invite_users",
            "can_post_stories",
            "can_edit_stories",
            "can_delete_stories",
            "can_send_welcome_messages",
        )
    }
    return ChatMemberAdministrator(user=tg_user(bot_id, "Bot", is_bot=True), **rights)


async def _call(mw, session, bot, message):
    seen = {}

    async def handler(event, data):
        seen.update(data)
        return "ok"

    update = Update(update_id=1, channel_post=message)
    data = {"session": session, "bot": bot, "event_chat": message.chat, "event_from_user": None}
    await mw(handler, update, data)
    return seen


async def test_unknown_channel_seen_via_post_is_discovered(session, cache, bot: FakeBot):
    bot.members[(CHANNEL, bot.id)] = _bot_admin(bot.id)
    bot.administrators[CHANNEL] = [
        ChatMemberOwner(user=tg_user(1, "Owner"), is_anonymous=False),
        _bot_admin(bot.id),
    ]
    mw = ChatContextMiddleware(cache)
    post = make_message(chat_id=CHANNEL, chat_type="channel", user_id=None, text="hi", bot=bot)

    data = await _call(mw, session, bot, post)
    chat = data["chat_row"]
    assert chat.bot_status == BotStatus.ADMINISTRATOR
    admins = list(await session.scalars(select(ChatAdmin).where(ChatAdmin.chat_id == chat.id)))
    assert len(admins) == 1
    assert len(bot.calls_named("get_chat_administrators")) == 1

    # Next post within the sync TTL does not hit the API again.
    await _call(
        mw,
        session,
        bot,
        make_message(chat_id=CHANNEL, chat_type="channel", user_id=None, message_id=11, bot=bot),
    )
    assert len(bot.calls_named("get_chat_administrators")) == 1
    assert (await session.scalar(select(Chat).where(Chat.telegram_id == CHANNEL))) is not None
    assert chat_service.admins_stale(chat) is False
