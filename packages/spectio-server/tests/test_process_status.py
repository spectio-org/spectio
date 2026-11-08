"""Process and rule states, checkpoints and outputs (P1 Task 34; ui-spec §5.2; api §5 and §7,
notes of 2026-11-07).

The Snakemake runs are fed with event lines in the shape the logger plugin sends (P1 Tasks 7
and 33), the rule files and `.spectio/rules.txt` written as the head writes them; the Nextflow
runs with `nf-spectio`'s hooks. `test_failure`'s `Run` drives both.
"""

import json
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from spectio.config import Settings
from spectio.runner.rundir import private_dir, write_file
from spectio.runner.types import HeadReport
from spectio_server.projector.ingest import apply_head_report
from spectio_server.store.schema import run_output_events
from spectio_server.store.writer import Writer

from .api.conftest import client_for, lone_host  # noqa: F401 - autouse: a lone host, any test host
from .api.test_failure import API, RUN, Run, write_private

SNAKEFILE = """\
rule all:
    input: "out/report.txt"

rule make_reads:
    output: "reads/{sample}.txt"

checkpoint split:
    output: directory("chunks")

rule align:
    output: "aligned/{chunk}.txt"

rule merge:
    output: "out/merged.txt"

rule report:
    output: "out/report.txt"

rule unused:
    output: "unused.txt"
"""
RULES = ["all", "make_reads", "split", "align", "merge", "report", "unused"]
RULEGRAPH = {"nodes": [{"rule": r} for r in ("make_reads", "split", "merge", "report", "all")]}


def smk_run(settings: Settings, writer: Writer, tmp_path: Path, plan: bool = True) -> Run:
    """A Snakemake run of SNAKEFILE: its rule files and `rules.txt`, `workflow_started`, the rule
    graph, and `run_info` planning make_reads (2 jobs), split, merge and all (report is up to
    date)."""
    pipeline = tmp_path / "pipeline"
    (pipeline / "workflow").mkdir(parents=True)
    main = pipeline / "workflow" / "Snakefile"
    main.write_text(SNAKEFILE)
    run = Run(settings, writer, "snakemake")
    writer.submit(
        lambda c: c.execute(text("UPDATE workflows SET location = :l"), {"l": str(pipeline)})
    ).result()
    with private_dir(settings.runs_root, RUN, "launch", ".spectio", create=True) as fd:
        write_file(fd, "rules.txt", "\n".join(RULES).encode() + b"\n")
    run.push("snakemake.workflow_started", snakefile_main=str(main), snakemake_version="9.27.1")
    run.push("snakemake.rulegraph", rulegraph=RULEGRAPH)
    if plan:
        stats = {"make_reads": 2, "split": 1, "merge": 1, "all": 1, "total": 5}
        run.push("snakemake.run_info", stats=stats)
    return run


def job(run: Run, jobid: int, rule: str, **info: Any) -> None:
    run.push("snakemake.job_info", jobid=jobid, rule_name=rule, wildcards={"n": str(jobid)}, **info)


def processes(client: TestClient) -> dict[str, dict[str, Any]]:
    found = client.get(f"{API}/runs/{RUN}/processes")
    assert found.status_code == 200, found.text
    return {p["process"]: p for p in found.json()["items"]}


def statuses(client: TestClient) -> dict[str, str]:
    return {name: p["status"] for name, p in processes(client).items()}


def summary(client: TestClient) -> dict[str, Any]:
    found = client.get(f"{API}/runs/{RUN}")
    assert found.status_code == 200, found.text
    return found.json()["summary"]  # type: ignore[no-any-return]


def checkpoint_running(run: Run) -> None:
    """make_reads done, the split checkpoint's job running."""
    for jobid in (1, 2):
        job(run, jobid, "make_reads")
        run.push("snakemake.job_finished", job_id=jobid)
    job(run, 3, "split", is_checkpoint=True)


# --- Snakemake (ui-spec §5.2, rules 1 to 3) ---------------------------------------------------


