"""Commands through the user's login shell, as the head script runs the engines (P1
Assumptions 13 and 14): `bash -l` with a cleared environment, so that the user's modules and
PATH apply and nothing from Spectio's own environment does."""

import contextlib
import os
import shutil
import signal
import subprocess

KEEP = ("HOME", "USER", "LOGNAME", "SHELL", "LANG", "TMPDIR")  # P1 Assumption 13
TIMEOUT_S = 30
_MARK = "\x1espectio\t"  # tells our lines from what the user's profile prints


def run_login(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    """`bash -lc script spectio args…`; `args` reach the script as "$@", never as shell words.
        A timeout gives return code 124, as timeout(1) does, and kills the command's whole process
        group, so that nothing it started keeps running (SEC-P3T08-04); a child that left the group
    and holds the pipes delays it by a few seconds at most (SEC-P3T09-R5-04)."""
    bash = shutil.which("bash") or "/bin/bash"
    env = {k: os.environ[k] for k in KEEP if k in os.environ}
    argv = [bash, "-lc", script, "spectio", *args]
    with subprocess.Popen(  # noqa: S603 - an argument list, no shell of ours
        argv,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    ) as proc:
        try:
            out, err = proc.communicate(timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):  # it ended just then
                os.killpg(proc.pid, signal.SIGKILL)
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:  # a child that left the group holds the pipes
                for pipe in (proc.stdout, proc.stderr):
                    if pipe is not None:
                        pipe.close()
                proc.wait(timeout=5)
            return subprocess.CompletedProcess(argv, 124, "", f"timed out after {TIMEOUT_S} s")
    return subprocess.CompletedProcess(argv, proc.returncode, out, err)


def which(*names: str) -> dict[str, str | None]:
    """The absolute path of each of `names` on the login shell's PATH, or None."""
    script = f'for c in "$@"; do printf "{_MARK}%s\\t%s\\n" "$c" "$(command -v -- "$c")"; done'
    found: dict[str, str | None] = dict.fromkeys(names)
    for line in run_login(script, *names).stdout.split("\n"):  # not splitlines: \x1e splits
        if line.startswith(_MARK):
            name, _, path = line.removeprefix(_MARK).partition("\t")
            if name in found and path.startswith("/"):  # not an alias or a function
                found[name] = path
    return found
