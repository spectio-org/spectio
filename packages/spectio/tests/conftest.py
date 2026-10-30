"""Shared fixtures of the CLI tests: a private HOME and TMPDIR, and fake tools on the login PATH."""

import os
import shlex
from collections.abc import Callable
from pathlib import Path

import pytest

# What each fake prints: the version lines of the real tools (nextflow's as build.sh reads it).
FAKES = {
    "nextflow": 'echo "      N E X T F L O W"; echo "      version 26.10.4 build 5960"',
    "snakemake": "echo 9.27.1",
    "java": "echo 'openjdk version \"21.0.5\" 2024-10-15' >&2",
    "tmux": "exit 0",
    "sbatch": "exit 0",
}


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """HOME and TMPDIR private to the test, no SPECTIO_* or NXF_* variable, and a login shell
    whose PATH holds nothing."""
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    tmp = tmp_path / "tmp"
    tmp.mkdir(mode=0o700)
    for name in list(os.environ):
        if name.startswith(("SPECTIO_", "NXF_")):
            monkeypatch.delenv(name)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TMPDIR", str(tmp))
    login_path(home, tmp_path / "empty")
    return home


def login_path(home: Path, *dirs: Path) -> None:
    """The login shell's PATH is exactly `dirs` (its profile resets PATH, as a site's does)."""
    path = ":".join(str(d) for d in dirs)
    (home / ".bash_profile").write_text(f"PATH={shlex.quote(path)}; export PATH\n")


@pytest.fixture
def tools(home: Path) -> Callable[..., Path]:
    """`tools(*names)`: fake `names` in a fresh directory that becomes the login shell's whole
    PATH; returns that directory."""
    count = 0

    def make(*names: str) -> Path:
        nonlocal count
        count += 1
        fakebin = home.parent / f"fakebin{count}"
        fakebin.mkdir()
        for name in names:
            tool = fakebin / name
            tool.write_text(f"#!/bin/sh\n{FAKES[name]}\n")
            tool.chmod(0o755)
        login_path(home, fakebin)
        return fakebin

    return make


@pytest.fixture
def fakebin(tools: Callable[..., Path]) -> Path:
    """nextflow, snakemake, java and tmux on the login PATH; no sbatch."""
    return tools("nextflow", "snakemake", "java", "tmux")
