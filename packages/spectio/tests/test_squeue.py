"""`squeue` for the stall check (FU-P3-126, schedulers §3.9): which of the user's job IDs
SLURM holds now, in one call for all of them (CON-SLURM-POLL-05).

A fake `squeue` in a directory of its own (`slurm-mini`, P1 Task 22, is not built): it records
its argument list in `calls.jsonl` and prints `out.txt`. The arguments, and `--states=all`
keeping a job that ended within the site's MinJobAge, stay [to be validated] on a real SLURM.
"""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from spectio.runner import sacct
from spectio.runner.squeue import squeue_argv, squeue_ids

FAKE = """#!{python}
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "calls.jsonl"), "a") as f:
    f.write(json.dumps({{"argv": sys.argv}}) + "\\n")
sys.stdout.write(open(os.path.join(here, "out.txt")).read())
"""


class Fake:
    def __init__(self, root: Path) -> None:
        self.dir = root / "slurm" / "bin"
        self.dir.mkdir(parents=True)
        self.path = self.dir / "squeue"
        self.path.write_text(FAKE.format(python=sys.executable))
        self.path.chmod(0o755)
        self.output("")

    def output(self, text: str) -> None:
        (self.dir / "out.txt").write_text(text)

    def calls(self) -> list[dict[str, Any]]:
        log = self.dir / "calls.jsonl"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines()]


@pytest.fixture
def fakebin(tmp_path: Path) -> Fake:  # this module's: a fake squeue, not the engines' fakes
    return Fake(tmp_path)


def test_squeue_argv(fakebin: Fake) -> None:
    """One call for every job, never `-j` with a list (CON-SLURM-POLL-05): the caller's own
    jobs, every state, only the ID."""
    assert squeue_argv(fakebin.path) == [
        str(fakebin.path),
        "--me",
        "--noheader",
        "--states=all",
        "--format=%i",
    ]
    assert squeue_ids(fakebin.path) == set()
    assert fakebin.calls()[0]["argv"] == squeue_argv(fakebin.path)


def test_squeue_ids_and_arrays(fakebin: Fake) -> None:
    """Each line is a job ID; only a pending array range `55_[1-3]` keeps its base `55`: a
    running array task `8812402_3` does not cover its siblings (CR-P3FU126-STALL-02)."""
    fakebin.output("8812401\n8812402_3\n55_[1-3]\n56_[4-9%2]\n")
    assert squeue_ids(fakebin.path) == {"8812401", "8812402_3", "55", "56"}


def test_squeue_failure_gives_no_answer(fakebin: Fake) -> None:
    """A non-zero exit or too much output is a warning and no answer, never an error."""
    fakebin.path.write_text("#!/bin/sh\nexit 1\n")
    assert squeue_ids(fakebin.path) is None
    fakebin.path.write_text("#!/bin/sh\nyes 1234567\n")
    assert squeue_ids(fakebin.path) is None


def test_squeue_refused_when_relative(fakebin: Fake) -> None:
    with pytest.raises(sacct.Refused):
        squeue_ids(Path("squeue"))
