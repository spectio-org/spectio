"""`sacct_jobs` against a real Slurm with accounting: `dev/slurm/native.sh up` in a cloud session
(FU-P3-66), then `SPECTIO_NATIVE_SLURM=1 uv run pytest -m native_slurm`. Skipped unless `sacct`
and `sbatch` are on PATH and SPECTIO_NATIVE_SLURM=1. A job that holds about 100 MB runs from a
directory of its own; its row is bound to that WorkDir and to nothing else (FU-P3-53, inbox #116
rule 10 (b))."""

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from spectio.runner.sacct import Found, sacct_jobs

SACCT, SBATCH = shutil.which("sacct"), shutil.which("sbatch")
pytestmark = [
    pytest.mark.native_slurm,
    pytest.mark.skipif(
        SACCT is None or SBATCH is None or os.environ.get("SPECTIO_NATIVE_SLURM") != "1",
        reason="needs dev/slurm/native.sh up and SPECTIO_NATIVE_SLURM=1",
    ),
]
MIB = 1024**2
# Touch every page of 100 MiB, then outlive two JobAcctGatherFrequency=5 samples.
JOB = (
    'python3 -c "b = bytearray(100 * 1024 * 1024); b[::4096] = b\\"x\\" * len(b[::4096]); '
    'import time; time.sleep(12)"'
)


def test_sacct_jobs_real_row_bound_to_its_workdir(tmp_path: Path) -> None:
    assert SACCT is not None and SBATCH is not None
    work, other = tmp_path / "launch", tmp_path / "other"
    work.mkdir()
    other.mkdir()
    launched = time.time()
    job = subprocess.run(
        [SBATCH, "--parsable", "--wait", "--mem=200M", f"--chdir={work}", "--wrap", JOB],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    ).stdout.strip()

    found: Found | None = None
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:  # the accounting record lands after the job ends
        found = sacct_jobs({job: {str(work): launched}}, sacct=Path(SACCT))
        row = (found or {}).get(job, {}).get(str(work))
        if row is not None and row.state == "COMPLETED" and row.max_rss_bytes is not None:
            break
        time.sleep(1)
    assert found is not None
    row = found[job][str(work)]
    assert row.state == "COMPLETED"
    assert row.exit_code == 0
    assert row.max_rss_bytes is not None and row.max_rss_bytes > 50 * MIB
    assert row.req_mem_bytes == 200 * MIB
    assert row.work_dir == str(work)
    assert row.total_cpu_s is not None

    assert sacct_jobs({job: {str(other): launched}}, sacct=Path(SACCT)) == {}
