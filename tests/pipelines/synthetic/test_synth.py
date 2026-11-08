"""Tests of bin/synth.py, the task bodies of the synthetic pipelines (no engine needed).

  uv run pytest -q tests/pipelines/synthetic/test_synth.py

Each task writes a few deterministic lines to stdout (INFO) and stderr (one WARN; ERROR lines
when it fails); SYNTH_VERBOSITY sets how many (quiet, normal, loud). The outputs never change.
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

SYNTH = Path(__file__).resolve().parent / "bin" / "synth.py"
TAIL = 65536  # the bytes Spectio's task-file view shows by default (files/confine.py TAIL)

# sha256 of every output of a small chain, recorded with synth.py before it wrote any log line.
CHAIN_DIGESTS = {
    "S01.reads.txt": "3e7e09acfef107c6900821f4b9dbbf577e47108d8e790faef8deaf4f2bb6ef63",
    "S07.reads.txt": "ee9a42d75334150030213c36f89491ae4dff99c131534ebe08ac6ded921797e6",
    "S01.qc.json": "f25fdcd6b7171ea870f570ff298581894fc273c51fa3e1f323dfeebb02c30806",
    "S07.qc.json": "899f4e3484cc52c83691d6f580b00fbf6628d239c82dbf48635e2a391caa0b70",
    "gs.tsv": "0cc39d131f6e99ff3fbc7bacc4839b607cc76539136621c101b3a998cf17e28a",
    "mq.json": "b8a6251861cad2f230c3fd42ac496d205645981f2aa69c35e847fa32d58e7cc4",
    "mq.html": "eef64c8123c9a7badc3aa1811811e2022f114f169e66147a96fce519f0c95b1a",
    "chunks/S01.chunk0000.txt": "6c47db8d2ba7face043733d8780f2d387a6e7bd627f67c9143b8cdfce43067dc",
    "chunks/S01.chunk0001.txt": "d7e93030acf6a32b1c07d98a26c4819119661f0cd1d734f48f7d3cf04a2f8112",
    "c0.tsv": "6a46c8e367bff8e13a18f85cf2c96dd730eceb11619d21d77414c1537b8bbd2d",
    "c1.tsv": "4e3b73a9893e9d5248577995131df1c3f419111001b54701607eda6988113ce3",
    "m.tsv": "3ad7ce1c82a6c28acf573c073638c37b3c6a5031102f73f8a2b6f625a9acd7d5",
    "cmp.tsv": "87d5dba496001629c3f78972710141e06e55e90d5ccdcab1c9379d8557c3c6bb",
}
CHAIN = [
    ["reads", "S01", "400", "42", "S01.reads.txt"],
    ["reads", "S07", "400", "42", "S07.reads.txt"],
    ["stats", "S01.reads.txt", "S01.qc.json"],
    ["stats", "S07.reads.txt", "S07.qc.json"],
    ["report", "gs.tsv", "mq.json", "mq.html", "S01.qc.json", "S07.qc.json"],
    ["split", "S01.reads.txt", "2", "chunks"],
    ["align", "chunks/S01.chunk0000.txt", "c0.tsv"],
    ["align", "chunks/S01.chunk0001.txt", "c1.tsv"],
    ["merge", "m.tsv", "c0.tsv", "c1.tsv"],
    ["compare", "m.tsv", "S01", "S07", "cmp.tsv"],
]


def synth(cwd: Path, *args: str, verbosity: str | None = None, attempt: str | None = None):
    env = {k: v for k, v in os.environ.items() if k not in ("SYNTH_VERBOSITY", "SPECTIO_ATTEMPT")}
    if verbosity is not None:
        env["SYNTH_VERBOSITY"] = verbosity
    if attempt is not None:
        env["SPECTIO_ATTEMPT"] = attempt
    return subprocess.run(
        [sys.executable, str(SYNTH), *args], cwd=cwd, env=env, capture_output=True, text=True
    )


def run_chain(cwd: Path, verbosity: str | None) -> list[subprocess.CompletedProcess[str]]:
    done = [synth(cwd, *step, verbosity=verbosity) for step in CHAIN]
    assert [p.returncode for p in done] == [0] * len(CHAIN), [p.stderr for p in done]
    return done


def digests(cwd: Path) -> dict[str, str]:
    return {name: hashlib.sha256((cwd / name).read_bytes()).hexdigest() for name in CHAIN_DIGESTS}


@pytest.mark.parametrize("verbosity", [None, "quiet", "normal", "loud"])
def test_outputs_do_not_depend_on_the_verbosity(tmp_path: Path, verbosity: str | None) -> None:
    run_chain(tmp_path, verbosity)
    assert digests(tmp_path) == CHAIN_DIGESTS
    assert sorted(p.name for p in (tmp_path / "chunks").iterdir()) == [
        "S01.chunk0000.txt",
        "S01.chunk0001.txt",
    ]


@pytest.mark.parametrize("verbosity", [None, "normal"])
def test_normal_writes_a_few_info_lines_and_one_warning(
    tmp_path: Path, verbosity: str | None
) -> None:
    for step, p in zip(CHAIN, run_chain(tmp_path, verbosity), strict=True):
        out, err = p.stdout.splitlines(), p.stderr.splitlines()
        assert 5 <= len(out) <= 20, (step, out)
        assert all(line.startswith("INFO ") for line in out), out
        assert len(err) == 1 and err[0].startswith("WARN "), err


def test_info_lines_name_the_inputs_and_the_outputs(tmp_path: Path) -> None:
    done = run_chain(tmp_path, "normal")
    stats = done[2].stdout
    assert "S01.reads.txt" in stats and "400 lines" in stats
    assert "S01.qc.json" in stats
    split = done[5].stdout
    assert "chunks" in split and "2 files" in split


def test_the_lines_are_deterministic(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = [(p.stdout, p.stderr) for p in run_chain(tmp_path / "a", "loud")]
    second = [(p.stdout, p.stderr) for p in run_chain(tmp_path / "b", "loud")]
    assert first == second


def test_quiet_writes_nothing_on_success(tmp_path: Path) -> None:
    for p in run_chain(tmp_path, "quiet"):
        assert (p.stdout, p.stderr) == ("", "")


def test_loud_fills_more_than_the_tail_on_both_streams(tmp_path: Path) -> None:
    for step, p in zip(CHAIN, run_chain(tmp_path, "loud"), strict=True):
        assert len(p.stdout.encode()) > TAIL, step
        assert len(p.stderr.encode()) > TAIL, step
        lines = len(p.stdout.splitlines()) + len(p.stderr.splitlines())
        assert 1800 <= lines <= 2200, (step, lines)


def test_unknown_verbosity_is_refused(tmp_path: Path) -> None:
    p = synth(tmp_path, "reads", "S01", "4", "42", "r.txt", verbosity="chatty")
    assert p.returncode != 0
    assert "chatty" in p.stderr
    assert not (tmp_path / "r.txt").exists()


def test_exit_failure_writes_error_lines(tmp_path: Path) -> None:
    p = synth(tmp_path, "fail", "exit", "1", "2")
    assert p.returncode == 1
    errors = [line for line in p.stderr.splitlines() if line.startswith("ERROR ")]
    assert errors and len(errors) <= 5
    # the text test_bridge_nextflow.py looks for in the spool (TOOL_STDERR)
    assert "synthetic failure: tool exited with code 1" in errors[0]
    assert [line for line in p.stderr.splitlines() if line.startswith("WARN ")]
    assert p.stdout.splitlines() and all(x.startswith("INFO ") for x in p.stdout.splitlines())


def test_quiet_failure_still_writes_its_error_lines(tmp_path: Path) -> None:
    p = synth(tmp_path, "fail", "exit", "1", "2", verbosity="quiet")
    assert p.returncode == 1
    assert p.stdout == ""
    assert p.stderr.splitlines() and all(x.startswith("ERROR ") for x in p.stderr.splitlines())


def test_a_killed_task_keeps_its_lines(tmp_path: Path) -> None:
    """SIGKILL loses what Python has not flushed: every line is flushed as it is written."""
    p = synth(tmp_path, "fail", "oom", "1", "2")
    assert p.returncode == -9
    assert p.stdout.splitlines()
    assert "simulated OOM kill" in p.stderr


@pytest.mark.parametrize(("mode", "attempt"), [("flaky", "2"), ("oom_once", "2"), ("none", "1")])
def test_no_error_line_when_nothing_fails(tmp_path: Path, mode: str, attempt: str) -> None:
    p = synth(tmp_path, "fail", mode, attempt, "2", attempt=attempt)
    assert p.returncode == 0
    assert "ERROR" not in p.stderr
