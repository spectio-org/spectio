"""The run's own environment (FU-P3-86a; api §5.4, §7 `runs`): `runs.environment`, and
`environments.name`, the built-in name `ensure_tenancy` keys on.

The runs already held get `state: not_recorded`, with the executor of the one environment row
they were launched on: before FU-P3-86 the server had one kind. Rows of runs started from a
terminal stay null.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
UNKNOWN = ("name", "label", "executor", "slurm", "local")


def upgrade() -> None:
    op.add_column("environments", sa.Column("name", sa.String(), nullable=True))
    op.add_column("runs", sa.Column("environment", JSON, nullable=True))
    conn = op.get_bind()
    envs = sa.table("environments", sa.column("id"), sa.column("kind"), sa.column("name"))
    runs = sa.table(
        "runs",
        sa.column("id"),
        sa.column("environment_id"),
        sa.column("origin"),
        sa.column("environment", JSON),
    )
    conn.execute(sa.update(envs).values(name=envs.c.kind))
    kinds = {i: k for i, k in conn.execute(sa.select(envs.c.id, envs.c.kind))}
    held = sa.select(runs.c.id, runs.c.environment_id).where(
        sa.or_(runs.c.origin.is_(None), runs.c.origin != "cli-observed")
    )
    for run_id, env_id in conn.execute(held).all():
        snapshot = {**dict.fromkeys(UNKNOWN), "executor": kinds.get(env_id)}
        conn.execute(
            sa.update(runs)
            .where(runs.c.id == run_id)
            .values(environment={**snapshot, "state": "not_recorded"})
        )


def downgrade() -> None:
    # SQLite >= 3.35 drops a column in place: a batch copy of `environments` breaks the keys
    # that point to it
    op.drop_column("runs", "environment")
    op.drop_column("environments", "name")
