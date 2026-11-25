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
import re
import shlex
import stat
import threading
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from spectio.config import Settings, software_cache_dir
from spectio.environments import (
    DefaultResources,
    Snapshot,
    as_snapshot,
    check_on_server,
    launch_fields,
    server_builtin,
    snapshot,
)
from spectio.runner.engines import EngineError, check_engine
from spectio.runner.local import checkable, same_process
from spectio.runner.observed import check_observed_launch_dir, end_pointer, scan_observed
from spectio.runner.resume import clear_stale_lock, prove
from spectio.runner.rundir import (
    MAIN_SCRIPT,
    RUN_ID,
    check_launch_dir,
    make_run_dirs,
    private_dir,
    read_small,
    run_paths,
    runs_disk,
    write_file,
)
from spectio.runner.sacct import site_accounting
from spectio.runner.spool import SPOOL_REFUSED, SPOOL_STALLED, try_read_spool
from spectio.runner.types import (
    Command,
    ExtraFile,
    Failure,
    FileRunner,
    HeadReport,
    Launcher,
    LaunchRef,
    LaunchSpec,
    ResumeSource,
    RunnerSink,
    SpoolBatch,
    Stalled,
)
from spectio.text import strip_escapes
from spectio_sdk.targets import RunTarget, from_registry

log = logging.getLogger(__name__)

LAUNCH_FAILED = "launch-failed.json"
CANCEL = "cancel"
HIDDEN = "«hidden»"  # as spectio_server.files.redact
HEAD_OUT = "head.out"  # the engine's output, as the head script copies it (headscript.py)
# The launch whose head files `.spectio/` holds (CR-P3T09-11): head.pid, head.exit, cancel and
# launch-failed.json are named per run, so a later launch clears an earlier one's first. No file
# is launch 1, as before P1 Task 30.
OWNER = "launch"
HEAD_FILES = ("head.pid", "head.exit", CANCEL, LAUNCH_FAILED)
_OWNER_LINE = re.compile(r"([1-9][0-9]{0,8})\n")
LAUNCH_CLASSES = frozenset({"launch_error", "engine_missing", "engine_version"})
T = TypeVar("T")


class ResumePayload(BaseModel):
    """What `:relaunch` mode `resume` asks (P1 Task 30): run in `run_id`'s directories after
    `parent_run_id`, found at `device` and `inode` when the server checked them."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(pattern=rf"^{RUN_ID.pattern}$")
    parent_run_id: str = Field(pattern=rf"^{RUN_ID.pattern}$")
    engine_session_id: str | None = None
    device: int
    inode: int


class ConfigFilePayload(BaseModel):
    """The launch command's extra config file (api §5.7): its bytes in `text`, set to null once
    the command is answered (`sink.ack`), so no lasting row holds a possible secret."""

    model_config = ConfigDict(extra="forbid", strict=True)

    kept_as: Literal["extra.config", "extra.yaml", "extra.json"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(ge=0, le=256 * 1024)
    text: str | None


class LaunchPayload(BaseModel):
    """The payload of a `launch` command (written by P1 Tasks 17 and 30). `environment` is the
    run's snapshot (FU-P3-86c), checked again here with the routes' strict model; a command
    written before it has none, and runs on the built-in of the server's kind (api §5.4)."""

    model_config = ConfigDict(extra="forbid")

    location: str
    profiles: list[str] = []
    params: dict[str, JsonValue] = {}
    resume_of: ResumePayload | None = None
    environment: Snapshot | None = None
    target: RunTarget | None = None  # one module or one rule (api §5.10)
    default_resources: DefaultResources | None = None  # api §5.7 (FU-P3-110b)
    config_file: ConfigFilePayload | None = None
    main_script: str | None = Field(None, pattern=rf"^{MAIN_SCRIPT.pattern}$")  # #351


def extra_file(payload: LaunchPayload) -> ExtraFile | None:
    kept = payload.config_file
    return None if kept is None else ExtraFile(kept.kept_as, kept.sha256, kept.text)


def _now() -> str:
    return datetime.now(UTC).isoformat()


