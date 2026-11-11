"""Runs that target one Nextflow module or one Snakemake rule (api-and-data-model.md §5.10, #161).

`launch_target` checks the `target` of `POST /runs`; `POST /targets:inspect` serves the Launch
form: a module's inputs (`nextflow module view -o json`, or a local module's `meta.yml`), and a
pipeline's rules with the jobs a rule needs (`snakemake --list-rules`, `snakemake -n <rule>`).
Engine commands run through the login shell, as the engine check does (`spectio.loginshell`),
in an empty temporary directory, their arguments as "$@", never as shell words.
"""

import hashlib
import json
import re
import shlex
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeVar

import yaml
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from spectio.config import Settings
from spectio.loginshell import run_login
from spectio_sdk.targets import REGISTRY_NAME, RULE, VERSION, RunTarget
from spectio_server.api.problems import Invalid, Problem
from spectio_server.api.workflows import _read, load_yaml, local_dir, refuse_control
from spectio_server.files.pool import READ_TIMEOUT_S, FilePool, Stalled

router = APIRouter()

MAX_META_BYTES = 1_048_576  # a `meta.yml`, and an engine's answer
MAX_RULES = 2000
INSPECTIONS = threading.BoundedSemaphore(2)  # engine processes `targets:inspect` may hold at once

T = TypeVar("T")

Engine = Callable[[str, list[str]], tuple[int, str, str]]  # (engine, argv) -> (rc, out, err)


