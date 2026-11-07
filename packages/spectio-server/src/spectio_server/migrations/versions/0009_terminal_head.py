"""`launches.head_host`: the host a run started from a terminal runs its head on (P1 Task 25).

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("launches", sa.Column("head_host", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("launches") as batch:
        batch.drop_column("head_host")
