"""api_keys.key_raw — keep the key itself so screens can show ready links

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("key_raw", sa.Text()))


def downgrade() -> None:
    op.drop_column("api_keys", "key_raw")
