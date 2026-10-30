"""The SQLite store and its discipline (api §7, architecture §7.2; P1 Task 2)."""

import logging
import os
import sqlite3
import stat
import sys
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, Engine, func, insert, select
from sqlalchemy.exc import IntegrityError, StatementError

from spectio_server.store import db, schema
from spectio_server.store.db import UnsafeDatabase, default_db_dir, open_db
from spectio_server.store.schema import (
    environments,
    principals,
    projects,
    runs,
    workflow_versions,
    workflows,
)
from spectio_server.store.writer import Writer

NOW = datetime(2026, 10, 29, tzinfo=UTC)


def _dev(path: Path) -> str:
    st = os.stat(path)
    return f"{os.major(st.st_dev)}:{os.minor(st.st_dev)}"


def fake_mountinfo(path: Path, *fstypes: str, dev: str | None = None) -> Path:
    """A mountinfo table: a local root, then each of `fstypes` mounted in turn on `path`, the
    last one holding the device of `path` (or `dev`)."""
    point = str(path).replace(" ", "\\040")
    lines = ["1 0 254:254 / / rw - ext4 /dev/sda1 rw"]
    for i, fstype in enumerate(fstypes):
        last = i == len(fstypes) - 1
        device = (dev or _dev(path)) if last else f"0:{900 + i}"
        lines.append(f"{i + 2} 1 {device} / {point} rw shared:1 - {fstype} srv:/x rw")
    table = path.parent / f"mountinfo-{'-'.join(fstypes)}"
    table.write_text("\n".join(lines) + "\n")
    return table


def private_dir(path: Path) -> Path:
    path.mkdir(mode=0o700)
    return path


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    eng, _ = open_db(tmp_path)
    yield eng
    eng.dispose()


@pytest.fixture
def writer(engine: Engine) -> Iterator[Writer]:
    w = Writer(engine)
    yield w
    w.close()


@pytest.mark.parametrize(
    "stack", [("nfs4",), ("lustre",), ("gpfs",), ("autofs",), ("autofs", "nfs4")]
)
def test_refuses_network_fs(tmp_path: Path, stack: tuple[str, ...]) -> None:
    db_dir = private_dir(tmp_path / "db dir")
    with pytest.raises(UnsafeDatabase, match=stack[-1]) as refused:
        open_db(db_dir, mountinfo=fake_mountinfo(db_dir, *stack))
    assert "node-local" in str(refused.value)  # names the alternatives (architecture §7.2)
    assert not (db_dir / db.DB_FILE).exists()


def test_fs_type_falls_back_to_mount_point(tmp_path: Path) -> None:
    # No device matches (btrfs subvolumes, for one): the last longest mount point decides.
    db_dir = private_dir(tmp_path / "d")
    table = fake_mountinfo(db_dir, "ext4", "nfs4", dev="0:999")
    assert db.fs_type(db_dir, mountinfo=table) == "nfs4"
    assert db.fs_type(tmp_path, mountinfo=table) == "ext4"


def test_mountinfo_unreadable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "no-mountinfo"
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(UnsafeDatabase, match="no-mountinfo"):
        open_db(tmp_path, mountinfo=missing)  # fail closed on Linux
    monkeypatch.setattr(sys, "platform", "darwin")
    assert db.fs_type(tmp_path, mountinfo=missing) == "unknown"


@pytest.mark.parametrize("version", ["3.45.0", "3.51.2", "3.50.6", "3.44.5", "3.43.9"])
def test_refuses_old_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    monkeypatch.setattr(sqlite3, "sqlite_version", version)
    with pytest.raises(UnsafeDatabase, match=r"3\.51\.3"):
        open_db(tmp_path)
    for fixed in ["3.51.3", "3.52.0", "3.50.7", "3.44.6"]:
        monkeypatch.setattr(sqlite3, "sqlite_version", fixed)
        open_db(tmp_path)[0].dispose()


def test_pragmas(engine: Engine) -> None:
    with engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
        assert conn.exec_driver_sql("PRAGMA auto_vacuum").scalar() == 2  # INCREMENTAL
        assert conn.exec_driver_sql("PRAGMA busy_timeout").scalar() == 5000


