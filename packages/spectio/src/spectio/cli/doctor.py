"""`spectio doctor` (P1 Task 8): one `ok|warn|fail <check> <detail>` line per check of
architecture §7.3 that 0.0.1 needs, and exit 1 on any `fail`."""

import os
import re
import socket
from collections.abc import Mapping
from pathlib import Path

import typer

from spectio.config import NF_SPECTIO_VERSION, Settings, config_path
from spectio.loginshell import run_login, which
from spectio.runner.engines import NEXTFLOW_VERSION, SNAKEMAKE_VERSION, nf_plugin_copy

Result = tuple[str, str, str]  # status, check, detail
_JAVA = re.compile(r'version "([0-9]+)(?:\.([0-9]+))?')
_PLUGINS_BLOCK = re.compile(r"\bplugins\s*\{[^}]*nf-spectio", re.DOTALL)


def _engine(name: str, cmd: str | None, flag: str, pattern: re.Pattern[str]) -> Result:
    if not cmd:
        return "fail", name, "not found on PATH"
    out = run_login(f"{cmd} {flag}")
    match = pattern.search(out.stdout) if out.returncode == 0 else None
    if not match:
        first = (out.stderr or out.stdout).strip().splitlines()[:1]
        return "fail", name, f"`{cmd} {flag}` exited {out.returncode}: {''.join(first)}"
    return "ok", name, f"{match.group(1)} {cmd}"


def _java() -> Result:
    out = run_login("java -version")
    match = _JAVA.search(out.stderr + out.stdout)
    if not match:
        return "warn", "java", "not found on PATH: Nextflow needs Java"
    major = match.group(2) if match.group(1) == "1" else match.group(1)  # 1.8 is Java 8
    return "ok", "java", str(major)


def _tools(local: bool) -> list[Result]:
    """tmux (the heads, the server's session) and sbatch (the engines' task jobs); the runs of
    local mode need neither (P1 Assumption 23)."""
    results: list[Result] = []
    for name, path in which("tmux", "sbatch").items():
        if path:
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
    copy = nf_plugin_copy(env)
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
    elif not copy.is_dir():
        return "fail", check, f"names {want} but {copy} is missing: run spectio init"
    else:
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
    here = socket.gethostname()
    if settings.host == here:
        results.append(("ok", "host", here))
    elif settings.host is None:
        results.append(("warn", "host", "none recorded: run spectio init"))
    else:
        results.append(("warn", "host", f"this is {here}; spectio init recorded {settings.host}"))
    engines = settings.engines
    results.append(_engine("nextflow", engines.nextflow_cmd, "-version", NEXTFLOW_VERSION))
    results.append(_engine("snakemake", engines.snakemake_cmd, "--version", SNAKEMAKE_VERSION))
    results.append(_java())
    results += _tools(settings.executor == "local")
    results.append(_nxf_plugins(env))
    return results


def run_doctor(
    settings: Settings, env: Mapping[str, str] | None = None, mountinfo: Path | None = None
) -> int:
    results = checks(settings, os.environ if env is None else env, mountinfo)
    for status, check, detail in results:
        typer.echo(f"{status} {check} {detail}")
    return 1 if any(status == "fail" for status, _, _ in results) else 0