# The end of the engine's own output a failure quotes (#368): enough for Nextflow's `ERROR ~`
# line and the error block above it, small enough for the run's failure summary
TAIL_READ = 16 * 1024
TAIL_LINES = 15
TAIL_CHARS = 2000
# Nextflow's task error report holds the task's script with its values filled in: it is hidden
# from the stored message, as `Command '…'` is in snakemake.error (SEC-NFERR-01, SEC-P3T1-08)
# a template task's block reads `Command executed [<template>]:` (TaskErrorFormatter.groovy:130,
# Nextflow 26.11.0-edge, read 2026-11-25; SEC-NFERR-05)
# Any line that starts like one ends in `:` counts, so an odd template name fails closed
# (SEC-NFERR-05a). A script line that starts with `Command exit status:` would end the hiding
# early; only a later real end repairs it, a residual accepted (SEC-NFERR-05b).
COMMAND_START = re.compile(r"Command executed\b[^\n]*:$")
COMMAND_END = "Command exit status:"
COMMAND_HIDDEN = f"Command executed: {HIDDEN}"


def _hide_commands(lines: list[str]) -> list[str]:
    """`lines` with each `Command executed:` block, up to its `Command exit status:` line, as
    one hidden line. Fails closed: a block with no end hides the rest, and an end with no start
    (the window began inside a block) hides everything back to the previous end."""
    kept: list[str] = []
    since_end = 0  # where `kept` stood after the last end, or the window's start
    hiding = False
    for line in lines:
        stripped = line.strip()
        if COMMAND_START.match(stripped):
            kept.append(COMMAND_HIDDEN)
            hiding = True
        elif stripped.startswith(COMMAND_END):
            if not hiding:
                del kept[since_end:]
                kept.append(COMMAND_HIDDEN)
            hiding = False
            kept.append(line)
            since_end = len(kept)
        elif not hiding:
            kept.append(line)
    return kept


def engine_output_tail(data: bytes) -> str | None:
    """The last non-blank lines of the engine's output: a line rewritten in place (`\\r`) as its
    last state, escape sequences, control and format characters removed (`strip_escapes`),
    commands hidden (`_hide_commands`), at most TAIL_LINES lines and TAIL_CHARS characters;
    None when blank."""
    text = data.decode("utf-8", "replace").replace("\r\n", "\n")
    text = strip_escapes("\n".join(line.rsplit("\r", 1)[-1] for line in text.split("\n")))
    lines = [line.rstrip() for line in text.split("\n") if line.strip()]
    kept = _hide_commands(lines)[-TAIL_LINES:]
    tail = "\n".join(kept)[-TAIL_CHARS:]
    return tail or None


def ended_failure(engine: str, report: HeadReport, output: str | None = None) -> HeadReport:
    """An ended head with the class the run fails with when no terminal engine event came
    (Assumption 15): `head_lost` with no exit code; `engine_fault` for a Nextflow head, which
    ends on its own event, quoting the end of its `output` when there is one (#368). A
    Snakemake head's exit code ends its launch (Assumption 16)."""
    if report.exit_code is None:
        message = "The head ended with no exit code: it was killed, or the machine restarted."
        return replace(report, failure=Failure("head_lost", message))
    if engine == "snakemake":
        return report
    message = f"Nextflow exited with code {report.exit_code} and sent no end event."
    if output:
        message += f" Its last lines:\n{output}"
    return replace(report, failure=Failure("engine_fault", message))


