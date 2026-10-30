"""`POST /runs/{id}:cancel` (P1 Task 18; api §5.1, §7.1) and the runner's `cancel` command."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from spectio.config import Settings
from spectio.runner import loop as loop_mod
from spectio.runner.engines import EngineInfo
from spectio.runner.loop import RunnerLoop
from spectio.runner.types import HeadReport, LaunchRef, LaunchSpec
from spectio_server.sink import StoreSink
from spectio_server.store.runs import first as first_row
from spectio_server.store.schema import events, principals, runner_commands, runs
from spectio_server.store.writer import Writer

from .conftest import add_run

RUN = "run_01K8T2F1XTVRES000000000201"


def cancel(client: TestClient, run_id: str = RUN, **kwargs: Any) -> Any:
    return client.post(f"/api/v1/runs/{run_id}:cancel", **kwargs)


def commands(writer: Writer) -> list[Any]:
    return writer.submit(lambda c: list(c.execute(select(runner_commands)).all())).result()


def test_cancel_states(authed_client: TestClient, writer: Writer, settings: Settings) -> None:
    add_run(writer, settings, RUN, "q", "queued")
    first = cancel(authed_client)
    assert first.status_code == 202, first.text
    assert (first.json()["id"], first.json()["state"]) == (RUN, "cancelling")
    (command,) = commands(writer)
    assert (command.kind, command.state, command.run_id) == ("cancel", "pending", RUN)
    again = cancel(authed_client)
    assert (again.status_code, again.json()["state"]) == (200, "cancelling")
    assert len(commands(writer)) == 1  # idempotent: no second command
    changes = writer.submit(
        lambda c: list(
            c.execute(
                select(events.c.payload).where(events.c.type == "spectio.run.state_changed")
            ).scalars()
        )
    ).result()
    assert changes == [{"from": "queued", "to": "cancelling"}]
    actor = writer.submit(
        lambda c: (
            c.execute(
                select(events.c.source, events.c.actor_kind, events.c.actor_principal_id).where(
                    events.c.type == "spectio.run.state_changed"
                )
            ).one(),
            first_row(c, principals),
        )
    ).result()
    assert actor[0] == ("api", "person", actor[1])  # who cancelled (SEC-P3T18-01)

    done = "run_01K8T2F1XTVRES000000000202"
    add_run(writer, settings, done, "c", "cancelled")
    unchanged = cancel(authed_client, done)
    assert (unchanged.status_code, unchanged.json()["state"]) == (200, "cancelled")
    assert cancel(authed_client, "run_01K8T2F1XTVRES000000000299").status_code == 404


def test_cancel_cli_observed_not_in_this_version(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, RUN, "cli", "running", origin="cli-observed")
    response = cancel(authed_client)
    assert response.status_code == 422, response.text
    assert response.json()["type"] == "/problems/not-in-this-version"
    assert commands(writer) == []


def test_cancel_is_a_write(authed_client: TestClient, writer: Writer, settings: Settings) -> None:
    """A cancel needs the loopback Origin (dev-env §15.3 req. 7): no other site cancels a run."""
    add_run(writer, settings, RUN, "q", "queued")
    assert cancel(authed_client, headers={"Origin": "https://evil.example"}).status_code == 403
    assert cancel(authed_client, headers={"Origin": ""}).status_code == 403
    assert commands(writer) == []


class SignalRecorder:
    """A launcher that starts nothing, and checks the cancel marker at each signal."""

    def __init__(self, marker: Path) -> None:
        self.marker = marker
        self.signalled: list[tuple[str, bool]] = []

    def submit(self, spec: LaunchSpec) -> str:
        return "4242"

    def adopt(self, launch: LaunchRef) -> HeadReport:
        raise AssertionError("not adopted in this test")

    def poll(self, ids: list[str]) -> dict[str, HeadReport]:
        return {}

    def cancel(self, native_id: str, grace_s: int = 60) -> None:
        self.signalled.append((native_id, self.marker.is_file()))

    def forget(self, ids: Iterable[str]) -> None:
        pass


def test_cancel_reaches_the_runner(
    authed_client: TestClient,
    writer: Writer,
    settings: Settings,
    synthetic: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The run's `cancel` command takes the path of P1 Task 9: `.spectio/cancel` first, then
    the launcher's signal."""
    launched = authed_client.post(
        "/api/v1/runs",
        json={"workflow": {"location": str(synthetic / "nextflow"), "engine": "nextflow"}},
    )
    assert launched.status_code == 201, launched.text
    run_id = launched.json()["id"]
    assert cancel(authed_client, run_id).status_code == 202
    monkeypatch.setattr(loop_mod, "check_engine", lambda e, cmd: EngineInfo("nextflow", "26.10.4"))
    launcher = SignalRecorder(settings.runs_root / run_id / "launch" / ".spectio" / "cancel")
    loop = RunnerLoop(StoreSink(writer, settings.runs_root), launcher, settings, end_grace_s=0)
    loop.tick()
    assert launcher.signalled == [("4242", True)]
    assert {c.kind: c.state for c in commands(writer)} == {"launch": "done", "cancel": "done"}
    state = writer.submit(
        lambda c: c.execute(select(runs.c.state).where(runs.c.id == run_id)).scalar_one()
    ).result()
    assert state == "cancelling"  # cancelled once the head is reported ended
