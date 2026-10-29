"""Smoke test of one name-holding package, run with the Python of a venv where its wheel is installed.

Usage: python smoke.py <project>
"""

import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path


def cli(project: str) -> None:
    out = subprocess.run([Path(sys.executable).parent / project, "--version"], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "0.0.0", out.stdout


def refused(handler_cls, settings) -> bool:
    try:
        handler_cls(None, settings).close()
    except OSError:
        return True
    return False


class Hung(Exception):
    """Not an OSError, so refused() lets it through."""


def raise_hung(signum, frame):
    raise Hung


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
        assert refused(LogHandler, LogHandlerSettings(file=str(link))), "a symlinked log file was followed"
        assert target.read_text() == ""

        # A second hard link to the file is refused.
        hard = Path(tmp, "hard.jsonl")
        os.link(target, hard)
        assert refused(LogHandler, LogHandlerSettings(file=str(hard))), "a hard-linked log file was opened"

        # A file owned by another user is refused; os.getuid is patched, since the test runs without root.
        real_getuid = os.getuid
        os.getuid = lambda: real_getuid() + 1
        try:
            assert refused(LogHandler, LogHandlerSettings(file=str(path))), "another user's log file was opened"
        finally:
            os.getuid = real_getuid

        # A FIFO planted at the path is refused (ENXIO with no reader) without blocking; 5 s alarm as a guard.
        fifo = Path(tmp, "fifo.jsonl")
        os.mkfifo(fifo, 0o600)
        signal.signal(signal.SIGALRM, raise_hung)
        signal.alarm(5)
        try:
            assert refused(LogHandler, LogHandlerSettings(file=str(fifo))), "a FIFO log file was opened"
        except Hung:
            raise AssertionError("opening a FIFO log file blocked") from None
        finally:
            signal.alarm(0)

        # An existing file of ours with loose permissions is tightened to 0600.
        loose = Path(tmp, "loose.jsonl")
        loose.touch()
        loose.chmod(0o666)
        LogHandler(None, LogHandlerSettings(file=str(loose))).close()
        assert loose.stat().st_mode & 0o777 == 0o600, oct(loose.stat().st_mode)

        # No settings (allowed by the interface's type): the default file in the working directory.
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            LogHandler(None, None).close()
        finally:
            os.chdir(cwd)
        assert Path(tmp, "spectio-events.jsonl").exists()


project = sys.argv[1]
logger() if project == "snakemake-logger-plugin-spectio" else cli(project)
print(f"smoke: {project} ok")
