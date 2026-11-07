"""Real Snakemake runs with the plugin on PYTHONPATH, as the head script runs them (no install)."""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]  # the directory the head puts on PYTHONPATH
REPO = ROOT.parents[1]
SYNTHETIC = REPO / "tests" / "pipelines" / "synthetic"
FILES = ROOT / "tests" / "workflows" / "files" / "Snakefile"
SNAKEMAKE = Path(sys.executable).parent / "snakemake"  # 9.27.1, from this project's lock
RUN_ID = "run_01K8T7SMKRVN00000000000000"
PLANTED = "planted-in-the-environment-7f3a"  # set in every run's environment: never sent


@dataclass
class SmkRun:
    launch: Path
    spool: Path
    proc: "subprocess.CompletedProcess[str]"

    def files(self) -> list[Path]:
        return sorted(self.spool.glob("*.jsonl")) if self.spool.is_dir() else []

    def lines(self) -> list[dict[str, Any]]:
        return [json.loads(line) for f in self.files() for line in f.read_text().splitlines()]

    def of(self, type_: str) -> list[dict[str, Any]]:
        return [e["data"] for e in self.lines() if e["type"] == type_]


def snakemake(launch: Path, snakefile: Path, *args: str, spool: Path | None = None) -> SmkRun:
    """Run Snakemake 9.27.1 with `--logger spectio` in `launch`, driven: the SPECTIO_* variables
    point at `spool` (default `<launch>/.spectio/events`)."""
    launch.mkdir(parents=True, exist_ok=True)
    if spool is None:
        (launch / ".spectio").mkdir(mode=0o700, exist_ok=True)
        spool = launch / ".spectio" / "events"
    env = {k: v for k, v in os.environ.items() if not k.startswith("SPECTIO_")}
    env |= {
        "PYTHONPATH": str(ROOT),
        "SPECTIO_RUN_ID": RUN_ID,
        "SPECTIO_LAUNCH_N": "1",
        "SPECTIO_SPOOL_DIR": str(spool),
        "SPECTIO_TEST_TOKEN": PLANTED,
    }
    cmd = [str(SNAKEMAKE), "-s", str(snakefile), "--directory", str(launch), "--logger", "spectio"]
    proc = subprocess.run(
        [*cmd, *args], cwd=launch, env=env, capture_output=True, text=True, timeout=300
    )
    return SmkRun(launch, spool, proc)


def synthetic_happy(launch: Path, spool: Path | None = None) -> SmkRun:
    """The synthetic pipeline, happy path, as run_scenarios.py runs it (local, 2 cores)."""
    config = [
        "outdir=results",
        f"samples={SYNTHETIC / 'data' / 'samplesheet.csv'}",
        "chunks=2",
    ]
    smk = SYNTHETIC / "snakemake" / "workflow" / "Snakefile"
    return snakemake(launch, smk, "--cores", "2", "--config", *config, spool=spool)


@pytest.fixture(scope="session")
def smk_run(tmp_path_factory: pytest.TempPathFactory) -> SmkRun:
    return synthetic_happy(tmp_path_factory.mktemp("happy") / "launch")


@pytest.fixture(scope="session")
def files_run(tmp_path_factory: pytest.TempPathFactory) -> SmkRun:
    """The `files` workflow with its `broken` rule failing (it needs `measured`: one order)."""
    launch = tmp_path_factory.mktemp("files") / "launch"
    return snakemake(launch, FILES, "--cores", "2", "--config", "fail=1")
