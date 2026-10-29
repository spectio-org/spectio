"""Smoke test of one name-holding package, run with the Python of a venv where its wheel is installed.

Usage: python smoke.py <project>
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def cli(project: str) -> None:
    out = subprocess.run([Path(sys.executable).parent / project, "--version"], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "0.0.0", out.stdout


def logger() -> None:
    from snakemake_logger_plugin_spectio import LogHandler, LogHandlerSettings

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp, "events.jsonl")
        handler = LogHandler(None, LogHandlerSettings(file=str(path)))
        record = logging.makeLogRecord({"msg": "Finished jobid: 0", "event": "job_finished", "job_id": 0})
        handler.emit(record)
        handler.close()
        line = json.loads(path.read_text())
        assert line["event"] == "job_finished" and line["job_id"] == 0, line

        # A symlink planted at the target path is refused (O_NOFOLLOW), and its target stays untouched.
        target, link = Path(tmp, "target"), Path(tmp, "link.jsonl")
        target.write_text("")
        os.symlink(target, link)
        try:
            LogHandler(None, LogHandlerSettings(file=str(link)))
        except OSError:
            pass
        else:
            raise AssertionError("a symlinked log file was followed")
        assert target.read_text() == ""


project = sys.argv[1]
logger() if project == "snakemake-logger-plugin-spectio" else cli(project)
print(f"smoke: {project} ok")