class RunnerLoop:
    def __init__(
        self,
        sink: RunnerSink,
        launcher: Launcher,
        settings: Settings,
        tick_s: float = 2,
        end_grace_s: float = 60,
        home: Path | None = None,
        observe_cap: int = 100,
        files: FileRunner | None = None,
        files_timeout_s: float = 5.0,
    ) -> None:
        self.sink = sink
        self.launcher = launcher
        self.settings = settings
        self.tick_s = tick_s
        self.end_grace_s = end_grace_s  # how long an ended head waits for its spool
        self.home = home  # `~/.spectio/observed/` is scanned when set (architecture §13.8)
        self.observe_cap = observe_cap  # pointers read per scan (req. 12)
        # where the file-system work of runs from a terminal runs, bounded: their launch
        # directory is project storage, which can stop answering (SEC-P3T25-01)
        self.files = files
        self.files_timeout_s = files_timeout_s
        self._busy: set[str] = set()  # jobs still in the pool: a launch ID, or "scan"
        self._pointers: set[str] = set()  # run IDs whose pointer was read or refused
        self._pointers_mtime: int | None = None
        self._observed_refused = False  # a loose `observed/` already warned of
        self._terminal: set[str] = set()  # the active runs started from a terminal
        self._known: set[str] = set()  # launches the launcher started or adopted
        self._refused: set[str] = set()  # launches whose refused spool is already counted
        self._unadopted: set[str] = set()  # launches whose refused adopt is already logged
        self._last: dict[str, HeadReport] = {}
        self._ended_at: dict[str, float] = {}
        self._starts: list[tuple[Command, LaunchSpec]] = []  # the heads of this lease, to start

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            try:
                self.tick()
            except Exception:  # the sink itself failed: try again at the next tick
                log.exception("runner tick failed")
            stop.wait(self.tick_s)

    def tick(self) -> None:
        if self.home is not None:
            try:
                self._observe(self.home)
            except Exception:
                log.exception("runs started from a terminal not scanned")
        for ref in self.sink.active_launches():
            if ref.native_id and ref.launch_id not in self._known:
                self._try_adopt(ref)  # after a restart
        for command in self.sink.lease_commands():
            self._command(command)
        # the heads start once the whole lease is applied: a cancel leased after its launch has
        # written its marker by then, so the head stops before its engine (FU-P3-108a)
        starts, self._starts = self._starts, []
        for command, spec in starts:
            self._command(command, spec)
        launches = self.sink.active_launches()
        for ref in launches:
            self._each(self._read, ref)
            if ref.terminal is not None:
                self._each(self._watch_terminal, ref)
        self._end_pointers({r.run_id for r in launches if r.terminal is not None})
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

    def _try_adopt(self, ref: LaunchRef) -> None:
        """Adopt, and log a refusal once per launch, not at every tick (CR-P3T09-09)."""
        try:
            self._adopt(ref)
        except Exception:
            if ref.launch_id in self._unadopted:
                log.debug("launch %s of %s still not adopted", ref.launch_n, ref.run_id)
            else:
                self._unadopted.add(ref.launch_id)
                log.exception("launch %s of %s not adopted", ref.launch_n, ref.run_id)
        else:
            self._unadopted.discard(ref.launch_id)

    def _forget(self, active: set[str]) -> None:
        gone = [r.native_id for i, r in self._last.items() if i not in active and r.native_id]
        self.launcher.forget(gone)  # CR-P3T09-07
        for kept in (self._known, self._refused, self._unadopted):
            kept.intersection_update(active)
        for by_launch in (self._last, self._ended_at):
            for launch_id in by_launch.keys() - active:
                del by_launch[launch_id]

    # --- Commands ------------------------------------------------------------------------

    def _command(self, command: Command, start: LaunchSpec | None = None) -> None:
        """Apply one command and ack it; a launch is acked once `start`, its head, is started."""
        try:
            if command.launch.terminal is not None:  # never a launcher call (req. 12)
                self.sink.ack(command.id, False, "a run started from a terminal is monitor only")
                return
            if start is not None:
                detail = self._start(command.launch, start)
            elif command.kind == "launch":
                found = self._launch(command)
                if isinstance(found, LaunchSpec):
                    self._starts.append((command, found))
                    return
                detail = found
            elif command.kind == "cancel":
                detail = self._cancel(command.launch)
            else:
                detail = f"unknown command {command.kind!r}"
        except Exception as exc:
            log.exception("command %s (%s) failed", command.id, command.kind)
            detail = f"{type(exc).__name__}: {exc}"
        self.sink.ack(command.id, detail is None, detail)

    def _launch(self, command: Command) -> LaunchSpec | str | None:
        """The head to start, or the ack's detail (None: nothing to start)."""
        ref = command.launch
        if ref.launch_id in self._known:
            return None  # delivered again: already started
        root = self.settings.runs_root
        try:
            paths = make_run_dirs(root, ref.run_id)
            check_launch_dir(root, ref.run_id, ref.launch_dir)
            with private_dir(root, ref.run_id, "launch", ".spectio") as fd:
                owner = _claim(fd, ref.launch_n)
                if owner != ref.launch_n:
                    return f"launch {owner} owns the head files: launch {ref.launch_n} is late"
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
            last = self._last.get(ref.launch_id)
            if cancelled and last is not None and last.native_id and not last.ended:
                # a cancel that came with no native ID only wrote the marker (CR-P3T09-04 r2)
                self.launcher.cancel(last.native_id)
            return None
        if cancelled:  # cancelled before its head started: it never starts (CR-P3T09-02),
            # and with a failure it skips the spool grace: no engine ran (CR-P3T09-03)
            failure = Failure("head_lost", "Cancelled before its head started.")
            self._report(ref, HeadReport("unknown", None, None, None, True, failure))
            return None
        try:
            payload = LaunchPayload.model_validate(command.payload)
            registry = from_registry(payload.target, ref.engine)  # api §5.10
            if not registry and not Path(payload.location).is_absolute():
                raise ValueError(f"{payload.location!r} is not an absolute path")
            environment = payload.environment or as_snapshot(
                snapshot(server_builtin(self.settings).environment)
            )
            check_on_server(environment, self.settings)
            asked = payload.resume_of
            resume = None if asked is None else self._resume_source(ref, asked)
            engines = self.settings.engines
            cmd = engines.nextflow_cmd if ref.engine == "nextflow" else engines.snakemake_cmd
            info = check_engine(ref.engine, cmd)
            fields = launch_fields(environment)  # the run's own, never the server's (req. 18)
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
                **fields,
                nxf_opts=engines.nxf_opts,
                nxf_syntax_parser=engines.nxf_syntax_parser,
                extra_args=engines.extra_args.get(ref.engine, []),
                resume_of=resume,
                target=payload.target,
                default_resources=payload.default_resources,
                config_file=extra_file(payload),
                main_script=payload.main_script,
                # The shared cache of the software deployment (inbox #161): the conda
                # environments and Apptainer images build once, off the home directory.
                software_cache=software_cache_dir(self.settings),
                # Only the Snakemake SLURM plugin has a status command to set (FU-P3-106b);
                # a definite answer is kept for the process, a failure asked again later.
                slurm_accounting=(
                    site_accounting(self.settings.slurm.sacct)
                    if ref.engine == "snakemake" and fields["slurm"] is not None
                    else None
                ),
            )
            status, detail = runs_disk(self.settings.runs_root)
            if status == "warn":  # never refused: the engine may still fit (FU-P3-74)
                log.warning("runs_disk %s", detail)
        except EngineError as exc:
            return self._fail(ref, exc.class_, str(exc))
        except (OSError, ValueError) as exc:
            return self._fail(ref, "launch_error", str(exc))
        return spec

    def _start(self, ref: LaunchRef, spec: LaunchSpec) -> str | None:
        if ref.launch_id in self._known:
            return None  # leased twice: already started
        try:
            native_id = self.launcher.submit(spec)
        except (OSError, ValueError) as exc:
            return self._fail(ref, "launch_error", str(exc))
        self._known.add(ref.launch_id)
        self._report(ref, HeadReport("starting", native_id, None, None, False, None))
        if self._cancel_asked(ref):  # cancelled in this lease: its marker first, then the signal
            self.launcher.cancel(native_id)
        return None

    def _resume_source(self, ref: LaunchRef, asked: ResumePayload) -> ResumeSource:
        """The parent's directories, checked again now (req. 16): its head gone, nobody in the
        launch directory, and that directory still the one the server checked. A lock its
        killed head left is removed. Raises NotResumable (a ValueError)."""
        root = self.settings.runs_root
        found = prove(root, asked.run_id, asked.parent_run_id)
        if found != (asked.device, asked.inode):
            raise ValueError("the parent's launch directory changed since Resume was asked")
        clear_stale_lock(root, asked.run_id)
        parent = run_paths(root, asked.run_id)
        return ResumeSource(
            launch_dir=parent.launch_dir,
            work_dir=parent.work_dir,
            device=found[0],
            inode=found[1],
            engine_session_id=asked.engine_session_id,
            unlock=ref.engine == "snakemake",  # its head is proven gone: prove() above
        )

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
            owner = _claim(fd, ref.launch_n)
            if owner != ref.launch_n:
                return f"launch {owner} owns the head files: launch {ref.launch_n} is late"
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
            if (
                ref.engine_ended
                or (ref.engine == "snakemake" and report.exit_code is not None)
                or self._cancel_asked(ref)
            ):
                # the engine's end event is in (G7), a Snakemake exit code ends the launch
                # (Assumption 16), or it was cancelled, and the run ends cancelled whatever the
                # engine says (FU-P3-108a): the head is gone, so one more read drains its
                # spool, with no grace to wait (FU-P3-14, CR-P3T09-04, CR-P3G7-07)
                self._read(ref)
            else:
                first = self._ended_at.setdefault(ref.launch_id, time.monotonic())
                if time.monotonic() - first < self.end_grace_s:
                    return  # its last events may still be in the spool (Assumption 15)
            if not ref.engine_ended:  # an engine that ended on its own event has no failure
                report = ended_failure(ref.engine, report, self._head_output(ref))
        if self._last.get(ref.launch_id) == report:
            return
        self._last[ref.launch_id] = report
        self.sink.head_report(ref.launch_id, report)

    def _head_output(self, ref: LaunchRef) -> str | None:
        """The end of the launch's `.spectio/head.out` (#368), None for a run started from a
        terminal, a Snakemake launch, or a file that cannot be read safely."""
        if ref.terminal is not None or ref.engine != "nextflow":
            return None
        try:
            with private_dir(self.settings.runs_root, ref.run_id, "launch", ".spectio") as fd:
                return engine_output_tail(_read_tail(fd, HEAD_OUT, TAIL_READ))
        except (OSError, ValueError):
            return None

    def _cancel_asked(self, ref: LaunchRef) -> bool:
        """Whether this launch's `.spectio/cancel` marker is there (never for a run started
        from a terminal, which is never cancelled from here); unreadable, the grace applies."""
        if ref.terminal is not None:
            return False
        try:
            with private_dir(self.settings.runs_root, ref.run_id, "launch", ".spectio") as fd:
                return _exists(fd, CANCEL)
        except (OSError, ValueError):
            return False

    def _fs(self, key: str, fn: Callable[[], T]) -> T:
        """`fn()` in the file pool with its timeout when there is one; raises `Stalled`. A job
        of `key` still in the pool is not sent again (`Stalled` at once): a stuck launch
        directory holds one thread, not one per tick (CR-P3T25-03). The one-shot `claim` lets
        exactly one side, the job or the caller that gave up, take the key off (CR-P3T25-r3-01)."""
        if self.files is None:
            return fn()
        if key in self._busy:
            raise Stalled("the file system has not answered the last read yet")
        claim = threading.Lock()

        def job() -> T:
            if not claim.acquire(blocking=False):
                raise Stalled("the caller gave up before this job ran")
            try:
                return fn()
            finally:
                self._busy.discard(key)

        self._busy.add(key)
        try:
            return self.files.run(job, self.files_timeout_s)
        except BaseException:  # also a pool that cannot start a thread (SEC-P3T25-r3-02)
            if claim.acquire(blocking=False):  # it never ran, and now never will
                self._busy.discard(key)
            raise

    def _read(self, ref: LaunchRef) -> None:
        cursor = self.sink.cursor(ref.launch_id)
        if ref.terminal is None:
            batch = self._spool(ref, cursor)
        else:  # project storage: bounded, and a stuck one is skipped and counted
            try:
                batch = self._fs(ref.launch_id, partial(self._spool, ref, cursor))
            except Stalled as exc:
                log.warning("spool of %s not read: %s", ref.run_id, exc)
                batch = SpoolBatch([], dict(cursor), Counter({SPOOL_STALLED: 1}))
                self._ended_at.pop(ref.launch_id, None)  # its last events are still unread
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

    def _spool(self, ref: LaunchRef, cursor: dict[str, int]) -> SpoolBatch:
        """Check the launch directory, then read its spool: a whole file-system job."""
        observed = ref.terminal is not None
        try:
            if observed:  # its pointer's launch directory, never one in the runs root
                check_observed_launch_dir(self.settings.runs_root, str(ref.launch_dir))
            else:
                check_launch_dir(self.settings.runs_root, ref.run_id, ref.launch_dir)
        except (OSError, ValueError) as exc:
            log.debug("launch directory of %s refused: %r", ref.run_id, exc)
            return SpoolBatch([], dict(cursor), Counter({SPOOL_REFUSED: 1}))
        return try_read_spool(ref.launch_dir, ref.run_id, ref.launch_n, cursor, observed=observed)

    # --- Runs started from a terminal (architecture §13.8, req. 12) ----------------------------

    def _observe(self, home: Path) -> None:
        """Scan `~/.spectio/observed/` when its mtime changed, and add each new run. The scan
        is bounded: a stuck one is logged and tried again at the next tick (SEC-P3T25-01)."""
        job = partial(
            scan_observed,
            home,
            self.settings.runs_root,
            set(self._pointers),  # a copy: a stalled scan goes on in its thread
            self.observe_cap,
            since_ns=self._pointers_mtime,
        )
        try:
            scan = self._fs("scan", job)
        except Stalled as exc:
            log.warning("runs started from a terminal not scanned: %s", exc)
            return
        self._pointers_mtime = scan.mtime_ns
        self._pointers |= scan.seen
        refused = bool(scan.skipped.pop("observed_refused", 0))
        if refused and not self._observed_refused:
            log.warning("%s/.spectio/observed is not a private directory: not read", home)
        self._observed_refused = refused
        if +scan.skipped:
            log.warning("pointers skipped: %s", dict(scan.skipped))
        for run in scan.runs:
            if self.sink.add_observed(run):
                end_pointer(home, run.run_id)  # it ended while its pointer stayed

    def _watch_terminal(self, ref: LaunchRef) -> None:
        """The PID check, only on the pointer's host and boot; elsewhere the head is not checked
        and only a terminal event ends the run. Nothing is ever signalled."""
        head = ref.terminal
        if head is None or not checkable(head.host, head.boot_id):
            return
        alive = same_process(head.pid, head.start)
        report = HeadReport(
            "running" if alive else "exited", None, head.host, None, not alive, None
        )
        self._report(ref, report)

    def _end_pointers(self, active: set[str]) -> None:
        """Move the pointer of each run started from a terminal that is no longer active."""
        ended, self._terminal = self._terminal - active, active
        if self.home is None:
            return
        for run_id in ended:
            try:
                end_pointer(self.home, run_id)
            except (OSError, ValueError):
                log.exception("pointer of %s not moved to ended/", run_id)


