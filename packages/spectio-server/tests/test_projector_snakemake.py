"""The Snakemake mapping: api §7.2 and P1 Assumption 16 (P1 Task 5).

The T2 fixtures are read through the real spool reader (Task 3), as the runner reads them, then
ingested through the one writer (Task 2). A Snakemake launch ends on its head's exit code, which a
head report carries (P1 Assumption 16).
"""

import json
import shutil
from collections import Counter
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, insert, select, update
from sqlalchemy import event as sa_event

from spectio.environments import Environment, run_column, snapshot
from spectio.runner.spool import read_spool
from spectio.runner.types import Failure, HeadReport, SpoolBatch
from spectio_sdk.events import DATA_MODELS, SnakemakeJobInfo, SpoolEvent, parse_data
from spectio_server.projector.ingest import _own_message, apply_head_report, ingest
from spectio_server.projector.runs import MAX_FAILURE_MESSAGE
from spectio_server.stall import _now_running, _submit_advance
from spectio_server.store.db import open_db
from spectio_server.store.schema import (
    attempts,
    environments,
    launches,
    projects,
    run_processes,
    run_stages,
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
TOOLERR_RERUN = "snakemake-9.27.1_tool_error_rerun.spool.jsonl"


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


def submit(writer: Writer, batch: SpoolBatch, watched: bool = True) -> None:
    """`watched`: the server reads `squeue` (the stall watch is on), as `serve` sets it when
    `[slurm] squeue` is configured (#385)."""
    writer.submit(lambda conn: ingest(conn, LAUNCH_ID, batch, queue_watched=watched)).result()


def ingest_events(writer: Writer, *evs: SpoolEvent, watched: bool = True) -> None:
    submit(writer, SpoolBatch(list(evs), {}, Counter()), watched)


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


def test_a_later_launch_keeps_the_first_start(engine: Engine, writer: Writer) -> None:
    # api §7: started_at is the first queued -> running; the duration covers all launches.
    ingest_events(writer, event(1, "workflow_started", time="2026-10-28T07:00:01Z"))
    writer.submit(
        lambda conn: conn.execute(
            insert(launches).values(id="lch_2", run_id=RUN_ID, n=2, created_at=NOW)
        )
    ).result()
    second = event(2, "workflow_started", time="2026-10-28T09:00:00Z").model_copy(
        update={"launch": 2, "id": "evt_s2b"}
    )
    writer.submit(lambda conn: ingest(conn, "lch_2", SpoolBatch([second], {}, Counter()))).result()
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


@pytest.mark.parametrize("class_", ["engine_fault", "head_lost"])
def test_exit_code_wins_over_a_head_failure(engine: Engine, writer: Writer, class_: str) -> None:
    # A runner that sets `failure` because no terminal engine event came (CR-P3T05-01).
    report = replace(exited(0), failure=Failure(class_, "no terminal engine event"))
    head(writer, report)
    assert (run_row(engine).state, run_row(engine).failure) == ("succeeded", None)


def test_exit_code_with_a_head_failure_keeps_the_tool_error(
    tmp_path: Path, engine: Engine, writer: Writer
) -> None:
    replay(tmp_path, writer, TOOLERR)
    head(writer, replace(exited(1), failure=Failure("engine_fault", "no terminal engine event")))
    assert run_row(engine).failure["class"] == "tool_error"


def test_launch_error_with_an_exit_code_still_fails(engine: Engine, writer: Writer) -> None:
    head(writer, replace(exited(0), failure=Failure("engine_missing", "snakemake not found")))
    run = run_row(engine)
    assert (run.state, run.failure["class"]) == ("failed", "engine_missing")


TAIL = (
    "Snakemake exited with code 1 before any job failed. Its last lines:\n"
    "Building DAG of jobs...\nApptainerError: image /shared/containers/align.sif not found"
)


def test_a_failure_before_any_job_quotes_the_head_report(engine: Engine, writer: Writer) -> None:
    """A Snakemake head that exits non-zero with no error record and no failed job (an
    Apptainer or config error at startup) fails `engine_fault` with the head report's own
    message — the end of its output, as Nextflow's (#352, #368): the run says why."""
    head(writer, replace(exited(1), failure=Failure("engine_fault", TAIL)))
    assert run_row(engine).failure == {
        "class": "engine_fault",
        "message": TAIL,
        "task_id": None,
        "attempt_n": None,
    }


def test_a_failed_job_keeps_its_message_with_a_head_report_tail(
    engine: Engine, writer: Writer
) -> None:
    """The run keeps blaming the launch's last failed job (#352): a head report's own lines are
    quoted only when no job failed, so this one keeps today's message."""
    ingest_events(
        writer,
        job_info(1, 7, sample="S1"),
        event(2, "job_error", jobid=7, rule_name="align"),
    )
    head(writer, replace(exited(1), failure=Failure("engine_fault", TAIL)))
    failure = run_row(engine).failure
    assert (failure["class"], failure["message"]) == ("tool_error", "snakemake exited with code 1")
    assert failure["task_id"] is not None and failure["attempt_n"] == 1


def test_an_error_record_beats_the_head_report(engine: Engine, writer: Writer) -> None:
    ingest_events(writer, event(1, "error", msg="WorkflowError:\nboom", exception="WorkflowError"))
    head(writer, replace(exited(1), failure=Failure("engine_fault", TAIL)))
    assert run_row(engine).failure["message"] == "WorkflowError:\nboom"


def test_a_retried_job_gets_no_head_tail(engine: Engine, writer: Writer) -> None:
    """A job that failed and was retried still failed: "before any job failed" would be untrue,
    so the run's failure quotes no tail (CR-SMKFAIL-01)."""
    ingest_events(
        writer,
        job_info(1, 7, sample="S1"),
        event(2, "job_error", jobid=7, rule_name="align"),
        job_info(3, 7, sample="S1"),
        event(4, "job_finished", job_id=7),
    )
    head(writer, replace(exited(1), failure=Failure("engine_fault", TAIL)))
    assert run_row(engine).failure["message"] == "snakemake exited with code 1"


def test_a_cancelling_run_with_a_head_tail_still_ends_cancelled(
    engine: Engine, writer: Writer
) -> None:
    ingest_events(writer, job_info(1, 7, sample="S1"))
    writer.submit(
        lambda conn: conn.execute(
            update(runs).where(runs.c.id == RUN_ID).values(state="cancelling")
        )
    ).result()
    head(writer, replace(exited(1), failure=Failure("engine_fault", TAIL)))
    row = run_row(engine)
    assert (row.state, row.failure) == ("cancelled", None)


def test_own_message_strips_escapes_and_caps() -> None:
    long = "Snakemake exited with code 1.\x1b[31m red\x1b[0m\a " + "x" * MAX_FAILURE_MESSAGE
    got = _own_message(replace(exited(1), failure=Failure("engine_fault", long)))
    assert got is not None and "\x1b" not in got and "\a" not in got
    assert got.startswith("Snakemake exited with code 1. red") and len(got) == MAX_FAILURE_MESSAGE
    assert _own_message(replace(exited(1), failure=Failure("head_lost", "x"))) is None
    assert _own_message(exited(1)) is None


def test_own_message_never_returns_the_command(engine: Engine, writer: Writer) -> None:
    """A runner that forgets to hide the commands cannot leak them (SEC-SMKFAIL-03)."""
    quoted = (
        "Snakemake exited with code 1 before any job failed. Its last lines:\n"
        "CalledProcessError in file /x/Snakefile, line 3:\n"
        "Command 'export TOKEN=s3cret; tool --in a' returned non-zero exit status 1.\n"
        "Error in rule map:\n    shell:\n        export TOKEN=s3cret2\n    jobid: 2"
    )
    report = replace(exited(1), failure=Failure("engine_fault", quoted))
    got = _own_message(report)
    assert got is not None and "s3cret" not in got and "tool --in" not in got
    assert "CalledProcessError in file /x/Snakefile, line 3:" in got
    unclosed = replace(exited(1), failure=Failure("engine_fault", "x\nCommand 'export T=s3cret"))
    assert "s3cret" not in (_own_message(unclosed) or "")
    head(writer, report)
    assert "s3cret" not in run_row(engine).failure["message"]


# --- The queue (#385, 2026-11-25): a SLURM job PENDING in squeue is `submitted` ------------


def set_environment(writer: Writer, env: dict[str, Any]) -> None:
    """`runs.environment`, as a launch writes it: the run's own executor decides."""
    writer.submit(
        lambda conn: conn.execute(update(runs).where(runs.c.id == RUN_ID).values(environment=env))
    ).result()


def slurm_column() -> dict[str, Any]:
    return run_column(snapshot(Environment(name="slurm", label="SLURM", executor="slurm")))


def test_a_slurm_run_opens_the_attempt_submitted(engine: Engine, writer: Writer) -> None:
    """A job the SLURM executor holds in its queue is not running: the attempt opens
    `submitted`, and its end moves it forward as before."""
    set_environment(writer, slurm_column())
    ingest_events(writer, job_info(1, 7, sample="S1"))
    assert attempt_rows(engine) == [("align", "sample=S1", 1, "submitted")]
    assert run_row(engine).task_counts == {"submitted": 1}
    ingest_events(writer, event(2, "job_finished", job_id=7))
    assert attempt_rows(engine) == [("align", "sample=S1", 1, "succeeded")]
    assert run_row(engine).task_counts == {"succeeded": 1}


def test_a_slurm_run_without_the_squeue_watch_opens_running(engine: Engine, writer: Writer) -> None:
    """With no `squeue` configured nothing would move a queued attempt, so it would read
    queued for the whole run: it opens `running`, as before #385."""
    set_environment(writer, slurm_column())
    ingest_events(writer, job_info(1, 7, sample="S1"), watched=False)
    assert attempt_rows(engine) == [("align", "sample=S1", 1, "running")]
    assert run_row(engine).task_counts == {"running": 1}


def test_a_local_run_opens_the_attempt_running(engine: Engine, writer: Writer) -> None:
    """A local executor runs a job at once: today's behaviour, environment or not."""
    set_environment(
        writer,
        run_column(snapshot(Environment(name="local", label="This machine", executor="local"))),
    )
    ingest_events(writer, job_info(1, 7, sample="S1"))
    assert attempt_rows(engine) == [("align", "sample=S1", 1, "running")]
    set_environment(writer, run_column(snapshot(Environment(name="slurm", executor="slurm"))))
    ingest_events(writer, job_info(2, 8, rule="merge"))
    assert attempt_rows(engine) == [
        ("align", "sample=S1", 1, "running"),
        ("merge", None, 1, "submitted"),
    ]


def test_a_localrule_job_on_slurm_runs_at_once(engine: Engine, writer: Writer) -> None:
    """A `localrule` job (`job_info.local`) never reaches SLURM's queue: `running`."""
    set_environment(writer, slurm_column())
    ingest_events(writer, event(1, "job_info", jobid=7, rule_name="all", wildcards={}, local=True))
    assert attempt_rows(engine) == [("all", None, 1, "running")]


def test_a_slurm_retry_opens_submitted_too(engine: Engine, writer: Writer) -> None:
    """A retried job queues again: its attempt 2 opens `submitted` as well."""
    set_environment(writer, slurm_column())
    ingest_events(
        writer,
        job_info(1, 7, sample="S1"),
        event(2, "job_error", jobid=7, rule_name="align"),
        job_info(3, 7, sample="S1"),
        event(4, "job_finished", job_id=7),
    )
    assert attempt_rows(engine) == [
        ("align", "sample=S1", 1, "failed"),
        ("align", "sample=S1", 2, "succeeded"),
    ]


def test_the_stall_poller_moves_a_submitted_attempt_to_running(
    engine: Engine, writer: Writer
) -> None:
    """squeue says the job runs now: the poller's write moves the `submitted` attempt to
    `running`, its task and the run's counts with it, and never an attempt that ended."""
    set_environment(writer, slurm_column())
    ingest_events(
        writer,
        job_info(1, 7, sample="S1"),
        event(2, "slurm_submitted", jobid=7, external_jobid="4242"),
        job_info(3, 8, rule="merge"),
        event(4, "slurm_submitted", jobid=8, external_jobid="4243"),
        event(5, "job_finished", job_id=8),
    )
    assert run_row(engine).task_counts == {"submitted": 1, "succeeded": 1}
    writer.submit(lambda conn: _now_running(conn, RUN_ID, {"4242", "4243"})).result()
    assert attempt_rows(engine) == [
        ("align", "sample=S1", 1, "running"),
        ("merge", None, 1, "succeeded"),  # ended: never moved again
    ]
    run = run_row(engine)
    assert run.task_counts == {"running": 1, "succeeded": 1}
    writer.submit(lambda conn: _now_running(conn, RUN_ID, {"4242", "4243"})).result()  # idempotent
    assert run_row(engine).task_counts == {"running": 1, "succeeded": 1}


def test_the_poller_hands_its_move_to_the_writer(engine: Engine, writer: Writer) -> None:
    """`_submit_advance` (the watch's `advance`) queues the write on the writer thread: the
    accounting thread never holds a connection."""
    set_environment(writer, slurm_column())
    ingest_events(
        writer,
        job_info(1, 7, sample="S1"),
        event(2, "slurm_submitted", jobid=7, external_jobid="4242"),
    )
    _submit_advance(writer.submit, RUN_ID, ["4242"])
    writer.submit(lambda conn: None).result()  # the writer runs its jobs in order
    assert attempt_rows(engine) == [("align", "sample=S1", 1, "running")]


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


@pytest.mark.parametrize("fixture", [FLAKY, TOOLERR, TOOLERR_RERUN])
def test_no_parsed_record_holds_the_fixture_shell_text(fixture: str) -> None:
    # SEC-P3T1-08: every free-text field the allow-list keeps (error.msg, job_info.reason) is
    # checked on real records; log and job_error `msg` are not in the allow-list.
    kept = []
    for line in (FIXTURES / fixture).read_text().splitlines():
        ev = SpoolEvent.model_validate(json.loads(line))
        if ev.type in DATA_MODELS:
            kept.append(json.dumps(parse_data(ev).model_dump(mode="json")))
    assert kept
    assert not [k for k in kept if "synth.py" in k or "SPECTIO_ATTEMPT" in k]


def test_params_changed_reason_keeps_the_label_only() -> None:
    reason = (
        "Missing output files: a.tsv; Params have changed since last execution: "
        "before: 'export TOKEN=s3cret; run' now: 'true' "
    )
    info = SnakemakeJobInfo.model_validate({"jobid": 1, "rule_name": "r", "reason": reason})
    assert info.reason == "Missing output files: a.tsv; Params have changed since last execution"


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


def test_the_poller_moves_the_stage_with_its_task(engine: Engine, writer: Writer) -> None:
    """A rule mapped to a stage: the stage reads `not_started` while its job is queued, and
    `running` (counts and start time) once the poller's write moves it (ui-spec §5.1.1)."""

    def map_rule(conn: Connection) -> None:
        conn.execute(
            insert(run_stages).values(
                id="stg_1",
                created_at=NOW,
                run_id=RUN_ID,
                stage_id="align",
                position=1,
                source="detected",
                state="not_started",
            )
        )
        conn.execute(
            insert(run_processes).values(
                id="prc_1",
                created_at=NOW,
                run_id=RUN_ID,
                name="align",
                position=1,
                stage_id="align",
                jobs_planned=1,
            )
        )

    writer.submit(map_rule).result()
    set_environment(writer, slurm_column())
    ingest_events(
        writer,
        job_info(1, 7, sample="S1"),
        event(2, "slurm_submitted", jobid=7, external_jobid="4242"),
    )

    def stage(conn: Connection) -> Any:
        return conn.execute(select(run_stages).where(run_stages.c.id == "stg_1")).one()

    with engine.connect() as conn:
        queued = stage(conn)
    assert (queued.state, queued.task_counts, queued.started_at) == (
        "not_started",
        {"submitted": 1},
        None,
    )
    writer.submit(lambda conn: _now_running(conn, RUN_ID, {"4242"})).result()
    with engine.connect() as conn:
        moved = stage(conn)
    assert (moved.state, moved.task_counts) == ("running", {"running": 1})
    assert moved.started_at is not None
