"""remember whether the chat itself asks for join requests

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chats",
        sa.Column("join_by_request", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("chats", "join_by_request")
