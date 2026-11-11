"""The workflow graph routes of issue #160 (api §5.10), behind the `graph_view` feature.

`GET /features` lists the server's features, off by default (dev-env §15.1: 0.0.1 ships no
graph). With `graph_view` off, every graph route is `404 feature-disabled`.

- `GET /runs/{id}/graph`: the GraphDocument with its runtime overlay. Snakemake: the rule graphs
  the logger sent (`smk-rulegraph`). Nextflow: the `dag` of `onFlowBegin` (`nf-dag`), else the
  run's processes with no edges (`stages-only`).
- `GET /runs/{id}/processes/{name}/outputs`: the files of a process's tasks. Snakemake: its jobs'
  `outputs` (`attempts.outputs`), `removed` once `temp_removed` named them. Nextflow: the files
  `onFilePublish` published from its tasks' work directories (matched by task hash).
- `GET /runs/{id}/processes/{name}/outputs:head?path=&task_id=`: the first lines of one of those
  outputs, gunzipped when it is gzip, for a listed item only (never a path the client chose).
- `GET /workflows:graph`: the static graph for the Launch form (`graph.static`), the location
  checked as `/workflows:inspect` checks it.
- `GET /workflows:source`: the code of one process or rule (`graph.static.definition`), found by
  its name in the pipeline's files; the client names no path.
"""

import zlib
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import PurePosixPath
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response
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
from spectio_server.api.taskfiles import HEADERS, in_pool, load_attempt
from spectio_server.api.workflows import inspect_dir, resolve
from spectio_server.failure import dir_run_id
from spectio_server.files import results as files_results
from spectio_server.files.confine import (
    NotAllowed,
    NotFound,
    entry_confined,
    list_confined,
)
from spectio_server.files.pool import READ_TIMEOUT_S, Stalled
from spectio_server.files.redact import strip_escapes
from spectio_server.files.results import Tree, Where, check_rel, open_raw
from spectio_server.files.taskfiles import AttemptFiles, TaskDir, check_work_rel
from spectio_server.graph import bioflow, document, static
from spectio_server.store.schema import attempts, events, run_output_events, run_stages, tasks

router = APIRouter()

FEATURE = "graph_view"
FLOW_BEGIN = "spectio.engine.nextflow.onFlowBegin"
FILE_PUBLISH = "spectio.engine.nextflow.onFilePublish"
MAX_OUTPUTS = 500
WORK_ENTRIES = 64  # the most entries read at the top of one work directory
WORK_S = 2.0  # the most seconds the work directories of one listing are read for
WORK_TASKS = 40  # Nextflow: the most tasks whose work directory an output listing reads
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
            temp = _temp_rules(conn, run_id)
        else:
            temp = set()
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
                "temp": item["process"] in temp,
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


def _temp_rules(conn: Connection, run_id: str) -> set[str]:
    """The Snakemake rules a `temp_removed` named an output of: they write temporary files."""
    removed = set(
        conn.execute(
            select(run_output_events.c.path).where(
                run_output_events.c.run_id == run_id, run_output_events.c.kind == "temp_removed"
            )
        ).scalars()
    )
    if not removed:
        return set()
    rows = conn.execute(
        select(tasks.c.process_or_rule, attempts.c.outputs)
        .join(attempts, attempts.c.task_id == tasks.c.id)
        .where(tasks.c.run_id == run_id, attempts.c.outputs.is_not(None))
    ).all()
    return {
        r.process_or_rule
        for r in rows
        if any(p in removed for p in r.outputs or [] if isinstance(p, str))
    }


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
        r.work_dir.rstrip("/") + "/": (r.id, r.n, r.work_dir)
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
        work_path: str | None = source[len(owner[2].rstrip("/")) + 1 :]
        try:
            check_work_rel(
                work_path or ""
            )  # never a dot name (`.command.env`), as the workdir routes
        except NotAllowed:
            work_path = None
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
                # the copy in the attempt's work directory, previewed by the workdir routes
                "work_path": work_path,
            }
        )
    return found


def _stat(items: list[dict[str, Any]], trees: dict[str, Where]) -> None:
    """`present` or `missing`, and the size of a regular file, for each item whose root is
    known: read through the Results routes' tree, so their root and alias checks apply, and a
    publish link is followed into the work directory (its target's size, not the link's)."""
    for name, tree in trees.items():
        mine = [i for i in items if i["root"] == name and i["state"] == "unknown"]
        if not mine:
            continue
        try:
            with tree.roots() as (root, work):
                if root is None:
                    continue
                for item in mine:
                    try:
                        rel = check_rel(item["path"])
                        found = entry_confined(root, rel, work=work) if rel else None
                    except (NotAllowed, NotFound, OSError, ValueError):
                        continue
                    item["state"] = "missing" if found is None else "present"
                    item["size"] = found.size if found and found.type == "file" else None
        except (NotAllowed, NotFound, OSError):
            continue


