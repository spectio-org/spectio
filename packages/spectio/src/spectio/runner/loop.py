"""The runner loop (P1 Task 9; architecture §7.1): lease `runner_commands`, read the spools,
watch the heads.

The in-process runner of `spectio serve` calls `tick()` every `tick_s` seconds. One launch
that fails (a refused spool, an unreadable head file, a launch that cannot start) is counted,
logged or reported, and never stops the others (SEC-P3T3-09, CR-P3T04-11). Every path is
derived from the runs root and the run ID, and walked one private directory at a time
(dev-env §15.3 req. 10).
"""

import json
import logging
import os
import shlex
import threading
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, JsonValue

from spectio.config import Settings
from spectio.runner.engines import EngineError, check_engine
from spectio.runner.rundir import (
    check_launch_dir,
    make_run_dirs,
    private_dir,
    read_small,
    write_file,
)
from spectio.runner.spool import SPOOL_REFUSED, try_read_spool
from spectio.runner.types import (
    Command,
    Failure,
    HeadReport,
    Launcher,
    LaunchRef,
    LaunchSpec,
    RunnerSink,
    SpoolBatch,
)

log = logging.getLogger(__name__)

LAUNCH_FAILED = "launch-failed.json"
CANCEL = "cancel"
LAUNCH_CLASSES = frozenset({"launch_error", "engine_missing", "engine_version"})


class LaunchPayload(BaseModel):
    """The payload of a `launch` command (written by P1 Task 17)."""

    model_config = ConfigDict(extra="forbid")

    location: str
    profiles: list[str] = []
    params: dict[str, JsonValue] = {}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def ended_failure(engine: str, report: HeadReport) -> HeadReport:
    """An ended head with the class the run fails with when no terminal engine event came
    (Assumption 15): `head_lost` with no exit code; `engine_fault` for a Nextflow head, which
    ends on its own event. A Snakemake head's exit code ends its launch (Assumption 16)."""
    if report.exit_code is None:
        message = "The head ended with no exit code: it was killed, or the machine restarted."
        return replace(report, failure=Failure("head_lost", message))
    if engine == "snakemake":
        return report
    message = f"Nextflow exited with code {report.exit_code} and sent no end event."
    return replace(report, failure=Failure("engine_fault", message))


