"""Environments as typed data (FU-P3-86a; api §5.4; dev-env §15.3 req. 18).

One strict model, shared by the routes, the runner and the index rebuild: every field is a name
of a closed character set, matched in full, or an integer in bounds, with strict types (no
`true`, `"5"` or `5.0` for an integer). The built-ins come from `Settings`: `local` always,
`slurm` on a server set up with SLURM.

A run keeps its own snapshot, `{name, label, executor, slurm, local}`, in its manifest and in
`runs.environment` with a `state`; every per-run decision reads that column, never
`settings.executor` or an `environments` row (SEC-PRE-FU86-R1-01).
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError, model_validator

from spectio.config import Settings, SlurmName

PROFILE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}")  # never a path, a comma or an option
NAME = re.compile(r"[a-z][a-z0-9-]{0,31}")
RESERVED = frozenset({"local", "slurm", "new"})  # the built-ins, and the screen route `new`
# Controls, format characters (the bidi overrides among them), separators, unassigned and
# private-use code points: a label is shown as text, and none of these reads as text.
_NOT_TEXT = frozenset({"Cc", "Cf", "Cn", "Co", "Cs", "Zl", "Zp"})
NO_SLURM = "This server was set up with spectio init --local: it has no SLURM"
LOCAL_CAPS = {"cpus": 2, "mem_mib": 8192}  # the built-in `local` on a login node (audit §7)
SnapshotState = Literal["recorded", "not_recorded", "not_readable"]


def _name(value: str) -> str:
    if not NAME.fullmatch(value):
        raise ValueError(f"{value[:40]!r} is not an environment name")
    return value


def _profile(value: str) -> str:
    if not PROFILE.fullmatch(value):
        raise ValueError(f"{value[:70]!r} is not a profile name")
    return value


def _label(value: str) -> str:
    if not 1 <= len(value) <= 80 or any(unicodedata.category(c) in _NOT_TEXT for c in value):
        raise ValueError("a label is 1 to 80 characters, with no control or format character")
    return value


Name = Annotated[str, AfterValidator(_name)]
Label = Annotated[str, AfterValidator(_label)]
ProfileName = Annotated[str, AfterValidator(_profile)]
MemMib = Annotated[int, Field(ge=1, le=4_194_304)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class SlurmValues(_Strict):
    partition: SlurmName | None = None
    account: SlurmName | None = None
    time_min: Annotated[int, Field(ge=1, le=43_200)] | None = None
    mem_mib: MemMib | None = None


class LocalValues(_Strict):
    """The most the tasks may request at once; the user's cgroup stays the only hard cap."""

    cpus: Annotated[int, Field(ge=1, le=256)] | None = None
    mem_mib: MemMib | None = None


class DefaultResources(_Strict):
    """A run's `default_resources` (api §5.7), in the units of §5.4."""

    cpus: Annotated[int, Field(ge=1, le=256)] | None = None
    mem_mib: MemMib | None = None
    time_min: Annotated[int, Field(ge=1, le=43_200)] | None = None


class Profiles(_Strict):
    nextflow: ProfileName | None = None
    snakemake: ProfileName | None = None


class Snapshot(_Strict):
    """What a run ran with: its manifest's `environment`, and `runs.environment` less `state`."""

    name: Name
    label: Label | None = None
    executor: Literal["local", "slurm"]
    slurm: SlurmValues | None = None
    local: LocalValues | None = None

    @model_validator(mode="after")
    def _one_executor(self) -> "Snapshot":
        if self.slurm is not None and self.executor != "slurm":
            raise ValueError("slurm values need executor slurm")
        if self.local is not None and self.executor != "local":
            raise ValueError("local values need executor local")
        return self


class Environment(Snapshot):
    """A definition: a snapshot's fields and the default profile of each engine."""

    profiles: Profiles = Profiles()


@dataclass(frozen=True)
class Builtin:
    environment: Environment
    usable: bool = True
    unusable_reason: str | None = None


def builtins(settings: Settings) -> list[Builtin]:
    """`slurm` (on a server set up with SLURM), then `local`, from `settings`."""
    if settings.executor != "slurm":
        return [Builtin(Environment(name="local", label="This machine", executor="local"))]
    local = Environment(
        name="local", label="Login node", executor="local", local=LocalValues(**LOCAL_CAPS)
    )
    return [_slurm(settings), Builtin(local)]


