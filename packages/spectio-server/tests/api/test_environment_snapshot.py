"""A run's own environment (FU-P3-86a; api §5.4, "The database is not the source", §7 `runs`;
dev-env §15.3 req. 18): `runs.environment` written at launch and at rebuild, read by every
per-run decision (the failure summary's SLURM reading and `sacct` call, the copied command),
never `settings.executor` or an `environments` row (SEC-PRE-FU86-R1-01)."""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from spectio import environments as envs
from spectio.config import Settings, SlurmOpts
from spectio.runner.observed import ObservedRun
from spectio.runner.rundir import make_run_dirs, read_run_manifest, run_paths
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.files.redact import FORMAT_CHARS
from spectio_server.rebuild import rebuild_index
from spectio_server.store.db import open_db
from spectio_server.store.runs import insert_observed_run
from spectio_server.store.schema import environments, launches, principals, runs
from spectio_server.store.writer import Writer

from ..test_serve import make_run, run_id
from .conftest import add_run, client_for
from .test_failure import Fake, accounting, event, push

API = "/api/v1"
FORMAT_CHARS_LIST = [
    chr(c)
    for a, b in re.findall(r"(.)(?:-(.))?", FORMAT_CHARS.encode().decode("unicode_escape"))
    for c in range(ord(a), ord(b or a) + 1)
]
LOCAL = {
    "name": "local",
    "label": "This machine",
    "executor": "local",
    "slurm": None,
    "local": None,
    "state": "recorded",
}
SLURM = {
    "name": "slurm",
    "label": "SLURM (from spectio init)",
    "executor": "slurm",
    "slurm": {"partition": "htc", "account": None, "time_min": None, "mem_mib": None},
    "local": None,
    "state": "recorded",
}


@pytest.fixture
def fakebin(tmp_path: Path) -> Fake:
    return Fake(tmp_path)


def launch(client: TestClient, synthetic: Path, engine: str = "snakemake") -> str:
    workflow = {"location": str(synthetic / engine), "engine": engine}
    found = client.post(f"{API}/runs", json={"workflow": workflow, "params": {}})
    assert found.status_code == 201, found.text
    return str(found.json()["id"])


def column(writer: Writer, rid: str) -> Any:
    query = select(runs.c.environment).where(runs.c.id == rid)
    return writer.submit(lambda c: c.execute(query).scalar_one()).result()


