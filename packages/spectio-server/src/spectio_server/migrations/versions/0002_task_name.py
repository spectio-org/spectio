"""`tasks.name`: the key of an untagged Nextflow task (P1 Task 4, CR-P3T04-02, inbox #77), and
the projector's indexes: the task key, and the attempt key of api §8.2 (CR-P3T04-03), and
`launches.culprit_attempt_id`, the attempt `runs.failure` blames (CR-P3T04-08).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("name", sa.String(), nullable=True))
    op.create_index("ix_tasks_run_key", "tasks", ["run_id", "process_or_rule", "tag", "name"])
    with op.batch_alter_table("attempts") as batch_op:
        batch_op.create_unique_constraint("uq_attempts_key", ["task_id", "launch_n", "n"])
    op.add_column("launches", sa.Column("culprit_attempt_id", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("launches") as batch_op:
        batch_op.drop_column("culprit_attempt_id")
    with op.batch_alter_table("attempts") as batch_op:
        batch_op.drop_constraint("uq_attempts_key", type_="unique")
    op.drop_index("ix_tasks_run_key", table_name="tasks")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("name")