def _work_files(work: list[tuple[str, int, AttemptFiles]], items: list[dict[str, Any]]) -> None:
    """Add the files at the top of each attempt's work directory that no publish event named:
    what a channel carries between two processes is mostly never published. Read below
    `TaskDir`'s root, so the workdir routes' confinement applies, with no link followed: the
    task's staged inputs are links, and they are not its outputs. Bounded: WORK_ENTRIES read
    per directory, MAX_OUTPUTS items, WORK_S seconds (SEC-160-12)."""
    published = {(i["task_id"], i.get("work_path")) for i in items}
    start = files_results.clock()
    for task_id, n, attempt in work:
        if len(items) >= MAX_OUTPUTS or files_results.clock() - start > WORK_S:
            return
        try:
            with TaskDir(attempt).roots() as (root, _):
                if root is None:
                    continue
                found = list_confined(root, PurePosixPath("."), WORK_ENTRIES)
        except (NotAllowed, NotFound, OSError):
            continue
        for e in found.entries:
            if e.type != "file" or not TaskDir.shown(e) or (task_id, e.name) in published:
                continue
            items.append(
                {
                    "path": e.name,
                    "root": "work",
                    "task_id": task_id,
                    "attempt_n": n,
                    "state": "present",
                    "temp": False,
                    "size": e.size,
                    "work_path": e.name,
                }
            )


def _latest_attempts(conn: Connection, run_id: str, name: str) -> list[tuple[str, int]]:
    """(task id, attempt) of each task's last attempt with a work directory, at most WORK_TASKS."""
    last: dict[str, int] = {}
    for task_id, n in conn.execute(
        select(tasks.c.id, attempts.c.n)
        .join(attempts, attempts.c.task_id == tasks.c.id)
        .where(
            tasks.c.run_id == run_id,
            tasks.c.process_or_rule == name,
            attempts.c.work_dir.is_not(None),
        )
        .order_by(tasks.c.id, attempts.c.n)
    ):
        last[task_id] = n
    return list(last.items())[:WORK_TASKS]


Work = list[tuple[str, int, AttemptFiles]]  # Nextflow: (task id, attempt, its files)


def _outputs(
    request: Request, run_id: str, name: str, *, look: bool = True
) -> tuple[list[dict[str, Any]], dict[str, Where], Work]:
    """The process's listed outputs, the trees they are read under and its tasks' last attempts;
    with `look`, each output stated and the work directories' files added (one pool job)."""
    settings: Settings = request.app.state.settings
    with read(request) as conn:
        run = run_row(conn, run_id)
        exists = conn.execute(
            select(tasks.c.id)
            .where(tasks.c.run_id == run_id, tasks.c.process_or_rule == name)
            .limit(1)
        ).first()
        if exists is None:
            raise not_found(f"no tasks of {name[:200]!r} in run {run_id}")
        work: Work = []
        if run.engine == "snakemake":
            items = _smk_outputs(conn, run, name)
        else:
            items = _nf_outputs(conn, run, name)
            for t, n in _latest_attempts(conn, run_id, name):
                if (a := load_attempt(conn, t, n, settings.runs_root)) is not None:
                    work.append((t, n, a))
    items = items[:MAX_OUTPUTS]  # a checkpoint's `<TBD>` stays `unknown`
    trees: dict[str, Where] = {}
    run_dir = dir_run_id(run)
    try:
        trees["launch"] = Where(
            settings.runs_root, run_dir, str(run_paths(settings.runs_root, run_dir).launch_dir)
        )
    except ValueError:
        pass
    if results_of(run):
        trees["results"] = Where(settings.runs_root, run_dir, str(results_of(run)))

    def stated() -> None:
        _stat(items, trees)
        _work_files(work, items)

    if look:
        try:
            request.app.state.files.run(stated, READ_TIMEOUT_S)
        except Stalled:
            pass  # the states stay `unknown`
    return items[:MAX_OUTPUTS], trees, work


@router.get("/runs/{run_id}/processes/{name}/outputs", response_model=models.ProcessOutputs)
def process_outputs(request: Request, run_id: str, name: str) -> Response:
    require_graph(request)
    items, _, _ = _outputs(request, run_id, name)
    body = models.ProcessOutputs.model_validate({"items": items})
    return Response(body.model_dump_json(), media_type="application/json", headers=HEADERS)


