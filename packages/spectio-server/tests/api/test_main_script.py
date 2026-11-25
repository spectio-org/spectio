"""A Nextflow pipeline whose entry script is not `main.nf` (#351, inbox #161 finding 17): inspect
lists the candidates, `POST /runs` takes `workflow.main_script`, the run keeps it, Resume and
Copy to a new launch carry it, and the launch map draws it."""

import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from spectio.config import Settings
from spectio.runner import loop, resume
from spectio.runner.engines import EngineInfo
from spectio.runner.loop import LaunchPayload
from spectio.runner.rundir import make_run_dirs, read_run_manifest, run_paths
from spectio_server.api import workflows as wf
from spectio_server.graph import bioflow
from spectio_server.sink import StoreSink
from spectio_server.store.schema import launches, runs
from spectio_server.store.writer import Writer

from .test_graph import graph_client
from .test_launch import INSPECT, RUNS, RecordingLauncher, fields, table

ENTRY = "workflow {\n    main:\n    FOO()\n}\n"


def scripts(tmp_path: Path, main: bool = False) -> Path:
    """Two entry scripts, a library of named workflows, and a symlinked entry script."""
    root = tmp_path / "multi"
    root.mkdir()
    (root / "main_cellpose.nf").write_text(f"include {{ FOO }} from './lib.nf'\n{ENTRY}")
    (root / "main_eubibridge_single.nf").write_text("workflow{ FOO() }\n")
    (root / "lib.nf").write_text("workflow FOO {\n}\nprocess BAR {\n}\n")
    (tmp_path / "elsewhere.nf").write_text(ENTRY)
    (root / "linked.nf").symlink_to(tmp_path / "elsewhere.nf")
    (root / "dir.nf").mkdir()  # a directory, and a FIFO where the system makes one
    if hasattr(os, "mkfifo"):
        os.mkfifo(root / "pipe.nf")
    if main:
        (root / "main.nf").write_text("// DSL1: no workflow block\n")
    return root


def launch(client: TestClient, root: Path, engine: str = "nextflow", **workflow: Any) -> Any:
    body = {"workflow": {"location": str(root), "engine": engine, **workflow}, "params": {}}
    return client.post(RUNS, json=body)


def message(response: Any) -> str:
    return str(response.json()["errors"][0]["message"])


# --- Inspect ---------------------------------------------------------------------------------


def test_inspect_lists_the_main_scripts(authed_client: TestClient, tmp_path: Path) -> None:
    root = scripts(tmp_path)
    body = authed_client.get(INSPECT, params={"location": str(root)}).json()
    # an unnamed workflow block, a regular file at the top: no library, no symlink
    assert body["main_scripts"] == ["main_cellpose.nf", "main_eubibridge_single.nf"]
    assert (body["engine"], body["engine_files"]) == ("nextflow", [])


def test_inspect_lists_main_nf_first(authed_client: TestClient, tmp_path: Path) -> None:
    root = scripts(tmp_path, main=True)
    body = authed_client.get(INSPECT, params={"location": str(root)}).json()
    assert body["main_scripts"] == ["main.nf", "main_cellpose.nf", "main_eubibridge_single.nf"]
    assert (body["engine"], body["engine_files"]) == ("nextflow", ["main.nf"])


def test_inspect_main_scripts_bounded(authed_client: TestClient, tmp_path: Path) -> None:
    """At most 50 files read, the first by name; a file past 1 MiB is left out."""
    root = tmp_path / "many"
    root.mkdir()
    for i in range(60):
        (root / f"entry_{i:02}.nf").write_text(ENTRY)
    body = authed_client.get(INSPECT, params={"location": str(root)}).json()
    assert body["main_scripts"] == [f"entry_{i:02}.nf" for i in range(50)]
    (root / "big.nf").write_text(ENTRY + "//" + "x" * wf.MAX_FILE)  # first by name
    body = authed_client.get(INSPECT, params={"location": str(root)}).json()
    assert body["main_scripts"] == [f"entry_{i:02}.nf" for i in range(49)]
    snakemake = tmp_path / "smk"
    (snakemake / "workflow").mkdir(parents=True)
    (snakemake / "workflow" / "Snakefile").write_text("rule all:\n    input: []\n")
    body = authed_client.get(INSPECT, params={"location": str(snakemake)}).json()
    assert (body["engine"], body["main_scripts"]) == ("snakemake", [])


