"""`spectio doctor` (P1 Task 8, architecture §7.3 and §13.8, G6 of P2 §10.7): one
`ok|warn|fail <check> <detail>` line per check, exit 1 on any `fail`."""

import os
import socket
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from spectio.cli.doctor import run_doctor
from spectio.config import Settings, write_config


def _dev(path: Path) -> str:
    st = os.stat(path)
    return f"{os.major(st.st_dev)}:{os.minor(st.st_dev)}"


def mountinfo(path: Path, fstype: str) -> Path:
    """A mountinfo table that puts `path` on a `fstype` mount."""
    table = path.parent / f"mountinfo-{fstype}"
    table.write_text(
        "1 0 254:254 / / rw - ext4 /dev/sda1 rw\n"
        f"2 1 {_dev(path)} / {path} rw shared:1 - {fstype} srv:/x rw\n"
    )
    return table


def doctor(
    capsys: pytest.CaptureFixture[str], settings: Settings, **kwargs: Any
) -> tuple[int, list[str]]:
    code = run_doctor(settings, **kwargs)
    return code, capsys.readouterr().out.splitlines()


def configured(home: Path, fakebin: Path | None = None, **values: Any) -> Settings:
    """Settings as `spectio init` leaves them, written to spectio.toml; the database directory
    exists, private."""
    db_dir = home.parent / "db"
    db_dir.mkdir(mode=0o700, exist_ok=True)
    engines = {}
    if fakebin:
        engines = {
            "nextflow_cmd": str(fakebin / "nextflow"),
            "snakemake_cmd": str(fakebin / "snakemake"),
        }
    values = {"db_dir": db_dir, "host": socket.gethostname(), "engines": engines, **values}
    settings = Settings(**values)
    (home / ".spectio").mkdir(mode=0o700, exist_ok=True)
    write_config(settings)
    return settings


def line(lines: list[str], check: str) -> str:
    (found,) = [x for x in lines if x.split()[1] == check]
    return found


def test_doctor_reports_engines(
    home: Path, tools: Callable[..., Path], capsys: pytest.CaptureFixture[str]
) -> None:
    fakebin = tools("nextflow", "java", "tmux", "sbatch")
    settings = configured(home, engines={"nextflow_cmd": str(fakebin / "nextflow")})
    code, lines = doctor(capsys, settings)
    assert code == 1
    assert line(lines, "nextflow") == f"ok nextflow 26.10.4 {fakebin / 'nextflow'}"
    assert line(lines, "snakemake") == "fail snakemake not found on PATH"
    assert line(lines, "java") == "ok java 21"
    assert line(lines, "tmux") == f"ok tmux {fakebin / 'tmux'}"
    assert line(lines, "sbatch") == f"ok sbatch {fakebin / 'sbatch'}"
    assert [x for x in lines if x.startswith("fail")] == ["fail snakemake not found on PATH"]


