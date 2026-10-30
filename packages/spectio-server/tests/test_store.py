"""The SQLite store and its discipline (api §7, architecture §7.2; P1 Task 2)."""

import logging
import os
import sqlite3
import stat
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Connection, Engine, func, insert, select
from sqlalchemy.exc import IntegrityError

from spectio_server.store import db
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


def fake_mounts(path: Path, fstype: str) -> Path:
    """A mounts table where `path` sits on a mount of type `fstype`, below a local root."""
    table = path.parent / f"mounts-{fstype}"
    mountpoint = str(path).replace(" ", "\\040")
    table.write_text(f"/dev/sda1 / ext4 rw 0 0\nsrv:/x {mountpoint} {fstype} rw 0 0\n")
    return table


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


@pytest.mark.parametrize("fstype", ["nfs4", "lustre", "gpfs"])
def test_refuses_network_fs(tmp_path: Path, fstype: str) -> None:
    db_dir = tmp_path / "db dir"
    db_dir.mkdir()
    with pytest.raises(UnsafeDatabase, match=fstype) as refused:
        open_db(db_dir, mounts=fake_mounts(db_dir, fstype))
    assert "node-local" in str(refused.value)  # names the alternatives (architecture §7.2)
    assert not (db_dir / db.DB_FILE).exists()
    assert db.fs_type(db_dir / "sub", mounts=fake_mounts(db_dir, fstype)) == fstype
    assert db.fs_type(tmp_path, mounts=fake_mounts(db_dir, fstype)) == "ext4"


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


def test_writer_serialises(engine: Engine, writer: Writer) -> None:
    def add(i: int) -> None:
        def fn(conn: Connection) -> None:
            conn.execute(insert(principals).values(id=f"prn_{i}", kind="user", created_at=NOW))

        writer.submit(fn).result()

    with ThreadPoolExecutor(max_workers=50) as pool:
        list(pool.map(add, range(50)))  # re-raises any SQLITE_BUSY
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(principals)).scalar() == 50


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


def _mode(path: Path) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


def test_default_db_dir_private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    path = default_db_dir()
    assert path == tmp_path / f"spectio-{os.getuid()}"
    assert _mode(path) == 0o700
    assert default_db_dir() == path  # an existing private directory is accepted


@pytest.mark.parametrize("squat", ["symlink", "other_uid", "mode_0755"])
def test_db_dir_squatted_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, squat: str
) -> None:
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    uid = os.getuid()
    if squat == "other_uid":  # the real user plays the squatter of a fake uid's path
        uid += 1000
        monkeypatch.setattr(os, "getuid", lambda: uid)
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
