"""The stall watch (FU-P3-126, schedulers §3.9): a run's tasks whose SLURM jobs are in
neither squeue nor sacct for longer than the grace period warn on their run, and a task held
`submitted` moves to `running` once squeue says its job runs (#385, 2026-11-25).

`squeue` is a fake `call` answering each job's state (None when it failed), the clock is fake
and shared with the limiter, and the runs root is a private directory of the test.
"""

import json
from collections.abc import Callable
from concurrent.futures import Future
from pathlib import Path
from typing import Any

import pytest

from spectio.config import Settings
from spectio_server.failure import Accounting
from spectio_server.stall import (
    GRACE_S,
    WATCH_S,
    Stall,
    StallWatch,
    _advance_failed,
    _submit_advance,
)


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Squeue:
    """A fake `squeue_states`: the job → state answers, one per call, None when it failed."""

    def __init__(self, *answers: dict[str, str] | None) -> None:
        self.answers = list(answers)
        self.calls = 0

    def __call__(self) -> dict[str, str] | None:
        self.calls += 1
        assert self.answers, "squeue called more times than it has answers"
        return self.answers.pop(0)


@pytest.fixture
def runs(tmp_path: Path) -> Path:
    root = tmp_path / "spectio-runs"
    root.mkdir(mode=0o700)
    return root


def stall_watch(
    runs: Path,
    clock: Clock,
    call: Callable[[], dict[str, str] | None],
    **kwargs: Any,
) -> StallWatch:
    seen = kwargs.pop("in_sacct", lambda run: set())
    return StallWatch(runs, None, seen, call=call, interval_s=60, clock=clock, **kwargs)


def test_seen_then_gone_past_grace(runs: Path) -> None:
    """A job seen once, then gone from squeue and sacct past the grace: the run stalls, the
    stall file is written and the run is notified."""
    clock = Clock()
    sq = Squeue({"8812401": "RUNNING"}, {})
    notified: list[str] = []
    watch = stall_watch(runs, clock, sq, notify=notified.append)
    watch.watch("run_a", {"8812401": clock.now})
    assert watch.step()  # the first call: the job is in squeue
    assert watch.stall("run_a") is None
    clock.now += GRACE_S + 100
    watch.watch("run_a", {"8812401": 1000.0})  # the page re-read: still its submitted time
    assert watch.step()
    assert watch.stall("run_a") == Stall(tasks=1, since=1000.0)
    assert notified == ["run_a"]
    body = json.loads((runs / ".stalled.json").read_text())
    assert body == {
        "v": 1,
        "checked": clock.now,
        "runs": {"run_a": {"tasks": 1, "since": 1000.0}},
    }


def test_gone_within_grace(runs: Path) -> None:
    """A job gone from squeue and sacct within the grace period: no warning yet."""
    clock = Clock()
    sq = Squeue({"8812401": "RUNNING"}, {})
    watch = stall_watch(runs, clock, sq)
    watch.watch("run_b", {"8812401": clock.now})
    watch.step()
    clock.now += GRACE_S - 100
    assert watch.step()
    assert watch.stall("run_b") is None
    assert json.loads((runs / ".stalled.json").read_text())["runs"] == {}


def test_seen_in_sacct_not_stalled(runs: Path) -> None:
    """A job gone from squeue but with a row in sacct ended: it is not gone."""
    clock = Clock()
    sq = Squeue({"8812401": "RUNNING"}, {})
    seen: dict[str, set[str]] = {}

    def in_sacct(run: str) -> set[str]:
        return seen.get(run, set())

    watch = stall_watch(runs, clock, sq, in_sacct=in_sacct)
    watch.watch("run_c", {"8812401": clock.now})
    watch.step()
    clock.now += 2 * GRACE_S
    seen["run_c"] = {"8812401"}  # sacct has the job's row: it ended
    assert watch.step()
    assert watch.stall("run_c") is None


