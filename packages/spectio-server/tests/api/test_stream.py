"""`GET /events/stream` (P1 Task 18, Assumption 7; api §8.3, §8.5)."""

import asyncio
import json
import threading
from collections import Counter
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
import uvicorn
from fastapi.testclient import TestClient

from spectio.config import Settings
from spectio.runner.types import SpoolBatch
from spectio_sdk.events import SpoolEvent
from spectio_server.api.stream import MAX_CLIENTS, Stream
from spectio_server.app import NO_API, create_app
from spectio_server.projector.ingest import ingest
from spectio_server.store.writer import Writer

from ..conftest import free_port
from .conftest import add_run

RUN = "run_01K8T2F1XTVRES000000000301"
STREAM = "/api/v1/events/stream"


def event(n: int, hook: str, **data: Any) -> SpoolEvent:
    return SpoolEvent.model_validate(
        {
            "v": 1,
            "id": f"evt_s{n}",
            "run": RUN,
            "launch": 1,
            "producer": "nf-spectio/0.0.1",
            "seq": n,
            "time": "2026-10-30T08:00:00Z",
            "type": f"nextflow.{hook}",
            "data": data,
        }
    )


@pytest.fixture
def served(settings: Settings, writer: Writer) -> Iterator[str]:
    """The app on a real loopback port, as `spectio serve` runs it."""
    app = create_app(settings, writer)
    port = free_port()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        lifespan="off",
        log_level="warning",
        timeout_graceful_shutdown=1,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        thread.join(0.01)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(10)


def test_stream_needs_session(client: TestClient, authed_client: TestClient) -> None:
    """TODO(P1 Task 16): no session cookie → 401 problem, no stream opened. Until sign-in is
    built, the stream is not mounted on a shared machine, and other sites are refused (#86)."""
    absent = client.get(STREAM)
    assert absent.status_code == 404
    assert absent.headers["content-type"].startswith("application/problem+json")
    assert NO_API in absent.json()["detail"]
    cross = authed_client.get(STREAM, headers={"Sec-Fetch-Site": "cross-site"})
    assert cross.status_code == 403
    foreign = authed_client.get(STREAM, headers={"Host": "rebind.example:8080"})
    assert foreign.status_code == 400


def frames(response: Any) -> Iterator[tuple[str, str]]:
    """(event, data) of each frame; a comment is ("", text)."""
    kind = ""
    for line in response.iter_lines():
        if line.startswith(":"):
            yield "", line[1:].strip()
        elif line.startswith("event: "):
            kind = line[len("event: ") :]
        elif line.startswith("data: "):
            yield kind, line[len("data: ") :]


def test_stream_delta_after_ingest(served: str, writer: Writer, settings: Settings) -> None:
    launch_id = add_run(writer, settings, RUN, "live", "queued")
    with (
        httpx2.Client(base_url=served, timeout=10) as http,
        http.stream("GET", STREAM) as response,
    ):
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-store"
        seen = frames(response)
        assert next(seen) == ("", "keep-alive")  # subscribed
        batch = SpoolBatch(
            [
                event(1, "onFlowCreate", nextflow="26.10.4"),
                event(2, "onTaskSubmit", process="ALIGN", tag="S01", attempt=1, taskId="1"),
                event(3, "onTaskSubmit", process="ALIGN", tag="S02", attempt=1, taskId="2"),
            ],
            {},
            Counter(),
        )
        writer.submit(lambda c: ingest(c, launch_id, batch)).result()
        kind, data = next(f for f in seen if f[0])
    assert kind == "spectio.run.delta"
    delta = json.loads(data)
    assert delta["run_id"] == RUN
    assert delta["counts"] == {"ALIGN": {"submitted": 2}}
    assert delta["seq_through"] >= 3
    assert len(delta["changed"]["tasks"]) == 2
    assert set(delta) == {"run_id", "seq_through", "counts", "changed"}


