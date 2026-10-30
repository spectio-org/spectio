"""RFC 9457 problem details for the API (api §4.1; P1 Global Constraints).

0.0.1 sends `validation-failed` with `errors: [{field, message}]`, the shape of P1 Task 17, where
`field` is a dotted path into the request (`workflow.location`, `params.chunks`), not the JSON
Pointer of api §4.1 (inbox #86).
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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


def problem(status: int, slug: str, title: str, detail: str, **extra: Any) -> JSONResponse:
    body = {"type": f"/problems/{slug}", "title": title, "status": status, "detail": detail}
    return JSONResponse({**body, **extra}, status_code=status, media_type=PROBLEM_JSON)


def _field(loc: tuple[int | str, ...]) -> str:
    """`("body", "workflow", "engine")` → `workflow.engine`; `("query", "location")` →
    `location`."""
    parts = [str(p) for p in loc[1:]] if loc and loc[0] in ("body", "query") else []
    return ".".join(parts) or "body"


def install(app: FastAPI) -> None:
    @app.exception_handler(Invalid)
    def invalid(request: Request, exc: Invalid) -> JSONResponse:
        detail = "; ".join(f"{e['field']}: {e['message']}" for e in exc.errors)
        return problem(422, "validation-failed", "Validation failed", detail, errors=exc.errors)

    @app.exception_handler(RequestValidationError)
    def malformed(request: Request, exc: RequestValidationError) -> JSONResponse:
        # The message only: pydantic's `input` would echo the value back (SEC-P3T11-06 (r1)).
        errors = [{"field": _field(tuple(e["loc"])), "message": e["msg"]} for e in exc.errors()]
        return invalid(request, Invalid.many(errors))
