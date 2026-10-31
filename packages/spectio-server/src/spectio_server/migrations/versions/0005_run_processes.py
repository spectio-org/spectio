"""`run_processes`: a run's processes or rules and their stage (P1 Task 27).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_processes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.String(), nullable=True),
        sa.Column("ended", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("jobs_planned", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["principals.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "name"),
    )


def downgrade() -> None:
    op.drop_table("run_processes")
