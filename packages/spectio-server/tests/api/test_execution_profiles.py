"""Launch with an execution profile (#408; api §5.13, §5.2; FU-P3-86c's tests, moved): the
snapshot built from a compute and a profile, the deprecated `environment` alias, Resume's rules
and the runner's reading of the payload's snapshot (SEC-P3FU86A-R3-02). The routes are in
test_computes."""

import os
import threading
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from spectio import computes, envfile
from spectio import environments as envs
from spectio.config import Settings, SlurmOpts
from spectio.runner import loop
from spectio.runner.engines import EngineInfo
from spectio.runner.loop import LaunchPayload
from spectio.runner.rundir import read_run_manifest, run_paths
from spectio_server.sink import StoreSink
from spectio_server.store.schema import runner_commands, runs
from spectio_server.store.writer import Writer

from .test_launch import RecordingLauncher
from .test_relaunch import end, resume

API = "/api/v1"
COMPUTES = f"{API}/computes"
PROFILES = f"{API}/execution-profiles"
MYLAB = {"name": "mylab", "label": "My lab", "executor": "local", "local": {"cpus": 4}}


def path() -> Path:
    return Path(os.environ["SPECTIO_CONFIG"]).parent / "execution-profiles.toml"


def hand_write(text: str, mode: int = 0o600) -> None:
    path().write_text(text)
    path().chmod(mode)


def create(client: TestClient, body: dict[str, Any] = MYLAB) -> Any:
    """The compute `body` names, and the profile of the same name that uses it."""
    compute = {k: v for k, v in body.items() if k != "profiles"}
    found = client.post(COMPUTES, json=compute)
    assert found.status_code == 201, found.text
    profile = {"name": body["name"], "label": body.get("label"), "compute": body["name"]}
    profile |= {k: body[k] for k in ("software",) if k in body}
    profile |= {"engine_profiles": body["profiles"]} if "profiles" in body else {}
    made = client.post(PROFILES, json=profile)
    assert made.status_code == 201, made.text
    return found


def problem(response: Any, status: int, slug: str, field: str | None = None) -> None:
    assert response.status_code == status, response.text
    body = response.json()
    assert body["type"] == f"/problems/{slug}", body
    if field is not None:
        assert field in [e["field"] for e in body["errors"]], body


def as_slurm(client: TestClient, settings: Settings, partition: str = "htc") -> Settings:
    """The server becomes one set up with SLURM (`[slurm] partition`), as behind its socket."""
    slurm = settings.model_copy(
        update={"executor": "slurm", "slurm": SlurmOpts(partition=partition)}
    )
    client.app.state.settings = slurm  # type: ignore[attr-defined]
    return slurm


def launch(client: TestClient, synthetic: Path, engine: str = "snakemake", **body: Any) -> Any:
    workflow = {"location": str(synthetic / engine), "engine": engine}
    return client.post(f"{API}/runs", json={"workflow": workflow, "params": {}, **body})


def launched(client: TestClient, synthetic: Path, **body: Any) -> str:
    found = launch(client, synthetic, **body)
    assert found.status_code == 201, found.text
    return str(found.json()["id"])


def column(writer: Writer, rid: str) -> Any:
    query = select(runs.c.environment).where(runs.c.id == rid)
    return writer.submit(lambda c: c.execute(query).scalar_one()).result()


def payload(writer: Writer, rid: str) -> LaunchPayload:
    query = select(runner_commands.c.payload).where(runner_commands.c.run_id == rid)
    return LaunchPayload.model_validate(
        writer.submit(lambda c: c.execute(query).scalar_one()).result()
    )


# --- Launch with an environment (FU-P3-86c) --------------------------------------------------


