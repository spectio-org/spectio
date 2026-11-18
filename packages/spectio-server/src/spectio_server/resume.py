"""Resume and copy, the parts the read routes share (P1 Task 30; api §5 and §5.1, notes of
2026-10-28; dev-env §15.3 req. 16).

`resume_refusal` says why a run cannot be resumed now, or None: first from its row (origin,
state, a child of the same launch directory not ended, a Nextflow session ID that is not a
UUID), then from its directories (`spectio.runner.resume.prove`, in the file pool). The same
answer is `actions.resume` on the run and the `409` of `:relaunch`. `command` rebuilds the engine
command the head script runs, from the run's `launch` command and the server's settings.
"""

import shlex
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Row, select

from spectio.config import Settings
from spectio.environments import as_snapshot, launch_fields, read_as
from spectio.runner.headscript import SESSION_ID, engine_args
from spectio.runner.loop import LaunchPayload, extra_file
from spectio.runner.resume import NotResumable, prove
from spectio.runner.rundir import run_paths
from spectio.runner.types import LaunchSpec, ResumeSource
from spectio_server.failure import Context, dir_run_id
from spectio_server.files.pool import Stalled
from spectio_server.store.schema import runner_commands, runs

TERMINAL = ("succeeded", "failed", "cancelled")
RESUMABLE = ("failed", "cancelled")


def row_refusal(conn: Connection, row: Row[Any]) -> str | None:
    """Why the store says no; also run in `:relaunch`'s own transaction (BEGIN IMMEDIATE)."""
    if row.origin == "cli-observed":
        return "cli_observed"
    if row.state not in RESUMABLE:
        return "not_failed_or_cancelled" if row.state in TERMINAL else "running"
    busy = conn.execute(
        select(runs.c.id)
        .where(runs.c.launch_dir == row.launch_dir, runs.c.state.not_in(TERMINAL))
        .limit(1)
    ).first()
    if busy is not None:
        return "resume_in_progress"
    session = row.engine_session_id
    if row.engine == "nextflow" and session is not None and not SESSION_ID.fullmatch(session):
        return "session_id_refused"
    return None


def check_dirs(ctx: Context, row: Row[Any]) -> tuple[int, int]:
    """`prove` in the file pool: the launch directory's device and inode, or NotResumable."""
    try:
        return ctx.files.run(lambda: prove(ctx.runs_root, dir_run_id(row), row.id), ctx.timeout_s)
    except Stalled as exc:
        raise NotResumable("head_unverified", str(exc)) from None


def resume_refusal(conn: Connection, row: Row[Any], ctx: Context) -> str | None:
    reason = row_refusal(conn, row)
    if reason is None:
        try:
            check_dirs(ctx, row)
        except NotResumable as exc:
            reason = exc.reason
    return reason


def resumed_as(conn: Connection, run_id: str) -> list[dict[str, Any]]:
    found = conn.execute(
        select(runs.c.id, runs.c.name, runs.c.state)
        .where(runs.c.parent_run_id == run_id, runs.c.deleted_at.is_(None))
        .order_by(runs.c.created_at, runs.c.id)
    )
    return [{"id": r.id, "name": r.name, "state": r.state} for r in found]


def launch_payload(conn: Connection, run_id: str) -> LaunchPayload | None:
    """The run's `launch` command payload; None for a run that has none (rebuilt, observed)."""
    raw = conn.execute(
        select(runner_commands.c.payload)
        .where(runner_commands.c.run_id == run_id, runner_commands.c.kind == "launch")
        .order_by(runner_commands.c.created_at)
        .limit(1)
    ).scalar()
    try:
        return None if raw is None else LaunchPayload.model_validate(raw)
    except ValueError:
        return None


def _words(cmd: str) -> list[str]:
    try:
        return shlex.split(cmd)
    except ValueError:  # an unbalanced quote: shown as one word
        return [cmd]


def command(conn: Connection, row: Row[Any], settings: Settings) -> dict[str, Any] | None:
    """`{argv, text}`: the engine command as the head script runs it (dev-env §15.3 req. 16),
    the parameters as their file; `text` quotes every word for a POSIX shell. None for a run
    started from a terminal, one with no launch command, or one whose snapshot is `not_readable`.
    Today's settings: an `engine_cmd` or `extra_args` changed since the launch shows the new
    ones; the executor and its SLURM values are the run's own, the server's built-in for a
    `not_recorded` run (FU-P3-86a, api §5.4)."""
    if row.origin == "cli-observed" or row.engine not in ("nextflow", "snakemake"):
        return None
    own = read_as(row.environment, settings)
    if own is None:  # `not_readable`: its executor is unknown
        return None
    payload = launch_payload(conn, row.id)
    if payload is None:
        return None
    resume = None
    if payload.resume_of is not None:
        parent = run_paths(settings.runs_root, payload.resume_of.run_id)
        session = payload.resume_of.engine_session_id
        resume = ResumeSource(parent.launch_dir, parent.work_dir, 0, 0, session)
    engines = settings.engines
    cmd = engines.nextflow_cmd if row.engine == "nextflow" else engines.snakemake_cmd
    paths = run_paths(settings.runs_root, row.id)
    spec = LaunchSpec(
        run_id=row.id,
        launch_n=1,
        engine=row.engine,
        engine_cmd=cmd or row.engine,
        location=Path(payload.location),
        launch_dir=paths.launch_dir,
        work_dir=paths.work_dir,
        profiles=payload.profiles,
        params=payload.params,
        **launch_fields(as_snapshot(own)),
        extra_args=engines.extra_args.get(row.engine, []),
        resume_of=resume,
        default_resources=payload.default_resources,
        config_file=extra_file(payload),  # its name only: the bytes are cleared once answered
    )
    try:
        argv = [*_words(spec.engine_cmd), *engine_args(spec)]
    except ValueError:  # a profile or session ID the head script would refuse
        return None
    return {"argv": argv, "text": shlex.join(argv)}
