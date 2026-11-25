"""Browser sessions that outlive a restart (#375; dev-env §15.3 "Access", auth §2).

A session is a row of `sessions`: the SHA-256 of the secret, never the secret, with when it
started and when it was last seen. It is valid while it is younger than the absolute lifetime
and was seen less than the idle time ago; it is revoked by deleting its row.
"""

import hashlib
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from spectio.cli.main import app as cli_app
from spectio.config import Settings
from spectio_server.auth.secrets import SessionStore
from spectio_server.bootstrap import revoke_all_sessions
from spectio_server.store.db import DB_FILE, open_db
from spectio_server.store.schema import sessions
from spectio_server.store.writer import Writer

from .api.conftest import client_for

T0 = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
IDLE, MAX = timedelta(days=7), timedelta(days=30)
EXCHANGE = "/api/v1/auth/magic-links:exchange"


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now

    def advance(self, by: timedelta) -> None:
        self.now += by


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def store(writer: Writer, clock: Clock) -> SessionStore:
    return SessionStore(writer, IDLE, MAX, clock)


def _rows(writer: Writer) -> list[tuple[bytes, datetime, datetime]]:
    with writer.engine.connect() as conn:
        found = conn.execute(
            select(sessions.c.digest, sessions.c.created_at, sessions.c.last_seen_at)
        ).all()
    return [(r.digest, r.created_at, r.last_seen_at) for r in found]


def test_a_session_survives_a_new_store_on_the_same_database(
    writer: Writer, store: SessionStore, clock: Clock
) -> None:
    secret = store.create()
    again = SessionStore(writer, IDLE, MAX, clock)  # what a restart builds
    assert again.valid(secret)
    assert again.started(secret) == T0
    assert not again.valid("not-a-session")


def test_a_session_survives_a_restart_of_the_database_connection(
    settings: Settings, writer: Writer, clock: Clock
) -> None:
    secret = SessionStore(writer, IDLE, MAX, clock).create()
    assert settings.db_dir is not None
    engine, new = open_db(settings.db_dir)  # a second open of the same file, as after a restart
    try:
        assert not new
        other = Writer(engine)
        try:
            assert SessionStore(other, IDLE, MAX, clock).valid(secret)
        finally:
            other.close()
    finally:
        engine.dispose()


def test_the_database_holds_the_digest_not_the_secret(
    settings: Settings, writer: Writer, store: SessionStore
) -> None:
    secret = store.create()
    [(digest, created, seen)] = _rows(writer)
    assert digest == hashlib.sha256(secret.encode()).digest()
    assert created == seen == T0
    assert settings.db_dir is not None
    raw = (settings.db_dir / DB_FILE).read_bytes()
    wal = settings.db_dir / f"{DB_FILE}-wal"
    assert secret.encode() not in raw
    assert not wal.exists() or secret.encode() not in wal.read_bytes()
    assert secret not in repr(vars(store))


def test_idle_expiry(writer: Writer, store: SessionStore, clock: Clock) -> None:
    secret = store.create()
    clock.advance(IDLE - timedelta(seconds=1))
    assert store.valid(secret)  # seen again: the idle time starts over
    clock.advance(IDLE - timedelta(seconds=1))
    assert store.valid(secret)
    clock.advance(IDLE)
    assert not store.valid(secret)
    assert _rows(writer) == []  # an expired row is deleted when met
    assert store.started(secret) is None


