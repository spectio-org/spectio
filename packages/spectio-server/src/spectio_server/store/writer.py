"""The one writer: every write goes through one thread and one connection (architecture §7.2).

Each submitted function runs in its own `BEGIN IMMEDIATE` transaction, so a write never has to
upgrade a read lock (the cause of SQLITE_BUSY), and writes run one at a time, in submit order.
A job notes the runs and tasks it changed with `note_change`; once its transaction commits, the
writer thread hands them to `on_commit` (the live stream of P1 Task 18), which must not block.
Readers open their own connections on `engine`.
"""

import logging
import queue
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import Future
from typing import Any, TypeVar

from sqlalchemy import Connection, Engine

T = TypeVar("T")

_Job = tuple[Callable[[Connection], Any], "Future[Any]"]
Changes = dict[str, set[str]]  # run ID → the IDs of its tasks that changed
_CHANGES = "spectio.changes"

log = logging.getLogger(__name__)


def note_change(conn: Connection, run_id: str, task_ids: Iterable[str] = ()) -> None:
    """Record, in the current transaction, that this run (and these tasks) changed."""
    conn.info.setdefault(_CHANGES, {}).setdefault(run_id, set()).update(task_ids)


class Writer:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.on_commit: Callable[[Changes], None] | None = None
        self._jobs: queue.Queue[_Job | None] = queue.Queue()
        self._lock = threading.Lock()
        self._closed = False
        self._thread = threading.Thread(
            target=self._run, args=(engine,), name="spectio-writer", daemon=True
        )
        self._thread.start()

    def submit(self, fn: Callable[[Connection], T]) -> "Future[T]":
        """Run `fn(conn)` in one transaction on the writer thread; commit unless it raises."""
        future: Future[T] = Future()
        with self._lock:
            if self._closed:
                raise RuntimeError("the writer is closed")
            self._jobs.put((fn, future))
        return future

    def close(self) -> None:
        """Finish the jobs already submitted, then stop the thread."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._jobs.put(None)
        self._thread.join()

    def _committed(self, changes: Changes | None) -> None:
        if changes and self.on_commit is not None:
            try:
                self.on_commit(changes)
            except Exception:  # a listener never stops the writer
                log.exception("on_commit failed")

    def _run(self, engine: Engine) -> None:
        try:
            with engine.connect().execution_options(spectio_begin="IMMEDIATE") as conn:
                while (job := self._jobs.get()) is not None:
                    fn, future = job
                    if not future.set_running_or_notify_cancel():
                        continue
                    try:
                        with conn.begin():
                            result = fn(conn)
                    except Exception as exc:
                        conn.info.pop(_CHANGES, None)
                        future.set_exception(exc)
                    except BaseException as exc:  # the thread dies: tell the caller first
                        future.set_exception(exc)
                        raise
                    else:
                        self._committed(conn.info.pop(_CHANGES, None))
                        future.set_result(result)
        finally:
            # Whatever ended the thread, no caller waits forever on a job it will never run.
            with self._lock:
                self._closed = True
            while not self._jobs.empty():
                left = self._jobs.get_nowait()
                if left is not None and left[1].set_running_or_notify_cancel():
                    left[1].set_exception(RuntimeError("writer stopped"))
