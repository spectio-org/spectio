"""Runs that target one module or one rule (api-and-data-model.md §5.10, #161): the launch, the
inspection for the Launch form, the store and the rebuild."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from spectio.config import FeatureOpts, Settings
from spectio.runner.loop import LaunchPayload
from spectio.runner.observed import ObservedRun
from spectio.runner.rundir import read_run_manifest, run_paths
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.rebuild import rebuild_index
from spectio_server.store.db import open_db
from spectio_server.store.runs import insert_observed_run
from spectio_server.store.schema import (
    events,
    launches,
    run_stages,
    runner_commands,
    runs,
    workflow_versions,
    workflows,
)
from spectio_server.store.writer import Writer
from spectio_server.targets import plan_of

from ..test_serve import run_id
from .conftest import client_for
from .test_failure import event, push
from .test_launch import RUNS, fields, table
from .test_relaunch import end, resume

INSPECT = "/api/v1/targets:inspect"
NONE = dict.fromkeys(("version", "hash", "source", "path", "flag", "checksum_changed"))
SPIKE = Path(__file__).resolve().parents[4] / "spikes" / "module-run"
VIEW = json.loads((SPIKE / "fastqc-view.json").read_text())
VERSION = VIEW["version"]
JOB_STATS = (SPIKE / "smk-merge-empty.txt").read_text().split("=== snakemake -n --until")[0]


class FakeEngine:
    """Answers `module view`, `--list-rules` and a dry run as the real engines do."""

    def __init__(self, rc: int = 0) -> None:
        self.calls: list[tuple[str, list[str]]] = []
        self.rc = rc

    def __call__(self, engine: str, argv: list[str]) -> tuple[int, str, str]:
        self.calls.append((engine, argv))
        if self.rc:
            return self.rc, "", "ERROR ~ Module nf-core/nope not found\nmore"
        if argv[:2] == ["module", "view"]:
            return 0, "profile noise\n" + json.dumps(VIEW), ""
        if "--list-rules" in argv:
            return 0, "all\nmake_reads\nqc_stats\nmerge\nalign_done\nsplit\n", ""
        return 0, "Building DAG of jobs...\n" + JOB_STATS, ""


@pytest.fixture
def engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def on(settings: Settings, writer: Writer, engine: FakeEngine) -> TestClient:
    settings.features = FeatureOpts(single_target=True)
    client = client_for(settings, writer)
    client.app.state.target_engine = engine  # type: ignore[attr-defined]
    return client


def module_launch(client: TestClient, **target: Any) -> Any:
    body = {
        "workflow": {"location": target.pop("location", "nf-core/fastqc"), "engine": "nextflow"},
        "params": target.pop("params", {"meta": {"id": "s1"}, "reads": "/data/s1.fq.gz"}),
        "target": {"kind": "module", **target},
    }
    return client.post(RUNS, json=body)


def test_flag_off_refuses_targets(authed_client: TestClient) -> None:
    response = module_launch(authed_client, version=VERSION)
    assert response.status_code == 422 and response.json()["type"].endswith("not-in-this-version")
    response = authed_client.post(INSPECT, json={"engine": "nextflow", "location": "nf-core/x"})
    assert response.status_code == 422 and response.json()["type"].endswith("not-in-this-version")


def test_registry_module_launch(on: TestClient, writer: Writer, settings: Settings) -> None:
    response = module_launch(on, version=VERSION)
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["name"] == f"fastqc-{run['id'][-6:]}"
    target = {"kind": "module", "name": "nf-core/fastqc", "version": VERSION}
    assert run["target"] == {**NONE, **target, "source": "registry", "more": 0}
    (workflow,) = table(writer, workflows)
    assert (workflow.source, workflow.location) == ("module-registry", "nf-core/fastqc")
    (version,) = table(writer, workflow_versions)
    assert version.revision == VERSION
    (row,) = table(writer, runs)
    assert row.target["version"] == VERSION and row.results_dir is None
    (cmd,) = table(writer, runner_commands)
    payload = LaunchPayload.model_validate(cmd.payload)
    assert payload.location == "nf-core/fastqc" and payload.target is not None
    assert payload.target.version == VERSION
    manifest = read_run_manifest(run_paths(settings.runs_root, run["id"]).run_dir)
    assert manifest.target == payload.target


def test_registry_module_is_pinned_and_allowed(on: TestClient, engine: FakeEngine) -> None:
    assert fields(module_launch(on)) == ["target.version"]
    assert fields(module_launch(on, version="latest")) == ["target.version"]
    assert fields(module_launch(on, version="1;rm")) == ["target.version"]
    assert fields(module_launch(on, location="someone/fastqc", version="1")) == [
        "workflow.location"
    ]
    assert fields(module_launch(on, location="nf-core/../x", version="1")) == ["workflow.location"]
    assert fields(module_launch(on, version=VERSION, params={"outdir": "/x"})) == ["params.outdir"]
    assert all(argv[-1] == "nf-core/fastqc" for _, argv in engine.calls)
    assert ["-version", VERSION] == engine.calls[0][1][4:6]


def test_engine_failure_is_a_502(settings: Settings, writer: Writer) -> None:
    settings.features = FeatureOpts(single_target=True)
    client = client_for(settings, writer)
    client.app.state.target_engine = FakeEngine(rc=1)  # type: ignore[attr-defined]
    response = module_launch(client, version="1.0")
    assert response.status_code == 502
    assert response.json()["detail"].endswith("ERROR ~ Module nf-core/nope not found")


def test_local_module_launch(on: TestClient, writer: Writer, tmp_path: Path) -> None:
    module = tmp_path / "hello"
    module.mkdir()
    (module / "main.nf").write_text("process HELLO { }\n")
    (module / "meta.yml").write_text(
        "name: hello\nversion: '1.2'\ninput:\n"
        "  - - meta:\n        type: map\n    - name:\n        type: string\n"
    )
    response = module_launch(on, location=str(module), params={"meta": {"id": "a"}})
    assert response.status_code == 201, response.text
    target = response.json()["target"]
    assert target["source"] == "local" and target["version"] == "1.2"
    assert target["hash"] == hashlib.sha256(b"process HELLO { }\n").hexdigest()
    (workflow,) = table(writer, workflows)
    assert (workflow.source, workflow.location) == ("module-local", str(module))
    assert fields(module_launch(on, location=str(module), version="9")) == ["target.version"]
    (module / "meta.yml").unlink()
    (module / "meta.yml").symlink_to(module / "main.nf")
    assert fields(module_launch(on, location=str(module))) == ["workflow.location"]


def test_rule_launch(on: TestClient, synthetic: Path, writer: Writer) -> None:
    body = {
        "workflow": {"location": str(synthetic / "snakemake"), "engine": "snakemake"},
        "params": {},
        "target": {"kind": "rule", "name": "qc_report"},
    }
    response = on.post(RUNS, json=body)
    assert response.status_code == 201, response.text
    assert response.json()["target"] == {
        **NONE,
        "kind": "rule",
        "name": "qc_report",
        "flag": "target",
        "more": 0,
    }
    (workflow,) = table(writer, workflows)
    assert workflow.source == "local"  # a rule target keeps the pipeline's workflow
    (cmd,) = table(writer, runner_commands)
    assert LaunchPayload.model_validate(cmd.payload).target is not None
    bad = {**body, "target": {"kind": "rule", "name": "all; rm"}}
    assert fields(on.post(RUNS, json=bad)) == ["target.name"]
    nf = {**body, "workflow": {"location": str(synthetic / "nextflow"), "engine": "nextflow"}}
    assert fields(on.post(RUNS, json=nf)) == ["target.kind"]


def test_inspect_module(on: TestClient) -> None:
    response = on.post(INSPECT, json={"engine": "nextflow", "location": "nf-core/fastqc"})
    assert response.status_code == 200, response.text
    found = response.json()
    assert (found["version"], found["source"]) == (VERSION, "registry")
    assert [i["name"] for i in found["inputs"]] == ["meta", "reads"]
    assert found["description"] == "Run FastQC on sequenced reads"


def test_inspect_rules_and_plan(on: TestClient, synthetic: Path, engine: FakeEngine) -> None:
    location = str(synthetic / "snakemake")
    body = {"engine": "snakemake", "location": location}
    found = on.post(INSPECT, json=body).json()
    assert found["rules"][:2] == ["all", "make_reads"] and found["plan"] is None
    found = on.post(INSPECT, json={**body, "rule": "merge"}).json()
    assert found["plan"] == {
        "jobs": {"make_reads": 1, "split": 1, "align_done": 1, "merge": 1},
        "total": 4,
    }
    argv = engine.calls[-1][1]
    assert argv[argv.index("--directory") + 2] == "merge" and "-n" in argv
    unknown = on.post(INSPECT, json={**body, "rule": "nope"})
    assert fields(unknown) == ["rule"]


def test_plan_of() -> None:
    assert plan_of("Nothing to be done (all requested files are present and up to date).") is None
    assert plan_of(JOB_STATS) == {
        "jobs": {"make_reads": 1, "split": 1, "align_done": 1, "merge": 1},
        "total": 4,
    }


def test_rebuild_keeps_the_target(on: TestClient, settings: Settings, tmp_path: Path) -> None:
    """A rebuilt index (Assumption 21) keeps the target and the module's workflow."""
    run_id = module_launch(on, version=VERSION).json()["id"]
    db_dir = tmp_path / "rebuilt"
    db_dir.mkdir(mode=0o700)
    engine, _ = open_db(db_dir)
    fresh = Writer(engine)
    try:
        fresh.submit(lambda c: ensure_tenancy(c, "me", "local", {}, "0.0.1")).result()
        rebuild_index(fresh, settings.runs_root)
        query = select(runs.c.target, workflows.c.source).where(runs.c.id == run_id)
        query = query.join(workflow_versions, workflow_versions.c.id == runs.c.workflow_version_id)
        query = query.join(workflows, workflows.c.id == workflow_versions.c.workflow_id)
        row = fresh.submit(lambda c: c.execute(query).one()).result()
    finally:
        fresh.close()
        engine.dispose()
    assert row.target["version"] == VERSION and row.source == "module-registry"


