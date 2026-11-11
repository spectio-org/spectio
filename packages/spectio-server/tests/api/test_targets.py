"""Runs that target one module or one rule (api-and-data-model.md §5.10, #161): the launch, the
inspection for the Launch form, the store and the rebuild."""

import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, update

from spectio.config import FeatureOpts, Settings
from spectio.runner import loop
from spectio.runner.engines import EngineInfo
from spectio.runner.loop import LaunchPayload
from spectio.runner.observed import ObservedRun
from spectio.runner.rundir import read_run_manifest, run_paths, write_run_manifest
from spectio_sdk.targets import RunTarget
from spectio_server.api.relaunch import _target_in
from spectio_server.api.workflows import read_params
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.rebuild import rebuild_index
from spectio_server.sink import StoreSink
from spectio_server.store.db import open_db
from spectio_server.store.runs import insert_observed_run
from spectio_server.store.schema import (
    events,
    launches,
    projects,
    run_stages,
    runner_commands,
    runs,
    spool_drops,
    workflow_versions,
    workflows,
)
from spectio_server.store.writer import Writer
from spectio_server.targets import INSPECTIONS, MAX_META_BYTES, login_engine, plan_of

from ..test_serve import run_id
from .conftest import client_for
from .test_failure import event, push
from .test_launch import RUNS, RecordingLauncher, fields, table
from .test_relaunch import end, resume

INSPECT = "/api/v1/targets:inspect"
NONE = dict.fromkeys(("version", "hash", "source", "path", "flag", "checksum_changed"))
SPIKE = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "module-run"
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
    create = event(1, "nextflow.onFlowCreate", run, target=REPORTED)
    push(writer, on.app.state.settings, launch.id, create)  # type: ignore[attr-defined]
    found = module_of(writer, run)
    assert found.target["hash"] == CHECKSUM and found.target["version"] == VERSION
    assert found.key == CHECKSUM


def test_launched_module_run_keeps_its_own_target(on: TestClient, writer: Writer) -> None:
    """SEC-161S-09: a head that reports another module adds nothing: the launch's target is
    kept, its checksum unknown."""
    run = module_launch(on, version=VERSION).json()["id"]
    (launch,) = table(writer, launches)
    create = event(1, "nextflow.onFlowCreate", run, target={**REPORTED, "name": "nf-core/other"})
    push(writer, on.app.state.settings, launch.id, create)  # type: ignore[attr-defined]
    found = module_of(writer, run)
    assert found.target["name"] == "nf-core/fastqc" and "hash" not in found.target
    assert found.key is None


def test_launched_module_run_keeps_its_pinned_version(on: TestClient, writer: Writer) -> None:
    """CR-161S2-03: the installed `meta.yml` may name the version otherwise than the pin: the
    pin is kept and the checksum still added."""
    run = module_launch(on, version=VERSION).json()["id"]
    (launch,) = table(writer, launches)
    create = event(1, "nextflow.onFlowCreate", run, target={**REPORTED, "version": "1.0"})
    push(writer, on.app.state.settings, launch.id, create)  # type: ignore[attr-defined]
    found = module_of(writer, run)
    assert found.target["version"] == VERSION and found.target["hash"] == CHECKSUM


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


# --- Review fixes (SEC-161S, CR-161S) ---------------------------------------------------------


def local(tmp_path: Path, meta: str, name: str = "hello") -> Path:
    module = tmp_path / name
    module.mkdir()
    (module / "main.nf").write_text("process HELLO { }\n")
    (module / "meta.yml").write_text(meta)
    return module


def inspect_local(client: TestClient, module: Path) -> Any:
    return client.post(INSPECT, json={"engine": "nextflow", "location": str(module)})


def test_meta_yml_aliases_and_nesting_refused(on: TestClient, tmp_path: Path) -> None:
    """SEC-161S-01: no alias (a small file growing huge), no nesting deep enough to recurse."""
    bomb = local(tmp_path, "a: &a [x, x]\nb: &b [*a, *a]\nname: hello\n", "bomb")
    assert fields(inspect_local(on, bomb)) == ["workflow.location"]
    deep = local(tmp_path, "name: deep\nx: " + "[" * 1000 + "]" * 1000 + "\n", "deep")
    assert fields(inspect_local(on, deep)) == ["workflow.location"]


def test_meta_yml_deep_flow_is_refused_fast(on: TestClient, tmp_path: Path) -> None:
    """SEC-161S2-01: deep flow nesting is refused before PyYAML parses it (a quadratic parse),
    and a `meta.yml` past 64 KiB is not read."""
    deep = local(tmp_path, "name: deep\nx: " + "[" * 60000 + "\n", "deep")
    start = time.monotonic()
    assert fields(inspect_local(on, deep)) == ["workflow.location"]
    assert time.monotonic() - start < 1
    big = local(tmp_path, "name: big\n" + "# padding\n" * 7000, "big")
    response = inspect_local(on, big)
    assert fields(response) == ["workflow.location"]
    assert "larger than 65536 bytes" in response.text