def _claim(dir_fd: int, launch_n: int) -> int:
    """The launch that owns the head files, after launch `launch_n` took them from an earlier
    one, whose files it removes first (CR-P3T09-11). A later owner is returned unchanged."""
    raw = read_small(dir_fd, OWNER, cap=16)
    owner = 1
    if raw is not None:
        match = _OWNER_LINE.fullmatch(raw.decode("ascii", "replace"))
        if match is None:
            raise ValueError(f".spectio/{OWNER} is not a launch number")
        owner = int(match[1])
    if owner >= launch_n:
        return owner
    for name in HEAD_FILES:
        try:
            os.unlink(name, dir_fd=dir_fd)
        except FileNotFoundError:
            pass
    write_file(dir_fd, OWNER, f"{launch_n}\n".encode())
    return launch_n


def _read_tail(dir_fd: int, name: str, size: int) -> bytes:
    """The last `size` bytes of a regular file of the user that others cannot write, reached
    through no symlink (the rules of `read_small`)."""
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid():
            raise PermissionError(f"{name}: not a regular file of this user")
        if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):  # as read_small (SEC-P3T09-01)
            raise PermissionError(f"{name}: writable by others")
        return os.pread(fd, size, max(0, st.st_size - size))
    finally:
        os.close(fd)


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
