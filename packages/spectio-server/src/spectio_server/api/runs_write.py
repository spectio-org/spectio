"""`POST /api/v1/runs`: the 0.0.1 launch (P1 Task 17, Assumption 2; api §5, §5.2).

The body is checked whole before anything is written: the location and revision (the rules of
`workflows.resolve`), the chosen engine's file, the profiles and the name, and the parameters
against the pipeline's schema (`nextflow_schema.json` or `config.schema.yaml`; types inferred
from `config/config.yaml` only shape the form and are not enforced). Then the run directory and
its manifest are written (`write_run_manifest`, Assumption 21), and the rows in one transaction:
the workflow (one row per location, with one engine: api §7), its version, the run (`queued`,
origin `ui`), its parameters (`run_inputs.kind = params`), launch 1 and its `launch` command,
which the runner leases (P1 Task 9). The runner launches the directory read here, the clone for
a Git location; the run keeps the location as given, the repository's URL for Git.
"""

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from fastapi import APIRouter, Request, Response
from jsonschema import validators
from jsonschema.exceptions import SchemaError
from pydantic import BaseModel, ConfigDict, Field, JsonValue
from referencing import Registry
from referencing.exceptions import Unresolvable
from sqlalchemy import Connection, insert

from spectio.runner.headscript import PROFILE
from spectio.runner.rundir import RunManifest, Workflow, run_paths, write_run_manifest
from spectio_server.api.problems import Invalid
from spectio_server.api.workflows import (
    ENTRY_FILES,
    Found,
    _regular,
    inspect_dir,
    refuse_control,
    resolve,
)
from spectio_server.ids import new_id
from spectio_server.store.runs import EngineConflict, first, insert_run
from spectio_server.store.schema import principals, runner_commands
from spectio_server.store.writer import Writer

router = APIRouter()


class WorkflowIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: str
    revision: str | None = None
    engine: Literal["nextflow", "snakemake"]


class LaunchIn(BaseModel):
    """The 0.0.1 body of `POST /runs` (api §5 note of 2026-10-30)."""

    model_config = ConfigDict(extra="forbid")

    workflow: WorkflowIn
    name: str | None = Field(None, min_length=1, max_length=200)
    profiles: list[str] = Field(default_factory=list, max_length=20)
    params: dict[str, JsonValue] = Field(default_factory=dict)


def _check(body: LaunchIn) -> None:
    if body.name is not None:
        refuse_control("name", body.name)
    for i, profile in enumerate(body.profiles):
        if not PROFILE.fullmatch(profile):
            raise Invalid(f"profiles.{i}", "a profile name: letters, digits, '.', '_' and '-'")
    if body.workflow.engine == "snakemake" and len(body.profiles) > 1:
        raise Invalid("profiles", "a Snakemake launch takes one profile")


def _check_params(found: Found, params: dict[str, Any]) -> None:
    """Validate against the pipeline's own schema (draft 7 or 2020-12, from its `$schema`).
    No `$ref` is retrieved (no file, no URL: api §5, Imports are untrusted input): an empty
    registry replaces jsonschema's default one, which fetches; one that cannot resolve is a 422."""
    if found.schema is None or found.schema_source == "inferred":
        return
    cls = validators.validator_for(found.schema, default=validators.Draft7Validator)
    try:
        cls.check_schema(found.schema)
        errors = sorted(
            cls(found.schema, registry=Registry()).iter_errors(params), key=lambda e: list(e.path)
        )
    except (SchemaError, Unresolvable) as exc:
        reason = exc.message if isinstance(exc, SchemaError) else str(exc)
        raise Invalid("params", f"the pipeline's schema cannot be used: {reason}") from None
    found_errors = []
    for error in errors:
        path = [str(p) for p in error.absolute_path]
        if error.validator == "required":  # the missing name is in the message only
            required = cast(list[str], error.validator_value)
            missing = [k for k in required if k not in cast(dict[str, Any], error.instance)]
            path += missing[:1]
        found_errors.append({"field": ".".join(["params", *path]), "message": error.message})
    if found_errors:
        raise Invalid.many(found_errors)


@router.post("/runs", status_code=201)
def create_run(body: LaunchIn, request: Request, response: Response) -> dict[str, Any]:
    _check(body)
    engine = body.workflow.engine
    try:
        resolved = resolve(
            request.app.state.settings.data_dir, body.workflow.location, body.workflow.revision
        )
    except Invalid as exc:
        raise exc.under("workflow") from None
    files = ENTRY_FILES[engine]
    if not any(_regular(resolved.directory, *f.split("/")) for f in files):
        names = " or ".join(files)
        raise Invalid("workflow.engine", f"no {names} in this pipeline: is it a {engine} one?")
    try:
        found = inspect_dir(resolved.directory, resolved.default_name)
    except Invalid as exc:
        raise exc.under("workflow") from None
    _check_params(found, body.params)

    runs_root = request.app.state.settings.runs_root
    run_id = new_id("run")
    name = body.name or f"{found.name}-{run_id[-6:]}"
    now = datetime.now(UTC)
    paths = run_paths(runs_root, run_id)
    manifest = RunManifest(
        run_id=run_id,
        name=name,
        workflow=Workflow(location=resolved.location, revision=resolved.revision, engine=engine),
        params=body.params,
        profiles=body.profiles,
        created_at=now,
    )
    write_run_manifest(paths.run_dir, manifest)
    payload = {
        "location": str(resolved.directory),
        "profiles": body.profiles,
        "params": body.params,
    }
    writer: Writer = request.app.state.writer
    try:
        writer.submit(
            lambda conn: _insert(
                conn, manifest, resolved.source, found.name, payload, now, runs_root
            )
        ).result()
    except BaseException:
        shutil.rmtree(paths.run_dir, ignore_errors=True)  # no run directory without its row
        raise
    response.headers["Location"] = f"/api/v1/runs/{run_id}"
    return {
        "id": run_id,
        "name": name,
        "state": "queued",
        "origin": "ui",
        "created_at": now.isoformat(),
        "workflow": {
            "location": resolved.location,
            "revision": resolved.revision,
            "engine": engine,
            "name": found.name,
            "version": found.version,
        },
        "profiles": body.profiles,
        "params": body.params,
    }


def _insert(
    conn: Connection,
    m: RunManifest,
    source: str,
    workflow_name: str,
    payload: dict[str, Any],
    now: datetime,
    runs_root: Path,
) -> None:
    try:
        launch_id = insert_run(
            conn,
            m,
            source=source,
            runs_root=runs_root,
            now=now,
            state="queued",
            origin="ui",
            workflow_name=workflow_name,
        )
    except EngineConflict as exc:
        raise Invalid(
            "workflow.engine",
            f"this pipeline was launched with {exc.engine} before; "
            "a location keeps one engine in 0.0.1",
        ) from None
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
