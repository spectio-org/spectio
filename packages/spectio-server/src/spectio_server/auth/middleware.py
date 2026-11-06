"""A session on every request (dev-env §15.3 req. 2; P1 Task 12).

Every request needs the session cookie that the link exchange set, named after the `Host` port
(`cookie_name`, req. 3; P1 Task 13), or gets a 401 problem with
no data, whatever its path, before any route runs. Four routes are exempt (P1 Assumption 8):
the bootstrap page and its script, which carry no data, the exchange, which checks its ticket,
and `auth/links`, which checks the server key. The Host allow-list (`auth.host`, req. 4), then
the cross-site and write checks (`api.browser`), run before this one.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from spectio_server.api.problems import problem
from spectio_server.auth import host

COOKIE = "spectio_session"
EXEMPT = frozenset(
    {
        ("GET", "/auth/link"),
        ("GET", "/auth/link.js"),
        ("POST", "/api/v1/auth/magic-links:exchange"),
        ("POST", "/api/v1/auth/links"),
    }
)


def cookie_name(host_header: str | None) -> str:
    """The session cookie of `Host`, named after its port as Jupyter's is (req. 3):
    `127.0.0.1:41234` → `spectio_session_41234`; a `Host` with no port → `spectio_session_80`.
    The port is the one the allow-list read (`host.parse`, SEC-P3T13-01); a `Host` it refuses
    never gets here, and gets `spectio_session_80` too."""
    parsed = host.parse(host_header)
    port = parsed[1] if parsed is not None and parsed[1] is not None else "80"
    return f"{COOKIE}_{port}"


def unauthenticated() -> Response:
    return problem(
        401,
        "unauthenticated",
        "Sign-in required",
        "Open the link that spectio serve printed, or run spectio login --print-link.",
    )


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def session(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if (request.method, request.url.path) in EXEMPT:
            return await call_next(request)
        secret = request.cookies.get(cookie_name(request.headers.get("host")))
        if secret is None or not request.app.state.sessions.valid(secret):
            return unauthenticated()
        return await call_next(request)
