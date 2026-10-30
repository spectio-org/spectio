"""Open the SQLite database, under the rules of architecture §7.2 and api §7.

The database is a rebuildable index in a node-local directory (architecture §7.2, note
2026-10-28): `default_db_dir()` finds that directory, `open_db()` refuses a network file system,
an SQLite without the WAL-reset fix and any path another user could have prepared, and tells the
caller when the database is new, so that boot rebuilds it from the run directories.
"""

import logging
import os
import re
import sqlite3
import stat
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import URL, Connection, Engine, create_engine, event

log = logging.getLogger(__name__)

DB_FILE = "spectio.db"  # the file name is ours: the specs name only the directory
MOUNTINFO = Path("/proc/self/mountinfo")
SYSTEM_TMP = Path("/tmp")  # noqa: S108 - the base of last resort, checked like any other
BUSY_TIMEOUT_MS = 5000

# Network and cluster file systems, where SQLite locking and WAL are unsafe (architecture §7.2),
# plus autofs: an automount point that did not mount is no proof of a local disk.
NETWORK_FS = frozenset(
    {"nfs", "nfs4", "lustre", "gpfs", "beegfs", "cifs", "smb3", "ceph", "fuse.sshfs", "autofs"}
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
    """Undo the octal escapes of /proc/self/mountinfo (\\040 for a space, and so on)."""
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), field)


def fs_type(path: Path, mountinfo: Path = MOUNTINFO) -> str:
    """The file system type of `path`.

    `stat` first, which triggers an automount; then the last mount whose device is the path's
    `st_dev` (the top of a stack of mounts). When no device matches (btrfs subvolumes report
    their own), the last of the longest mount points that contain the path decides. Without a
    mountinfo table: refused on Linux (fail closed), "unknown" and accepted elsewhere (macOS).
    """
    st = os.stat(path)
    try:
        table = mountinfo.read_text()
    except OSError as exc:
        if sys.platform == "linux":
            raise UnsafeDatabase(f"cannot read {mountinfo} to check the file system") from exc
        return "unknown"
    dev = f"{os.major(st.st_dev)}:{os.minor(st.st_dev)}"
    real = Path(os.path.realpath(path))
    by_dev, by_point, best = None, "unknown", -1
    for line in table.splitlines():
        fields = line.split()
        if "-" not in fields or len(fields) < 5:
            continue
        kind = fields[fields.index("-") + 1]
        if fields[2] == dev:
            by_dev = kind
        point = Path(_unescape(fields[4]))
        if real.is_relative_to(point) and len(point.parts) >= best:
            by_point, best = kind, len(point.parts)
    return by_dev or by_point


