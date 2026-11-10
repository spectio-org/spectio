"""The workflow graph routes of issue #160 (api §5.8), behind the `graph_view` feature.

`GET /features` lists the server's features, off by default (dev-env §15.1: 0.0.1 ships no
graph). With `graph_view` off, every graph route is `404 feature-disabled`.

- `GET /runs/{id}/graph`: the GraphDocument with its runtime overlay. Snakemake: the rule graphs
  the logger sent (`smk-rulegraph`). Nextflow: the `dag` of `onFlowBegin` (`nf-dag`), else the
  run's processes with no edges (`stages-only`).
- `GET /runs/{id}/processes/{name}/outputs`: the files of a process's tasks. Snakemake: its jobs'
  `outputs` (`attempts.outputs`), `removed` once `temp_removed` named them. Nextflow: the files
  `onFilePublish` published from its tasks' work directories (matched by task hash).
- `GET /workflows:graph`: the static graph for the Launch form (`graph.static`), the location
  checked as `/workflows:inspect` checks it.
"""

import os
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import Connection, Row, select

from spectio.config import Settings
from spectio.runner.rundir import run_paths
from spectio_server.api import models
from spectio_server.api.problems import Problem, not_found
from spectio_server.api.runs_read import (
    RULEGRAPH,
    context,
    process_items,
    read,
    results_of,
    run_row,
)
from spectio_server.api.workflows import inspect_dir, resolve
from spectio_server.failure import dir_run_id
from spectio_server.files.confine import NotAllowed, NotFound, open_root, safe_rel, stat_confined
from spectio_server.files.pool import READ_TIMEOUT_S, Stalled
from spectio_server.graph import bioflow, document, static
from spectio_server.store.schema import attempts, events, run_output_events, run_stages, tasks

router = APIRouter()

FEATURE = "graph_view"
FLOW_BEGIN = "spectio.engine.nextflow.onFlowBegin"
FILE_PUBLISH = "spectio.engine.nextflow.onFilePublish"
MAX_OUTPUTS = 500
OPEN = ("pending", "submitted", "running")
TERMINAL = ("succeeded", "failed", "cancelled")


def require_graph(request: Request) -> None:
    settings: Settings = request.app.state.settings
    if FEATURE not in settings.server.features:
        raise Problem(404, "feature-disabled", "Not found", f"the {FEATURE} feature is off")


@router.get("/features", response_model=models.Features)
def features(request: Request) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    return {"features": list(dict.fromkeys(settings.server.features))}


# --- The run's graph -------------------------------------------------------------------------


