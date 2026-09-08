"""reward_claims — who already received a channel's reward

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reward_claims",
        sa.Column(
            "chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("user_tg_id", sa.BigInteger(), primary_key=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("reward_claims")