def test_meta_yml_not_utf8_quotes_no_bytes(on: TestClient, tmp_path: Path) -> None:
    """SEC-161S2-05: the refusal names the file, not the bytes the decoder stopped at."""
    module = local(tmp_path, "name: hello\n", "latin")
    (module / "meta.yml").write_bytes(b"name: h\xe9llo\n")
    response = inspect_local(on, module)
    assert fields(response) == ["workflow.location"] and "not UTF-8 text" in response.text
    assert "xe9" not in response.text


def test_meta_yml_control_characters_refused(on: TestClient, tmp_path: Path) -> None:
    """SEC-161S-12: a meta.yml name or version is refused as a location would be."""
    named = local(tmp_path, 'name: "hello\\u001b[31m"\n', "named")
    assert fields(inspect_local(on, named)) == ["workflow.location"]
    versioned = local(tmp_path, 'name: hello\nversion: "1\\n2"\n', "versioned")
    assert fields(inspect_local(on, versioned)) == ["workflow.location"]


def test_local_module_reads_no_fifo(on: TestClient, tmp_path: Path) -> None:
    """SEC-161S-05: `main.nf` read without blocking, as inspect reads a pipeline's files."""
    module = local(tmp_path, "name: hello\n")
    (module / "main.nf").unlink()
    os.mkfifo(module / "main.nf")
    assert fields(inspect_local(on, module)) == ["workflow.location"]


def test_module_view_text_after_the_json(settings: Settings, writer: Writer) -> None:
    """CR-161S-10: the answer is JSON, read up to its end; what follows does not matter."""

    def view(engine: str, argv: list[str]) -> tuple[int, str, str]:
        return 0, "profile noise\n" + json.dumps(VIEW) + "\nbye {", ""

    settings.features = FeatureOpts(single_target=True)
    client = client_for(settings, writer)
    client.app.state.target_engine = view  # type: ignore[attr-defined]
    response = client.post(INSPECT, json={"engine": "nextflow", "location": "nf-core/fastqc"})
    assert response.status_code == 200, response.text


def test_engine_answer_is_capped(settings: Settings) -> None:
    """CR-161S-02, SEC-161S-06: an engine that prints without end is stopped past 1 MiB."""
    settings.engines.nextflow_cmd = "yes"
    rc, out, err = login_engine(settings)("nextflow", ["module", "view"])
    assert rc == 125 and len(out) <= MAX_META_BYTES and "larger than" in err


def test_inspect_is_bounded(on: TestClient) -> None:
    """At most two inspections at once: a third is 503, never a queue of engine processes."""
    taken = [INSPECTIONS.acquire(blocking=False) for _ in range(2)]
    try:
        assert all(taken)
        response = on.post(INSPECT, json={"engine": "nextflow", "location": "nf-core/fastqc"})
        assert response.status_code == 503
    finally:
        for _ in taken:
            INSPECTIONS.release()
    response = on.post(INSPECT, json={"engine": "nextflow", "location": "nf-core/fastqc"})
    assert response.status_code == 200


def test_module_launch_is_bounded(on: TestClient, engine: FakeEngine) -> None:
    """SEC-161S2-03: `POST /runs` of a registry module asks the engine under the same bound."""
    taken = [INSPECTIONS.acquire(blocking=False) for _ in range(2)]
    try:
        assert all(taken)
        assert module_launch(on, version=VERSION).status_code == 503 and engine.calls == []
    finally:
        for _ in taken:
            INSPECTIONS.release()


def test_module_without_inputs_takes_no_params(on: TestClient, tmp_path: Path) -> None:
    """CR-161S-04: a module that declares no input takes no parameter."""
    module = local(tmp_path, "name: hello\n")
    assert fields(module_launch(on, location=str(module), params={"x": 1})) == ["params.x"]


def test_module_target_takes_no_name(on: TestClient) -> None:
    """CR-161S-08: a module's name is its location."""
    assert fields(module_launch(on, version=VERSION, name="other")) == ["target.name"]


def test_module_config_file_refused_first(settings: Settings, writer: Writer) -> None:
    """CR-161S-09: a config file is refused before the engine is asked anything."""
    settings.features = FeatureOpts(single_target=True)
    client = client_for(settings, writer)
    failing = FakeEngine(rc=1)
    client.app.state.target_engine = failing  # type: ignore[attr-defined]
    body = {
        "workflow": {"location": "nf-core/fastqc", "engine": "nextflow"},
        "target": {"kind": "module", "version": VERSION},
        "config_file": "/etc/x.config",
    }
    assert fields(client.post(RUNS, json=body)) == ["config_file"] and failing.calls == []


