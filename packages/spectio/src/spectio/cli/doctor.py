"""`spectio doctor` (P1 Task 8): one `ok|warn|fail <check> <detail>` line per check of
architecture §7.3 that 0.0.1 needs, and exit 1 on any `fail`."""

import json
import os
import re
import socket
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import typer

from spectio import catalog, envfile
from spectio.config import MIN_UV, NF_SPECTIO_VERSION, Settings, config_path
from spectio.environments import builtins
from spectio.loginshell import run_login, which
from spectio.runner.engines import (
    NEXTFLOW_VERSION,
    SNAKEMAKE_VERSION,
    existing_copy,
    nf_plugin_copy,
)
from spectio.runner.headscript import status_command
from spectio.runner.rundir import private_dir, read_small, runs_disk
from spectio.runner.sacct import site_accounting
from spectio.runner.squeue import STALL_FILE

Result = tuple[str, str, str]  # status, check, detail
_JAVA = re.compile(r'version "([0-9]+)(?:\.([0-9]+))?')
_UV = re.compile(r"^uv ([0-9]+)\.([0-9]+)\.([0-9]+)\b", re.MULTILINE)
_PLUGINS_BLOCK = re.compile(r"\bplugins\s*\{[^}]*nf-spectio", re.DOTALL)
# 2.8.0 is the first Snakemake SLURM executor plugin that logs job events (its #478: run_job_pre);
# older ones never do, and Spectio then shows no task of a Snakemake SLURM run.
MIN_SLURM_PLUGIN = (2, 8, 0)
_PLUGIN_VERSION = re.compile(r"([0-9]+)\.([0-9]+)(?:\.([0-9]+))?")
_PLUGIN_PROBE = """\
import importlib.metadata as m, os, sys
me = sys.modules.pop("sitecustomize")
sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != os.path.dirname(__file__)]
try:  # the site's own sitecustomize still runs: EasyBuild's sets the module's search path
    import sitecustomize  # noqa: F401
except Exception:
    sys.modules["sitecustomize"] = me
try:
    version = m.version("snakemake-executor-plugin-slurm")
except m.PackageNotFoundError:
    version = "none"
path = os.environ["SPECTIO_PROBE_OUT"]
try:  # only into this user's own directory, never through a link
    if os.stat(os.path.dirname(path)).st_uid == os.getuid():
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
        with os.fdopen(os.open(path, flags, 0o600), "w") as out:
            out.write(version)
except OSError:
    pass
"""


def _engine(name: str, cmd: str | None, flag: str, pattern: re.Pattern[str]) -> Result:
    if not cmd:
        return "fail", name, "not found on PATH"
    out = run_login(f"{cmd} {flag}")
    match = pattern.search(out.stdout) if out.returncode == 0 else None
    if not match:
        first = (out.stderr or out.stdout).strip().splitlines()[:1]
        return "fail", name, f"`{cmd} {flag}` exited {out.returncode}: {''.join(first)}"
    return "ok", name, f"{match.group(1)} {cmd}"


def _java(nextflow_ok: bool) -> Result:
    """Java for Nextflow: fine when on the PATH, and also when only Nextflow works without it,
    as a site's Nextflow wrapper or module loads its own Java."""
    out = run_login("java -version")
    match = _JAVA.search(out.stderr + out.stdout)
    if not match:
        if nextflow_ok:
            return "ok", "java", "not on the login shell's PATH; Nextflow works without it"
        return "warn", "java", "not found on PATH: Nextflow needs Java"
    major = match.group(2) if match.group(1) == "1" else match.group(1)  # 1.8 is Java 8
    return "ok", "java", str(major)


def uv_version(out: str) -> tuple[int, int, int] | None:
    """The version in the output of `uv --version` ("uv 0.13.7 (abc 2026-10-01)"), or None."""
    match = _UV.search(out)
    return (int(match[1]), int(match[2]), int(match[3])) if match else None


def _uv(path: str | None) -> Result:
    """The uv on the login PATH: only installing Spectio needs it, so an old one is a warning
    and a missing one is fine (FU-P3-73)."""
    if not path:
        return "ok", "uv", "not found on the login shell's PATH: only installing Spectio needs it"
    out = run_login('"$1" --version', path)
    first = "".join((out.stderr or out.stdout).strip().splitlines()[:1])
    if out.returncode != 0:
        return "warn", "uv", f"`{path} --version` exited {out.returncode}: {first}"
    version = uv_version(out.stdout)
    if version is None:
        return "warn", "uv", f"`{path} --version` printed no version: {first}"
    found, minimum = (".".join(map(str, v)) for v in (version, MIN_UV))
    if version < MIN_UV:
        return (
            "warn",
            "uv",
            f"{found} {path} is older than {minimum}: its Pythons may carry an SQLite that "
            "Spectio refuses; upgrade it (uv self update, or its installer)",
        )
    return "ok", "uv", f"{found} {path}"


