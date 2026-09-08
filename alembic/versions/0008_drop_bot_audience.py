"""drop owner-bot tokens and audiences (broadcasts via third-party bots removed)

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("bot_audience")
    op.drop_column("api_keys", "bot_user_id")
    op.drop_column("api_keys", "bot_username")
    op.drop_column("api_keys", "bot_token")


def downgrade() -> None:
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
