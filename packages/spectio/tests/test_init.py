"""`spectio init` (P1 Task 8, G6 of P2 §10.7): the data directory, `spectio.toml` and the rows
of P1 Assumption 18."""

import os
import shutil
import socket
import stat
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from spectio.cli.main import app
from spectio.config import Settings, config_path
from spectio_server.store.db import DB_FILE, open_db
from spectio_server.store.schema import environments, principals, projects, runners


def init(*args: str) -> Any:
    """`spectio init ARGS` with stdin closed: it must never prompt."""
    return CliRunner().invoke(app, ["init", *args], input="")


def recorded() -> dict[str, Any]:
    with config_path().open("rb") as f:
        return tomllib.load(f)


def rows(db_dir: Path) -> dict[str, list[Any]]:
    engine, created = open_db(db_dir)
    assert not created
    try:
        with engine.connect() as conn:
            return {
                t.name: list(conn.execute(select(t)))
                for t in (principals, projects, environments, runners)
            }
    finally:
        engine.dispose()


def mode(path: Path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def default_db() -> Path:
    """The default database directory of the `home` fixture: `$TMPDIR/spectio-<uid>`."""
    return Path(os.environ["TMPDIR"]) / f"spectio-{os.getuid()}"


def test_init_creates_one_environment(home: Path, fakebin: Path) -> None:
    runs_root = home / "runs"
    runs_root.mkdir(mode=0o700)
    for _ in range(2):  # a second init adds nothing
        result = init("--runs-root", str(runs_root))
        assert result.exit_code == 0, result.output
    found = rows(default_db())
    assert {name: len(r) for name, r in found.items()} == {
        "principals": 1,
        "projects": 1,
        "environments": 1,
        "runners": 1,
    }
    (user,), (project,), (env,), (runner,) = found.values()
    assert user.kind == "user" and user.display_name
    assert project.name == "default"
    assert env.kind == "slurm" and env.config == {"runs_root": str(runs_root)}
    assert runner.environment_id == env.id and runner.principal_id == user.id
    assert runner.version == "0.0.1"


def test_runs_root_must_exist_and_be_absolute(home: Path, fakebin: Path) -> None:
    shared = home / "shared"
    shared.mkdir(mode=0o700)
    shared.chmod(0o775)  # a group-writable runs root (dev-env §15.3 req. 10)
    for value, message in [
        ("runs", "absolute"),
        (str(home / "missing"), "does not exist"),
        (str(shared), "others cannot write"),
    ]:
        result = init("--runs-root", value)
        assert result.exit_code == 2, result.output
        assert message in result.output
        assert not config_path().exists()


def test_init_records_engine_commands(home: Path, fakebin: Path) -> None:
    assert init().exit_code == 0
    engines = recorded()["engines"]
    assert engines["nextflow_cmd"] == str(fakebin / "nextflow")  # from the login shell's PATH
    assert engines["snakemake_cmd"] == str(fakebin / "snakemake")
    explicit = "module load Nextflow/26.10.4 && nextflow"
    assert init("--nextflow", explicit).exit_code == 0
    assert recorded()["engines"]["nextflow_cmd"] == explicit  # kept as given
    assert recorded()["engines"]["snakemake_cmd"] == str(fakebin / "snakemake")


def test_init_engine_missing_still_records(home: Path) -> None:
    result = init()  # nothing on the login PATH
    assert result.exit_code == 0, result.output
    assert "nextflow not found" in result.output
    assert "nextflow_cmd" not in recorded()["engines"]


def test_init_defaults_unattended(home: Path, fakebin: Path) -> None:
    result = init()
    assert result.exit_code == 0, result.output
    config = recorded()
    data_dir, db_dir = home / ".spectio", default_db()
    runs_root = home / "spectio-runs"
    assert config_path() == data_dir / "spectio.toml"
    assert config["data_dir"] == str(data_dir)
    assert "db_dir" not in config  # resolved at each start, not pinned (§15.3 fallback)
    assert config["runs_root"] == str(runs_root)
    assert config["executor"] == "slurm"
    assert config["host"] == socket.gethostname()
    assert isinstance(config["port"], int)
    assert config["engines"]["nxf_opts"] == "-Xmx2g"
    assert config["runner"] == {"head_watch_s": 5.0, "spool_s": 2.0}
    assert "slurm" in config  # partition and account unset: an empty table to fill in
    for path in (data_dir, db_dir, runs_root):  # private to the user (SEC-P3T3-09)
        assert mode(path) == 0o700, path
    assert mode(config_path()) == 0o600
    assert (db_dir / DB_FILE).exists()


@pytest.fixture
def port_8080_taken() -> Iterator[None]:
    """Port 8080 on 127.0.0.1 is in use: by this socket, or already by someone else."""
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", 8080))
        sock.listen()
    except OSError:
        pass
    yield
    sock.close()


def test_init_port_taken_picks_one_and_keeps_it(
    home: Path, fakebin: Path, port_8080_taken: None
) -> None:
    assert init().exit_code == 0
    port = recorded()["port"]
    assert port != 8080
    assert init().exit_code == 0
    assert recorded()["port"] == port  # picked once (P1 Assumption 10)
    assert init("--port", "9123").exit_code == 0
    assert recorded()["port"] == 9123


def test_init_local_environment(home: Path, fakebin: Path) -> None:
    result = init("--local")
    assert result.exit_code == 0, result.output
    config = recorded()
    assert config["executor"] == "local"
    assert "slurm" not in config  # no [slurm] options written
    (env,) = rows(default_db())["environments"]
    assert env.kind == "local"
    result = init("--local", "--partition", "short")
    assert result.exit_code == 2
    assert "SLURM" in result.output


def test_init_local_refused_off_linux(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    result = init("--local")
    assert result.exit_code == 2
    assert "Local mode needs Linux in 0.0.1" in result.output
    assert not (home / ".spectio").exists()


def test_init_needs_the_server_package(
    home: Path, fakebin: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "spectio_server.bootstrap", None)  # as if not installed
    result = init()
    assert result.exit_code == 2
    assert "spectio[server]" in result.output
    assert not (home / ".spectio").exists() and not (home / "spectio-runs").exists()


def test_settings_layers(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # built-in defaults < spectio.toml < SPECTIO_* < flags (architecture §7.3)
    config_path().parent.mkdir(mode=0o700)
    config_path().write_text('port = 9000\n[slurm]\npartition = "toml"\naccount = "toml"\n')
    assert Settings().port == 9000
    monkeypatch.setenv("SPECTIO_PORT", "9001")
    monkeypatch.setenv("SPECTIO_SLURM_ACCOUNT", "env")
    monkeypatch.setenv("SPECTIO_ENGINES_EXTRA_ARGS_SNAKEMAKE", "--keep-going --cores 'a b'")
    settings = Settings()
    assert settings.port == 9001
    assert (settings.slurm.partition, settings.slurm.account) == ("toml", "env")
    assert settings.engines.extra_args == {"snakemake": ["--keep-going", "--cores", "a b"]}
    flagged = Settings(port=9002, slurm={"partition": "flag"})
    assert flagged.port == 9002
    assert (flagged.slurm.partition, flagged.slurm.account) == ("flag", "env")
    assert Settings().runner.head_watch_s == 5
    assert Settings().data_dir == home / ".spectio"


def test_bad_config_refused(home: Path, fakebin: Path) -> None:
    config_path().parent.mkdir(mode=0o700)
    for text in ("port = [", "colour = 1\n"):  # not TOML; an unknown key
        config_path().write_text(text)
        result = init()
        assert result.exit_code == 2, result.output
        assert "spectio init:" in result.output
        doctor = CliRunner().invoke(app, ["doctor"])
        assert doctor.exit_code == 1
        assert doctor.output.startswith("fail config ")


def test_extra_args_per_engine_round_trip(home: Path, fakebin: Path) -> None:
    # the spectio.toml of P1 Task 22: Snakemake-only flags, kept away from Nextflow
    flags = ["--slurm-init-seconds-before-status-checks", "5"]
    config_path().parent.mkdir(mode=0o700)
    config_path().write_text(f"engines.extra_args.snakemake = {flags!r}\n".replace("'", '"'))
    result = init()
    assert result.exit_code == 0, result.output
    assert recorded()["engines"]["extra_args"] == {"snakemake": flags}
    assert Settings().engines.extra_args == {"snakemake": flags}
    config_path().write_text('engines.extra_args.cromwell = ["-x"]\n')
    assert init().exit_code == 2  # an engine 0.0.1 does not run


def test_init_squatted_default_db_dir(home: Path, fakebin: Path) -> None:
    # SEC-P3T08-01: the default is resolved at each init, so the mkdtemp fallback still applies
    assert init().exit_code == 0
    squatted = default_db()
    shutil.rmtree(squatted)  # the node-local temporary directory was purged
    squatted.mkdir(mode=0o755)  # and another user took the path
    if os.getuid() == 0:
        os.chown(squatted, 4242, 4242)
    result = init()
    assert result.exit_code == 0, result.output
    used = [p for p in squatted.parent.iterdir() if p.name.startswith(f"{squatted.name}-")]
    assert len(used) == 1 and mode(used[0]) == 0o700
    assert (used[0] / DB_FILE).exists()
    assert "db_dir" not in recorded()
    explicit = init("--db-dir", str(squatted))  # chosen explicitly: refused, naming the owner
    assert explicit.exit_code == 2
    assert f"owner uid {os.stat(squatted).st_uid}" in explicit.output
