"""`attempts.scheduler`: the SLURM state and reason an engine's own message gave (P1 Task 29).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("attempts", sa.Column("scheduler", JSON, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("attempts") as batch:
        batch.drop_column("scheduler")
