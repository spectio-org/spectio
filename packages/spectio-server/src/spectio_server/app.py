"""The FastAPI app of `spectio serve` (P1 Tasks 11 and 17).

Sign-in (P1 Tasks 12 to 16: token link, session) is not built yet, so the API is served in local
mode only (`spectio init --local`): on a SLURM environment, where other
users share the login node and its loopback port, every `/api/v1` path answers 404 with the
reason (inbox #86). In local mode too, the API is left unmounted on a machine that looks like
a cluster node or a shared one (`shared_host`, SEC-P3T17-06): kind `local` is a configuration
value, which can be set on a login node. The Host allow-list and the write checks (dev-env §15.3
req. 4 and 7) run on every request already (`api.browser`). The generated docs stay off.
"""

import os
import pwd
import shutil
from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

from spectio.config import Settings
from spectio_server.api import browser, problems, runs_write, workflows
from spectio_server.store.writer import Writer

PLACEHOLDER = (
    "Spectio {version} is running.\n"
    "Sign-in comes with P1 Task 12 and the screens with Task 19: this build is local-only.\n"
)
API = "/api/v1"
NO_API = (
    "The API is served in local mode only (spectio init --local) until sign-in is built: "
    "P1 Tasks 12 to 16 (token link, session, CSRF and Host checks)."
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


def create_app(settings: Settings, writer: Writer) -> FastAPI:
    app = FastAPI(title="Spectio", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.writer = writer
    app.state.engine_versions = workflows.engine_versions(settings)
    page = PLACEHOLDER.format(version=version("spectio"))
    problems.install(app)
    browser.install(app)  # Host allow-list, cross-site and write checks (§15.3 req. 4, 7)

    @app.get("/", response_class=PlainTextResponse)
    def home() -> str:
        return page

    reason = no_api_reason(settings)  # one scan: the start text reads it back (CR-P3T17-04)
    app.state.no_api = reason
    if reason is None:
        app.include_router(workflows.router, prefix=API)
        app.include_router(runs_write.router, prefix=API)
    else:

        @app.api_route(API + "/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
        def absent(path: str) -> JSONResponse:
            return problems.problem(404, "not-found", "Not found", reason)

    return app
