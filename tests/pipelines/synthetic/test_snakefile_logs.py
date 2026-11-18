"""The rule logs of the Snakemake twin, on a real fail_demo run (needs snakemake on PATH).

  uv run pytest -q tests/pipelines/synthetic/test_snakefile_logs.py

failure.py:_log_tail reads a Snakemake job's SLURM log, else its first rule log: the .err log
must come first, and the job's stderr must still reach its own stream (the SLURM job log).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

SMK = Path(__file__).resolve().parent / "snakemake"
ERROR = "ERROR synthetic failure: tool exited with code 1"

pytestmark = pytest.mark.skipif(shutil.which("snakemake") is None, reason="needs snakemake")


@pytest.fixture(scope="module")
def fail_demo(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    d = tmp_path_factory.mktemp("fail_demo")
    p = subprocess.run(
        ["snakemake", "--workflow-profile", str(SMK / "profiles" / "fail_demo"), "--retries", "0",
         "-d", str(d), "--config", "fail_mode=exit", "fail_rule=compare", "fail_sample=treatA",
         f"outdir={d}/results"],
        cwd=SMK, capture_output=True, text=True,
    )  # fmt: skip
    assert p.returncode == 1, p.stderr[-2000:]
    return d / "results" / "logs" / "compare", p.stderr


def test_the_err_log_is_declared_first(fail_demo: tuple[Path, str]) -> None:
    logs, stderr = fail_demo
    line = next(x for x in stderr.splitlines() if "log:" in x and "compare/treatA" in x)
    assert line.split("log:", 1)[1].split(",")[0].strip().endswith("compare/treatA.err"), line


def test_error_lines_reach_the_err_log_and_the_job_stream(fail_demo: tuple[Path, str]) -> None:
    logs, stderr = fail_demo
    assert ERROR in (logs / "treatA.err").read_text()
    assert ERROR in stderr  # the job's own stderr: the SLURM job log on a cluster
    out = (logs / "treatA.out").read_text().splitlines()
    assert out and all(x.startswith("INFO ") for x in out)
