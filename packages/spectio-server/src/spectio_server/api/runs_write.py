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

from spectio.environments import PROFILE, DefaultResources, Environment, Name, snapshot
from spectio.runner.rundir import RunManifest, Workflow, run_paths, write_run_manifest
from spectio_server.api.environments import choose
from spectio_server.api.extras import check_resources, checked_config_file
from spectio_server.api.problems import Invalid
from spectio_server.api.workflows import (
    ENTRY_FILES,
    MAX_DEPTH,
    Found,
    Resolved,
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
    default_resources: DefaultResources | None = None  # api §5.7 (FU-P3-110a)
    config_file: str | None = None  # an absolute path, api §5.7

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
    chosen = choose(request, body.environment)
    environment = snapshot(chosen)
    resources = _resources(body, chosen)
    config_file, config_bytes = _config_file(request, body, resolved)

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
        environment=environment,
        default_resources=resources,
        config_file=config_file,
    )
    write_run_manifest(paths.run_dir, manifest)
    payload = {
        "location": str(resolved.directory),
        "profiles": body.profiles,
        "params": body.params,
        "environment": environment,
        **extras_payload(resources, config_bytes),
    }
    writer: Writer = request.app.state.writer
    try:
        writer.submit(
            lambda conn: _insert(conn, manifest, resolved.source, found, payload, now, runs_root)
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


def _resources(body: LaunchIn, env: Environment) -> dict[str, Any] | None:
    """`default_resources` as sent, checked against the engine, the profile and the
    environment's caps (api §5.7); None when absent or `{}`, which changes nothing."""
    found = body.default_resources
    if found is None or found == DefaultResources():
        return None
    check_resources(found, body.workflow.engine, body.profiles, env)
    return found.model_dump(mode="json")


def extras_payload(
    resources: dict[str, Any] | None, config_bytes: dict[str, Any] | None
) -> dict[str, Any]:
    """The launch command's `default_resources` and `config_file` (api §5.7), when set."""
    found = {"default_resources": resources, "config_file": config_bytes}
    return {k: v for k, v in found.items() if v is not None}


def _config_file(
    request: Request, body: LaunchIn, resolved: Resolved
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """The extra config file, checked and read (`extras.checked_config_file`, api §5.7): what
    the run keeps of it, and the launch command's `{kept_as, sha256, size, text}`."""
    if body.config_file is None:
        return None, None
    kept = checked_config_file(request, body.config_file, resolved.directory, body.workflow.engine)
    text = kept.pop("text")
    sent = {k: kept[k] for k in ("kept_as", "sha256", "size")}
    return {"path": body.config_file, **kept}, {**sent, "text": text}


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
