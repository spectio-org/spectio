"""Runs table actions (FU-P3-115a; api §5 note of 2026-11-10): `POST /runs:delete` and
`PATCH /runs/{id}` (`pinned`). Sorting is `GET /runs?sort=` (`runs_read`).

A delete is all or nothing over ended runs, and soft: `runs.deleted_at` is set and the reads
leave the run out, since the boot's rebuild would add a removed row back from its directory
(P1 Task 11). Nothing on disk changes unless `directories` is true; then each run's own
directory, `<runs root>/<run ID>`, is removed once the rows are marked, relative to the runs
root's descriptor and never through a symlink. Both writes pass the guards of every write
(session, loopback Origin, JSON body: dev-env §15.3 req. 7).
"""

import logging
import os
import shutil
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import Connection, Row, or_, select, update

from spectio.runner.rundir import RUN_ID, private_dir, run_paths
from spectio_server.api import models
from spectio_server.api.problems import Problem, not_found
from spectio_server.api.runs_read import context, read, run_detail, run_row
from spectio_server.projector.runs import TERMINAL
from spectio_server.store.schema import launches, runs
from spectio_server.store.writer import Writer, note_change

router = APIRouter()
log = logging.getLogger(__name__)

MAX_DELETE = 200
SAFE_RMTREE = shutil.rmtree.avoids_symlink_attacks  # the descriptor walk (Python docs, shutil)

RunId = Annotated[str, StringConstraints(pattern=RUN_ID.pattern)]
DirResult = Literal["removed", "missing", "failed"]


class DeleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ids: Annotated[list[RunId], Field(min_length=1, max_length=MAX_DELETE)]
    directories: bool = False  # also remove each run's own directory

    @field_validator("ids")
    @classmethod
    def _distinct(cls, ids: list[str]) -> list[str]:
        if len(set(ids)) != len(ids):
            raise ValueError("each run once")
        return ids


class PinIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    pinned: bool


def _conflict(slug: str, title: str, detail: str, errors: list[dict[str, str]]) -> Problem:
    return Problem(409, slug, title, detail, errors=errors)


def _directory_refusals(
    conn: Connection, found: list[Row[Any]], runs_root: Path
) -> list[dict[str, str]]:
    """Why a run's directory may not be removed, one error per run, in request order."""
    ids = [r.id for r in found]
    shared = conn.execute(
        select(runs.c.launch_dir, runs.c.work_dir).where(
            runs.c.id.not_in(ids),
            runs.c.deleted_at.is_(None),
            or_(
                runs.c.launch_dir.in_([r.launch_dir for r in found if r.launch_dir]),
                runs.c.work_dir.in_([r.work_dir for r in found if r.work_dir]),
            ),
        )
    ).all()
    used = {d for row in shared for d in row if d}
    alive = set(  # the runner still watches the head (`StoreSink.active_launches`)
        conn.execute(
            select(launches.c.run_id).where(
                launches.c.run_id.in_(ids),
                launches.c.head_native_id.is_not(None),
                launches.c.exited_at.is_(None),
            )
        ).scalars()
    )
    errors = []
    for r in found:
        if r.origin == "cli-observed":
            reason = "started from a terminal: its launch directory is your own"
        elif r.id in alive:
            reason = "its head has not been seen to exit yet: try again in a minute"
        elif r.launch_dir != str(run_paths(runs_root, r.lineage_id or r.id).launch_dir):
            reason = "its directory is not where the runs root says: the runs root changed"
        elif r.launch_dir in used or r.work_dir in used:
            reason = "a run not deleted shares its directories (Resume): delete them together"
        else:
            continue
        errors.append({"field": r.id, "message": reason})
    return errors


def _mark(conn: Connection, body: DeleteIn, runs_root: Path) -> list[str]:
    """Check every run, then mark them all deleted; the IDs whose directory goes."""
    rows: dict[str, Any] = {
        r.id: r
        for r in conn.execute(
            select(
                runs.c.id,
                runs.c.state,
                runs.c.origin,
                runs.c.launch_dir,
                runs.c.work_dir,
                runs.c.lineage_id,
            ).where(runs.c.id.in_(body.ids), runs.c.deleted_at.is_(None))
        )
    }
    missing = [i for i in body.ids if i not in rows]
    if missing:
        raise not_found(f"no run {missing[0]!r}")
    found = [rows[i] for i in body.ids]
    active = [
        {"field": r.id, "message": f"the run is {r.state}"}
        for r in found
        if r.state not in TERMINAL
    ]
    if active:
        raise _conflict(
            "run-not-ended", "Run not ended", "Only an ended run can be deleted.", active
        )
    if body.directories:
        refused = _directory_refusals(conn, found, runs_root)
        if refused:
            raise _conflict(
                "directory-not-removable",
                "Directory not removable",
                "Spectio removes only a run directory it created and no other run uses.",
                refused,
            )
    conn.execute(update(runs).where(runs.c.id.in_(body.ids)).values(deleted_at=datetime.now(UTC)))
    for run_id in body.ids:
        note_change(conn, run_id)
    return body.ids if body.directories else []


def remove_run_dir(runs_root: Path, run_id: str) -> DirResult:
    """Remove `<runs_root>/<run_id>` and nothing else: the runs root opened as
    `rundir.open_private` opens it, the entry a real private directory of the user (lstat
    through the root's descriptor), then `rmtree` relative to that descriptor, which never
    follows a symlink."""
    run_paths(runs_root, run_id)  # a run ID: one plain path component
    if not SAFE_RMTREE:
        return "failed"
    try:
        with private_dir(runs_root) as root:
            try:
                st = os.stat(run_id, dir_fd=root, follow_symlinks=False)
            except FileNotFoundError:
                return "missing"
            if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o077:
                return "failed"
            shutil.rmtree(run_id, dir_fd=root)
    except OSError:
        return "failed"
    return "removed"


@router.post("/runs:delete")
def delete_runs(body: DeleteIn, request: Request) -> dict[str, Any]:
    runs_root: Path = request.app.state.settings.runs_root
    writer: Writer = request.app.state.writer
    doomed = writer.submit(lambda conn: _mark(conn, body, runs_root)).result()
    log.info("runs deleted: %s", ", ".join(body.ids))
    directories = []
    for run_id in doomed:
        result = remove_run_dir(runs_root, run_id)
        log.info("run %s: directory %s %s", run_id, runs_root / run_id, result)
        directories.append({"id": run_id, "result": result})
    return {"deleted": body.ids, "directories": directories}


def _pin(conn: Connection, run_id: str, pinned: bool) -> None:
    run_row(conn, run_id)  # 404 when unknown or deleted
    conn.execute(update(runs).where(runs.c.id == run_id).values(pinned=pinned))
    note_change(conn, run_id)


@router.patch("/runs/{run_id}", response_model=models.RunDetail)
def patch_run(body: PinIn, request: Request, run_id: str) -> dict[str, Any]:
    writer: Writer = request.app.state.writer
    writer.submit(lambda conn: _pin(conn, run_id, body.pinned)).result()
    with read(request) as conn:
        return run_detail(conn, run_id, context(request))