def test_migration_keeps_workflows(settings: Settings) -> None:
    """0015 copies `workflows` to change its CHECK: the rows that point to it survive."""
    assert settings.db_dir is not None
    engine, _ = open_db(settings.db_dir)
    alembic = Config()
    alembic.set_main_option("script_location", "spectio_server:migrations")
    with engine.begin() as conn:
        ensure_tenancy(conn, "me", "local", {}, "0.0.1")
        alembic.attributes["connection"] = conn
        command.downgrade(alembic, "0011")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO workflows (id, created_at, project_id, location, source, engine) "
            "SELECT 'wfl_1', CURRENT_TIMESTAMP, id, '/p', 'local', 'nextflow' FROM projects"
        )
        conn.exec_driver_sql(
            "INSERT INTO workflow_versions (id, created_at, workflow_id) "
            "VALUES ('wfv_1', CURRENT_TIMESTAMP, 'wfl_1')"
        )
    engine.dispose()
    engine, new = open_db(settings.db_dir)
    try:
        assert not new
        with engine.connect() as conn:
            assert conn.execute(select(workflow_versions.c.workflow_id)).scalar_one() == "wfl_1"
            assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []
            sql = conn.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE name = 'workflows'"
            ).scalar_one()
            assert "module-registry" in sql
    finally:
        engine.dispose()


