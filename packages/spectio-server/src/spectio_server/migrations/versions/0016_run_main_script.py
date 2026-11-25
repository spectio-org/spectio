"""A run's Nextflow entry script other than `main.nf` (#351; api §5.6, §7 `runs`): one nullable
column. The runs already held ran `main.nf`, or are Snakemake runs: null.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | Sequence[str] | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("main_script", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "main_script")
