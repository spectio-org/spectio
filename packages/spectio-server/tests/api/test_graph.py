"""The workflow graph of issue #160 (api §5.10; spikes/metroflow/graph-contract.md): the feature
flag, the run graph from Snakemake's rule graphs and Nextflow's `onFlowBegin` DAG, a process's
outputs, and the Launch graph (rule files, BioFlow-Insight's metro map)."""

import gzip
import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from spectio.config import ServerOpts, Settings
from spectio.runner.rundir import run_paths
from spectio_server.graph import bioflow, document, static
from spectio_server.store.writer import Writer

from ..test_process_status import job, smk_run
from .conftest import FLAKY_RUN, SYNTHETIC, add_run, client_for, replay
from .test_failure import API, RUN, Run

DATA = Path(__file__).resolve().parents[1] / "data" / "graph"
FETCHNGS = DATA / "bioflow-insight-2.1.1_fetchngs_metro_map.json"
SYNTH_MAP = DATA / "bioflow-insight-2.1.1_synthetic_metro_map.json"
SMK_FIXTURE = "snakemake-9.27.1_checkpoint_flaky_retry.spool.jsonl"


def on(settings: Settings) -> Settings:
    return settings.model_copy(update={"server": ServerOpts(features=["graph_view"])})


def graph_client(settings: Settings, writer: Writer) -> TestClient:
    return client_for(on(settings), writer)


def got(client: TestClient, path: str) -> dict[str, Any]:
    found = client.get(f"{API}{path}")
    assert found.status_code == 200, found.text
    return found.json()  # type: ignore[no-any-return]


# --- The feature flag ------------------------------------------------------------------------


def test_features_off_by_default(settings: Settings, writer: Writer) -> None:
    client = client_for(settings, writer)
    assert got(client, "/features") == {"features": []}
    for path in (
        f"/runs/{RUN}/graph",
        f"/runs/{RUN}/processes/A/outputs",
        "/workflows:graph?location=/x",
        "/workflows:source?location=/x&name=A",
    ):
        found = client.get(f"{API}{path}")
        assert found.status_code == 404
        assert found.json()["type"] == "/problems/feature-disabled"


def test_features_on(settings: Settings, writer: Writer) -> None:
    assert got(graph_client(settings, writer), "/features") == {"features": ["graph_view"]}


