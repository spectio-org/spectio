"""A launch's `default_resources` and `config_file` (FU-P3-110a; api §5.7, §7 `runs`): two
nullable columns. The runs already held have neither, as a rebuild from their manifest reads
them (`spectio_server.api.extras.column(…, None)`).

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("runs", sa.Column("default_resources", JSON, nullable=True))
    op.add_column("runs", sa.Column("config_file", JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "config_file")
    op.drop_column("runs", "default_resources")
