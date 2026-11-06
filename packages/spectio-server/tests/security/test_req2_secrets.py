"""dev-env §15.3 req. 2: the token link, the server key and the session (P1 Task 12).

Every route needs the session secret, except the four of P1 Assumption 8; the ticket is single
use and lives 15 minutes; only `spectio login --print-link` uses the server key.
"""

import base64
import json
import os
import re
import threading
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from spectio.cli import login
from spectio.cli.main import app as cli_app
from spectio.config import Settings
from spectio_server import app as app_mod
from spectio_server.auth.middleware import COOKIE, EXEMPT
from spectio_server.auth.routes import EXPIRED
from spectio_server.auth.secrets import ServerKey, SessionStore, TicketStore
from spectio_server.serve import STATE, started
from spectio_server.store.writer import Writer

from ..api.conftest import client_for

PROBLEM_KEYS = {"type", "title", "status", "detail"}
EXCHANGE = "/api/v1/auth/magic-links:exchange"
LINKS = "/api/v1/auth/links"


@pytest.fixture(autouse=True)
def lone_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mount the API, as on one person's machine (SEC-P3T17-06)."""
    monkeypatch.setattr(app_mod, "shared_host", lambda: None)


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<!doctype html><title>Spectio</title>")
    (root / "assets" / "index-AbC1.js").write_text("console.log(1)")
    return root


@pytest.fixture
def anon(settings: Settings, writer: Writer) -> TestClient:
    """The app, signed out."""
    return client_for(settings, writer, signed_in=False)


def _ticket(client: TestClient) -> str:
    ticket: str = client.app.state.tickets.mint()  # type: ignore[attr-defined]
    return ticket


def _exchange(client: TestClient, ticket: str) -> Any:
    return client.post(EXCHANGE, json={"ticket": ticket})


def _routes(routes: list[Any], prefix: str) -> Iterator[tuple[set[str], str]]:
    """Each route's methods and full path, through the included routers (FastAPI keeps
    those as `_IncludedRouter`, with the prefix in `include_context`)."""
    for route in routes:
        included = getattr(route, "original_router", None)
        if included is not None:
            yield from _routes(included.routes, prefix + route.include_context.prefix)
        else:
            yield getattr(route, "methods", None) or {"GET"}, prefix + route.path


@pytest.mark.parametrize("web", [False, True])
def test_req2_every_route_needs_session(
    settings: Settings, writer: Writer, dist: Path, web: bool
) -> None:
    client = client_for(settings, writer, web_dir=dist if web else None, signed_in=False)
    checked = 0
    for method_set, path in _routes(client.app.routes, ""):  # type: ignore[attr-defined]
        url = re.sub(r"\{[^}]+\}", "x", path)
        for method in sorted(method_set):
            if (method, path) in EXEMPT or (method == "HEAD" and ("GET", path) in EXEMPT):
                continue
            answer = client.request(method, url)
            assert answer.status_code == 401, (method, url, answer.text)
            if method != "HEAD":
                body = answer.json()
                assert set(body) == PROBLEM_KEYS
                assert body["type"] == "/problems/unauthenticated"
            checked += 1
    assert checked > 15  # the API is mounted
    assert client.get("/no/such/route").status_code == 401  # nothing answers before the check
    client.cookies.set(COOKIE, "x" * 43)  # not a session of this server
    assert client.get("/api/v1/runs").status_code == 401


def test_req2_exemptions_are_the_four() -> None:
    assert {
        ("GET", "/auth/link"),
        ("GET", "/auth/link.js"),
        ("POST", EXCHANGE),
        ("POST", LINKS),
    } == set(EXEMPT)


