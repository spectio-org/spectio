"""Writes need Origin and JSON (dev-env §15.3 req. 7; P1 Task 16; inbox #37).

A method other than `GET` and `HEAD` needs `Origin` equal to `http://<Host>`, port included (403),
and a body of type `application/json` (415), with a `Content-Length` (411) of at most 1 MiB (413;
FU-P3-17); a request with no body, such as `:cancel`, needs only the Origin. The Host allow-list
(req. 4, `auth.host`), the cross-site check (`api.browser`) and the session check (req. 2,
`auth.middleware`) run before this one, so a request with no session gets a 401 and learns
nothing of these rules. The two session-exempt writes, the exchange and `auth/links`, are
checked here all the same. No route sends a CORS header, so a cross-site preflight is never
granted.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from spectio_server.api.problems import problem

MAX_BODY = 1048576


def refusal(request: Request) -> Response | None:
    if request.method in ("GET", "HEAD"):
        return None
    origin = request.headers.get("origin")
    if origin is None:
        return problem(403, "cross-site", "Origin required", "A write needs an Origin header.")
    if origin.lower() != f"http://{request.headers.get('host', '').lower()}":
        return problem(
            403, "cross-site", "Cross-site request", "Writes from other sites are refused."
        )
    if "transfer-encoding" in request.headers:
        return problem(411, "length-required", "Length required", "Send a Content-Length.")
    length = request.headers.get("content-length")
    media = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if length not in (None, "0") and media != "application/json":
        return problem(
            415, "unsupported-media-type", "Unsupported media type", "Send application/json."
        )
    if length is not None and not (
        length.isascii() and length.isdigit() and int(length) <= MAX_BODY
    ):
        return problem(413, "request-too-large", "Request too large", f"At most {MAX_BODY} bytes.")
    return None


def install(app: FastAPI) -> None:
    """Install first, so that it runs last (Starlette runs the last middleware outermost)."""

    @app.middleware("http")
    async def check(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        return refusal(request) or await call_next(request)
