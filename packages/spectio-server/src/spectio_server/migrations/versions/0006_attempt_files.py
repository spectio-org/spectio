"""`attempts.work_dir`, `native_id` and `logs`: where each attempt's files are (P1 Task 28).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("attempts", sa.Column("work_dir", sa.String(), nullable=True))
    op.add_column("attempts", sa.Column("native_id", sa.String(), nullable=True))
    op.add_column("attempts", sa.Column("logs", JSON, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("attempts") as batch:
        batch.drop_column("logs")
        batch.drop_column("native_id")
        batch.drop_column("work_dir")
