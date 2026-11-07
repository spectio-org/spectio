"""dev-env §15.3 req. 5: directories 0700, secrets and database files 0600 (P1 Task 15).

The data directory (`~/.spectio`), the node-local database directory and the run directories
are 0700; `server.key`, the database files, `serve.lock`, `server.json` and `spectio.toml` are
0600. Files are created at their mode (`os.open(..., 0o600)`), never chmod-ed after the write,
so the umask cannot loosen them. A loose data directory is refused, never tightened (inbox
#83 rule 1); the node-local directory is never tightened either (Task 2).
"""

import json
import os
import shlex
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from spectio.cli.main import app
from spectio.config import Settings, UnsafeConfig
from spectio.runner.headscript import write_launch_files
from spectio.runner.rundir import RunManifest, RunPaths, Workflow, make_run_dirs, write_run_manifest
from spectio.runner.types import LaunchSpec
from spectio_server import app as app_mod
from spectio_server.auth.secrets import KEY_FILE
from spectio_server.serve import LOCK, STATE, ServeError, started
from spectio_server.store.db import DB_FILE

from ..conftest import free_port

RUN_ID = "run_01K8T2F1XT0000000000000015"


@pytest.fixture(autouse=True)
def lone_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mount the API, as on one person's machine (SEC-P3T17-06)."""
    monkeypatch.setattr(app_mod, "shared_host", lambda: None)


def mode(path: Path) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


def init_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """`spectio init --local` in a fresh HOME and TMPDIR; the settings it recorded."""
    home, tmp = tmp_path / "home", tmp_path / "tmp"
    for path in (home, tmp):
        os.mkdir(path, 0o700)
    for name in list(os.environ):
        if name.startswith(("SPECTIO_", "NXF_")):
            monkeypatch.delenv(name)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TMPDIR", str(tmp))
    monkeypatch.setenv("NXF_HOME", str(tmp_path / "nxf"))  # nf-spectio, outside the roots
    meta = tmp_path / "bridges" / "nf-spectio-0.0.1" / "classes" / "META-INF"
    meta.mkdir(parents=True, exist_ok=True)  # as the Task 6 build leaves it
    (meta / "MANIFEST.MF").write_text("Plugin-Id: nf-spectio\nPlugin-Version: 0.0.1\n")
    monkeypatch.setenv("SPECTIO_BRIDGES_DIR", str(tmp_path / "bridges"))
    (home / ".bash_profile").write_text(f"PATH={shlex.quote(str(tmp_path / 'empty'))}\n")
    result = CliRunner().invoke(app, ["init", "--local", "--port", str(free_port())], input="")
    assert result.exit_code == 0, result.output
    return Settings()


@contextmanager
def serving(settings: Settings) -> Iterator[Path]:
    """`spectio serve`, booted and bound; yields the database directory it used."""
    with started(settings):
        yield Path(json.loads((settings.data_dir / STATE).read_text())["db_dir"])


def launch(settings: Settings) -> RunPaths:
    """A run as the runner leaves it before the head starts: manifest and launch files."""
    paths = make_run_dirs(settings.runs_root, RUN_ID)
    write_run_manifest(
        paths.run_dir,
        RunManifest(
            run_id=RUN_ID,
            name="modes",
            workflow=Workflow(location="/pipelines/happy", engine="nextflow"),
            params={"greeting": "hi"},
            profiles=[],
            created_at="2026-11-06T00:00:00Z",
        ),
    )
    write_launch_files(
        LaunchSpec(
            run_id=RUN_ID,
            launch_n=1,
            engine="nextflow",
            engine_cmd="false",
            location=Path("/pipelines/happy"),
            launch_dir=paths.launch_dir,
            work_dir=paths.work_dir,
            params={"greeting": "hi"},
        )
    )
    return paths


