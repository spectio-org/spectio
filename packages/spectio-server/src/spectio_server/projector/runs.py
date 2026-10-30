"""Run state, the event log and the run summary: api §7.1, §7.2 and §8.2 (P1 Task 4).

A `Projection` is one transaction's view of a run and the launch being projected. It allocates
`seq` (api §8.2), moves the run along the transitions 0.0.1 uses, never out of a terminal state,
and writes the summary when the transaction ends.

The run summary of P1 Task 4 maps to the columns of api §7 `runs`: its `counts` (state → n,
over the run's tasks) is `runs.task_counts`; `tasks_expected` is `runs.tasks_expected`, set by
an engine that reports a planned total (Snakemake, Task 5); `tasks_total` is not stored: it is
the sum of `task_counts`, and the computed `summary.tasks.total` of api §7 is `tasks_expected`
when set, else that sum.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, func, insert, select, update

from spectio_server.ids import new_id
from spectio_server.store.schema import attempts, events, launches, runs, tasks

TERMINAL = frozenset({"succeeded", "failed", "cancelled"})
OPEN_ATTEMPT_STATES = ("pending", "submitted", "running")
# The engine's own end of a launch, kept in `launches.head_state` (api §8.2: the first wins).
ENGINE_ENDED = frozenset({"succeeded", "failed"})
# The transitions of api §7.1 that 0.0.1 uses.
_NEXT = {
    "queued": frozenset({"running", "failed", "cancelling"}),
    "running": frozenset({"succeeded", "failed", "cancelling"}),
    "cancelling": frozenset({"cancelled"}),
}


def failure_json(
    class_: str, message: str, task_id: str | None = None, attempt_n: int | None = None
) -> dict[str, Any]:
    """`runs.failure` (api §7)."""
    return {"class": class_, "message": message, "task_id": task_id, "attempt_n": attempt_n}


@dataclass
class Projection:
    conn: Connection
    run_id: str
    launch_id: str
    launch_n: int
    state: str
    head_state: str | None
    last_seq: int
    now: datetime

    @classmethod
    def load(cls, conn: Connection, launch_id: str) -> "Projection":
        row = conn.execute(
            select(
                launches.c.run_id,
                launches.c.n,
                launches.c.head_state,
                runs.c.state,
                runs.c.last_seq,
            )
            .join(runs, runs.c.id == launches.c.run_id)
            .where(launches.c.id == launch_id)
            .with_for_update(of=runs)  # the run row lock of api §8.2 (no-op on SQLite)
        ).one()
        now = datetime.now(UTC)
        return cls(conn, row.run_id, launch_id, row.n, row.state, row.head_state, row.last_seq, now)

    def log(self, type_: str, payload: dict[str, Any], **columns: Any) -> None:
        """Append one event to the run's log with the next `seq`."""
        self.last_seq += 1
        self.conn.execute(
            insert(events).values(
                id=new_id("evt"),
                created_at=self.now,
                received_at=self.now,
                run_id=self.run_id,
                seq=self.last_seq,
                event_id=columns.pop("event_id", None) or new_id("evt"),
                type=type_,
                payload=payload,
                **columns,
            )
        )

    def move(self, to: str, failure: dict[str, Any] | None = None) -> bool:
        """Move the run to `to` if api §7.1 allows it from its state; log the change."""
        if to not in _NEXT.get(self.state, ()):
            return False
        values: dict[str, Any] = {"state": to, "state_changed_at": self.now}
        if self.state == "queued" and to == "running":
            values["started_at"] = self.now
        if to in TERMINAL:
            values["ended_at"] = self.now
        if failure is not None:
            values["failure"] = failure
        self.conn.execute(update(runs).where(runs.c.id == self.run_id).values(**values))
        self.log("spectio.run.state_changed", {"from": self.state, "to": to}, source="projector")
        self.state = to
        return True

    def end_launch(self, to: str = "aborted", failure_class: str | None = None) -> None:
        """Close this launch's open attempts: `aborted` (api §7.2), or `failed` when the head is
        lost (api §7.1)."""
        run_tasks = select(tasks.c.id).where(tasks.c.run_id == self.run_id)
        self.conn.execute(
            update(attempts)
            .where(
                attempts.c.task_id.in_(run_tasks.scalar_subquery()),
                attempts.c.launch_n == self.launch_n,
                attempts.c.state.in_(OPEN_ATTEMPT_STATES),
            )
            .values(state=to, failure_class=failure_class)
        )
        self.sync_tasks()

    def sync_tasks(self, task_id: str | None = None) -> None:
        """A task's state is its last attempt's (api §7.2)."""
        last = (
            select(attempts.c.state)
            .where(attempts.c.task_id == tasks.c.id)
            .order_by(attempts.c.launch_n.desc(), attempts.c.n.desc())
            .limit(1)
            .scalar_subquery()
        )
        where = tasks.c.id == task_id if task_id else tasks.c.run_id == self.run_id
        self.conn.execute(update(tasks).where(where, last.is_not(None)).values(state=last))

    def set_launch(self, **values: Any) -> None:
        if values:
            self.conn.execute(
                update(launches).where(launches.c.id == self.launch_id).values(**values)
            )
        self.head_state = values.get("head_state", self.head_state)

    def finish(self) -> None:
        """Write the summary; the projection is current with the log (P1 Assumption 11)."""
        counts = self.conn.execute(
            select(tasks.c.state, func.count())
            .where(tasks.c.run_id == self.run_id)
            .group_by(tasks.c.state)
        ).all()
        self.conn.execute(
            update(runs)
            .where(runs.c.id == self.run_id)
            .values(
                last_seq=self.last_seq,
                projected_seq=self.last_seq,
                task_counts={state: n for state, n in counts},
                updated_at=self.now,
            )
        )
