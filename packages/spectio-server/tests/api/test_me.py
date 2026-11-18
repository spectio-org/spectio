"""`GET /api/v1/me` and `POST /api/v1/auth/session:sign-out`: the Profile page of 0.0.1
(ui-spec §4.10.1, api §5.8; FU-P3-112).

`/me` answers who the server runs as, this session and the config paths, behind the session:
paths only, never a secret, a token or a file's contents.
"""

import os
import pwd
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from spectio.config import Settings, config_path
from spectio_server.auth.middleware import cookie_name
from spectio_server.auth.secrets import SessionStore
from spectio_server.store.writer import Writer

from .conftest import client_for

ME = "/api/v1/me"
SIGN_OUT = "/api/v1/auth/session:sign-out"


def _cookie(client: TestClient, settings: Settings) -> str:
    value = client.cookies.get(cookie_name(f"127.0.0.1:{settings.port}"))
    assert value is not None
    return value


def test_me_names_the_principal_the_session_and_the_paths(
    authed_client: TestClient, settings: Settings
) -> None:
    answer = authed_client.get(ME)
    assert answer.status_code == 200
    body = answer.json()
    assert body["principal"] == {"user": pwd.getpwuid(os.getuid()).pw_name, "uid": os.getuid()}
    started = datetime.fromisoformat(body["session"]["started_at"])
    assert timedelta(0) <= datetime.now(UTC) - started < timedelta(minutes=1)
    assert body["session"]["expires_at"] is None  # in memory: it ends when the server stops
    assert body["paths"] == {
        "config_file": str(config_path()),
        "data_dir": str(settings.data_dir),
        "db_dir": str(settings.db_dir),
        "observed_dir": str(Path.home() / ".spectio" / "observed"),
    }
    assert answer.headers["cache-control"] == "no-store"


def test_me_holds_no_secret_and_no_file_contents(
    authed_client: TestClient, settings: Settings
) -> None:
    text = authed_client.get(ME).text
    state = authed_client.app.state  # type: ignore[attr-defined]
    assert _cookie(authed_client, settings) not in text
    assert state.server_key.value not in text
    assert config_path().read_text().strip().splitlines()[0] not in text  # a path, not the file


def test_me_needs_the_session(settings: Settings, writer: Writer) -> None:
    anon = client_for(settings, writer, signed_in=False)
    answer = anon.get(ME)
    assert answer.status_code == 401
    assert "paths" not in answer.text and str(settings.db_dir) not in answer.text


def test_sign_out_ends_this_session_only(authed_client: TestClient, settings: Settings) -> None:
    state = authed_client.app.state  # type: ignore[attr-defined]
    other = state.sessions.create()
    answer = authed_client.post(SIGN_OUT)
    assert answer.status_code == 204
    name = cookie_name(f"127.0.0.1:{settings.port}")
    assert (
        f"{name}=" in answer.headers["set-cookie"] and "Max-Age=0" in answer.headers["set-cookie"]
    )
    assert authed_client.get(ME).status_code == 401
    assert state.sessions.valid(other)


def test_sign_out_needs_an_origin(authed_client: TestClient) -> None:
    assert authed_client.post(SIGN_OUT, headers={"Origin": ""}).status_code == 403


def test_session_store_keeps_the_start_and_revokes() -> None:
    store = SessionStore()
    before = datetime.now(UTC)
    secret = store.create()
    started = store.started(secret)
    assert started is not None and before <= started <= datetime.now(UTC)
    assert store.started("unknown") is None
    store.revoke(secret)
    assert not store.valid(secret) and store.started(secret) is None
    store.revoke(secret)  # twice: nothing to do
