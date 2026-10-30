"""`snakemake_jobs`: the task of each Snakemake `jobid` in a launch (P1 Task 5).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "snakemake_jobs",
        sa.Column("launch_id", sa.String(), nullable=False),
        sa.Column("jobid", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["launch_id"], ["launches.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("launch_id", "jobid"),
    )


def downgrade() -> None:
    op.drop_table("snakemake_jobs")
