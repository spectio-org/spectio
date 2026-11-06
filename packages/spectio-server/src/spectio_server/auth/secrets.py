"""The three secrets of 0.0.1 (dev-env §15.3 "Access" and req. 2; P1 Task 12).

Each is 32 bytes from `secrets` (43 base64url characters) and compared in constant time:

- the **server key**, written at each start to `server.key` (0600) in the node-local directory;
  only `POST /api/v1/auth/links` accepts it;
- the **link ticket**, single use, valid 15 minutes; only its SHA-256 is kept (auth §2.1);
- the **session secret**, in memory only, so a restart ends every session; only its SHA-256 is
  kept too.
"""

import hashlib
import hmac
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from spectio.runner.rundir import private_dir, write_file

KEY_FILE = "server.key"
TICKET_TTL_S = 15 * 60


def _new() -> str:
    return secrets.token_urlsafe(32)


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
    """Session digests, until the server stops."""

    def __init__(self) -> None:
        self._digests: list[bytes] = []
        self._lock = threading.Lock()

    def create(self) -> str:
        secret = _new()
        with self._lock:
            self._digests.append(_digest(secret))
        return secret

    def valid(self, secret: str) -> bool:
        found = _digest(secret)
        with self._lock:
            return any(hmac.compare_digest(found, d) for d in self._digests)