def test_features_env(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    monkeypatch.setenv("SPECTIO_SERVER_FEATURES", "graph_view, ")
    assert Settings().server.features == ["graph_view"]
    monkeypatch.setenv("SPECTIO_SERVER_FEATURES", "nope")
    with pytest.raises(ValueError):
        Settings()


# --- The run graph: Snakemake ----------------------------------------------------------------


def test_snakemake_rulegraph_replayed(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """The T2 checkpoint run: its rule graph's links are the edges, the rules its nodes."""
    launch_id = add_run(writer, settings, FLAKY_RUN, "smk", engine="snakemake")
    replay(writer, tmp_path, launch_id, SMK_FIXTURE, FLAKY_RUN)
    doc = got(graph_client(settings, writer), f"/runs/{FLAKY_RUN}/graph")
    assert doc["version"] == 1 and doc["engine"] == "snakemake"
    assert doc["producer"] == "smk-rulegraph"
    ids = {n["id"] for n in doc["nodes"]}
    assert {"make_reads", "split", "merge", "all"} <= ids
    edges = {(e["source"], e["target"]) for e in doc["edges"]}
    assert ("make_reads", "split") in edges and ("merge", "all") in edges
    assert all(e["source"] in ids and e["target"] in ids for e in doc["edges"])
    node = next(n for n in doc["nodes"] if n["id"] == "make_reads")
    assert node["kind"] == "rule" and node["status"] and node["counts"]
    assert set(node["metrics"]) == {"duration_s", "cpu_mean", "mem_max", "failed"}
    assert node["first_start"] is not None
    assert next(n for n in doc["nodes"] if n["id"] == "split")["kind"] == "checkpoint"


def test_snakemake_no_rulegraph(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """With no rule graph yet: the rules, no edges, `stages-only`, not complete."""
    run = smk_run(settings, writer, tmp_path)
    writer.submit(
        lambda c: c.exec_driver_sql("DELETE FROM events WHERE type LIKE '%rulegraph'")
    ).result()
    job(run, 1, "make_reads")
    doc = got(graph_client(settings, writer), f"/runs/{RUN}/graph")
    assert doc["producer"] == "stages-only" and not doc["complete"] and doc["edges"] == []
    assert "make_reads" in {n["id"] for n in doc["nodes"]}


def test_snakemake_outputs(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """A rule's outputs: its jobs' `outputs`, `present` or `missing` in the launch directory,
    `removed` once a `temp_removed` named them."""
    run = smk_run(settings, writer, tmp_path)
    (run.paths.launch_dir / "reads").mkdir(parents=True)
    (run.paths.launch_dir / "reads" / "1.txt").write_text("x")
    job(run, 1, "make_reads", output=[str(run.paths.launch_dir / "reads" / "1.txt")])
    job(run, 2, "make_reads", output=[str(run.paths.launch_dir / "reads" / "2.txt")])
    run.push("snakemake.temp_removed", path=str(run.paths.launch_dir / "reads" / "2.txt"))
    client = graph_client(settings, writer)
    items = got(client, f"/runs/{RUN}/processes/make_reads/outputs")["items"]
    states = {i["path"]: (i["state"], i["root"], i["temp"]) for i in items}
    assert states == {
        "reads/1.txt": ("present", "launch", False),
        "reads/2.txt": ("removed", "launch", True),
    }
    assert all(i["task_id"] for i in items)
    assert client.get(f"{API}/runs/{RUN}/processes/nope/outputs").status_code == 404
    # the graph flags the rule as writing temporary files
    nodes = {n["id"]: n for n in got(client, f"/runs/{RUN}/graph")["nodes"]}
    assert nodes["make_reads"]["temp"] is True


def test_output_head(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """The first lines of a listed output: plain text as is, gzip inflated (capped, so a bomb
    costs 16 KiB), binary refused, and a path the process did not write is not found."""
    run = smk_run(settings, writer, tmp_path)
    reads = run.paths.launch_dir / "reads"
    reads.mkdir(parents=True)
    (reads / "a.txt").write_text("".join(f"line {i}\n" for i in range(100)))
    (reads / "a.fq.gz").write_bytes(gzip.compress(b"@r1\nACGT\n+\nIIII\n"))
    (reads / "bomb.gz").write_bytes(gzip.compress(b"A" * (64 << 20)))
    (reads / "b.bam").write_bytes(b"BAM\x01\x00\x00")
    names = ["a.txt", "a.fq.gz", "bomb.gz", "b.bam"]
    job(run, 1, "make_reads", output=[str(reads / n) for n in names])
    client = graph_client(settings, writer)
    items = got(client, f"/runs/{RUN}/processes/make_reads/outputs")["items"]
    assert {i["path"]: i["size"] for i in items}["reads/a.txt"] == 790
    task = items[0]["task_id"]

    def head(path: str) -> Any:
        return client.get(
            f"{API}/runs/{RUN}/processes/make_reads/outputs:head",
            params={"path": path, "task_id": task},
        )

    text = head("reads/a.txt").json()
    assert text["more"] and not text["gzip"] and text["text"].splitlines()[-1] == "line 39"
    fq = head("reads/a.fq.gz").json()
    assert fq == {"text": "@r1\nACGT\n+\nIIII", "more": False, "gzip": True}
    bomb = head("reads/bomb.gz").json()
    assert bomb["more"] and len(bomb["text"]) <= 16 << 10
    assert head("reads/b.bam").status_code == 422
    assert head("../../etc/passwd").status_code == 404
    assert head("reads/nope.txt").status_code == 404


# --- The run graph: Nextflow -----------------------------------------------------------------


def test_nextflow_without_dag(settings: Settings, writer: Writer, replayed_flaky: str) -> None:
    doc = got(graph_client(settings, writer), f"/runs/{replayed_flaky}/graph")
    assert doc["producer"] == "stages-only" and not doc["complete"] and doc["edges"] == []
    assert {"MAKE_READS", "ALIGN", "FINAL_REPORT"} <= {n["id"] for n in doc["nodes"]}
    assert all(n["kind"] == "process" for n in doc["nodes"])


def test_nextflow_dag(settings: Settings, writer: Writer) -> None:
    """`onFlowBegin`'s DAG: its edges, the processes with no task yet as idle nodes, and the
    qualified names' subworkflows as nested groups."""
    run = Run(settings, writer)
    names = ["PIPE:QC:FASTQC", "PIPE:QC:STATS", "PIPE:ALIGN"]
    dag = {"processes": names, "edges": [names[:2], names[1:], ["PIPE:ALIGN", "GHOST"]]}
    run.push("nextflow.onFlowBegin", dag=dag)
    run.push("nextflow.onTaskSubmit", process="PIPE:QC:FASTQC", tag="S1", attempt=1)
    doc = got(graph_client(settings, writer), f"/runs/{RUN}/graph")
    assert doc["producer"] == "nf-dag" and doc["complete"] and not doc["estimate"]
    assert {(e["source"], e["target"]) for e in doc["edges"]} == {
        ("PIPE:QC:FASTQC", "PIPE:QC:STATS"),
        ("PIPE:QC:STATS", "PIPE:ALIGN"),
    }
    nodes = {n["id"]: n for n in doc["nodes"]}
    assert set(nodes) == set(names)
    assert nodes["PIPE:ALIGN"]["status"] == "pending" and nodes["PIPE:ALIGN"]["counts"] == {}
    assert nodes["PIPE:QC:STATS"]["name"] == "STATS"
    assert nodes["PIPE:QC:STATS"]["subworkflow"] == "sub:PIPE:QC"
    groups = {g["id"]: g for g in doc["groups"]}
    assert groups["sub:PIPE:QC"]["parent"] == "sub:PIPE"
    assert groups["sub:PIPE"]["parent"] is None and groups["sub:PIPE"]["kind"] == "subworkflow"


def test_nextflow_dag_truncated(settings: Settings, writer: Writer) -> None:
    run = Run(settings, writer)
    run.push("nextflow.onFlowBegin", dag={"truncated": True})
    doc = got(graph_client(settings, writer), f"/runs/{RUN}/graph")
    assert doc["producer"] == "stages-only"


def test_nextflow_outputs(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """QC_STATS's outputs: the files published from its attempts' work directories, matched by
    the stored `attempts.work_dir`, which names the task and the attempt (CR-1)."""
    launch_id = add_run(writer, settings, FLAKY_RUN, "rnaseq-flaky")
    paths = run_paths(settings.runs_root, FLAKY_RUN)
    subs = {"<launch>/work": str(paths.work_dir), "<launch>": str(paths.launch_dir)}
    replay(
        writer,
        tmp_path,
        launch_id,
        "nextflow-26.10.4_plugin_flaky.spool.jsonl",
        FLAKY_RUN,
        subs,
        settings.runs_root,
    )
    client = graph_client(settings, writer)
    items = got(client, f"/runs/{FLAKY_RUN}/processes/QC_STATS/outputs")["items"]
    assert items and all(i["path"].endswith(".qc.json") for i in items)
    assert all(i["task_id"] and i["attempt_n"] for i in items)
    assert all(i["work_path"].endswith(".qc.json") and "_work" not in i for i in items)
    assert not got(client, f"/runs/{FLAKY_RUN}/processes/MAKE_READS/outputs")["items"]


# --- The pure document -----------------------------------------------------------------------


def test_metro_map_fetchngs() -> None:
    mapped = document.from_metro(json.loads(FETCHNGS.read_text()))
    name = "NFCORE_FETCHNGS:FETCHNGS:SRA_IDS_TO_RUNINFO"
    assert name in mapped["nodes"]
    info = mapped["nodes"][name]
    assert info["source"]["file"] == "modules/local/sra_ids_to_runinfo/main.nf"
    assert info["layout"] is not None
    sub = "sub:NFCORE_FETCHNGS:FETCHNGS:FASTQ_DOWNLOAD_PREFETCH_FASTERQDUMP_SRATOOLS"
    assert mapped["groups"][sub] == "!skip_fastq_download"
    assert all(":" in a and ":" in b for a, b in mapped["edges"])


def test_metro_map_synthetic_params() -> None:
    mapped = document.from_metro(json.loads(SYNTH_MAP.read_text()))
    assert "ALIGN" in mapped["nodes"]
    assert "verbosity" in mapped["nodes"]["ALIGN"]["params"]


def test_build_drops_dangling_edges_and_unknown_stages() -> None:
    doc = document.build(
        engine="snakemake",
        producer="smk-rulegraph",
        complete=True,
        nodes=[{"id": "a", "stage_id": "s1"}, {"id": "b", "stage_id": "gone"}],
        edges=[("a", "b"), ("a", "z")],
        stages=[{"id": "s1", "name": "One"}],
    )
    assert doc["edges"] == [{"source": "a", "target": "b", "condition": None}]
    assert [n["stage_id"] for n in doc["nodes"]] == ["s1", None]
    assert doc["groups"] == [
        {"id": "stage:s1", "kind": "stage", "name": "One", "parent": None, "condition": None}
    ]


# --- The Launch graph ------------------------------------------------------------------------


def test_launch_snakemake(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    pipeline = tmp_path / "smk"
    shutil.copytree(SYNTHETIC / "snakemake", pipeline)
    doc = got(graph_client(settings, writer), f"/workflows:graph?location={pipeline}")
    assert doc["engine"] == "snakemake" and doc["producer"] == "stages-only"
    ids = [n["id"] for n in doc["nodes"]]
    assert "make_reads" in ids and "all" in ids
    assert all(n["source"]["file"].endswith("Snakefile") for n in doc["nodes"])
    assert "status" not in doc["nodes"][0] or doc["nodes"][0]["status"] is None


def test_launch_nextflow_without_bioflow(
    settings: Settings, writer: Writer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bioflow, "available", lambda: None)
    pipeline = tmp_path / "nf"
    shutil.copytree(SYNTHETIC / "nextflow", pipeline)
    doc = got(graph_client(settings, writer), f"/workflows:graph?location={pipeline}")
    assert doc["producer"] == "stages-only" and doc["edges"] == []
    nodes = {n["id"]: n for n in doc["nodes"]}
    assert {"MAKE_READS", "ALIGN", "FINAL_REPORT"} <= set(nodes)
    assert nodes["ALIGN"]["source"]["file"] == "main.nf"
    assert nodes["ALIGN"]["stage_id"] is None  # bare names: detection needs qualified ones


def test_launch_nextflow_with_bioflow(
    settings: Settings, writer: Writer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BioFlow-Insight's map (its recorded output) gives edges, conditions and positions."""
    monkeypatch.setattr(bioflow, "metro_map", lambda _: json.loads(FETCHNGS.read_text()))
    pipeline = tmp_path / "nf"
    shutil.copytree(SYNTHETIC / "nextflow", pipeline)
    doc = got(graph_client(settings, writer), f"/workflows:graph?location={pipeline}")
    assert doc["producer"] == "bioflow-insight" and doc["edges"]
    assert doc["estimate"] and not doc["complete"]  # static edges, cycles included
    edges = {(e["source"], e["target"]): e["condition"] for e in doc["edges"]}
    fq, al = "NFCORE_FETCHNGS:FETCHNGS:FASTQDL", "NFCORE_FETCHNGS:FETCHNGS:ASPERA_CLI"
    assert (fq, al) in edges and (al, fq) in edges  # a cycle, kept
    assert edges[(fq, al)] == "!skip_fastq_download"
    node = next(n for n in doc["nodes"] if n["name"] == "SRA_FASTQ_FTP")
    assert node["subworkflow"] == "sub:NFCORE_FETCHNGS:FETCHNGS"
    assert node["condition"] == "!skip_fastq_download" and node["layout"]
    assert "process SRA_FASTQ_FTP" in node["code"]


def test_source_of_a_rule_and_a_process(
    settings: Settings, writer: Writer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The code of a rule or a process, found by its name (a Nextflow name by its last part):
    the file, the 1-based line and the block; an unknown or odd name is 404, never a path."""
    monkeypatch.setattr(bioflow, "available", lambda: None)
    client = graph_client(settings, writer)
    smk = tmp_path / "smk"
    shutil.copytree(SYNTHETIC / "snakemake", smk)
    block = got(client, f"/workflows:source?location={smk}&name=make_reads")
    assert block["file"] == "workflow/Snakefile" and block["line"] >= 1 and not block["truncated"]
    assert block["code"].startswith("rule make_reads:")
    assert "rule " not in block["code"].splitlines()[-1]  # the next rule is not part of it
    nf = tmp_path / "nf"
    shutil.copytree(SYNTHETIC / "nextflow", nf)
    block = got(client, f"/workflows:source?location={nf}&name=PIPE:ALIGN")
    assert block["file"] == "main.nf" and block["code"].lstrip().startswith("process ALIGN")
    assert block["code"].rstrip().endswith("}")
    for name in ("nope", "../etc/passwd", "ALIGN;x", "a" * 600):
        found = client.get(f"{API}/workflows:source", params={"location": str(nf), "name": name})
        assert found.status_code == 404, name


def test_source_search_is_linear(tmp_path: Path) -> None:
    """A `.nf` file of 1 MiB of newlines: the process search ends at once (SEC-SRC-01; `^\\s*`
    crossed newlines and went quadratic)."""
    (tmp_path / "main.nf").write_text("\n" * ((1 << 20) - 1))
    began = time.monotonic()
    assert static.definition(tmp_path, "nextflow", None, "ALIGN") is None
    assert time.monotonic() - began < 2


def test_launch_location_checked(settings: Settings, writer: Writer) -> None:
    found = graph_client(settings, writer).get(f"{API}/workflows:graph?location=/nonexistent")
    assert found.status_code == 422


@pytest.mark.skipif(bioflow.available() is None, reason="bioflow-insight and dot not installed")
def test_bioflow_real() -> None:  # pragma: no cover - only where the tool is installed
    metro = bioflow.metro_map(SYNTHETIC / "nextflow" / "main.nf")
    assert metro is not None and document.from_metro(metro)["edges"]


def _fake_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    """A fake `bioflow-insight` (and `dot`) first on PATH."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for name, text in (("bioflow-insight", body), ("dot", "exit 0")):
        exe = bin_ / name
        exe.write_text(f"#!/bin/sh\n{text}\n")
        exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_}:{os.environ['PATH']}")


def test_bioflow_timeout_kills_the_whole_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-160-01: a timeout kills the tool's children too, not only the tool."""
    pidfile = tmp_path / "child.pid"
    _fake_tool(tmp_path, monkeypatch, f"sleep 600 & echo $! > {pidfile}; sleep 600")
    started = time.monotonic()
    assert bioflow.metro_map(tmp_path / "main.nf", timeout_s=1) is None
    assert time.monotonic() - started < 10
    child = int(pidfile.read_text())
    time.sleep(0.2)
    status = Path(f"/proc/{child}/status")
    # gone, or a zombie waiting for a reaper that is not us (container PID 1)
    assert not status.exists() or "\nState:\tZ" in status.read_text()


def test_bioflow_one_at_a_time_and_private_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-160-01/-02: a second call while one runs falls back (None) at once; HOME is a
    private temporary directory, and no proxy or JAVA_TOOL_OPTIONS reaches the tool."""
    envfile = tmp_path / "env.txt"
    _fake_tool(tmp_path, monkeypatch, f"env > {envfile}; sleep 2")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid")
    monkeypatch.setenv("JAVA_TOOL_OPTIONS", "-Dx=y")
    first = threading.Thread(target=bioflow.metro_map, args=(tmp_path / "main.nf",))
    first.start()
    time.sleep(0.5)
    started = time.monotonic()
    assert bioflow.metro_map(tmp_path / "main.nf") is None
    assert time.monotonic() - started < 1
    first.join()
    env = dict(line.split("=", 1) for line in envfile.read_text().splitlines() if "=" in line)
    assert env["HOME"].startswith(tempfile.gettempdir()) and "spectio-bfi-" in env["HOME"]
    assert not {k for k in env if k.lower().endswith("_proxy") or k == "JAVA_TOOL_OPTIONS"}


def test_launch_walk_is_bounded(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """SEC-160-03: a huge tree beside main.nf is not walked in full; output dirs are skipped."""
    pipeline = tmp_path / "nf"
    shutil.copytree(SYNTHETIC / "nextflow", pipeline)
    hidden = pipeline / "results" / "late.nf"
    hidden.parent.mkdir()
    hidden.write_text("process HIDDEN {\n}\n")
    big = pipeline / "data"
    big.mkdir()
    for i in range(static.MAX_WALK_ENTRIES + 10):
        (big / f"f{i}").touch()
    started = time.monotonic()
    doc = got(graph_client(settings, writer), f"/workflows:graph?location={pipeline}")
    assert time.monotonic() - started < 10
    assert "HIDDEN" not in {n["id"] for n in doc["nodes"]}


def test_a_one_line_process_is_one_line() -> None:
    """`process X { ... }` on one line ends on that line, not on the next (code-review CR-9)."""
    from spectio_server.graph import static

    lines = ["process A { script: 'echo' }", "process B {", "}"]
    assert static._nf_block(lines, 0) == lines[:1]
    assert static._nf_block(lines, 1) == lines[1:]
