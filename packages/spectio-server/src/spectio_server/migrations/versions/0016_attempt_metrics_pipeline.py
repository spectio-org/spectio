"""An index `(project_id, pipeline, ended_at)` on `attempt_metrics` (FU-P3-105e, api §5.5):
the across-runs `pipeline=` filter with no `process=` searches a range of `ended_at` on it.
SQLite's planner takes `(project_id, ended_at)` over the four-column pipeline index of 0015
for that filter, since `process_or_rule` sits between `pipeline` and `ended_at` there.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0016"
down_revision: str | Sequence[str] | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_attempt_metrics_project_pipeline_ended",
        "attempt_metrics",
        ["project_id", "pipeline", "ended_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_attempt_metrics_project_pipeline_ended", "attempt_metrics")
