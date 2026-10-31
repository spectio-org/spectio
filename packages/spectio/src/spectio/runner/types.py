"""What the runner hands to the server; the runner never imports the server (architecture §6)."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from spectio.config import SlurmOpts
from spectio_sdk.events import SpoolEvent


@dataclass(frozen=True)
class SpoolBatch:
    """One read of a launch's spool; the caller stores all three in one transaction.

    `cursor` maps a spool file name to the bytes read from it, or to `REFUSED` for a file that
    is never read again and whose drop is counted. Keys that start with "#" are the reader's own:
    the hash of a name outside the grammar (`REFUSED`), and `EXCESS`. `drops` counts what this
    read dropped, by reason (api §14.1).
    """

    events: list[SpoolEvent]
    cursor: dict[str, int]
    drops: Counter[str]


REFUSED = -1  # a cursor offset: the file is never read, and its drop is counted
EXCESS = "#excess"  # a cursor key: the most names found with no slot, already counted


@dataclass(frozen=True)
class Failure:
    """Why a run failed: `runs.failure` (api §7). `class_` is a `failure_class` (api §7)."""

    class_: str
    message: str
    task_id: str | None = None


# The launcher's states of a head; never the engine's `succeeded` / `failed` (CR-P3T04-01).
HeadState = Literal["starting", "running", "exited", "unknown"]


@dataclass(frozen=True)
class HeadReport:
    """What the runner saw of a launch's head process (schedulers §3.1.1, P1 Assumption 15).

    `state` is the head's own state as the launcher sees it (`running` while it lives);
    `ended` is true once it has exited. `failure` is set when the launch could not start, or the
    head ended with no terminal engine event: the runner decides the class (`launch_error`,
    `engine_missing`, `engine_version`, `head_lost`, `engine_fault`). A Snakemake head never
    writes a terminal engine event: for a Snakemake launch the runner reports the exit code and
    leaves `failure` None, and sets it (`head_lost`) only when the exit code is unknown. The
    projector lets a known exit code win over `head_lost` / `engine_fault` (CR-P3T05-01).
    """

    state: HeadState
    native_id: str | None
    node: str | None
    exit_code: int | None
    ended: bool
    failure: Failure | None


Engine = Literal["nextflow", "snakemake"]


@dataclass(frozen=True)
class LaunchSpec:
    """One launch of a run, as the head script runs it (P1 Task 9, Assumption 13).

    `engine_cmd` is a shell command from `spectio.toml` (the user's own); every other value is
    quoted or written to a file, never read as shell words. `slurm` is None on the local
    executor. `env` holds extra variables for the engine, set after the login profile.
    """

    run_id: str
    launch_n: int
    engine: Engine
    engine_cmd: str
    location: Path
    launch_dir: Path
    work_dir: Path
    profiles: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    slurm: SlurmOpts | None = None
    env: dict[str, str] = field(default_factory=dict)
    nxf_opts: str | None = None
    extra_args: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LaunchRef:
    """A launch the runner watches: a `launches` row (api §7). `native_id` is the head's id as
    the launcher gave it, None until the head is started."""

    launch_id: str
    run_id: str
    launch_n: int
    engine: Engine
    launch_dir: Path
    native_id: str | None = None


@dataclass(frozen=True)
class Command:
    """A leased `runner_commands` row (api §7): `launch` or `cancel` in 0.0.1. A `launch`
    payload is `{location, profiles, params}`; the engine is the launch's."""

    id: str
    kind: str
    launch: LaunchRef
    payload: dict[str, Any] = field(default_factory=dict)


class RunnerSink(Protocol):
    """What the runner loop reads and writes; the server implements it through its `Writer`,
    so that the runner never imports the server (architecture §6)."""

    def lease_commands(self) -> list[Command]: ...
    def ack(self, command_id: str, ok: bool, detail: str | None) -> None: ...
    def active_launches(self) -> list[LaunchRef]: ...
    def cursor(self, launch_id: str) -> dict[str, int]: ...
    def ingest(self, launch_id: str, batch: SpoolBatch) -> None: ...
    def head_report(self, launch_id: str, report: HeadReport) -> None: ...


class Launcher(Protocol):
    """Starts and watches heads (schedulers §3.1.1): `LocalLauncher` here, tmux in Task 10."""

    def submit(self, spec: LaunchSpec) -> str: ...
    def poll(self, ids: list[str]) -> dict[str, HeadReport]: ...
    def cancel(self, native_id: str, grace_s: int = 60) -> None: ...
    def adopt(self, launch: LaunchRef) -> HeadReport: ...
    def forget(self, ids: Iterable[str]) -> None:
        """Drop what is held for these heads: their launches are no longer active."""
        ...
