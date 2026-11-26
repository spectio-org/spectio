"""Where a workflow version came from (#400; api §5, note of 2026-10-30): one nullable column
on `workflow_versions`, `manifest`, `file` or `tag`. The rows before this change have `null`
for it, whether their version is the Nextflow manifest's or none: where it came from was not
kept, and a module's version (§5.10) is the registry's, so nothing is backfilled.

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | Sequence[str] | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("workflow_versions", sa.Column("version_source", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("workflow_versions", "version_source")
