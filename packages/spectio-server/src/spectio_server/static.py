"""The screens: the built `web/dist` (P1 Task 19), served at `/` beside the API.

Only the screen routes (`/`, `/runs`, `/launch`, `/runs/{run_id}`, the report viewer
`/runs/{run_id}/report` and the results browser `/runs/{run_id}/results`) answer `index.html`
(to `GET` and `HEAD`), and
only `/assets/<name>` answers a file: one plain name, a known web type, opened under `dist`
with `O_NOFOLLOW` at each step, so no symlink is followed and no path leaves the directory.
Hashed assets are cached for a year, `index.html` is revalidated, and every answer carries a
CSP that allows only this origin and no inline script (Mantine sets inline styles, so styles
allow them), with `Referrer-Policy: no-referrer` and `Cross-Origin-Opener-Policy: same-origin`
(SEC-P3T19-03). Every screen allows `frame-src 'self'`, for the report viewer's sandboxed
report, which the API serves with the CSP of req. 14 (P1 Task 31): a CSP is the document's, and
the viewer is also reached by in-app navigation from another screen's document (CR-P3T31-02);
the iframe's `sandbox` attribute and that CSP carry the protection. `app.create_app` mounts
these routes only with the API (inbox #80, #86).
"""

import logging
import os
import re
import stat
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response

from spectio_server.api.problems import not_found
from spectio_server.api.workflows import _open

log = logging.getLogger(__name__)


def _owned(path: Path) -> bool:
    """A directory, not a symlink, owned by this user and writable by no one else."""
    try:
        st = path.lstat()
    except OSError:
        return False
    return stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid() and not st.st_mode & 0o022


def find_dist(module: Path) -> Path:
    """The wheel's screens (hatch_build.py, P1 Task 21), else `web/dist` of the checkout that
    holds `module` (an editable install). The checkout is used only when it is the workspace
    (`packages/<name>/src/spectio_server/` under a `pyproject.toml`) and its root, `web` and
    `web/dist` are this user's and writable by no one else: a wheel without screens, installed
    anywhere, gets the "not built" page, never a `web/dist` another user planted (SEC-P3T21-02).
    A refused checkout whose screens are built logs which directory and why (CR-P3T21-02).
    """
    packaged = module.parent / "web"
    if (packaged / "index.html").is_file() or len(module.parents) < 5:
        return packaged
    root = module.parents[4]
    checkout = root / "web" / "dist"
    workspace = module.parents[3].name == "packages" and module.parents[1].name == "src"
    walk = (root, root / "web", checkout)
    if not (workspace and (root / "pyproject.toml").is_file()):
        return packaged
    refused = next((d for d in walk if not _owned(d)), None)
    if refused is None:
        return checkout
    if (checkout / "index.html").is_file():
        log.warning(
            "%s is group- or world-writable or not yours: chmod g-w,o-w %s", refused, refused
        )
    return packaged


DIST = find_dist(Path(__file__).resolve())
ROUTES = (
    "/",
    "/runs",
    "/launch",
    "/runs/{run_id}",
    "/runs/{run_id}/report",
    "/runs/{run_id}/results",
    "/runs/{run_id}/results/file",
)
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
    "form-action 'self'; frame-ancestors 'none'; frame-src 'self'"
)
HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    # Run URLs carry run IDs: send no referrer out, and keep pages opened from here apart.
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
}
NOT_BUILT = (
    "The screens are not built: run "
    "`npm --prefix web ci --ignore-scripts && npm --prefix web run build`, "
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
        app.add_api_route(route, index, methods=["GET", "HEAD"], include_in_schema=False)

    @app.api_route("/assets/{name}", methods=["GET", "HEAD"], include_in_schema=False)
    def asset(name: str) -> Response:
        media = TYPES.get(Path(name).suffix)
        body = read(dist, "assets", name) if ASSET.fullmatch(name) and media else None
        if body is None:
            raise not_found("No such file.")
        headers = {**HEADERS, "Cache-Control": "public, max-age=31536000, immutable"}
        return Response(body, media_type=media, headers=headers)
