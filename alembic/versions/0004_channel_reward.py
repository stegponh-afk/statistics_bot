"""chats.reward_* — «награда за подписку» handed out by this bot

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chats", sa.Column("reward_slug", sa.String(16)))
    op.add_column("chats", sa.Column("reward_content", sa.JSON()))
    op.create_index("ix_chats_reward_slug", "chats", ["reward_slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_chats_reward_slug", table_name="chats")
    op.drop_column("chats", "reward_content")
    op.drop_column("chats", "reward_slug")