def test_failed_call_backs_off(runs: Path) -> None:
    """A failed squeue warns nothing and the next call waits the doubled interval."""
    clock = Clock()
    sq = Squeue(None, None)
    watch = stall_watch(runs, clock, sq)
    watch.watch("run_d", {"8812401": clock.now})
    assert watch.step()
    assert watch.stall("run_d") is None  # squeue fails: no warning
    assert watch.wait_s() == 120  # the first back-off (CR-P3FU106A-05)
    clock.now += 120
    assert watch.step()
    assert watch.wait_s() == 240


def test_never_seen_submitted_past_grace(runs: Path) -> None:
    """A job squeue never said and whose submission is past the grace: stalled at once, its
    stall since its submission."""
    clock = Clock()
    sq = Squeue({})
    watch = stall_watch(runs, clock, sq)
    watch.watch("run_e", {"8812402": clock.now - GRACE_S - 10})
    assert watch.step()
    assert watch.stall("run_e") == Stall(tasks=1, since=clock.now - GRACE_S - 10)


def test_watch_empty_forgets(runs: Path) -> None:
    """A run watched with no jobs (it ended, or is not on SLURM) is forgotten, its stall too."""
    clock = Clock()
    sq = Squeue({}, {})
    watch = stall_watch(runs, clock, sq)
    watch.watch("run_f", {"8812401": clock.now - GRACE_S - 10})
    assert watch.step()
    assert watch.stall("run_f") is not None
    assert watch.watch("run_f", {})  # a stall was forgotten: the caller rewrites the file
    assert watch.stall("run_f") is None
    assert watch.missing("run_f") == []
    clock.now += 60
    assert watch.step()  # the request left from the last answer: nothing asked after it
    assert watch.wait_s() is None


def test_created_watch_clears_the_stall_file(runs: Path) -> None:
    """CR-P3FU126-STALL-01: a new watch (server start) writes an empty stall file, so the
    doctor no longer reports what an earlier server saw."""
    old = {"v": 1, "checked": 1.0, "runs": {"run_old": {"tasks": 1, "since": 1.0}}}
    (runs / ".stalled.json").write_text(json.dumps(old))
    stall_watch(runs, Clock(), Squeue())
    assert json.loads((runs / ".stalled.json").read_text())["runs"] == {}


def test_gone_unconfirmed_notifies_then_read_stalls(runs: Path) -> None:
    """CR-P3FU126-STALL-01: a job past the grace with no read since does not stall its run: the
    run is notified, and once a read has confirmed the task still running, the next answer
    stalls it."""
    clock = Clock()
    sq = Squeue({"8812401": "RUNNING"}, {}, {})
    notified: list[str] = []
    watch = stall_watch(runs, clock, sq, notify=notified.append)
    watch.watch("run_g", {"8812401": clock.now})
    assert watch.step()  # seen at 1000
    clock.now += GRACE_S + 100
    assert watch.step()
    assert watch.stall("run_g") is None  # not confirmed by a read
    assert notified == ["run_g"]  # an open page reads it again
    watch.watch("run_g", {"8812401": 1000.0})  # the read: the task is still running
    clock.now += 60
    assert watch.step()
    assert watch.stall("run_g") == Stall(tasks=1, since=1000.0)
    assert notified == ["run_g", "run_g"]


def test_not_read_again_task_ended_no_stall(runs: Path) -> None:
    """CR-P3FU126-STALL-01: a run read once, whose task then ended and whose job left squeue,
    never stalls with no read; past WATCH_S it is no longer polled and the file stays empty."""
    clock = Clock()
    sq = Squeue({"8812401": "RUNNING"}, {}, {})
    watch = stall_watch(runs, clock, sq)
    watch.watch("run_h", {"8812401": clock.now})
    assert watch.step()
    clock.now += GRACE_S + 100
    assert watch.step()
    assert watch.stall("run_h") is None
    clock.now += WATCH_S
    assert watch.step()
    assert watch.stall("run_h") is None
    assert watch.missing("run_h") == []
    assert watch.wait_s() is None  # no longer polled
    assert json.loads((runs / ".stalled.json").read_text())["runs"] == {}


