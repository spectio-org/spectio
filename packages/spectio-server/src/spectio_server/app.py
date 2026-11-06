"""The FastAPI app of `spectio serve` (P1 Tasks 11, 12, 17 and 18).

Every request needs the session of the token link (dev-env §15.3 req. 2, `auth`, P1 Task 12).
Sign-in is not complete until P1 Task 16 (the cookie per Host port, Task 13), so the API is
served in local mode only (`spectio init --local`): on a SLURM environment, where other
users share the login node and its loopback port, every `/api/v1` path answers 404 with the
reason (inbox #86). In local mode too, the API is left unmounted on a machine that looks like
a cluster node or a shared one (`shared_host`, SEC-P3T17-06): kind `local` is a configuration
value, which can be set on a login node. The Host allow-list (dev-env §15.3 req. 4, `auth.host`),
the cross-site check (`api.browser`), the session and the write checks (req. 7, `auth.writes`)
run on every request, in that order. The generated docs stay off: the
OpenAPI document is a file, `openapi/0.0.1.json`, written from `app.openapi()` (Task 18), with
typed responses (`api.models`, FU-P3-21).

The screens (`web/dist`, Task 19) follow the API's rule: served at `/` when the API is mounted,
else `/` stays this plain page and says why (`static`), behind the session too.
"""

import os
import pwd
import shutil
from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

from spectio.config import Settings
from spectio_server import static
from spectio_server.api import (
    browser,
    cancel,
    logs,
    problems,
    relaunch,
    results,
    runs_read,
    runs_write,
    stream,
    taskfiles,
    workflows,
)
from spectio_server.auth import host, middleware, routes, writes
from spectio_server.auth.secrets import ServerKey, SessionStore, TicketStore
from spectio_server.failure import Accounting
from spectio_server.files.pool import FilePool
from spectio_server.store.writer import Writer

PLACEHOLDER = "Spectio {version} is running.\n{why}\n"
API = "/api/v1"
API_VERSION = "0.0.1"  # the API document's version, not the package's: a release bump keeps it
NO_API = (
    "The API is served in local mode only (spectio init --local) until sign-in is complete: "
    "P1 Tasks 13 to 16 (the session cookie per port and its checks)."
)

SLURM_CONF_FILE = Path("/etc/slurm/slurm.conf")
PROC = Path("/proc")
NOBODY = 65534


def _a_person(uid: int) -> bool:
    """A uid with a user account (local or from the directory, NSS): not a container's
    unnamed service."""
    try:
        pwd.getpwuid(uid)
    except KeyError:
        return False
    return True


def shared_host() -> str | None:
    """Why this machine looks like a cluster node or one other people use, or None. Best effort:
    a /proc mounted with hidepid hides the other users' processes."""
    if os.environ.get("SLURM_CONF"):
        return "SLURM_CONF is set"
    if SLURM_CONF_FILE.exists():
        return f"{SLURM_CONF_FILE} exists"
    if shutil.which("sinfo"):
        return "sinfo is on PATH"
    me = os.getuid()
    for status in PROC.glob("[0-9]*/status"):
        try:
            line = next(x for x in status.read_text().splitlines() if x.startswith("Uid:"))
        except (OSError, StopIteration):  # the process ended meanwhile
            continue
        uid = int(line.split()[1])
        if uid >= 1000 and uid not in (me, NOBODY) and _a_person(uid):
            return f"a process of uid {uid} runs here"
    return None


def no_api_reason(settings: Settings) -> str | None:
    """Why the `/api/v1` routers are not mounted, or None when they are."""
    if settings.executor != "local":
        return NO_API
    shared = shared_host()
    if shared is not None:
        return f"This machine looks shared ({shared}): {NO_API}"
    return None


def create_app(
    settings: Settings,
    writer: Writer,
    web_dir: Path = static.DIST,
    files: FilePool | None = None,
    accounting: Accounting | None = None,
    server_key: ServerKey | None = None,
) -> FastAPI:
    """The app; `files` is the pool the routes read run files in, `accounting` the server's
    one gate to `sacct` (each made from the settings when None), `server_key` the key of
    `auth/links` (one kept in memory only when None)."""
    app = FastAPI(
        title="Spectio",
        version=API_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.writer = writer
    app.state.files = FilePool() if files is None else files  # dev-env §15.3 req. 13
    # dev-env §15.3 req. 15: its thread starts on the first job asked
    app.state.accounting = Accounting.from_settings(settings) if accounting is None else accounting
    app.state.engine_versions = workflows.engine_versions(settings)
    app.state.server_key = server_key or ServerKey.new()
    app.state.tickets = TicketStore()
    app.state.sessions = SessionStore()
    problems.install(app)
    # Starlette runs the last middleware installed first: Host, cross-site, session, writes
    writes.install(app)  # last, the session-exempt writes included: Origin and JSON (§15.3 req. 7)
    middleware.install(app)  # a session on every request but four (§15.3 req. 2)
    browser.install(app)  # no cross-site request, a GET included (§15.3 req. 7, SEC-P3T17-02)
    host.install(app)  # first, the bootstrap routes included: the Host allow-list (§15.3 req. 4)
    app.include_router(routes.pages)
    app.include_router(routes.router, prefix=API)

    reason = no_api_reason(settings)  # one scan: the start text reads it back (CR-P3T17-04)
    app.state.no_api = reason
    if reason is None and static.built(web_dir):
        static.install(app, web_dir)
    else:
        why = static.NOT_BUILT if reason is None else f"{reason} The screens are served with it."
        page = PLACEHOLDER.format(version=version("spectio"), why=why)

        @app.get("/", response_class=PlainTextResponse, include_in_schema=False)
        def home() -> str:
            return page

    if reason is None:
        app.state.stream = stream.Stream(writer.engine)
        writer.on_commit = app.state.stream.notify  # the writer thread, after each commit
        # relaunch first: `GET /runs/{id}:launch-template` before `GET /runs/{run_id}`
        app.state.reports = {}  # the reports of ended runs (P1 Task 31)
        app.state.follows = logs.Follows()  # dev-env §15.3 req. 14
        routers = (workflows, runs_write, relaunch, runs_read, logs, taskfiles, results, cancel)
        for module in (*routers, stream):
            app.include_router(module.router, prefix=API)
    else:

        @app.api_route(API + "/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
        def absent(path: str) -> JSONResponse:
            return problems.problem(404, "not-found", "Not found", reason)

    return app