def _private_dir(path: Path, uid: int) -> tuple[bool, int | None]:
    """Whether `path` is a real directory owned by `uid` with no group or other bits, checked on
    the opened directory (no symlink followed); and the owner uid seen, None when unknown."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        try:
            return False, os.lstat(path).st_uid
        except OSError:
            return False, None
    try:
        st, lst = os.fstat(fd), os.lstat(path)
    finally:
        os.close(fd)
    same = (st.st_dev, st.st_ino) == (lst.st_dev, lst.st_ino)
    return same and st.st_uid == uid and not stat.S_IMODE(st.st_mode) & 0o077, st.st_uid


def _safe_base(base: Path, uid: int) -> bool:
    """An absolute directory that is sticky, or owned by `uid` and not writable by others."""
    if not base.is_absolute():
        return False
    try:
        st = os.stat(base)
    except OSError:
        return False
    mode = st.st_mode
    return stat.S_ISDIR(mode) and (
        bool(mode & stat.S_ISVTX) or (st.st_uid == uid and not mode & 0o022)
    )


def default_db_dir() -> Path:
    """`$TMPDIR` (or /tmp)/spectio-<uid>, 0700; a squatted path is left as it is and a fresh
    `mkdtemp` directory is used instead (dev-environment-and-testing.md §15.3, Where data lives).
    """
    uid = os.getuid()
    base = Path(os.environ.get("TMPDIR") or SYSTEM_TMP)
    if not _safe_base(base, uid):
        log.warning(
            "TMPDIR %s is not absolute, or is writable by others; using %s", base, SYSTEM_TMP
        )
        base = SYSTEM_TMP
    path = base / f"spectio-{uid}"
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        pass
    private, owner = _private_dir(path, uid)
    if private:
        return path
    fallback = Path(tempfile.mkdtemp(prefix=f"spectio-{uid}-", dir=base))
    seen = "uid unknown" if owner is None else f"uid {owner}"
    log.warning("%s is not a private directory of this user (%s); using %s", path, seen, fallback)
    return fallback


def _check_private_file(path: Path, uid: int) -> None:
    """Refuse `path` unless it is a regular file of `uid` with no group or other bits."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise UnsafeDatabase(f"{path} cannot be opened safely (a symlink?): {exc}") from exc
    try:
        st = os.fstat(fd)
    finally:
        os.close(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid != uid or stat.S_IMODE(st.st_mode) & 0o077:
        raise UnsafeDatabase(
            f"{path} must be a regular file of this user with mode 0600 "
            f"(found uid {st.st_uid}, mode {stat.S_IMODE(st.st_mode):o})"
        )


def _on_connect(dbapi_connection: sqlite3.Connection, _record: Any) -> None:
    # Let SQLAlchemy, not pysqlite, emit BEGIN (SQLAlchemy's pysqlite transaction recipe).
    dbapi_connection.isolation_level = None
    dbapi_connection.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


def _on_begin(conn: Connection) -> None:
    # The writer asks for BEGIN IMMEDIATE (writer.py); readers keep a deferred BEGIN.
    immediate = conn.get_execution_options().get("spectio_begin") == "IMMEDIATE"
    conn.exec_driver_sql("BEGIN IMMEDIATE" if immediate else "BEGIN")


def _migrate(engine: Engine) -> bool:
    """Upgrade to the latest revision; True when the database had no revision (it is new)."""
    config = Config()
    config.set_main_option("script_location", "spectio_server:migrations")
    with engine.begin() as conn:
        new = MigrationContext.configure(conn).get_current_revision() is None
        config.attributes["connection"] = conn
        command.upgrade(config, "head")
    return new


def open_db(db_dir: Path, mountinfo: Path = MOUNTINFO) -> tuple[Engine, bool]:
    """Open (or create) the database in `db_dir` and migrate it to the latest revision.

    Returns the engine and True when the database is new (created, or never migrated).
    """
    check_sqlite_version(sqlite3.sqlite_version)
    uid = os.getuid()
    private, owner = _private_dir(db_dir, uid)
    if not private:  # an explicit directory gets no fallback
        raise UnsafeDatabase(
            f"{db_dir} must be a directory of this user with mode 0700 (owner uid {owner})"
        )
    kind = fs_type(db_dir, mountinfo)
    if kind in NETWORK_FS:
        raise UnsafeDatabase(
            f"{db_dir} is on a {kind} file system, where SQLite is unsafe. Put the database "
            "on a local disk: a node-local directory (--db-dir), a laptop, a VM or a service node."
        )
    path = db_dir / DB_FILE
    try:  # created at its mode, never chmod-ed (dev-env §15.3 req. 5); WAL and SHM inherit it
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600))
    except FileExistsError:
        pass
    for file in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        _check_private_file(file, uid)
    with closing(sqlite3.connect(path)) as raw:
        if raw.execute("PRAGMA page_count").fetchone()[0] == 0:
            # auto_vacuum only takes effect on an empty database; WAL mode is persistent.
            raw.execute("PRAGMA auto_vacuum=INCREMENTAL")
            raw.execute("PRAGMA journal_mode=WAL")
    engine = create_engine(URL.create("sqlite+pysqlite", database=str(path)))
    event.listen(engine, "connect", _on_connect)
    event.listen(engine, "begin", _on_begin)
    return engine, _migrate(engine)