def test_stream_coalesces_per_run(writer: Writer, settings: Settings) -> None:
    """Two commits of one run before a flush give one frame, with the tasks of both."""
    add_run(writer, settings, RUN, "live", "running")
    stream = Stream(writer.engine)

    async def scenario() -> list[str]:
        sub = stream.subscribe()
        stream.notify({RUN: {"tsk_1"}})
        stream.notify({RUN: {"tsk_2"}})
        await stream.flush()
        found = []
        while not sub.queue.empty():
            found.append(sub.queue.get_nowait())
        stream.unsubscribe(sub)
        return found

    (frame,) = asyncio.run(scenario())
    assert frame.startswith("event: spectio.run.delta\ndata: ")
    assert sorted(json.loads(frame.split("data: ", 1)[1])["changed"]["tasks"]) == ["tsk_1", "tsk_2"]


def test_slow_client_dropped_never_blocks(writer: Writer, settings: Settings) -> None:
    """A client that reads nothing fills its bounded queue and is dropped; the others and the
    writer's `notify` never wait for it."""
    add_run(writer, settings, RUN, "live", "running")
    stream = Stream(writer.engine, queue_size=2)

    async def scenario() -> tuple[bool, bool, int]:
        slow, fast = stream.subscribe(), stream.subscribe()
        for i in range(5):
            stream.notify({RUN: {f"tsk_{i}"}})  # returns at once: no client is waited for
            await stream.flush()
            while not fast.queue.empty():
                fast.queue.get_nowait()
        return slow.dropped, fast.dropped, len(stream.subscribers)

    assert asyncio.run(scenario()) == (True, False, 1)


def test_stream_keep_alive(served: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from spectio_server.api import stream as stream_mod

    monkeypatch.setattr(stream_mod, "KEEP_ALIVE_S", 0.2)
    with (
        httpx2.Client(base_url=served, timeout=10) as http,
        http.stream("GET", STREAM) as response,
    ):
        seen = frames(response)
        assert [next(seen), next(seen)] == [("", "keep-alive"), ("", "keep-alive")]


def test_new_run_sends_a_delta(served: str, writer: Writer, settings: Settings) -> None:
    """A run just inserted (`insert_run`, used by `POST /runs` and the rebuild) sends a frame,
    before any head report (CR-P3T18-01)."""
    with (
        httpx2.Client(base_url=served, timeout=10) as http,
        http.stream("GET", STREAM) as response,
    ):
        seen = frames(response)
        assert next(seen) == ("", "keep-alive")
        add_run(writer, settings, RUN, "new", "queued")
        kind, data = next(f for f in seen if f[0])
    assert kind == "spectio.run.delta"
    assert json.loads(data)["run_id"] == RUN


def test_client_cap_holds_under_concurrent_opens(served: str) -> None:
    """Opens that arrive together cannot pass the cap (CR-P3T18-02, SEC-P3T18-02), and a closed
    stream frees its slot."""

    async def scenario() -> tuple[Counter[int], int]:
        async with httpx2.AsyncClient(base_url=served, timeout=10) as http:

            async def one() -> tuple[int, Any]:
                response = await http.send(http.build_request("GET", STREAM), stream=True)
                return response.status_code, response

            opened = await asyncio.gather(*(one() for _ in range(40)))
            codes = Counter(code for code, _ in opened)
            for _, response in opened:
                await response.aclose()
            await asyncio.sleep(0.2)  # the server sees the closes
            again = await http.send(http.build_request("GET", STREAM), stream=True)
            await again.aclose()
            return codes, again.status_code

    codes, again = asyncio.run(scenario())
    assert codes == Counter({200: MAX_CLIENTS, 429: 40 - MAX_CLIENTS})
    assert again == 200


def test_dropped_client_still_counts(writer: Writer, settings: Settings) -> None:
    """A slow client dropped from the fan-out keeps its slot until its connection ends."""
    stream = Stream(writer.engine, queue_size=1)

    async def scenario() -> tuple[int, int]:
        sub = stream.open()
        sub.queue.put_nowait("x")
        stream._publish("y")  # full: dropped from the fan-out
        held = stream.clients
        stream.close(sub)
        return held, stream.clients

    assert asyncio.run(scenario()) == (1, 0)
