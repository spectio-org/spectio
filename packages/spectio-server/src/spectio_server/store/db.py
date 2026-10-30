"""Open the SQLite database, under the rules of architecture §7.2 and api §7.

The database is a rebuildable index in a node-local directory (architecture §7.2, note
2026-10-28): `default_db_dir()` finds that directory, `open_db()` refuses a network file system
and an SQLite without the WAL-reset fix, and tells the caller when it created the database, so
that boot rebuilds it from the run directories.
"""

import logging
import os
import re
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, event

log = logging.getLogger(__name__)

DB_FILE = "spectio.db"  # the file name is ours: the specs name only the directory
MOUNTS = Path("/proc/self/mounts")
BUSY_TIMEOUT_MS = 5000

# Network and cluster file systems, where SQLite locking and WAL are unsafe (architecture §7.2).
NETWORK_FS = frozenset(
    {"nfs", "nfs4", "lustre", "gpfs", "beegfs", "cifs", "smb3", "ceph", "fuse.sshfs"}
)


class UnsafeDatabase(Exception):
    """The database cannot be opened safely here; the message says why and what to do."""


def check_sqlite_version(version: str) -> None:
    """The library Python loads must carry the WAL-reset fix (api §7, SQLite version rule)."""
    v = tuple(int(part) for part in version.split("."))
    if v >= (3, 51, 3) or (3, 50, 7) <= v < (3, 51) or (3, 44, 6) <= v < (3, 45):
        return
    raise UnsafeDatabase(
        f"SQLite {version} lacks the WAL-reset fix: Spectio needs SQLite >= 3.51.3, "
        "or >= 3.50.7 in the 3.50 series, or >= 3.44.6 in the 3.44 series "
        "(the library Python loads, sqlite3.sqlite_version)"
    )


def _unescape(field: str) -> str:
    """Undo the octal escapes of /proc/self/mounts (\\040 for a space, and so on)."""
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), field)


def fs_type(path: Path, mounts: Path = MOUNTS) -> str:
    """The file system type of `path`: the type of the longest mount point that contains it.

    Without a mounts table (macOS, a laptop) the type is "unknown", which is accepted.
    """
    try:
        table = mounts.read_text()
    except FileNotFoundError:
        return "unknown"
    real = Path(os.path.realpath(path))
    best, best_type = -1, "unknown"
    for line in table.splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        point = Path(_unescape(fields[1]))
        if real.is_relative_to(point) and len(point.parts) > best:
            best, best_type = len(point.parts), fields[2]
    return best_type


def _private_dir(path: Path, uid: int) -> bool:
    """True if `path` is a real directory owned by `uid` with no group or other bits, checked on
    the opened directory (no symlink followed)."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        return False
    try:
        st, lst = os.fstat(fd), os.lstat(path)
    finally:
        os.close(fd)
    same = (st.st_dev, st.st_ino) == (lst.st_dev, lst.st_ino)
    return same and st.st_uid == uid and not stat.S_IMODE(st.st_mode) & 0o077


def default_db_dir() -> Path:
    """`$TMPDIR` (or /tmp)/spectio-<uid>, 0700; a squatted path is left as it is and a fresh
    `mkdtemp` directory is used instead (dev-environment-and-testing.md §15.3, Where data lives).
    """
    uid = os.getuid()
    base = Path(os.environ.get("TMPDIR") or "/tmp")  # noqa: S108 - checked below, mkdtemp fallback
    path = base / f"spectio-{uid}"
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        pass
    if _private_dir(path, uid):
        return path
    fallback = Path(tempfile.mkdtemp(prefix=f"spectio-{uid}-", dir=base))
    log.warning(
        "%s is not a private directory of this user (owned by uid %d); using %s",
        path,
        os.lstat(path).st_uid,
        fallback,
    )
    return fallback


def _on_connect(dbapi_connection: sqlite3.Connection, _record: Any) -> None:
    # Let SQLAlchemy, not pysqlite, emit BEGIN (SQLAlchemy's pysqlite transaction recipe).
    dbapi_connection.isolation_level = None
    dbapi_connection.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


def _on_begin(conn: Connection) -> None:
    # The writer asks for BEGIN IMMEDIATE (writer.py); readers keep a deferred BEGIN.
    immediate = conn.get_execution_options().get("spectio_begin") == "IMMEDIATE"
    conn.exec_driver_sql("BEGIN IMMEDIATE" if immediate else "BEGIN")


def _migrate(engine: Engine) -> None:
    config = Config()
    config.set_main_option("script_location", "spectio_server:migrations")
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")


def open_db(db_dir: Path, mounts: Path = MOUNTS) -> tuple[Engine, bool]:
    """Open (or create) the database in `db_dir` and migrate it to the latest revision.

    Returns the engine and True when the database was created by this call.
    """
    check_sqlite_version(sqlite3.sqlite_version)
    kind = fs_type(db_dir, mounts)
    if kind in NETWORK_FS:
        raise UnsafeDatabase(
            f"{db_dir} is on a {kind} file system, where SQLite is unsafe. Put the database "
            "on a local disk: a node-local directory (--db-dir), a laptop, a VM or a service node."
        )
    path = db_dir / DB_FILE
    created = not path.exists()
    if created:
        # auto_vacuum only takes effect on an empty database; WAL mode is persistent.
        with closing(sqlite3.connect(path)) as raw:
            raw.execute("PRAGMA auto_vacuum=INCREMENTAL")
            raw.execute("PRAGMA journal_mode=WAL")
    engine = create_engine(f"sqlite+pysqlite:///{path}")
    event.listen(engine, "connect", _on_connect)
    event.listen(engine, "begin", _on_begin)
    _migrate(engine)
    return engine, created
