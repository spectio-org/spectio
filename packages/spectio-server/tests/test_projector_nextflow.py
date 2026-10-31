"""The projector, run states and the Nextflow mapping: api §7.1, §7.2, §8.2 (P1 Task 4).

The T2 fixtures are read through the real spool reader (Task 3), as the runner reads them, then
ingested through the one writer (Task 2).
"""

import json
import logging
import shutil
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, func, insert, select, update
from sqlalchemy import event as sa_event
from sqlalchemy.exc import IntegrityError, OperationalError

from spectio.runner.spool import read_spool, try_read_spool
from spectio.runner.types import Failure, HeadReport, SpoolBatch
from spectio_sdk.events import SpoolEvent
from spectio_server.projector import nextflow as nextflow_projector
from spectio_server.projector.ingest import apply_head_report, ingest, load_cursor
from spectio_server.projector.runs import Projection
from spectio_server.store.db import open_db
from spectio_server.store.schema import (
    attempts,
    environments,
    events,
    launches,
    projects,
    runs,
    spool_drops,
    tasks,
    workflow_versions,
    workflows,
)
from spectio_server.store.writer import Writer

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "engine-events"
RUN_ID = "run_01K8T2F1XTVRES000000000000"  # the run of every converted T2 fixture
LAUNCH_ID = "lch_1"
NF_FILE = "nf-spectio-1-0001.jsonl"
NOW = datetime(2026, 10, 30, tzinfo=UTC)
FORBIDDEN = ("script", "env", "commandLine", "homeDir", "configText", "cmd")


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    db_dir = tmp_path / "db"
    db_dir.mkdir(mode=0o700)
    eng, _ = open_db(db_dir)
    yield eng
    eng.dispose()


@pytest.fixture
def writer(engine: Engine) -> Iterator[Writer]:
    w = Writer(engine)
    w.submit(_seed).result()
    yield w
    w.close()


def _seed(conn: Connection) -> None:
    conn.execute(insert(projects).values(id="prj_1", owning_group_id="grp_1", created_at=NOW))
    conn.execute(insert(environments).values(id="env_1", kind="local", created_at=NOW))
    conn.execute(
        insert(workflows).values(
            id="wfl_1", project_id="prj_1", source="local", location="/w", created_at=NOW
        )
    )
    conn.execute(insert(workflow_versions).values(id="wfv_1", workflow_id="wfl_1", created_at=NOW))
    conn.execute(
        insert(runs).values(
            id=RUN_ID,
            project_id="prj_1",
            workflow_version_id="wfv_1",
            environment_id="env_1",
            state="queued",
            created_at=NOW,
        )
    )
    conn.execute(insert(launches).values(id=LAUNCH_ID, run_id=RUN_ID, n=1, created_at=NOW))


def spool_dir(tmp_path: Path) -> Path:
    launch_dir = tmp_path / "launch"
    (launch_dir / ".spectio" / "events").mkdir(mode=0o700, parents=True)
    (launch_dir / ".spectio").chmod(0o700)
    return launch_dir


def batches(tmp_path: Path, fixture: str) -> list[SpoolBatch]:
    """The fixture as the runner reads it: every batch until the spool is drained."""
    launch_dir = spool_dir(tmp_path)
    target = launch_dir / ".spectio" / "events" / NF_FILE
    shutil.copyfile(FIXTURES / fixture, target)
    target.chmod(0o600)
    out: list[SpoolBatch] = []
    cursor: dict[str, int] = {}
    while True:
        batch = read_spool(launch_dir, RUN_ID, 1, cursor, max_lines=100)
        if not batch.events:
            return out
        out.append(batch)
        cursor = batch.cursor


def submit(writer: Writer, batch: SpoolBatch) -> None:
    writer.submit(lambda conn: ingest(conn, LAUNCH_ID, batch)).result()


def replay(tmp_path: Path, writer: Writer, fixture: str) -> None:
    for batch in batches(tmp_path, fixture):
        submit(writer, batch)


def run_row(engine: Engine) -> Any:
    with engine.connect() as conn:
        return conn.execute(select(runs).where(runs.c.id == RUN_ID)).one()


