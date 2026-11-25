"""The health probes of `spectio serve` (admin-and-operations.md §3.5, "Endpoints for
orchestrators"; architecture-plugins-and-packaging.md §7.5: the Helm probes).

`GET /health/live` says only that the process serves: no database access. `GET /health/ready`
reads the database's schema revision and answers 503 unless it is one this release supports.
Both are GET-only, outside the API prefix (`app.API`), and a platform, not a browser, calls
them: the session, cross-site and write checks stand aside on their paths (`PATHS`, the one
list `auth.middleware`, `api.browser` and `api.writes` read), while the Host allow-list
(`auth.host`) still runs. Every answer carries `Cache-Control: no-store`, and a 503 reason is
one of the fixed sentences below: no path, no secret, no stack trace. No all-checks `/health`
and no `/metrics` yet.

A release only adds (admin-and-operations.md §4.3, "Expand and contract"), so a revision at
least as new as this release's head stays readable while a Helm pre-upgrade hook migrates
further: ready is not "at head", or every old pod would turn unready at once (§3.5). An older
revision, or none, is not the schema this server migrated its database to (`db.open_db`), and
ready refuses.
"""

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

LIVE = "/health/live"
READY = "/health/ready"
PATHS = frozenset({LIVE, READY})  # the paths every session and browser check stands aside on
NO_STORE = {"Cache-Control": "no-store"}
UNREACHABLE = "database unavailable"
NOT_MIGRATED = "database schema is not migrated"
UNSUPPORTED = "database schema revision is not supported by this release"

router = APIRouter(include_in_schema=False)  # a probe is not part of the API document


def head_revision() -> str:
    """The head of this release's migrations, the one `db.open_db` upgrades to: the oldest
    schema revision this server serves."""
    config = Config()
    config.set_main_option("script_location", "spectio_server:migrations")
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head is not None  # noqa: S101 - the package ships its migrations
    return head


def ready_reason(engine: Engine) -> str | None:
    """None when `engine` answers a trivial read (the revision itself) and its schema revision
    is one this release supports; else the short reason, one of the fixed sentences above."""
    try:
        with engine.connect() as conn:
            revision = MigrationContext.configure(conn).get_current_revision()
    except (OSError, SQLAlchemyError):
        return UNREACHABLE
    if revision is None:
        return NOT_MIGRATED
    if revision < head_revision():  # four-digit zero-padded: string order is numeric order
        return UNSUPPORTED
    return None


@router.get(LIVE)
def live() -> JSONResponse:
    """The process serves; nothing else is checked."""
    return JSONResponse({"status": "ok"}, headers=NO_STORE)


@router.get(READY)
def ready(request: Request) -> JSONResponse:
    """The database answers and its schema revision is one this release supports."""
    reason = ready_reason(request.app.state.writer.engine)
    if reason is None:
        return JSONResponse({"status": "ok"}, headers=NO_STORE)
    return JSONResponse(
        {"status": "unavailable", "reason": reason}, status_code=503, headers=NO_STORE
    )
