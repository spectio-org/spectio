"""RFC 9457 problem details for the API (api §4.1; P1 Global Constraints).

0.0.1 sends `validation-failed` with `errors: [{field, message}]`, the shape of P1 Task 17, where
`field` is a dotted path into the request (`workflow.location`, `params.chunks`), not the JSON
Pointer of api §4.1 (inbox #86). The framework's own refusals are problems too (FU-P3-17): an
unknown path is `not-found`, a body it cannot parse (too deep for the JSON parser) is
`validation-failed` on `body`, and any other status, such as 405, has the RFC 9457 type
`about:blank` with the status phrase as its title, since api §4.1 has no slug for it.
"""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

PROBLEM_JSON = "application/problem+json"


class Invalid(Exception):
    """A request the API refuses with `422 validation-failed`; each error names its field."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.errors = [{"field": field, "message": message}]

    @classmethod
    def many(cls, errors: list[dict[str, str]]) -> "Invalid":
        found = cls(errors[0]["field"], errors[0]["message"])
        found.errors = errors
        return found

    def under(self, prefix: str) -> "Invalid":
        """The same errors, their fields under `prefix` (`location` → `workflow.location`)."""
        return Invalid.many([{**e, "field": f"{prefix}.{e['field']}"} for e in self.errors])


class Problem(Exception):
    """A request the API answers with this problem (api §4.1 catalogue)."""

    def __init__(self, status: int, slug: str, title: str, detail: str) -> None:
        super().__init__(detail)
        self.status, self.slug, self.title, self.detail = status, slug, title, detail


def not_found(detail: str, slug: str = "not-found") -> Problem:
    return Problem(404, slug, "Not found", detail)


def problem(status: int, slug: str, title: str, detail: str, **extra: Any) -> JSONResponse:
    body = {"type": f"/problems/{slug}", "title": title, "status": status, "detail": detail}
    return JSONResponse({**body, **extra}, status_code=status, media_type=PROBLEM_JSON)


def _field(loc: tuple[int | str, ...]) -> str:
    """`("body", "workflow", "engine")` → `workflow.engine`; `("query", "location")` →
    `location`."""
    parts = [str(p) for p in loc[1:]] if loc and loc[0] in ("body", "query") else []
    return ".".join(parts) or "body"


def install(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    def known(request: Request, exc: Problem) -> JSONResponse:
        return problem(exc.status, exc.slug, exc.title, exc.detail)

    @app.exception_handler(Invalid)
    def invalid(request: Request, exc: Invalid) -> JSONResponse:
        detail = "; ".join(f"{e['field']}: {e['message']}" for e in exc.errors)
        return problem(422, "validation-failed", "Validation failed", detail, errors=exc.errors)

    @app.exception_handler(RequestValidationError)
    def malformed(request: Request, exc: RequestValidationError) -> JSONResponse:
        # The message only: pydantic's `input` would echo the value back (SEC-P3T11-06 (r1)).
        errors = [{"field": _field(tuple(e["loc"])), "message": e["msg"]} for e in exc.errors()]
        return invalid(request, Invalid.many(errors))

    @app.exception_handler(HTTPException)
    def framework(request: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code == 400:  # FastAPI's only 400: a body it could not parse
            return invalid(request, Invalid("body", "the body could not be parsed as JSON"))
        if exc.status_code == 404:
            return problem(404, "not-found", "Not found", str(exc.detail))
        status, title = exc.status_code, HTTPStatus(exc.status_code).phrase
        body = {"type": "about:blank", "title": title, "status": status, "detail": str(exc.detail)}
        # exc.headers keeps a 405's Allow header
        return JSONResponse(body, status, headers=exc.headers, media_type=PROBLEM_JSON)