def test_req2_secrets_256_bits(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    key = ServerKey.generate(tmp_path)
    for secret in (TicketStore().mint(), SessionStore().create(), key.value):
        assert re.fullmatch(r"[A-Za-z0-9_-]{43}", secret)
        assert len(base64.urlsafe_b64decode(secret + "=")) >= 32
    assert TicketStore().mint() != TicketStore().mint()
    assert (tmp_path / "server.key").read_text() == key.value
    assert (tmp_path / "server.key").stat().st_mode & 0o777 == 0o600
    assert ServerKey.generate(tmp_path).value != key.value  # replaced at each start


def test_req2_exchange_sets_the_session(anon: TestClient) -> None:
    answer = _exchange(anon, _ticket(anon))
    assert answer.status_code == 204
    cookie = answer.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    assert "httponly" in cookie.lower()
    assert "samesite=strict" in cookie.lower()
    assert answer.headers["cache-control"] == "no-store"
    assert anon.get("/api/v1/runs").status_code == 200  # the client keeps the cookie


def test_req2_ticket_single_use_and_15_min(anon: TestClient) -> None:
    ticket = _ticket(anon)
    assert _exchange(anon, ticket).status_code == 204
    assert _exchange(anon, ticket).status_code == 401
    now = [1000.0]
    anon.app.state.tickets.clock = lambda: now[0]  # type: ignore[attr-defined]
    late, in_time = _ticket(anon), _ticket(anon)
    now[0] += 15 * 60 - 1
    assert _exchange(anon, in_time).status_code == 204
    now[0] += 2  # 15 min 1 s after the mint
    assert _exchange(anon, late).status_code == 401
    assert _exchange(anon, "not-a-ticket").status_code == 401


def test_req2_ticket_stored_hashed(anon: TestClient) -> None:
    store: TicketStore = anon.app.state.tickets  # type: ignore[attr-defined]
    ticket = store.mint()
    assert ticket not in repr(vars(store))
    sessions: SessionStore = anon.app.state.sessions  # type: ignore[attr-defined]
    secret = sessions.create()
    assert secret not in repr(vars(sessions))
    other = "B" if secret[-1] == "A" else "A"  # always a different secret (DOC-P3T12-01)
    assert sessions.valid(secret) and not sessions.valid(secret[:-1] + other)


def test_req2_server_key_only_for_links(anon: TestClient) -> None:
    key: ServerKey = anon.app.state.server_key  # type: ignore[attr-defined]
    bearer = {"Authorization": f"Bearer {key.value}"}
    assert anon.get("/api/v1/runs", headers=bearer).status_code == 401
    assert anon.post(LINKS, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert anon.post(LINKS).status_code == 401
    answer = anon.post(LINKS, headers=bearer)
    assert answer.status_code == 200
    url = answer.json()["url"]
    prefix = f"http://127.0.0.1:{anon.app.state.settings.port}/auth/link#"  # type: ignore[attr-defined]
    assert url.startswith(prefix)
    assert _exchange(anon, url.removeprefix(prefix)).status_code == 204
    assert "set-cookie" not in answer.headers  # the key gives a link, never a session


def test_reused_or_expired_link_message(anon: TestClient) -> None:
    ticket = _ticket(anon)
    _exchange(anon, ticket)
    second = _exchange(anon, ticket)
    assert second.status_code == 401
    assert second.json()["type"] == "/problems/link-expired"
    page = anon.get("/auth/link")
    assert page.status_code == 200
    text = re.sub(r"</?code>", "`", page.text)
    assert EXPIRED in text
    assert EXPIRED == (
        "This link was already used or has expired. Run `spectio login --print-link` on the "
        "cluster for a new one."
    )
    for answer in (page, anon.get("/auth/link.js")):
        assert answer.headers["cache-control"] == "no-store"
        assert answer.headers["referrer-policy"] == "no-referrer"
        assert answer.headers["content-security-policy"] == "default-src 'self'"
    assert "set-cookie" not in page.headers


def test_link_js_drops_the_ticket(anon: TestClient) -> None:
    script = anon.get("/auth/link.js")
    assert script.headers["content-type"].startswith("text/javascript")
    js = script.text
    for needle in ("location.hash", "history.replaceState", EXCHANGE, 'location.replace("/")'):
        assert needle in js
    assert js.index("history.replaceState") < js.index("fetch(")  # dropped before the post


# --- spectio login --print-link -----------------------------------------------------------


@pytest.fixture
def running_server(settings: Settings) -> Iterator[Settings]:
    """`spectio serve` itself, on the recorded port: server.json, server.key and the app."""
    with started(settings) as server:
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 20
        while not server.uvicorn.started:
            assert time.monotonic() < deadline, "the server did not start"
            time.sleep(0.05)
        try:
            yield settings
        finally:
            server.uvicorn.should_exit = True
            thread.join(20)


def _exchange_live(port: int, ticket: str) -> int:
    origin = f"http://127.0.0.1:{port}"
    request = urllib.request.Request(  # noqa: S310 (a loopback URL)
        origin + EXCHANGE,
        data=json.dumps({"ticket": ticket}).encode(),
        headers={"Content-Type": "application/json", "Origin": origin},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as answer:  # noqa: S310
            return int(answer.status)
    except urllib.error.HTTPError as exc:
        return exc.code


def test_login_print_link(running_server: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    port = running_server.port
    for name in ("no_proxy", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")  # the key never goes to a proxy
    result = CliRunner().invoke(cli_app, ["login", "--print-link"])
    assert result.exit_code == 0, result.output
    found = re.fullmatch(
        rf"http://127\.0\.0\.1:{port}/auth/link#([A-Za-z0-9_-]{{43}})", result.stdout.strip()
    )
    assert found, result.stdout
    monkeypatch.undo()
    assert _exchange_live(port, found[1]) == 204  # a working link
    assert _exchange_live(port, found[1]) == 401  # once


def test_print_link_json(running_server: Settings) -> None:
    result = CliRunner().invoke(cli_app, ["login", "--print-link", "--json"])
    assert result.exit_code == 0, result.output
    lines = result.stdout.splitlines()
    assert len(lines) == 1
    sentinel, _, payload = lines[0].partition(" ")
    assert sentinel == login.SENTINEL
    ticket = json.loads(payload)["ticket"]
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", ticket)
    assert _exchange_live(running_server.port, ticket) == 204


def _state(settings: Settings, **record: Any) -> None:
    path = settings.data_dir / STATE
    body = {"host": "login3", "port": settings.port, "pid": 1, "db_dir": str(settings.db_dir)}
    path.write_text(json.dumps({**body, **record}))
    path.chmod(0o600)


@pytest.fixture
def no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("no request may be sent")

    monkeypatch.setattr(login.DIRECT, "open", refuse)


@pytest.mark.usefixtures("no_request")
def test_print_link_on_other_node(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(login, "hostname", lambda: "login1")
    _state(settings)
    result = CliRunner().invoke(cli_app, ["login", "--print-link"])
    assert result.exit_code == 2
    assert "ssh login3 spectio login --print-link" in result.output
    assert "http" not in result.stdout
    _state(settings, host="x;y")
    result = CliRunner().invoke(cli_app, ["login", "--print-link"])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "x;y" not in result.output


@pytest.mark.usefixtures("no_request")
def test_print_link_refuses_foreign_listener(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(login, "hostname", lambda: "login3")
    _state(settings)
    monkeypatch.setattr(login, "port_owners", lambda port: {os.getuid(), os.getuid() + 1})
    result = CliRunner().invoke(cli_app, ["login", "--print-link"])
    assert result.exit_code == 2
    assert f"uid {os.getuid() + 1}" in result.output
    monkeypatch.setattr(login, "port_owners", lambda port: set())
    assert CliRunner().invoke(cli_app, ["login", "--print-link"]).exit_code == 2


@pytest.mark.usefixtures("no_request")
def test_print_link_bad_port_or_no_state(settings: Settings) -> None:
    result = CliRunner().invoke(cli_app, ["login", "--print-link"])
    assert result.exit_code == 2  # no server.json: no server runs
    assert "spectio serve" in result.output
    _state(settings, port=80)
    assert CliRunner().invoke(cli_app, ["login", "--print-link"]).exit_code == 2
