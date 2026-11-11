"""BioFlow-Insight as the static producer of a Nextflow graph (graph contract; spike #160).

BioFlow-Insight (MIT, gitlab.liris.cnrs.fr/sharefair/bioflow-insight, 2.1.1) analyses Nextflow
code without running it and writes `graphs/metro_map.json`. It is not a dependency of the server:
its pins (numpy 1.26, sympy 1.9, jpype1) do not fit the workspace, so a site installs it as a
tool (`uv tool install bioflow-insight==2.1.1`), with Graphviz's `dot` on PATH (it lays the map
out with it, and fails without it). The server finds the `bioflow-insight` executable on PATH.

It runs on a local pipeline directory only, never on the hosted service: one at a time (a second
call meanwhile falls back at once), in its own process group killed whole on timeout, with a
private temporary directory as its output and its HOME, the pipeline directory as its working
directory, and an environment reduced to PATH, the locale and JAVA_HOME (no proxy, no
JAVA_TOOL_OPTIONS). No network is requested; the process is not sandboxed from one
(SEC-160-02: the tool's Python has no HTTP client, the bundled language server is
[to be validated]). Its output is read with a size cap; its stdout and stderr are discarded.
"""

import contextlib
import json
import logging
import os
import shutil
import signal
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

TIMEOUT_S = 60
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
EXECUTABLE = "bioflow-insight"
_ENV_KEPT = ("PATH", "LANG", "LC_ALL", "JAVA_HOME")
_ONE = threading.Semaphore(1)  # one run at a time on the server (SEC-160-01)


def available() -> str | None:
    """The executable's path, when it and Graphviz's `dot` are on PATH."""
    found = shutil.which(EXECUTABLE)
    return found if found and shutil.which("dot") else None


def metro_map(main_nf: Path, timeout_s: float = TIMEOUT_S) -> dict[str, Any] | None:
    """The metro map of the pipeline whose entry is `main_nf`, or None when the tool is not
    installed, fails, times out or writes no map."""
    exe = available()
    if exe is None or not _ONE.acquire(blocking=False):
        return None
    try:
        return _run(exe, main_nf, timeout_s)
    finally:
        _ONE.release()


def _run(exe: str, main_nf: Path, timeout_s: float) -> dict[str, Any] | None:
    with tempfile.TemporaryDirectory(prefix="spectio-bfi-") as out:
        home = Path(out) / "home"
        home.mkdir()
        env = {k: v for k, v in os.environ.items() if k in _ENV_KEPT} | {"HOME": str(home)}
        argv = [exe, "--analysis", "metroflow", "--no-render-graphs", "--output-dir", out]
        try:
            proc = subprocess.Popen(  # noqa: S603 - a fixed executable, no shell
                [*argv, str(main_nf)],
                cwd=main_nf.parent,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            log.warning("bioflow-insight on %s: %s", main_nf, exc)
            return None
        try:
            code = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)  # its children (dot, java) too
            proc.wait()
            log.warning("bioflow-insight on %s: timed out after %s s", main_nf, timeout_s)
            return None
        path = Path(out) / "graphs" / "metro_map.json"
        if code != 0 or not path.is_file():
            log.warning("bioflow-insight on %s: exit %s, no metro map", main_nf, code)
            return None
        if path.stat().st_size > MAX_OUTPUT_BYTES:
            log.warning("bioflow-insight on %s: metro map too large", main_nf)
            return None
        try:
            found = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            log.warning("bioflow-insight on %s: %s", main_nf, exc)
            return None
    return found if isinstance(found, dict) else None