def test_inspect_main_scripts_byte_budget(authed_client: TestClient, tmp_path: Path) -> None:
    """At most 8 MiB read in all: eight files of nearly 1 MiB, then the reads stop."""
    root = tmp_path / "large"
    root.mkdir()
    text = ENTRY + "//" + "x" * (wf.MAX_FILE - len(ENTRY) - 100) + "\n"
    for i in range(60):
        (root / f"entry_{i:02}.nf").write_text(text)
    assert wf.MAX_MAIN_SCRIPT_BYTES == 8 * wf.MAX_FILE
    body = authed_client.get(INSPECT, params={"location": str(root)}).json()
    assert body["main_scripts"] == [f"entry_{i:02}.nf" for i in range(8)]


def test_inspect_main_scripts_name_cap(
    authed_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At most MAX_SCRIPT_NAMES (1000) matching names are collected before they are sorted."""
    assert wf.MAX_SCRIPT_NAMES == 1000
    monkeypatch.setattr(wf, "MAX_SCRIPT_NAMES", 3)
    root = tmp_path / "names"
    root.mkdir()
    for i in range(10):
        (root / f"entry_{i}.nf").write_text(ENTRY)
    body = authed_client.get(INSPECT, params={"location": str(root)}).json()
    assert len(body["main_scripts"]) == 3


def test_inspect_lists_no_fifo_nor_directory(authed_client: TestClient, tmp_path: Path) -> None:
    root = scripts(tmp_path)
    body = authed_client.get(INSPECT, params={"location": str(root)}).json()
    assert not {"dir.nf", "pipe.nf"} & set(body["main_scripts"])


# --- Launch ----------------------------------------------------------------------------------


def test_launch_with_a_main_script(
    authed_client: TestClient,
    tmp_path: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = scripts(tmp_path)
    response = launch(authed_client, root, main_script="main_cellpose.nf")
    assert response.status_code == 201, response.text
    run_id = response.json()["id"]
    assert response.json()["workflow"]["main_script"] == "main_cellpose.nf"
    manifest = read_run_manifest(run_paths(settings.runs_root, run_id).run_dir)
    assert manifest.workflow.main_script == "main_cellpose.nf"
    (row,) = table(writer, runs)
    assert row.main_script == "main_cellpose.nf"
    detail = authed_client.get(f"{RUNS}/{run_id}").json()
    assert detail["workflow"]["main_script"] == "main_cellpose.nf"
    # the runner hands it to the head script
    monkeypatch.setattr(loop, "check_engine", lambda engine, cmd: EngineInfo("nextflow", "26.10.4"))
    launcher = RecordingLauncher()
    loop.RunnerLoop(StoreSink(writer, settings.runs_root), launcher, settings).tick()
    (spec,) = launcher.specs
    assert spec.main_script == "main_cellpose.nf"


def test_launch_without_main_nf_must_choose(authed_client: TestClient, tmp_path: Path) -> None:
    """No guess, even with one candidate: the refusal names them."""
    root = scripts(tmp_path)
    (root / "main_eubibridge_single.nf").unlink()
    response = launch(authed_client, root)
    assert fields(response) == ["workflow.main_script"]
    assert "main_cellpose.nf" in message(response)


def test_launch_with_main_nf_needs_no_choice(
    authed_client: TestClient, tmp_path: Path, writer: Writer
) -> None:
    response = launch(authed_client, scripts(tmp_path, main=True))
    assert response.status_code == 201, response.text
    (row,) = table(writer, runs)
    assert row.main_script is None


@pytest.mark.parametrize(
    "bad",
    [
        "../elsewhere.nf",
        "sub/x.nf",
        "-x.nf",
        "x.config",
        "missing.nf",
        "linked.nf",
        "lib",
        "dir.nf",
        "pipe.nf",  # missing where no FIFO was made: refused all the same
        "x" * 253 + ".nf",
    ],
)
def test_launch_main_script_refused(authed_client: TestClient, tmp_path: Path, bad: str) -> None:
    root = scripts(tmp_path)
    (root / "sub").mkdir()
    (root / "sub" / "x.nf").write_text(ENTRY)
    assert fields(launch(authed_client, root, main_script=bad)) == ["workflow.main_script"]


def test_launch_main_script_only_for_nextflow(authed_client: TestClient, tmp_path: Path) -> None:
    root = scripts(tmp_path)
    (root / "Snakefile").write_text("rule all:\n    input: []\n")
    response = launch(authed_client, root, "snakemake", main_script="main_cellpose.nf")
    assert fields(response) == ["workflow.main_script"]


# --- Resume, Copy to a new launch ------------------------------------------------------------


def test_resume_and_copy_keep_the_main_script(
    authed_client: TestClient,
    tmp_path: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resume, "processes_in", lambda path: [])  # no /proc on every system
    root = scripts(tmp_path)
    response = launch(authed_client, root, main_script="main_eubibridge_single.nf")
    assert response.status_code == 201, response.text
    run_id = response.json()["id"]
    template = authed_client.get(f"{RUNS}/{run_id}:launch-template").json()
    assert template["workflow"]["main_script"] == "main_eubibridge_single.nf"

    make_run_dirs(settings.runs_root, run_id)  # its head ran and failed
    session = "5f1c8a43-7f62-4a5e-9d4f-0a1b2c3d4e5f"

    def failed(conn: Any) -> None:
        conn.execute(update(runs).where(runs.c.id == run_id).values(state="failed"))
        conn.execute(
            update(launches).where(launches.c.run_id == run_id).values(engine_session_id=session)
        )

    writer.submit(failed).result()
    child = authed_client.post(f"{RUNS}/{run_id}:relaunch", json={"mode": "resume"})
    assert child.status_code == 201, child.text
    child_id = child.json()["id"]
    assert child.json()["workflow"]["main_script"] == "main_eubibridge_single.nf"
    manifest = read_run_manifest(run_paths(settings.runs_root, child_id).run_dir)
    assert manifest.workflow.main_script == "main_eubibridge_single.nf"
    (command,) = [
        c
        for c in StoreSink(writer, settings.runs_root).lease_commands()
        if c.kind == "launch" and c.launch.run_id == child_id
    ]
    assert LaunchPayload.model_validate(command.payload).main_script == "main_eubibridge_single.nf"
    found = writer.submit(
        lambda c: c.execute(select(runs.c.main_script).where(runs.c.id == child_id)).scalar()
    ).result()
    assert found == "main_eubibridge_single.nf"


def test_resume_checks_the_main_script_again(
    authed_client: TestClient,
    tmp_path: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The parent's entry script became a symlink: Resume refuses, as Launch would."""
    monkeypatch.setattr(resume, "processes_in", lambda path: [])
    root = scripts(tmp_path)
    response = launch(authed_client, root, main_script="main_cellpose.nf")
    assert response.status_code == 201, response.text
    run_id = response.json()["id"]
    make_run_dirs(settings.runs_root, run_id)
    session = "5f1c8a43-7f62-4a5e-9d4f-0a1b2c3d4e5f"

    def failed(conn: Any) -> None:
        conn.execute(update(runs).where(runs.c.id == run_id).values(state="failed"))
        conn.execute(
            update(launches).where(launches.c.run_id == run_id).values(engine_session_id=session)
        )

    writer.submit(failed).result()
    (root / "main_cellpose.nf").unlink()
    (root / "main_cellpose.nf").symlink_to(tmp_path / "elsewhere.nf")
    refused = authed_client.post(f"{RUNS}/{run_id}:relaunch", json={"mode": "resume"})
    assert fields(refused) == ["workflow.main_script"]
    assert len(table(writer, runs)) == 1  # no child


# --- The launch map --------------------------------------------------------------------------


def test_graph_draws_the_main_script(
    settings: Settings, writer: Writer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    drawn: list[Path] = []
    monkeypatch.setattr(bioflow, "metro_map", lambda path: drawn.append(path))
    root = scripts(tmp_path, main=True)
    client = graph_client(settings, writer)
    graph = "/api/v1/workflows:graph"
    found = client.get(graph, params={"location": str(root), "main_script": "main_cellpose.nf"})
    assert found.status_code == 200, found.text
    assert client.get(graph, params={"location": str(root)}).status_code == 200
    assert drawn == [root / "main_cellpose.nf", root / "main.nf"]
    refused = client.get(graph, params={"location": str(root), "main_script": "../x.nf"})
    assert fields(refused) == ["main_script"]
    too_long = client.get(graph, params={"location": str(root), "main_script": "x" * 253 + ".nf"})
    assert fields(too_long) == ["main_script"]
    # a main.nf that is a symlink is not handed to the tool
    (root / "main.nf").unlink()
    (root / "main.nf").symlink_to(tmp_path / "elsewhere.nf")
    assert client.get(graph, params={"location": str(root)}).status_code == 200
    assert drawn == [root / "main_cellpose.nf", root / "main.nf"]
