"""Computes and execution profiles (#408; api §5.13): an environment (§5.4) split in two.

A **compute** is a backend: the executor, the SLURM account or the local caps, the software
methods on it and the Apptainer arguments. An **execution profile** is what one run asks of one
compute: partition, constraint, GRES, time, memory, CPUs, the software it deploys with and the
default engine profiles. Both are strict models that reuse the validators of
`spectio.environments`, and live in `computes.toml` and `execution-profiles.toml` next to
`spectio.toml` (`spectio.envfile`).

A run still keeps today's snapshot (`environments.Snapshot`): `resolve` builds it from one
compute and one profile, so the head script and every reader of `runs.environment` are unchanged.
`split` is the other way, for the built-ins and for the migration of `environments.toml`.
"""

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spectio import envfile
from spectio import environments as envs
from spectio.config import Settings, SlurmName
from spectio.environments import (
    ApptainerArgs,
    Constraint,
    Gres,
    Label,
    LocalValues,
    MemMib,
    Name,
    Profiles,
    SlurmValues,
    Snapshot,
    Software,
)

COMPUTES_FILE = "computes.toml"
PROFILES_FILE = "execution-profiles.toml"
MAX_COMPUTES = 32
MAX_PROFILES = 64
SLURM_ONLY = ("partition", "constraint", "gres", "time_min")  # no meaning on a local compute


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ComputeSlurm(_Strict):
    account: SlurmName | None = None


class Compute(_Strict):
    name: Name
    label: Label | None = None
    executor: Literal["local", "slurm"]
    slurm: ComputeSlurm | None = None
    local: LocalValues | None = None
    software: Software = ["conda", "apptainer"]
    apptainer_args: ApptainerArgs = ""

    @model_validator(mode="after")
    def _one_executor(self) -> "Compute":
        if self.slurm is not None and self.executor != "slurm":
            raise ValueError("slurm values need executor slurm")
        if self.local is not None and self.executor != "local":
            raise ValueError("local values need executor local")
        return self


class Resources(_Strict):
    """What a run asks for; null is the engine's or SLURM's default."""

    partition: SlurmName | None = None
    constraint: Constraint | None = None
    gres: Gres | None = None
    time_min: Annotated[int, Field(ge=1, le=43_200)] | None = None
    mem_mib: MemMib | None = None
    cpus: Annotated[int, Field(ge=1, le=256)] | None = None


class ExecutionProfile(_Strict):
    name: Name
    label: Label | None = None
    compute: Name
    resources: Resources = Resources()
    software: Software = ["conda", "apptainer"]  # a subset of the compute's
    engine_profiles: Profiles = Profiles()


# the built-ins' names are reserved, as for environments; only the profiles file has a `default`
COMPUTES = envfile.Kind(COMPUTES_FILE, "computes", Compute, MAX_COMPUTES, envs.RESERVED, False)
PROFILES = envfile.Kind(
    PROFILES_FILE, "execution-profiles", ExecutionProfile, MAX_PROFILES, envs.RESERVED, True
)


def check(compute: Compute, profile: ExecutionProfile) -> tuple[str, str] | None:
    """The first rule the pair breaks, as (field of the profile, message); None when it holds."""
    missing = [s for s in profile.software if s not in compute.software]
    if missing:
        return "software", f"{compute.name} has no {', '.join(missing)}"
    if compute.executor == "slurm":
        return None
    for key in SLURM_ONLY:
        if getattr(profile.resources, key) is not None:
            return f"resources.{key}", f"{key} applies to a SLURM compute: {compute.name} is local"
    caps = compute.local
    if caps is not None:
        cpus, mem = profile.resources.cpus, profile.resources.mem_mib
        if caps.cpus is not None and (cpus or 0) > caps.cpus:
            return "resources.cpus", f"At most {caps.cpus} CPUs in {compute.name}"
        if caps.mem_mib is not None and (mem or 0) > caps.mem_mib:
            return "resources.mem_mib", f"At most {caps.mem_mib} MiB in {compute.name}"
    return None


def resolve(compute: Compute, profile: ExecutionProfile) -> Snapshot:
    """The run's snapshot (§5.4's shape) from a compute and a profile that `check` accepts. On
    SLURM, `resources.cpus` has no place in it: a launch applies it (`runs_write`). On a local
    compute the profile's CPUs and memory replace the compute's caps."""
    r = profile.resources
    slurm = local = None
    if compute.executor == "slurm":
        account = None if compute.slurm is None else compute.slurm.account
        values = SlurmValues(
            partition=r.partition,
            account=account,
            time_min=r.time_min,
            mem_mib=r.mem_mib,
            constraint=r.constraint,
            gres=r.gres,
        )
        slurm = values if values != SlurmValues() else None
    else:
        caps = compute.local or LocalValues()
        capped = LocalValues(
            cpus=caps.cpus if r.cpus is None else r.cpus,
            mem_mib=caps.mem_mib if r.mem_mib is None else r.mem_mib,
        )
        local = capped if capped != LocalValues() else None
    return Snapshot(
        name=profile.name,
        label=profile.label or compute.label,
        executor=compute.executor,
        slurm=slurm,
        local=local,
        software=list(profile.software),
        apptainer_args=compute.apptainer_args,
        compute=compute.name,
        execution_profile=profile.name,
    )


def split(env: envs.Environment) -> tuple[Compute, ExecutionProfile]:
    """The compute and the profile, both named as `env`, that `resolve` turns back into it."""
    values = env.slurm or SlurmValues()
    compute = Compute(
        name=env.name,
        label=env.label,
        executor=env.executor,
        slurm=ComputeSlurm(account=values.account) if values.account else None,
        local=env.local,
        software=env.software,
        apptainer_args=env.apptainer_args,
    )
    resources = Resources(
        partition=values.partition,
        constraint=values.constraint,
        gres=values.gres,
        time_min=values.time_min,
        mem_mib=values.mem_mib,
    )
    profile = ExecutionProfile(
        name=env.name,
        label=env.label,
        compute=env.name,
        resources=resources,
        software=env.software,
        engine_profiles=env.profiles,
    )
    return compute, profile


@dataclass(frozen=True)
class Builtin:
    compute: Compute
    profile: ExecutionProfile
    usable: bool = True
    unusable_reason: str | None = None


def builtins(settings: Settings) -> list[Builtin]:
    """One compute and one profile of the same name per built-in environment: `slurm` (on a
    server set up with SLURM), then `local`."""
    return [
        Builtin(*split(b.environment), b.usable, b.unusable_reason) for b in envs.builtins(settings)
    ]
