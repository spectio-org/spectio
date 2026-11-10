"""BioFlow-Insight as the static producer of a Nextflow graph (graph contract; spike #160).

BioFlow-Insight (MIT, gitlab.liris.cnrs.fr/sharefair/bioflow-insight, 2.1.1) analyses Nextflow
code without running it and writes `graphs/metro_map.json`. It is not a dependency of the server:
its pins (numpy 1.26, sympy 1.9, jpype1) do not fit the workspace, so a site installs it as a
tool (`uv tool install bioflow-insight==2.1.1`), with Graphviz's `dot` on PATH (it lays the map
out with it, and fails without it). The server finds the `bioflow-insight` executable on PATH.

It runs on a local pipeline directory only, never on the hosted service: in a subprocess with a
timeout, a private temporary output directory, the pipeline directory as its working directory,
and an environment reduced to PATH, HOME and the locale. Its output is read with a size cap.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

TIMEOUT_S = 60
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
EXECUTABLE = "bioflow-insight"
_ENV_KEPT = ("PATH", "HOME", "LANG", "LC_ALL", "JAVA_HOME")


def available() -> str | None:
    """The executable's path, when it and Graphviz's `dot` are on PATH."""
    found = shutil.which(EXECUTABLE)
    return found if found and shutil.which("dot") else None


def metro_map(main_nf: Path, timeout_s: float = TIMEOUT_S) -> dict[str, Any] | None:
    """The metro map of the pipeline whose entry is `main_nf`, or None when the tool is not
    installed, fails, times out or writes no map."""
    exe = available()
    if exe is None:
        return None
    env = {k: v for k, v in os.environ.items() if k in _ENV_KEPT}
    with tempfile.TemporaryDirectory(prefix="spectio-bfi-") as out:
        argv = [exe, "--analysis", "metroflow", "--no-render-graphs", "--output-dir", out]
        try:
            done = subprocess.run(  # noqa: S603 - a fixed executable, no shell
                [*argv, str(main_nf)],
                cwd=main_nf.parent,
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=timeout_s,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("bioflow-insight on %s: %s", main_nf, exc)
            return None
        path = Path(out) / "graphs" / "metro_map.json"
        if done.returncode != 0 or not path.is_file():
            log.warning("bioflow-insight on %s: exit %s, no metro map", main_nf, done.returncode)
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