def test_req18_snapshot_written_at_launch(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    """The built-in of the server's kind until FU-P3-86c: in the manifest and on the row, and
    on `GET /runs/{id}` and `GET /runs`."""
    rid = launch(authed_client, synthetic)
    assert column(writer, rid) == LOCAL
    manifest = read_run_manifest(run_paths(settings.runs_root, rid).run_dir)
    assert manifest.environment == {k: v for k, v in LOCAL.items() if k != "state"}
    assert authed_client.get(f"{API}/runs/{rid}").json()["environment"] == LOCAL
    (item,) = authed_client.get(f"{API}/runs").json()["items"]
    assert item["environment"] == LOCAL


def test_req18_snapshot_rebuilt_from_the_manifest(settings: Settings, writer: Writer) -> None:
    """Read with the routes' validators (req. 10): `recorded`, `not_recorded` without one,
    `not_readable` when it fails them; the run is still added."""
    good = {k: v for k, v in SLURM.items() if k != "state"}
    bad = {**good, "slurm": {"partition": "htc'; x"}}
    make_run(settings.runs_root, run_id(1), environment=good)
    make_run(settings.runs_root, run_id(2))
    make_run(settings.runs_root, run_id(3), environment=bad)
    assert rebuild_index(writer, settings.runs_root).added == 3
    assert column(writer, run_id(1)) == SLURM
    assert column(writer, run_id(2)) == envs.run_column(None)
    assert column(writer, run_id(2))["state"] == "not_recorded"
    assert column(writer, run_id(3))["state"] == "not_readable"


def jobs(client: TestClient, writer: Writer, settings: Settings, rid: str, native: str) -> None:
    """One Snakemake job of `rid` ended, with SLURM ID `native`, its launch directory made."""
    query = select(launches.c.id).where(launches.c.run_id == rid)
    launch_id = writer.submit(lambda c: c.execute(query).scalar_one()).result()
    paths = make_run_dirs(settings.runs_root, rid)
    (paths.run_dir / ".spectio").mkdir(mode=0o700, exist_ok=True)
    found = [
        event(1, "snakemake.job_info", rid, jobid=1, rule_name="align", threads=1, resources={}),
        event(2, "snakemake.slurm_submitted", rid, jobid=1, external_jobid=native),
        event(3, "snakemake.job_finished", rid, job_id=1),
    ]
    push(writer, settings, launch_id, *found)


def test_req18_snapshot_local_to_slurm_rename(
    authed_client: TestClient,
    synthetic: Path,
    settings: Settings,
    writer: Writer,
    fakebin: Fake,
) -> None:
    """SEC-PRE-FU86-R1-01: the server's environment becomes SLURM between two runs (its row
    and its settings). The first run keeps the "local" reason, no `sacct` call and a local copy
    command; the second is read as SLURM."""
    first = launch(authed_client, synthetic)
    app = authed_client.app
    slurm = settings.model_copy(update={"executor": "slurm", "slurm": SlurmOpts(partition="htc")})
    app.state.settings = slurm  # type: ignore[attr-defined]
    acct = app.state.accounting = accounting(slurm, fakebin)  # type: ignore[attr-defined]
    config = {"runs_root": str(settings.runs_root)}
    writer.submit(lambda c: ensure_tenancy(c, "me", "slurm", config, "0.0.1")).result()
    writer.submit(lambda c: c.execute(update(environments).values(kind="slurm"))).result()
    second = launch(authed_client, synthetic)
    assert column(writer, first) == LOCAL and column(writer, second) == SLURM
    jobs(authed_client, writer, settings, first, "8812401")
    jobs(authed_client, writer, settings, second, "8812402")
    fakebin.at("8812402", run_paths(settings.runs_root, second).launch_dir)

    def items(rid: str) -> list[dict[str, Any]]:
        found = authed_client.get(f"{API}/runs/{rid}/tasks")
        assert found.status_code == 200, found.text
        return found.json()["items"]  # type: ignore[no-any-return]

    (one,) = items(first)
    assert one["efficiency"]["reason"] == "local" and one["slurm"] is None
    (two,) = items(second)
    assert two["efficiency"]["reason"] is None
    while acct.step():
        pass
    assert fakebin.ids() == ["8812402"]  # never the first run's job
    argv = authed_client.get(f"{API}/runs/{first}").json()["command"]["argv"]
    assert "--executor" not in argv and "--local-cores" not in argv
    argv = authed_client.get(f"{API}/runs/{second}").json()["command"]["argv"]
    assert argv[argv.index("--executor") + 1] == "slurm"
    assert argv[argv.index("--default-resources") + 1] == "slurm_partition='htc'"
    assert "--local-cores" in argv


def test_req18_snapshot_unknown_executor_is_not_slurm(
    settings: Settings, writer: Writer, fakebin: Fake
) -> None:
    """A run with no recorded executor (a manifest from before FU-P3-86) never asks `sacct`,
    whatever the server's kind is."""
    rid = run_id(1)
    add_run(writer, settings, rid, "old", engine="snakemake")  # its manifest has no snapshot
    assert column(writer, rid)["state"] == "not_recorded"
    writer.submit(lambda c: c.execute(update(environments).values(kind="slurm"))).result()
    client = client_for(settings, writer)
    client.app.state.accounting = accounting(settings, fakebin)  # type: ignore[attr-defined]
    jobs(client, writer, settings, rid, "8812401")
    found = client.get(f"{API}/runs/{rid}/tasks").json()["items"]
    assert found[0]["efficiency"]["reason"] == "local" and fakebin.ids() == []


def test_req18_snapshot_ensure_tenancy_by_name(settings: Settings, writer: Writer) -> None:
    """The built-in's row is found by its name, never "the oldest row": a re-init to SLURM adds
    the `slurm` row and leaves the `local` one as it was; one principal still."""
    rows = select(environments.c.name, environments.c.kind, environments.c.config)
    config = {"runs_root": "/elsewhere"}
    writer.submit(lambda c: ensure_tenancy(c, "me", "slurm", config, "0.0.1")).result()
    writer.submit(lambda c: ensure_tenancy(c, "me", "slurm", config, "0.0.1")).result()
    found = writer.submit(lambda c: sorted(c.execute(rows).all())).result()
    local = {"runs_root": str(settings.runs_root)}
    assert [tuple(r) for r in found] == [("local", "local", local), ("slurm", "slurm", config)]
    count = writer.submit(lambda c: len(c.execute(select(principals.c.id)).all())).result()
    assert count == 1


def test_req18_snapshot_migration_backfills(settings: Settings) -> None:
    """A database at 0010 gains `runs.environment` and `environments.name`: the runs it held
    are `not_recorded`, with the executor of the one environment they ran on."""
    assert settings.db_dir is not None
    engine, _ = open_db(settings.db_dir)
    alembic = Config()
    alembic.set_main_option("script_location", "spectio_server:migrations")
    with engine.begin() as conn:
        ensure_tenancy(conn, "me", "slurm", {}, "0.0.1")
        alembic.attributes["connection"] = conn
        command.downgrade(alembic, "0010")
    with engine.begin() as conn:  # a run of the old schema, as a 0010 server wrote it
        values = conn.execute(select(environments.c.id, environments.c.owning_group_id)).one()
        conn.exec_driver_sql(
            "INSERT INTO workflows (id, created_at, project_id, location, source, engine) "
            "SELECT 'wfl_1', CURRENT_TIMESTAMP, id, '/p', 'local', 'nextflow' FROM projects"
        )
        conn.exec_driver_sql(
            "INSERT INTO workflow_versions (id, created_at, workflow_id) "
            "VALUES ('wfv_1', CURRENT_TIMESTAMP, 'wfl_1')"
        )
        conn.exec_driver_sql(
            "INSERT INTO runs (id, created_at, project_id, workflow_version_id, environment_id, "
            "state, origin) SELECT 'run_old', CURRENT_TIMESTAMP, id, 'wfv_1', ?, 'failed', 'ui' "
            "FROM projects",
            (values.id,),
        )
    engine.dispose()
    engine, new = open_db(settings.db_dir)
    try:
        assert not new
        with engine.connect() as conn:
            (environment,) = conn.execute(select(runs.c.environment)).scalars()
            assert environment == {**envs.run_column(None), "executor": "slurm"}
            assert conn.execute(select(environments.c.name)).scalar_one() == "slurm"
    finally:
        engine.dispose()


def test_req18_snapshot_observed_run_has_none(authed_client: TestClient, writer: Writer) -> None:
    """A run started from a terminal has `environment: null` (UX-PRE-FU86-R1-05)."""
    run = ObservedRun(
        run_id=run_id(7),
        launch_dir="/somewhere",
        engine="nextflow",
        engine_version="26.10.4",
        bridge_version="0.0.1",
        host="login1",
        pid=4242,
        pid_start_time="1",
        boot_id="0" * 36,
    )
    writer.submit(lambda c: insert_observed_run(c, run, datetime.now(UTC))).result()
    assert column(writer, run_id(7)) is None
    assert authed_client.get(f"{API}/runs/{run_id(7)}").json()["environment"] is None


@pytest.mark.parametrize("char", ["\x00", "\x9b", "\u00ad", "\ue000", *FORMAT_CHARS_LIST])
def test_req18_snapshot_label_refuses_format_chars(char: str) -> None:
    """No control or format character in a label: the FORMAT_CHARS of the Job files read
    included."""
    with pytest.raises(ValueError):
        envs.Environment.model_validate({"name": "x", "executor": "local", "label": f"a{char}"})