def attempt_states(engine: Engine) -> list[tuple[str, str | None, int, str]]:
    """(process, tag, attempt n, state) of every attempt."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(tasks.c.process_or_rule, tasks.c.tag, attempts.c.n, attempts.c.state).join(
                attempts, attempts.c.task_id == tasks.c.id
            )
        ).all()
    return [tuple(r) for r in rows]


def state_changes(engine: Engine) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(events.c.payload)
            .where(events.c.type == "spectio.run.state_changed")
            .order_by(events.c.seq)
        ).all()
    return [r.payload for r in rows]


def event(n: int, type_: str, **data: Any) -> SpoolEvent:
    return SpoolEvent.model_validate(
        {
            "v": 1,
            "id": f"evt_x{n}",
            "run": RUN_ID,
            "launch": 1,
            "producer": "nf-spectio/0.0.1",
            "seq": 10_000 + n,
            "time": "2026-10-28T07:30:00Z",
            "type": f"nextflow.{type_}",
            "data": data,
        }
    )


def ingest_events(writer: Writer, *evs: SpoolEvent, cursor: dict[str, int] | None = None) -> None:
    batch = SpoolBatch(list(evs), cursor or {}, Counter())
    submit(writer, batch)


def task(n: int, hook: str, process: str = "ALIGN", tag: str | None = "S01", **data: Any) -> Any:
    return event(n, hook, process=process, tag=tag, attempt=1, taskId=str(n), **data)


# --- The T2 fixtures (P1 Task 4, Step 1) ---------------------------------------------------


@pytest.mark.parametrize("version", ["26.10.4", "25.10.9"])
def test_flaky(tmp_path: Path, engine: Engine, writer: Writer, version: str) -> None:
    replay(tmp_path, writer, f"nextflow-{version}_plugin_flaky.spool.jsonl")
    run = run_row(engine)
    assert run.state == "succeeded"
    assert run.task_counts == {"succeeded": 65}
    assert run.failure is None
    states = attempt_states(engine)
    assert len(states) == 67
    assert Counter(s for *_, s in states) == {"succeeded": 65, "failed": 2}
    per_task = Counter((p, t) for p, t, _, _ in states)
    assert len(per_task) == 65
    assert sorted(per_task.values())[-3:] == [1, 2, 2]  # two tasks retried once
    assert [c["to"] for c in state_changes(engine)] == ["running", "succeeded"]


def test_toolerr_26_10_4(tmp_path: Path, engine: Engine, writer: Writer) -> None:
    replay(tmp_path, writer, "nextflow-26.10.4_plugin_toolerr.spool.jsonl")
    run = run_row(engine)
    assert run.state == "failed"
    assert run.failure["message"] == "synthetic failure: tool exited with code 1"
    assert run.failure["class"] == "tool_error"
    states = {(p, t): s for p, t, _, s in attempt_states(engine)}
    assert states[("COMPARE", "treatA_vs_ctrl")] == "failed"
    assert states[("FINAL_REPORT", None)] == "aborted"
    assert run.task_counts["failed"] == 1  # FINAL_REPORT is aborted, not failed
    assert run.task_counts["aborted"] == 1
    with engine.connect() as conn:
        failed = conn.execute(
            select(tasks.c.id, attempts.c.n, attempts.c.failure_class)
            .join(attempts, attempts.c.task_id == tasks.c.id)
            .where(tasks.c.process_or_rule == "COMPARE", tasks.c.tag == "treatA_vs_ctrl")
        ).one()
        aborted = conn.execute(
            select(attempts.c.failure_class)
            .join(tasks, attempts.c.task_id == tasks.c.id)
            .where(tasks.c.process_or_rule == "FINAL_REPORT")
        ).scalar_one()
    assert (run.failure["task_id"], run.failure["attempt_n"]) == (failed.id, failed.n)
    assert failed.failure_class == "tool_error"
    assert aborted is None  # an aborted attempt has no failure class (api §7.2)


def test_toolerr_25_10_9_double_flow_complete(
    tmp_path: Path, engine: Engine, writer: Writer
) -> None:
    replay(tmp_path, writer, "nextflow-25.10.9_plugin_toolerr.spool.jsonl")
    assert [c["to"] for c in state_changes(engine)] == ["running", "failed"]
    run = run_row(engine)
    assert run.state == "failed"
    assert run.failure["class"] == "tool_error"
    with engine.connect() as conn:
        launch = conn.execute(select(launches).where(launches.c.id == LAUNCH_ID)).one()
        flow_completes = conn.execute(
            select(func.count())
            .select_from(events)
            .where(events.c.type == "spectio.engine.nextflow.onFlowComplete")
        ).scalar_one()
    assert flow_completes == 2  # both are logged; only the first one counts
    assert launch.head_state == "failed"
    states = {(p, t): s for p, t, _, s in attempt_states(engine)}
    assert states[("COMPARE", "treatB_vs_ctrl")] == "aborted"  # trace status ABORTED


@pytest.mark.parametrize(("version", "cached"), [("26.10.4", 63), ("25.10.9", 62)])
def test_resume(tmp_path: Path, engine: Engine, writer: Writer, version: str, cached: int) -> None:
    # Only the `cached` mapping: Resume itself is not in this task.
    replay(tmp_path, writer, f"nextflow-{version}_plugin_resume.spool.jsonl")
    run = run_row(engine)
    assert run.state == "succeeded"
    assert run.task_counts == {"cached": cached, "succeeded": 65 - cached}


def test_forbidden_fields_never_stored(engine: Engine, writer: Writer) -> None:
    secret = {k: f"SECRET-{k}" for k in FORBIDDEN}
    ingest_events(
        writer,
        task(
            1,
            "onTaskComplete",
            status="COMPLETED",
            trace={"status": "COMPLETED", **secret},
            **secret,
        ),
        event(2, "onFlowCreate", nextflow="26.10.4", **secret),
    )
    with engine.connect() as conn:
        stored = conn.execute(select(events.c.payload)).scalars().all()
    text = json.dumps(stored)
    assert "SECRET-" not in text
    for key in FORBIDDEN:
        assert f'"{key}"' not in text


def test_replay_is_idempotent(tmp_path: Path, engine: Engine, writer: Writer) -> None:
    all_batches = batches(tmp_path, "nextflow-26.10.4_plugin_flaky.spool.jsonl")
    for batch in all_batches:
        submit(writer, batch)
    first = run_row(engine)
    for batch in all_batches:
        submit(writer, batch)
    again = run_row(engine)
    assert (again.task_counts, again.last_seq, again.state) == (
        first.task_counts,
        first.last_seq,
        first.state,
    )
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(events)).scalar_one() == first.last_seq


def test_run_times_come_from_the_engine(tmp_path: Path, engine: Engine, writer: Writer) -> None:
    # onFlowBegin and onFlowComplete times, not the ingest clock (inbox #79, FU-P3-04).
    fixture = "nextflow-26.10.4_plugin_flaky.spool.jsonl"
    lines = [json.loads(x) for x in (FIXTURES / fixture).read_text().splitlines()]
    when = {e["type"]: datetime.fromisoformat(e["time"]) for e in lines}
    replay(tmp_path, writer, fixture)
    run = run_row(engine)
    assert run.started_at == when["nextflow.onFlowBegin"]
    assert run.ended_at == when["nextflow.onFlowComplete"]


def test_terminal_state_never_moves_back(tmp_path: Path, engine: Engine, writer: Writer) -> None:
    replay(tmp_path, writer, "nextflow-26.10.4_plugin_flaky.spool.jsonl")
    late = task(1, "onTaskStart", process="MAKE_READS", tag="S01")
    ingest_events(writer, late)
    assert run_row(engine).state == "succeeded"
    states = {(p, t): s for p, t, _, s in attempt_states(engine)}
    assert states[("MAKE_READS", "S01")] == "succeeded"
    with engine.connect() as conn:
        logged = conn.execute(select(events.c.type).where(events.c.event_id == late.id)).scalar()
    assert logged == "spectio.engine.nextflow.onTaskStart"


# --- Sequence, cursor and drops (api §8.2, P1 Assumption 11) -------------------------------


def test_seq_without_gaps_and_projected(tmp_path: Path, engine: Engine, writer: Writer) -> None:
    replay(tmp_path, writer, "nextflow-26.10.4_plugin_toolerr.spool.jsonl")
    run = run_row(engine)
    with engine.connect() as conn:
        seqs = conn.execute(select(events.c.seq).order_by(events.c.seq)).scalars().all()
    assert seqs == list(range(1, run.last_seq + 1))
    assert run.projected_seq == run.last_seq
    assert run.last_seq == 293 + 3  # every spool line, two state changes, the stages frozen


def test_first_event_starts_the_run(engine: Engine, writer: Writer) -> None:
    ingest_events(writer, event(1, "onFlowCreate", nextflow="26.10.4", sessionId="s-1"))
    run = run_row(engine)
    assert run.state == "running"
    assert run.started_at is not None and run.state_changed_at is not None
    assert run.engine_version == "26.10.4"
    with engine.connect() as conn:
        launch = conn.execute(select(launches).where(launches.c.id == LAUNCH_ID)).one()
    assert launch.engine_session_id == "s-1"


def test_cursor_and_drops_stored(engine: Engine, writer: Writer) -> None:
    batch = SpoolBatch([], {NF_FILE: 120, "#excess": 3}, Counter({"invalid": 2}))
    for _ in range(2):  # drop counts are per read, so they add up
        submit(writer, batch)
    with engine.connect() as conn:
        assert load_cursor(conn, LAUNCH_ID) == {NF_FILE: 120, "#excess": 3}
        drops = conn.execute(select(spool_drops.c.reason, spool_drops.c.count)).all()
    assert [tuple(d) for d in drops] == [("invalid", 4)]
    assert run_row(engine).state == "queued"  # drops alone do not start the run


def test_batch_of_another_run_refused(engine: Engine, writer: Writer) -> None:
    other = event(1, "onFlowCreate").model_copy(update={"run": "run_01K8T2F1XTVRES000000000001"})
    with pytest.raises(ValueError, match="another run or launch"):
        ingest_events(writer, other)
    assert run_row(engine).last_seq == 0


def test_unsafe_spool_is_counted_not_raised(tmp_path: Path, engine: Engine, writer: Writer) -> None:
    """read_spool raises on a non-private or swapped `.spectio` (Task 3); its caller must not."""
    launch_dir = spool_dir(tmp_path)
    (launch_dir / ".spectio").chmod(0o755)
    with pytest.raises(PermissionError):
        read_spool(launch_dir, RUN_ID, 1, {})
    batch = try_read_spool(launch_dir, RUN_ID, 1, {NF_FILE: 7})
    assert batch.events == [] and batch.cursor == {NF_FILE: 7}
    assert batch.drops == {"spool_refused": 1}
    (launch_dir / ".spectio").chmod(0o700)
    shutil.rmtree(launch_dir / ".spectio" / "events")
    (launch_dir / ".spectio" / "events").symlink_to(tmp_path)
    assert try_read_spool(launch_dir, RUN_ID, 1, {}).drops == {"spool_refused": 1}
    submit(writer, batch)
    with engine.connect() as conn:
        assert conn.execute(select(spool_drops.c.count)).scalar_one() == 1


# --- Lattice and attempts (api §7.2, §8.2) -------------------------------------------------


def test_attempt_states_only_move_forward(engine: Engine, writer: Writer) -> None:
    ingest_events(writer, task(1, "onTaskStart"))
    ingest_events(writer, task(2, "onTaskPending"), task(3, "onTaskSubmit"))  # late, lower rank
    assert attempt_states(engine) == [("ALIGN", "S01", 1, "running")]


def test_task_state_follows_its_last_attempt(engine: Engine, writer: Writer) -> None:
    fail: dict[str, Any] = {
        "status": "COMPLETED",
        "trace": {"status": "FAILED"},
        "errorAction": "RETRY",
    }
    ingest_events(writer, task(1, "onTaskComplete", **fail))
    ingest_events(writer, event(2, "onTaskStart", process="ALIGN", tag="S01", attempt=2))
    with engine.connect() as conn:
        assert conn.execute(select(tasks.c.state)).scalar_one() == "running"
    assert run_row(engine).task_counts == {"running": 1}


def test_ignored_failure(engine: Engine, writer: Writer) -> None:
    ignore: dict[str, Any] = {"trace": {"status": "FAILED", "exit": "3"}, "errorAction": "IGNORE"}
    ingest_events(writer, task(1, "onTaskComplete", **ignore))
    with engine.connect() as conn:
        row = conn.execute(select(attempts.c.state, attempts.c.ignored, attempts.c.exit)).one()
    assert tuple(row) == ("failed", True, 3)


def test_untagged_instances_of_one_process_are_distinct_tasks(
    engine: Engine, writer: Writer
) -> None:
    # Untagged instances are keyed on Nextflow's task `name` (CR-P3T04-02; inbox #77).
    done: dict[str, Any] = {"trace": {"status": "COMPLETED"}}
    ingest_events(
        writer,
        task(1, "onTaskStart", process="MERGE", tag=None, name="MERGE (1)"),
        task(2, "onTaskStart", process="MERGE", tag=None, name="MERGE (2)"),
        task(3, "onTaskComplete", process="MERGE", tag=None, name="MERGE (1)", **done),
        task(4, "onTaskComplete", process="MERGE", tag=None, name="MERGE (2)", **done),
    )
    with engine.connect() as conn:
        rows = conn.execute(select(tasks.c.name, tasks.c.tag, tasks.c.state)).all()
    assert sorted(tuple(r) for r in rows) == [
        ("MERGE (1)", None, "succeeded"),
        ("MERGE (2)", None, "succeeded"),
    ]
    assert run_row(engine).task_counts == {"succeeded": 2}


def test_req6_malformed_trace_exit_dropped(engine: Engine, writer: Writer) -> None:
    # A string `trace.exit` that is not a plain int64 is no exit code (SEC-P3T04-01).
    evs = [
        task(i, "onTaskComplete", tag=f"S{i}", trace={"status": "FAILED", "exit": raw})
        for i, raw in enumerate(["\u00b2", "--5", "9" * 30], start=1)
    ]
    ingest_events(writer, *evs, cursor={NF_FILE: 999})
    with engine.connect() as conn:
        assert load_cursor(conn, LAUNCH_ID) == {NF_FILE: 999}
        exits = conn.execute(select(attempts.c.state, attempts.c.exit)).all()
    assert [tuple(r) for r in exits] == [("failed", None)] * 3


def test_projection_error_drops_one_event_only(
    engine: Engine,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # One event whose projection raises is dropped and counted; the batch commits (§15.3 req. 6).
    real = nextflow_projector.project

    def project(p: Any, hook: str, data: Any) -> None:
        if getattr(data, "tag", None) == "BAD":
            raise OverflowError("boom")
        real(p, hook, data)

    monkeypatch.setattr(nextflow_projector, "project", project)
    with caplog.at_level(logging.ERROR, logger="spectio_server.projector.ingest"):
        ingest_events(
            writer,
            task(1, "onTaskStart", tag="BAD"),
            task(2, "onTaskStart", tag="S02"),
            cursor={NF_FILE: 999},
        )
    # The dropped event leaves a log line with its traceback (CR-P3T04-04).
    [record] = caplog.records
    assert record.getMessage() == f"event evt_x1 of {RUN_ID} not projected"
    assert record.exc_info is not None and record.exc_info[0] is OverflowError
    with engine.connect() as conn:
        assert load_cursor(conn, LAUNCH_ID) == {NF_FILE: 999}
        drops = conn.execute(select(spool_drops.c.reason, spool_drops.c.count)).all()
        logged = conn.execute(select(events.c.event_id)).scalars().all()
    assert [tuple(d) for d in drops] == [("projection_error", 1)]
    assert attempt_states(engine) == [("ALIGN", "S02", 1, "running")]
    assert "evt_x1" not in logged and "evt_x2" in logged
    run = run_row(engine)
    assert run.state == "running" and run.projected_seq == run.last_seq == len(logged)


def test_storage_error_rolls_back_the_batch(
    engine: Engine, writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A database fault is no projection error: the batch rolls back, the cursor stays
    # (CR-P3T04-04).
    real = nextflow_projector.project

    def project(p: Any, hook: str, data: Any) -> None:
        if getattr(data, "tag", None) == "BAD":
            raise OperationalError("UPDATE …", {}, Exception("disk I/O error"))
        real(p, hook, data)

    monkeypatch.setattr(nextflow_projector, "project", project)
    with pytest.raises(OperationalError):
        ingest_events(
            writer,
            task(1, "onTaskStart", tag="S01"),
            task(2, "onTaskStart", tag="BAD"),
            cursor={NF_FILE: 999},
        )
    with engine.connect() as conn:
        assert load_cursor(conn, LAUNCH_ID) == {}
        assert conn.execute(select(func.count()).select_from(events)).scalar_one() == 0
        assert conn.execute(select(func.count()).select_from(spool_drops)).scalar_one() == 0
    assert attempt_states(engine) == []


def test_attempt_key_is_unique(engine: Engine, writer: Writer) -> None:
    # api §8.2: one attempt per task, launch and attempt number (CR-P3T04-03).
    ingest_events(writer, task(1, "onTaskStart"))

    def duplicate(conn: Connection) -> None:
        row = conn.execute(select(attempts)).one()._asdict()
        conn.execute(insert(attempts).values({**row, "id": "att_dup"}))

    with pytest.raises(IntegrityError):
        writer.submit(duplicate).result()


def test_projector_queries_use_indexes(engine: Engine, writer: Writer) -> None:
    # No projector query scans the whole tasks or attempts table (CR-P3T04-03).
    seen: list[tuple[str, Any]] = []

    def record(conn: Any, cursor: Any, sql: str, params: Any, ctx: Any, many: bool) -> None:
        if not many and ("tasks" in sql or "attempts" in sql):
            seen.append((sql, params))

    sa_event.listen(engine, "before_cursor_execute", record)
    try:
        ingest_events(writer, task(1, "onTaskStart"), task(2, "onTaskStart", tag=None, name="M"))
        head(writer, report(state="exited", ended=True, failure=Failure("head_lost", "gone", None)))
        ingest_events(writer, event(3, "onFlowComplete", success=False))
    finally:
        sa_event.remove(engine, "before_cursor_execute", record)
    scans = []
    with engine.connect() as conn:
        for sql, params in seen:
            plan = conn.exec_driver_sql(f"EXPLAIN QUERY PLAN {sql}", params).all()
            scans += [(sql, row[-1]) for row in plan if row[-1] in ("SCAN tasks", "SCAN attempts")]
    assert seen and scans == []


def test_end_launch_syncs_only_the_tasks_it_changed(
    engine: Engine, writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    # CR-P3T04-03: closing a launch re-reads the state of the tasks it closed, not the run's.
    ingest_events(
        writer,
        task(1, "onTaskStart"),
        task(2, "onTaskComplete", tag="S02", trace={"status": "COMPLETED"}),
    )
    synced: list[list[str]] = []
    real = Projection.sync_tasks

    def spy(self: Projection, task_ids: Any) -> None:
        synced.append(sorted(task_ids))
        real(self, task_ids)

    monkeypatch.setattr(Projection, "sync_tasks", spy)
    head(writer, report(state="exited", ended=True, failure=Failure("head_lost", "gone", None)))
    with engine.connect() as conn:
        s01 = conn.execute(select(tasks.c.id).where(tasks.c.tag == "S01")).scalar_one()
    assert synced == [[s01]]
    assert run_row(engine).task_counts == {"failed": 1, "succeeded": 1}


def test_failure_without_terminate_is_engine_fault(engine: Engine, writer: Writer) -> None:
    ingest_events(writer, event(1, "onFlowComplete", success=False, errorMessage="boom"))
    run = run_row(engine)
    assert run.state == "failed"
    assert run.failure == {
        "class": "engine_fault",
        "message": "boom",
        "task_id": None,
        "attempt_n": None,
    }


def test_first_terminate_in_a_batch_is_the_culprit(
    engine: Engine, writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ids that sort backwards, so a tie on created_at cannot fall back on id order (CR-P3T04-07).
    countdown = iter(range(999, 0, -1))
    monkeypatch.setattr(nextflow_projector, "new_id", lambda prefix: f"{prefix}_{next(countdown)}")
    fail: dict[str, Any] = {"trace": {"status": "FAILED"}, "errorAction": "TERMINATE"}
    ingest_events(
        writer,
        task(1, "onTaskComplete", tag="S01", **fail),
        task(2, "onTaskComplete", tag="S02", **fail),
        event(3, "onFlowComplete", success=False, errorMessage="boom"),
    )
    with engine.connect() as conn:
        first = conn.execute(select(tasks.c.id).where(tasks.c.tag == "S01")).scalar_one()
        classes = conn.execute(select(attempts.c.failure_class)).scalars().all()
    assert run_row(engine).failure["task_id"] == first
    assert classes == ["tool_error", "tool_error"]  # each attempt is classified (CR-P3T04-08)


# --- Head reports and cancel (api §7.1, P1 Assumption 15) ----------------------------------


def report(**kw: Any) -> HeadReport:
    base: dict[str, Any] = {
        "state": "running",
        "native_id": "4242",
        "node": "login1",
        "exit_code": None,
        "ended": False,
        "failure": None,
    }
    return HeadReport(**{**base, **kw})


def head(writer: Writer, r: HeadReport) -> None:
    writer.submit(lambda conn: apply_head_report(conn, LAUNCH_ID, r)).result()


def set_state(writer: Writer, state: str) -> None:
    writer.submit(
        lambda conn: conn.execute(update(runs).where(runs.c.id == RUN_ID).values(state=state))
    ).result()


def test_head_running_starts_the_run(engine: Engine, writer: Writer) -> None:
    head(writer, report())
    assert run_row(engine).state == "running"
    with engine.connect() as conn:
        launch = conn.execute(select(launches).where(launches.c.id == LAUNCH_ID)).one()
    assert (launch.head_native_id, launch.head_state) == ("4242", "running")


def test_launch_failure_fails_a_queued_run(engine: Engine, writer: Writer) -> None:
    failure = Failure("engine_missing", "nextflow not found on PATH", None)
    head(writer, report(state="exited", ended=True, exit_code=127, failure=failure))
    run = run_row(engine)
    assert run.state == "failed"
    assert run.failure == {
        "class": "engine_missing",
        "message": "nextflow not found on PATH",
        "task_id": None,
        "attempt_n": None,
    }
    assert run.ended_at is not None
    assert [c["to"] for c in state_changes(engine)] == ["failed"]
    with engine.connect() as conn:
        launch = conn.execute(select(launches).where(launches.c.id == LAUNCH_ID)).one()
    assert launch.exit_code == 127 and launch.exited_at is not None


def test_head_lost_fails_open_attempts(engine: Engine, writer: Writer) -> None:
    ingest_events(
        writer,
        task(1, "onTaskStart"),
        task(2, "onTaskComplete", tag="S02", trace={"status": "COMPLETED"}),
    )
    head(writer, report(state="exited", ended=True, failure=Failure("head_lost", "gone", None)))
    run = run_row(engine)
    assert (run.state, run.failure["class"]) == ("failed", "head_lost")
    with engine.connect() as conn:
        rows = conn.execute(
            select(tasks.c.tag, attempts.c.state, attempts.c.failure_class).join(
                attempts, attempts.c.task_id == tasks.c.id
            )
        ).all()
    assert sorted(tuple(r) for r in rows) == [
        ("S01", "failed", "head_lost"),
        ("S02", "succeeded", None),
    ]


def test_cancelling_ends_cancelled_whatever_the_engine_says(engine: Engine, writer: Writer) -> None:
    ingest_events(writer, task(1, "onTaskStart"))
    set_state(writer, "cancelling")
    ingest_events(writer, event(2, "onFlowComplete", success=True))
    run = run_row(engine)
    assert run.state == "cancelled" and run.failure is None
    assert attempt_states(engine) == [("ALIGN", "S01", 1, "aborted")]


def test_cancelling_ends_when_the_head_ends(engine: Engine, writer: Writer) -> None:
    ingest_events(writer, task(1, "onTaskStart"))
    set_state(writer, "cancelling")
    head(writer, report(state="exited", ended=True, exit_code=130))
    assert run_row(engine).state == "cancelled"
    assert attempt_states(engine) == [("ALIGN", "S01", 1, "aborted")]


def test_head_report_after_the_end_changes_no_state(engine: Engine, writer: Writer) -> None:
    ingest_events(writer, event(1, "onFlowComplete", success=True))
    head(
        writer,
        report(
            state="exited", ended=True, exit_code=0, failure=Failure("engine_fault", "late", None)
        ),
    )
    run = run_row(engine)
    assert (run.state, run.failure) == ("succeeded", None)
    with engine.connect() as conn:
        launch = conn.execute(select(launches).where(launches.c.id == LAUNCH_ID)).one()
    assert launch.head_state == "succeeded"  # the engine's end is kept
    assert launch.exit_code == 0


def test_head_end_before_flow_complete_still_succeeds(engine: Engine, writer: Writer) -> None:
    # The head report can land before the engine's onFlowComplete (CR-P3T04-01).
    ingest_events(writer, task(1, "onTaskStart"))
    head(writer, report(state="exited", ended=True, exit_code=0))
    ingest_events(writer, event(2, "onFlowComplete", success=True))
    assert run_row(engine).state == "succeeded"


def test_exited_at_is_set_once(engine: Engine, writer: Writer) -> None:
    def exited_at() -> Any:
        with engine.connect() as conn:
            return conn.execute(
                select(launches.c.exited_at).where(launches.c.id == LAUNCH_ID)
            ).scalar_one()

    head(writer, report(state="exited", ended=True, exit_code=0))
    first = exited_at()
    head(writer, report(state="exited", ended=True, exit_code=0))
    assert exited_at() == first