def _timing(conn: Connection, run_id: str, jobs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Per process: its first attempt's record time, and its last end (the record time of each
    ended task's last attempt plus its measured elapsed time), None while a task is open or
    unmeasured. Record times are the server's, a few seconds after the engine's."""
    rows = conn.execute(
        select(tasks.c.id, tasks.c.process_or_rule, tasks.c.state, attempts.c.created_at)
        .join(attempts, attempts.c.task_id == tasks.c.id)
        .where(tasks.c.run_id == run_id)
    ).all()
    first: dict[str, datetime] = {}
    last: dict[str, datetime] = {}
    latest: dict[str, datetime] = {}  # task → its last attempt's record time
    for task_id, process, _, at in rows:
        first[process] = min(first.get(process, at), at)
        latest[task_id] = max(latest.get(task_id, at), at)
    open_: set[str] = set()
    for task_id, process, state, _ in rows:
        if state in OPEN:
            open_.add(process)
            continue
        elapsed = ((jobs.get(task_id) or {}).get("efficiency") or {}).get("elapsed_s")
        if elapsed is None:
            continue
        end = latest[task_id] + timedelta(seconds=float(elapsed))
        last[process] = max(last.get(process, end), end)
    return {p: (first[p], None if p in open_ else last.get(p)) for p in first}


def _iso(at: datetime | None) -> str | None:
    return None if at is None else at.isoformat()


def _metrics(item: dict[str, Any], span: tuple[datetime, datetime | None] | None) -> dict[str, Any]:
    eff = item["efficiency"]
    duration = None
    if span is not None and span[1] is not None:
        duration = round((span[1] - span[0]).total_seconds(), 3)
    elif eff["used"]["elapsed_s_max"] is not None:
        duration = float(eff["used"]["elapsed_s_max"])
    return {
        "duration_s": duration,
        "cpu_mean": eff["cpu_mean"],
        "mem_max": eff["mem_max"],
        "failed": item["counts"].get("failed", 0),
    }


def _flow_begin(conn: Connection, run_id: str) -> Any:
    return conn.execute(
        select(events.c.payload)
        .where(events.c.run_id == run_id, events.c.type == FLOW_BEGIN)
        .order_by(events.c.seq)
        .limit(1)
    ).scalar()


@router.get("/runs/{run_id}/graph", response_model=models.GraphDocument)
def run_graph(request: Request, run_id: str) -> dict[str, Any]:
    require_graph(request)
    with read(request) as conn:
        run = run_row(conn, run_id)
        items, jobs = process_items(conn, run, context(request))
        stages = conn.execute(
            select(run_stages.c.stage_id, run_stages.c.name)
            .where(run_stages.c.run_id == run_id)
            .order_by(run_stages.c.position)
        ).all()
        timing = _timing(conn, run_id, jobs)
        if run.engine == "snakemake":
            graphs = [
                g
                for g in (
                    (p or {}).get("rulegraph")
                    for p in conn.execute(
                        select(events.c.payload)
                        .where(events.c.run_id == run_id, events.c.type == RULEGRAPH)
                        .order_by(events.c.seq)
                    ).scalars()
                )
                if isinstance(g, dict)
            ]
            dag = None
        else:
            graphs, dag = [], document.nf_dag(_flow_begin(conn, run_id))
    nodes = []
    for item in items:
        span = timing.get(item["process"])
        kind = {"kind": "checkpoint"} if item["is_checkpoint"] else {}
        nodes.append(
            kind
            | {
                "id": item["process"],
                "stage_id": item["stage_id"],
                "status": item["status"],
                "counts": item["counts"],
                "retries": item["retries"],
                "pipeline_order": item["pipeline_order"],
                "metrics": _metrics(item, span),
                "first_start": _iso(span[0]) if span else None,
                "last_end": _iso(span[1]) if span else None,
            }
        )
    known = {n["id"] for n in nodes}
    if run.engine == "snakemake":
        edges = document.rulegraph_edges(graphs)
        producer = "smk-rulegraph" if graphs else "stages-only"
        complete = bool(graphs) and not (items and items[0]["lower_bound"])
    elif dag is not None:
        processes, edges = dag
        idle = "no_tasks" if run.state in TERMINAL else "pending"
        order = len(nodes)
        for name in processes:
            if name not in known:
                nodes.append(_idle_node(name, idle, order))
                order += 1
        producer, complete = "nf-dag", True
    else:
        edges, producer, complete = [], "stages-only", False
    return document.build(
        engine=run.engine or "nextflow",
        producer=producer,
        complete=complete,
        nodes=nodes,
        edges=edges,
        stages=[{"id": s.stage_id, "name": s.name} for s in stages],
    )


def _idle_node(name: str, status: str, order: int) -> dict[str, Any]:
    """A process of the DAG with no task yet."""
    return {
        "id": name,
        "stage_id": None,
        "status": status,
        "counts": {},
        "retries": 0,
        "pipeline_order": order,
        "metrics": {"duration_s": None, "cpu_mean": None, "mem_max": None, "failed": 0},
        "first_start": None,
        "last_end": None,
    }


# --- A process's outputs ---------------------------------------------------------------------


def _smk_outputs(conn: Connection, run: Row[Any], name: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        select(tasks.c.id, attempts.c.n, attempts.c.launch_n, attempts.c.outputs)
        .join(attempts, attempts.c.task_id == tasks.c.id)
        .where(tasks.c.run_id == run.id, tasks.c.process_or_rule == name)
        .order_by(tasks.c.id, attempts.c.launch_n, attempts.c.n)
    ).all()
    last: dict[str, Any] = {}
    for row in rows:
        last[row.id] = row  # ordered: the last attempt of each task wins
    removed = set(
        conn.execute(
            select(run_output_events.c.path).where(
                run_output_events.c.run_id == run.id, run_output_events.c.kind == "temp_removed"
            )
        ).scalars()
    )
    found = []
    for task_id, row in last.items():
        for path in row.outputs or []:
            if not isinstance(path, str):
                continue
            found.append(
                {
                    "path": path,
                    "root": "launch",
                    "task_id": task_id,
                    "attempt_n": row.n,
                    "state": "removed" if path in removed else "unknown",
                    "temp": path in removed,
                }
            )
    return found


def _nf_outputs(conn: Connection, run: Row[Any], name: str) -> list[dict[str, Any]]:
    """The files the process's attempts published: a publish event's `source` lies in an
    attempt's work directory (`attempts.work_dir`, any `-w`), which names its task and attempt."""
    dirs = {
        r.work_dir.rstrip("/") + "/": (r.id, r.n)
        for r in conn.execute(
            select(tasks.c.id, attempts.c.n, attempts.c.work_dir)
            .join(attempts, attempts.c.task_id == tasks.c.id)
            .where(
                tasks.c.run_id == run.id,
                tasks.c.process_or_rule == name,
                attempts.c.work_dir.is_not(None),
            )
        )
    }
    if not dirs:
        return []
    mine = events.c.run_id == run.id
    results = results_of(run)
    found = []
    for payload in conn.execute(
        select(events.c.payload).where(mine, events.c.type == FILE_PUBLISH).order_by(events.c.seq)
    ).scalars():
        p = payload or {}
        source, target = p.get("source"), p.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        owner = next((v for d, v in dirs.items() if source.startswith(d)), None)
        if owner is None:
            continue
        path, root = target, "absolute"
        if results and target.startswith(results.rstrip("/") + "/"):
            path, root = target[len(results.rstrip("/")) + 1 :], "results"
        found.append(
            {
                "path": path,
                "root": root,
                "task_id": owner[0],
                "attempt_n": owner[1],
                "state": "unknown",
                "temp": False,
            }
        )
    return found


def _stat(items: list[dict[str, Any]], roots: dict[str, str]) -> None:
    """`present` or `missing` for each item whose root is known, read confined to that root."""
    for root_name, root_path in roots.items():
        mine = [i for i in items if i["root"] == root_name and i["state"] == "unknown"]
        if not mine:
            continue
        try:
            root = open_root(root_path)
        except (NotAllowed, NotFound, OSError):
            continue
        try:
            for item in mine:
                try:
                    found = stat_confined(root, safe_rel(item["path"]))
                except (NotAllowed, NotFound, OSError, ValueError):
                    continue
                item["state"] = "missing" if found is None else "present"
        finally:
            os.close(root.fd)


@router.get("/runs/{run_id}/processes/{name}/outputs", response_model=models.ProcessOutputs)
def process_outputs(request: Request, run_id: str, name: str) -> dict[str, Any]:
    require_graph(request)
    with read(request) as conn:
        run = run_row(conn, run_id)
        exists = conn.execute(
            select(tasks.c.id)
            .where(tasks.c.run_id == run_id, tasks.c.process_or_rule == name)
            .limit(1)
        ).first()
        if exists is None:
            raise not_found(f"no tasks of {name[:200]!r} in run {run_id}")
        if run.engine == "snakemake":
            items = _smk_outputs(conn, run, name)
        else:
            items = _nf_outputs(conn, run, name)
    items = items[:MAX_OUTPUTS]  # a checkpoint's `<TBD>` stays `unknown`
    roots: dict[str, str] = {}
    settings: Settings = request.app.state.settings
    try:
        roots["launch"] = str(run_paths(settings.runs_root, dir_run_id(run)).launch_dir)
    except ValueError:
        pass
    if results_of(run):
        roots["results"] = str(results_of(run))
    try:
        request.app.state.files.run(lambda: _stat(items, roots), READ_TIMEOUT_S)
    except Stalled:
        pass  # the states stay `unknown`
    return {"items": items}


# --- Before a run: the Launch form -----------------------------------------------------------


def _in_pool(request: Request, build: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """The pipeline's files read in the file pool, so a stalled mount answers 503 (SEC-160-03)."""
    try:
        return request.app.state.files.run(build, READ_TIMEOUT_S)  # type: ignore[no-any-return]
    except Stalled as exc:
        raise Problem(503, "runner-offline", "File system not answering", str(exc)) from None


@router.get("/workflows:graph", response_model=models.GraphDocument)
def workflow_graph(request: Request, location: str, revision: str | None = None) -> dict[str, Any]:
    require_graph(request)
    settings: Settings = request.app.state.settings
    resolved = resolve(settings.data_dir, location, revision)
    found = inspect_dir(resolved.directory, resolved.default_name)
    root = resolved.directory
    if found.engine == "snakemake":
        entry = next(f for f in found.engine_files if "Snakefile" in f)
        return _in_pool(request, lambda: static.snakemake_graph(root, entry))
    if found.engine == "nextflow":
        metro = bioflow.metro_map(root / "main.nf")  # its own timeout, one at a time
        return _in_pool(request, lambda: static.nextflow_graph(root, found.name, metro))
    raise Problem(
        422,
        "validation-failed",
        "Validation failed",
        "no single engine found in the pipeline",
        errors=[{"field": "location", "message": "neither or both of main.nf and a Snakefile"}],
    )
