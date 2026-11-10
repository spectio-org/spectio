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
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator
from referencing import Registry
from referencing.exceptions import Unresolvable
from sqlalchemy import Connection, insert

from spectio.environments import PROFILE, Name, snapshot
from spectio.runner.rundir import RunManifest, Workflow, run_paths, write_run_manifest
from spectio_sdk.targets import RunTarget
from spectio_server.api.environments import choose
from spectio_server.api.problems import Invalid
from spectio_server.api.workflows import (
    ENTRY_FILES,
    MAX_DEPTH,
    Found,
    depth,
    entry_files,
    inspect_dir,
    refuse_control,
    resolve,
    schema_defaults,
)
from spectio_server.ids import new_id
from spectio_server.store.runs import EngineConflict, first, insert_run
from spectio_server.store.schema import principals, runner_commands
from spectio_server.store.writer import Writer
from spectio_server.targets import TargetIn, launch_module, launch_rule, require_flag

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
    environment: Name | None = None  # by name; the default when absent (FU-P3-86c, api §5.4)
    target: TargetIn | None = None  # one module or one rule (api §5.9), behind a flag

    @field_validator("params")
    @classmethod
    def _shallow(cls, params: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if depth(params) > MAX_DEPTH:
            raise ValueError(f"nested deeper than {MAX_DEPTH} levels")
        return params


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
    if not isinstance(found.schema.get("$schema", ""), str):
        raise Invalid("params", "the pipeline's schema cannot be used: $schema is not a URI")
    cls = validators.validator_for(found.schema, default=validators.Draft7Validator)
    try:
        cls.check_schema(found.schema)
        errors = sorted(
            cls(found.schema, registry=Registry()).iter_errors(params), key=lambda e: list(e.path)
        )
    except (SchemaError, Unresolvable, RecursionError) as exc:  # `{"$ref": "#"}` recurses
        reason = exc.message if isinstance(exc, SchemaError) else type(exc).__name__
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
    if body.target is not None:
        require_flag(request.app.state.settings)
        if body.target.kind == "module":
            return _launch_module(body, body.target, request, response)
        if engine != "snakemake":
            raise Invalid("target.kind", "a Nextflow run targets a module, not a rule")
    try:
        resolved = resolve(
            request.app.state.settings.data_dir, body.workflow.location, body.workflow.revision
        )
    except Invalid as exc:
        raise exc.under("workflow") from None
    files = ENTRY_FILES[engine]
    if not set(files) & set(entry_files(resolved.directory)):
        names = " or ".join(files)
        raise Invalid("workflow.engine", f"no {names} in this pipeline: is it a {engine} one?")
    try:
        found = inspect_dir(resolved.directory, resolved.default_name)
    except Invalid as exc:
        raise exc.under("workflow") from None
    _check_params(found, body.params)
    # the values as resolved now: the run keeps them whatever the file says later (req. 18)
    environment = snapshot(choose(request, body.environment))

    target = None if body.target is None else launch_rule(body.target)
    return _create(
        body,
        request,
        response,
        Workflow(location=resolved.location, revision=resolved.revision, engine=engine),
        str(resolved.directory),
        resolved.source,
        found,
        environment,
        target,
    )


def _launch_module(
    body: LaunchIn, given: TargetIn, request: Request, response: Response
) -> dict[str, Any]:
    """A run of one Nextflow module (api §5.9): no pipeline to resolve, no schema; the module's
    inputs are its parameters, and a registry module always runs at a pinned version."""
    if body.workflow.engine != "nextflow":
        raise Invalid("target.kind", "a Snakemake run targets a rule, not a module")
    if body.workflow.revision is not None:
        raise Invalid("workflow.revision", "a module has a version, not a revision")
    settings = request.app.state.settings
    module = launch_module(
        settings, request.app.state.target_engine, body.workflow.location, given, body.params
    )
    t = module.target
    found = Found([], "nextflow", t.name, t.version, [], None, "none")
    environment = snapshot(choose(request, body.environment))
    workflow = Workflow(location=module.location, revision=None, engine="nextflow")
    source = "module-registry" if t.source == "registry" else "module-local"
    return _create(
        body, request, response, workflow, module.location, source, found, environment, t
    )


def _create(
    body: LaunchIn,
    request: Request,
    response: Response,
    workflow: Workflow,
    location: str,
    source: str,
    found: Found,
    environment: dict[str, Any],
    target: RunTarget | None,
) -> dict[str, Any]:
    runs_root = request.app.state.settings.runs_root
    run_id = new_id("run")
    short = found.name.rsplit("/", 1)[-1] if source.startswith("module-") else found.name
    name = body.name or f"{short}-{run_id[-6:]}"
    now = datetime.now(UTC)
    paths = run_paths(runs_root, run_id)
    manifest = RunManifest(
        run_id=run_id,
        name=name,
        workflow=workflow,
        params=body.params,
        profiles=body.profiles,
        created_at=now,
        environment=environment,
        target=target,
    )
    write_run_manifest(paths.run_dir, manifest)
    payload: dict[str, Any] = {
        "location": location,
        "profiles": body.profiles,
        "params": body.params,
        "environment": environment,
    }
    if target is not None:
        payload["target"] = target.model_dump(exclude_none=True)
    writer: Writer = request.app.state.writer
    try:
        writer.submit(
            lambda conn: _insert(conn, manifest, source, found, payload, now, runs_root)
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
            "location": workflow.location,
            "revision": workflow.revision,
            "engine": workflow.engine,
            "name": found.name,
            "version": found.version,
        },
        "profiles": body.profiles,
        "params": body.params,
        "target": None if target is None else target.model_dump(),
    }


def _insert(
    conn: Connection,
    m: RunManifest,
    source: str,
    found: Found,
    payload: dict[str, Any],
    now: datetime,
    runs_root: Path,
) -> None:
    outdir = schema_defaults(found.schema).get("outdir")
    try:
        launch_id = insert_run(
            conn,
            m,
            source=source,
            runs_root=runs_root,
            now=now,
            state="queued",
            origin="ui",
            workflow_name=found.name,
            workflow_version=found.version,
            default_outdir=outdir if isinstance(outdir, str) else None,
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
