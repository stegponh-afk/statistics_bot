from datetime import UTC, datetime, timedelta

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import GetChatAdministrators
from aiogram.types import Chat as TgChat
from aiogram.types import ChatMemberAdministrator, ChatMemberMember, ChatMemberOwner
from sqlalchemy import select

from app.database.models import BotStatus, ChatAdmin, User
from app.services import chat_service
from tests.fakes import FakeBot, tg_user


def _tg_chat(chat_id: int = -100_1, chat_type: str = "supergroup") -> TgChat:
    return TgChat(id=chat_id, type=chat_type, title="Chat")


def _admin(user_id: int, *, is_bot: bool = False, **rights) -> ChatMemberAdministrator:
    base = dict(
        can_be_edited=False,
        is_anonymous=False,
        can_manage_chat=True,
        can_delete_messages=False,
        can_manage_video_chats=False,
        can_restrict_members=False,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=False,
        can_post_stories=False,
        can_edit_stories=False,
        can_delete_stories=False,
        can_send_welcome_messages=False,
    )
    base.update(rights)
    return ChatMemberAdministrator(user=tg_user(user_id, is_bot=is_bot), **base)


async def test_sync_admins_upserts_users_and_replaces_rows(session, bot: FakeBot, cache):
    chat = await chat_service.upsert_chat(session, _tg_chat())
    bot.administrators[chat.telegram_id] = [
        ChatMemberOwner(user=tg_user(1, "Owner"), is_anonymous=True),
        _admin(2),
        _admin(3, is_bot=True),  # bots are skipped
    ]
    rows = await chat_service.sync_admins(bot, session, chat, cache)
    assert {r.user_id for r in rows} == {
        u.id for u in (await session.scalars(select(User))) if u.telegram_id in (1, 2)
    }
    assert any(r.is_anonymous for r in rows)
    assert chat.admins_synced_at is not None

    # Demotion: user 2 disappears from the next sync.
    bot.administrators[chat.telegram_id] = [ChatMemberOwner(user=tg_user(1), is_anonymous=False)]
    rows = await chat_service.sync_admins(bot, session, chat, cache)
    assert len(rows) == 1
    remaining = list(await session.scalars(select(ChatAdmin)))
    assert len(remaining) == 1


async def test_sync_admins_keeps_rows_when_api_fails(session, bot: FakeBot):
    chat = await chat_service.upsert_chat(session, _tg_chat())
    bot.administrators[chat.telegram_id] = [ChatMemberOwner(user=tg_user(1), is_anonymous=False)]
    await chat_service.sync_admins(bot, session, chat)
    bot.administrators[chat.telegram_id] = TelegramBadRequest(
        method=GetChatAdministrators(chat_id=1), message="chat not found"
    )
    rows = await chat_service.sync_admins(bot, session, chat)
    assert len(rows) == 1


async def test_admin_ids_are_cached(session, bot: FakeBot, cache):
    chat = await chat_service.upsert_chat(session, _tg_chat())
    bot.administrators[chat.telegram_id] = [ChatMemberOwner(user=tg_user(1), is_anonymous=False)]
    ids = await chat_service.get_admin_telegram_ids(session, cache, chat, bot)
    assert ids == {1}
    assert len(bot.calls_named("get_chat_administrators")) == 1
    ids = await chat_service.get_admin_telegram_ids(session, cache, chat, bot)
    assert ids == {1}
    assert len(bot.calls_named("get_chat_administrators")) == 1  # served from cache


async def test_bot_membership_fields_and_gate_auto_off(session):
    chat = await chat_service.upsert_chat(session, _tg_chat())
    chat.forcesub_enabled = True
    await chat_service.apply_bot_membership(
        session, chat, _admin(999, is_bot=True, can_delete_messages=True)
    )
    assert chat.bot_status == BotStatus.ADMINISTRATOR and chat.bot_can_delete
    assert chat.forcesub_enabled

    await chat_service.apply_bot_membership(
        session, chat, ChatMemberMember(user=tg_user(999, is_bot=True))
    )
    assert chat.bot_status == BotStatus.MEMBER and not chat.bot_can_delete
    assert chat.forcesub_enabled is False


async def test_list_admin_chats_only_where_bot_is_present(session, bot: FakeBot):
    group = await chat_service.upsert_chat(session, _tg_chat(-1))
    gone = await chat_service.upsert_chat(session, _tg_chat(-2))
    bot.administrators[-1] = [ChatMemberOwner(user=tg_user(1), is_anonymous=False)]
    bot.administrators[-2] = [ChatMemberOwner(user=tg_user(1), is_anonymous=False)]
    await chat_service.sync_admins(bot, session, group)
    await chat_service.sync_admins(bot, session, gone)
    gone.bot_status = BotStatus.KICKED
    await session.commit()

    user = await session.scalar(select(User).where(User.telegram_id == 1))
    chats = await chat_service.list_admin_chats(session, user)
    assert [c.telegram_id for c in chats] == [-1]


def test_admins_stale():
    class C:
        admins_synced_at = None
        is_active = True

    assert chat_service.admins_stale(C())
    C.admins_synced_at = datetime.now(UTC) - timedelta(seconds=5)
    assert not chat_service.admins_stale(C())
    C.admins_synced_at = datetime.now(UTC) - timedelta(hours=2)
    assert chat_service.admins_stale(C())


async def test_migrate_chat_id(session):
    chat = await chat_service.upsert_chat(session, _tg_chat(-5, "group"))
    await chat_service.migrate_chat_id(session, -5, -100_5)
    assert (await chat_service.get_chat_by_telegram_id(session, -100_5)).id == chat.id


def test_enum_columns_store_values_not_member_names():
    # PostgreSQL enums in alembic 0001 are declared with the lowercase
    # .value strings; SQLAlchemy's default would send member names.
    from app.database.models import Chat, ChatAdmin

    assert Chat.__table__.c.bot_status.type.enums == ["member", "administrator", "left", "kicked"]
    assert Chat.__table__.c.type.type.enums == ["group", "supergroup", "channel"]
    assert ChatAdmin.__table__.c.status.type.enums == ["creator", "administrator"]


async def test_sync_admins_retries_after_transient_refusal(session, bot: FakeBot, monkeypatch):
    chat = await chat_service.upsert_chat(session, _tg_chat())
    attempts = {"n": 0}

    async def flaky(chat_id):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise TelegramBadRequest(
                method=GetChatAdministrators(chat_id=chat_id), message="member list is inaccessible"
            )
        return [ChatMemberOwner(user=tg_user(1), is_anonymous=False)]

    monkeypatch.setattr(bot, "get_chat_administrators", flaky)
    rows = await chat_service.sync_admins(bot, session, chat, retries=1, retry_delay=0)
    assert attempts["n"] == 2 and len(rows) == 1


async def test_remember_admin_records_the_adder(session, cache):
    chat = await chat_service.upsert_chat(session, _tg_chat())
    user = User(telegram_id=5)
    session.add(user)
    await session.commit()
    await chat_service.remember_admin(session, cache, chat, user)
    await chat_service.remember_admin(session, cache, chat, user)  # idempotent
    assert [c.telegram_id for c in await chat_service.list_admin_chats(session, user)] == [
        chat.telegram_id
    ]