def _slurm(settings: Settings) -> Builtin:
    """Its `[slurm]` partition and account; a value that is not a SLURM name (UX-PRE-FU86-R1-23)
    makes it unusable."""
    label = "SLURM (from spectio init)"
    try:
        values = SlurmValues(partition=settings.slurm.partition, account=settings.slurm.account)
    except ValidationError as exc:  # only a hand-built Settings: SlurmOpts checks each value
        key = next(str(e["loc"][0]) for e in exc.errors())
        reason = f"{key} in spectio.toml is not a valid name: run spectio init"
        empty = Environment(name="slurm", label=label, executor="slurm", slurm=SlurmValues())
        return Builtin(empty, False, reason)
    return Builtin(Environment(name="slurm", label=label, executor="slurm", slurm=values))


def server_builtin(settings: Settings) -> Builtin:
    """The built-in of the server's own kind: the default environment."""
    return next(b for b in builtins(settings) if b.environment.name == settings.executor)


def snapshot(env: Snapshot) -> dict[str, Any]:
    """The manifest's `environment`: the run's values as resolved, without the profiles."""
    return Snapshot.model_validate(env.model_dump(exclude={"profiles"})).model_dump(mode="json")


_UNKNOWN = dict.fromkeys(("name", "label", "executor", "slurm", "local"))


def run_column(raw: object) -> dict[str, Any]:
    """`runs.environment` from a manifest's `environment` (req. 10): `recorded` when it passes
    the validators, `not_readable` when not, `not_recorded` when there is none."""
    if raw is None:
        return {**_UNKNOWN, "state": "not_recorded"}
    try:
        found = Snapshot.model_validate(raw)
    except ValidationError:
        return {**_UNKNOWN, "state": "not_readable"}
    return {**found.model_dump(mode="json"), "state": "recorded"}


def read_as(column: dict[str, Any] | None, settings: Settings) -> dict[str, Any] | None:
    """The snapshot a run is read with (api §5.4, Resume): its own when `recorded`; the
    built-in of the server's kind when `not_recorded` (a run from before FU-P3-86: today's
    behaviour, CR-P3FU86A-02); None when `not_readable` or for a run started from a terminal."""
    state = None if column is None else column.get("state")
    if column is None or state == "not_readable":
        return None
    if state == "not_recorded":
        return snapshot(server_builtin(settings).environment)
    return column


def executor_of(column: dict[str, Any] | None) -> str | None:
    """The run's executor from its `runs.environment`; None when unknown (a run started from a
    terminal, a manifest without a snapshot or one that fails the validators)."""
    return None if column is None else column.get("executor")


def as_snapshot(column: dict[str, Any]) -> Snapshot:
    """A `runs.environment` column, or a `snapshot()`, as the model, through the validators."""
    return Snapshot.model_validate({k: v for k, v in column.items() if k != "state"})


def launch_fields(env: Snapshot) -> dict[str, Any]:
    """`LaunchSpec`'s `environment`, `slurm` and `local` from a run's snapshot (FU-P3-86c)."""
    slurm = (env.slurm or SlurmValues()) if env.executor == "slurm" else None
    return {"environment": env.name, "slurm": slurm, "local": env.local if slurm is None else None}


class NotAllowed(ValueError):
    """A snapshot that this server's launch rules refuse; the message says why."""


def resume_snapshot(column: dict[str, Any] | None, settings: Settings) -> Snapshot:
    """What a Resume runs with: the launch rules applied again to the parent's `runs.environment`
    (api §5.4, Resume; SEC-PRE-FU86-R1-03). Raises NotAllowed for a `not_readable` parent, or a
    SLURM one on a server with no SLURM. A `local` parent without caps on a SLURM server gets the
    built-in `local` caps; a `not_recorded` one the built-in of the server's kind (`read_as`)."""
    own = read_as(column, settings)
    if own is None:
        raise NotAllowed("This run's environment cannot be read: copy it to a new launch instead")
    env = as_snapshot(own)
    if env.executor == "slurm" and settings.executor != "slurm":
        raise NotAllowed("This run ran on SLURM; this server has no SLURM")
    if env.executor == "local" and settings.executor == "slurm" and not _capped(env.local):
        return env.model_copy(update={"local": LocalValues(**LOCAL_CAPS)})
    return env


def check_on_server(env: Snapshot, settings: Settings) -> None:
    """The runner's own check of a payload's snapshot against its server's kind (defence in
    depth, SEC-P3FU86BCD-02): raises NotAllowed for SLURM on a server with no SLURM, which
    `choose()` and `resume_snapshot()` already refuse. A `local` without caps is not refused:
    a file's environment may have none on a SLURM server (api §5.4)."""
    if env.executor == "slurm" and settings.executor != "slurm":
        raise NotAllowed("This run asks for SLURM; this server has no SLURM")


def _capped(local: LocalValues | None) -> bool:
    return local is not None and (local.cpus is not None or local.mem_mib is not None)
