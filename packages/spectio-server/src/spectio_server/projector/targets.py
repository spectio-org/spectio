"""The target a bridge reports (api §5.9, architecture §13.8; #161), stored on the run.

A run launched from the screens already holds its target: the report adds what only the head
knows, a registry module's checksum. A run started from a terminal gets the reported target, and
a module run moves from its launch directory's workflow to the module's, so that every run of
`nf-core/fastqc@<v>` is listed under one workflow (Discovered). When an earlier run of the same
`name@version` stored another checksum, the run's target says `checksum_changed`.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Connection, delete, func, insert, select, update

from spectio_sdk.targets import RunTarget
from spectio_server.ids import new_id
from spectio_server.store.runs import module_source
from spectio_server.store.schema import runs, workflow_versions, workflows

if TYPE_CHECKING:
    from spectio_server.projector.runs import Projection


def capture(p: "Projection", reported: RunTarget | None) -> None:
    if reported is None:
        return
    row = p.conn.execute(
        select(runs.c.target, runs.c.origin, runs.c.workflow_version_id).where(
            runs.c.id == p.run_id
        )
    ).one()
    if row.target is not None:  # launched with one: the launch wins, the head adds its hash
        stored = RunTarget.model_validate(row.target)
        if stored.kind != "module" or stored.hash is not None or reported.hash is None:
            return
        target = stored.model_copy(update={"hash": reported.hash})
    elif row.origin == "cli-observed":
        target = reported
        if target.kind == "module":
            _move(p.conn, row.workflow_version_id, target)
    else:
        return  # a run launched as a whole pipeline stays one
    if target.kind == "module" and target.hash is not None:
        p.conn.execute(
            update(workflow_versions)
            .where(
                workflow_versions.c.id == row.workflow_version_id, workflow_versions.c.key.is_(None)
            )
            .values(key=target.hash)
        )
        if _checksum_changed(p.conn, p.run_id, target):
            target = target.model_copy(update={"checksum_changed": True})
    p.conn.execute(
        update(runs)
        .where(runs.c.id == p.run_id)
        .values(target=target.model_dump(exclude_none=True))
    )


def _location(target: RunTarget) -> str:
    return target.path if target.source == "local" and target.path else target.name


def _move(conn: Connection, old_version: str, target: RunTarget) -> None:
    """Key a terminal module run by its module (api §5.9 Identity): its version row moves to the
    module's workflow; the launch directory's workflow goes when no version is left in it."""
    old = conn.execute(
        select(workflows.c.id, workflows.c.project_id, workflows.c.created_by)
        .join(workflow_versions, workflow_versions.c.workflow_id == workflows.c.id)
        .where(workflow_versions.c.id == old_version)
    ).one()
    source, location = module_source(target), _location(target)
    found = conn.execute(
        select(workflows.c.id).where(
            workflows.c.project_id == old.project_id,
            workflows.c.source == source,
            workflows.c.location == location,
        )
    ).scalar_one_or_none()
    if found is None:
        found = new_id("wfl")
        conn.execute(
            insert(workflows).values(
                id=found,
                project_id=old.project_id,
                name=target.name,
                location=location,
                source=source,
                engine="nextflow",
                created_at=func.now(),
                created_by=old.created_by,
            )
        )
    conn.execute(
        update(workflow_versions)
        .where(workflow_versions.c.id == old_version)
        .values(workflow_id=found, revision=target.version)
    )
    left = conn.execute(
        select(func.count()).where(workflow_versions.c.workflow_id == old.id)
    ).scalar_one()
    if not left:
        conn.execute(delete(workflows).where(workflows.c.id == old.id))


def _checksum_changed(conn: Connection, run_id: str, target: RunTarget) -> bool:
    """Another run of this module and version stored another checksum."""
    keys = conn.execute(
        select(workflow_versions.c.key)
        .join(workflows, workflows.c.id == workflow_versions.c.workflow_id)
        .join(runs, runs.c.workflow_version_id == workflow_versions.c.id)
        .where(
            workflows.c.source == module_source(target),
            workflows.c.location == _location(target),
            workflow_versions.c.revision == target.version,
            workflow_versions.c.key.is_not(None),
            runs.c.id != run_id,
        )
    ).scalars()
    return any(key != target.hash for key in keys)


def target_of(conn: Connection, run_id: str) -> RunTarget | None:
    value: Any = conn.execute(select(runs.c.target).where(runs.c.id == run_id)).scalar_one()
    return None if value is None else RunTarget.model_validate(value)
