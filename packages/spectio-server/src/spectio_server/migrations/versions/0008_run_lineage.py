"""`runs.parent_run_id`, `lineage_id` and `relaunch_mode`: a Resume is a child run (P1 Task 30).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("parent_run_id", sa.String(), nullable=True))
    op.add_column("runs", sa.Column("lineage_id", sa.String(), nullable=True))
    op.add_column("runs", sa.Column("relaunch_mode", sa.String(), nullable=True))
    op.create_index("ix_runs_parent", "runs", ["parent_run_id"])


def downgrade() -> None:
    op.drop_index("ix_runs_parent", table_name="runs")
    with op.batch_alter_table("runs") as batch:
        for column in ("relaunch_mode", "lineage_id", "parent_run_id"):
            batch.drop_column(column)