# --- Capture: the target the bridges report (architecture §13.8) ------------------------------

CHECKSUM = "b64b18ed1fe095a8be3354d2b6706c87fbff3c2108214ac7887b428f5227173a"
REPORTED = {
    "kind": "module",
    "name": "nf-core/fastqc",
    "version": VERSION,
    "hash": CHECKSUM,
    "source": "registry",
}


def observed(writer: Writer, n: int, launch_dir: str, engine: str = "nextflow") -> str:
    """A run started from a terminal in `launch_dir`; its launch's ID."""
    run = ObservedRun(
        run_id=run_id(n),
        launch_dir=launch_dir,
        engine=engine,  # type: ignore[arg-type]
        engine_version="26.10.4",
        bridge_version="0.0.1",
        host="login1",
        pid=4242,
        pid_start_time="1",
        boot_id="0" * 36,
    )
    writer.submit(lambda c: insert_observed_run(c, run, datetime.now(UTC))).result()
    query = select(launches.c.id).where(launches.c.run_id == run_id(n))
    launch_id: str = writer.submit(lambda c: c.execute(query).scalar_one()).result()
    return launch_id


def module_of(writer: Writer, run: str) -> Any:
    query = (
        select(runs.c.target, workflows.c.source, workflows.c.location, workflow_versions.c.key)
        .join(workflow_versions, workflow_versions.c.id == runs.c.workflow_version_id)
        .join(workflows, workflows.c.id == workflow_versions.c.workflow_id)
        .where(runs.c.id == run)
    )
    return writer.submit(lambda c: c.execute(query).one()).result()