@pytest.fixture
def initialised(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    return init_home(tmp_path, monkeypatch)


@pytest.fixture
def served(initialised: Settings) -> Iterator[tuple[Settings, Path]]:
    with serving(initialised) as db_dir:
        yield initialised, db_dir


@pytest.fixture
def launched(initialised: Settings) -> RunPaths:
    return launch(initialised)


def check_data_dir(settings: Settings) -> None:
    assert mode(settings.data_dir) == 0o700
    assert mode(settings.data_dir / "spectio.toml") == 0o600


def check_served(settings: Settings, db_dir: Path) -> None:
    assert mode(db_dir) == 0o700
    for name in (KEY_FILE, DB_FILE, f"{DB_FILE}-wal", f"{DB_FILE}-shm", LOCK):
        assert mode(db_dir / name) == 0o600, name
    assert mode(settings.data_dir / STATE) == 0o600


def check_run(paths: RunPaths) -> None:
    for path in (paths.run_dir, paths.launch_dir, paths.work_dir):
        assert mode(path) == 0o700, path
    for top, dirs, files in os.walk(paths.run_dir):
        for name in dirs:
            assert mode(Path(top, name)) == 0o700, Path(top, name)
        for name in files:
            assert mode(Path(top, name)) == 0o600, Path(top, name)


def test_req5_data_dir_0700(initialised: Settings) -> None:
    check_data_dir(initialised)


def test_req5_key_and_db_files_0600(served: tuple[Settings, Path]) -> None:
    check_served(*served)


def test_req5_run_dirs_0700(launched: RunPaths) -> None:
    check_run(launched)


def _recorder(
    monkeypatch: pytest.MonkeyPatch, roots: Callable[[], list[Path]]
) -> list[tuple[str, str, int]]:
    """Record every file or directory Spectio creates or chmods under `roots()`, with its mode.
    A name relative to a directory descriptor is always one of Spectio's own."""
    seen: list[tuple[str, str, int]] = []

    def ours(path: Any, dir_fd: int | None) -> bool:
        if dir_fd is not None and not os.path.isabs(path):
            return True
        if isinstance(path, int):
            return False
        real = Path(os.path.abspath(path))
        return any(real.is_relative_to(root) for root in roots())

    real_open, real_mkdir, real_chmod = os.open, os.mkdir, os.chmod

    def fake_open(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        if flags & os.O_CREAT and ours(path, dir_fd):
            seen.append(("open", str(path), mode))
        return real_open(path, flags, mode, dir_fd=dir_fd)

    def fake_mkdir(path: Any, mode: int = 0o777, *, dir_fd: int | None = None) -> None:
        if ours(path, dir_fd):
            seen.append(("mkdir", str(path), mode))
        real_mkdir(path, mode, dir_fd=dir_fd)

    def fake_chmod(path: Any, mode: int, **kw: Any) -> None:
        if ours(path, kw.get("dir_fd")):
            seen.append(("chmod", str(path), mode))
        real_chmod(path, mode, **kw)

    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "mkdir", fake_mkdir)
    monkeypatch.setattr(os, "chmod", fake_chmod)
    return seen


def test_req5_umask_does_not_loosen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    roots: list[Path] = []
    seen = _recorder(monkeypatch, lambda: roots)
    old = os.umask(0)
    try:
        roots += [tmp_path / "home" / ".spectio", tmp_path / "home" / "spectio-runs"]
        roots.append(tmp_path / "tmp")  # the default node-local database directory's parent
        settings = init_home(tmp_path, monkeypatch)
        check_data_dir(settings)
        with serving(settings) as db_dir:
            check_served(settings, db_dir)
            check_run(launch(settings))
    finally:
        os.umask(old)
    assert seen, "nothing was recorded"
    assert not [s for s in seen if s[0] == "chmod"], "a file was chmod-ed after its creation"
    wide = [s for s in seen if s[2] & (0o077 if s[0] == "mkdir" else 0o177)]
    assert not wide, f"created wider than 0700 / 0600: {wide}"


def test_req5_key_not_in_shared_home(served: tuple[Settings, Path]) -> None:
    _, db_dir = served
    home = Path.home()
    assert not db_dir.is_relative_to(home)
    assert (db_dir / KEY_FILE).exists()
    key = (db_dir / KEY_FILE).read_bytes()
    for top, _dirs, files in os.walk(home):  # the data directory, the runs root, the config
        for name in files:
            assert key not in Path(top, name).read_bytes(), Path(top, name)
            assert name != KEY_FILE


def test_req5_existing_loose_dir_tightened_or_refused(initialised: Settings) -> None:
    """A loose data directory is refused, by `spectio init` and by `spectio serve`, and left as
    it is; a loose node-local directory is never tightened (the mkdtemp fallback, Task 2)."""
    data_dir = initialised.data_dir
    data_dir.chmod(0o755)
    result = CliRunner().invoke(app, ["init", "--local"], input="")
    assert result.exit_code == 2 and f"chmod 700 {data_dir}" in result.output, result.output
    with pytest.raises(ServeError, match=rf"{data_dir}.*mode 755"), started(initialised):
        pass
    assert mode(data_dir) == 0o755 and not (data_dir / STATE).exists()
    data_dir.chmod(0o700)
    squatted = Path(os.environ["TMPDIR"]) / f"spectio-{os.getuid()}"
    squatted.chmod(0o755)
    with serving(initialised) as db_dir:
        assert db_dir != squatted and mode(db_dir) == 0o700
    assert mode(squatted) == 0o755


def test_req5_state_file_never_partial(
    initialised: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-P3T11-02: the first `server.json` is written under a temporary name and linked into
    place, so another node never reads an empty or partial file; it still acts as the lock."""
    calls: list[str] = []
    real_open = os.open

    def fake_open(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        if flags & os.O_CREAT:
            calls.append(str(path))
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", fake_open)
    with serving(initialised):
        assert (initialised.data_dir / STATE).read_bytes().startswith(b"{")
    assert STATE not in [os.path.basename(c) for c in calls]
    assert not [p for p in initialised.data_dir.iterdir() if p.name.startswith(".")]


def test_req5_lock_after_db_dir_checked(initialised: Settings, tmp_path: Path) -> None:
    """SEC-P3T11-01: `serve.lock` is created only once the database directory and its parents
    have passed the checks of `open_db`."""
    shared = tmp_path / "shared"
    os.mkdir(shared, 0o700)
    shared.chmod(0o777)  # writable by others, not sticky
    db_dir = shared / "db"
    os.mkdir(db_dir, 0o700)
    settings = initialised.model_copy(update={"db_dir": db_dir})
    with pytest.raises(ServeError, match="parent"), started(settings):
        pass
    assert not (db_dir / LOCK).exists()


@pytest.mark.parametrize("loose", ["file", "dir", "owner"])
def test_req5_config_others_cannot_write(
    initialised: Settings, monkeypatch: pytest.MonkeyPatch, loose: str
) -> None:
    """SEC-P3T08-03: `spectio.toml` holds shell commands, so a file or directory another user
    can write is refused before it is read."""
    path = initialised.data_dir / "spectio.toml"
    if loose == "file":
        path.chmod(0o666)
    elif loose == "dir":
        initialised.data_dir.chmod(0o777)
    else:
        monkeypatch.setattr(os, "geteuid", lambda: os.getuid() + 1)
    with pytest.raises(UnsafeConfig, match=str(path)):
        Settings()
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 1 and "fail config" in result.output


def test_req5_config_missing_is_fine(initialised: Settings) -> None:
    (initialised.data_dir / "spectio.toml").unlink()
    assert Settings().port != 0