def _tools(local: bool, paths: Mapping[str, str | None]) -> list[Result]:
    """tmux (the heads, the server's session) and sbatch (the engines' task jobs); the runs of
    local mode need neither (P1 Assumption 23)."""
    results: list[Result] = []
    for name in ("tmux", "sbatch"):
        if path := paths[name]:
            results.append(("ok", name, path))
        elif not local:
            results.append(("fail", name, "not found on PATH"))
        elif name == "sbatch":
            results.append(("ok", name, "not needed in local mode"))
        else:
            results.append(("warn", name, "not found on PATH: spectio serve --detach needs it"))
    return results


def _nxf_plugins(env: Mapping[str, str]) -> Result:
    """The check of architecture §13.8 (spectio doctor): the variable that enables nf-spectio."""
    check, want = "nxf_plugins_default", f"nf-spectio@{NF_SPECTIO_VERSION}"
    nxf_home = Path(env.get("NXF_HOME") or Path.home() / ".nextflow")
    try:
        copy = nf_plugin_copy(env)
    except ValueError as exc:  # a relative NXF_HOME or NXF_PLUGINS_DIR (SEC-P3T09-05)
        return "fail", check, str(exc)
    value = env.get("NXF_PLUGINS_DEFAULT")
    ours = [p.strip() for p in (value or "").split(",") if p.strip().split("@")[0] == "nf-spectio"]
    if value is None:
        result = (
            "ok",
            check,
            f"unset; for a run from a terminal: NXF_PLUGINS_DEFAULT={want} nextflow run …",
        )
    elif value.strip() == "false":
        result = ("warn", check, "is false: runs from a terminal load no nf-spectio")
    elif not ours:
        result = ("warn", check, f"{value} has no nf-spectio: runs from a terminal are not seen")
    elif ours != [want]:
        result = ("warn", check, f"names {', '.join(ours)}, not {want}")
    else:
        try:  # the launcher's own check of the copy (CR-P3T09-R5-02)
            present = existing_copy(copy)
        except OSError as exc:
            return "fail", check, str(exc)
        if not present:
            return "fail", check, f"names {want} but {copy} is missing: run spectio init"
        result = ("ok", check, value)
    try:
        text = (nxf_home / "config").read_text(errors="replace")
    except OSError:
        text = ""
    if result[0] == "ok" and _PLUGINS_BLOCK.search(text):
        return (
            "warn",
            check,
            f"a plugins block in {nxf_home / 'config'} names nf-spectio: remove it",
        )
    return result


def _environments(settings: Settings) -> Result:
    """The environments file (FU-P3-86b, api §5.4): its path, state and the default. A file
    that cannot be used is a warning: launches with a built-in still work."""
    path = envfile.environments_path()
    found = envfile.read_file(path, [b.environment.name for b in builtins(settings)])
    default = (found.state == "ok" and found.default) or settings.executor
    state = found.state if found.detail is None else f"{found.state} ({found.detail})"
    status = "ok" if found.state in ("missing", "ok") else "warn"
    return status, "environments", f"{path}: {state}, default {default}"


def _catalog() -> Result:
    """The catalog file (FU-P3-87a, api §5.6): its path and state. A file that cannot be used
    is a warning: the free Pipeline field still works."""
    path = catalog.catalog_path()
    found = envfile.read_kind(catalog.KIND, path, ())
    state = found.state if found.detail is None else f"{found.state} ({found.detail})"
    return ("ok" if found.state in ("missing", "ok") else "warn"), "catalog", f"{path}: {state}"


def _utc(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%d %H:%M UTC")


def _stalled(runs_root: Path, shown: int = 5) -> Result:
    """The runs the server last saw stalled (FU-P3-126, schedulers §3.9): tasks running whose
    SLURM jobs are gone from squeue and sacct, from the server's stall file, read with no link
    followed. A missing file is none; one that cannot be read is a warning."""
    try:
        with private_dir(runs_root) as fd:
            data = read_small(fd, STALL_FILE)
        if data is None:
            return "ok", "stalled_runs", "none"
        body = json.loads(data)
        if not isinstance(body, dict) or body.get("v") != 1:
            raise ValueError("not a stall file of version 1")
        found = [
            f"{run}: {int(s['tasks'])} tasks running, their SLURM jobs gone from squeue and "
            f"sacct since {_utc(float(s['since']))}"
            for run, s in sorted(body["runs"].items())
        ]
        checked = _utc(float(body["checked"]))
    except FileNotFoundError:  # no runs root yet
        return "ok", "stalled_runs", "none"
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        RecursionError,
        OverflowError,
    ) as exc:
        return "warn", "stalled_runs", f"{STALL_FILE} not read: {exc}"
    if not found:
        return "ok", "stalled_runs", "none"
    more = f"; +{len(found) - shown} more" if len(found) > shown else ""
    return "warn", "stalled_runs", "; ".join(found[:shown]) + f"{more} (checked {checked})"


