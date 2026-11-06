"""Who listens on a loopback port (dev-env §15.3 req. 9): `spectio serve` names the owner of a
taken port, and `spectio login --print-link` sends the server key only to the user's own."""

from collections.abc import Iterator, Sequence
from pathlib import Path

TABLES = ("/proc/net/tcp", "/proc/net/tcp6")


def _listeners(port: int, tables: Sequence[str]) -> Iterator[int]:
    """The uid of each socket listening on `port`, at any local address."""
    for table in tables:
        try:
            lines = Path(table).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if int(fields[1].rsplit(":", 1)[1], 16) == port and fields[3] == "0A":  # LISTEN
                yield int(fields[7])


def port_owner(port: int) -> int | None:
    """The uid of a socket listening on `port`, from /proc/net/tcp and tcp6."""
    return next(_listeners(port, TABLES), None)


def port_owners(port: int, tables: Sequence[str] = TABLES) -> set[int]:
    """Every uid listening on `port`: login dials 127.0.0.1, and the first listener in the
    table may sit on another local address, so the key goes out only if all are the user's."""
    return set(_listeners(port, tables))
