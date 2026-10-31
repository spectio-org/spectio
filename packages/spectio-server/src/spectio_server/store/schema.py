"""The 0.0.1 tables of api-and-data-model.md §7, as SQLAlchemy Core metadata.

Portable across SQLite and Postgres: text primary keys (prefixed ULIDs), UTC timestamps, JSON
through the ORM type, CHECK constraints instead of enums. Each table keeps only the columns of
api §7 that P1 uses; later tasks add the others by migration.
"""

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Dialect,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

Json = JSON().with_variant(JSONB(), "postgresql")  # TEXT with JSON1 on SQLite


class UTCDateTime(TypeDecorator[datetime]):
    """A timestamp that is UTC both ways: an aware value is converted to UTC on write (a naive
    one is refused), and a value read back carries `tzinfo=UTC` (SQLite stores none)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.utcoffset() is None:
            raise ValueError(f"naive datetime {value!r}: pass a timezone-aware value")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


_ENUM_VALUE = re.compile(r"[a-z_-]+")


def _check(table: str, column: str, values: tuple[str, ...], nullable: bool = False) -> Any:
    """A CHECK constraint `column IN (values)`; the values are spliced into SQL, so each must
    be a plain lower-case word."""
    bad = [v for v in values if not _ENUM_VALUE.fullmatch(v)]
    if bad:
        raise ValueError(f"CHECK values must match [a-z_-]+: {bad}")
    sql = f"{column} IN ({', '.join(repr(v) for v in values)})"
    return CheckConstraint(
        f"{column} IS NULL OR {sql}" if nullable else sql, name=f"ck_{table}_{column}"
    )


def _base() -> list[Any]:
    """id, created_at, created_by: on every table (api §7). created_by is nullable only so
    that the first principal, `system`, can exist; every other row names its creator, the
    `system` principal for the rows Spectio writes itself."""
    return [
        Column("id", String, primary_key=True),
        Column("created_at", UTCDateTime(), nullable=False),
        Column("created_by", String, ForeignKey("principals.id")),
    ]


def _mutable() -> list[Any]:
    return [
        Column("updated_at", UTCDateTime()),
        Column("deleted_at", UTCDateTime()),
    ]


# api §7.1: the full enum; 0.0.1 uses queued, running, cancelling, succeeded, failed, cancelled.
RUN_STATES = (
    "queued",
    "running",
    "pausing",
    "paused",
    "awaiting_review",
    "cancelling",
    "succeeded",
    "failed",
    "cancelled",
)
# api §7.2.
ATTEMPT_STATES = (
    "pending",
    "submitted",
    "running",
    "succeeded",
    "failed",
    "cached",
    "stored",
    "aborted",
)
TASK_STATES = (*ATTEMPT_STATES, "not_scheduled")
# api §7, `failure_class`, with the head and launch classes.
FAILURE_CLASSES = (
    "oom",
    "timeout",
    "preempted",
    "node_failure",
    "cancelled_external",
    "image",
    "tool_error",
    "engine_fault",
    "head_lost",
    "launch_error",
    "engine_missing",
    "engine_version",
    "input_check",
)
STAGE_SOURCES = ("declared", "detected")
STAGE_STATES = ("not_started", "running", "awaiting_review", "completed", "failed", "skipped")
RUN_ORIGINS = ("ui", "api", "wes", "cli-observed", "cli-adopted")
COMMAND_STATES = ("pending", "leased", "acked", "done", "failed")
WORKFLOW_SOURCES = ("git", "nf-core", "catalog", "crate", "local")
RUN_INPUT_KINDS = ("params", "params_resolved", "samplesheet", "manifest", "resources")
PRINCIPAL_KINDS = ("user", "service", "agent", "runner", "system")  # api §6
ACTOR_KINDS = ("person", "agent", "service", "cli")

principals = Table(
    "principals",
    metadata,
    *_base(),
    Column("kind", String, nullable=False),
    Column("display_name", String),
    Column("disabled_at", UTCDateTime()),
    _check("principals", "kind", PRINCIPAL_KINDS),
)

# owning_group_id has no foreign key: `groups` is not in the 0.0.1 store.
projects = Table(
    "projects",
    metadata,
    *_base(),
    Column("owning_group_id", String, nullable=False),
    Column("name", String),
    Column("visibility", String),
)

environments = Table(
    "environments",
    metadata,
    *_base(),
    Column("owning_group_id", String),
    Column("kind", String, nullable=False),  # slurm, k8s, local…: open-ended, no CHECK
    Column("config", Json),
)

runners = Table(
    "runners",
    metadata,
    *_base(),
    Column("environment_id", String, ForeignKey("environments.id"), nullable=False),
    Column("principal_id", String, ForeignKey("principals.id")),
    Column("version", String),
    Column("last_heartbeat_at", UTCDateTime()),
    Column("status", String),
)

workflows = Table(
    "workflows",
    metadata,
    *_base(),
    *_mutable(),
    Column("project_id", String, ForeignKey("projects.id"), nullable=False),
    Column("name", String),
    Column("location", String, nullable=False),
    Column("source", String, nullable=False),
    Column("engine", String),
    UniqueConstraint("project_id", "source", "location"),
    _check("workflows", "source", WORKFLOW_SOURCES),
)

workflow_versions = Table(
    "workflow_versions",
    metadata,
    *_base(),
    Column("workflow_id", String, ForeignKey("workflows.id"), nullable=False),
    Column("revision", String),
    Column("commit", String),
    Column("key", String),
    Column("params_schema", Json),
    Column("version", String),  # the version the pipeline declares, read at launch (inbox #87)
)

runs = Table(
    "runs",
    metadata,
    *_base(),
    *_mutable(),
    Column("project_id", String, ForeignKey("projects.id"), nullable=False),
    Column("workflow_version_id", String, ForeignKey("workflow_versions.id"), nullable=False),
    Column("environment_id", String, ForeignKey("environments.id"), nullable=False),
    Column("name", String),
    Column("state", String, nullable=False),
    Column("state_changed_at", UTCDateTime()),
    Column("started_at", UTCDateTime()),
    Column("ended_at", UTCDateTime()),
    Column("flags", Json),
    Column("failure", Json),
    Column("cancel_reason", String),
    Column("task_counts", Json),
    Column("tasks_expected", Integer),
    Column("origin", String),
    Column("launch_dir", String),
    Column("work_dir", String),
    Column("results_dir", String),
    Column("engine_version", String),
    Column("idempotency_key", String),
    Column("last_seq", Integer, nullable=False, server_default="0"),
    Column("projected_seq", Integer, nullable=False, server_default="0"),
    _check("runs", "state", RUN_STATES),
    _check("runs", "origin", RUN_ORIGINS, nullable=True),
    Index("ix_runs_project_created", "project_id", "created_at"),
    Index("ix_runs_state_project", "state", "project_id"),
)

run_inputs = Table(
    "run_inputs",
    metadata,
    *_base(),
    Column("run_id", String, ForeignKey("runs.id"), nullable=False),
    Column("version", Integer, nullable=False),
    Column("kind", String, nullable=False),
    Column("content", Json),
    Column("checksum", String),
    _check("run_inputs", "kind", RUN_INPUT_KINDS),
)

launches = Table(
    "launches",
    metadata,
    *_base(),
    Column("run_id", String, ForeignKey("runs.id"), nullable=False),
    Column("n", Integer, nullable=False),
    Column("launch_dir", String),
    Column("pid", Integer),
    Column("pid_start_time", String),
    Column("host_boot_id", String),
    Column("engine_session_id", String),
    Column("head_native_id", String),
    Column("head_state", String),
    Column("started_at", UTCDateTime()),
    Column("exited_at", UTCDateTime()),
    Column("exit_code", Integer),
    Column("culprit_attempt_id", String),  # the launch's first TERMINATE failure (api §7.2)
    UniqueConstraint("run_id", "n"),
)

runner_commands = Table(
    "runner_commands",
    metadata,
    *_base(),
    Column("runner_id", String, ForeignKey("runners.id")),
    Column("run_id", String, ForeignKey("runs.id")),
    Column("launch_id", String, ForeignKey("launches.id")),
    Column("kind", String, nullable=False),  # launch, cancel, resume, …: open-ended
    Column("payload", Json),
    Column("idempotency_key", String),
    Column("state", String, nullable=False),
    Column("lease_until", UTCDateTime()),
    Column("attempts", Integer, nullable=False, server_default="0"),
    _check("runner_commands", "state", COMMAND_STATES),
)

tasks = Table(
    "tasks",
    metadata,
    *_base(),
    Column("run_id", String, ForeignKey("runs.id"), nullable=False),
    Column("process_or_rule", String, nullable=False),
    Column("tag", String),
    Column("name", String),  # Nextflow's task name: the key of an untagged task (inbox #77)
    Column("state", String, nullable=False),
    Column("stage_id", String),  # a `run_stages.stage_id`, or none (P1 Task 27 sets it)
    _check("tasks", "state", TASK_STATES),
    Index("ix_tasks_run_key", "run_id", "process_or_rule", "tag", "name"),  # the projector's key
)

attempts = Table(
    "attempts",
    metadata,
    *_base(),
    Column("task_id", String, ForeignKey("tasks.id"), nullable=False),
    Column("n", Integer, nullable=False),
    Column("launch_n", Integer, nullable=False),
    Column("state", String, nullable=False),
    Column("ignored", Boolean, nullable=False, server_default="0"),
    Column("exit", Integer),
    Column("failure_class", String),
    Column("resources", Json),
    _check("attempts", "state", ATTEMPT_STATES),
    _check("attempts", "failure_class", FAILURE_CLASSES, nullable=True),
    UniqueConstraint("task_id", "launch_n", "n", name="uq_attempts_key"),  # api §8.2
)

events = Table(
    "events",
    metadata,
    *_base(),
    Column("run_id", String, ForeignKey("runs.id"), nullable=False),
    Column("seq", Integer, nullable=False),
    Column("event_id", String, nullable=False),
    Column("type", String, nullable=False),
    Column("source", String),
    Column("source_seq", Integer),
    Column("engine_time", UTCDateTime()),
    Column("received_at", UTCDateTime()),
    Column("actor_principal_id", String, ForeignKey("principals.id")),
    Column("actor_kind", String),
    Column("payload", Json),
    UniqueConstraint("run_id", "event_id"),
    Index("ix_events_run_seq", "run_id", "seq"),
    _check("events", "actor_kind", ACTOR_KINDS, nullable=True),
)

# api §7 `run_stages`, without `gate_id` (no gates in 0.0.1): P1 Task 27 fills it, Task 18 reads it.
run_stages = Table(
    "run_stages",
    metadata,
    *_base(),
    Column("run_id", String, ForeignKey("runs.id"), nullable=False),
    Column("stage_id", String, nullable=False),
    Column("position", Integer, nullable=False),
    Column("name", String),
    Column("source", String, nullable=False),
    Column("state", String, nullable=False),
    Column("task_counts", Json),
    Column("started_at", UTCDateTime()),
    Column("ended_at", UTCDateTime()),
    UniqueConstraint("run_id", "stage_id"),
    _check("run_stages", "source", STAGE_SOURCES),
    _check("run_stages", "state", STAGE_STATES),
)

# The processes (Nextflow) or rules (Snakemake) of a run, in first-seen order, with their stage:
# Nextflow's from `onProcessCreate`, Snakemake's from the rule files read when the stages freeze,
# and any other from its first task (P1 Task 27). `ended`: `onProcessTerminate` was seen;
# `jobs_planned`: the rule's jobs in Snakemake's last `run_info`. Not in api §7, which keys
# processes by name only: the stage of a process with no task yet needs a row.
run_processes = Table(
    "run_processes",
    metadata,
    *_base(),
    Column("run_id", String, ForeignKey("runs.id"), nullable=False),
    Column("name", String, nullable=False),
    Column("position", Integer, nullable=False),
    Column("stage_id", String),
    Column("ended", Boolean, nullable=False, server_default="0"),
    Column("jobs_planned", Integer),
    UniqueConstraint("run_id", "name"),
)

# The spool cursor and drop counts of a launch (P1 Assumption 11), written in the ingest
# transaction. Keyed by their natural key, so no id / created_at / created_by.
spool_cursors = Table(
    "spool_cursors",
    metadata,
    Column("launch_id", String, ForeignKey("launches.id"), primary_key=True),
    Column("file", String, primary_key=True),
    Column("offset", Integer, nullable=False),
)

spool_drops = Table(
    "spool_drops",
    metadata,
    Column("launch_id", String, ForeignKey("launches.id"), primary_key=True),
    Column("reason", String, primary_key=True),
    Column("count", Integer, nullable=False),
)

# The task of each Snakemake `jobid` in a launch: `job_finished` and `job_error` carry the jobid
# only (P1 Task 5). Written in the ingest transaction.
snakemake_jobs = Table(
    "snakemake_jobs",
    metadata,
    Column("launch_id", String, ForeignKey("launches.id"), primary_key=True),
    Column("jobid", Integer, primary_key=True),
    Column("task_id", String, ForeignKey("tasks.id"), nullable=False),
)