def test_req18_snapshot_launch_with_environment(
    authed_client: TestClient,
    synthetic: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The values as resolved at launch go into the manifest, the row and the payload; an edit
    after the launch changes none of them, and the runner launches from the payload."""
    create(authed_client)
    rid = launched(authed_client, synthetic, execution_profile="mylab")
    want = {
        "name": "mylab",
        "label": "My lab",
        "executor": "local",
        "slurm": None,
        "local": {"cpus": 4, "mem_mib": None},
        "software": ["conda", "apptainer"],
        "apptainer_args": "",
        "compute": "mylab",
        "execution_profile": "mylab",
    }
    assert column(writer, rid) == {**want, "state": "recorded"}
    assert read_run_manifest(run_paths(settings.runs_root, rid).run_dir).environment == want
    assert payload(writer, rid).environment == envs.Snapshot.model_validate(want)
    tag = {"If-Match": authed_client.get(f"{COMPUTES}/mylab").headers["etag"]}
    authed_client.put(f"{COMPUTES}/mylab", json={**MYLAB, "local": {"cpus": 64}}, headers=tag)
    assert column(writer, rid)["local"]["cpus"] == 4
    assert authed_client.get(f"{API}/runs/{rid}").json()["environment"]["local"]["cpus"] == 4

    monkeypatch.setattr(loop, "check_engine", lambda engine, cmd: EngineInfo(engine, "9.27.1"))
    launcher = RecordingLauncher()
    loop.RunnerLoop(StoreSink(writer, settings.runs_root), launcher, settings).tick()
    (spec,) = launcher.specs
    assert (spec.environment, spec.slurm) == ("mylab", None)
    assert spec.local == envs.LocalValues(cpus=4)
    # The software of the snapshot, and the server's data directory for its prefixes (inbox #161)
    assert (spec.software, spec.apptainer_args) == (["conda", "apptainer"], "")
    assert spec.software_cache == settings.runs_root / ".software-cache"


def test_software_round_trip(authed_client: TestClient, synthetic: Path, writer: Writer) -> None:
    """inbox #161: the software and the Apptainer arguments are part of a compute, the software
    also of a profile: the routes give them back, the files hold them — an empty list and empty
    arguments too — and a launch keeps the profile's in its snapshot and its spec."""
    item = create(
        authed_client,
        {**MYLAB, "software": ["apptainer", "conda"], "apptainer_args": "--bind /g,/scratch"},
    ).json()
    assert (item["software"], item["apptainer_args"]) == (
        ["apptainer", "conda"],
        "--bind /g,/scratch",
    )
    text = path().with_name("computes.toml").read_text()
    assert 'software = ["apptainer", "conda"]' in text
    assert 'apptainer_args = "--bind /g,/scratch"' in text
    changed = {**MYLAB, "software": [], "apptainer_args": ""}
    tag = {"If-Match": item["etag"]}
    put = authed_client.put(f"{COMPUTES}/mylab", json=changed, headers=tag)
    assert put.status_code == 200, put.text
    assert (put.json()["software"], put.json()["apptainer_args"]) == ([], "")
    # the profile asks for what its compute no longer has: refused at launch
    found = launch(authed_client, synthetic, execution_profile="mylab")
    problem(found, 422, "validation-failed", "execution_profile")
    assert "mylab has no apptainer, conda" in found.json()["errors"][0]["message"]
    profile = authed_client.get(f"{PROFILES}/mylab")
    body = {"name": "mylab", "label": "My lab", "compute": "mylab", "software": []}
    put = authed_client.put(
        f"{PROFILES}/mylab", json=body, headers={"If-Match": profile.headers["etag"]}
    )
    assert put.status_code == 200, put.text
    # an empty list and empty arguments survive the file round-trip, not folded into a default
    (read,) = envfile.read_kind(computes.COMPUTES, path().with_name("computes.toml"), []).entries
    assert (read.software, read.apptainer_args) == ([], "")
    rid = launched(authed_client, synthetic, execution_profile="mylab")
    assert column(writer, rid)["software"] == []
    run = authed_client.get(f"{API}/runs/{rid}").json()["environment"]
    assert (run["software"], run["apptainer_args"]) == ([], "")


def test_req18_snapshot_launch_default(
    authed_client: TestClient, synthetic: Path, writer: Writer
) -> None:
    create(authed_client)
    assert column(writer, launched(authed_client, synthetic))["name"] == "local"
    path().write_text(f'default = "mylab"\n{path().read_text()}')  # a migrated `default`
    assert column(writer, launched(authed_client, synthetic))["name"] == "mylab"
    assert authed_client.get(PROFILES).json()["default"] == "mylab"


@pytest.mark.parametrize("name", ["gone", "slurm", "hpc", "../x", "Mylab"])
def test_req18_snapshot_launch_refused(
    authed_client: TestClient, synthetic: Path, settings: Settings, name: str
) -> None:
    """Unknown, `slurm` on a local server, a SLURM one there (not usable), not a name."""
    path().with_name("computes.toml").write_text('[computes.hpc]\nexecutor = "slurm"\n')
    path().with_name("computes.toml").chmod(0o600)
    hand_write('[execution-profiles.hpc]\ncompute = "hpc"\n')
    found = launch(authed_client, synthetic, environment=name)
    problem(found, 422, "validation-failed", "environment")
    if name == "slurm":
        assert "spectio init --local" in found.json()["errors"][0]["message"]
    assert list(settings.runs_root.iterdir()) == []


def test_req18_snapshot_runner_reads_the_payload_not_settings(
    authed_client: TestClient,
    synthetic: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-P3FU86A-R3-02: the runner builds the SLURM values from the payload's snapshot; a
    `[slurm]` changed after the launch changes nothing. A payload whose snapshot fails the
    strict model is a launch error, never a launch."""
    slurm = as_slurm(authed_client, settings)
    rid = launched(authed_client, synthetic)
    bad = launched(authed_client, synthetic)
    query = select(runner_commands.c.id, runner_commands.c.payload).where(
        runner_commands.c.run_id == bad
    )
    cid, sent = writer.submit(lambda c: c.execute(query).one()).result()
    broken = {**sent, "environment": {**sent["environment"], "slurm": {"partition": "htc\n"}}}
    writer.submit(
        lambda c: c.execute(
            update(runner_commands).where(runner_commands.c.id == cid).values(payload=broken)
        )
    ).result()
    later = slurm.model_copy(update={"slurm": SlurmOpts(partition="gpu", account="other")})
    monkeypatch.setattr(loop, "check_engine", lambda engine, cmd: EngineInfo(engine, "9.27.1"))
    launcher = RecordingLauncher()
    loop.RunnerLoop(StoreSink(writer, settings.runs_root), launcher, later).tick()
    (spec,) = launcher.specs
    assert spec.run_id == rid and spec.environment == "slurm"
    assert spec.slurm == envs.SlurmValues(partition="htc")
    failed = writer.submit(
        lambda c: c.execute(select(runs.c.state, runs.c.failure).where(runs.c.id == bad)).one()
    ).result()
    assert failed.failure["class"] == "launch_error"


def test_req18_snapshot_runner_checks_the_server_kind(
    authed_client: TestClient,
    synthetic: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-P3FU86BCD-02: a payload asking for SLURM on a server with no SLURM is a launch
    error, never a launch, even past the routes."""
    rid = launched(authed_client, synthetic)
    query = select(runner_commands.c.id, runner_commands.c.payload).where(
        runner_commands.c.run_id == rid
    )
    cid, sent = writer.submit(lambda c: c.execute(query).one()).result()
    forged = {**sent, "environment": {"name": "forged", "executor": "slurm"}}
    writer.submit(
        lambda c: c.execute(
            update(runner_commands).where(runner_commands.c.id == cid).values(payload=forged)
        )
    ).result()
    monkeypatch.setattr(loop, "check_engine", lambda engine, cmd: EngineInfo(engine, "9.27.1"))
    launcher = RecordingLauncher()
    loop.RunnerLoop(StoreSink(writer, settings.runs_root), launcher, settings).tick()
    assert launcher.specs == []
    failed = writer.submit(
        lambda c: c.execute(select(runs.c.failure).where(runs.c.id == rid)).one()
    ).result()
    assert failed.failure["class"] == "launch_error"


# --- Resume's rules (api §5.4, Resume; SEC-PRE-FU86-R1-03) -----------------------------------


def failed(
    client: TestClient, writer: Writer, settings: Settings, synthetic: Path, **body: Any
) -> str:
    rid = launched(client, synthetic, **body)
    end(writer, settings, rid)
    return rid


def child_payload(response: Any, writer: Writer) -> LaunchPayload:
    assert response.status_code == 201, response.text
    return payload(writer, response.json()["id"])


def test_req18_snapshot_resume_recorded(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    """A recorded snapshot still allowed: unchanged, whatever the file says now."""
    create(authed_client)
    rid = failed(authed_client, writer, settings, synthetic, environment="mylab")
    tag = {"If-Match": authed_client.get(f"{PROFILES}/mylab").headers["etag"]}
    authed_client.delete(f"{PROFILES}/mylab", headers=tag)
    found = child_payload(resume(authed_client, rid), writer)
    assert found.environment is not None and found.environment.local == envs.LocalValues(cpus=4)
    assert found.resume_of is not None
    child = resume(authed_client, rid)  # the first child is queued: refused
    assert child.status_code == 409


def test_req18_snapshot_resume_slurm_on_local_server(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    as_slurm(authed_client, settings)
    rid = failed(authed_client, writer, settings, synthetic)
    authed_client.app.state.settings = settings  # type: ignore[attr-defined]
    found = resume(authed_client, rid)
    problem(found, 422, "validation-failed", "environment")
    assert "this server has no SLURM" in found.json()["errors"][0]["message"]


def test_req18_snapshot_resume_local_gets_caps_on_slurm(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    rid = failed(authed_client, writer, settings, synthetic)  # the local-mode built-in: no caps
    as_slurm(authed_client, settings)
    found = child_payload(resume(authed_client, rid), writer)
    assert found.environment is not None and found.environment.name == "local"
    assert found.environment.local == envs.LocalValues(cpus=2, mem_mib=8192)


def set_column(writer: Writer, rid: str, value: dict[str, Any]) -> None:
    query = update(runs).where(runs.c.id == rid).values(environment=value)
    writer.submit(lambda c: c.execute(query)).result()


def test_req18_snapshot_resume_not_recorded_and_not_readable(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    old = failed(authed_client, writer, settings, synthetic)
    bad = failed(authed_client, writer, settings, synthetic)
    for rid, value in ((old, envs.run_column(None)), (bad, envs.run_column({"name": "x'"}))):
        set_column(writer, rid, value)
    slurm = as_slurm(authed_client, settings)
    found = child_payload(resume(authed_client, old), writer)
    builtin = envs.snapshot(envs.server_builtin(slurm).environment)
    assert found.environment == envs.Snapshot.model_validate(builtin)
    problem(resume(authed_client, bad), 422, "validation-failed", "environment")


def test_req18_snapshot_launch_template_environment(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    """Copy to a new launch preselects the run's environment by name, or the default with a
    notice when it is gone."""
    create(authed_client)
    rid = failed(authed_client, writer, settings, synthetic, environment="mylab")
    template = authed_client.get(f"{API}/runs/{rid}:launch-template").json()
    assert (template["environment"], template["environment_notice"]) == ("mylab", None)
    assert template["execution_profile"] == "mylab"
    tag = {"If-Match": authed_client.get(f"{PROFILES}/mylab").headers["etag"]}
    authed_client.delete(f"{PROFILES}/mylab", headers=tag)
    template = authed_client.get(f"{API}/runs/{rid}:launch-template").json()
    assert template["environment"] == "local"
    assert "mylab" in template["environment_notice"]


def test_req18_snapshot_launch_template_file_unusable(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    """CR-P3FU86BCD-03: a file that cannot be used now does not say the environment is gone."""
    create(authed_client)
    rid = failed(authed_client, writer, settings, synthetic, environment="mylab")
    path().chmod(0o620)  # others may write it: refused
    template = authed_client.get(f"{API}/runs/{rid}:launch-template").json()
    assert template["environment"] == "local"
    assert template["environment_notice"] == (
        "The execution profile mylab of this run cannot be read: the execution profiles file is"
        " refused; local is chosen."
    )


def test_req13_write_lock_waited_for_outside_the_file_pool(
    authed_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-P3FU86BCD-02: a write waits for the one before it in its request thread, never in a
    file-pool worker (dev-env §15.3 req. 13): while the lock is held, the write answers `503`
    without entering the pool, and the lock is free again after the next write."""
    entered: list[str] = []
    update_kind = envfile.update_kind

    def spy(*args: Any, **kwargs: Any) -> Any:
        entered.append(threading.current_thread().name)
        return update_kind(*args, **kwargs)

    monkeypatch.setattr(envfile, "update_kind", spy)
    monkeypatch.setattr(envfile, "LOCK_TIMEOUT_S", 0.2)
    assert envfile.WRITE.acquire(blocking=False)
    try:
        problem(authed_client.post(COMPUTES, json=MYLAB), 503, "runner-offline")
    finally:
        envfile.WRITE.release()
    assert entered == []
    create(authed_client)
    assert entered and entered[0].startswith("spectio-files-")
    assert envfile.WRITE.acquire(blocking=False)
    envfile.WRITE.release()
