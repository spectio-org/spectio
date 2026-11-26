"""Computes and execution profiles as data (#408; api §5.13): the strict models, the pair that
`resolve` turns into the run's snapshot, `split` as its inverse for the built-ins and the
migration, and the rules `check` applies to a profile on its compute."""

from typing import Any

import pytest
from pydantic import ValidationError

from spectio import computes
from spectio import environments as envs
from spectio.config import Settings, SlurmOpts


def environment(**fields: Any) -> envs.Environment:
    return envs.Environment.model_validate({"name": "mylab", **fields})


ENVIRONMENTS = [
    environment(executor="local"),
    environment(executor="local", label="Lab", local={"cpus": 4, "mem_mib": 1024}),
    environment(executor="slurm"),
    environment(
        executor="slurm",
        label="HPC",
        slurm={
            "partition": "gpu",
            "account": "lab-a",
            "time_min": 60,
            "mem_mib": 2048,
            "constraint": "avx512",
            "gres": "gpu:H100:1",
        },
        software=["apptainer"],
        apptainer_args="--bind /g",
        profiles={"nextflow": "slurm", "snakemake": None},
    ),
]


@pytest.mark.parametrize("env", ENVIRONMENTS)
def test_split_then_resolve_is_the_environment_plus_two_names(env: envs.Environment) -> None:
    """The migration's promise: a run launched from the migrated pair has the snapshot the
    environment gave, with the compute and profile names."""
    compute, profile = computes.split(env)
    assert (compute.name, profile.name, profile.compute) == (env.name, env.name, env.name)
    assert computes.check(compute, profile) is None
    resolved = computes.resolve(compute, profile)
    expected = envs.snapshot(env) | {"compute": env.name, "execution_profile": env.name}
    assert resolved.model_dump(mode="json") == expected
    assert profile.engine_profiles == env.profiles


def test_builtins_are_one_pair_per_environment() -> None:
    settings = Settings(executor="local")
    assert [b.compute.name for b in computes.builtins(settings)] == ["local"]
    slurm = settings.model_copy(update={"executor": "slurm", "slurm": SlurmOpts(partition="htc")})
    pairs = computes.builtins(slurm)
    assert [(b.compute.name, b.profile.name) for b in pairs] == [("slurm", "slurm"), ("local",) * 2]
    assert pairs[0].profile.resources.partition == "htc"
    assert pairs[1].compute.local == envs.LocalValues(**envs.LOCAL_CAPS)


def test_models_are_strict() -> None:
    for bad in (
        {"name": "a", "executor": "local", "slurm": {"account": "x"}},
        {"name": "a", "executor": "slurm", "local": {"cpus": 1}},
        {"name": "a", "executor": "local", "software": ["conda", "conda"]},
        {"name": "a", "executor": "local", "apptainer_args": "$(x)"},
        {"name": "a", "executor": "local", "extra": 1},
    ):
        with pytest.raises(ValidationError):
            computes.Compute.model_validate(bad)
    for resources in ({"cpus": "2"}, {"cpus": 0}, {"gres": "a b"}, {"partition": "x\n"}, {"k": 1}):
        with pytest.raises(ValidationError):
            computes.ExecutionProfile.model_validate(
                {"name": "p", "compute": "c", "resources": resources}
            )


def test_check_rules() -> None:
    local = computes.Compute(
        name="c", executor="local", local=envs.LocalValues(cpus=4), software=["conda"]
    )
    slurm = computes.Compute(name="s", executor="slurm")

    def profile(compute: str, **resources: Any) -> computes.ExecutionProfile:
        return computes.ExecutionProfile.model_validate(
            {"name": "p", "compute": compute, "resources": resources, "software": ["conda"]}
        )

    assert computes.check(local, profile("c", cpus=4)) is None
    assert computes.check(local, profile("c", cpus=5)) == ("resources.cpus", "At most 4 CPUs in c")
    for key, value in (("partition", "x"), ("constraint", "x"), ("gres", "g:1"), ("time_min", 5)):
        found = computes.check(local, profile("c", **{key: value}))
        assert found is not None and found[0] == f"resources.{key}"
    assert computes.check(slurm, profile("s", partition="gpu", cpus=64, time_min=5)) is None
    both = computes.ExecutionProfile(name="p", compute="c")  # the default asks for apptainer too
    assert computes.check(local, both) == ("software", "c has no apptainer")