def test_status_awaiting_checkpoint(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """A defined rule with no planned job while a checkpoint has not finished waits for it; the
    checkpoint is one from its `checkpoint split:` line before its first job."""
    client = client_for(settings, writer)
    run = smk_run(settings, writer, tmp_path)
    found = processes(client)
    assert found["split"]["is_checkpoint"] and found["split"]["status"] == "pending"
    assert not found["merge"]["is_checkpoint"]
    checkpoint_running(run)
    assert statuses(client) == {
        "all": "pending",
        "make_reads": "done",
        "split": "running",
        "align": "awaiting_checkpoint",  # behind the checkpoint: in no plan yet
        "merge": "pending",
        "report": "up_to_date",
        "unused": "awaiting_checkpoint",  # it may yet come: Spectio cannot tell
    }


def test_status_pending_after_dag_update(
    settings: Settings, writer: Writer, tmp_path: Path
) -> None:
    """Once the checkpoint has ended and the DAG is updated, a defined rule with no job moves
    from Waiting for a checkpoint to Pending while the progress total exceeds the jobs known
    (ui-spec §5.2, CR-P3T34-02); a rule behind the checkpoint takes its state from its jobs."""
    client = client_for(settings, writer)
    run = smk_run(settings, writer, tmp_path)
    checkpoint_running(run)
    run.push("snakemake.job_finished", job_id=3)
    run.push("snakemake.dag_updated")
    run.push("snakemake.progress", done=3, total=8)
    found = statuses(client)
    assert found["align"] == "pending"  # its jobs are not known until their job_info
    assert found["unused"] == "pending"  # Spectio cannot tell which rule the 5 jobs are of
    job(run, 4, "align")
    assert statuses(client)["align"] == "running"


def test_status_not_needed(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """Once the checkpoint has ended, a defined rule in neither the rule graph, `run_info` nor
    any `job_info` is not needed when every job of the progress total is known, or once the
    run has ended."""
    client = client_for(settings, writer)
    run = smk_run(settings, writer, tmp_path)
    checkpoint_running(run)
    run.push("snakemake.job_finished", job_id=3)
    run.push("snakemake.dag_updated")
    run.push("snakemake.progress", done=3, total=4)
    job(run, 4, "align")
    assert statuses(client)["unused"] == "not_needed"  # the 4 jobs of the total are known
    run.push("snakemake.progress", done=3, total=8)
    assert statuses(client)["unused"] == "pending"
    report = HeadReport(
        state="exited", native_id="1", node="n", exit_code=0, ended=True, failure=None
    )
    writer.submit(lambda c: apply_head_report(c, run.launch_id, report)).result()
    assert statuses(client)["unused"] == "not_needed"  # the run ended


def test_status_up_to_date(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """In the rule graph and absent from `run_info`: up to date. With nothing to run (no
    `run_info`, the head exits 0), every rule is."""
    client = client_for(settings, writer)
    smk_run(settings, writer, tmp_path)
    found = statuses(client)
    assert found["report"] == "up_to_date"
    assert found["unused"] == "awaiting_checkpoint"  # the planned checkpoint has not ended


def test_status_nothing_to_be_done(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    client = client_for(settings, writer)
    run = smk_run(settings, writer, tmp_path, plan=False)
    assert set(statuses(client).values()) == {"pending"}  # before `run_info`, nothing is known
    report = HeadReport(
        state="exited", native_id="1", node="n", exit_code=0, ended=True, failure=None
    )
    writer.submit(lambda c: apply_head_report(c, run.launch_id, report)).result()
    assert set(statuses(client).values()) == {"up_to_date"}


def test_lower_bound(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """`summary.tasks.lower_bound` and `open_checkpoints` while the checkpoint job is planned
    or running; `dag_updates` counts `snakemake.dag_updated`."""
    client = client_for(settings, writer)
    run = smk_run(settings, writer, tmp_path)
    first = summary(client)
    assert first["tasks"]["lower_bound"] and first["open_checkpoints"] == ["split"]
    checkpoint_running(run)
    assert summary(client)["open_checkpoints"] == ["split"]
    assert processes(client)["merge"]["lower_bound"]
    run.push("snakemake.job_finished", job_id=3)
    run.push("snakemake.dag_updated")
    run.push("snakemake.progress", done=3, total=8)
    found = summary(client)
    assert not found["tasks"]["lower_bound"] and found["open_checkpoints"] == []
    assert found["dag_updates"] == 1 and found["tasks"]["total"] == 8
    assert not processes(client)["merge"]["lower_bound"]
    listed = client.get(f"{API}/runs").json()["items"][0]["summary"]
    assert listed["dag_updates"] == 1 and listed["open_checkpoints"] == []


# --- Nextflow (ui-spec §5.2, rule 4) ----------------------------------------------------------


def test_status_nf_no_tasks(settings: Settings, writer: Writer) -> None:
    """`onProcessTerminate` with no task since `onProcessCreate`: no task. A process still open
    with no task is pending; one with tasks takes their state."""
    client = client_for(settings, writer)
    run = Run(settings, writer)
    for name in ("ALIGN", "FILTERED", "LATER"):
        run.push("nextflow.onProcessCreate", process=name)
    run.nf_task(0, 1, "COMPLETED")
    run.push("nextflow.onProcessTerminate", process="ALIGN")
    run.push("nextflow.onProcessTerminate", process="FILTERED")
    found = processes(client)
    assert {n: p["status"] for n, p in found.items()} == {
        "ALIGN": "done",
        "FILTERED": "no_tasks",
        "LATER": "pending",
    }
    assert not any(p["is_checkpoint"] or p["lower_bound"] for p in found.values())
    run.push("nextflow.onFlowComplete", success=False)
    assert statuses(client)["LATER"] == "stopped"


# --- Pipeline order (FU-P3-82; ui-spec §4.4 note 2026-11-08) -----------------------------------


def pipeline_order(client: TestClient) -> list[str]:
    found = processes(client)
    return sorted(found, key=lambda name: found[name]["pipeline_order"])


def test_pipeline_order_follows_rulegraph_links(
    settings: Settings, writer: Writer, tmp_path: Path
) -> None:
    """With the rule graph's links, the rules come in topological order, ties broken by their
    order in the Snakefile; a rule outside the graph keeps its place among the ties. The list
    itself stays in the Snakefile's order."""
    client = client_for(settings, writer)
    run = smk_run(settings, writer, tmp_path)
    chain = ["make_reads", "split", "align", "merge", "report", "all"]
    links = [{"sourcerule": a, "targetrule": b} for a, b in pairwise(chain)]
    links.append({"sourcerule": "merge", "targetrule": "gone"})  # a rule the run no longer has
    graph = {"nodes": [{"rule": r} for r in chain], "links": links}
    run.push("snakemake.rulegraph", rulegraph=graph)
    assert list(processes(client)) == RULES
    assert pipeline_order(client) == [*chain, "unused"]


def test_pipeline_order_rule_missing_from_rulegraph(
    settings: Settings, writer: Writer, tmp_path: Path
) -> None:
    """A rule in no rule graph (one that joins the DAG after a checkpoint, as `align` on the demo
    run) comes after every graph rule, never first (FU-P3-90). A later graph that has it places
    it by its links: the links of every graph of the run are merged."""
    client = client_for(settings, writer)
    run = smk_run(settings, writer, tmp_path)
    first = ["make_reads", "split", "merge", "report", "all"]
    links = [{"sourcerule": a, "targetrule": b} for a, b in pairwise(first)]
    run.push("snakemake.rulegraph", rulegraph={"nodes": RULEGRAPH["nodes"], "links": links})
    assert pipeline_order(client) == [*first, "align", "unused"]
    later = [{"sourcerule": "split", "targetrule": "align"}]  # from a later graph of the run
    later.append({"sourcerule": "align", "targetrule": "merge"})
    nodes = [{"rule": r} for r in ("split", "align", "merge")]
    run.push("snakemake.rulegraph", rulegraph={"nodes": nodes, "links": later})
    chain = ["make_reads", "split", "align", "merge", "report", "all"]
    assert pipeline_order(client) == [*chain, "unused"]


def test_pipeline_order_without_links(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """A rule graph with no links: its rules in the order of the Snakefile, then the rules in no
    graph, in the same order."""
    client = client_for(settings, writer)
    smk_run(settings, writer, tmp_path)
    graph = ["all", "make_reads", "split", "merge", "report"]
    assert pipeline_order(client) == [*graph, "align", "unused"]
    ranks = sorted(p["pipeline_order"] for p in processes(client).values())
    assert ranks == list(range(len(RULES)))


def test_pipeline_order_cycle(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """A malformed graph with a cycle never loses a rule: the graph rules left come after the
    other graph rules, in Snakefile order, then the rules in no graph."""
    client = client_for(settings, writer)
    run = smk_run(settings, writer, tmp_path)
    links = [
        {"sourcerule": "merge", "targetrule": "split"},
        {"sourcerule": "split", "targetrule": "merge"},
        {"sourcerule": 3, "targetrule": None},  # not names: ignored
        {"sourcerule": ["merge"], "targetrule": {"rule": "all"}},
        "merge -> all",
    ]
    run.push("snakemake.rulegraph", rulegraph={"nodes": [], "links": links})
    first = ["all", "make_reads", "report"]  # smk_run's graph has the nodes, this one the links
    assert pipeline_order(client) == [*first, "split", "merge", "align", "unused"]


def test_pipeline_order_nextflow(settings: Settings, writer: Writer) -> None:
    """Nextflow: the order the processes were first seen."""
    client = client_for(settings, writer)
    run = Run(settings, writer)
    for name in ("ZETA", "ALPHA", "MID"):
        run.push("nextflow.onProcessCreate", process=name)
    assert pipeline_order(client) == ["ZETA", "ALPHA", "MID"]


# --- Outputs (ui-spec §5.2, temporary and protected outputs) ----------------------------------


def files(client: TestClient, task_id: str) -> dict[str, Any]:
    found = client.get(f"{API}/tasks/{task_id}/attempts/1/files")
    assert found.status_code == 200, found.text
    return found.json()  # type: ignore[no-any-return]


def test_outputs_temp_removed(settings: Settings, writer: Writer) -> None:
    """Each output of the job's `job_info` with its state; a removal or write-protection text is
    kept once, and only for an output of the run's jobs (SEC-P3T33-03); a path outside the
    launch directory is not kept."""
    client = client_for(settings, writer)
    run = Run(settings, writer, "snakemake")
    outputs = ["tmp/a.txt", "out/b.txt", "out/missing.txt", "<TBD>", "/etc/passwd"]
    job(run, 1, "make", output=outputs)
    write_private(run.paths.launch_dir / "out" / "b.txt", "b\n")
    run.push("snakemake.job_finished", job_id=1)
    for _ in range(2):  # Snakemake 9.27.1 logs some removals twice (T2 row 19)
        run.push("snakemake.temp_removed", path="tmp/a.txt")
    run.push("snakemake.protected", path="out/b.txt")
    run.push("snakemake.temp_removed", path="forged/x.txt")  # no job's output
    run.push("snakemake.temp_removed", path="out/missing.txt\x1b[2K")  # a control character
    job(run, 2, "make", output=["out/c.txt"])  # still running
    first, second = run.task_ids()

    listed = files(client, first)["outputs"]
    assert [o["path"] for o in listed] == ["tmp/a.txt", "out/b.txt", "out/missing.txt", "<TBD>"]
    by_path = {o["path"]: o for o in listed}
    removed = by_path["tmp/a.txt"]
    assert (removed["state"], removed["protected"]) == ("temp_removed", False)
    assert datetime.fromisoformat(removed["removed_at"]).year == 2026
    assert by_path["out/b.txt"] == {
        "path": "out/b.txt",
        "state": "present",
        "protected": True,
        "removed_at": None,
    }
    assert by_path["out/missing.txt"]["state"] == "absent"
    assert by_path["<TBD>"]["state"] == "tbd"
    assert files(client, second)["outputs"] == [
        {"path": "out/c.txt", "state": "not_yet", "protected": False, "removed_at": None}
    ]
    with writer.engine.connect() as conn:
        kept = conn.execute(
            select(run_output_events.c.path, run_output_events.c.kind).where(
                run_output_events.c.kind != "output"
            )
        ).all()
    assert sorted(map(tuple, kept)) == [("out/b.txt", "protected"), ("tmp/a.txt", "temp_removed")]


def test_outputs_nextflow_null_and_cleanup(settings: Settings, writer: Writer) -> None:
    """A Nextflow attempt has no outputs list; `cleanup` from `onFlowCreate` is the run's
    `engine_settings`; `clusterOptionsSet` is kept but not shown there."""
    client = client_for(settings, writer)
    run = Run(settings, writer)
    run.push("nextflow.onFlowCreate", cleanup=True, clusterOptionsSet=True)
    run.nf_task(0, 1, "COMPLETED")
    (task_id,) = run.task_ids()
    assert files(client, task_id)["outputs"] is None
    found = client.get(f"{API}/runs/{RUN}").json()
    assert found["engine_settings"] == {"cleanup": True, "notemp": None}


@pytest.mark.parametrize("engine", ["snakemake", "nextflow"])
def test_engine_settings_unknown(settings: Settings, writer: Writer, engine: str) -> None:
    client = client_for(settings, writer)
    Run(settings, writer, engine)
    found = client.get(f"{API}/runs/{RUN}").json()
    assert found["engine_settings"] == {"cleanup": None, "notemp": None}
    assert json.dumps(found).count("cluster") == 0
