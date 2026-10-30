"""The Snakemake mapping: api §7.2 and P1 Assumption 16 (P1 Task 5).

The T2 fixtures are read through the real spool reader (Task 3), as the runner reads them, then
ingested through the one writer (Task 2). A Snakemake launch ends on its head's exit code, which a
head report carries (P1 Assumption 16).
"""

import json
import shutil
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, insert, select, update
from sqlalchemy import event as sa_event

from spectio.runner.spool import read_spool
from spectio.runner.types import HeadReport, SpoolBatch
from spectio_sdk.events import SpoolEvent
from spectio_server.projector.ingest import apply_head_report, ingest
from spectio_server.store.db import open_db
from spectio_server.store.schema import (
    attempts,
    environments,
    launches,
    projects,
    runs,
    tasks,
    workflow_versions,
    workflows,
)
from spectio_server.store.writer import Writer

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "engine-events"
RUN_ID = "run_01K8T2F1XTVRES000000000000"  # the run of every converted T2 fixture
LAUNCH_ID = "lch_1"
SMK_FILE = "snakemake-logger-spectio-1-0001.jsonl"
NOW = datetime(2026, 10, 30, tzinfo=UTC)
FLAKY = "snakemake-9.27.1_checkpoint_flaky_retry.spool.jsonl"
TOOLERR = "snakemake-9.27.1_tool_error.spool.jsonl"


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
            id="wfl_1",
            project_id="prj_1",
            source="local",
            location="/w",
            engine="snakemake",
            created_at=NOW,
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


def replay(tmp_path: Path, writer: Writer, fixture: str) -> None:
    """The fixture as the runner reads it, every batch until the spool is drained."""
    launch_dir = tmp_path / "launch"
    (launch_dir / ".spectio" / "events").mkdir(mode=0o700, parents=True)
    (launch_dir / ".spectio").chmod(0o700)
    target = launch_dir / ".spectio" / "events" / SMK_FILE
    shutil.copyfile(FIXTURES / fixture, target)
    target.chmod(0o600)
    cursor: dict[str, int] = {}
    while (batch := read_spool(launch_dir, RUN_ID, 1, cursor, max_lines=100)).events:
        submit(writer, batch)
        cursor = batch.cursor


def submit(writer: Writer, batch: SpoolBatch) -> None:
    writer.submit(lambda conn: ingest(conn, LAUNCH_ID, batch)).result()


def ingest_events(writer: Writer, *evs: SpoolEvent) -> None:
    submit(writer, SpoolBatch(list(evs), {}, Counter()))


def event(n: int, type_: str, time: str = "2026-10-28T07:30:00Z", **data: Any) -> SpoolEvent:
    return SpoolEvent.model_validate(
        {
            "v": 1,
            "id": f"evt_s{n}",
            "run": RUN_ID,
            "launch": 1,
            "producer": "snakemake-logger-spectio/0.0.1",
            "seq": 10_000 + n,
            "time": time,
            "type": f"snakemake.{type_}",
            "data": data,
        }
    )


def job_info(n: int, jobid: int, rule: str = "align", **wildcards: str) -> SpoolEvent:
    return event(n, "job_info", jobid=jobid, rule_name=rule, wildcards=wildcards)


def exited(code: int) -> HeadReport:
    return HeadReport(
        state="exited", native_id="4242", node="login1", exit_code=code, ended=True, failure=None
    )


def head(writer: Writer, r: HeadReport) -> None:
    writer.submit(lambda conn: apply_head_report(conn, LAUNCH_ID, r)).result()


def run_row(engine: Engine) -> Any:
    with engine.connect() as conn:
        return conn.execute(select(runs).where(runs.c.id == RUN_ID)).one()


