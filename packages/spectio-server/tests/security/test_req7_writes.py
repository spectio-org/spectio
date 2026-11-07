"""dev-env §15.3 req. 7: writes need Origin and JSON (P1 Task 16; inbox #37).

Every method other than `GET` and `HEAD` needs an `Origin` equal to `http://<Host>`, port
included (403), and a body of type `application/json` (415); a request with no body, such as
`:cancel`, needs only the Origin. The check runs after the Host allow-list (req. 4) and the
session check (req. 2), and covers the two session-exempt writes, the exchange and
`auth/links`, too. No route sends a CORS header.
"""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from spectio.config import Settings
from spectio_server import app as app_mod
from spectio_server.auth import writes
from spectio_server.auth.middleware import cookie_name
from spectio_server.store.writer import Writer

from ..api.conftest import client_for

RUNS = "/api/v1/runs"
CANCEL = "/api/v1/runs/run_01K8T2F1XTVRES000000000000:cancel"  # no such run: 404
EXCHANGE = "/api/v1/auth/magic-links:exchange"
LINKS = "/api/v1/auth/links"


@pytest.fixture(autouse=True)
def lone_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mount the API, as on one person's machine (SEC-P3T17-06)."""
    monkeypatch.setattr(app_mod, "shared_host", lambda: None)


@pytest.fixture
def authed_client(settings: Settings, writer: Writer) -> TestClient:
    """Signed in, on `Host: 127.0.0.1:<port>`, with the matching `Origin`."""
    return client_for(settings, writer)


BODY = json.dumps({"workflow": {"location": "/pipelines/nextflow", "engine": "nextflow"}})


def slug(answer: Any) -> str:
    kind: str = answer.json()["type"]
    return kind.rsplit("/", 1)[-1]


def test_req7_missing_origin_403(authed_client: TestClient) -> None:
    del authed_client.headers["origin"]
    answer = authed_client.post(CANCEL)
    assert answer.status_code == 403
    assert slug(answer) == "cross-site"


@pytest.mark.parametrize("origin", ["https://evil.example", "null", "http://evil.example"])
def test_req7_foreign_origin_403(authed_client: TestClient, origin: str) -> None:
    assert authed_client.post(CANCEL, headers={"Origin": origin}).status_code == 403


def test_req7_origin_port_must_match_host(authed_client: TestClient, settings: Settings) -> None:
    for origin in (
        f"http://127.0.0.1:{settings.port + 1}",  # another port
        "http://127.0.0.1",  # no port
        f"http://localhost:{settings.port}",  # another loopback name, same port
        f"https://127.0.0.1:{settings.port}",  # another scheme
    ):
        assert authed_client.post(CANCEL, headers={"Origin": origin}).status_code == 403, origin
    sessions = authed_client.app.state.sessions  # type: ignore[attr-defined]
    authed_client.cookies.set(cookie_name("127.0.0.1:8080"), sessions.create())
    other = {"Host": "127.0.0.1:8080", "Origin": "http://127.0.0.1:9000"}  # the plan's case
    assert authed_client.post(CANCEL, headers=other).status_code == 403


@pytest.mark.parametrize(
    "content_type", ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data", None]
)
def test_req7_body_needs_json_415(authed_client: TestClient, content_type: str | None) -> None:
    headers = {} if content_type is None else {"Content-Type": content_type}
    answer = authed_client.post(RUNS, content=BODY, headers=headers)
    assert answer.status_code == 415, answer.text
    assert slug(answer) == "unsupported-media-type"


def test_req7_bodyless_cancel_needs_origin_only(authed_client: TestClient) -> None:
    answer = authed_client.post(CANCEL)
    assert answer.status_code not in (403, 415), answer.text
    assert answer.status_code == 404


def test_req7_get_head_unaffected(authed_client: TestClient) -> None:
    del authed_client.headers["origin"]
    plain = {"Content-Type": "text/plain"}
    assert authed_client.get(RUNS, headers=plain).status_code == 200
    assert authed_client.head(RUNS).status_code == 405  # the route's answer: not refused here


def test_req7_body_size_limits(authed_client: TestClient) -> None:
    big = {"Content-Type": "application/json", "Content-Length": str(writes.MAX_BODY + 1)}
    assert authed_client.post(RUNS, content=b"{}", headers=big).status_code == 413


def test_req7_runs_after_the_session_check(settings: Settings, writer: Writer) -> None:
    """Signed out, a write with no Origin and a form body is a 401: the session check comes
    first, so a request with no session learns nothing of the write rules."""
    signed_out = client_for(settings, writer, signed_in=False)
    del signed_out.headers["origin"]
    answer = signed_out.post(RUNS, content="a=1", headers={"Content-Type": "text/plain"})
    assert answer.status_code == 401
    assert slug(answer) == "unauthenticated"


@pytest.mark.parametrize("path", [EXCHANGE, LINKS])
def test_req7_covers_the_session_exempt_writes(
    settings: Settings, writer: Writer, path: str
) -> None:
    """The exchange and `auth/links` skip the session check, not the write check."""
    client = client_for(settings, writer, signed_in=False)
    ticket = client.app.state.tickets.mint()  # type: ignore[attr-defined]
    key = {"Authorization": f"Bearer {client.app.state.server_key.value}"}  # type: ignore[attr-defined]
    payload = json.dumps({"ticket": ticket})
    form = {"Content-Type": "text/plain", **key}
    assert client.post(path, content=payload, headers=form).status_code == 415
    del client.headers["origin"]
    assert client.post(path, json={"ticket": ticket}, headers=key).status_code == 403
    assert client.app.state.tickets.burn(ticket)  # type: ignore[attr-defined]  # still unused


def test_req7_no_cors_headers(authed_client: TestClient, settings: Settings) -> None:
    """A preflight from another site gets no grant; no answer carries a CORS header."""
    preflight = {
        "Origin": "http://evil.example",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    answers = [
        authed_client.options(RUNS, headers=preflight),
        authed_client.get(RUNS),
        authed_client.post(CANCEL),
        authed_client.get("/auth/link"),
    ]
    for answer in answers:
        assert not [h for h in answer.headers if h.lower().startswith("access-control-")]
    assert answers[0].status_code == 403
