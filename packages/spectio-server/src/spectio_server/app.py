"""The FastAPI app of `spectio serve` (P1 Tasks 11 and 17).

Sign-in (P1 Tasks 12 to 16: token link, session, CSRF, Host allow-list) is not built yet, so the
API is served in local mode only (`spectio init --local`): on a SLURM environment, where other
users share the login node and its loopback port, every `/api/v1` path answers 404 with the
reason (inbox #86). The generated docs stay off.
"""

from importlib.metadata import version

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

from spectio.config import Settings
from spectio_server.api import problems, runs_write, workflows
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


def create_app(settings: Settings, writer: Writer) -> FastAPI:
    app = FastAPI(title="Spectio", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.writer = writer
    app.state.engine_versions = workflows.engine_versions(settings)
    page = PLACEHOLDER.format(version=version("spectio"))
    problems.install(app)

    @app.get("/", response_class=PlainTextResponse)
    def home() -> str:
        return page

    if settings.executor == "local":
        app.include_router(workflows.router, prefix=API)
        app.include_router(runs_write.router, prefix=API)
    else:

        @app.api_route(API + "/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
        def absent(path: str) -> JSONResponse:
            return problems.problem(404, "not-found", "Not found", NO_API)

    return app
