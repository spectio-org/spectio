"""The run's own environment, as data (FU-P3-86a; api §5.4; dev-env §15.3 req. 18): the strict
model shared by the routes, the runner and the rebuild, the built-ins from `Settings`, the
`[slurm]` names of `spectio.toml`, and the Snakemake values the head script builds from them."""

from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import ValidationError

from spectio import environments as envs
from spectio.config import Settings, SlurmOpts
from spectio.runner.headscript import engine_args
from spectio.runner.types import LaunchSpec

RUN_ID = "run_01K8T9HEAD0000000000000T09"


def slurm_env(**slurm: Any) -> dict[str, Any]:
    return {"name": "mylab", "label": "My lab", "executor": "slurm", "slurm": slurm}


def test_req18_snapshot_model_accepts_typed_values() -> None:
    env = envs.Environment.model_validate(
        {
            **slurm_env(partition="htc", account="my.lab_1", time_min=43200, mem_mib=4194304),
            "profiles": {"nextflow": "slurm", "snakemake": None},
        }
    )
    assert env.slurm is not None and env.slurm.partition == "htc"
    local = envs.Environment.model_validate(
        {"name": "small", "executor": "local", "local": {"cpus": 256, "mem_mib": 1}}
    )
    assert local.local is not None and local.local.cpus == 256


