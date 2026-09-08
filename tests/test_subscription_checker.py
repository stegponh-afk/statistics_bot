from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.methods import GetChatMember
from aiogram.types import (
    ChatMemberAdministrator,
    ChatMemberBanned,
    ChatMemberLeft,
    ChatMemberMember,
    ChatMemberOwner,
    ChatMemberRestricted,
)

from app.database.models import Chat, ChatKind
from app.services.subscription_checker import (
    REASON_BOT_NOT_ADMIN,
    REASON_RATE_LIMITED,
    check_user,
)
from tests.fakes import FakeBot, FakeClock, tg_user

USER = 42


def _channel(tg_id: int) -> Chat:
    return Chat(id=abs(tg_id), telegram_id=tg_id, type=ChatKind.CHANNEL, title=f"C{tg_id}")


def _restricted(is_member: bool) -> ChatMemberRestricted:
    flags = {
        name: False
        for name in (
            "can_send_messages",
            "can_send_audios",
            "can_send_documents",
            "can_send_photos",
            "can_send_videos",
            "can_send_video_notes",
            "can_send_voice_notes",
            "can_send_polls",
            "can_send_other_messages",
            "can_add_web_page_previews",
            "can_change_info",
            "can_invite_users",
            "can_pin_messages",
            "can_manage_topics",
            "can_react_to_messages",
            "can_edit_tag",
        )
    }
    return ChatMemberRestricted(user=tg_user(USER), is_member=is_member, until_date=0, **flags)


def _admin() -> ChatMemberAdministrator:
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
    return ChatMemberAdministrator(user=tg_user(USER), **rights)


async def test_statuses(bot: FakeBot, cache):
    subscribed = [
        ChatMemberMember(user=tg_user(USER)),
        _admin(),
        ChatMemberOwner(user=tg_user(USER), is_anonymous=False),
        _restricted(True),
    ]
    not_subscribed = [
        ChatMemberLeft(user=tg_user(USER)),
        ChatMemberBanned(user=tg_user(USER), until_date=0),
        _restricted(False),
    ]
    for i, member in enumerate(subscribed):
        bot.members[(-10 - i, USER)] = member
        result = await check_user(bot, cache, USER, [_channel(-10 - i)])
        assert result.subscribed, member
    for i, member in enumerate(not_subscribed):
        bot.members[(-20 - i, USER)] = member
        result = await check_user(bot, cache, USER, [_channel(-20 - i)])
        assert not result.subscribed and [c.telegram_id for c in result.missing] == [-20 - i]


async def test_cache_hit_and_force(bot: FakeBot, cache, clock: FakeClock):
    bot.members[(-1, USER)] = ChatMemberLeft(user=tg_user(USER))
    first = await check_user(bot, cache, USER, [_channel(-1)])
    assert not first.subscribed and first.cached is False
    assert len(bot.calls_named("get_chat_member")) == 1

    bot.members[(-1, USER)] = ChatMemberMember(user=tg_user(USER))
    second = await check_user(bot, cache, USER, [_channel(-1)])
    assert not second.subscribed and second.cached is True  # stale but cached
    assert len(bot.calls_named("get_chat_member")) == 1

    forced = await check_user(bot, cache, USER, [_channel(-1)], force=True)
    assert forced.subscribed and forced.cached is False
    assert len(bot.calls_named("get_chat_member")) == 2

    clock.advance(61)
    bot.members[(-1, USER)] = ChatMemberLeft(user=tg_user(USER))
    expired = await check_user(bot, cache, USER, [_channel(-1)])
    assert not expired.subscribed and len(bot.calls_named("get_chat_member")) == 3


async def test_unavailable_channels_fail_open(bot: FakeBot, cache):
    bot.members[(-1, USER)] = TelegramBadRequest(
        method=GetChatMember(chat_id=-1, user_id=USER),
        message="Bad Request: member list is inaccessible",
    )
    bot.members[(-2, USER)] = ChatMemberMember(user=tg_user(USER))
    result = await check_user(bot, cache, USER, [_channel(-1), _channel(-2)])
    assert result.subscribed
    assert [(c.telegram_id, r) for c, r in result.unavailable] == [(-1, REASON_BOT_NOT_ADMIN)]


async def test_user_not_found_means_not_subscribed(bot: FakeBot, cache):
    bot.members[(-1, USER)] = TelegramBadRequest(
        method=GetChatMember(chat_id=-1, user_id=USER), message="Bad Request: user not found"
    )
    result = await check_user(bot, cache, USER, [_channel(-1)])
    assert not result.subscribed and not result.unavailable


async def test_rate_limit_is_unavailable(bot: FakeBot, cache):
    bot.members[(-1, USER)] = TelegramRetryAfter(
        method=GetChatMember(chat_id=-1, user_id=USER), message="retry", retry_after=5
    )
    result = await check_user(bot, cache, USER, [_channel(-1)])
    assert result.subscribed and result.unavailable[0][1] == REASON_RATE_LIMITED


async def test_no_channels_is_trivially_subscribed(bot: FakeBot, cache):
    result = await check_user(bot, cache, USER, [])
    assert result.subscribed and not bot.calls
