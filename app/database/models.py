import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON,
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


def _enum_values(enum_cls) -> list[str]:
    """Store enum .value (lowercase, as the migration declares the PG
    types), not the member name — SQLAlchemy's default."""
    return [member.value for member in enum_cls]


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
    # What gets appended to a post marked as advertising; NULL = «#реклама».
    ad_label: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Chat(Base):
    """A group, supergroup or channel the bot is (or was) a member of."""

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    type: Mapped[ChatKind] = mapped_column(
        Enum(ChatKind, name="chat_kind", values_callable=_enum_values)
    )
    title: Mapped[str | None] = mapped_column(String(256))
    username: Mapped[str | None] = mapped_column(String(64))
    invite_link: Mapped[str | None] = mapped_column(Text)
    # For channels: the discussion group (comments), from getChat.
    linked_chat_tg_id: Mapped[int | None] = mapped_column(BigInteger)
    # Whether the chat itself is set to "join by request" (getChat). The
    # join gate is dead weight without it — Telegram sends no request at
    # all — so the card has to be able to say so.
    join_by_request: Mapped[bool] = mapped_column(default=False)
    # «Награда за подписку» (channels): deep-link slug + the message
    # (broadcast_service.Content JSON) handed to verified subscribers.
    reward_slug: Mapped[str | None] = mapped_column(String(16), unique=True, index=True)
    reward_content: Mapped[dict | None] = mapped_column(JSON)

    bot_status: Mapped[BotStatus] = mapped_column(
        Enum(BotStatus, name="bot_status", values_callable=_enum_values), default=BotStatus.MEMBER
    )
    bot_can_delete: Mapped[bool] = mapped_column(default=False)
    bot_can_invite: Mapped[bool] = mapped_column(default=False)
    # "Ограничивать участников" — the captcha mutes a newcomer with it.
    bot_can_restrict: Mapped[bool] = mapped_column(default=False)

    member_count: Mapped[int | None] = mapped_column()
    member_count_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    admins_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    forcesub_enabled: Mapped[bool] = mapped_column(default=False)
    # «Заявки на вступление»: hold every join request until the applicant is
    # subscribed to the chat's required channels, then approve it. Unlike
    # forcesub_enabled this also works for channels, which have no messages
    # to delete.
    join_gate_enabled: Mapped[bool] = mapped_column(default=False)
    stats_enabled: Mapped[bool] = mapped_column(default=True)
    # IANA name; NULL = settings.default_timezone.
    timezone: Mapped[str | None] = mapped_column(String(48))

    # «Приветствие» (groups): what a newcomer gets, and the anti-spam
    # captcha that mutes them until they prove they are human.
    welcome_enabled: Mapped[bool] = mapped_column(default=False)
    # A broadcast_service.Content, whose text may use {name} and {title}.
    welcome_content: Mapped[dict | None] = mapped_column(JSON)
    # True: only the newcomer sees the greeting (ephemeral, the chat stays
    # clean); False: a normal message everyone sees.
    welcome_ephemeral: Mapped[bool] = mapped_column(default=True)
    captcha_enabled: Mapped[bool] = mapped_column(default=False)

    # Digest of the chat's numbers, DMed to its admins.
    digest_enabled: Mapped[bool] = mapped_column(default=False)
    digest_period: Mapped[str] = mapped_column(String(8), default="daily")  # daily | weekly
    digest_time: Mapped[str] = mapped_column(String(5), default="10:00")  # local "HH:MM"
    # The local day a digest was last sent for — the guard against sending
    # the same report twice when the job runs every few minutes.
    digest_last_day: Mapped[date | None] = mapped_column(Date)

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
    status: Mapped[AdminStatus] = mapped_column(
        Enum(AdminStatus, name="admin_status", values_callable=_enum_values)
    )
    is_anonymous: Mapped[bool] = mapped_column(default=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JoinRequest(Base):
    """A join request the bot is holding until the applicant subscribes to
    the chat's required channels."""

    __tablename__ = "join_requests"
    __table_args__ = (Index("ix_join_requests_user", "user_tg_id"),)

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
    )
    user_tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # The private chat Telegram opens for this request. Writable for five
    # minutes even if the applicant never started the bot — which is the
    # only reason the bot can explain itself to a stranger at all.
    user_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


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


class MemberEvent(Base):
    """A subscriber joined or left (from chat_member updates)."""

    __tablename__ = "member_events"
    __table_args__ = (Index("ix_member_events_chat_day", "chat_tg_id", "local_day"),)

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    chat_tg_id: Mapped[int] = mapped_column(BigInteger)
    user_tg_id: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(8))  # "join" | "leave"
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    local_day: Mapped[date] = mapped_column(Date)


class MemberSnapshot(Base):
    """Subscriber count per chat per local day (last value of the day)."""

    __tablename__ = "member_snapshots"

    chat_tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    local_day: Mapped[date] = mapped_column(Date, primary_key=True)
    member_count: Mapped[int] = mapped_column()


class AdPost(Base):
    """A post the admin marked as advertising. Kept apart from
    message_events so the hot write path stays untouched, and so the
    statistics can answer the question an admin who sells ads actually
    has: what did this cost me in subscribers?"""

    __tablename__ = "ad_posts"
    __table_args__ = (Index("ix_ad_posts_chat_day", "chat_tg_id", "local_day"),)

    chat_tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    local_day: Mapped[date] = mapped_column(Date)
    broadcast_id: Mapped[int | None] = mapped_column()


class PostReaction(Base):
    """Anonymous reaction total per post (message_reaction_count updates)."""

    __tablename__ = "post_reactions"

    chat_tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    total: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RewardClaim(Base):
    """A user already received the channel's «награда за подписку»."""

    __tablename__ = "reward_claims"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
    )
    user_tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
    # The key itself, so the owner's screens can show ready-to-paste
    # links (the owner already trusts this service with a bot token).
    key_raw: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)
    request_count: Mapped[int] = mapped_column(BigInteger, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BroadcastKind(str, enum.Enum):
    NOW = "now"
    ONCE = "once"
    RECURRING = "recurring"


class BroadcastStatus(str, enum.Enum):
    SCHEDULED = "scheduled"  # waiting for next_run_at
    PAUSED = "paused"
    DONE = "done"
    CANCELLED = "cancelled"


class Broadcast(Base):
    __tablename__ = "broadcasts"
    __table_args__ = (Index("ix_broadcasts_due", "status", "next_run_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default=BroadcastStatus.SCHEDULED.value)
    # See broadcast_service.Content: type, text, entities, file_id, buttons.
    content: Mapped[dict] = mapped_column(JSON)

    # once: the moment; recurring: weekdays (0=Mon .. 6=Sun, comma-separated)
    # + "HH:MM" in `timezone`.
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recur_days: Mapped[str | None] = mapped_column(String(16))
    recur_time: Mapped[str | None] = mapped_column(String(5))
    timezone: Mapped[str] = mapped_column(String(48))

    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    runs_count: Mapped[int] = mapped_column(default=0)
    sent_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def recur_days_list(self) -> list[int]:
        return [int(x) for x in (self.recur_days or "").split(",") if x != ""]


class BroadcastTargetKind(str, enum.Enum):
    CHAT = "chat"  # target_id = chats.id


class BroadcastTarget(Base):
    __tablename__ = "broadcast_targets"

    broadcast_id: Mapped[int] = mapped_column(
        ForeignKey("broadcasts.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(8), primary_key=True)
    target_id: Mapped[int] = mapped_column(primary_key=True)


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
