"""The server's side of the runner (P1 Task 11): `StoreSink` implements `RunnerSink` through the
one writer, so that the runner never imports the server (architecture §6).

Launch directories are derived from the runs root and the run ID, never read from a row
(dev-env §15.3 req. 10). A `runner_commands` row is leased for `LEASE` and delivered again once
the lease runs out; the runner loop makes a second delivery harmless (P1 Task 9).
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar, cast, get_args

from sqlalchemy import Connection, Row, and_, or_, select, update

from spectio.runner.rundir import run_paths
from spectio.runner.types import Command, Engine, HeadReport, LaunchRef, SpoolBatch
from spectio_server.projector.ingest import apply_head_report, ingest, load_cursor
from spectio_server.projector.runs import TERMINAL
from spectio_server.stages.freeze import StageSources
from spectio_server.store.schema import (
    launches,
    runner_commands,
    runs,
    workflow_versions,
    workflows,
)
from spectio_server.store.writer import Writer

log = logging.getLogger(__name__)

LEASE = timedelta(seconds=60)
ENGINES = get_args(Engine)

T = TypeVar("T")


class StoreSink:
    def __init__(self, writer: Writer, runs_root: Path, overlays: Path | None = None) -> None:
        self.writer = writer
        self.runs_root = runs_root
        self.sources = StageSources(overlays, runs_root)  # stage sources (P1 Task 27)

    def _do(self, fn: Callable[[Connection], T]) -> T:
        return self.writer.submit(fn).result()

    def lease_commands(self) -> list[Command]:
        return self._do(self._lease)

    def ack(self, command_id: str, ok: bool, detail: str | None) -> None:
        if detail:
            log.info("command %s: %s", command_id, detail)
        self._do(
            lambda conn: conn.execute(
                update(runner_commands)
                .where(runner_commands.c.id == command_id)
                .values(state="done" if ok else "failed", lease_until=None)
            )
        )

    def active_launches(self) -> list[LaunchRef]:
        """The launches of every run that has not ended, and of every head not yet reported
        ended: a run can end (its engine's own end, a cancel) before its head, which the runner
        keeps watching, or `forget` would drop a SIGKILL still due (CR-P3T09-R5-03)."""
        head_left = launches.c.head_native_id.is_not(None) & launches.c.exited_at.is_(None)
        active = or_(runs.c.state.not_in(TERMINAL), head_left)
        return self._do(
            lambda conn: [
                ref
                for row in conn.execute(_launch_query().where(active))
                if (ref := self._ref(row)) is not None
            ]
        )

    def cursor(self, launch_id: str) -> dict[str, int]:
        return self._do(lambda conn: load_cursor(conn, launch_id))

    def ingest(self, launch_id: str, batch: SpoolBatch) -> None:
        self._do(lambda conn: ingest(conn, launch_id, batch, self.sources))

    def head_report(self, launch_id: str, report: HeadReport) -> None:
        self._do(lambda conn: apply_head_report(conn, launch_id, report))

    def _lease(self, conn: Connection) -> list[Command]:
        now = datetime.now(UTC)
        due = or_(
            runner_commands.c.state == "pending",
            and_(runner_commands.c.state == "leased", runner_commands.c.lease_until < now),
        )
        found = conn.execute(
            select(runner_commands).where(due).order_by(runner_commands.c.created_at)
        ).all()
        refs = {
            row.id: self._ref(row)
            for row in conn.execute(
                _launch_query().where(launches.c.id.in_({c.launch_id for c in found}))
            )
        }
        commands = []
        for row in found:
            ref = refs.get(row.launch_id)
            if ref is None:  # no launch, or one the runner cannot run: never delivered
                values: dict[str, Any] = {"state": "failed"}
            else:
                values = {"state": "leased", "lease_until": now + LEASE}
                commands.append(Command(row.id, row.kind, ref, row.payload or {}))
            conn.execute(
                update(runner_commands)
                .where(runner_commands.c.id == row.id)
                .values(attempts=runner_commands.c.attempts + 1, **values)
            )
        return commands

    def _ref(self, row: Row[Any]) -> LaunchRef | None:
        if row.engine not in ENGINES:
            log.warning("launch %s: engine %r is not one the runner runs", row.id, row.engine)
            return None
        return LaunchRef(
            launch_id=row.id,
            run_id=row.run_id,
            launch_n=row.n,
            engine=cast(Engine, row.engine),
            launch_dir=run_paths(self.runs_root, row.run_id).launch_dir,
            native_id=row.head_native_id,
        )


def _launch_query() -> Any:
    return (
        select(
            launches.c.id,
            launches.c.run_id,
            launches.c.n,
            launches.c.head_native_id,
            workflows.c.engine,
        )
        .join(runs, runs.c.id == launches.c.run_id)
        .join(workflow_versions, workflow_versions.c.id == runs.c.workflow_version_id)
        .join(workflows, workflows.c.id == workflow_versions.c.workflow_id)
    )