def _add_principal(i: int, kind: str = "user", at: datetime = NOW) -> Callable[[Connection], None]:
    def fn(conn: Connection) -> None:
        conn.execute(insert(principals).values(id=f"prn_{i}", kind=kind, created_at=at))

    return fn


def test_writer_serialises(engine: Engine, writer: Writer) -> None:
    with ThreadPoolExecutor(max_workers=50) as pool:
        list(pool.map(lambda i: writer.submit(_add_principal(i)).result(), range(50)))
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(principals)).scalar() == 50


def test_writer_begins_immediate(tmp_path: Path, writer: Writer) -> None:
    def probe(_conn: Connection) -> str:
        other = sqlite3.connect(tmp_path / db.DB_FILE, timeout=0, isolation_level=None)
        try:
            other.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            return str(exc)
        finally:
            other.close()
        return "not locked"

    assert "locked" in writer.submit(probe).result()


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_writer_death_fails_queued_jobs(writer: Writer) -> None:
    go = threading.Event()

    def interrupted(_conn: Connection) -> None:
        go.wait()
        raise KeyboardInterrupt

    first = writer.submit(interrupted)
    queued = writer.submit(lambda _conn: None)
    go.set()
    with pytest.raises(KeyboardInterrupt):
        first.result(timeout=5)
    with pytest.raises(RuntimeError, match="writer stopped"):
        queued.result(timeout=5)
    with pytest.raises(RuntimeError):
        writer.submit(lambda _conn: None)


def test_principal_kinds(writer: Writer) -> None:  # api §6
    for i, kind in enumerate(["user", "service", "agent", "runner", "system"]):
        writer.submit(_add_principal(i, kind)).result()


def test_timestamps_are_utc(engine: Engine, writer: Writer) -> None:
    paris = datetime(2026, 10, 29, 12, 0, tzinfo=timezone(timedelta(hours=2)))
    writer.submit(_add_principal(1, at=paris)).result()
    with engine.connect() as conn:
        stored = conn.execute(select(principals.c.created_at)).scalar_one()
    assert stored == datetime(2026, 10, 29, 10, 0, tzinfo=UTC)
    assert stored.tzinfo is UTC
    with pytest.raises(StatementError, match="naive"):
        writer.submit(_add_principal(2, at=datetime(2026, 10, 29))).result()


def test_check_values_are_safe() -> None:
    with pytest.raises(ValueError, match="CHECK"):
        schema._check("t", "c", ("ok", "x') OR 1=1 --"))


def test_run_state_check_constraint(writer: Writer) -> None:
    def parents(conn: Connection) -> None:
        conn.execute(insert(projects).values(id="prj_1", owning_group_id="grp_1", created_at=NOW))
        conn.execute(insert(environments).values(id="env_1", kind="local", created_at=NOW))
        conn.execute(
            insert(workflows).values(
                id="wfl_1", project_id="prj_1", source="local", location="/w", created_at=NOW
            )
        )
        conn.execute(
            insert(workflow_versions).values(id="wfv_1", workflow_id="wfl_1", created_at=NOW)
        )

    def run(state: str) -> None:
        def fn(conn: Connection) -> None:
            conn.execute(
                insert(runs).values(
                    id=f"run_{state}",
                    project_id="prj_1",
                    workflow_version_id="wfv_1",
                    environment_id="env_1",
                    state=state,
                    created_at=NOW,
                )
            )

        writer.submit(fn).result()

    writer.submit(parents).result()
    run("queued")  # the parents are valid: only the state can fail below
    with pytest.raises(IntegrityError, match="ck_runs_state"):
        run("paused_forever")


def test_migration_matches_schema(engine: Engine) -> None:
    with engine.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), schema.metadata) == []


def _mode(path: Path) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


def test_database_files_private(tmp_path: Path) -> None:  # dev-env §15.3 req. 5
    old = os.umask(0o022)
    try:
        eng, _ = open_db(private_dir(tmp_path / "umask"))
        w = Writer(eng)
        w.submit(_add_principal(1)).result()
        base = tmp_path / "umask" / db.DB_FILE
        modes = {p.name: _mode(p) for p in (base, Path(f"{base}-wal"), Path(f"{base}-shm"))}
        w.close()
        eng.dispose()
    finally:
        os.umask(old)
    assert set(modes.values()) == {0o600}, modes


