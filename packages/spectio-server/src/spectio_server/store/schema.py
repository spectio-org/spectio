"""The 0.0.1 tables of api-and-data-model.md §7, as SQLAlchemy Core metadata.

Portable across SQLite and Postgres: text primary keys (prefixed ULIDs), UTC timestamps, JSON
through the ORM type, CHECK constraints instead of enums. Each table keeps only the columns of
api §7 that P1 uses; later tasks add the others by migration.
"""

from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

Json = JSON().with_variant(JSONB(), "postgresql")  # TEXT with JSON1 on SQLite


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _check(table: str, column: str, values: tuple[str, ...], nullable: bool = False) -> Any:
    sql = _in(column, values)
    return CheckConstraint(
        f"{column} IS NULL OR {sql}" if nullable else sql, name=f"ck_{table}_{column}"
    )


def _base() -> list[Any]:
    """id, created_at, created_by: on every table (api §7). created_by is null for the first
    principal and for rows the system writes itself."""
    return [
        Column("id", String, primary_key=True),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("created_by", String, ForeignKey("principals.id")),
    ]


def _mutable() -> list[Any]:
    return [
        Column("updated_at", DateTime(timezone=True)),
        Column("deleted_at", DateTime(timezone=True)),
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
RUN_ORIGINS = ("ui", "api", "wes", "cli-observed", "cli-adopted")
COMMAND_STATES = ("pending", "leased", "acked", "done", "failed")
WORKFLOW_SOURCES = ("git", "nf-core", "catalog", "crate", "local")
RUN_INPUT_KINDS = ("params", "params_resolved", "samplesheet", "manifest", "resources")
PRINCIPAL_KINDS = ("user", "service", "agent")
ACTOR_KINDS = ("person", "agent", "service", "cli")

principals = Table(
    "principals",
    metadata,
    *_base(),
    Column("kind", String, nullable=False),
    Column("display_name", String),
    Column("disabled_at", DateTime(timezone=True)),
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
    Column("last_heartbeat_at", DateTime(timezone=True)),
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
    Column("state_changed_at", DateTime(timezone=True)),
    Column("started_at", DateTime(timezone=True)),
    Column("ended_at", DateTime(timezone=True)),
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
    Column("started_at", DateTime(timezone=True)),
    Column("exited_at", DateTime(timezone=True)),
    Column("exit_code", Integer),
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
    Column("lease_until", DateTime(timezone=True)),
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
    Column("state", String, nullable=False),
    _check("tasks", "state", TASK_STATES),
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
    Column("engine_time", DateTime(timezone=True)),
    Column("received_at", DateTime(timezone=True)),
    Column("actor_principal_id", String, ForeignKey("principals.id")),
    Column("actor_kind", String),
    Column("payload", Json),
    UniqueConstraint("run_id", "event_id"),
    Index("ix_events_run_seq", "run_id", "seq"),
    _check("events", "actor_kind", ACTOR_KINDS, nullable=True),
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
