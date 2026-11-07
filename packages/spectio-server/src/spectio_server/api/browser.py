"""No cross-site request, on every request, before the session check (dev-env §15.3 req. 7;
SEC-P3T17-02; inbox #37). The Host allow-list (req. 4, `auth.host`) runs before it, so `Host`
here is a loopback one; the write checks of req. 7 (`auth.writes`) run after the session check.

`Sec-Fetch-Site: cross-site` or `same-site`, or an `Origin` or `Referer` other than this loopback
origin, is refused with 403, a `GET` too. A `GET` such as inspect clones a repository, so another
site's `<img src>` must not reach it. The `SameSite=Strict` cookie (req. 3) does not cover a page
on another port of the same loopback host: a site ignores the port ([HTML standard, "same
site"](https://html.spec.whatwg.org/multipage/browsers.html#same-site) **[to be validated]**), so
this check stays.
"""

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Response

from spectio_server.api.problems import problem


def _netloc(url: str) -> str | None:
    try:
        return urlsplit(url).netloc.lower()
    except ValueError:  # `http://[`: malformed, so not this origin
        return None


def refusal(request: Request) -> Response | None:
    host = request.headers.get("host", "")
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
    return None


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def check(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        return refusal(request) or await call_next(request)
