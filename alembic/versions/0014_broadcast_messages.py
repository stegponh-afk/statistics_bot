"""every published post, so it can be edited, deleted or auto-deleted

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-10

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "broadcast_messages",
        sa.Column("chat_tg_id", sa.BigInteger(), primary_key=True),
        sa.Column("message_id", sa.BigInteger(), primary_key=True),
        sa.Column("broadcast_id", sa.Integer()),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delete_at", sa.DateTime(timezone=True)),
        sa.Column("delete_after_reactions", sa.Integer()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_broadcast_messages_broadcast", "broadcast_messages", ["broadcast_id"])
    op.create_index("ix_broadcast_messages_due", "broadcast_messages", ["delete_at"])


def downgrade() -> None:
    op.drop_index("ix_broadcast_messages_due", table_name="broadcast_messages")
    op.drop_index("ix_broadcast_messages_broadcast", table_name="broadcast_messages")
    op.drop_table("broadcast_messages")
