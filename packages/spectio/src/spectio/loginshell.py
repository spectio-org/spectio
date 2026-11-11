"""Commands through the user's login shell, as the head script runs the engines (P1
Assumptions 13 and 14): `bash -l` with a cleared environment, so that the user's modules and
PATH apply and nothing from Spectio's own environment does."""

import contextlib
import os
import selectors
import shutil
import signal
import subprocess
import time

KEEP = ("HOME", "USER", "LOGNAME", "SHELL", "LANG", "TMPDIR")  # P1 Assumption 13
TIMEOUT_S = 30
_MARK = "\x1espectio\t"  # tells our lines from what the user's profile prints


def run_login(
    script: str, *args: str, max_bytes: int | None = None
) -> subprocess.CompletedProcess[str]:
    """`bash -lc script spectio args…`; `args` reach the script as "$@", never as shell words.
    A timeout gives return code 124, as timeout(1) does, and kills the command's whole process
    group, so that nothing it started keeps running (SEC-P3T08-04); a child that left the group
    and holds the pipes delays it by a few seconds at most (SEC-P3T09-R5-04). With `max_bytes`,
    more output than that (stdout and stderr together) kills the group too: return code 125
    (SEC-161S-06)."""
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
        if max_bytes is not None:
            return _capped(proc, argv, max_bytes)
        try:
            out, err = proc.communicate(timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            _kill(proc)
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:  # a child that left the group holds the pipes
                for pipe in (proc.stdout, proc.stderr):
                    if pipe is not None:
                        pipe.close()
                proc.wait(timeout=5)
            return subprocess.CompletedProcess(argv, 124, "", f"timed out after {TIMEOUT_S} s")
    return subprocess.CompletedProcess(argv, proc.returncode, out, err)


def _kill(proc: "subprocess.Popen[str]") -> None:
    with contextlib.suppress(ProcessLookupError):  # it ended just then
        os.killpg(proc.pid, signal.SIGKILL)


def _capped(
    proc: "subprocess.Popen[str]", argv: list[str], max_bytes: int
) -> subprocess.CompletedProcess[str]:
    """Both pipes read in chunks until they close, the timeout, or `max_bytes`."""
    out_fd, err_fd = (p.fileno() for p in (proc.stdout, proc.stderr) if p is not None)
    got = {out_fd: bytearray(), err_fd: bytearray()}
    deadline = time.monotonic() + TIMEOUT_S
    with selectors.DefaultSelector() as sel:
        for fd in got:
            sel.register(fd, selectors.EVENT_READ)
        while sel.get_map():
            left = deadline - time.monotonic()
            ready = sel.select(left) if left > 0 else []
            if not ready:
                _kill(proc)
                return subprocess.CompletedProcess(argv, 124, "", f"timed out after {TIMEOUT_S} s")
            for key, _ in ready:
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    sel.unregister(key.fd)
                got[key.fd] += chunk
            if sum(map(len, got.values())) > max_bytes:
                _kill(proc)
                out = got[out_fd][:max_bytes].decode(errors="replace")
                return subprocess.CompletedProcess(
                    argv, 125, out, f"output larger than {max_bytes} bytes"
                )
    try:
        code = proc.wait(max(deadline - time.monotonic(), 0))
    except subprocess.TimeoutExpired:
        _kill(proc)
        return subprocess.CompletedProcess(argv, 124, "", f"timed out after {TIMEOUT_S} s")
    out, err = (got[fd].decode(errors="replace") for fd in (out_fd, err_fd))
    return subprocess.CompletedProcess(argv, code, out, err)


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
