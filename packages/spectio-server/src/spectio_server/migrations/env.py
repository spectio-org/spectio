"""Alembic environment: online only, on the connection that `store.db.open_db` passes in."""

from typing import Any, Literal

from alembic import context
from alembic.autogenerate.api import AutogenContext

from spectio_server.store.schema import UTCDateTime, metadata


def _render_item(type_: str, obj: Any, _context: AutogenContext) -> str | Literal[False]:
    # A revision stays frozen: it names the stored type, not the live Python wrapper.
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


connection = context.config.attributes["connection"]
# render_as_batch: SQLite alters a table by copying it (Alembic batch mode).
context.configure(
    connection=connection,
    target_metadata=metadata,
    render_as_batch=True,
    render_item=_render_item,
)
with context.begin_transaction():
    context.run_migrations()