HEAD_RAW = 256 << 10  # the most bytes read from the file for a head
HEAD_TEXT = 16 << 10  # the most text a head returns, gunzipped or not
HEAD_LINES = 40
GZIP = (".gz", ".bgz")


def _head_of(raw: bytes, gz: bool, cut: bool) -> tuple[str, bool] | None:
    """The first lines of `raw` as text and whether the file has more; None for binary. A gzip
    stream (several members for bgzip) is inflated up to HEAD_TEXT only, so a small file that
    inflates to gigabytes costs HEAD_TEXT bytes."""
    # `cut`: the read stopped before the file's end
    if gz:
        out, data = b"", raw
        try:
            while data and len(out) <= HEAD_TEXT:
                d = zlib.decompressobj(wbits=31)
                out += d.decompress(data, HEAD_TEXT + 1 - len(out))
                if not d.eof:
                    break
                data = d.unused_data
        except zlib.error:
            if not out:
                return None
        raw = out
    cut = cut or len(raw) > HEAD_TEXT
    if b"\x00" in raw[:HEAD_TEXT]:
        return None
    lines = strip_escapes(raw[:HEAD_TEXT].decode("utf-8", "replace")).split("\n")
    if (cut and len(lines) > 1) or lines[-1] == "":
        lines.pop()  # never a line cut in the middle, nor the empty one after the last newline
    more = cut or len(lines) > HEAD_LINES
    return "\n".join(lines[:HEAD_LINES]).rstrip("\n"), more


@router.get("/runs/{run_id}/processes/{name}/outputs:head", response_model=models.OutputHead)
def output_head(request: Request, run_id: str, name: str, path: str, task_id: str) -> Response:
    """The first lines of one of the process's outputs (api §5.10), read only through the trees
    of the Results and workdir routes, so their rules apply (dev-env §15.3 req. 13 and 14): a
    listed output of the launch or results directory, or a file at the top of the work
    directory of one of the process's tasks, never a name that starts with `.`."""
    require_graph(request)
    items, trees, work = _outputs(request, run_id, name, look=False)
    item = next((i for i in items if i["path"] == path and i["task_id"] == task_id), None)
    latest = next((a for t, _, a in work if t == task_id), None)
    tree: Tree
    try:
        if item is not None and item.get("work_path") and item["attempt_n"] is not None:
            with read(request) as conn:  # the attempt that published it
                attempt = load_attempt(
                    conn, task_id, item["attempt_n"], request.app.state.settings.runs_root
                )
            if attempt is None:
                raise not_found("no such attempt")
            tree, rel = TaskDir(attempt), check_work_rel(item["work_path"])
        elif item is not None and item["root"] in trees:
            tree, rel = trees[item["root"]], check_rel(item["path"])
        elif item is None and latest is not None and "/" not in path:
            # a file of the work-directory listing: one name, at the top
            tree, rel = TaskDir(latest), check_work_rel(path)
        elif item is None:
            raise not_found("not an output of this process")
        else:
            raise NotAllowed("its folder is not known")
        if rel is None:
            raise NotAllowed("not a file")
    except NotAllowed as exc:
        raise Problem(422, "file-not-allowed", "File not allowed", str(exc)) from None
    gz = rel.name.lower().endswith(GZIP)

    def take() -> tuple[bytes, bool]:
        raw = open_raw(tree, rel, None, HEAD_RAW if gz else HEAD_TEXT + 1)
        return raw.first, raw.size > len(raw.first)

    raw, cut = in_pool(request, take, missing="not-found")
    head = _head_of(raw, gz, cut)
    if head is None:
        raise Problem(422, "not-text", "Not text", "a binary file has no head to show")
    body = models.OutputHead(text=head[0], more=head[1], gzip=gz)
    return Response(body.model_dump_json(), media_type="application/json", headers=HEADERS)


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


@router.get("/workflows:source", response_model=models.SourceBlock)
def workflow_source(
    request: Request, location: str, name: str, revision: str | None = None
) -> dict[str, Any]:
    require_graph(request)
    settings: Settings = request.app.state.settings
    if len(name) > 512:
        raise not_found("no such process or rule in the pipeline's code")
    resolved = resolve(settings.data_dir, location, revision)
    found = inspect_dir(resolved.directory, resolved.default_name)
    root = resolved.directory
    engine = found.engine
    if engine not in ("snakemake", "nextflow"):
        raise not_found("no single engine found in the pipeline")
    entry = next((f for f in found.engine_files if "Snakefile" in f), None)
    block = _in_pool(request, lambda: static.definition(root, engine, entry, name) or {})
    if not block:
        raise not_found("no such process or rule in the pipeline's code")
    return block
