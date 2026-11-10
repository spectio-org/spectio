"""`principals.notifications_read_at` (FU-P3-113, api §5.9): the principal's notifications
mark; an item newer than it is unread.

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "principals", sa.Column("notifications_read_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("principals", "notifications_read_at")
