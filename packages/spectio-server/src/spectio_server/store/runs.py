"""The rows of one run, shared by `POST /runs` and the index rebuild (P1 Tasks 11 and 17).

`insert_run` finds or creates the location's `workflows` row (one per location, with one engine:
api §7), then adds its version, the run, its parameters (`run_inputs.kind = params`) and
launch 1. The launch endpoint adds its `launch` command; the rebuild gives the state it read.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, insert, null, select

from spectio.runner.rundir import RunManifest, run_paths
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
) -> str:
    """Insert the run of manifest `m` and its launch 1; return the launch's ID."""
    mine = {"created_at": now, "created_by": first(conn, principals)}
    project = first(conn, projects)
    location, engine = m.workflow.location, m.workflow.engine
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
        workflow_id = workflow.id
    else:
        workflow_id = new_id("wfl")
        conn.execute(
            insert(workflows).values(
                id=workflow_id,
                project_id=project,
                name=workflow_name,
                location=location,
                source=source,
                engine=engine,
                **mine,
            )
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
            launch_dir=str(paths.launch_dir),
            work_dir=str(paths.work_dir),
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
            launch_dir=str(paths.launch_dir),
            head_native_id=native_id,
            **mine,
        )
    )
    return launch_id
