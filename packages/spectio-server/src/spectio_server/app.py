"""The FastAPI app of `spectio serve` (P1 Task 11).

It serves no data yet: the API comes with P1 Tasks 17 and 18, behind the session that Task 12
brings. Until then the only route is a plain page that says so, and the generated docs are off,
so the app shows nothing to another user of the machine who reaches the loopback port.
"""

from importlib.metadata import version

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from spectio.config import Settings

PLACEHOLDER = (
    "Spectio {version} is running.\n"
    "Sign-in comes with P1 Task 12 and the screens with Task 19: this build is local-only.\n"
)


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Spectio", docs_url=None, redoc_url=None, openapi_url=None)
    page = PLACEHOLDER.format(version=version("spectio"))

    @app.get("/", response_class=PlainTextResponse)
    def home() -> str:
        return page

    return app
