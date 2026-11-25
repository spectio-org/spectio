"""`GET /health/live` and `GET /health/ready`, the probes of a container platform
(admin-and-operations.md §3.5, "Endpoints for orchestrators"; architecture-plugins-and-
packaging.md §7.5: the Helm probes).

Both are GET-only outside the API prefix and need no session, Origin or Referer: a platform
probes them, not a browser, so the session, cross-site and write checks stand aside on their
paths (`health.PATHS`); the Host allow-list still runs. `live` says only that the process
serves; `ready` reads the database and checks its schema revision, and its 503 reason is a
fixed sentence — no path, no secret, no stack trace.
"""

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from spectio.config import Settings
from spectio_server import health
from spectio_server.store.writer import Writer

from .conftest import client_for

LIVE = "/health/live"
READY = "/health/ready"


@pytest.fixture
def probe(settings: Settings, writer: Writer) -> TestClient:
    """A client with no session cookie and no Origin, like a platform's prober."""
    found = client_for(settings, writer, signed_in=False)
    found.headers.pop("Origin")
    return found


def test_live_needs_no_session(probe: TestClient) -> None:
    answer = probe.get(LIVE)
    assert answer.status_code == 200
    assert answer.json() == {"status": "ok"}
    assert answer.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "headers",
    [
        {"Sec-Fetch-Site": "cross-site"},
        {"Referer": "http://evil.example/"},
        {"Origin": "http://evil.example"},
    ],
)
def test_live_ignores_the_browser_checks(probe: TestClient, headers: dict[str, str]) -> None:
    """The cross-site refusal stands aside: a probe sends no browser headers (SEC-P3T17-02)."""
    assert probe.get(LIVE, headers=headers).status_code == 200


def test_ready_on_a_migrated_database(probe: TestClient) -> None:
    answer = probe.get(READY)
    assert answer.status_code == 200
    assert answer.json() == {"status": "ok"}
    assert answer.headers["cache-control"] == "no-store"


def test_a_write_is_refused_without_a_session_or_origin(probe: TestClient) -> None:
    """GET only: the routes themselves say 405, not the middlewares' 401 or 403."""
    assert probe.post(LIVE).status_code == 405
    assert probe.post(READY).status_code == 405


def test_ready_refuses_a_revision_this_release_does_not_support(
    probe: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health, "head_revision", lambda: "9999")
    answer = probe.get(READY)
    assert answer.status_code == 503
    body = answer.json()
    assert body["status"] == "unavailable"
    assert body["reason"] and "/" not in body["reason"]
    assert answer.headers["cache-control"] == "no-store"


def test_ready_when_the_database_read_fails(probe: TestClient, settings: Settings) -> None:
    probe.app.state.writer = SimpleNamespace(  # type: ignore[attr-defined]
        engine=create_engine("sqlite:////no-such-directory/spectio.db")
    )
    answer = probe.get(READY)
    assert answer.status_code == 503
    body: dict[str, Any] = answer.json()
    assert body["status"] == "unavailable"
    assert body["reason"] and "/" not in body["reason"]
    assert str(settings.db_dir) not in answer.text
