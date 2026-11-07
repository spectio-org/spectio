"""Outputs, checkpoints, engine settings and the SLURM request (P1 Task 34; api §7 note of
2026-11-07). The note planned `0009`, which `0009_terminal_head` (P1 Task 25) took.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("attempts", sa.Column("outputs", JSON, nullable=True))
    op.add_column("attempts", sa.Column("slurm", JSON, nullable=True))
    op.add_column(
        "run_processes",
        sa.Column("is_checkpoint", sa.Boolean(), server_default="0", nullable=False),
    )
    op.add_column("runs", sa.Column("engine_settings", JSON, nullable=True))
    op.create_table(
        "run_output_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('output', 'temp_removed', 'protected')",
            name="ck_run_output_events_kind",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["principals.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "path", "kind"),
    )


def downgrade() -> None:
    op.drop_table("run_output_events")
    with op.batch_alter_table("runs") as batch:
        batch.drop_column("engine_settings")
    with op.batch_alter_table("run_processes") as batch:
        batch.drop_column("is_checkpoint")
    with op.batch_alter_table("attempts") as batch:
        batch.drop_column("slurm")
        batch.drop_column("outputs")
