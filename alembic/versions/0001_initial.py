"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

chat_kind = sa.Enum("group", "supergroup", "channel", name="chat_kind")
bot_status = sa.Enum("member", "administrator", "left", "kicked", name="bot_status")
admin_status = sa.Enum("creator", "administrator", name="admin_status")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64)),
        sa.Column("full_name", sa.String(256)),
        sa.Column("started_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rich_buttons_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("type", chat_kind, nullable=False),
        sa.Column("title", sa.String(256)),
        sa.Column("username", sa.String(64)),
        sa.Column("invite_link", sa.Text()),
        sa.Column("bot_status", bot_status, nullable=False, server_default="member"),
        sa.Column("bot_can_delete", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("bot_can_invite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("member_count", sa.Integer()),
        sa.Column("member_count_updated_at", sa.DateTime(timezone=True)),
        sa.Column("admins_synced_at", sa.DateTime(timezone=True)),
        sa.Column("forcesub_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stats_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("timezone", sa.String(48)),
        sa.Column("added_by_user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chats_telegram_id", "chats", ["telegram_id"], unique=True)

    op.create_table(
        "chat_admins",
        sa.Column(
            "chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("status", admin_status, nullable=False),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chat_admins_user_id", "chat_admins", ["user_id"])

    op.create_table(
        "group_required_channels",
        sa.Column(
            "chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "channel_id",
            sa.Integer(),
            sa.ForeignKey("chats.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "chat_whitelist",
        sa.Column(
            "chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("user_tg_id", sa.BigInteger(), primary_key=True),
        sa.Column("added_by_user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("request_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_api_keys_owner_user_id", "api_keys", ["owner_user_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    op.create_table(
        "api_key_channels",
        sa.Column(
            "api_key_id",
            sa.Integer(),
            sa.ForeignKey("api_keys.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "channel_id",
            sa.Integer(),
            sa.ForeignKey("chats.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False, server_default="0"),
    )

    op.create_table(
        "message_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("chat_tg_id", sa.BigInteger(), nullable=False),
        sa.Column("user_tg_id", sa.BigInteger()),
        sa.Column("sender_chat_tg_id", sa.BigInteger()),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_day", sa.Date(), nullable=False),
        sa.Column("local_hour", sa.SmallInteger(), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("text_length", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_forward", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_reply", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("chat_tg_id", "message_id", name="uq_message_events_chat_message"),
    )
    op.create_index("ix_message_events_chat_day", "message_events", ["chat_tg_id", "local_day"])
    op.create_index(
        "ix_message_events_chat_user_day",
        "message_events",
        ["chat_tg_id", "user_tg_id", "local_day"],
    )
    op.create_index("ix_message_events_sent_at", "message_events", ["sent_at"])

    op.create_table(
        "word_stats_daily",
        sa.Column("chat_tg_id", sa.BigInteger(), primary_key=True),
        sa.Column("local_day", sa.Date(), primary_key=True),
        sa.Column("word", sa.String(64), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_word_stats_daily_chat_day", "word_stats_daily", ["chat_tg_id", "local_day"])


def downgrade() -> None:
    op.drop_table("word_stats_daily")
    op.drop_table("message_events")
    op.drop_table("api_key_channels")
    op.drop_table("api_keys")
    op.drop_table("chat_whitelist")
    op.drop_table("group_required_channels")
    op.drop_table("chat_admins")
    op.drop_table("chats")
    op.drop_table("users")
    bind = op.get_bind()
    admin_status.drop(bind, checkfirst=True)
    bot_status.drop(bind, checkfirst=True)
    chat_kind.drop(bind, checkfirst=True)
