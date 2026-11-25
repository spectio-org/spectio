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

import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Request, Response
from jsonschema import validators
from jsonschema.exceptions import SchemaError
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator
from referencing import Registry
from referencing.exceptions import Unresolvable
from sqlalchemy import Connection, insert

from spectio.environments import PROFILE, DefaultResources, Environment, Name, snapshot
from spectio.runner.rundir import RunManifest, Workflow, run_paths, write_run_manifest
from spectio_sdk.targets import RunTarget
from spectio_server.api.environments import choose
from spectio_server.api.extras import check_resources, checked_config_file
from spectio_server.api.problems import Invalid
from spectio_server.api.workflows import (
    ENTRY_FILES,
    MAX_DEPTH,
    Found,
    Resolved,
    check_main_script,
    depth,
    entry_files,
    inspect_dir,
    main_scripts,
    refuse_control,
    resolve,
    schema_defaults,
)
from spectio_server.defaults import effective_defaults
from spectio_server.ids import new_id
from spectio_server.mounts import (
    echoed_paths,
    env_binds,
    site_bind_paths,
    suggested_binds,
    unmounted_paths,
)
from spectio_server.store.runs import EngineConflict, first, insert_run, module_source
from spectio_server.store.schema import principals, runner_commands
from spectio_server.store.writer import Writer
from spectio_server.targets import TargetIn, launch_module, launch_rule, require_flag

router = APIRouter()

# "'x' is a required property": the missing name is in the message only (api §5.12).
_REQUIRED_NAME = re.compile(r"^['\"](.+)['\"] is a required property$")


class WorkflowIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: str
    revision: str | None = None
    engine: Literal["nextflow", "snakemake"]
    main_script: str | None = Field(None, max_length=255)  # a Nextflow entry script (#351)


class LaunchIn(BaseModel):
    """The 0.0.1 body of `POST /runs` (api §5 note of 2026-10-30)."""

    model_config = ConfigDict(extra="forbid")

    workflow: WorkflowIn
    name: str | None = Field(None, min_length=1, max_length=200)
    profiles: list[str] = Field(default_factory=list, max_length=20)
    params: dict[str, JsonValue] = Field(default_factory=dict)
    environment: Name | None = None  # by name; the default when absent (FU-P3-86c, api §5.4)
    target: TargetIn | None = None  # one module or one rule (api §5.10), behind a flag
    default_resources: DefaultResources | None = None  # api §5.7 (FU-P3-110a)
    config_file: str | None = None  # an absolute path, api §5.7
    # Built 2026-11-25 (api §5.2): launch although some of `params`' paths are not visible in the
    # containers. Absent or false: such a launch is refused with this field.
    allow_unmounted: bool = False

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


def _check_params(
    found: Found, params: dict[str, Any], complete: bool = True
) -> list[dict[str, str]]:
    """Validate against the pipeline's own schema (draft 7 or 2020-12, from its `$schema`).
    `params` are the *effective* ones (api §5.12): the sources' defaults under the form's
    values. When the sources are not complete, a `required` error is returned as a warning
    instead of raised: the engine's own check has the last word. No `$ref` is retrieved (no
    file, no URL: api §5, Imports are untrusted input): an empty registry replaces jsonschema's
    default one, which fetches; one that cannot resolve is a 422."""
    if found.schema is None or found.schema_source == "inferred":
        return []
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
    found_errors: list[tuple[dict[str, str], bool]] = []
    for error in errors:
        path = [str(p) for p in error.absolute_path]
        # soft/hard by the validator, not the words of the message (CR-04)
        required = error.validator == "required"
        if required:  # one error per missing name, in the message only
            quoted = _REQUIRED_NAME.match(error.message)
            if quoted is not None:  # the error's own name, not the first missing one (§5.12)
                path.append(quoted.group(1))
        entry = {"field": ".".join(["params", *path]), "message": error.message}
        found_errors.append((entry, required))
    if not found_errors:
        return []
    if complete:
        raise Invalid.many([entry for entry, _ in found_errors])
    # api §5.12: with a source unread, a `required` error is a warning; every other one —
    # a type, an enum, a pattern — stays a refusal. jsonschema's own message names the miss.
    hard = [entry for entry, soft in found_errors if not soft]
    if hard:
        raise Invalid.many(hard)
    return [entry for entry, soft in found_errors if soft]


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
    present = entry_files(resolved.directory)
    scripts = main_scripts(resolved.directory)  # read once, inspect_dir reuses them
    if not set(files) & set(present) and not (engine == "nextflow" and scripts):
        names = " or ".join(files)
        raise Invalid("workflow.engine", f"no {names} in this pipeline: is it a {engine} one?")
    main_script = _main_script(body.workflow, resolved.directory, "main.nf" in present, scripts)
    try:
        found = inspect_dir(resolved.directory, resolved.default_name, scripts)
    except Invalid as exc:
        raise exc.under("workflow") from None
    # the effective parameters (api §5.12): the sources' defaults under the form's values; the
    # 0.0.1 body carries no params file, whose values the form sends within `params` (§5.6).
    # Only when the schema is usable: `_check_params` has nothing to validate against otherwise,
    # and `nextflow config` would start the JVM for nothing (CR-03).
    if found.schema is None or found.schema_source == "inferred":
        param_warnings = None
    else:
        defaults, complete = effective_defaults(
            resolved.directory,
            request.app.state.target_engine,
            engine,
            body.profiles,
            found.schema,
        )
        merged = {name: given["value"] for name, given in defaults.items()} | body.params
        param_warnings = _check_params(found, merged, complete)
    # the values as resolved now: the run keeps them whatever the file says later (req. 18)
    chosen = choose(request, body.environment)
    environment = snapshot(chosen)
    _check_mounts(request, body, chosen, resolved.directory)
    resources = _resources(body, chosen)
    config_file, config_bytes = _config_file(request, body, resolved)

    target = None if body.target is None else launch_rule(body.target)
    return _create(
        body,
        request,
        response,
        Workflow(
            location=resolved.location,
            revision=resolved.revision,
            engine=engine,
            main_script=main_script,
        ),
        str(resolved.directory),
        resolved.source,
        found,
        environment,
        target,
        (resources, config_file, config_bytes),
        param_warnings,
    )


