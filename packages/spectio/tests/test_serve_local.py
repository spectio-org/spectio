"""heads() in tests/e2e/serve-local.sh, whose PIDs stop() signals as process groups: it names a
head only from a strictly parsed head.pid that matches a live group leader on this boot
(SEC-P3T20-02; spec §15.3 req. 10 to 12)."""

import re
import shutil
import signal
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
BASH = shutil.which("bash") or "/bin/bash"
BOOT = Path("/proc/sys/kernel/random/boot_id")

pytestmark = pytest.mark.skipif(not BOOT.exists(), reason="needs Linux /proc")


def heads_function() -> str:
    text = (REPO / "tests/e2e/serve-local.sh").read_text()
    match = re.search(r"^heads\(\) \{\n.*?^\}\n", text, re.M | re.S)
    assert match, "heads() not found in serve-local.sh"
    return match.group(0)


def start_time(pid: int) -> str:
    stat = Path(f"/proc/{pid}/stat").read_text()
    return stat.rsplit(") ", 1)[1].split()[19]


def run_heads(home: Path) -> list[str]:
    script = f'set -euo pipefail\nhome={home}\n{heads_function()}live=$(heads)\necho "$live"\n'
    out = subprocess.run([BASH, "-c", script], capture_output=True, text=True, check=True)
    return out.stdout.split()


def write_pid(home: Path, name: str, line: str) -> Path:
    spectio = home / "runs" / name / "launch" / ".spectio"
    spectio.mkdir(parents=True)
    (spectio / "head.pid").write_text(line)
    return spectio / "head.pid"


def test_heads_names_a_live_group_leader_and_refuses_forgeries(tmp_path: Path) -> None:
    boot = BOOT.read_text().strip()
    head = subprocess.Popen(["sleep", "30"], start_new_session=True)  # noqa: S607
    try:
        pid, start = head.pid, start_time(head.pid)
        write_pid(tmp_path, "real", f"{pid} {pid} {start} {boot} host\n")
        # PID 1: stop() would run `kill -TERM -- -1`
        write_pid(tmp_path, "init", f"1 1 {start_time(1)} {boot} host\n")
        # another boot, loose syntax, and a symlink to a valid file
        write_pid(tmp_path, "boot", f"{pid} {pid} {start} {'0' * 8}-0000-0000-0000-{'0' * 12} h\n")
        write_pid(tmp_path, "loose", f"{pid} {pid} {start}\n")
        link = tmp_path / "runs" / "link" / "launch" / ".spectio"
        link.mkdir(parents=True)
        (link / "head.pid").symlink_to(tmp_path / "runs/real/launch/.spectio/head.pid")
        assert run_heads(tmp_path) == [str(pid)]
    finally:
        head.send_signal(signal.SIGKILL)
        head.wait()


def test_heads_refuses_a_pid_that_does_not_lead_its_group(tmp_path: Path) -> None:
    boot = BOOT.read_text().strip()
    child = subprocess.Popen(["sleep", "30"])  # noqa: S607 - same group as pytest
    try:
        pid = child.pid
        write_pid(tmp_path, "child", f"{pid} {pid} {start_time(pid)} {boot} host\n")
        assert run_heads(tmp_path) == []
    finally:
        child.kill()
        child.wait()
