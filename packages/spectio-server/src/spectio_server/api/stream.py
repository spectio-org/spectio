"""`GET /events/stream`: live run deltas over SSE (P1 Task 18, Assumption 7; api §8.3, §8.5).

The writer thread calls `Stream.notify` after each commit with the runs and tasks it changed
(`store.writer.note_change`); `notify` only records them, under a lock, so it never waits for a
client. A pump task on the server's event loop flushes them once per `INTERVAL_S`: one
`spectio.run.delta` frame per changed run, so at most one per run per second, whatever the number
of commits. Each client has a bounded queue; one that falls `QUEUE_SIZE` frames behind is
dropped (its stream ends, and its `EventSource` reconnects and refetches). A comment line
`: keep-alive` opens each stream and is sent after `KEEP_ALIVE_S` without a frame.

The frame is a strict subset of api §8.5: `{run_id, seq_through, counts: {<process>: {<state>:
n}}, changed: {tasks: [<task ID>]}}`, with no `id:` line and no replay (no `Last-Event-ID`).
"""

import asyncio
import json
import logging
import threading
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import Engine, func, select

from spectio_server.api.problems import Problem
from spectio_server.store.schema import runs, tasks
from spectio_server.store.writer import Changes

log = logging.getLogger(__name__)
router = APIRouter()

INTERVAL_S = 1.0
KEEP_ALIVE_S = 15.0
QUEUE_SIZE = 64
MAX_CLIENTS = 32  # each server process caps its SSE clients (api §8.3)
KEEP_ALIVE = ": keep-alive\n\n"


@dataclass(eq=False)
class Subscriber:
    queue: "asyncio.Queue[str]"
    dropped: bool = False


@dataclass(eq=False)
class Stream:
    engine: Engine
    queue_size: int = QUEUE_SIZE
    subscribers: set[Subscriber] = field(default_factory=set)
    clients: int = 0  # open connections, dropped ones included: the cap counts these
    _pending: Changes = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _pump: "asyncio.Task[None] | None" = None

    def notify(self, changes: Changes) -> None:
        """Record changed runs and tasks (the writer thread, after a commit); never blocks."""
        if not self.subscribers:
            return
        with self._lock:
            for run_id, task_ids in changes.items():
                self._pending.setdefault(run_id, set()).update(task_ids)

    def subscribe(self) -> Subscriber:
        """A new client, on the running event loop; starts the pump if it is not running."""
        sub = Subscriber(asyncio.Queue(self.queue_size))
        self.subscribers.add(sub)
        if self._pump is None or self._pump.done():
            self._pump = asyncio.get_running_loop().create_task(self._run())
        return sub

    def unsubscribe(self, sub: Subscriber) -> None:
        self.subscribers.discard(sub)

    def open(self) -> Subscriber:
        """A new connection: it holds a slot of the cap until `close`, even once dropped."""
        self.clients += 1
        return self.subscribe()

    def close(self, sub: Subscriber) -> None:
        self.unsubscribe(sub)
        self.clients -= 1

    async def flush(self) -> None:
        """Send one frame per run changed since the last flush."""
        with self._lock:
            pending, self._pending = self._pending, {}
        if pending:
            for frame in await asyncio.to_thread(self._frames, pending):
                self._publish(frame)

    def _publish(self, frame: str) -> None:
        for sub in list(self.subscribers):
            try:
                sub.queue.put_nowait(frame)
            except asyncio.QueueFull:  # a slow client: drop it, never wait for it
                sub.dropped = True
                self.subscribers.discard(sub)

    def _frames(self, pending: Changes) -> list[str]:
        found = []
        with self.engine.connect() as conn:
            for run_id, task_ids in pending.items():
                seq = conn.execute(select(runs.c.last_seq).where(runs.c.id == run_id)).scalar()
                if seq is None:
                    continue
                counts: dict[str, dict[str, int]] = {}
                for process, state, n in conn.execute(
                    select(tasks.c.process_or_rule, tasks.c.state, func.count())
                    .where(tasks.c.run_id == run_id)
                    .group_by(tasks.c.process_or_rule, tasks.c.state)
                ):
                    counts.setdefault(process, {})[state] = n
                data = {
                    "run_id": run_id,
                    "seq_through": seq,
                    "counts": counts,
                    "changed": {"tasks": sorted(task_ids)},
                }
                found.append(f"event: spectio.run.delta\ndata: {json.dumps(data)}\n\n")
        return found

    async def _run(self) -> None:
        while self.subscribers:
            await asyncio.sleep(INTERVAL_S)
            try:
                await self.flush()
            except Exception:  # a failed read: the next flush tries again
                log.exception("stream flush failed")


class _Response(StreamingResponse):
    """Frees the connection's slot when the response ends, even if its body never starts."""

    def __init__(self, stream: Stream, sub: Subscriber, body: AsyncIterator[str]) -> None:
        super().__init__(
            body, media_type="text/event-stream", headers={"Cache-Control": "no-store"}
        )
        self.stream, self.sub = stream, sub

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.stream.close(self.sub)


@router.get("/events/stream", response_class=StreamingResponse)
async def events_stream(request: Request) -> StreamingResponse:
    stream: Stream = request.app.state.stream
    if stream.clients >= MAX_CLIENTS:
        raise Problem(429, "rate-limited", "Too many streams", "Close another Spectio tab.")
    sub = stream.open()  # no `await` since the check: concurrent opens cannot both pass it

    async def frames() -> AsyncIterator[str]:
        yield KEEP_ALIVE
        while not sub.dropped:
            try:
                yield await asyncio.wait_for(sub.queue.get(), KEEP_ALIVE_S)
            except TimeoutError:
                yield KEEP_ALIVE

    return _Response(stream, sub, frames())
