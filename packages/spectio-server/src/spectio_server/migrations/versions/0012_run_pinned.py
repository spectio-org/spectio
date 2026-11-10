"""`runs.pinned` (FU-P3-115a; api §5 note of 2026-11-10): pinned runs come first in the list.

`runs.deleted_at` is already there (§7, soft delete): `POST /runs:delete` sets it.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("pinned", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("runs", "pinned")