def _slurm_accounting(settings: Settings) -> Result:
    """FU-P3-106b (inbox #156 item 1): what Snakemake's SLURM plugin will poll this site's
    jobs with, once the site's accounting is known."""
    if (cmd := status_command(site_accounting(settings.slurm.sacct))) is None:
        return (
            "warn",
            "slurm_accounting",
            "unknown (the reason is logged as a warning): Snakemake keeps its SLURM plugin's"
            " default",
        )
    return (
        "ok",
        "slurm_accounting",
        f"{'on' if cmd == 'sacct' else 'off'}: Snakemake polls its SLURM jobs with {cmd}",
    )


def _slurm_plugin(cmd: str) -> Result:
    """The version of Snakemake's SLURM executor plugin, asked through PYTHONPATH, the way the
    head script gives Snakemake the Spectio logger plugin: a sitecustomize.py there makes the
    Python that the configured command itself runs answer — also when a wrapper script loads a
    module first, or the command is a line like `pixi run snakemake`. MIN_SLURM_PLUGIN is the
    first that logs job events, without which Spectio shows no task of a Snakemake SLURM run;
    whatever stands in the way is a warning, so the line never fails a doctor run."""
    check, want = "snakemake_slurm_plugin", ".".join(map(str, MIN_SLURM_PLUGIN))
    need = f"Snakemake SLURM runs need snakemake-executor-plugin-slurm {want} or later"

    def unknown(reason: str) -> Result:
        return "warn", check, f"version unknown ({reason}): {need}"

    with tempfile.TemporaryDirectory() as tmp:  # the probe, private and gone after the run
        (Path(tmp) / "sitecustomize.py").write_text(_PLUGIN_PROBE, encoding="utf-8")
        answer_file = Path(tmp) / "plugin-version"
        out = run_login(
            'export PYTHONPATH="$1${PYTHONPATH:+:$PYTHONPATH}" SPECTIO_PROBE_OUT="$2"; '
            f"{cmd} --version",
            tmp,
            str(answer_file),
        )
        try:
            with answer_file.open("rb") as file:
                answer = file.read(100).decode(errors="replace").strip()
        except OSError:
            answer = None
    if out.returncode == 124:
        return unknown("timed out")
    if answer is None:
        return unknown("Snakemake's Python did not load the probe")
    if answer == "none":
        return unknown("not installed")
    found = _PLUGIN_VERSION.search(answer)
    if found is None:
        return unknown("printed no version")
    if (int(found[1]), int(found[2]), int(found[3] or 0)) < MIN_SLURM_PLUGIN:
        return (
            "warn",
            check,
            f"{found[0]}: older than {want}, which Spectio needs to see the jobs of a Snakemake "
            f"SLURM run; install snakemake-executor-plugin-slurm>={want}",
        )
    return "ok", check, found[0]


def checks(
    settings: Settings, env: Mapping[str, str], mountinfo: Path | None = None
) -> list[Result]:
    path = config_path()
    results: list[Result] = [
        ("ok", "config", str(path))
        if path.is_file()
        else ("fail", "config", f"{path} is missing: run spectio init")
    ]
    try:
        import spectio_server.bootstrap as server  # the one import of the server (architecture §6)
    except ImportError:
        results.append(("warn", "db_dir", "spectio[server] is not installed: no database checks"))
    else:
        try:
            db_dir = settings.db_dir or server.preferred_db_dir()  # not created here
        except server.UnsafeDatabase as exc:
            results.append(("fail", "db_dir", str(exc)))
        else:
            results += server.db_checks(db_dir, mountinfo, fallback=settings.db_dir is None)
    results += [_environments(settings), _catalog()]
    status, detail = runs_disk(settings.runs_root)  # a `warn` at most (FU-P3-74)
    results.append((status, "runs_disk", detail))
    results.append(_stalled(settings.runs_root))
    here = socket.gethostname()
    if settings.host == here:
        results.append(("ok", "host", here))
    elif settings.host is None:
        results.append(("warn", "host", "none recorded: run spectio init"))
    else:
        results.append(("warn", "host", f"this is {here}; spectio init recorded {settings.host}"))
    engines = settings.engines
    nextflow = _engine("nextflow", engines.nextflow_cmd, "-version", NEXTFLOW_VERSION)
    results.append(nextflow)
    snakemake = _engine("snakemake", engines.snakemake_cmd, "--version", SNAKEMAKE_VERSION)
    results.append(snakemake)
    results.append(_java(nextflow[0] == "ok"))
    paths = which("tmux", "sbatch", "uv")
    results += _tools(settings.executor == "local", paths)
    if settings.executor == "slurm":
        results.append(_slurm_accounting(settings))
        if snakemake[0] == "ok" and (cmd := engines.snakemake_cmd) is not None:
            results.append(_slurm_plugin(cmd))
    results.append(_uv(paths["uv"]))
    results.append(_nxf_plugins(env))
    return results


def run_doctor(
    settings: Settings, env: Mapping[str, str] | None = None, mountinfo: Path | None = None
) -> int:
    results = checks(settings, os.environ if env is None else env, mountinfo)
    for status, check, detail in results:
        typer.echo(f"{status} {check} {detail}")
    return 1 if any(status == "fail" for status, _, _ in results) else 0
