"""Shared fixtures of the server tests: settings in a private HOME, written to spectio.toml."""

import os
import socket
from pathlib import Path

import pytest

from spectio.config import Settings, write_config


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Local-mode settings with private data, database and runs directories, recorded in the
    `spectio.toml` that `$SPECTIO_CONFIG` names, so that the CLI reads the same."""
    for name in list(os.environ):
        if name.startswith("SPECTIO_"):
            monkeypatch.delenv(name)
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    monkeypatch.setenv("HOME", str(home))
    data_dir = home / ".spectio"
    db_dir = tmp_path / "db"
    runs_root = home / "spectio-runs"
    for path in (data_dir, db_dir, runs_root):
        path.mkdir(mode=0o700)
    monkeypatch.setenv("SPECTIO_CONFIG", str(data_dir / "spectio.toml"))
    found = Settings(
        data_dir=data_dir, db_dir=db_dir, runs_root=runs_root, port=free_port(), executor="local"
    )
    write_config(found)
    return found
