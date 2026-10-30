"""`spectio init` (P1 Task 8): the data directory, `spectio.toml` and the rows of P1
Assumption 18. Every option has a default, so that `spectio open` can run it unattended."""

import getpass
import os
import shlex
import socket
import stat
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

import typer

from spectio.config import DEFAULT_PORT, EngineOpts, Settings, config_path, write_config
from spectio.loginshell import which


class InitError(Exception):
    """A refusal; the message says why and what to do."""


def _private_dir(path: Path) -> None:
    """Create `path` with mode 0700, or accept an existing directory of this user that others
    cannot write; never tightened."""
    try:
        os.mkdir(path, 0o700)
        return
    except FileExistsError:
        pass
    except FileNotFoundError as exc:
        raise InitError(f"{path}: its parent directory does not exist") from exc
    st = os.stat(path)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o022:
        raise InitError(
            f"{path} must be a directory of yours that others cannot write (chmod go-w)"
        )


def _runs_root(settings: Settings) -> Path:
    """The runs root: created when it is the default; a chosen one must exist already. Either
    way, the user's own and not writable by others (dev-env §15.3 req. 10)."""
    path = settings.runs_root
    if "runs_root" in settings.model_fields_set and not path.is_dir():
        raise InitError(f"runs root {path} does not exist: create it on the shared file system")
    _private_dir(path)
    return path


def _free_port(preferred: int) -> int:
    """`preferred` if it is free on 127.0.0.1, else a port the system picks (P1 Assumption 10)."""
    for port in (preferred, 0):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return int(sock.getsockname()[1])
    raise InitError("no free port on 127.0.0.1")  # pragma: no cover - port 0 always binds


def _engines(settings: Settings) -> dict[str, Any]:
    """The engine commands: as recorded or given, else the engine on the login shell's PATH."""
    engines = settings.engines.model_dump()
    missing = [n for n in ("nextflow", "snakemake") if not engines[f"{n}_cmd"]]
    for name, path in which(*missing).items():
        if path:
            engines[f"{name}_cmd"] = shlex.quote(path)
        else:
            typer.echo(
                f"warning: {name} not found on the login shell's PATH: give it with --{name}"
            )
    return engines


def run_init(local: bool, **flags: Any) -> int:
    """`flags`: data_dir, db_dir, runs_root, port, partition, account, nextflow, snakemake;
    None means not given."""
    if local and sys.platform != "linux":  # inbox #73 (a)
        typer.echo("Local mode needs Linux in 0.0.1", err=True)
        return 2
    given: dict[str, Any] = {k: v for k, v in flags.items() if v is not None}
    slurm = {k: given.pop(k) for k in ("partition", "account") if k in given}
    engines = {f"{k}_cmd": given.pop(k) for k in ("nextflow", "snakemake") if k in given}
    if local:
        given["executor"] = "local"
    if slurm:
        given["slurm"] = slurm
    if engines:
        given["engines"] = engines
    try:
        settings = Settings(**given)
        if settings.executor == "local" and slurm:
            raise InitError("--partition and --account need a SLURM environment, not --local")
        _init(settings)
    except (ValueError, InitError, OSError) as exc:  # ValueError: a bad flag or spectio.toml
        typer.echo(f"spectio init: {exc}", err=True)
        return 2
    return 0


def _init(settings: Settings) -> None:
    try:
        import spectio_server.bootstrap as server  # the one import of the server (architecture §6)
    except ImportError as exc:
        raise InitError("the server package is missing: install spectio[server]") from exc
    runs_root = _runs_root(settings)
    for path in (config_path().parent, settings.data_dir):
        _private_dir(path)
    try:
        db_dir = settings.db_dir or server.default_db_dir()
        if settings.db_dir:
            _private_dir(db_dir)
        settings = settings.model_copy(
            update={
                "db_dir": db_dir,
                "port": settings.port
                if "port" in settings.model_fields_set
                else _free_port(DEFAULT_PORT),
                "host": socket.gethostname(),
                "engines": EngineOpts.model_validate(_engines(settings)),
            }
        )
        server.init_store(
            db_dir,
            user=getpass.getuser(),
            kind=settings.executor,
            config={"runs_root": str(runs_root)},
            version=version("spectio"),
        )
    except server.UnsafeDatabase as exc:
        raise InitError(str(exc)) from exc
    path = write_config(settings)
    typer.echo(f"Wrote {path}; database in {db_dir}; runs under {runs_root}; port {settings.port}")