def test_resume_checks_the_registry_module_again(
    on: TestClient, writer: Writer, settings: Settings
) -> None:
    """CR-161S-03, SEC-161S-03: Resume runs the launch's rules again: the flag, the namespace."""
    run = module_launch(on, version=VERSION).json()["id"]
    end(writer, settings, run)
    settings.features = FeatureOpts(single_target=True, module_namespaces=["other"])
    assert fields(resume(on, run)) == ["workflow.location"]
    settings.features = FeatureOpts(single_target=False)
    response = resume(on, run)
    assert response.status_code == 422 and response.json()["type"].endswith("not-in-this-version")


def test_resume_of_a_registry_module_drops_its_checksum(
    on: TestClient, writer: Writer, settings: Settings
) -> None:
    """SEC-161S-09: the child's head reports its own checksum, compared with the parent's."""
    run = module_launch(on, version=VERSION).json()["id"]
    launch = next(r for r in table(writer, launches) if r.run_id == run)
    push(writer, settings, launch.id, event(1, "nextflow.onFlowCreate", run, target=REPORTED))
    end(writer, settings, run)
    response = resume(on, run)
    assert response.status_code == 201, response.text
    assert response.json()["target"]["hash"] is None


def test_resume_of_a_local_module_reads_it_again(
    on: TestClient, writer: Writer, settings: Settings, tmp_path: Path
) -> None:
    """CR-161S-03: a local module is read again: the child runs what is there now."""
    module = local(tmp_path, "name: hello\nversion: '1'\n")
    run = module_launch(on, location=str(module), params={}).json()["id"]
    end(writer, settings, run)
    (module / "main.nf").write_text("process HELLO2 { }\n")
    (module / "meta.yml").write_text("name: hello\nversion: '2'\n")
    response = resume(on, run)
    assert response.status_code == 201, response.text
    target = response.json()["target"]
    assert target["hash"] == hashlib.sha256(b"process HELLO2 { }\n").hexdigest()
    assert target["version"] == "2"


def test_rebuild_refuses_a_bad_registry_manifest(
    on: TestClient, settings: Settings, tmp_path: Path
) -> None:
    """CR-161S-03: a rebuilt registry module run meets the launch grammar, or is skipped."""
    run_id = module_launch(on, version=VERSION).json()["id"]
    run_dir = run_paths(settings.runs_root, run_id).run_dir
    manifest = read_run_manifest(run_dir)
    assert manifest.target is not None
    bad = manifest.target.model_copy(update={"version": "1;rm -rf"})
    write_run_manifest(run_dir, manifest.model_copy(update={"target": bad}))
    db_dir = tmp_path / "rebuilt"
    db_dir.mkdir(mode=0o700)
    engine, _ = open_db(db_dir)
    fresh = Writer(engine)
    try:
        fresh.submit(lambda c: ensure_tenancy(c, "me", "local", {}, "0.0.1")).result()
        found = rebuild_index(fresh, settings.runs_root)
    finally:
        fresh.close()
        engine.dispose()
    assert (found.added, found.skipped) == (0, 1)


def test_copy_of_a_local_module_flags_its_directory(on: TestClient, tmp_path: Path) -> None:
    """SEC-161S-02: a module directory others may write is flagged, as a pipeline's is."""
    module = local(tmp_path, "name: hello\n")
    run = module_launch(on, location=str(module), params={}).json()["id"]
    module.chmod(0o777)
    found = on.get(f"/api/v1/runs/{run}:launch-template").json()["code_loading"]
    assert found == [
        {"field": "workflow.location", "value": str(module), "writable_by_others": True}
    ]


def test_runner_refuses_a_relative_location_unless_a_registry_module(
    on: TestClient, synthetic: Path, writer: Writer, settings: Settings, monkeypatch: Any
) -> None:
    """SEC-161S-10: only a Nextflow registry module runs from a name, not a rule that says
    `source: registry`."""
    monkeypatch.setattr(loop, "check_engine", lambda e, c: EngineInfo("snakemake", "9.27.1"))
    body = {
        "workflow": {"location": str(synthetic / "snakemake"), "engine": "snakemake"},
        "target": {"kind": "rule", "name": "qc_report"},
    }
    assert on.post(RUNS, json=body).status_code == 201
    (cmd,) = table(writer, runner_commands)
    target = {"kind": "rule", "name": "qc_report", "source": "registry"}
    payload = {**cmd.payload, "location": "nf-core/fastqc", "target": target}
    query = update(runner_commands).where(runner_commands.c.id == cmd.id).values(payload=payload)
    writer.submit(lambda c: c.execute(query)).result()
    launcher = RecordingLauncher()
    loop.RunnerLoop(StoreSink(writer, settings.runs_root), launcher, settings).tick()
    assert launcher.specs == []
    (row,) = table(writer, runs)
    assert row.state == "failed" and "absolute path" in row.failure["message"]