@pytest.mark.parametrize("unsafe", ["symlinked_db", "mode_0755", "other_uid"])
def test_open_db_refuses_unsafe_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unsafe: str
) -> None:
    db_dir = private_dir(tmp_path / "d")
    if unsafe == "symlinked_db":
        target = tmp_path / "elsewhere.db"
        target.touch(mode=0o600)
        (db_dir / db.DB_FILE).symlink_to(target)
    elif unsafe == "mode_0755":
        db_dir.chmod(0o755)
    else:
        uid = os.getuid() + 1000
        monkeypatch.setattr(os, "getuid", lambda: uid)
    with pytest.raises(UnsafeDatabase):
        open_db(db_dir)


def test_open_db_path_is_not_a_url(tmp_path: Path) -> None:
    db_dir = private_dir(tmp_path / "a%41?mode=ro#x")
    open_db(db_dir)[0].dispose()
    with sqlite3.connect(db_dir / db.DB_FILE) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
    conn.close()
    assert "runs" in tables
    assert sorted(p.name for p in tmp_path.iterdir()) == [db_dir.name]  # no stray database


def test_default_db_dir_private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    path = default_db_dir()
    assert path == tmp_path / f"spectio-{os.getuid()}"
    assert _mode(path) == 0o700
    assert default_db_dir() == path  # an existing private directory is accepted


@pytest.mark.parametrize("base", ["relative", "world_writable", "sticky"])
def test_default_db_dir_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, base: str
) -> None:
    system_tmp = private_dir(tmp_path / "system-tmp")
    monkeypatch.setattr(db, "SYSTEM_TMP", system_tmp)
    tmpdir = private_dir(tmp_path / "tmpdir")
    if base == "relative":
        monkeypatch.setenv("TMPDIR", "tmpdir")
    else:
        tmpdir.chmod(0o777 if base == "world_writable" else 0o1777)
        monkeypatch.setenv("TMPDIR", str(tmpdir))
    with caplog.at_level(logging.WARNING):
        path = default_db_dir()
    expected = tmpdir if base == "sticky" else system_tmp
    assert path == expected / f"spectio-{os.getuid()}"
    assert ("TMPDIR" in caplog.text) == (base != "sticky")


@pytest.mark.parametrize("squat", ["symlink", "other_uid", "mode_0755"])
def test_db_dir_squatted_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, squat: str
) -> None:
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    uid = os.getuid()
    if squat == "other_uid":  # the real user plays the squatter of a fake uid's path
        uid += 1000
        monkeypatch.setattr(os, "getuid", lambda: uid)
        tmp_path.chmod(0o1700)  # a sticky base, as /tmp, which the fake uid does not own
    squatted = tmp_path / f"spectio-{uid}"
    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    if squat == "symlink":
        squatted.symlink_to(target)
    else:
        squatted.mkdir(mode=0o755 if squat == "mode_0755" else 0o700)
    os.chmod(target, 0o700)
    before = os.lstat(squatted)

    with caplog.at_level(logging.WARNING):
        path = default_db_dir()

    assert path != squatted
    assert path.parent == tmp_path
    assert path.name.startswith(f"spectio-{uid}-")
    assert _mode(path) == 0o700
    assert f"uid {before.st_uid}" in caplog.text
    after = os.lstat(squatted)  # untouched: never tightened, never removed
    assert (after.st_mode, after.st_uid, after.st_ino) == (
        before.st_mode,
        before.st_uid,
        before.st_ino,
    )


def test_open_db_reports_created(tmp_path: Path) -> None:
    first, created = open_db(tmp_path)
    first.dispose()
    assert created
    second, created = open_db(tmp_path)
    second.dispose()
    assert not created


def test_open_db_created_when_never_migrated(tmp_path: Path) -> None:
    # A database file without an Alembic revision (an interrupted first start) is new.
    os.close(os.open(tmp_path / db.DB_FILE, os.O_CREAT | os.O_WRONLY, 0o600))
    eng, created = open_db(tmp_path)
    eng.dispose()
    assert created
