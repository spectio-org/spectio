"""A session on every request (dev-env §15.3 req. 2; P1 Task 12).

Every request needs the session cookie that the link exchange set, or gets a 401 problem with
no data, whatever its path, before any route runs. Four routes are exempt (P1 Assumption 8):
the bootstrap page and its script, which carry no data, the exchange, which checks its ticket,
and `auth/links`, which checks the server key. The Host and write checks (`api.browser`) run
before this one.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from spectio_server.api.problems import problem

COOKIE = "spectio_session"  # TODO(P1 Task 13): its name carries the Host port (req. 3)
EXEMPT = frozenset(
    {
        ("GET", "/auth/link"),
        ("GET", "/auth/link.js"),
        ("POST", "/api/v1/auth/magic-links:exchange"),
        ("POST", "/api/v1/auth/links"),
    }
)


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
        secret = request.cookies.get(COOKIE)
        if secret is None or not request.app.state.sessions.valid(secret):
            return unauthenticated()
        return await call_next(request)
