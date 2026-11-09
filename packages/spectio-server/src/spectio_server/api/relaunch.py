"""Resume and Copy to a new launch (P1 Task 30; api §5 and §5.1, notes of 2026-10-28; dev-env
§15.3 req. 7, 10 and 16).

`POST /runs/{id}:relaunch` takes `{mode: "resume"}` only (every other field or mode is
`422 not-in-this-version`). From a `failed` or `cancelled` run it creates a child run, `queued`,
with its own run directory and `.spectio/`, whose head runs in the lineage's launch and work
directories; the parent keeps its state. The checks of `spectio_server.resume` come first,
outside the writer, then the store's again in the transaction that inserts the child
(`BEGIN IMMEDIATE`, the writer's), so two parallel requests make one child. The runner checks
the directories once more before the head starts. A refusal is `409 run-state-conflict` with
the `reason` of `actions.resume`. The session (req. 2) and the Origin check of req. 7
(`auth.writes`) run before any route.

`GET /runs/{id}:launch-template` is the `POST /runs` body of the run, for Copy to a new launch,
with `non_default` (the parameters that differ from the pipeline's schema defaults) and
`code_loading` (the values that load code or configuration, req. 16).
"""

import os
import shutil
import stat
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import Connection, insert, select

from spectio.environments import NotAllowed, resume_snapshot
from spectio.runner.loop import LaunchPayload
from spectio.runner.resume import NotResumable
from spectio.runner.rundir import (
    RunManifest,
    Workflow,
    read_run_manifest,
    run_paths,
    write_run_manifest,
)
from spectio_server.api import models
from spectio_server.api.environments import view
from spectio_server.api.problems import Invalid, Problem
from spectio_server.api.runs_read import context, read, run_detail, run_row
from spectio_server.api.workflows import inspect_dir, resolve, schema_defaults
from spectio_server.failure import dir_run_id
from spectio_server.files.pool import READ_TIMEOUT_S, Stalled
from spectio_server.ids import new_id
from spectio_server.resume import check_dirs, launch_payload, row_refusal
from spectio_server.store.runs import first, insert_run
from spectio_server.store.schema import principals, run_inputs, runner_commands
from spectio_server.store.writer import Writer

router = APIRouter()

CONFIG_PARAMS = ("custom_config_base",)  # nf-core's: where institutional configs load from
CONFIG_OPTIONS = {"nextflow": ("-c", "-config"), "snakemake": ("--configfile", "--configfiles")}