def test_target_in_of_a_copy() -> None:
    """CR-161S-07: a file target is copied as the whole pipeline; a rule keeps its name."""
    assert _target_in(RunTarget(kind="file", name="out/a.txt", flag="target")) is None
    until = RunTarget(kind="rule", name="qc_report", flag="until")
    assert _target_in(until) == {"kind": "rule", "name": "qc_report"}


def drops_of(writer: Writer, launch: str) -> dict[str, int]:
    query = select(spool_drops.c.reason, spool_drops.c.count).where(
        spool_drops.c.launch_id == launch
    )
    rows = writer.submit(lambda c: c.execute(query).all()).result()
    return {reason: n for reason, n in rows}


@pytest.mark.parametrize(
    ("engine", "target"),
    [
        ("nextflow", {"kind": "rule", "name": "qc_report"}),
        ("snakemake", {**REPORTED}),
        ("nextflow", {**REPORTED, "name": "NF/../fastqc"}),
        ("nextflow", {**REPORTED, "hash": "abc"}),
        ("nextflow", {**REPORTED, "version": "1\x1b[31m"}),
        ("nextflow", {"kind": "module", "name": "m", "source": "local", "path": "rel/m"}),
        ("nextflow", {"kind": "module", "name": "m", "source": "local", "path": "/a/../m"}),
        ("nextflow", {"kind": "module", "name": "m"}),
        ("nextflow", {**REPORTED, "hash": None}),
    ],
    ids=[
        *("rule-on-nf", "module-on-smk", "name", "hash", "control", "relative", "dotdot"),
        *("nosrc", "nohash"),
    ],
)
def test_reported_target_that_does_not_fit_is_dropped(
    settings: Settings, writer: Writer, engine: str, target: dict[str, Any]
) -> None:
    """SEC-161S-07: a reported target that does not fit its engine or the grammars moves
    nothing: no target, no workflow moved; the refusal is counted."""
    launch = observed(writer, 5, "/scratch/forged", engine=engine)
    hook = "nextflow.onFlowCreate" if engine == "nextflow" else "snakemake.workflow_started"
    push(writer, settings, launch, event(1, hook, run_id(5), target=target))
    found = module_of(writer, run_id(5))
    assert found.target is None and found.source == "local"
    assert drops_of(writer, launch) == {"target_refused": 1}


def test_checksum_changed_within_one_project(settings: Settings, writer: Writer) -> None:
    """SEC-161S-08: another project's run of the module is not compared."""
    launch = observed(writer, 6, "/scratch/a")
    push(writer, settings, launch, event(1, "nextflow.onFlowCreate", run_id(6), target=REPORTED))

    def elsewhere(conn: Any) -> None:
        conn.execute(
            insert(projects).values(
                id="prj_other", created_at=datetime.now(UTC), owning_group_id="grp_x"
            )
        )
        conn.execute(update(workflows).values(project_id="prj_other"))
        conn.execute(update(runs).values(project_id="prj_other"))

    writer.submit(elsewhere).result()
    launch = observed(writer, 7, "/scratch/b")
    other = {**REPORTED, "hash": "0" * 64}
    push(writer, settings, launch, event(1, "nextflow.onFlowCreate", run_id(7), target=other))
    assert "checksum_changed" not in module_of(writer, run_id(7)).target


def test_unversioned_module_runs_are_not_compared(settings: Settings, writer: Writer) -> None:
    """CR-161S-01: with no version, two checksums say nothing about one release."""
    for n, hash_ in ((8, CHECKSUM), (9, "0" * 64)):
        launch = observed(writer, n, f"/scratch/{n}")
        target = {**REPORTED, "version": None, "hash": hash_}
        push(writer, settings, launch, event(1, "nextflow.onFlowCreate", run_id(n), target=target))
    assert "checksum_changed" not in module_of(writer, run_id(9)).target


def test_deep_params_file_says_nested_too_deep(tmp_path: Path) -> None:
    """CR-161S3-02: the bracket bound of `load_yaml` keeps the callers' own message."""
    (tmp_path / "params.yml").write_text("x: " + "[" * 100 + "]" * 100 + "\n")
    with pytest.raises(ValueError, match=r"params\.yml is nested too deep to be read"):
        read_params(tmp_path, "params.yml")