def test_absolute_expiry_even_when_always_seen(
    writer: Writer, store: SessionStore, clock: Clock
) -> None:
    secret = store.create()
    for _ in range(MAX // timedelta(days=3) - 1):  # seen every 3 days, never idle
        clock.advance(timedelta(days=3))
        assert store.valid(secret)
    clock.advance(timedelta(days=3))  # day 30
    assert not store.valid(secret)
    assert _rows(writer) == []


def test_last_seen_is_refreshed_at_most_once_a_minute(
    writer: Writer, store: SessionStore, clock: Clock
) -> None:
    secret = store.create()
    clock.advance(timedelta(seconds=59))
    assert store.valid(secret)
    assert _rows(writer)[0][2] == T0  # too soon: no write
    clock.advance(timedelta(seconds=1))
    assert store.valid(secret)
    assert _rows(writer)[0][2] == T0 + timedelta(seconds=60)
    clock.advance(timedelta(seconds=30))
    assert store.valid(secret)
    assert _rows(writer)[0][2] == T0 + timedelta(seconds=60)


def test_started_does_not_count_as_a_visit(
    writer: Writer, store: SessionStore, clock: Clock
) -> None:
    secret = store.create()
    clock.advance(timedelta(minutes=5))
    assert store.started(secret) == T0
    assert _rows(writer)[0][2] == T0


def test_revoke_deletes_the_row_and_only_that_one(writer: Writer, store: SessionStore) -> None:
    mine, other = store.create(), store.create()
    store.revoke(mine)
    assert not store.valid(mine) and store.valid(other)
    store.revoke(mine)  # twice: nothing to do
    assert len(_rows(writer)) == 1


def test_creating_a_session_purges_the_expired_ones(
    writer: Writer, store: SessionStore, clock: Clock
) -> None:
    store.create()
    clock.advance(IDLE)  # never met again: only a purge can remove it
    kept = store.create()
    assert len(_rows(writer)) == 1
    assert store.valid(kept)


def test_revoke_all(writer: Writer, store: SessionStore) -> None:
    secrets = [store.create(), store.create()]
    assert store.revoke_all() == 2
    assert not any(store.valid(s) for s in secrets)
    assert store.revoke_all() == 0


def test_expiry_is_the_earlier_of_idle_and_absolute(store: SessionStore, clock: Clock) -> None:
    secret = store.create()
    assert store.expires_at(secret) == T0 + IDLE
    for _ in range(4):  # seen every 6 days, up to day 24
        clock.advance(timedelta(days=6))
        assert store.valid(secret)
    assert store.expires_at(secret) == T0 + MAX  # the 30 days end before a new week
    assert store.expires_at("unknown") is None


def test_the_exchange_sets_a_cookie_that_lasts_the_absolute_lifetime(
    settings: Settings, writer: Writer
) -> None:
    anon = client_for(settings, writer, signed_in=False)
    ticket = anon.app.state.tickets.mint()  # type: ignore[attr-defined]
    answer = anon.post(EXCHANGE, json={"ticket": ticket})
    cookie = answer.headers["set-cookie"].lower()
    assert f"max-age={30 * 86400}" in cookie
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/" in cookie


def test_the_lifetimes_are_settings_with_env_overrides(
    settings: Settings, writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (settings.auth.session_idle_days, settings.auth.session_max_days) == (7, 30)
    monkeypatch.setenv("SPECTIO_AUTH_SESSION_IDLE_DAYS", "1")
    monkeypatch.setenv("SPECTIO_AUTH_SESSION_MAX_DAYS", "2")
    changed = Settings()
    anon = client_for(changed, writer, signed_in=False)
    ticket = anon.app.state.tickets.mint()  # type: ignore[attr-defined]
    answer = anon.post(EXCHANGE, json={"ticket": ticket})
    assert f"max-age={2 * 86400}" in answer.headers["set-cookie"].lower()
    store: SessionStore = anon.app.state.sessions  # type: ignore[attr-defined]
    assert (store.idle, store.max_age) == (timedelta(days=1), timedelta(days=2))


@pytest.mark.parametrize(
    "name", ["SPECTIO_AUTH_SESSION_IDLE_DAYS", "SPECTIO_AUTH_SESSION_MAX_DAYS"]
)
@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "100000"])
def test_a_bad_lifetime_is_refused(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        Settings()


def test_the_default_lifetimes_are_not_written_to_spectio_toml(settings: Settings) -> None:
    from spectio.config import render_toml

    assert "auth" not in render_toml(settings)


@pytest.fixture
def db_dir(settings: Settings, writer: Writer) -> Iterator[Path]:
    assert settings.db_dir is not None
    yield settings.db_dir


def test_revoke_all_sessions_works_on_the_database_alone(
    db_dir: Path, writer: Writer, store: SessionStore
) -> None:
    secret = store.create()
    assert revoke_all_sessions(db_dir) == 1  # the server is running: its writer is open
    assert not store.valid(secret)
    assert revoke_all_sessions(db_dir) == 0


def test_revoke_all_sessions_with_no_database_creates_none(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir(mode=0o700)
    assert revoke_all_sessions(empty) == 0
    assert not (empty / DB_FILE).exists()


def test_logout_all_ends_every_session(
    settings: Settings, writer: Writer, store: SessionStore
) -> None:
    secrets = [store.create(), store.create()]
    result = CliRunner().invoke(cli_app, ["logout", "--all"])
    assert result.exit_code == 0, result.output
    assert "2" in result.stdout
    assert not any(store.valid(s) for s in secrets)


def test_logout_needs_all(settings: Settings) -> None:
    result = CliRunner().invoke(cli_app, ["logout"])
    assert result.exit_code == 2
    assert "--all" in result.output


def test_logout_all_prints_no_secret_and_no_digest(
    settings: Settings, writer: Writer, store: SessionStore
) -> None:
    secret = store.create()
    digest = hashlib.sha256(secret.encode()).hexdigest()
    result = CliRunner().invoke(cli_app, ["logout", "--all"])
    assert secret not in result.output and digest not in result.output


def test_sessions_table_is_in_the_migration(settings: Settings) -> None:
    assert settings.db_dir is not None
    engine, _ = open_db(settings.db_dir)
    engine.dispose()
    with sqlite3.connect(settings.db_dir / DB_FILE) as raw:
        columns = {r[1] for r in raw.execute("PRAGMA table_info(sessions)")}
        unique = {
            r[2]
            for index in raw.execute("PRAGMA index_list(sessions)")
            if index[2]
            for r in raw.execute(f"PRAGMA index_info({index[1]})")
        }
    assert columns == {"id", "digest", "created_at", "last_seen_at"}
    assert "digest" in unique
