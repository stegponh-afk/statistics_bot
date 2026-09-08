"""chats.linked_chat_tg_id — a channel's discussion group

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chats", sa.Column("linked_chat_tg_id", sa.BigInteger()))


def downgrade() -> None:
    op.drop_column("chats", "linked_chat_tg_id")
