"""The Host allow-list, before any other check (dev-env §15.3 req. 4; P1 Task 14).

`Host` names `127.0.0.1`, `localhost` or `[::1]`, on any port or none (a tunnel's local port
can differ from the server's), case-insensitively, or the request is refused with 400 before the
session check, the bootstrap routes included, against DNS rebinding. `parse` is the one reading
of `Host`: the session cookie name (`auth.middleware.cookie_name`, req. 3) takes its port, so the
allow-list and the cookie never read two different ports (SEC-P3T13-01).
"""

import re
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from spectio_server.api.problems import problem

LOOPBACK = frozenset({"127.0.0.1", "localhost", "[::1]"})
# RFC 9110 §7.2: uri-host [ ":" port ]; a bracketed IPv6 literal, or a name without colons
HOST = re.compile(r"(\[[^\[\]]*\]|[^:\[\]]*)(?::([0-9]{0,5}))?")
MAX_PORT = 65535


def parse(host_header: str | None) -> tuple[str, str | None] | None:
    """`LocalHost:8080` → `("localhost", "8080")`, `[::1]` → `("[::1]", None)`; an empty port is
    no port. None for a missing or malformed `Host`, or a port above 65535."""
    found = HOST.fullmatch(host_header or "")
    if not host_header or found is None:
        return None
    name, port = found.group(1).lower(), found.group(2) or None
    if port is not None and int(port) > MAX_PORT:
        return None
    return name, port


def host_allowed(host_header: str | None) -> bool:
    parsed = parse(host_header)
    return parsed is not None and parsed[0] in LOOPBACK


def install(app: FastAPI) -> None:
    """Install last, so that it runs first (Starlette runs the last middleware outermost)."""

    @app.middleware("http")
    async def check(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not host_allowed(request.headers.get("host")):
            return problem(
                400, "host-not-allowed", "Host not allowed", "Open Spectio on 127.0.0.1."
            )
        return await call_next(request)