@pytest.mark.parametrize(
    "slurm",
    [
        {"partition": "htc\n"},  # `$` would accept the final newline: fullmatch does not
        {"partition": "-htc"},
        {"partition": "htc,gpu"},  # no list in 0.0.1
        {"partition": "h'tc"},
        {"account": "$HOME"},
        {"account": "~lab"},
        {"account": "a" * 65},
        {"partition": 5},
        {"time_min": True},
        {"time_min": "5"},
        {"time_min": 5.0},
        {"time_min": 0},
        {"time_min": 43201},
        {"mem_mib": 4194305},
        {"qos": "normal"},  # nothing else (req. 18)
    ],
)
def test_req18_snapshot_model_refuses(slurm: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        envs.Environment.model_validate(slurm_env(**slurm))


@pytest.mark.parametrize(
    "fields",
    [
        {"name": "../spectio"},
        {"name": "My-lab"},
        {"name": "a" * 33},
        {"name": "lab\n"},
        {"label": ""},
        {"label": "a" * 81},
        {"label": "lab\x1b[31m"},
        {"label": "lab‮"},  # a bidi override (FORMAT_CHARS)
        {"executor": "k8s"},
        {"local": {"cpus": 2}},  # `local` with executor slurm
        {"profiles": {"nextflow": "a,b"}},
        {"profiles": {"cwl": "x"}},
        {"extra": 1},
    ],
)
def test_req18_snapshot_model_refuses_fields(fields: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        envs.Environment.model_validate({**slurm_env(partition="htc"), **fields})


@pytest.mark.parametrize("cpus", [0, 257, True, "2"])
def test_req18_snapshot_local_caps_bounds(cpus: object) -> None:
    with pytest.raises(ValidationError):
        envs.Environment.model_validate({"name": "x", "executor": "local", "local": {"cpus": cpus}})


def test_req18_snapshot_reserved_names() -> None:
    assert {"local", "slurm", "new"} == envs.RESERVED
    for name in envs.RESERVED:  # a valid name, refused for a definition by the routes (-86d)
        assert envs.NAME.fullmatch(name)


def settings_of(executor: Literal["slurm", "local"], **slurm: Any) -> Settings:
    return Settings.model_construct(executor=executor, slurm=SlurmOpts.model_construct(**slurm))


def test_req18_snapshot_builtins_on_a_slurm_server() -> None:
    found = {b.environment.name: b for b in envs.builtins(settings_of("slurm", partition="htc"))}
    assert list(found) == ["slurm", "local"]
    slurm, local = found["slurm"].environment, found["local"].environment
    assert slurm.label == "SLURM (from spectio init)" and found["slurm"].usable
    assert slurm.slurm == envs.SlurmValues(partition="htc")
    assert local.label == "Login node"  # its tasks run on the login node: capped
    assert local.local == envs.LocalValues(cpus=2, mem_mib=8192)
    assert envs.server_builtin(settings_of("slurm")).environment.name == "slurm"


def test_req18_snapshot_builtins_in_local_mode() -> None:
    (local,) = envs.builtins(settings_of("local"))
    assert local.environment.label == "This machine" and local.environment.local is None
    assert envs.server_builtin(settings_of("local")) == local


def test_req18_snapshot_builtin_slurm_unusable_on_a_bad_name() -> None:
    """A `[slurm]` value that does not match, as only a hand-built Settings can hold now that
    SlurmOpts checks it (UX-PRE-FU86-R1-23)."""
    found = envs.builtins(settings_of("slurm", partition="htc;rm", account="lab"))[0]
    assert (found.environment.name, found.usable) == ("slurm", False)
    assert (
        found.unusable_reason == "partition in spectio.toml is not a valid name: run spectio init"
    )


@pytest.mark.parametrize("value", ["htc\n", "h'tc", "$X", "a,b", "~x", "-p"])
def test_req18_snapshot_slurmopts_pattern(value: str) -> None:
    """SEC-PRE-FU86-01: `[slurm]` partition and account get the SLURM name pattern."""
    for key in ("partition", "account"):
        with pytest.raises(ValidationError):
            SlurmOpts.model_validate({key: value})
    assert SlurmOpts(partition="htc", account="my.lab-1").partition == "htc"


def test_req18_snapshot_column_states() -> None:
    env = envs.Environment.model_validate(slurm_env(partition="htc"))
    recorded = envs.run_column(envs.snapshot(env))
    assert recorded == {
        "name": "mylab",
        "label": "My lab",
        "executor": "slurm",
        "slurm": {"partition": "htc", "account": None, "time_min": None, "mem_mib": None},
        "local": None,
        "state": "recorded",
    }
    assert envs.run_column(None)["state"] == "not_recorded"
    assert envs.run_column(None)["executor"] is None
    for bad in ({**envs.snapshot(env), "slurm": {"partition": "htc\n"}}, {"name": "x"}, [1]):
        assert envs.run_column(bad) == {**envs.run_column(None), "state": "not_readable"}
    assert envs.executor_of(recorded) == "slurm"
    assert envs.executor_of(None) is None
    assert "profiles" not in envs.snapshot(env)  # a snapshot keeps what the run ran with


def test_req18_snapshot_read_as() -> None:
    """api §5.4, Resume: `recorded` is the run's own; `not_recorded` (a run from before
    FU-P3-86) the built-in of the server's kind, today's behaviour; `not_readable` and a run
    started from a terminal, nothing (CR-P3FU86A-02)."""
    own = envs.run_column(envs.snapshot(envs.Environment.model_validate(slurm_env())))
    slurm, local = settings_of("slurm", partition="htc"), settings_of("local")
    assert envs.read_as(own, local) == own
    old = envs.run_column(None)
    assert envs.read_as(old, slurm) == envs.snapshot(envs.server_builtin(slurm).environment)
    assert envs.executor_of(envs.read_as(old, slurm)) == "slurm"
    assert envs.executor_of(envs.read_as(old, local)) == "local"
    assert envs.read_as(envs.run_column([1]), slurm) is None
    assert envs.read_as(None, slurm) is None


def smk_spec(tmp_path: Path, **kw: Any) -> LaunchSpec:
    location = tmp_path / "pipeline"
    (location / "workflow").mkdir(parents=True, exist_ok=True)
    (location / "workflow" / "Snakefile").write_text("")
    return LaunchSpec(
        run_id=RUN_ID,
        launch_n=1,
        engine="snakemake",
        engine_cmd="snakemake",
        location=location,
        launch_dir=tmp_path / "launch",
        work_dir=tmp_path / "work",
        **kw,
    )


def test_req18_snapshot_snakemake_resources_are_string_literals(tmp_path: Path) -> None:
    """SEC-PRE-FU86-01: Snakemake evaluates each `--default-resources` value as Python, so
    partition and account go as string literals."""
    spec = smk_spec(tmp_path, slurm=envs.SlurmValues(partition="htc", account="my.lab"))
    args = engine_args(spec)
    at = args.index("--default-resources")
    assert args[at + 1 : at + 3] == ["slurm_partition='htc'", "slurm_account='my.lab'"]
    bad = envs.SlurmValues.model_construct(partition="htc'+__import__('os')+'", account=None)
    with pytest.raises(ValueError, match="not a SLURM name"):  # checked again where it is used
        engine_args(smk_spec(tmp_path, slurm=bad))


@pytest.mark.parametrize("profiles", [[], ["slurm"]])
def test_req18_snapshot_local_cores_on_every_slurm_launch(
    tmp_path: Path, profiles: list[str]
) -> None:
    """SEC-PRE-FU86-R1-02: local rules otherwise use every core of the login node."""
    args = engine_args(smk_spec(tmp_path, slurm=envs.SlurmValues(), profiles=profiles))
    assert args[args.index("--local-cores") + 1] == "2"
    assert "--local-cores" not in engine_args(smk_spec(tmp_path))
