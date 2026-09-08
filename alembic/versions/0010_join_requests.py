"""join requests held until the applicant is subscribed

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chats",
        sa.Column("join_gate_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "join_requests",
        sa.Column(
            "chat_id",
            sa.Integer(),
            sa.ForeignKey("chats.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_tg_id", sa.BigInteger(), primary_key=True),
        sa.Column("user_chat_id", sa.BigInteger()),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_join_requests_user", "join_requests", ["user_tg_id"])


def downgrade() -> None:
    op.drop_index("ix_join_requests_user", table_name="join_requests")
    op.drop_table("join_requests")
    op.drop_column("chats", "join_gate_enabled")
