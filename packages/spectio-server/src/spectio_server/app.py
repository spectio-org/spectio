"""The FastAPI app of `spectio serve` (P1 Tasks 11, 12, 17 and 18).

Every request needs the session of the token link (dev-env §15.3 req. 2, `auth`, P1 Task 12).
On a TCP port the API is served in local mode only (`spectio init --local`; inbox #86), on a
machine that does not look like a cluster node or a shared one (`shared_host`, SEC-P3T17-06:
kind `local` is a configuration value, which can be set on a login node); elsewhere every
`/api/v1` path answers 404 with the reason. On SLURM and shared hosts `spectio serve` listens
on a Unix socket in its 0700 database directory instead (`on_socket`), where the kernel refuses
other users at `connect`, and the API is mounted there (inbox #109 rule 5, Thomas 2026-11-08;
FU-P3-72): another user can reach a loopback port of the same node, never that socket.
The Host allow-list (dev-env §15.3 req. 4, `auth.host`),
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

from spectio import envfile
from spectio.catalog import KIND as CATALOG
from spectio.catalog import catalog_path
from spectio.config import Settings
from spectio.envfile import environments_path
from spectio_server import static
from spectio_server.api import (
    browser,
    cancel,
    catalog,
    environments,
    logs,
    problems,
    relaunch,
    results,
    runs_manage,
    runs_read,
    runs_write,
    stream,
    taskfiles,
    workdir,
    workflows,
)
from spectio_server.auth import host, middleware, routes, writes
from spectio_server.auth.secrets import ServerKey, SessionStore, TicketStore
from spectio_server.failure import Accounting, Measures
from spectio_server.files.pool import FilePool
from spectio_server.store.writer import Writer

PLACEHOLDER = "Spectio {version} is running.\n{why}\n"
API = "/api/v1"
API_VERSION = "0.0.1"  # the API document's version, not the package's: a release bump keeps it
# inbox #109 rule 5, Thomas 2026-11-08: never on a TCP port on SLURM and shared hosts
NO_API = (
    "The API is served on a TCP port only in local mode (spectio init --local), on a machine "
    "only you use: on a cluster or another shared host, other users could reach its port, so "
    "spectio serve serves it there on a Unix socket in its 0700 database directory."
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
    """Why the `/api/v1` routers may not be mounted on a TCP port here, or None when they may:
    `spectio serve` then listens on a Unix socket instead."""
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
    on_socket: bool = False,
) -> FastAPI:
    """The app; `files` is the pool the routes read run files in, `accounting` the server's
    one gate to `sacct` (each made from the settings when None), `server_key` the key of
    `auth/links` (one kept in memory only when None). `on_socket`: served on the Unix socket of
    `spectio serve`, so the API is mounted; on TCP, `no_api_reason` decides."""
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
    app.state.imaging_slots = results.ImagingSlots(results.IMAGING_SLOTS)  # api §5.3.1
    # dev-env §15.3 req. 15: its thread starts on the first job asked
    app.state.accounting = Accounting.from_settings(settings) if accounting is None else accounting
    app.state.measures = Measures()  # benchmarks of ended attempts, read once (CR-P3T34-01)
    app.state.engine_versions = workflows.EngineVersions(settings)
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

    # one scan, on TCP only: the start text reads it back (CR-P3T17-04)
    reason = None if on_socket else no_api_reason(settings)
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
        app.state.environments = environments.Store(
            environments_path(), envfile.ENVIRONMENTS, "environments"
        )  # §15.3 req. 18
        app.state.catalog = environments.Store(catalog_path(), CATALOG, "catalog")  # api §5.6
        routers = (
            workflows,
            runs_write,
            runs_manage,
            relaunch,
            runs_read,
            logs,
            taskfiles,
            results,
            workdir,
            cancel,
            environments,
            catalog,
        )
        for module in (*routers, stream):
            app.include_router(module.router, prefix=API)
    else:

        @app.api_route(API + "/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
        def absent(path: str) -> JSONResponse:
            return problems.problem(404, "not-found", "Not found", reason)

    return app
