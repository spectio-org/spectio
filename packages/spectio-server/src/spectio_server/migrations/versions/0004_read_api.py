"""`run_stages`, `tasks.stage_id` and `workflow_versions.version` (P1 Task 18).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_stages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("stage_id", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column(
            "task_counts",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("source IN ('declared', 'detected')", name="ck_run_stages_source"),
        sa.CheckConstraint(
            "state IN ('not_started', 'running', 'awaiting_review', 'completed', 'failed', "
            "'skipped')",
            name="ck_run_stages_state",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["principals.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "stage_id"),
    )
    op.add_column("tasks", sa.Column("stage_id", sa.String(), nullable=True))
    op.add_column("workflow_versions", sa.Column("version", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("workflow_versions") as batch:
        batch.drop_column("version")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("stage_id")
    op.drop_table("run_stages")
