"""The token link (dev-env §15.3 "Access" and req. 2; auth §2.1; P1 Task 12).

- `GET /auth/link` and `GET /auth/link.js`: the bootstrap page, static, with no data. Its script
  reads the ticket from the fragment, drops it from the history and posts the exchange.
- `POST /api/v1/auth/magic-links:exchange` (`{"ticket"}`): burns the ticket and answers 204 with
  the session cookie (`HttpOnly`, `SameSite=Strict`, `Path=/`, named after the `Host` port:
  req. 3); a used, expired or unknown ticket gets 401 `/problems/link-expired`.
- `POST /api/v1/auth/links` (`Authorization: Bearer <server key>`): a new link, for
  `spectio login --print-link`. The key gives a link, never a session.

All four answer `Cache-Control: no-store`, `Referrer-Policy: no-referrer` and a CSP of this
origin only. The session middleware lets these four through (`middleware.EXEMPT`).
"""

from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from spectio_server.api.problems import problem
from spectio_server.auth.middleware import cookie_name

STATIC = Path(__file__).parent / "static"
PAGE = (STATIC / "link.html").read_bytes()
SCRIPT = (STATIC / "link.js").read_bytes()
HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'",
    "X-Content-Type-Options": "nosniff",
}
NO_PASTE = "Spectio never asks you to paste a link."  # dev-env §15.3 req. 14, the viewer
EXPIRED = (
    "This link was already used or has expired. Run `spectio login --print-link` on the "
    "cluster for a new one."
)


def link_url(port: int, ticket: str) -> str:
    return f"http://127.0.0.1:{port}/auth/link#{ticket}"


pages = APIRouter(include_in_schema=False)
router = APIRouter(tags=["auth"])


@pages.get("/auth/link")
def link_page() -> Response:
    return Response(PAGE, media_type="text/html; charset=utf-8", headers=HEADERS)


@pages.get("/auth/link.js")
def link_script() -> Response:
    return Response(SCRIPT, media_type="text/javascript; charset=utf-8", headers=HEADERS)


class Exchange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket: str = Field(max_length=128)


class Link(BaseModel):
    url: str


def _refused(slug: str, title: str, detail: str) -> JSONResponse:
    answer = problem(401, slug, title, detail)
    answer.headers.update(HEADERS)
    return answer


@router.post(
    "/auth/magic-links:exchange",
    status_code=204,
    response_class=Response,
    responses={401: {"description": "The ticket was already used, has expired or is unknown"}},
)
def exchange(body: Exchange, request: Request) -> Response:
    state = request.app.state
    if not state.tickets.burn(body.ticket):
        return _refused("link-expired", "Link used or expired", EXPIRED)
    answer = Response(status_code=204, headers=HEADERS)
    name = cookie_name(request.headers.get("host"))  # no Domain: this host only (req. 3)
    answer.set_cookie(name, state.sessions.create(), httponly=True, samesite="strict", path="/")
    return answer


@router.post(
    "/auth/links",
    response_model=Link,
    responses={401: {"description": "No server key, or another one"}},
)
def new_link(request: Request) -> Response:
    state = request.app.state
    scheme, _, key = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not state.server_key.matches(key):
        return _refused("unauthenticated", "Server key required", "Send the server key.")
    url = link_url(state.settings.port, state.tickets.mint())
    return JSONResponse({"url": url}, headers=HEADERS)
