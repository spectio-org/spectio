"""`attempt_metrics` (FU-P3-105a; api §5.5 and §7, schedulers §3.7): the performance measures
of each ended attempt, with its run's identity, and `runs.metrics_sacct_at`, the marker of the
background `sacct.json` fill.

The rows of the runs already held are filled from the database only, never from a file:
`attempts.resources` (the trace's six values on Nextflow, the request on Snakemake) and, on
Nextflow, the partition of `attempts.slurm` (the trace's `queue`). Their `ended_at` is the
run's end, or the attempt's first sight while the run is live: the attempt's own end is not
stored. A deleted run's attempts and those that did not end get no row.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-11
"""

import re
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | Sequence[str] | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
ENDED = ("succeeded", "failed", "aborted")
PARTITION = re.compile(r"[A-Za-z0-9_.-]{1,64}")
MAX_RATIO = 1_000_000
BATCH = 500


def upgrade() -> None:
    op.add_column("runs", sa.Column("metrics_sacct_at", sa.DateTime(timezone=True), nullable=True))
    table = op.create_table(
        "attempt_metrics",
        sa.Column("attempt_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(), nullable=True),
        sa.Column("process_or_rule", sa.String(), nullable=False),
        sa.Column("engine", sa.String(), nullable=True),
        sa.Column("pipeline", sa.String(), nullable=True),
        sa.Column("pipeline_version", sa.String(), nullable=True),
        sa.Column("environment_id", sa.String(), nullable=True),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=True),
        sa.Column("run_state", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("partition", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("cpus", sa.Integer(), nullable=True),
        sa.Column("mem_bytes", sa.BigInteger(), nullable=True),
        sa.Column("time_limit_s", sa.Float(), nullable=True),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("cpu_eff", sa.Float(), nullable=True),
        sa.Column("peak_rss_bytes", sa.BigInteger(), nullable=True),
        sa.Column("peak_vmem_bytes", sa.BigInteger(), nullable=True),
        sa.Column("mem_eff", sa.Float(), nullable=True),
        sa.Column("realtime_s", sa.Float(), nullable=True),
        sa.Column("time_eff", sa.Float(), nullable=True),
        sa.Column("wait_s", sa.Float(), nullable=True),
        sa.Column("rchar_bytes", sa.BigInteger(), nullable=True),
        sa.Column("wchar_bytes", sa.BigInteger(), nullable=True),
        sa.Column("read_bytes", sa.BigInteger(), nullable=True),
        sa.Column("write_bytes", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "state IN ('succeeded', 'failed', 'aborted')", name="ck_attempt_metrics_state"
        ),
        sa.CheckConstraint(
            "source IS NULL OR source IN ('trace', 'benchmark', 'sacct')",
            name="ck_attempt_metrics_source",
        ),
        sa.ForeignKeyConstraint(["attempt_id"], ["attempts.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("attempt_id"),
    )
    with op.batch_alter_table("attempt_metrics") as batch_op:
        batch_op.create_index("ix_attempt_metrics_project_ended", ["project_id", "ended_at"])
        batch_op.create_index(
            "ix_attempt_metrics_project_process", ["project_id", "process_or_rule", "ended_at"]
        )
        batch_op.create_index(
            "ix_attempt_metrics_project_pipeline",
            ["project_id", "pipeline", "process_or_rule", "ended_at"],
        )
        batch_op.create_index(
            "ix_attempt_metrics_project_partition", ["project_id", "partition", "ended_at"]
        )
        batch_op.create_index("ix_attempt_metrics_run", ["run_id"])
    _fill(table)


def _number(value: Any) -> float | None:
    ok = isinstance(value, int | float) and not isinstance(value, bool) and value >= 0
    return float(value) if ok and value == value and value != float("inf") else None


def _whole(value: Any) -> int | None:
    found = _number(value)
    return None if found is None or found > 2**63 - 1 else int(found)


def _ratio(part: float | None, whole: float | None) -> float | None:
    if part is None or not whole:
        return None
    found = round(part / whole, 4)
    return None if found > MAX_RATIO else found


def _row(r: Any) -> dict[str, Any]:
    own = r.resources if isinstance(r.resources, dict) else {}
    cpus, memory = _whole(own.get("cpus")), _whole(own.get("memory_bytes"))
    time_s, real = _number(own.get("time_s")), _number(own.get("realtime_s"))
    cpu, peak = _number(own.get("cpu_percent")), _whole(own.get("peak_rss_bytes"))
    request = (r.slurm or {}).get("request") if isinstance(r.slurm, dict) else None
    queue = request.get("partition") if isinstance(request, dict) else None
    nextflow = r.engine == "nextflow"
    measured = nextflow and any(v is not None for v in (cpu, peak, real))
    return {
        "attempt_id": r.attempt_id,
        "run_id": r.run_id,
        "task_id": r.task_id,
        "attempt": r.n,
        "tag": r.tag,
        "process_or_rule": r.process_or_rule,
        "engine": r.engine,
        "pipeline": r.pipeline,
        "pipeline_version": r.pipeline_version,
        "environment_id": r.environment_id,
        "project_id": r.project_id,
        "owner_id": r.owner_id,
        "run_state": r.run_state,
        "state": r.state,
        "ended_at": r.run_ended_at or r.seen_at,
        "partition": queue
        if nextflow and isinstance(queue, str) and PARTITION.fullmatch(queue)
        else None,
        "source": "trace" if measured else None,
        "cpus": cpus,
        "mem_bytes": memory,
        "time_limit_s": time_s,
        "cpu_percent": cpu if nextflow else None,
        "cpu_eff": _ratio(cpu, None if cpus is None else 100 * cpus) if nextflow else None,
        "peak_rss_bytes": peak if nextflow else None,
        "mem_eff": _ratio(peak, memory) if nextflow else None,
        "realtime_s": real if nextflow else None,
        "time_eff": _ratio(real, time_s) if nextflow else None,
    }


def _fill(table: sa.Table) -> None:
    conn = op.get_bind()
    m = sa.MetaData()
    runs = sa.Table("runs", m, autoload_with=conn)
    tasks = sa.Table("tasks", m, autoload_with=conn)
    attempts = sa.Table("attempts", m, autoload_with=conn)
    versions = sa.Table("workflow_versions", m, autoload_with=conn)
    workflows = sa.Table("workflows", m, autoload_with=conn)
    query = (
        sa.select(
            attempts.c.id.label("attempt_id"),
            attempts.c.n,
            attempts.c.state,
            attempts.c.created_at.label("seen_at"),
            sa.type_coerce(attempts.c.resources, JSON).label("resources"),
            sa.type_coerce(attempts.c.slurm, JSON).label("slurm"),
            tasks.c.id.label("task_id"),
            tasks.c.tag,
            tasks.c.process_or_rule,
            runs.c.id.label("run_id"),
            runs.c.project_id,
            runs.c.environment_id,
            runs.c.created_by.label("owner_id"),
            runs.c.state.label("run_state"),
            runs.c.ended_at.label("run_ended_at"),
            workflows.c.engine,
            workflows.c.name.label("pipeline"),
            versions.c.version.label("pipeline_version"),
        )
        .select_from(attempts)
        .join(tasks, tasks.c.id == attempts.c.task_id)
        .join(runs, runs.c.id == tasks.c.run_id)
        .join(versions, versions.c.id == runs.c.workflow_version_id)
        .join(workflows, workflows.c.id == versions.c.workflow_id)
        .where(attempts.c.state.in_(ENDED), runs.c.deleted_at.is_(None))
        .order_by(attempts.c.id)
        .limit(BATCH)
    )
    after = ""
    while found := conn.execute(query.where(attempts.c.id > after)).all():  # read, then write
        conn.execute(sa.insert(table), [_row(r) for r in found])
        after = found[-1].attempt_id


def downgrade() -> None:
    op.drop_table("attempt_metrics")
    op.drop_column("runs", "metrics_sacct_at")