def test_run_not_read_for_watch_s_drops_its_stall(runs: Path) -> None:
    """CR-P3FU126-STALL-01: a run no view has read for WATCH_S is no longer polled, and its
    stall is dropped from the watch and the file."""
    clock = Clock()
    sq = Squeue({}, {})
    watch = stall_watch(runs, clock, sq)
    watch.watch("run_i", {"8812401": clock.now - GRACE_S - 10})
    assert watch.step()
    assert watch.stall("run_i") is not None
    clock.now += WATCH_S + 1
    assert watch.step()
    assert watch.stall("run_i") is None
    assert watch.wait_s() is None
    assert json.loads((runs / ".stalled.json").read_text())["runs"] == {}


def test_disabled_without_squeue(runs: Path) -> None:
    """Without a squeue path (and no call to test with), nothing is watched or asked."""
    watch = StallWatch(runs, None, lambda run: set(), clock=Clock())
    assert not watch.enabled
    watch.watch("run_x", {"8812401": 0.0})  # no-op: nothing queued, nothing asked
    assert not watch.step()


def test_stall_file_of_a_refused_runs_root(tmp_path: Path) -> None:
    """A runs root others can write into is refused: the watch still answers, without a file."""
    clock = Clock()
    sq = Squeue({})
    runs = tmp_path / "spectio-runs"
    runs.mkdir()
    runs.chmod(0o757)  # others can write it
    watch = stall_watch(runs, clock, sq)
    watch.watch("run_r", {"8812401": clock.now - GRACE_S - 10})
    assert watch.step()
    assert watch.stall("run_r") is not None
    assert not (runs / ".stalled.json").exists()  # refused: no file written


def test_from_settings_without_squeue(settings: Settings) -> None:
    """From settings with no squeue path recorded: disabled (a plain server)."""
    accounting = Accounting.from_settings(settings, start_thread=False)
    watch = StallWatch.from_settings(settings, accounting)
    assert not watch.enabled


# --- The queue (#385, 2026-11-25): `submitted` until squeue says the job runs ----------------


def test_submitted_job_moved_to_running_once(runs: Path) -> None:
    """A watched `submitted` job squeue says RUNNING (or COMPLETING) is moved to `running`
    once: the next answer asks nothing of it, and a PENDING job is left alone."""
    clock = Clock()
    sq = Squeue(
        {"8812401": "PENDING", "8812402": "RUNNING", "8812403": "COMPLETING"},
        {"8812401": "PENDING", "8812402": "RUNNING", "8812403": "COMPLETING"},
        {"8812401": "RUNNING", "8812402": "RUNNING", "8812403": "RUNNING"},
    )
    moved: list[tuple[str, list[str]]] = []
    watch = stall_watch(
        runs,
        clock,
        sq,
        grace_s=GRACE_S * 10,  # no stall here: only the queue's move is tested
        advance=lambda run_id, jobs: moved.append((run_id, sorted(jobs))),
    )
    watch.watch(
        "run_q",
        {"8812401": clock.now, "8812402": clock.now, "8812403": clock.now},
        submitted={"8812401", "8812402", "8812403"},
    )
    clock.now += 60
    assert watch.step()
    assert moved == [("run_q", ["8812402", "8812403"])]  # PENDING stays submitted
    clock.now += 60
    assert watch.step()
    assert moved == [("run_q", ["8812402", "8812403"])]  # already moved: not again
    clock.now += 60
    assert watch.step()
    assert moved[1:] == [("run_q", ["8812401"])]  # now the queued one runs: it alone moves


