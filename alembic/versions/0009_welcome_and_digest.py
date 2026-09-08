"""newcomer welcome + captcha, and the admin digest

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BOOLS = (
    ("bot_can_restrict", sa.false()),
    ("welcome_enabled", sa.false()),
    ("welcome_ephemeral", sa.true()),
    ("captcha_enabled", sa.false()),
    ("digest_enabled", sa.false()),
)


def upgrade() -> None:
    for name, default in _BOOLS:
        op.add_column(
            "chats", sa.Column(name, sa.Boolean(), nullable=False, server_default=default)
        )
    op.add_column("chats", sa.Column("welcome_content", sa.JSON()))
    op.add_column(
        "chats",
        sa.Column("digest_period", sa.String(8), nullable=False, server_default="daily"),
    )
    op.add_column(
        "chats", sa.Column("digest_time", sa.String(5), nullable=False, server_default="10:00")
    )
    op.add_column("chats", sa.Column("digest_last_day", sa.Date()))


def downgrade() -> None:
    for column in (
        "digest_last_day",
        "digest_time",
        "digest_period",
        "welcome_content",
        *(name for name, _ in reversed(_BOOLS)),
    ):
        op.drop_column("chats", column)