def test_doctor_engine_command_fails(
    home: Path, fakebin: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = configured(home, fakebin, engines={"nextflow_cmd": "nextflow-gone"})
    _, lines = doctor(capsys, settings)
    assert line(lines, "nextflow").startswith("fail nextflow `nextflow-gone -version` ")


def test_doctor_reports_fs_and_sqlite(
    home: Path, fakebin: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = configured(home, fakebin, executor="local")
    db_dir = settings.db_dir
    assert db_dir
    code, lines = doctor(capsys, settings, mountinfo=mountinfo(db_dir, "ext4"))
    assert code == 0, lines
    assert line(lines, "sqlite") == f"ok sqlite {sqlite3.sqlite_version}"
    assert line(lines, "db_dir") == f"ok db_dir {db_dir} (ext4, 0700)"

    code, lines = doctor(capsys, settings, mountinfo=mountinfo(db_dir, "nfs4"))
    assert code == 1
    assert line(lines, "db_dir").startswith(f"fail db_dir {db_dir} is on a nfs4 file system")

    db_dir.chmod(0o750)
    code, lines = doctor(capsys, settings, mountinfo=mountinfo(db_dir, "ext4"))
    assert code == 1
    assert line(lines, "db_dir").startswith(f"fail db_dir {db_dir} must be a directory")

    db_dir.rmdir()
    code, lines = doctor(capsys, settings)
    assert code == 0, lines
    assert line(lines, "db_dir") == f"warn db_dir {db_dir} is missing: the next start rebuilds it"

    monkeypatch.setattr(sqlite3, "sqlite_version", "3.45.0")
    code, lines = doctor(capsys, settings)
    assert code == 1
    assert line(lines, "sqlite").startswith("fail sqlite SQLite 3.45.0 lacks the WAL-reset fix")


ONE_SHOT = "NXF_PLUGINS_DEFAULT=nf-spectio@0.0.1 nextflow run"


@pytest.mark.parametrize(
    ("value", "nxf_config", "copy", "expected"),
    [
        (None, None, False, "ok"),
        ("false", None, True, "warn"),
        ("nf-schema@2.7.2", None, True, "warn"),
        ("nf-spectio@0.0.2", None, True, "warn"),
        ("nf-spectio", None, True, "warn"),
        (None, "plugins {\n  id 'nf-spectio@0.0.1'\n}\n", True, "warn"),
        ("nf-schema@2.7.2,nf-spectio@0.0.1", None, False, "fail"),
        ("nf-schema@2.7.2,nf-spectio@0.0.1", None, True, "ok"),
        (None, "plugins { id 'nf-schema@2.7.2' }\n", False, "ok"),
    ],
)
def test_doctor_nxf_plugins_default(
    home: Path,
    fakebin: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    value: str | None,
    nxf_config: str | None,
    copy: bool,
    expected: str,
) -> None:
    nxf_home = home / ".nextflow"
    (nxf_home / "plugins").mkdir(parents=True)
    if value is not None:
        monkeypatch.setenv("NXF_PLUGINS_DEFAULT", value)
    if nxf_config is not None:
        (nxf_home / "config").write_text(nxf_config)
    if copy:
        (nxf_home / "plugins" / "nf-spectio-0.0.1").mkdir(mode=0o700)  # as unpacked
    _, lines = doctor(capsys, configured(home, fakebin, executor="local"))
    found = line(lines, "nxf_plugins_default")
    assert found.split()[0] == expected, found
    if value is None and expected == "ok":
        assert ONE_SHOT in found  # the one-shot line for runs from a terminal
    if expected == "fail":
        assert str(nxf_home / "plugins" / "nf-spectio-0.0.1") in found


def test_doctor_local_skips_sbatch(
    home: Path, fakebin: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, lines = doctor(capsys, configured(home, fakebin, executor="local"))
    assert code == 0, lines
    assert not [x for x in lines if x.startswith("fail")]
    assert line(lines, "sbatch") == "ok sbatch not needed in local mode"

    code, lines = doctor(capsys, configured(home, fakebin, executor="slurm"))
    assert code == 1
    assert line(lines, "sbatch") == "fail sbatch not found on PATH"


def test_doctor_host_pin_and_config(
    home: Path, fakebin: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = configured(home, fakebin, executor="local")
    _, lines = doctor(capsys, settings)
    assert line(lines, "host") == f"ok host {socket.gethostname()}"
    assert line(lines, "config").startswith("ok config ")
    _, lines = doctor(capsys, settings.model_copy(update={"host": "login-9"}))
    assert line(lines, "host") == (
        f"warn host this is {socket.gethostname()}; spectio init recorded login-9"
    )
    (home / ".spectio" / "spectio.toml").unlink()
    code, lines = doctor(capsys, settings)
    assert code == 1
    assert line(lines, "config").startswith("fail config ")


def test_doctor_default_db_dir(
    home: Path, fakebin: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # db_dir unset (SEC-P3T08-01): doctor resolves the default without creating it
    settings = configured(home, fakebin, executor="local", db_dir=None)
    default = Path(os.environ["TMPDIR"]) / f"spectio-{os.getuid()}"
    code, lines = doctor(capsys, settings)
    assert code == 0, lines
    assert line(lines, "db_dir") == f"warn db_dir {default} is missing: the next start rebuilds it"
    assert not default.exists()
    default.mkdir(mode=0o755)  # squatted: the next start falls back to mkdtemp
    code, lines = doctor(capsys, settings)
    assert code == 0, lines
    assert line(lines, "db_dir").startswith(f"warn db_dir {default} is not a private directory")
    assert f"owner uid {os.getuid()}" in line(lines, "db_dir")
    default.chmod(0o700)
    code, lines = doctor(capsys, settings, mountinfo=mountinfo(default, "ext4"))
    assert line(lines, "db_dir") == f"ok db_dir {default} (ext4, 0700)"


def test_doctor_relative_plugins_dir(
    home: Path, fakebin: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-P3T09-05: a relative NXF_HOME is a `fail`, not a crash."""
    monkeypatch.setenv("NXF_HOME", "nxf")
    code, lines = doctor(capsys, configured(home, fakebin, executor="local"))
    assert code == 1
    assert line(lines, "nxf_plugins_default").startswith("fail")


def test_doctor_refuses_an_untrusted_copy(
    home: Path, fakebin: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-P3T09-R5-02: doctor checks the copy as the launcher does: a group-writable copy is a
    `fail` with the launcher's message."""
    copy = home / ".nextflow" / "plugins" / "nf-spectio-0.0.1"
    copy.mkdir(parents=True)
    copy.chmod(0o775)
    monkeypatch.setenv("NXF_PLUGINS_DEFAULT", "nf-spectio@0.0.1")
    code, lines = doctor(capsys, configured(home, fakebin, executor="local"))
    found = line(lines, "nxf_plugins_default")
    assert code == 1 and found.startswith("fail") and "only you can write" in found, found