def _main_script(
    workflow: WorkflowIn, directory: Path, has_main: bool, scripts: list[str]
) -> str | None:
    """The Nextflow entry script (#351): a bare `*.nf` name, a regular file at the pipeline's
    root reached through no symlink. Without `main.nf` one must be chosen: never guessed."""
    given = workflow.main_script
    if given is None:
        if workflow.engine == "nextflow" and not has_main:
            names = ", ".join(scripts)
            raise Invalid("workflow.main_script", f"no main.nf: choose the main script ({names})")
        return None
    if workflow.engine != "nextflow":
        raise Invalid("workflow.main_script", "only a Nextflow pipeline takes a main script")
    return check_main_script(directory, given, "workflow.main_script")


def _launch_module(
    body: LaunchIn, given: TargetIn, request: Request, response: Response
) -> dict[str, Any]:
    """A run of one Nextflow module (api §5.10): no pipeline to resolve, no schema; the module's
    inputs are its parameters, and a registry module always runs at a pinned version."""
    if body.workflow.engine != "nextflow":
        raise Invalid("target.kind", "a Snakemake run targets a rule, not a module")
    if body.workflow.revision is not None:
        raise Invalid("workflow.revision", "a module has a version, not a revision")
    if body.config_file is not None:  # its roots are a pipeline's (api §5.7, §5.10)
        raise Invalid("config_file", "a module run takes no extra config file")
    if body.workflow.main_script is not None:  # #351: a pipeline's entry script
        raise Invalid("workflow.main_script", "a module run takes no main script")
    state = request.app.state
    module = launch_module(
        state.settings, state.target_engine, state.files, body.workflow.location, given, body.params
    )
    t = module.target
    found = Found([], "nextflow", t.name, t.version, [], None, "none")
    chosen = choose(request, body.environment)
    environment = snapshot(chosen)
    extras = (_resources(body, chosen), None, None)
    workflow = Workflow(location=module.location, revision=None, engine="nextflow")
    source = module_source(t)
    return _create(
        body, request, response, workflow, module.location, source, found, environment, t, extras
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
    extras: tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None],
    warnings: list[dict[str, str]] | None = None,  # the `201` answer's (api §5.12)
) -> dict[str, Any]:
    resources, config_file, config_bytes = extras
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
        default_resources=resources,
        config_file=config_file,
    )
    write_run_manifest(paths.run_dir, manifest)
    payload: dict[str, Any] = {
        "location": location,
        "profiles": body.profiles,
        "params": body.params,
        "environment": environment,
        **extras_payload(resources, config_bytes),
    }
    if workflow.main_script is not None:  # #351
        payload["main_script"] = workflow.main_script
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
    answer: dict[str, Any] = {
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
            "main_script": workflow.main_script,  # #351
        },
        "profiles": body.profiles,
        "params": body.params,
        "target": None if target is None else target.model_dump(),
    }
    if warnings:  # a `required` error with the sources not complete (api §5.12)
        answer["warnings"] = warnings
    return answer


def _check_mounts(request: Request, body: LaunchIn, env: Environment, pipeline: Path) -> None:
    """The paths of `params` the containers would not see (built 2026-11-25, api §5.2), for a
    Snakemake launch with Apptainer deployed by Spectio and no profile (the profile owns its
    software). Read configuration only: no container, no stat, and a path a Snakefile builds
    while it runs is not seen. Refused until the launch binds the paths or the user confirms
    with `allow_unmounted`. The pipeline's directory counts as visible: Snakemake binds it
    (its `apptainer exec` lines, seen on a cluster 2026-11-25), passed as a root of its own —
    never as a bind, which is parsed (CR-05)."""
    if (
        body.workflow.engine != "snakemake"
        or body.profiles
        or "apptainer" not in env.software
        or body.allow_unmounted
    ):
        return
    invisible = unmounted_paths(
        body.params,
        env.apptainer_args,
        home=Path.home(),
        launch_dir=request.app.state.settings.runs_root,
        site_binds=site_bind_paths(),
        env_binds=env_binds(),
        extra_roots=[str(pipeline)],
    )
    if not invisible:
        return
    safe = echoed_paths(invisible)  # only a plain path is echoed or suggested (SEC-mounts-01)
    shown = safe[:5]
    named = ", ".join(shown) or f"{len(invisible)} path{'s' if len(invisible) > 1 else ''}"
    more = len(invisible) - len(shown) if shown else 0
    if more > 0:
        named = f"{named}, and {more} more"
    binds = ",".join(suggested_binds(safe))
    how = (
        f" Add -B {binds} to the Apptainer options of environment {env.name},"
        " or confirm to launch anyway."
        if binds
        else " Confirm to launch anyway."
    )
    raise Invalid("allow_unmounted", f"May not be visible in the containers: {named}.{how}")


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
