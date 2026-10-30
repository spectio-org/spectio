"""Alembic environment: online only, on the connection that `store.db.open_db` passes in."""

from alembic import context

from spectio_server.store.schema import metadata

connection = context.config.attributes["connection"]
# render_as_batch: SQLite alters a table by copying it (Alembic batch mode).
context.configure(connection=connection, target_metadata=metadata, render_as_batch=True)
with context.begin_transaction():
    context.run_migrations()
