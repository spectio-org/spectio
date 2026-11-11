"""A run's target: one module or one rule (api §5.10, §7 `runs`; #161): `runs.target`, null for
the whole pipeline, which every run held so far is; and two `workflows.source` values,
`module-registry` and `module-local`, the identity of a module run's workflow.

SQLite changes a CHECK by copying the table, which drops `workflows` while `workflow_versions`
points to it: `store.db._migrate` runs with foreign keys off and checks them before the commit.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | Sequence[str] | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = ("git", "nf-core", "catalog", "crate", "local")
NEW = (*OLD, "module-registry", "module-local")
JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _sources(values: tuple[str, ...]) -> None:
    with op.batch_alter_table("workflows", recreate="always") as batch:
        batch.drop_constraint("ck_workflows_source", type_="check")
        sql = ", ".join(repr(v) for v in values)
        batch.create_check_constraint("ck_workflows_source", f"source IN ({sql})")


def upgrade() -> None:
    op.add_column("runs", sa.Column("target", JSON, nullable=True))
    _sources(NEW)


def downgrade() -> None:
    _sources(OLD)  # fails while a module workflow is held: delete those runs first
    op.drop_column("runs", "target")
