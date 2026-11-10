"""The rows of one run, shared by `POST /runs` and the index rebuild (P1 Tasks 11 and 17).

`insert_run` finds or creates the location's `workflows` row (one per location, with one engine:
api §7), then adds its version, the run, its parameters (`run_inputs.kind = params`) and
launch 1. The launch endpoint adds its `launch` command; the rebuild gives the state it read.
"""

from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import Connection, insert, null, select

from spectio.environments import DefaultResources, run_column
from spectio.runner.observed import ObservedRun
from spectio.runner.rundir import RunManifest, run_paths
from spectio_server.api.extras import KeptConfig, column
from spectio_server.files.results import results_dir
from spectio_server.ids import new_id
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
from spectio_server.store.writer import note_change


class EngineConflict(ValueError):
    """The location already has a `workflows` row of the other engine."""

    def __init__(self, location: str, engine: str) -> None:
        super().__init__(f"{location} is already a {engine} workflow")
        self.engine = engine


def first(conn: Connection, table: Any) -> str:
    """The oldest row's ID: the one principal, project and environment of 0.0.1."""
    found = conn.execute(select(table.c.id).order_by(table.c.created_at).limit(1)).scalar()
    if found is None:
        raise RuntimeError(f"no {table.name} row: the boot creates them first")
    return str(found)


def _workflow_id(
    conn: Connection,
    project: str,
    source: str,
    location: str,
    engine: str,
    name: str | None,
    mine: dict[str, Any],
) -> str:
    """The location's `workflows` row, created when missing (one per location, one engine)."""
    workflow = conn.execute(
        select(workflows.c.id, workflows.c.engine).where(
            workflows.c.project_id == project,
            workflows.c.source == source,
            workflows.c.location == location,
        )
    ).one_or_none()
    if workflow is not None and workflow.engine != engine:
        raise EngineConflict(location, workflow.engine)
    if workflow is not None:
        return str(workflow.id)
    workflow_id = new_id("wfl")
    conn.execute(
        insert(workflows).values(
            id=workflow_id,
            project_id=project,
            name=name,
            location=location,
            source=source,
            engine=engine,
            **mine,
        )
    )
    return workflow_id


def insert_run(
    conn: Connection,
    m: RunManifest,
    *,
    source: str,
    runs_root: Path,
    now: datetime,
    state: str,
    origin: str | None = None,
    workflow_name: str | None = None,
    workflow_version: str | None = None,
    failure: dict[str, Any] | None = None,
    native_id: str | None = None,
    default_outdir: str | None = None,
) -> str:
    """Insert the run of manifest `m` and its launch 1; return the launch's ID. A Resume's child
    (`m.parent_run_id`, P1 Task 30) runs in its lineage's directories: those of its parent's row,
    or, when the rebuild finds no such row, the parent's own. Its results directory (P1 Task 31)
    follows from its launch directory and its parameters, `default_outdir` standing for a
    Nextflow `outdir` it does not set (the schema's default); a child's is its parent's row's.
    Its `environment` is the manifest's snapshot, through the validators (FU-P3-86a)."""
    mine = {"created_at": now, "created_by": first(conn, principals)}
    project = first(conn, projects)
    engine = m.workflow.engine
    workflow_id = _workflow_id(
        conn, project, source, m.workflow.location, engine, workflow_name, mine
    )
    version_id, launch_id = new_id("wfv"), new_id("lch")
    conn.execute(
        insert(workflow_versions).values(
            id=version_id,
            workflow_id=workflow_id,
            revision=m.workflow.revision,
            version=workflow_version,
            **mine,
        )
    )
    paths = run_paths(runs_root, m.run_id)
    launch_dir, work_dir = str(paths.launch_dir), str(paths.work_dir)
    lineage: dict[str, Any] = {}
    results = None
    if m.parent_run_id is not None:
        parent = conn.execute(
            select(runs.c.lineage_id, runs.c.launch_dir, runs.c.work_dir, runs.c.results_dir).where(
                runs.c.id == m.parent_run_id
            )
        ).one_or_none()
        if parent is not None and parent.launch_dir and parent.work_dir:
            root, launch_dir, work_dir = parent.lineage_id, parent.launch_dir, parent.work_dir
            results = parent.results_dir  # a Resume changes no parameter (CR-P3T31-04)
        else:
            root, own = None, run_paths(runs_root, m.parent_run_id)
            launch_dir, work_dir = str(own.launch_dir), str(own.work_dir)
        lineage = {
            "parent_run_id": m.parent_run_id,
            "lineage_id": root or m.parent_run_id,
            "relaunch_mode": "resume",
        }
    conn.execute(
        insert(runs).values(
            id=m.run_id,
            project_id=project,
            workflow_version_id=version_id,
            environment_id=first(conn, environments),
            name=m.name,
            state=state,
            state_changed_at=now,
            failure=null() if failure is None else failure,  # SQL NULL, not JSON null
            origin=origin,
            launch_dir=launch_dir,
            work_dir=work_dir,
            results_dir=results
            or results_dir(engine, m.run_id, runs_root, launch_dir, m.params, default_outdir),
            environment=run_column(m.environment),
            default_resources=column(DefaultResources, m.default_resources),
            config_file=column(KeptConfig, m.config_file),
            **lineage,
            **{**mine, "created_at": m.created_at},
        )
    )
    note_change(conn, m.run_id)  # a new run is a change for the stream (CR-P3T18-01)
    conn.execute(
        insert(run_inputs).values(
            id=new_id("rin"), run_id=m.run_id, version=1, kind="params", content=m.params, **mine
        )
    )
    conn.execute(
        insert(launches).values(
            id=launch_id,
            run_id=m.run_id,
            n=1,
            launch_dir=launch_dir,
            head_native_id=native_id,
            **mine,
        )
    )
    return launch_id


def insert_observed_run(conn: Connection, run: ObservedRun, now: datetime) -> None:
    """Insert a run started from a terminal (P1 Task 25, architecture §13.8), `queued` with
    origin `cli-observed`, and its launch 1 with the pointer's head fields and no native ID:
    no launcher ever adopts it. Its workflow is its launch directory (the pipeline is not in the
    pointer); it has no parameters, work directory or results directory in 0.0.1. Raises
    EngineConflict when that directory is a workflow of the other engine."""
    mine = {"created_at": now, "created_by": first(conn, principals)}
    project = first(conn, projects)
    workflow_id = _workflow_id(conn, project, "local", run.launch_dir, run.engine, None, mine)
    version_id = new_id("wfv")
    conn.execute(insert(workflow_versions).values(id=version_id, workflow_id=workflow_id, **mine))
    conn.execute(
        insert(runs).values(
            id=run.run_id,
            project_id=project,
            workflow_version_id=version_id,
            environment_id=first(conn, environments),
            name=f"{PurePosixPath(run.launch_dir).name or 'terminal'}-{run.run_id[-6:]}",
            state="queued",
            state_changed_at=now,
            origin="cli-observed",
            launch_dir=run.launch_dir,
            engine_version=run.engine_version,
            **mine,
        )
    )
    note_change(conn, run.run_id)
    conn.execute(
        insert(launches).values(
            id=new_id("lch"),
            run_id=run.run_id,
            n=1,
            launch_dir=run.launch_dir,
            pid=run.pid,
            pid_start_time=run.pid_start_time,
            host_boot_id=run.boot_id,
            head_host=run.host,
            **mine,
        )
    )
