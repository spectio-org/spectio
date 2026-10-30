"""Browser checks on every request, before any route (dev-env §15.3 req. 4 and 7; inbox #37).

- **Host allow-list** (req. 4): the `Host` name is `127.0.0.1`, `localhost` or `[::1]`, any port,
  or the request is refused with 400, against DNS rebinding.
- **No cross-site request** (stands in for the `SameSite=Strict` session of req. 3 until P1
  Tasks 12 to 16; SEC-P3T17-02): `Sec-Fetch-Site: cross-site` or `same-site`, or an `Origin` or
  `Referer` other than this loopback origin, is refused with 403. A `GET` such as inspect clones
  a repository, so another site's `<img src>` must not reach it.
- **Writes** (req. 7): a method other than `GET` and `HEAD` needs `Origin` equal to
  `http://<Host>` (403), and a body of type `application/json` (415), with a `Content-Length`
  (411) of at most 1 MiB (413; FU-P3-17).
"""

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Response

from spectio_server.api.problems import problem

LOOPBACK = frozenset({"127.0.0.1", "localhost", "[::1]"})
MAX_BODY = 1048576


def _netloc(url: str) -> str | None:
    try:
        return urlsplit(url).netloc.lower()
    except ValueError:  # `http://[`: malformed, so not this origin
        return None


def _name(host: str) -> str:
    """`localhost:8080` → `localhost`; `[::1]:8080` → `[::1]`."""
    host = host.lower()
    return (
        host[: host.index("]") + 1] if host.startswith("[") and "]" in host else host.split(":")[0]
    )


def refusal(request: Request) -> Response | None:
    host = request.headers.get("host", "")
    if _name(host) not in LOOPBACK:
        return problem(400, "host-not-allowed", "Host not allowed", "Open Spectio on 127.0.0.1.")
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    same = f"http://{host.lower()}"
    if (
        request.headers.get("sec-fetch-site") in ("cross-site", "same-site")
        or (origin is not None and origin.lower() != same)
        or (referer is not None and f"http://{_netloc(referer)}" != same)
    ):
        return problem(
            403, "cross-site", "Cross-site request", "Requests from other sites are refused."
        )
    if request.method in ("GET", "HEAD"):
        return None
    if origin is None:
        return problem(403, "cross-site", "Origin required", "A write needs an Origin header.")
    length = request.headers.get("content-length")
    if "transfer-encoding" in request.headers:
        return problem(411, "length-required", "Length required", "Send a Content-Length.")
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
    @app.middleware("http")
    async def check(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        return refusal(request) or await call_next(request)