def test_terminal_module_runs_share_one_workflow(settings: Settings, writer: Writer) -> None:
    """Discovered: two terminal runs of one module, in two directories, are one workflow."""
    for n, where in ((1, "/scratch/a"), (2, "/scratch/b")):
        launch = observed(writer, n, where)
        hash_ = CHECKSUM if n == 1 else "0" * 64
        create = event(1, "nextflow.onFlowCreate", run_id(n), target={**REPORTED, "hash": hash_})
        push(writer, settings, launch, create, event(2, "nextflow.onFlowBegin", run_id(n)))
    first, second = module_of(writer, run_id(1)), module_of(writer, run_id(2))
    assert (first.source, first.location) == ("module-registry", "nf-core/fastqc")
    assert (second.source, second.location) == ("module-registry", "nf-core/fastqc")
    assert first.key == CHECKSUM and "checksum_changed" not in first.target
    assert second.target["checksum_changed"] is True
    sources = [w.source for w in table(writer, workflows)]
    assert sources == ["module-registry"]  # the launch directories' workflows are gone
    stages_note = writer.submit(
        lambda c: c.execute(
            select(events.c.payload).where(
                events.c.run_id == run_id(1), events.c.type == "spectio.stages.frozen"
            )
        ).scalar_one()
    ).result()
    assert stages_note["note"] == "This run targets one module"


def test_launched_module_run_gets_its_checksum(on: TestClient, writer: Writer) -> None:
    run = module_launch(on, version=VERSION).json()["id"]
    (launch,) = table(writer, launches)
    create = event(1, "nextflow.onFlowCreate", run, target={**REPORTED, "version": "other"})
    push(writer, on.app.state.settings, launch.id, create)  # type: ignore[attr-defined]
    found = module_of(writer, run)
    assert found.target["hash"] == CHECKSUM and found.target["version"] == VERSION
    assert found.key == CHECKSUM


def test_rule_target_has_no_stages(on: TestClient, writer: Writer, settings: Settings) -> None:
    launch = observed(writer, 3, "/scratch/smk", engine="snakemake")
    target = {"kind": "rule", "name": "qc_report", "flag": "until"}
    push(writer, settings, launch, event(1, "snakemake.workflow_started", run_id(3), target=target))
    detail = on.get(f"/api/v1/runs/{run_id(3)}").json()
    assert detail["target"] == {**NONE, **target, "more": 0}
    assert detail["stages_note"] == "This run targets rule qc_report"
    assert table(writer, run_stages) == []
    assert module_of(writer, run_id(3)).source == "local"  # a rule keeps its workflow


def test_runs_list_filter_and_version(on: TestClient, writer: Writer, settings: Settings) -> None:
    module = module_launch(on, version=VERSION).json()["id"]
    whole = observed(writer, 4, "/scratch/whole")
    assert whole
    listed = {
        f: [r["id"] for r in on.get(f"/api/v1/runs?target={f}").json()["items"]]
        for f in ("any", "none")
    }
    assert listed == {"any": [module], "none": [run_id(4)]}
    assert on.get("/api/v1/runs?target=some").status_code == 422
    assert on.get("/api/v1/version").json()["features"] == {"single_target": True}


def test_copy_and_resume_keep_the_target(on: TestClient, writer: Writer) -> None:
    run = module_launch(on, version=VERSION).json()["id"]
    template = on.get(f"/api/v1/runs/{run}:launch-template").json()
    assert template["target"] == {"kind": "module", "version": VERSION}
    assert template["workflow"]["location"] == "nf-core/fastqc"
    copy = on.post(RUNS, json={k: template[k] for k in ("workflow", "params", "target")})
    assert copy.status_code == 201, copy.text
    assert copy.json()["target"]["version"] == VERSION


def test_resume_keeps_the_target(on: TestClient, writer: Writer, settings: Settings) -> None:
    run = module_launch(on, version=VERSION).json()["id"]
    end(writer, settings, run)
    response = resume(on, run)
    assert response.status_code == 201, response.text
    assert response.json()["target"]["version"] == VERSION
    child = response.json()["id"]
    command = next(c for c in table(writer, runner_commands) if c.run_id == child)
    payload = LaunchPayload.model_validate(command.payload)
    assert payload.location == "nf-core/fastqc" and payload.resume_of is not None
    assert payload.target is not None and payload.target.version == VERSION
