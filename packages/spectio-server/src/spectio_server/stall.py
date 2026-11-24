"""The stall watch (FU-P3-126, schedulers §3.9): a run's tasks held as `submitted` or
`running` whose SLURM jobs are in neither `squeue` nor `sacct` for longer than a grace period
warn on their run, and `spectio doctor` says so from the stall file written here.

`squeue` is asked for all watched jobs at once, through the same gate as `sacct` (§3.8: one
pace and back-off for slurmctld), on the accounting thread (a poller, `Accounting.pollers`).
A job `sacct` has a row for ended: it is not gone. A failed `squeue` gives no warning: the
jobs are asked again under the back-off.
"""

import contextlib
import json
import logging
import threading
import time
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import Connection, select

from spectio.config import Settings
from spectio.runner import sacct
from spectio.runner.rundir import private_dir, run_paths, write_file
from spectio.runner.sacct import JOB_ID, SacctLimiter
from spectio.runner.squeue import STALL_FILE, squeue_ids
from spectio_server.failure import _launched, _resolver, dir_run_id, on_slurm
from spectio_server.files.pool import Stalled
from spectio_server.projector.runs import TERMINAL as RUN_ENDED
from spectio_server.store.schema import attempts, tasks

if TYPE_CHECKING:
    from spectio_server.failure import Accounting, Context

log = logging.getLogger(__name__)

GRACE_S = 900.0  # past this without squeue or sacct seeing a job, its task's run stalls
WATCH_S = 3600.0  # a run is polled while a view read it within this


@dataclass(frozen=True)
class Stall:
    """How many of a run's running tasks are stalled, and when their jobs were last seen,
    epoch seconds (the latest of them)."""

    tasks: int
    since: float


class StallWatch:
    """The watches of the runs their pages read: each run's job IDs and when they were last
    seen in `squeue` or `sacct`, polled on the accounting thread. A job past the grace stalls
    its run only once a read after the grace still holds its task running; a run no view has
    read for WATCH_S is no longer polled, and its stall is dropped."""

    def __init__(
        self,
        runs_root: Path,
        squeue: Path | None,
        in_sacct: Callable[[str], Collection[str]],
        *,
        notify: Callable[[str], None] | None = None,
        interval_s: float = sacct.INTERVAL_S,
        timeout_s: float = sacct.TIMEOUT_S,
        grace_s: float = GRACE_S,
        watch_s: float = WATCH_S,
        clock: Callable[[], float] = time.time,
        call: Callable[[], set[str] | None] | None = None,
    ) -> None:
        self.runs_root = runs_root
        self._in_sacct = in_sacct  # run → its job IDs sacct has a row for
        self._notify = notify
        self._grace = grace_s
        self._watch_s = watch_s
        self._clock = clock
        self.enabled = squeue is not None or call is not None
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, float]] = {}  # run → job ID → last seen (epoch)
        self._viewed: dict[str, float] = {}  # run → when its page last read it
        self._missing: dict[str, list[str]] = {}  # run → its jobs absent from squeue's answer
        self._stalled: dict[str, Stall] = {}

        def default_call() -> set[str] | None:
            return squeue_ids(squeue, timeout_s) if squeue is not None else None

        self._call = call if call is not None else default_call
        self._limiter = SacctLimiter(
            self._ask, interval_s=interval_s, batch=sacct.MAX_PENDING, clock=clock
        )
        if self.enabled:
            self.write()  # server start: no stall yet, whatever an earlier server saw

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        accounting: "Accounting",
        notify: Callable[[str], None] | None = None,
    ) -> "StallWatch":
        """With the `squeue` path `spectio init` recorded (none: the watch is off, and no
        warning), and `sacct`'s rows through the accounting."""
        return cls(
            settings.runs_root,
            settings.slurm.squeue,
            lambda run_id: {j for j, row in accounting.rows(run_id).items() if row is not None},
            notify=notify,
        )

    def _ask(self, ids: list[str]) -> sacct.Found | None:
        """The limiter's call: the whole `squeue` answer, kept for the asked IDs it holds
        (a pending array range's base covers its tasks); None when it failed."""
        said = self._call()
        if said is None:
            return None
        return {job: {} for job in ids if job in said or job.partition("_")[0] in said}

    def watch(self, run_id: str, jobs: Mapping[str, float]) -> bool:
        """The run's jobs, job ID → its submission epoch, as its page reads them. None: the
        run ended, or is not on SLURM — forget it and its stall. True when a stall was
        forgotten: the caller rewrites the stall file (`write`), off this thread."""
        if not self.enabled:
            return False
        with self._lock:
            if not jobs:
                for state in (self._jobs, self._viewed, self._missing):
                    state.pop(run_id, None)
                return self._stalled.pop(run_id, None) is not None
            seen = self._jobs.get(run_id, {})
            self._jobs[run_id] = {job: max(seen.get(job, when), when) for job, when in jobs.items()}
            self._viewed[run_id] = self._clock()
        self._limiter.request(jobs)
        return False

    def stall(self, run_id: str) -> Stall | None:
        with self._lock:
            return self._stalled.get(run_id)

    def missing(self, run_id: str) -> list[str]:
        """The run's jobs absent from the last `squeue` answer: `sacct` is asked for them."""
        with self._lock:
            return list(self._missing.get(run_id, ()))

    def wait_s(self) -> float | None:
        return self._limiter.wait_s()

    def step(self) -> bool:
        """One `squeue` call when one is due; False when none was. A failed or refused call
        keeps no warning and asks again; an answer without a job past the grace stalls its
        run once a read after the grace confirmed its task still running, and notifies the
        run until one did. Returns True when a call was made."""
        done = self._limiter.run_once()
        if done is None:
            return False
        answer = done[1]
        now = self._clock()
        changed: set[str] = set()
        with self._lock:
            before = dict(self._stalled)
            for run_id, viewed in list(self._viewed.items()):
                if now - viewed > self._watch_s:  # no view read the run: stop polling it
                    for state in (self._jobs, self._viewed, self._missing, self._stalled):
                        state.pop(run_id, None)
        if not isinstance(answer, dict):
            # None, FINAL, SITE_LIMIT: squeue failed or was refused — no warning (§3.9)
            with self._lock:
                self._stalled.clear()
                ids = [job for jobs in self._jobs.values() for job in jobs]
            if before:
                self.write()
            self._limiter.request(ids)  # the limiter has already backed off
            return True
        with self._lock:
            for run_id, jobs in self._jobs.items():
                was = self._missing.get(run_id, [])
                ended = self._in_sacct(run_id)  # once per run, not per job
                for job in jobs:
                    if job in answer or job in ended:
                        jobs[job] = now
                self._missing[run_id] = [job for job in jobs if job not in answer]
                late = [job for job, at in jobs.items() if now - at > self._grace]
                # gone: a read after the grace still held its task running (no read: no stall)
                gone = [job for job in late if self._viewed[run_id] >= jobs[job] + self._grace]
                if len(gone) < len(late):
                    changed.add(run_id)  # an open page reads the run again
                if gone:
                    self._stalled[run_id] = Stall(len(gone), max(jobs[job] for job in gone))
                else:
                    self._stalled.pop(run_id, None)
                if self._stalled.get(run_id) != before.get(run_id) or self._missing[run_id] != was:
                    changed.add(run_id)
            stalled_changed = self._stalled != before
            ids = [job for jobs in self._jobs.values() for job in jobs]
        for run_id in changed:
            self._notify_run(run_id)
        if stalled_changed or self._stalled:
            self.write()
        self._limiter.request(ids)
        return True

    def _notify_run(self, run_id: str) -> None:
        """The run's page re-reads it (api §8.3), when a notify was given."""
        if self._notify is not None:
            self._notify(run_id)

    def write(self) -> None:
        """The stall file in the runs root, for `spectio doctor`; a failure to write it is a
        warning, never more (the watch still answers)."""
        now = self._clock()
        with self._lock:
            runs = {
                run_id: {"tasks": s.tasks, "since": s.since} for run_id, s in self._stalled.items()
            }
        body = json.dumps({"v": 1, "checked": now, "runs": runs})
        try:
            with private_dir(self.runs_root) as fd:
                write_file(fd, STALL_FILE, body.encode())
        except (OSError, ValueError) as exc:
            log.warning("%s not written: %s", STALL_FILE, exc)


