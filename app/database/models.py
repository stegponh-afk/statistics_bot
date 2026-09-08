import enum
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ChatKind(str, enum.Enum):
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class BotStatus(str, enum.Enum):
    MEMBER = "member"
    ADMINISTRATOR = "administrator"
    LEFT = "left"
    KICKED = "kicked"


class AdminStatus(str, enum.Enum):
    CREATOR = "creator"
    ADMINISTRATOR = "administrator"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(256))
    # True once the user pressed /start in a private chat — only then can the
    # bot DM them (e.g. "гейт отключён: потеряны права").
    started_bot: Mapped[bool] = mapped_column(default=False)
    # "Визуализация меню": True = buttons embedded in the message as rich
    # blocks (new style), False = classic inline keyboard below the message.
    rich_buttons_enabled: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Chat(Base):
    """A group, supergroup or channel the bot is (or was) a member of."""

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    type: Mapped[ChatKind] = mapped_column(Enum(ChatKind, name="chat_kind"))
    title: Mapped[str | None] = mapped_column(String(256))
    username: Mapped[str | None] = mapped_column(String(64))
    invite_link: Mapped[str | None] = mapped_column(Text)

    bot_status: Mapped[BotStatus] = mapped_column(
        Enum(BotStatus, name="bot_status"), default=BotStatus.MEMBER
    )
    bot_can_delete: Mapped[bool] = mapped_column(default=False)
    bot_can_invite: Mapped[bool] = mapped_column(default=False)

    member_count: Mapped[int | None] = mapped_column()
    member_count_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    admins_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    forcesub_enabled: Mapped[bool] = mapped_column(default=False)
    stats_enabled: Mapped[bool] = mapped_column(default=True)
    # IANA name; NULL = settings.default_timezone.
    timezone: Mapped[str | None] = mapped_column(String(48))

    added_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def is_channel(self) -> bool:
        return self.type == ChatKind.CHANNEL

    @property
    def is_active(self) -> bool:
        return self.bot_status in (BotStatus.MEMBER, BotStatus.ADMINISTRATOR)


class ChatAdmin(Base):
    """Who administers which chat — the source of the «Мои чаты» screen."""

    __tablename__ = "chat_admins"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    status: Mapped[AdminStatus] = mapped_column(Enum(AdminStatus, name="admin_status"))
    is_anonymous: Mapped[bool] = mapped_column(default=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupRequiredChannel(Base):
    """Force-sub binding: members of `chat` must be subscribed to `channel`."""

    __tablename__ = "group_required_channels"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatWhitelist(Base):
    __tablename__ = "chat_whitelist"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
    )
    user_tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    added_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    # Only the sha256 of the full key is stored; the key itself is shown to
    # the owner exactly once, at creation.
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(12))
    is_active: Mapped[bool] = mapped_column(default=True)
    request_count: Mapped[int] = mapped_column(BigInteger, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApiKeyChannel(Base):
    __tablename__ = "api_key_channels"

    api_key_id: Mapped[int] = mapped_column(
        ForeignKey("api_keys.id", ondelete="CASCADE"), primary_key=True
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, default=0)


class MessageEvent(Base):
    """One row per counted group message / channel post. Metadata only —
    the text itself is never stored (see stats_service.record_message).

    Keyed by raw Telegram ids (no FKs) so the hot write path never joins.
    local_day/local_hour are computed at write time in the chat's timezone,
    which keeps every read query a plain comparison on a Date column that
    behaves identically on PostgreSQL and the sqlite test database.
    """

    __tablename__ = "message_events"
    __table_args__ = (
        UniqueConstraint("chat_tg_id", "message_id", name="uq_message_events_chat_message"),
        Index("ix_message_events_chat_day", "chat_tg_id", "local_day"),
        Index("ix_message_events_chat_user_day", "chat_tg_id", "user_tg_id", "local_day"),
        Index("ix_message_events_sent_at", "sent_at"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    chat_tg_id: Mapped[int] = mapped_column(BigInteger)
    # NULL for channel posts and messages sent on behalf of a chat
    # (anonymous admins, linked-channel auto-forwards).
    user_tg_id: Mapped[int | None] = mapped_column(BigInteger)
    sender_chat_tg_id: Mapped[int | None] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    local_day: Mapped[date] = mapped_column(Date)
    local_hour: Mapped[int] = mapped_column(SmallInteger)
    content_type: Mapped[str] = mapped_column(String(32))
    text_length: Mapped[int] = mapped_column(default=0)
    is_forward: Mapped[bool] = mapped_column(default=False)
    is_reply: Mapped[bool] = mapped_column(default=False)


class WordStatDaily(Base):
    __tablename__ = "word_stats_daily"
    __table_args__ = (Index("ix_word_stats_daily_chat_day", "chat_tg_id", "local_day"),)

    chat_tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    local_day: Mapped[date] = mapped_column(Date, primary_key=True)
    word: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