def attempt_rows(engine: Engine) -> list[tuple[str, str | None, int, str]]:
    """(rule, tag, attempt n, state) of every attempt, by task then attempt."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(tasks.c.process_or_rule, tasks.c.tag, attempts.c.n, attempts.c.state)
            .join(attempts, attempts.c.task_id == tasks.c.id)
            .order_by(tasks.c.process_or_rule, tasks.c.tag, attempts.c.n)
        ).all()
    return [tuple(r) for r in rows]


def fixture_time(fixture: str, type_: str, last: bool = False) -> datetime:
    lines = [json.loads(line) for line in (FIXTURES / fixture).read_text().splitlines()]
    times = [e["time"] for e in lines if type_ in ("*", e["type"])]
    return datetime.fromisoformat(times[-1] if last else times[0])


# --- The T2 fixtures (P1 Task 5, Step 1) ---------------------------------------------------


def test_checkpoint_flaky_retry(tmp_path: Path, engine: Engine, writer: Writer) -> None:
    replay(tmp_path, writer, FLAKY)
    rows = attempt_rows(engine)
    assert not [r for r in rows if r[3] in ("pending", "submitted", "running")]  # none left open
    assert len(rows) == 69 and Counter(r[3] for r in rows) == {"succeeded": 67, "failed": 2}
    retried = [r for r in rows if r[2] == 2]
    assert sorted((rule, tag) for rule, tag, _, _ in retried) == [
        ("align", "i=0000, sample=S07"),
        ("align", "i=0001, sample=S07"),
    ]
    for rule, tag, _, _ in retried:  # a failed attempt 1, then a succeeded attempt 2
        assert [(n, s) for r, t, n, s in rows if (r, t) == (rule, tag)] == [
            (1, "failed"),
            (2, "succeeded"),
        ]
    run = run_row(engine)
    assert run.tasks_expected == 67  # the last progress.total
    assert run.task_counts == {"succeeded": 67}
    assert run.engine_version == "9.27.1"
    head(writer, exited(0))
    assert run_row(engine).state == "succeeded"


def test_tool_error(tmp_path: Path, engine: Engine, writer: Writer) -> None:
    replay(tmp_path, writer, TOOLERR)
    assert run_row(engine).state == "running"  # no engine event ends a Snakemake launch
    head(writer, exited(1))
    run = run_row(engine)
    assert run.state == "failed"
    assert run.failure["class"] == "tool_error"
    assert run.failure["message"] == (
        "WorkflowError:\nAt least one job did not complete successfully."
    )  # the last error record
    with engine.connect() as conn:
        culprit = conn.execute(
            select(tasks.c.id).where(
                tasks.c.process_or_rule == "compare", tasks.c.tag == "group=treatA"
            )
        ).scalar_one()
        classes = conn.execute(
            select(attempts.c.n, attempts.c.state, attempts.c.failure_class)
            .where(attempts.c.task_id == culprit)
            .order_by(attempts.c.n)
        ).all()
    assert (run.failure["task_id"], run.failure["attempt_n"]) == (culprit, 3)
    assert [tuple(c) for c in classes] == [
        (1, "failed", None),
        (2, "failed", None),
        (3, "failed", "tool_error"),
    ]


def test_success_needs_head_exit_zero(tmp_path: Path, engine: Engine, writer: Writer) -> None:
    replay(tmp_path, writer, "snakemake-9.27.1_tool_error_rerun.spool.jsonl")
    assert run_row(engine).state == "running"  # every job finished, no head report yet
    head(writer, exited(0))
    run = run_row(engine)
    assert (run.state, run.failure) == ("succeeded", None)


def test_untyped_records_ignored(tmp_path: Path, engine: Engine, writer: Writer) -> None:
    # The 122 records without "event" are `snakemake.log`: they change no task and no attempt.
    lines = (FIXTURES / FLAKY).read_text().splitlines()
    logs = [SpoolEvent.model_validate_json(x) for x in lines if '"snakemake.log"' in x]
    assert len(logs) == 122
    ingest_events(writer, *logs)
    run = run_row(engine)
    assert (run.state, run.task_counts, run.tasks_expected) == ("running", {}, None)
    assert attempt_rows(engine) == []


# --- Run times from the engine (inbox #79, FU-P3-04) ---------------------------------------


def test_run_times_come_from_the_engine(tmp_path: Path, engine: Engine, writer: Writer) -> None:
    replay(tmp_path, writer, FLAKY)
    head(writer, exited(0))
    run = run_row(engine)
    assert run.started_at == fixture_time(FLAKY, "snakemake.workflow_started")
    assert run.ended_at == fixture_time(FLAKY, "*", last=True)  # the last record, not the clock


def test_start_from_a_head_report_is_replaced_by_the_engine_time(
    engine: Engine, writer: Writer
) -> None:
    running = HeadReport(
        state="running", native_id="1", node="n", exit_code=None, ended=False, failure=None
    )
    head(writer, running)
    ingest_events(writer, event(1, "workflow_started", time="2026-10-28T07:00:01Z"))
    assert run_row(engine).started_at == datetime(2026, 10, 28, 7, 0, 1, tzinfo=UTC)


# --- The mapping (P1 Assumption 16) --------------------------------------------------------


def test_job_started_before_job_info_gives_one_running_attempt(
    engine: Engine, writer: Writer
) -> None:
    # Snakemake logs JOB_STARTED, then JOB_INFO as each job runs.
    ingest_events(writer, event(1, "job_started", jobs=[7, 8]), job_info(2, 7, sample="S1"))
    ingest_events(writer, job_info(3, 8, rule="merge"))
    assert attempt_rows(engine) == [
        ("align", "sample=S1", 1, "running"),
        ("merge", None, 1, "running"),
    ]


def test_wildcards_sorted_into_the_tag(engine: Engine, writer: Writer) -> None:
    ingest_events(writer, job_info(1, 7, sample="S07", i="0001"))
    assert attempt_rows(engine) == [("align", "i=0001, sample=S07", 1, "running")]


def test_retry_opens_the_next_attempt(engine: Engine, writer: Writer) -> None:
    ingest_events(
        writer,
        job_info(1, 7, sample="S1"),
        event(2, "job_error", jobid=7, rule_name="align"),
        event(3, "job_started", jobs=[7]),
        job_info(4, 7, sample="S1"),
        event(5, "job_finished", job_id=7),
    )
    assert attempt_rows(engine) == [
        ("align", "sample=S1", 1, "failed"),
        ("align", "sample=S1", 2, "succeeded"),
    ]


def test_unknown_jobid_is_logged_only(engine: Engine, writer: Writer) -> None:
    ingest_events(
        writer,
        event(1, "job_finished", job_id=99),
        event(2, "job_error", jobid=98, rule_name="align"),
    )
    assert attempt_rows(engine) == []
    assert run_row(engine).last_seq == 3  # both logged, and the run started


def test_late_job_event_after_the_end_is_logged_only(engine: Engine, writer: Writer) -> None:
    ingest_events(writer, job_info(1, 7, sample="S1"), event(2, "job_finished", job_id=7))
    head(writer, exited(0))
    ingest_events(writer, job_info(3, 8, sample="S2"))
    assert attempt_rows(engine) == [("align", "sample=S1", 1, "succeeded")]
    assert run_row(engine).state == "succeeded"


def test_head_exit_aborts_open_attempts(engine: Engine, writer: Writer) -> None:
    ingest_events(writer, job_info(1, 7, sample="S1"))
    head(writer, exited(1))
    run = run_row(engine)
    assert attempt_rows(engine) == [("align", "sample=S1", 1, "aborted")]
    assert run.failure == {
        "class": "engine_fault",  # no job failed
        "message": "snakemake exited with code 1",  # no error record
        "task_id": None,
        "attempt_n": None,
    }


def test_retried_culprit_is_not_blamed(engine: Engine, writer: Writer) -> None:
    # The last failed job was retried and succeeded: the run's failure names no task.
    ingest_events(
        writer,
        job_info(1, 7, sample="S1"),
        event(2, "job_error", jobid=7, rule_name="align"),
        job_info(3, 7, sample="S1"),
        event(4, "job_finished", job_id=7),
        event(5, "error", msg="WorkflowError:\nboom", exception="WorkflowError"),
    )
    head(writer, exited(1))
    assert run_row(engine).failure == {
        "class": "engine_fault",
        "message": "WorkflowError:\nboom",
        "task_id": None,
        "attempt_n": None,
    }


def test_cancelling_ends_cancelled_on_head_exit(engine: Engine, writer: Writer) -> None:
    ingest_events(writer, job_info(1, 7, sample="S1"))
    writer.submit(
        lambda conn: conn.execute(
            update(runs).where(runs.c.id == RUN_ID).values(state="cancelling")
        )
    ).result()
    head(writer, exited(1))
    assert run_row(engine).state == "cancelled"
    assert attempt_rows(engine) == [("align", "sample=S1", 1, "aborted")]


def test_exit_zero_without_events_succeeds(engine: Engine, writer: Writer) -> None:
    head(writer, exited(0))  # "Nothing to be done" can come with no job at all
    assert run_row(engine).state == "succeeded"


# --- Security (SEC-P3T1-08, SEC-P3T1-11) ---------------------------------------------------


def test_failure_message_hides_a_quoted_command(engine: Engine, writer: Writer) -> None:
    msg = (
        'RuleException:\nCalledProcessError in file "Snakefile", line 9:\n'
        "Command 'set -euo pipefail; export TOKEN=s3cret; run' returned non-zero exit status 1."
    )
    ingest_events(
        writer,
        job_info(1, 7, sample="S1"),
        event(2, "error", msg=msg, exception="RuleException"),
        event(3, "job_error", jobid=7, rule_name="align"),
    )
    head(writer, exited(1))
    failure = run_row(engine).failure
    assert failure["class"] == "tool_error"
    assert "s3cret" not in failure["message"]
    assert failure["message"].endswith("Command «hidden» returned non-zero exit status 1.")


def test_snakemake_queries_use_indexes(engine: Engine, writer: Writer) -> None:
    seen: list[tuple[str, Any]] = []

    def record(conn: Any, cursor: Any, sql: str, params: Any, ctx: Any, many: bool) -> None:
        if not many and any(t in sql for t in ("tasks", "attempts", "snakemake_jobs", "events")):
            seen.append((sql, params))

    sa_event.listen(engine, "before_cursor_execute", record)
    try:
        ingest_events(
            writer,
            event(1, "job_started", jobs=[7]),
            job_info(2, 7, sample="S1"),
            event(3, "job_error", jobid=7, rule_name="align"),
            job_info(4, 7, sample="S1"),
            event(5, "job_finished", job_id=7),
            event(6, "error", msg="boom"),
        )
        head(writer, exited(1))
    finally:
        sa_event.remove(engine, "before_cursor_execute", record)
    scans = []
    with engine.connect() as conn:
        for sql, params in seen:
            plan = conn.exec_driver_sql(f"EXPLAIN QUERY PLAN {sql}", params).all()
            scans += [(sql, row[-1]) for row in plan if row[-1].startswith("SCAN ")]
    assert seen and scans == []
