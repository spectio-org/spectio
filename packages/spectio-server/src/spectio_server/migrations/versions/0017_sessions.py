"""Browser sessions kept in the database (#375; auth §2, dev-env §15.3 "Access"): one table,
`sessions`, with the SHA-256 of each session secret (never the secret), when the session started
and when it was last seen. A restart keeps the sessions that are still valid.

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | Sequence[str] | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("digest", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("digest", name="uq_sessions_digest"),
    )


def downgrade() -> None:
    op.drop_table("sessions")
