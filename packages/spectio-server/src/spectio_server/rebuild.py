"""The index rebuilt from the run directories (P1 Task 11, Assumption 21; dev-env §15.3, Where
data lives and "Server restart").

Each boot adds the run directories missing from the index: all of them when the database is
new. A run is added in one transaction, with its launch, so a boot interrupted part way leaves
whole runs only, and the next boot adds the rest; no completion mark is needed. What the run
directory holds decides the row:

- `launch/.spectio/launch-failed.json`: the run failed with that class;
- no `head.pid` (no head ever ran): `cancelled` under a cancel marker, else failed `head_lost`;
- else the run is `queued` (`cancelling` under a cancel marker), and its launch carries the
  head's native ID: the runner loop adopts the head and replays the spool from offset 0, and
  event IDs make the replay idempotent (Assumption 11).

Every directory is walked under §15.3 req. 10 (`rundir.private_dir`): a symlink, another user's
directory, a loose one or a name that is not a run ID is skipped and counted. The manifest is
parsed strictly (`extra="forbid"`), its run ID must be the directory's name, and every path is
derived from the run ID. Per-boot caps bound the work; what is left waits for the next boot.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, insert, select

from spectio.runner.local import read_head_pid
from spectio.runner.loop import CANCEL, LAUNCH_CLASSES, LAUNCH_FAILED
from spectio.runner.rundir import (
    MAX_SMALL_FILE,
    RUN_ID,
    RunManifest,
    check_launch_dir,
    private_dir,
    read_run_manifest,
    read_small,
    run_paths,
)
from spectio_server.ids import new_id
from spectio_server.projector.runs import failure_json
from spectio_server.store.schema import (
    environments,
    launches,
    principals,
    projects,
    run_inputs,
    runs,
    workflow_versions,
    workflows,
)
from spectio_server.store.writer import Writer

log = logging.getLogger(__name__)

MAX_RUNS = 1000  # run directories added per boot
MAX_BYTES = 64 * 1048576  # manifest bytes read per boot


@dataclass(frozen=True)
class Rebuilt:
    added: int  # runs added to the index
    skipped: int  # entries refused: not a run ID, not private, or a bad manifest
    deferred: int  # runs left for the next boot by the caps


@dataclass(frozen=True)
class _Found:
    manifest: RunManifest
    size: int
    native_id: str | None
    cancelled: bool
    failed: dict[str, Any] | None


def rebuild_index(
    writer: Writer, runs_root: Path, *, max_runs: int = MAX_RUNS, max_bytes: int = MAX_BYTES
) -> Rebuilt:
    """Add the run directories under `runs_root` that the index lacks, oldest first."""
    known = writer.submit(lambda conn: set(conn.execute(select(runs.c.id)).scalars())).result()
    with private_dir(runs_root) as fd:
        names = sorted(os.listdir(fd))
    added = skipped = deferred = used = 0
    for name in names:
        if name in known:
            continue
        if not RUN_ID.fullmatch(name):
            skipped += 1
            continue
        if added >= max_runs or used >= max_bytes:
            deferred += 1
            continue
        try:
            found = _read(runs_root, name)
        except (OSError, ValueError) as exc:  # pydantic's ValidationError is a ValueError
            log.warning("run directory %s skipped: %r", name, exc)
            skipped += 1
            continue
        used += found.size
        try:
            writer.submit(partial(_add, runs_root=runs_root, found=found)).result()
        except ValueError as exc:
            log.warning("run directory %s skipped: %s", name, exc)
            skipped += 1
            continue
        added += 1
    if skipped or deferred:
        log.warning(
            "index rebuild: %d runs added, %d entries skipped, %d left for the next boot",
            added,
            skipped,
            deferred,
        )
    return Rebuilt(added, skipped, deferred)


def _read(runs_root: Path, run_id: str) -> _Found:
    paths = run_paths(runs_root, run_id)
    manifest = read_run_manifest(paths.run_dir)
    size = len(manifest.model_dump_json())
    try:
        check_launch_dir(runs_root, run_id, paths.launch_dir)
        with private_dir(runs_root, run_id, "launch", ".spectio") as fd:
            raw = read_small(fd, LAUNCH_FAILED, cap=MAX_SMALL_FILE)
            cancelled = _exists(fd, CANCEL)
    except FileNotFoundError:  # the launch directory was never made: no head ran
        return _Found(manifest, size, None, False, None)
    failed = None
    if raw is not None:
        failed = json.loads(raw)
        if not isinstance(failed, dict):
            raise ValueError(f"{LAUNCH_FAILED} is not a JSON object")
    head = read_head_pid(paths.launch_dir)
    native_id = None if head is None else f"{head.pid}.{head.start}"  # LocalLauncher's form
    return _Found(manifest, size, native_id, cancelled, failed)


def _exists(dir_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _state(found: _Found) -> tuple[str, dict[str, Any] | None]:
    if found.failed is not None:
        class_ = found.failed.get("class")
        return "failed", failure_json(
            class_ if class_ in LAUNCH_CLASSES else "launch_error",
            str(found.failed.get("message"))[:4096],
        )
    if found.native_id is None:
        if found.cancelled:
            return "cancelled", None
        return "failed", failure_json("head_lost", "No head ran for this run (index rebuilt).")
    return ("cancelling" if found.cancelled else "queued"), None


def _first(conn: Connection, table: Any) -> str:
    found = conn.execute(select(table.c.id).order_by(table.c.created_at).limit(1)).scalar()
    if found is None:
        raise RuntimeError(f"no {table.name} row: the boot creates them first")
    return str(found)


def _add(conn: Connection, runs_root: Path, found: _Found) -> None:
    m = found.manifest
    now = datetime.now(UTC)
    mine = {"created_by": _first(conn, principals)}
    project = _first(conn, projects)
    source = "git" if m.workflow.revision else "local"
    workflow = conn.execute(
        select(workflows.c.id, workflows.c.engine).where(
            workflows.c.project_id == project,
            workflows.c.source == source,
            workflows.c.location == m.workflow.location,
        )
    ).one_or_none()
    if workflow is not None and workflow.engine != m.workflow.engine:
        # one workflows row per location (api §7), and its engine is the runs' (P1 Task 17)
        raise ValueError(f"{m.workflow.location} is already a {workflow.engine} workflow")
    if workflow is not None:
        workflow_id = workflow.id
    else:
        workflow_id = new_id("wfl")
        conn.execute(
            insert(workflows).values(
                id=workflow_id,
                project_id=project,
                location=m.workflow.location,
                source=source,
                engine=m.workflow.engine,
                created_at=now,
                **mine,
            )
        )
    version_id = new_id("wfv")
    conn.execute(
        insert(workflow_versions).values(
            id=version_id,
            workflow_id=workflow_id,
            revision=m.workflow.revision,
            created_at=now,
            **mine,
        )
    )
    state, failure = _state(found)
    paths = run_paths(runs_root, m.run_id)
    conn.execute(
        insert(runs).values(
            id=m.run_id,
            project_id=project,
            workflow_version_id=version_id,
            environment_id=_first(conn, environments),
            name=m.name,
            state=state,
            state_changed_at=now,
            failure=failure,
            launch_dir=str(paths.launch_dir),
            work_dir=str(paths.work_dir),
            created_at=m.created_at,
            **mine,
        )
    )
    conn.execute(
        insert(run_inputs).values(
            id=new_id("rin"),
            run_id=m.run_id,
            version=1,
            kind="params",
            content=m.params,
            created_at=now,
            **mine,
        )
    )
    conn.execute(
        insert(launches).values(
            id=new_id("lch"),
            run_id=m.run_id,
            n=1,
            launch_dir=str(paths.launch_dir),
            head_native_id=found.native_id,
            created_at=now,
            **mine,
        )
    )
