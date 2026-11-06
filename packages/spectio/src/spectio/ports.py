"""Who listens on a loopback port (dev-env §15.3 req. 9): `spectio serve` names the owner of a
taken port, and `spectio login --print-link` sends the server key only to the user's own."""

from pathlib import Path


def port_owner(port: int) -> int | None:
    """The uid of a socket listening on `port`, from /proc/net/tcp and tcp6."""
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            lines = Path(table).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if int(fields[1].rsplit(":", 1)[1], 16) == port and fields[3] == "0A":  # LISTEN
                return int(fields[7])
    return None