def run_stall(conn: Connection, row: Any, ctx: "Context") -> dict[str, Any] | None:
    """The run's stall for its detail (api §7.2): how many of its running tasks' SLURM jobs
    are gone from squeue and sacct past the grace period, and when they were last seen;
    None when there is no watch, or the run has none."""
    watch = ctx.stall
    if watch is None or not watch.enabled:
        return None
    given: dict[str, float] = {}
    where: dict[str, str | None] = {}
    if row.state not in RUN_ENDED and on_slurm(row.environment, ctx.settings):
        asked = conn.execute(
            select(attempts.c.native_id, attempts.c.created_at, attempts.c.work_dir)
            .join(tasks, attempts.c.task_id == tasks.c.id)
            .where(tasks.c.run_id == row.id, attempts.c.state.in_(("submitted", "running")))
        ).all()
        for attempt in asked:
            job = attempt.native_id
            if job and JOB_ID.fullmatch(job):
                given.setdefault(job, attempt.created_at.timestamp())
                where.setdefault(job, attempt.work_dir)
    if watch.watch(row.id, given):  # a stall forgotten: the doctor's file says so, in the pool
        with contextlib.suppress(Stalled):
            ctx.files.run(watch.write, ctx.timeout_s)
    if given:
        ctx.accounting.kick()  # the watch's jobs are queued: the thread starts and wakes
        if missing := [job for job in watch.missing(row.id) if job in given]:
            launch = str(run_paths(ctx.runs_root, dir_run_id(row)).launch_dir)
            jobs = [(job, launch if row.engine == "snakemake" else where[job]) for job in missing]
            ctx.accounting.want(
                row.id, jobs, _launched(row.created_at, row.started_at), _resolver(ctx)
            )
    found = watch.stall(row.id)
    if found is None:
        return None
    return {"tasks": found.tasks, "since": datetime.fromtimestamp(found.since, UTC).isoformat()}