class RunnerLoop:
    def __init__(
        self,
        sink: RunnerSink,
        launcher: Launcher,
        settings: Settings,
        tick_s: float = 2,
        end_grace_s: float = 60,
    ) -> None:
        self.sink = sink
        self.launcher = launcher
        self.settings = settings
        self.tick_s = tick_s
        self.end_grace_s = end_grace_s  # how long an ended head waits for its spool
        self._known: set[str] = set()  # launches the launcher started or adopted
        self._refused: set[str] = set()  # launches whose refused spool is already counted
        self._last: dict[str, HeadReport] = {}
        self._ended_at: dict[str, float] = {}

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            try:
                self.tick()
            except Exception:  # the sink itself failed: try again at the next tick
                log.exception("runner tick failed")
            stop.wait(self.tick_s)

    def tick(self) -> None:
        for ref in self.sink.active_launches():
            if ref.native_id and ref.launch_id not in self._known:
                self._each(self._adopt, ref)  # after a restart
        for command in self.sink.lease_commands():
            self._command(command)
        launches = self.sink.active_launches()
        for ref in launches:
            self._each(self._read, ref)
        watched = {r.native_id: r for r in launches if r.native_id and r.launch_id in self._known}
        try:
            polled = self.launcher.poll(list(watched))
        except Exception:
            log.exception("heads not polled")
            polled = {}
        for native_id, report in polled.items():
            self._each(self._report, watched[native_id], report)
        self._forget({r.launch_id for r in launches})

    def _each(self, fn: Callable[..., None], ref: LaunchRef, *args: object) -> None:
        try:
            fn(ref, *args)
        except Exception:
            log.exception("launch %s of %s", ref.launch_n, ref.run_id)

    def _forget(self, active: set[str]) -> None:
        for kept in (self._known, self._refused):
            kept.intersection_update(active)
        for by_launch in (self._last, self._ended_at):
            for launch_id in by_launch.keys() - active:
                del by_launch[launch_id]

    # --- Commands ------------------------------------------------------------------------

    def _command(self, command: Command) -> None:
        try:
            if command.kind == "launch":
                detail = self._launch(command)
            elif command.kind == "cancel":
                detail = self._cancel(command.launch)
            else:
                detail = f"unknown command {command.kind!r}"
        except Exception as exc:
            log.exception("command %s (%s) failed", command.id, command.kind)
            detail = f"{type(exc).__name__}: {exc}"
        self.sink.ack(command.id, detail is None, detail)

    def _launch(self, command: Command) -> str | None:
        ref = command.launch
        if ref.launch_id in self._known:
            return None  # delivered again: already started
        root = self.settings.runs_root
        try:
            paths = make_run_dirs(root, ref.run_id)
            check_launch_dir(root, ref.run_id, ref.launch_dir)
            with private_dir(root, ref.run_id, "launch", ".spectio") as fd:
                failed = _read_json(fd, LAUNCH_FAILED)
                started = _exists(fd, "head.pid") or _exists(fd, "head.exit")
                cancelled = _exists(fd, CANCEL)
        except (OSError, ValueError) as exc:
            return self._fail(ref, "launch_error", str(exc))
        if failed is not None:  # delivered again after a failed launch: the same failure
            class_ = failed.get("class")
            failure = Failure(
                class_ if class_ in LAUNCH_CLASSES else "launch_error", str(failed.get("message"))
            )
            self._report(ref, HeadReport("unknown", None, None, None, True, failure))
            return failure.message
        if started:  # delivered again after a restart: adopt, never start twice
            self._adopt(ref)
            return None
        if cancelled:  # cancelled before its head started: it never starts (CR-P3T09-02)
            self._report(ref, HeadReport("unknown", None, None, None, True, None))
            return None
        try:
            payload = LaunchPayload.model_validate(command.payload)
            if not Path(payload.location).is_absolute():
                raise ValueError(f"{payload.location!r} is not an absolute path")
            engines = self.settings.engines
            cmd = engines.nextflow_cmd if ref.engine == "nextflow" else engines.snakemake_cmd
            info = check_engine(ref.engine, cmd)
            spec = LaunchSpec(
                run_id=ref.run_id,
                launch_n=ref.launch_n,
                engine=ref.engine,
                engine_cmd=cmd or shlex.quote(info.path),
                location=Path(payload.location),
                launch_dir=paths.launch_dir,
                work_dir=paths.work_dir,
                profiles=payload.profiles,
                params=payload.params,
                slurm=self.settings.slurm if self.settings.executor == "slurm" else None,
                nxf_opts=engines.nxf_opts,
                extra_args=engines.extra_args.get(ref.engine, []),
            )
            native_id = self.launcher.submit(spec)
        except EngineError as exc:
            return self._fail(ref, exc.class_, str(exc))
        except (OSError, ValueError) as exc:
            return self._fail(ref, "launch_error", str(exc))
        self._known.add(ref.launch_id)
        self._report(ref, HeadReport("starting", native_id, None, None, False, None))
        return None

    def _fail(self, ref: LaunchRef, class_: str, message: str) -> str:
        """`.spectio/launch-failed.json`, when the directory can hold it, and the failure."""
        failure = Failure(class_, message[:4096])
        record = {"class": class_, "message": failure.message, "time": _now()}
        try:
            with private_dir(self.settings.runs_root, ref.run_id, "launch", ".spectio") as fd:
                write_file(fd, LAUNCH_FAILED, json.dumps(record).encode())
        except (OSError, ValueError) as exc:
            log.warning("%s of %s not written: %r", LAUNCH_FAILED, ref.run_id, exc)
        self._report(ref, HeadReport("unknown", None, None, None, True, failure))
        return failure.message

    def _cancel(self, ref: LaunchRef) -> str | None:
        """The marker `.spectio/cancel` first, then the launcher's interrupt (Assumption 4).
        Before the head has started, the marker alone: `_launch` then starts none, and a head
        started in this lease checks it before the engine runs (CR-P3T09-02)."""
        root = self.settings.runs_root
        last = self._last.get(ref.launch_id)
        native_id = ref.native_id or (last.native_id if last else None)
        if native_id is None:
            make_run_dirs(root, ref.run_id)
        check_launch_dir(root, ref.run_id, ref.launch_dir)
        with private_dir(root, ref.run_id, "launch", ".spectio") as fd:
            write_file(fd, CANCEL, json.dumps({"time": _now()}).encode())
        if native_id is None:
            return None
        if ref.launch_id not in self._known:
            self._adopt(ref)
        self.launcher.cancel(native_id)
        return None

    # --- Heads and spools ------------------------------------------------------------------

    def _adopt(self, ref: LaunchRef) -> None:
        check_launch_dir(self.settings.runs_root, ref.run_id, ref.launch_dir)
        report = self.launcher.adopt(ref)
        self._known.add(ref.launch_id)
        self._report(ref, report)

    def _report(self, ref: LaunchRef, report: HeadReport) -> None:
        if report.ended and report.failure is None:
            first = self._ended_at.setdefault(ref.launch_id, time.monotonic())
            if time.monotonic() - first < self.end_grace_s:
                return  # its last events may still be in the spool (Assumption 15)
            report = ended_failure(ref.engine, report)
        if self._last.get(ref.launch_id) == report:
            return
        self._last[ref.launch_id] = report
        self.sink.head_report(ref.launch_id, report)

    def _read(self, ref: LaunchRef) -> None:
        cursor = self.sink.cursor(ref.launch_id)
        try:
            check_launch_dir(self.settings.runs_root, ref.run_id, ref.launch_dir)
        except (OSError, ValueError) as exc:
            log.debug("launch directory of %s refused: %r", ref.run_id, exc)
            batch = SpoolBatch([], dict(cursor), Counter({SPOOL_REFUSED: 1}))
        else:
            batch = try_read_spool(ref.launch_dir, ref.run_id, ref.launch_n, cursor)
        if batch.drops[SPOOL_REFUSED]:
            if ref.launch_id in self._refused:
                return  # counted when it was first refused
            self._refused.add(ref.launch_id)
            log.warning(
                "spool of %s launch %d refused; read again once it is private",
                ref.run_id,
                ref.launch_n,
            )
        else:
            self._refused.discard(ref.launch_id)
        if batch.events or +batch.drops or batch.cursor != cursor:
            self.sink.ingest(ref.launch_id, batch)


def _exists(dir_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _read_json(dir_fd: int, name: str) -> dict[str, object] | None:
    raw = read_small(dir_fd, name, cap=65536)
    if raw is None:
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{name} is not a JSON object")
    return data
