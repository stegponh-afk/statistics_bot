"""posts marked as advertising, and the label appended to them

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ad_label", sa.String(64)))
    op.create_table(
        "ad_posts",
        sa.Column("chat_tg_id", sa.BigInteger(), primary_key=True),
        sa.Column("message_id", sa.BigInteger(), primary_key=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_day", sa.Date(), nullable=False),
        sa.Column("broadcast_id", sa.Integer()),
    )
    op.create_index("ix_ad_posts_chat_day", "ad_posts", ["chat_tg_id", "local_day"])


def downgrade() -> None:
    op.drop_index("ix_ad_posts_chat_day", table_name="ad_posts")
    op.drop_table("ad_posts")
    op.drop_column("users", "ad_label")
