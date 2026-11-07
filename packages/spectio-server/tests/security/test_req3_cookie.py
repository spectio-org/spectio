"""dev-env §15.3 req. 3: the session cookie (P1 Task 13).

It is `HttpOnly`, `SameSite=Strict`, `Path=/` and has no `Domain`; its name carries the port of
the `Host` header, as Jupyter's does, so two tunnelled servers on different local ports do not
overwrite each other's cookie. The browser behaviours marked [to be validated] in req. 3 stay with
the spike sec-single-mode and the Playwright smoke.
"""

import pytest
from fastapi.testclient import TestClient

from spectio.config import Settings
from spectio_server import app as app_mod
from spectio_server.auth.middleware import cookie_name
from spectio_server.store.writer import Writer

from ..api.conftest import client_for

EXCHANGE = "/api/v1/auth/magic-links:exchange"


@pytest.fixture(autouse=True)
def lone_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mount the API, as on one person's machine (SEC-P3T17-06)."""
    monkeypatch.setattr(app_mod, "shared_host", lambda: None)


@pytest.fixture
def client(settings: Settings, writer: Writer) -> TestClient:
    """The app, signed out."""
    return client_for(settings, writer, signed_in=False)


def _on(client: TestClient, host: str) -> TestClient:
    """The same app, reached as `http://<host>` (a tunnel on another local port)."""
    origin = f"http://{host}"
    return TestClient(client.app, base_url=origin, headers={"Origin": origin})


def _sign_in(client: TestClient) -> str:
    ticket = client.app.state.tickets.mint()  # type: ignore[attr-defined]
    answer = client.post(EXCHANGE, json={"ticket": ticket})
    assert answer.status_code == 204
    cookie: str = answer.headers["set-cookie"]
    return cookie


@pytest.mark.parametrize(
    ("host", "name"),
    [
        ("127.0.0.1:41234", "spectio_session_41234"),
        ("localhost:8080", "spectio_session_8080"),
        ("[::1]:5", "spectio_session_5"),
        ("127.0.0.1", "spectio_session_80"),
        ("localhost", "spectio_session_80"),
        ("[::1]", "spectio_session_80"),
        ("", "spectio_session_80"),
        ("127.0.0.1:", "spectio_session_80"),
        ("127.0.0.1:\uff19\uff10\uff10\uff11", "spectio_session_80"),  # fullwidth 9001: no port
        ("127.0.0.1:²", "spectio_session_80"),
        ("127.0.0.1:12a", "spectio_session_80"),
    ],
)
def test_req3_cookie_name(host: str, name: str) -> None:
    assert cookie_name(host) == name


def test_req3_attributes(client: TestClient) -> None:
    attributes = [a.strip().lower() for a in _sign_in(client).split(";")]
    assert "httponly" in attributes
    assert "samesite=strict" in attributes
    assert "path=/" in attributes
    assert not any(a.startswith("domain") for a in attributes)


def test_req3_name_has_host_port(client: TestClient) -> None:
    on_9001 = _on(client, "127.0.0.1:9001")
    assert _sign_in(on_9001).startswith("spectio_session_9001=")
    assert on_9001.get("/api/v1/runs").status_code == 200  # the client sends it back


def test_req3_other_port_cookie_ignored(client: TestClient) -> None:
    on_9001 = _on(client, "127.0.0.1:9001")
    _sign_in(on_9001)
    secret = on_9001.cookies["spectio_session_9001"]
    on_9002 = _on(client, "127.0.0.1:9002")
    on_9002.cookies.set("spectio_session_9001", secret)  # a browser sends every port's cookies
    answer = on_9002.get("/api/v1/runs")
    assert answer.status_code == 401
    assert answer.json()["type"] == "/problems/unauthenticated"
    on_9002.cookies.set("spectio_session_9002", secret)
    assert on_9002.get("/api/v1/runs").status_code == 200  # one server, so the secret is valid
