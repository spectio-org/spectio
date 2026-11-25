"""The three secrets of 0.0.1 (dev-env §15.3 "Access" and req. 2; P1 Task 12).

Each is 32 bytes from `secrets` (43 base64url characters) and compared in constant time:

- the **server key**, written at each start to `server.key` (0600) in the node-local directory;
  only `POST /api/v1/auth/links` accepts it;
- the **link ticket**, single use, valid 15 minutes; only its SHA-256 is kept (auth §2.1);
- the **session secret**, kept only as its SHA-256 in the `sessions` table, with when the session
  started and when it was last seen (#375): a restart keeps it while it is valid, within an idle
  time and an absolute lifetime; Sign out and `spectio logout --all` delete its row.
"""

import hashlib
import hmac
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Row, delete, insert, select, update

from spectio.runner.rundir import private_dir, write_file
from spectio_server.ids import new_id
from spectio_server.store.schema import sessions
from spectio_server.store.writer import Writer

KEY_FILE = "server.key"
TICKET_TTL_S = 15 * 60
SEEN_EVERY = timedelta(minutes=1)  # `last_seen_at` is written at most this often


def _new() -> str:
    return secrets.token_urlsafe(32)


def _now() -> datetime:
    return datetime.now(UTC)


def _digest(secret: str) -> bytes:
    return hashlib.sha256(secret.encode()).digest()


@dataclass(frozen=True, repr=False)
class ServerKey:
    value: str

    @classmethod
    def new(cls) -> "ServerKey":
        """A key kept in memory only."""
        return cls(_new())

    @classmethod
    def generate(cls, db_dir: Path) -> "ServerKey":
        """A new key, replacing `<db_dir>/server.key` (created 0600 under a temporary name)."""
        key = cls.new()
        with private_dir(db_dir) as fd:
            write_file(fd, KEY_FILE, key.value.encode())
        return key

    def matches(self, candidate: str) -> bool:
        return hmac.compare_digest(_digest(candidate), _digest(self.value))


class TicketStore:
    """Link tickets by digest, each with its expiry."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self._expiry: dict[bytes, float] = {}
        self._lock = threading.Lock()

    def mint(self) -> str:
        ticket = _new()
        with self._lock:
            now = self.clock()
            self._expiry = {d: t for d, t in self._expiry.items() if t > now}
            self._expiry[_digest(ticket)] = now + TICKET_TTL_S
        return ticket

    def burn(self, ticket: str) -> bool:
        """True once for a ticket minted here less than 15 minutes ago."""
        with self._lock:
            expiry = self._expiry.pop(_digest(ticket), None)
            return expiry is not None and self.clock() <= expiry


class SessionStore:
    """Sessions in the database, by digest (#375): each is valid while it is younger than
    `max_age` and was seen less than `idle` ago. Reads and writes go through the server's own
    database and writer, so a restart keeps the sessions that are still valid, and `spectio
    logout --all` revokes them with no server running."""

    def __init__(
        self,
        writer: Writer,
        idle: timedelta,
        max_age: timedelta,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self.writer = writer
        self.idle = idle
        self.max_age = max_age
        self.clock = clock

    def _expired(self, conn: Connection, now: datetime) -> None:
        conn.execute(
            delete(sessions).where(
                (sessions.c.created_at <= now - self.max_age)
                | (sessions.c.last_seen_at <= now - self.idle)
            )
        )

    def create(self) -> str:
        secret = _new()
        now = self.clock()

        def write(conn: Connection) -> None:
            self._expired(conn, now)  # rows never met again would stay for ever
            conn.execute(
                insert(sessions).values(
                    id=new_id("ses"), digest=_digest(secret), created_at=now, last_seen_at=now
                )
            )

        self.writer.submit(write).result()
        return secret

    def _find(self, secret: str) -> Row[Any] | None:
        """The row of this secret's digest (the unique index), checked again in constant time."""
        found = _digest(secret)
        with self.writer.engine.connect() as conn:
            row = conn.execute(select(sessions).where(sessions.c.digest == found)).first()
        return row if row is not None and hmac.compare_digest(found, row.digest) else None

    def _delete(self, session_id: str) -> None:
        self.writer.submit(
            lambda c: c.execute(delete(sessions).where(sessions.c.id == session_id))
        ).result()

    def _live(self, secret: str, now: datetime) -> Row[Any] | None:
        """The session's row, or None for a secret that is not a session or that has expired
        (its row is deleted when met)."""
        row = self._find(secret)
        if row is None:
            return None
        if now - row.created_at >= self.max_age or now - row.last_seen_at >= self.idle:
            self._delete(row.id)
            return None
        return row

    def lifespan(self, secret: str) -> tuple[datetime, datetime] | None:
        """When this session started and when it ends if it is not seen again (its idle time,
        or its absolute lifetime when that comes first); None for a secret that is not a live
        session. Expiry follows the wall clock, so a clock set back lengthens a session."""
        row = self._live(secret, self.clock())
        if row is None:
            return None
        end: datetime = min(row.created_at + self.max_age, row.last_seen_at + self.idle)
        return row.created_at, end

    def _seen(self, session_id: str, now: datetime) -> bool:
        """Write `last_seen_at`, unless a request seen it less than a minute ago already did."""
        return bool(
            self.writer.submit(
                lambda c: (
                    c.execute(
                        update(sessions)
                        .where(sessions.c.id == session_id)
                        .where(sessions.c.last_seen_at <= now - SEEN_EVERY)
                        .values(last_seen_at=now)
                    ).rowcount
                )
            ).result()
        )

    def valid(self, secret: str) -> bool:
        """Whether this is a live session; it is then seen now, in the database once a minute."""
        now = self.clock()
        row = self._live(secret, now)
        if row is None:
            return False
        if now - row.last_seen_at >= SEEN_EVERY:
            self._seen(row.id, now)
        return True

    def revoke(self, secret: str) -> None:
        row = self._find(secret)
        if row is not None:
            self._delete(row.id)

    def revoke_all(self) -> int:
        return self.writer.submit(lambda c: c.execute(delete(sessions)).rowcount).result()
