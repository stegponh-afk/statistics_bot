"""owner bots (token + audience) and broadcasts

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("bot_token", sa.Text()))
    op.add_column("api_keys", sa.Column("bot_username", sa.String(64)))
    op.add_column("api_keys", sa.Column("bot_user_id", sa.BigInteger()))

    op.create_table(
        "bot_audience",
        sa.Column(
            "api_key_id",
            sa.Integer(),
            sa.ForeignKey("api_keys.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_tg_id", sa.BigInteger(), primary_key=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="scheduled"),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("recur_days", sa.String(16)),
        sa.Column("recur_time", sa.String(5)),
        sa.Column("timezone", sa.String(48), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("runs_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_broadcasts_owner_user_id", "broadcasts", ["owner_user_id"])
    op.create_index("ix_broadcasts_due", "broadcasts", ["status", "next_run_at"])

    op.create_table(
        "broadcast_targets",
        sa.Column(
            "broadcast_id",
            sa.Integer(),
            sa.ForeignKey("broadcasts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("kind", sa.String(8), primary_key=True),
        sa.Column("target_id", sa.Integer(), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("broadcast_targets")
    op.drop_table("broadcasts")
    op.drop_table("bot_audience")
    op.drop_column("api_keys", "bot_user_id")
    op.drop_column("api_keys", "bot_username")
    op.drop_column("api_keys", "bot_token")
