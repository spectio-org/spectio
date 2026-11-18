"""The run's own environment (FU-P3-86a; api §5.4, §7 `runs`): `runs.environment`, and
`environments.name`, the built-in name `ensure_tenancy` keys on.

The runs already held get `state: not_recorded` with every field null, the same as a rebuild
from their manifest writes (`spectio.environments.run_column(None)`, CR-P3FU86A-01): so a run
from before FU-P3-86 reads as not SLURM. Rows of runs started from a terminal stay null.

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
    envs = sa.table("environments", sa.column("kind"), sa.column("name"))
    runs = sa.table("runs", sa.column("origin"), sa.column("environment", JSON))
    conn.execute(sa.update(envs).values(name=envs.c.kind))
    conn.execute(
        sa.update(runs)
        .where(sa.or_(runs.c.origin.is_(None), runs.c.origin != "cli-observed"))
        .values(environment={**dict.fromkeys(UNKNOWN), "state": "not_recorded"})
    )


def downgrade() -> None:
    # SQLite >= 3.35 drops a column in place: a batch copy of `environments` breaks the keys
    # that point to it
    op.drop_column("runs", "environment")
    op.drop_column("environments", "name")
