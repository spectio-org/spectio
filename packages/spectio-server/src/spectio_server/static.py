"""The screens: the built `web/dist` (P1 Task 19), served at `/` beside the API.

Only the four screen routes (`/`, `/runs`, `/launch`, `/runs/{run_id}`) answer `index.html`, and
only `/assets/<name>` answers a file: one plain name, a known web type, opened under `dist`
with `O_NOFOLLOW` at each step, so no symlink is followed and no path leaves the directory.
Hashed assets are cached for a year, `index.html` is revalidated, and every answer carries a
CSP that allows only this origin and no inline script (Mantine sets inline styles, so styles
allow them). `app.create_app` mounts these routes only with the API (inbox #80, #86).
"""

import os
import re
import stat
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response

from spectio_server.api.problems import not_found
from spectio_server.api.workflows import _open

# TODO(P1 Task 21): the wheel ships the screens as package data; read them from there first.
DIST = Path(__file__).resolve().parents[4] / "web" / "dist"
ROUTES = ("/", "/runs", "/launch", "/runs/{run_id}")
ASSET = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,199}")
TYPES = {
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".woff2": "font/woff2",
}
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self'; font-src 'self'; connect-src 'self'; base-uri 'none'; "
    "form-action 'self'; frame-ancestors 'none'"
)
HEADERS = {"Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff"}
NOT_BUILT = (
    "The screens are not built: run `npm --prefix web ci && npm --prefix web run build`, "
    "then start spectio serve again."
)


def read(root: Path, *parts: str) -> bytes | None:
    """A regular file under `root`, reached through no symlink (`root` included), or None."""
    try:
        fd = _open(root.parent, root.name, *parts)
    except OSError:
        return None
    with os.fdopen(fd, "rb") as f:
        try:
            return f.read() if stat.S_ISREG(os.fstat(fd).st_mode) else None
        except OSError:
            return None


def built(dist: Path) -> bool:
    return read(dist, "index.html") is not None


def install(app: FastAPI, dist: Path) -> None:
    def index() -> Response:
        page = read(dist, "index.html")
        if page is None:
            raise not_found("The screens are not built.")
        headers = {**HEADERS, "Cache-Control": "no-cache"}
        return Response(page, media_type="text/html; charset=utf-8", headers=headers)

    for route in ROUTES:
        app.add_api_route(route, index, methods=["GET"], include_in_schema=False)

    @app.get("/assets/{name}", include_in_schema=False)
    def asset(name: str) -> Response:
        media = TYPES.get(Path(name).suffix)
        body = read(dist, "assets", name) if ASSET.fullmatch(name) and media else None
        if body is None:
            raise not_found("No such file.")
        headers = {**HEADERS, "Cache-Control": "public, max-age=31536000, immutable"}
        return Response(body, media_type=media, headers=headers)
