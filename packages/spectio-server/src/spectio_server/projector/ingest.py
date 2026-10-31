"""Ingest a spool batch and a head report: api §8.1, §8.2 and §14.1 (P1 Task 4).

Both run on the writer thread, in its transaction (P1 Assumption 11): `ingest` appends the new
events to the log, projects them, and stores the cursor and the drop counts; the run's
`projected_seq` therefore always equals its `last_seq`. Event IDs make a replay a no-op.
"""

import logging
from collections import Counter
from typing import Any

from pydantic import ValidationError
from sqlalchemy import Connection, select, update
from sqlalchemy.exc import OperationalError

from spectio.runner.types import HeadReport, SpoolBatch
from spectio_sdk.events import UnknownEventType, parse_data
from spectio_server.projector import nextflow, snakemake
from spectio_server.projector.runs import ENGINE_ENDED, IN_CHUNK, Projection, failure_json
from spectio_server.store.schema import events, launches, spool_cursors, spool_drops

# Classes of a head that ended with no terminal engine event: its open attempts failed (§7.1).
HEAD_FAILURES = frozenset({"head_lost", "engine_fault"})

log = logging.getLogger(__name__)


def load_cursor(conn: Connection, launch_id: str) -> dict[str, int]:
    """The launch's spool cursor, as `read_spool` takes it."""
    rows = conn.execute(
        select(spool_cursors.c.file, spool_cursors.c.offset).where(
            spool_cursors.c.launch_id == launch_id
        )
    ).all()
    return {file: offset for file, offset in rows}


def ingest(conn: Connection, launch_id: str, batch: SpoolBatch) -> None:
    """Log and project the batch's new events, then store its cursor and drops.

    An event already in the log (same run, same event ID) is skipped. Its data is checked
    against the allow-list again before it is stored, so a forbidden field never reaches the
    log whoever built the batch (P1 Assumption 3); data that fails is dropped and counted
    `invalid`. Each event is logged and projected in its own savepoint: one whose projection
    raises is rolled back, dropped and counted `projection_error`, so it never holds back the
    cursor (dev-env §15.3 req. 6), and is logged with its traceback. A database
    `OperationalError` (disk full, I/O error) propagates, so the batch rolls back and the cursor
    stays. Raises ValueError, and writes nothing, when an event is of another run or launch.
    """
    p = Projection.load(conn, launch_id)
    if any(e.run != p.run_id or e.launch != p.launch_n for e in batch.events):
        raise ValueError(f"the batch holds an event of another run or launch than {launch_id}")
    seen = _logged(conn, p.run_id, [e.id for e in batch.events])
    drops = Counter(batch.drops)
    for event in batch.events:
        if event.id in seen:
            continue
        seen.add(event.id)
        try:
            data = parse_data(event)
        except (ValidationError, UnknownEventType):
            drops["invalid"] += 1
            continue
        kept = (p.last_seq, p.state, p.head_state)
        p.event_time = event.time
        savepoint = conn.begin_nested()
        try:
            p.log(
                f"spectio.engine.{event.type}",
                data.model_dump(mode="json", by_alias=True, exclude_unset=True),
                event_id=event.id,
                source=event.producer,
                source_seq=event.seq,
                engine_time=event.time,
            )
            p.move("running")  # the first engine event starts a queued run (api §7.1)
            engine, hook = event.type.split(".", 1)
            if engine == "nextflow":
                nextflow.project(p, hook, data)
            else:
                snakemake.project(p, data)
        except OperationalError:
            raise  # a storage fault: the whole batch rolls back and the cursor stays
        except Exception:
            log.exception("event %s of %s not projected", event.id, p.run_id)
            savepoint.rollback()
            p.last_seq, p.state, p.head_state = kept
            drops["projection_error"] += 1
            continue
        savepoint.commit()
    _store_cursor(conn, launch_id, batch.cursor, drops)
    p.finish()


def apply_head_report(conn: Connection, launch_id: str, report: HeadReport) -> None:
    """Record what the runner saw of the head, and move the run (api §7.1, P1 Assumption 15).

    A running head starts a queued run. A failure fails a queued or running run: a launch that
    could not start, or a head that ended with no terminal engine event (`head_lost`,
    `engine_fault`), whose open attempts then fail with class `head_lost`. A head that ends
    while the run is `cancelling` makes it `cancelled`. A Snakemake head's exit code ends its
    launch (P1 Assumption 16), even when the report also carries a `head_lost` or `engine_fault`
    failure: a Snakemake head never writes a terminal engine event (CR-P3T05-01). A terminal
    run does not move, and the engine's own end (`head_state` set by `onFlowComplete`) is kept.
    """
    p = Projection.load(conn, launch_id)
    values: dict[str, Any] = {}
    if p.head_state not in ENGINE_ENDED:
        values["head_state"] = report.state
    if report.native_id is not None:
        values["head_native_id"] = report.native_id
    if report.exit_code is not None:
        values["exit_code"] = report.exit_code
    p.set_launch(**values)
    if report.ended:  # the first end is kept (api §8.2)
        conn.execute(
            update(launches)
            .where(launches.c.id == launch_id, launches.c.exited_at.is_(None))
            .values(exited_at=p.now)
        )
    failure = report.failure
    if p.state == "cancelling" and report.ended:
        p.end_launch()
        p.move("cancelled")
    elif (
        report.ended
        and report.exit_code is not None
        and (failure is None or failure.class_ in HEAD_FAILURES)
        and snakemake.drives(p)
    ):  # a Snakemake head never writes a terminal event: its exit code wins (CR-P3T05-01)
        snakemake.head_exit(p, report.exit_code)
    elif failure is not None and p.state in ("queued", "running"):
        if failure.class_ in HEAD_FAILURES:
            p.end_launch("failed", "head_lost")
        else:
            p.end_launch()
        p.move("failed", failure_json(failure.class_, failure.message, failure.task_id))
    elif report.state == "running" and not report.ended:
        p.move("running")
    p.finish()


def _logged(conn: Connection, run_id: str, event_ids: list[str]) -> set[str]:
    found: set[str] = set()
    for i in range(0, len(event_ids), IN_CHUNK):
        chunk = event_ids[i : i + IN_CHUNK]
        found.update(
            conn.execute(
                select(events.c.event_id).where(
                    events.c.run_id == run_id, events.c.event_id.in_(chunk)
                )
            ).scalars()
        )
    return found


def _store_cursor(
    conn: Connection, launch_id: str, cursor: dict[str, int], drops: Counter[str]
) -> None:
    """Upsert each cursor offset; add each drop count (they are per read)."""
    for file, offset in cursor.items():
        key = (spool_cursors.c.launch_id == launch_id) & (spool_cursors.c.file == file)
        if not conn.execute(update(spool_cursors).where(key).values(offset=offset)).rowcount:
            conn.execute(
                spool_cursors.insert().values(launch_id=launch_id, file=file, offset=offset)
            )
    for reason, n in drops.items():
        if n <= 0:
            continue
        key = (spool_drops.c.launch_id == launch_id) & (spool_drops.c.reason == reason)
        added = update(spool_drops).where(key).values(count=spool_drops.c.count + n)
        if not conn.execute(added).rowcount:
            conn.execute(spool_drops.insert().values(launch_id=launch_id, reason=reason, count=n))
