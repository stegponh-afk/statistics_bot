"""member_events, member_snapshots, post_reactions — channel metrics

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "member_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("chat_tg_id", sa.BigInteger(), nullable=False),
        sa.Column("user_tg_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_day", sa.Date(), nullable=False),
    )
    op.create_index("ix_member_events_chat_day", "member_events", ["chat_tg_id", "local_day"])

    op.create_table(
        "member_snapshots",
        sa.Column("chat_tg_id", sa.BigInteger(), primary_key=True),
        sa.Column("local_day", sa.Date(), primary_key=True),
        sa.Column("member_count", sa.Integer(), nullable=False),
    )

    op.create_table(
        "post_reactions",
        sa.Column("chat_tg_id", sa.BigInteger(), primary_key=True),
        sa.Column("message_id", sa.BigInteger(), primary_key=True),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("post_reactions")
    op.drop_table("member_snapshots")
    op.drop_index("ix_member_events_chat_day", table_name="member_events")
    op.drop_table("member_events")