class RelaunchIn(BaseModel):
    """The body of `:relaunch` (api §5.1); 0.0.1 takes `mode: resume` alone."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["resume", "rerun_from", "fresh"]
    from_stage: JsonValue = None
    params_patch: JsonValue = None
    samplesheets: JsonValue = None
    resources: JsonValue = None
    gates: JsonValue = None
    dry_run: JsonValue = None


def _conflict(reason: str, detail: str) -> Problem:
    return Problem(409, "run-state-conflict", "Run state conflict", detail, reason=reason)


def _not_in_this_version(detail: str) -> Problem:
    return Problem(422, "not-in-this-version", "Not in this version", detail)


REFUSED = {
    "running": "The run, or its head, is still running.",
    "not_failed_or_cancelled": "Only a failed or cancelled run can be resumed.",
    "resume_in_progress": "Another run of this launch directory has not ended yet.",
    "session_id_refused": "The run's Nextflow session ID is not a UUID.",
}


def _params(conn: Connection, run_id: str) -> dict[str, Any]:
    found = conn.execute(
        select(run_inputs.c.content)
        .where(run_inputs.c.run_id == run_id, run_inputs.c.kind == "params")
        .order_by(run_inputs.c.version.desc())
        .limit(1)
    ).scalar()
    return dict(found or {})


def _profiles(runs_root: Path, run_id: str, launched: LaunchPayload | None) -> list[str] | None:
    """The run's profiles: its `launch` command's, else its manifest's (a run rebuilt from its
    run directories has no command, CR-P3T30-04); None when neither can be read."""
    if launched is not None:
        return launched.profiles
    try:
        return read_run_manifest(run_paths(runs_root, run_id).run_dir).profiles
    except (OSError, ValueError):
        return None


def _insert_child(
    conn: Connection,
    parent_id: str,
    m: RunManifest,
    source: str,
    payload: dict[str, Any],
    now: datetime,
    runs_root: Path,
) -> None:
    parent = run_row(conn, parent_id)
    reason = row_refusal(conn, parent)  # again, in this BEGIN IMMEDIATE transaction
    if reason is not None:
        raise _conflict(reason, REFUSED.get(reason, reason))
    launch_id = insert_run(
        conn,
        m,
        source=source,
        runs_root=runs_root,
        now=now,
        state="queued",
        origin="ui",
        workflow_name=parent.workflow_name,
        workflow_version=parent.workflow_version,
    )
    conn.execute(
        insert(runner_commands).values(
            id=new_id("cmd"),
            run_id=m.run_id,
            launch_id=launch_id,
            kind="launch",
            payload=payload,
            state="pending",
            created_at=now,
            created_by=first(conn, principals),
        )
    )


@router.post("/runs/{run_id}:relaunch", status_code=201, response_model=models.RunDetail)
def relaunch(body: RelaunchIn, request: Request, run_id: str, response: Response) -> dict[str, Any]:
    if body.mode != "resume" or body.model_fields_set - {"mode"}:
        raise _not_in_this_version("0.0.1 relaunches with {mode: resume} and nothing else.")
    settings = request.app.state.settings
    ctx = context(request)
    with read(request) as conn:
        parent = run_row(conn, run_id)
        reason = row_refusal(conn, parent)
        params = _params(conn, run_id)
        launched = launch_payload(conn, run_id)
    if reason == "cli_observed":
        raise _not_in_this_version("Spectio did not start this run's head: it cannot resume it.")
    if reason is not None:
        raise _conflict(reason, REFUSED[reason])
    try:  # the launch rules again, on the parent's own snapshot (api §5.4, Resume)
        environment = resume_snapshot(parent.environment, settings).model_dump(mode="json")
    except NotAllowed as exc:
        raise Invalid("environment", str(exc)) from None
    profiles = _profiles(settings.runs_root, run_id, launched)
    if profiles is None:
        raise _conflict("profiles_unknown", "The run's profiles cannot be read from its manifest.")
    try:
        device, inode = check_dirs(ctx, parent)
    except NotResumable as exc:
        raise _conflict(exc.reason, str(exc)) from None
    try:
        resolved = resolve(settings.data_dir, parent.location, parent.revision)
    except Invalid as exc:
        raise exc.under("workflow") from None

    child_id = new_id("run")
    now = datetime.now(UTC)
    manifest = RunManifest(
        run_id=child_id,
        name=f"{parent.workflow_name or resolved.default_name}-{child_id[-6:]}",
        workflow=Workflow(location=parent.location, revision=parent.revision, engine=parent.engine),
        params=params,
        profiles=profiles,
        created_at=now,
        parent_run_id=run_id,
        environment=environment,
    )
    payload = {
        "location": str(resolved.directory),
        "profiles": profiles,
        "params": params,
        "resume_of": {
            "run_id": dir_run_id(parent),
            "parent_run_id": run_id,
            "engine_session_id": parent.engine_session_id,
            "device": device,
            "inode": inode,
        },
        "environment": environment,
    }
    paths = run_paths(settings.runs_root, child_id)
    write_run_manifest(paths.run_dir, manifest)
    writer: Writer = request.app.state.writer
    try:
        writer.submit(
            lambda conn: _insert_child(
                conn, run_id, manifest, resolved.source, payload, now, settings.runs_root
            )
        ).result()
    except BaseException:
        shutil.rmtree(paths.run_dir, ignore_errors=True)  # no run directory without its row
        raise
    response.headers["Location"] = f"/api/v1/runs/{child_id}"
    with read(request) as conn:
        return run_detail(conn, child_id, ctx)


# --- Copy to a new launch -----------------------------------------------------------------


MAX_LINK_HOPS = 40  # Linux's MAXSYMLINKS


def writable_by_others(path: str) -> bool:
    """Whether someone else may change what the path loads (SEC-P3T30-01, SEC-P3T30-02): the
    path is resolved one component at a time, without following anything first. Flagged: a
    directory on the way, or the target, owned by a user other than this one and root, or
    writable by group or others; a symlink owned by another user, as one can repoint it. A
    sticky directory (`/tmp`) is excepted only above the nearest existing part: a missing file
    in it, or the directory itself as a workflow, can still be planted. A link's own mode says
    nothing; its target is resolved the same way, up to 40 links."""
    me = os.geteuid()

    def others(st: os.stat_result, sticky_ok: bool) -> bool:
        sticky = sticky_ok and stat.S_ISDIR(st.st_mode) and st.st_mode & stat.S_ISVTX
        return st.st_uid not in (me, 0) or bool(
            st.st_mode & (stat.S_IWGRP | stat.S_IWOTH) and not sticky
        )

    current, hops = "/", 0
    todo = os.path.join(os.getcwd(), path).split("/")[::-1]  # not normalised: `link/..`
    try:
        while todo:
            name = todo.pop()
            if name in ("", "."):
                continue
            if name == "..":  # `current` holds no link: its parent is the real one
                current = os.path.dirname(current)
                continue
            holder = os.lstat(current)
            child = os.path.join(current, name)
            try:
                st = os.lstat(child)
            except OSError:  # missing: `current` is the nearest existing part
                return others(holder, sticky_ok=False)
            if others(holder, sticky_ok=True):
                return True
            if stat.S_ISLNK(st.st_mode):
                hops += 1
                if hops > MAX_LINK_HOPS or st.st_uid not in (me, 0):
                    return True
                target = os.readlink(child)
                todo += target.split("/")[::-1]
                if target.startswith("/"):
                    current = "/"
                continue
            current = child
        return others(os.lstat(current), sticky_ok=False)
    except OSError:  # changed while it was walked: flagged
        return True


def code_loading(
    location: str, local: bool, params: dict[str, Any], engine: str, extra: list[str]
) -> list[dict[str, Any]]:
    values = [("workflow.location", location)] if local else []
    values += [(f"params.{k}", params[k]) for k in CONFIG_PARAMS if isinstance(params.get(k), str)]
    options = CONFIG_OPTIONS.get(engine, ())
    values += [(f"engine.{a}", b) for a, b in pairwise(extra) if a in options]
    return [
        {
            "field": field,
            "value": value,
            "writable_by_others": value.startswith("/") and writable_by_others(value),
        }
        for field, value in values
    ]


@router.get("/runs/{run_id}:launch-template", response_model=models.LaunchTemplate)
def launch_template(request: Request, run_id: str) -> dict[str, Any]:
    settings = request.app.state.settings
    with read(request) as conn:
        row = run_row(conn, run_id)
        params = _params(conn, run_id)
        payload = launch_payload(conn, run_id)
    try:
        resolved = resolve(settings.data_dir, row.location, row.revision)
        found = inspect_dir(resolved.directory, resolved.default_name)
    except Invalid as exc:
        raise exc.under("workflow") from None
    defaults = schema_defaults(found.schema if found.schema_source != "inferred" else None)
    extra = settings.engines.extra_args.get(row.engine, [])
    local = resolved.source == "local"
    try:
        loading = request.app.state.files.run(
            lambda: code_loading(row.location, local, params, row.engine, extra), READ_TIMEOUT_S
        )
    except Stalled as exc:
        raise Problem(503, "runner-offline", "File system not answering", str(exc)) from None
    name, notice = _template_environment(request, row.environment)
    return {
        "workflow": {"location": row.location, "revision": row.revision, "engine": row.engine},
        "profiles": _profiles(settings.runs_root, run_id, payload) or [],
        "params": params,
        "non_default": [k for k in params if k not in defaults or params[k] != defaults[k]],
        "code_loading": loading,
        "environment": name,
        "environment_notice": notice,
    }


def _template_environment(
    request: Request, column: dict[str, Any] | None
) -> tuple[str, str | None]:
    """The run's environment by name, with its current values, or the default with a notice
    when that name is gone (api §5.4, A run keeps what it ran with)."""
    _, entries, default = view(request)
    name = None if column is None or column.get("state") != "recorded" else column.get("name")
    if name is None or any(env.name == name for env, *_ in entries):
        return name or default, None
    return default, f"The environment {name} of this run no longer exists: {default} is chosen."
