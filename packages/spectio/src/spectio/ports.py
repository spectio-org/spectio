"""Who listens on a loopback port (dev-env §15.3 req. 9): `spectio serve` names the owner of a
taken port, and `spectio login --print-link` sends the server key only to the user's own. On
SLURM and shared hosts the server listens on `SOCKET` in its database directory instead
(inbox #109 rule 5, Thomas 2026-11-08)."""

import os
from collections.abc import Iterator, Sequence
from pathlib import Path

TABLES = ("/proc/net/tcp", "/proc/net/tcp6")
SOCKET = "spectio.sock"  # the server's Unix socket, in its 0700 database directory
SUN_PATH_MAX = 107  # bytes of a socket path on Linux: sun_path[108] with its NUL, unix(7)


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


def is_server_socket(value: object, db_dir: object) -> bool:
    """Whether `value` is `SOCKET` in `db_dir`, within the AF_UNIX path limit."""
    return value == f"{db_dir}/{SOCKET}" and len(os.fsencode(str(value))) <= SUN_PATH_MAX
