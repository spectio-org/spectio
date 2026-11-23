"""`squeue` for the stall check (FU-P3-126, schedulers §3.9): the job IDs SLURM holds now, of
the server user's own jobs, in one call for all of them (CON-SLURM-POLL-05: never `-j` with a
list, which asks slurmctld for the whole job table and filters on the client).

`--states=all` keeps a job that ended within the site's MinJobAge (EMBL login1 7200 s as
given, Slurm's default 300 s: both [to be validated], on slurm-mini too): until slurmctld
forgets it, a job that ended lately is still in `squeue`, maybe not yet in `sacct`.
"""

import logging
import re
import subprocess
import tempfile
import threading
from pathlib import Path

from spectio.runner.sacct import (
    JOB_ID,
    MAX_OUTPUT,
    TIMEOUT_S,
    _kill,
    check_tool,
    sacct_env,
)

log = logging.getLogger(__name__)

_RANGE = re.compile(r"([0-9]{1,12})_\[[^\]]*\]")  # a pending array range: 55_[1-3]
STALL_FILE = ".stalled.json"  # in the runs root: what `spectio doctor` reads (FU-P3-126)


def squeue_argv(path: Path) -> list[str]:
    """The call: the caller's own jobs (`--me`), every state, only the ID."""
    return [str(path), "--me", "--noheader", "--states=all", "--format=%i"]


def squeue_ids(path: Path, timeout_s: float = TIMEOUT_S) -> set[str] | None:
    """The job IDs `squeue` holds now; None when it failed or timed out. Raises Refused for
    a tool that is not accepted, OSError when the tool cannot be read for now (both as
    `sacct`, CR-P3FU106A-04). A line is a job ID; a pending array range `55_[1-3]` gives
    its base `55`, which covers the tasks the watch is on (a running task `55_3` is itself
    only, CR-P3FU126-STALL-02)."""
    check_tool(path, "squeue")
    with (
        tempfile.TemporaryFile() as err,  # a file, not a pipe: it never blocks the tool
        subprocess.Popen(  # noqa: S603 - an argument list of checked values, no shell
            squeue_argv(path),
            env=sacct_env(path),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=err,
            start_new_session=True,
        ) as proc,
    ):
        timer = threading.Timer(timeout_s, _kill, (proc,))
        timer.start()
        try:
            data = proc.stdout.read(MAX_OUTPUT + 1) if proc.stdout else b""
            if len(data) > MAX_OUTPUT:
                _kill(proc)
            code = proc.wait()
        finally:
            timer.cancel()
    if len(data) > MAX_OUTPUT or code != 0:
        log.warning("squeue gave no answer (exit %s, %d bytes)", code, len(data))
        return None
    found: set[str] = set()
    for line in data.decode("utf-8", "replace").splitlines():
        job = line.strip()
        if JOB_ID.fullmatch(job):
            found.add(job)
        elif pending := _RANGE.fullmatch(job):
            found.add(pending[1])
    return found
