"""The file pool: every read of a run's files runs here, with a timeout (dev-env §15.3 req. 13,
SEC-157; checking-scenarios §11.1).

Its threads are its own: not the writer's, which projects the spools, nor the runner's, which
reads them, so a stalled file system (an NFS or Lustre mount that stops answering) never stops a
run's events. A caller waits at most its timeout, then gets `Stalled`; the read itself cannot be
interrupted and goes on in its thread. Jobs in flight are bounded: once every thread is stuck
and the backlog is full, `run` refuses at once instead of queueing. The threads are daemons, so
a read stuck in the kernel never holds the server's exit.

A job must be whole: it opens, reads and closes, and returns data, never an open file, since a
caller that timed out never sees what it returns.
"""

import queue
import threading
from collections.abc import Callable
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any, TypeVar

T = TypeVar("T")

WORKERS = 4
READ_TIMEOUT_S = 5.0  # what a route waits for one listing, one read or one view's reads
BACKLOG = 16  # jobs waiting for a thread, beyond those running


class Stalled(Exception):
    """The file system did not answer in time, or the pool is full of stalled reads."""


class FilePool:
    def __init__(self, workers: int = WORKERS, backlog: int = BACKLOG) -> None:
        self._workers = workers
        self._slots = threading.BoundedSemaphore(workers + backlog)
        self._jobs: queue.SimpleQueue[tuple[Callable[[], Any], Future[Any]]] = queue.SimpleQueue()
        self._started = False
        self._lock = threading.Lock()

    def _start(self) -> None:
        with self._lock:
            if self._started:
                return
            for i in range(self._workers):
                threading.Thread(target=self._work, name=f"spectio-files-{i}", daemon=True).start()
            self._started = True

    def _work(self) -> None:
        while True:
            fn, future = self._jobs.get()
            try:
                if future.set_running_or_notify_cancel():
                    try:
                        future.set_result(fn())
                    except BaseException as exc:  # handed to the caller, never kills the thread
                        future.set_exception(exc)
            finally:
                self._slots.release()

    def run(self, fn: Callable[[], T], timeout_s: float) -> T:
        """`fn()` in a pool thread; its result, or its exception. Raises `Stalled` when it has
        not answered within `timeout_s`, or at once when the pool is full."""
        if not self._slots.acquire(blocking=False):
            raise Stalled("the file system is not answering: every file reader is waiting")
        self._start()
        future: Future[T] = Future()
        self._jobs.put((fn, future))
        try:
            return future.result(timeout_s)
        except FutureTimeout:
            future.cancel()  # a job still queued never runs
            raise Stalled(f"the file system did not answer within {timeout_s:g} s") from None
