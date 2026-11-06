"""dev-env §15.3 req. 4: the Host allow-list (P1 Task 14).

`Host` names `127.0.0.1`, `localhost` or `[::1]`, on any port or none, or the request is refused
with 400 before the session check, the bootstrap routes included, against DNS rebinding. One
parser reads `Host` for the allow-list and for the session cookie name (req. 3), so both read the
same port (SEC-P3T13-01, FU-P3-40).
"""

import pytest
from fastapi.testclient import TestClient

from spectio.config import Settings
from spectio_server import app as app_mod
from spectio_server.auth.host import host_allowed
from spectio_server.auth.middleware import EXEMPT, cookie_name
from spectio_server.store.writer import Writer

from ..api.conftest import client_for


@pytest.fixture(autouse=True)
def lone_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mount the API, as on one person's machine (SEC-P3T17-06)."""
    monkeypatch.setattr(app_mod, "shared_host", lambda: None)


@pytest.fixture
def authed_client(settings: Settings, writer: Writer) -> TestClient:
    return client_for(settings, writer)


@pytest.mark.parametrize(
    "h", ["127.0.0.1:8080", "localhost:41234", "[::1]:5", "LOCALHOST", "127.0.0.1", "[::1]"]
)
def test_req4_loopback_accepted(h: str) -> None:
    assert host_allowed(h)


@pytest.mark.parametrize(
    "h",
    [
        "evil.example:8080",
        "127.0.0.1.evil.example",
        "0.0.0.0:8080",
        "localhost.",
        "[::ffff:127.0.0.1]",
        "",
        None,
        # the odd values of SEC-P3T13-01: the old allow-list passed them
        "localhost:1:2",
        "localhost:abc",
        "[::1]x:5",
        "127.0.0.1:099999999",
        "127.0.0.1:65536",
        "127.0.0.1:\uff19\uff10\uff10\uff11",  # fullwidth 9001
        "127.0.0.1:²",
        " localhost",
        "localhost:80 ",
    ],
)
def test_req4_others_refused(h: str | None) -> None:
    assert not host_allowed(h)


@pytest.mark.parametrize(
    ("h", "name"),
    [
        ("127.0.0.1:41234", "spectio_session_41234"),
        ("[::1]:5", "spectio_session_5"),
        ("LOCALHOST:9001", "spectio_session_9001"),
        ("localhost", "spectio_session_80"),
        ("127.0.0.1:", "spectio_session_80"),  # an empty port is no port (RFC 3986 §3.2.3)
    ],
)
def test_req4_cookie_name_reads_the_allowed_port(h: str, name: str) -> None:
    """Every `Host` that passes the allow-list names its cookie after the port it parsed."""
    assert host_allowed(h)
    assert cookie_name(h) == name


@pytest.mark.parametrize("path", ["/api/v1/runs", "/"])
def test_req4_refused_before_auth(authed_client: TestClient, settings: Settings, path: str) -> None:
    """A valid session cookie for this name and port, and `Host` evil.example: no data. The
    cross-site header would get a 403 from `api.browser`: the Host check runs first."""
    host = f"evil.example:{settings.port}"
    authed_client.cookies.set(cookie_name(host), authed_client.app.state.sessions.create())  # type: ignore[attr-defined]
    headers = {"Host": host, "Origin": f"http://{host}", "Sec-Fetch-Site": "cross-site"}
    answer = authed_client.get(path, headers=headers)
    assert answer.status_code == 400
    assert answer.json()["type"].endswith("/host-not-allowed")
    assert "runs" not in answer.json() and "set-cookie" not in answer.headers


@pytest.mark.parametrize(("method", "path"), sorted(EXEMPT))
def test_req4_bootstrap_routes_checked_too(
    settings: Settings, writer: Writer, method: str, path: str
) -> None:
    """The four routes the session check exempts are behind the Host check all the same."""
    client = client_for(settings, writer, signed_in=False)
    ticket = client.app.state.tickets.mint()  # type: ignore[attr-defined]
    host = "evil.example"
    answer = client.request(
        method, path, json={"ticket": ticket}, headers={"Host": host, "Origin": f"http://{host}"}
    )
    assert answer.status_code == 400
    assert "set-cookie" not in answer.headers
    assert client.app.state.tickets.burn(ticket)  # type: ignore[attr-defined]  # still unused