def test_submitted_job_pending_then_gone_keeps_submitted(runs: Path) -> None:
    """A `submitted` job gone from squeue is not moved by the watch: the engine's end event
    ends its attempt (or the stall warns), never a write of the queue's move."""
    clock = Clock()
    sq = Squeue({"8812401": "PENDING"}, {})
    moved: list[tuple[str, list[str]]] = []
    watch = stall_watch(
        runs, clock, sq, advance=lambda run_id, jobs: moved.append((run_id, sorted(jobs)))
    )
    watch.watch("run_p", {"8812401": clock.now}, submitted={"8812401"})
    clock.now += 60
    assert watch.step()
    clock.now += 60
    assert watch.step()
    assert moved == []
    assert watch.stall("run_p") is None  # within the grace: no warning either


def test_failed_answer_moves_nothing(runs: Path) -> None:
    """A failed squeue answer advances no queued job (§3.9): the next answer decides."""
    clock = Clock()
    sq = Squeue(None, {"8812401": "RUNNING"})
    moved: list[tuple[str, list[str]]] = []
    watch = stall_watch(
        runs, clock, sq, advance=lambda run_id, jobs: moved.append((run_id, sorted(jobs)))
    )
    watch.watch("run_n", {"8812401": clock.now}, submitted={"8812401"})
    clock.now += 120  # the back-off of the failed call
    assert watch.step()
    assert moved == []
    clock.now += 120  # the doubled interval
    assert watch.step()
    assert moved == [("run_n", ["8812401"])]


def test_watch_empty_forgets_the_submitted_jobs(runs: Path) -> None:
    """A run watched with no jobs (it ended) leaves nothing to move."""
    clock = Clock()
    sq = Squeue({"8812401": "RUNNING"})
    moved: list[tuple[str, list[str]]] = []
    watch = stall_watch(
        runs, clock, sq, advance=lambda run_id, jobs: moved.append((run_id, sorted(jobs)))
    )
    watch.watch("run_m", {"8812401": clock.now}, submitted={"8812401"})
    watch.watch("run_m", {})
    clock.now += 60
    assert watch.step()
    assert moved == []


def test_no_advance_without_a_write(runs: Path) -> None:
    """A watch with no `advance` (no writer wired) still answers and warns."""
    clock = Clock()
    sq = Squeue({"8812401": "RUNNING"})
    watch = stall_watch(runs, clock, sq)  # no advance: nothing to call
    watch.watch("run_l", {"8812401": clock.now}, submitted={"8812401"})
    assert watch.step()
    assert watch.stall("run_l") is None


def test_closed_writer_is_logged_not_raised(caplog: pytest.LogCaptureFixture) -> None:
    """The writer closes when the server stops: the poller's move is dropped with a warning,
    never an exception on the accounting thread."""

    def closed(fn: Callable[..., Any]) -> Future[None]:
        raise RuntimeError("the writer is closed")

    with caplog.at_level("WARNING"):
        _submit_advance(closed, "run_x", ["8812401"])
    assert "not queued" in caplog.text


def test_cancelled_move_is_not_an_error(caplog: pytest.LogCaptureFixture) -> None:
    """A cancelled future has no exception to read: `_advance_failed` returns quietly."""
    future: Future[None] = Future()
    future.cancel()
    with caplog.at_level("WARNING"):
        _advance_failed(future)
    assert caplog.text == ""


def test_the_move_comes_after_the_notify_and_the_stall_file(runs: Path) -> None:
    """A slow or failing writer never delays the warning: `advance` runs last."""
    clock = Clock()
    order: list[str] = []
    watch = stall_watch(
        runs,
        clock,
        Squeue({"8812401": "RUNNING"}),
        notify=lambda run_id: order.append("notify"),
        advance=lambda run_id, jobs: order.append("advance"),
        grace_s=0,
    )
    watch.write = lambda: order.append("write")  # type: ignore[method-assign]
    # job A runs now; job B was never seen and is past the grace: its stall is notified
    watch.watch("run_o", {"8812401": clock.now, "8812402": clock.now - 10}, submitted={"8812401"})
    assert watch.step()
    assert order == ["notify", "write", "advance"]
