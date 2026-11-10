"""Runs that target one Nextflow module or one Snakemake rule (api-and-data-model.md §5.9, #161).

`launch_target` checks the `target` of `POST /runs`; `POST /targets:inspect` serves the Launch
form: a module's inputs (`nextflow module view -o json`, or a local module's `meta.yml`), and a
pipeline's rules with the jobs a rule needs (`snakemake --list-rules`, `snakemake -n <rule>`).
Engine commands run through the login shell, as the engine check does (`spectio.loginshell`),
in an empty temporary directory, their arguments as "$@", never as shell words.
"""

import hashlib
import re
import shlex
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from spectio.config import Settings
from spectio.loginshell import run_login
from spectio_sdk.targets import REGISTRY_NAME, RULE, VERSION, RunTarget
from spectio_server.api.problems import Invalid, Problem
from spectio_server.api.workflows import refuse_control

router = APIRouter()

MAX_META_BYTES = 1_048_576  # a `meta.yml`, and an engine's answer
MAX_RULES = 2000

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
            out = run_login(f'cd "$1" && shift && {cmd} "$@"', tmp, *argv)
        return out.returncode, out.stdout, out.stderr

    return run


def _engine_failed(engine: str, rc: int, err: str) -> Problem:
    first = next((line.strip() for line in err.splitlines() if line.strip()), f"exit {rc}")
    return Problem(502, "engine-failed", "The engine failed", f"{engine}: {first[:500]}")


# --- Nextflow modules -------------------------------------------------------------------------


def registry_module(settings: Settings, name: str, version: str | None) -> None:
    """The launch grammar of a registry module (§5.9): its name, its namespace, its version."""
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


def _read_small(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise Invalid("workflow.location", f"{path.name} is missing or not a regular file")
    with path.open("rb") as f:
        data = f.read(MAX_META_BYTES + 1)
    if len(data) > MAX_META_BYTES:
        raise Invalid("workflow.location", f"{path.name} is larger than 1 MiB")
    return data


def local_module(location: str) -> tuple[Module, dict[str, Any]]:
    """A module directory: `main.nf` and `meta.yml`, read here; its hash is `main.nf`'s SHA-256."""
    refuse_control("workflow.location", location)
    directory = Path(location)
    if not directory.is_absolute() or not directory.is_dir():
        raise Invalid("workflow.location", f"{location} is not a directory this account can read")
    main = _read_small(directory / "main.nf")
    try:
        meta = yaml.safe_load(_read_small(directory / "meta.yml"))
    except yaml.YAMLError:
        raise Invalid("workflow.location", "meta.yml is not YAML") from None
    if not isinstance(meta, dict):
        raise Invalid("workflow.location", "meta.yml is not a mapping")
    name = str(meta.get("name") or directory.name)[:128]
    version = meta.get("version")
    target = RunTarget(
        kind="module",
        name=name,
        version=None if version is None else str(version)[:64],
        hash=hashlib.sha256(main).hexdigest(),
        source="local",
        path=str(directory),
    )
    about = str(meta.get("description") or "")[:2000]
    return Module(target, str(directory), _inputs(meta.get("input")), about), meta


def module_view(engine: Engine, name: str, version: str | None) -> dict[str, Any]:
    argv = ["module", "view", "-o", "json", *(["-version", version] if version else []), name]
    rc, out, err = engine("nextflow", argv)
    if rc != 0:
        raise _engine_failed("nextflow module view", rc, err or out)
    if len(out) > MAX_META_BYTES:
        raise Problem(502, "engine-failed", "The engine failed", "module view: answer too large")
    start = out.find("{")  # a login profile may print first
    try:
        view = yaml.safe_load(out[start:]) if start >= 0 else None  # JSON is YAML
    except yaml.YAMLError:
        view = None
    if not isinstance(view, dict):
        raise Problem(502, "engine-failed", "The engine failed", "module view: no JSON answer")
    return view


def inspect_module(
    settings: Settings, engine: Engine, location: str, version: str | None
) -> Module:
    if location.startswith("/"):
        return local_module(location)[0]
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
    settings: Settings, engine: Engine, location: str, given: TargetIn, params: dict[str, Any]
) -> Module:
    """The target of a module launch, checked whole (§5.9): pinned, allowed, inputs by name."""
    if location.startswith("/"):
        module = local_module(location)[0]
        if given.version is not None and given.version != module.target.version:
            raise Invalid("target.version", "differs from the module's meta.yml")
    else:
        if given.version is None:
            raise Invalid("target.version", "a registry module runs at a pinned version")
        module = inspect_module(settings, engine, location, given.version)
    names = {i["name"] for i in module.inputs}
    unknown = sorted(set(params) - names) if names else []
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
    from spectio_server.api.workflows import resolve  # the launch's own rules

    settings: Settings = request.app.state.settings
    require_flag(settings)
    engine: Engine = request.app.state.target_engine
    if body.engine == "nextflow":
        module = inspect_module(settings, engine, body.location, body.version)
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
