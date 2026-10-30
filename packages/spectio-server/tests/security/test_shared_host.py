"""SEC-P3T17-06: in local mode, the session-less API is not served on a machine that looks like
a cluster node or a shared one (inbox #86), whatever the configuration says."""

import os
import shutil
from pathlib import Path

import pytest

from spectio_server import app as app_mod


@pytest.fixture
def lone_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """No SLURM signal and a /proc with only this user's processes; returns that /proc."""
    proc = tmp_path / "proc"
    (proc / "1").mkdir(parents=True)
    (proc / "1" / "status").write_text(f"Name:\tx\nUid:\t{os.getuid()}\t0\t0\t0\n")
    (proc / "self").mkdir()
    monkeypatch.delenv("SLURM_CONF", raising=False)
    monkeypatch.setattr(app_mod, "SLURM_CONF_FILE", tmp_path / "no-slurm.conf")
    monkeypatch.setattr(app_mod, "PROC", proc)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setattr(app_mod, "_a_person", lambda uid: True)
    return proc


def process_of(proc: Path, pid: int, uid: int) -> None:
    (proc / str(pid)).mkdir()
    (proc / str(pid) / "status").write_text(f"Name:\tx\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n")


def test_lone_host_not_shared(lone_host: Path) -> None:
    process_of(lone_host, 2, 0)  # root
    process_of(lone_host, 3, 999)  # a system account
    process_of(lone_host, 4, 65534)  # nobody
    assert app_mod.shared_host() is None


def test_slurm_conf_variable(lone_host: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLURM_CONF", "/etc/slurm-llnl/slurm.conf")
    assert "SLURM_CONF" in (app_mod.shared_host() or "")


def test_slurm_conf_file(lone_host: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    conf = tmp_path / "slurm.conf"
    conf.write_text("ClusterName=x\n")
    monkeypatch.setattr(app_mod, "SLURM_CONF_FILE", conf)
    assert str(conf) in (app_mod.shared_host() or "")


def test_sinfo_on_path(lone_host: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    assert "sinfo" in (app_mod.shared_host() or "")


def test_process_of_another_user(lone_host: Path) -> None:
    other = 1000 if os.getuid() != 1000 else 1001
    process_of(lone_host, 2, other)
    assert f"uid {other}" in (app_mod.shared_host() or "")


def test_uid_with_no_account_not_a_person(lone_host: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A service with no user account (a container's sandbox daemon) is not another user."""
    monkeypatch.setattr(app_mod, "_a_person", lambda uid: False)
    process_of(lone_host, 2, 64321)
    assert app_mod.shared_host() is None