class TargetIn(BaseModel):
    """`target` in the body of `POST /runs`; the rest of the target comes from the server."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["module", "rule"]
    name: str | None = Field(None, max_length=128)
    version: str | None = Field(None, max_length=64)


class InspectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: Literal["nextflow", "snakemake"]
    location: str = Field(max_length=4096)
    version: str | None = Field(None, max_length=64)
    revision: str | None = None
    rule: str | None = Field(None, max_length=128)


@dataclass(frozen=True)
class Module:
    """A module as a launch sees it: `location` is the registry name or the directory."""

    target: RunTarget
    location: str
    inputs: list[dict[str, Any]]
    description: str = ""


def require_flag(settings: Settings) -> None:
    if not settings.features.single_target:
        detail = "Runs that target one module or one rule are off: [features] single_target."
        raise Problem(422, "not-in-this-version", "Not in this version", detail)


def login_engine(settings: Settings) -> Engine:
    """Run the engine of `[engines]` (or the login shell's) in an empty temporary directory."""

    def run(engine: str, argv: list[str]) -> tuple[int, str, str]:
        given = (
            settings.engines.nextflow_cmd
            if engine == "nextflow"
            else settings.engines.snakemake_cmd
        )
        cmd = given or shlex.quote(engine)
        with tempfile.TemporaryDirectory(prefix="spectio-inspect-") as tmp:
            out = run_login(f'cd "$1" && shift && {cmd} "$@"', tmp, *argv, max_bytes=MAX_META_BYTES)
        return out.returncode, out.stdout, out.stderr

    return run


def _engine_failed(engine: str, rc: int, err: str) -> Problem:
    first = next((line.strip() for line in err.splitlines() if line.strip()), f"exit {rc}")
    return Problem(502, "engine-failed", "The engine failed", f"{engine}: {first[:500]}")


# --- Nextflow modules -------------------------------------------------------------------------


def registry_module(settings: Settings, name: str, version: str | None) -> None:
    """The launch grammar of a registry module (§5.10): its name, its namespace, its version."""
    if not REGISTRY_NAME.fullmatch(name):
        raise Invalid("workflow.location", "a registry module: namespace/name, in lower case")
    namespace = name.split("/", 1)[0]
    if namespace not in settings.features.module_namespaces:
        raise Invalid("workflow.location", f"namespace {namespace} is not allowed on this server")
    if version is not None and (version == "latest" or not VERSION.fullmatch(version)):
        raise Invalid("target.version", "a pinned version: letters, digits, '.', '_', '+', '-'")


def _inputs(raw: Any) -> list[dict[str, Any]]:
    """`[{name, type, description}]` from `module view`'s `input` or `meta.yml`'s: a tuple gives
    one entry per item."""
    found: list[dict[str, Any]] = []
    for entry in raw if isinstance(raw, list) else []:
        items = entry.get("items", []) if isinstance(entry, dict) and "items" in entry else entry
        for item in items if isinstance(items, list) else [items]:
            if not isinstance(item, dict):
                continue
            if "name" in item:  # module view
                name, spec = item.get("name"), item
            elif len(item) == 1:  # meta.yml: {name: {type, description}}
                name, spec = next(iter(item.items()))
            else:
                continue
            spec = spec if isinstance(spec, dict) else {}
            if isinstance(name, str):
                found.append(
                    {
                        "name": name,
                        "type": str(spec.get("type") or ""),
                        "description": str(spec.get("description") or "").strip()[:2000],
                    }
                )
    return found


def pooled(files: FilePool, fn: Callable[[], T]) -> T:
    """`fn()` in the file pool, with its timeout: `503` when the file system does not answer."""
    try:
        return files.run(fn, READ_TIMEOUT_S)
    except Stalled as exc:
        raise Problem(503, "runner-offline", "File system not answering", str(exc)) from None


def _module_files(directory: Path) -> tuple[bytes, Any]:
    """`main.nf`'s bytes and `meta.yml`'s value, each a regular file reached through no symlink,
    read without blocking (`workflows._read`), YAML with no alias."""
    try:
        main, meta = _read(directory, "main.nf"), _read(directory, "meta.yml")
    except (OSError, ValueError) as exc:
        raise Invalid("workflow.location", str(exc)) from None
    if main is None or meta is None:
        raise Invalid("workflow.location", "main.nf or meta.yml is missing or not a regular file")
    try:
        return main.encode(), load_yaml(meta)
    except (ValueError, TypeError, RecursionError, yaml.YAMLError):
        raise Invalid("workflow.location", "meta.yml is not YAML this server reads") from None


def local_module(files: FilePool, location: str) -> Module:
    """A module directory: `main.nf` and `meta.yml`, read here; its hash is `main.nf`'s SHA-256."""
    refuse_control("workflow.location", location)
    if not location.startswith("/"):
        raise Invalid("workflow.location", "a local module is an absolute path")
    try:
        directory = local_dir(location)
    except Invalid as exc:
        raise exc.under("workflow") from None
    main, meta = pooled(files, lambda: _module_files(directory))
    if not isinstance(meta, dict):
        raise Invalid("workflow.location", "meta.yml is not a mapping")
    name = str(meta.get("name") or directory.name)[:128]
    version = meta.get("version")
    version = None if version is None else str(version)[:64]
    for value in (name, version or ""):
        refuse_control("workflow.location", value)
    target = RunTarget(
        kind="module",
        name=name,
        version=version,
        hash=hashlib.sha256(main).hexdigest(),
        source="local",
        path=str(directory),
    )
    about = str(meta.get("description") or "")[:2000]
    return Module(target, str(directory), _inputs(meta.get("input")), about)


def module_view(engine: Engine, name: str, version: str | None) -> dict[str, Any]:
    argv = ["module", "view", "-o", "json", *(["-version", version] if version else []), name]
    rc, out, err = engine("nextflow", argv)
    if rc != 0:
        raise _engine_failed("nextflow module view", rc, err or out)
    try:  # a login profile may print first; what follows the JSON is not read
        view = json.JSONDecoder().raw_decode(out, out.index("{"))[0]
    except (ValueError, RecursionError):
        view = None
    if not isinstance(view, dict):
        raise Problem(502, "engine-failed", "The engine failed", "module view: no JSON answer")
    return view


def inspect_module(
    settings: Settings, engine: Engine, files: FilePool, location: str, version: str | None
) -> Module:
    if location.startswith("/"):
        return local_module(files, location)
    registry_module(settings, location, version)
    view = module_view(engine, location, version)
    found = str(view.get("version") or "")
    if not VERSION.fullmatch(found) or (version is not None and found != version):
        raise Problem(502, "engine-failed", "The engine failed", "module view: no pinned version")
    target = RunTarget(
        kind="module",
        name=location,
        version=found,
        source="registry",
    )
    about = str(view.get("description") or "")[:2000]
    return Module(target, location, _inputs(view.get("input")), about)


def launch_module(
    settings: Settings,
    engine: Engine,
    files: FilePool,
    location: str,
    given: TargetIn,
    params: dict[str, Any],
) -> Module:
    """The target of a module launch, checked whole (§5.10): pinned, allowed, inputs by name."""
    if given.name is not None:
        raise Invalid("target.name", "a module's name is its location")
    if location.startswith("/"):
        module = local_module(files, location)
        if given.version is not None and given.version != module.target.version:
            raise Invalid("target.version", "differs from the module's meta.yml")
    else:
        if given.version is None:
            raise Invalid("target.version", "a registry module runs at a pinned version")
        module = inspect_module(settings, engine, files, location, given.version)
    names = {i["name"] for i in module.inputs}
    unknown = sorted(set(params) - names)
    if unknown:
        raise Invalid(f"params.{unknown[0]}", f"the module has no input {unknown[0]}")
    return module


# --- Snakemake rules --------------------------------------------------------------------------

_JOB_LINE = re.compile(r"^(\S+)\s+(\d+)\s*$")


def plan_of(text: str) -> dict[str, Any] | None:
    """The "Job stats" table of a dry run: `{jobs: {rule: n}, total}`, or None."""
    jobs: dict[str, int] = {}
    total = None
    inside = False
    for line in text.splitlines():
        if line.startswith("Job stats:"):
            inside, jobs = True, {}
            continue
        if not inside:
            continue
        if not line.strip():
            if jobs or total is not None:
                break
            continue
        match = _JOB_LINE.match(line.strip())
        if match is None:
            continue
        rule, n = match.group(1), int(match.group(2))
        if rule == "total":
            total = n
        elif RULE.fullmatch(rule):
            jobs[rule] = n
    return None if total is None else {"jobs": jobs, "total": total}


def snakefile_of(directory: Path) -> Path:
    found = directory / "workflow" / "Snakefile"
    return found if found.is_file() else directory / "Snakefile"


def inspect_rules(engine: Engine, directory: Path, rule: str | None) -> dict[str, Any]:
    snakefile = str(snakefile_of(directory))
    rc, out, err = engine("snakemake", ["--snakefile", snakefile, "--list-rules"])
    if rc != 0:
        raise _engine_failed("snakemake --list-rules", rc, err or out)
    rules = [w for w in (line.strip() for line in out.splitlines()) if RULE.fullmatch(w)]
    answer: dict[str, Any] = {"kind": "rule", "rules": rules[:MAX_RULES], "plan": None}
    if rule is None:
        return answer
    if not RULE.fullmatch(rule):
        raise Invalid("rule", "a rule name: letters, digits and '_'")
    if rule not in rules:
        raise Invalid("rule", f"the pipeline has no rule {rule}")
    # `-n` in the empty temporary directory: every job the rule needs from scratch
    rc, out, err = engine("snakemake", ["--snakefile", snakefile, "--directory", ".", rule, "-n"])
    answer["plan"] = plan_of(out + "\n" + err) if rc == 0 else None
    if answer["plan"] is None:
        first = next((s.strip() for s in (err or out).splitlines() if s.strip()), "")
        answer["error"] = first[:500] or "the dry run planned nothing"
    return answer


def launch_rule(given: TargetIn) -> RunTarget:
    if given.name is None or not RULE.fullmatch(given.name):
        raise Invalid("target.name", "a rule name: letters, digits and '_'")
    if given.version is not None:
        raise Invalid("target.version", "a rule has no version")
    return RunTarget(kind="rule", name=given.name, flag="target")


@router.post("/targets:inspect")
def inspect(body: InspectIn, request: Request) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    require_flag(settings)
    if not INSPECTIONS.acquire(blocking=False):
        raise Problem(503, "runner-offline", "Busy", "other inspections are running: try again")
    try:
        return _inspect(body, request, settings)
    finally:
        INSPECTIONS.release()


def _inspect(body: InspectIn, request: Request, settings: Settings) -> dict[str, Any]:
    from spectio_server.api.workflows import resolve  # the launch's own rules

    engine: Engine = request.app.state.target_engine
    if body.engine == "nextflow":
        module = inspect_module(
            settings, engine, request.app.state.files, body.location, body.version
        )
        t = module.target
        return {
            "kind": "module",
            "source": t.source,
            "name": t.name,
            "version": t.version,
            "description": module.description,
            "inputs": module.inputs,
        }
    resolved = resolve(settings.data_dir, body.location, body.revision)
    return inspect_rules(engine, resolved.directory, body.rule)
