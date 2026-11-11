"""`GET /me/notifications` and `POST /me/notifications:mark-read` in 0.0.1 (FU-P3-113, api §5.9).

A notification is derived from the run records: a run that succeeded, failed or was cancelled,
or waits at a gate (`awaiting_review`), newest first, at most 50. The unread count is the items
newer than the principal's `notifications_read_at`, which `mark-read` moves forward.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from spectio.config import Settings
from spectio_server.store.writer import Writer

from .conftest import add_run, client_for

LIST = "/api/v1/me/notifications"
MARK = "/api/v1/me/notifications:mark-read"
T0 = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)


def _id(n: int) -> str:
    return f"run_01K8T2F1XTVRES{n:012d}"


def _ended(writer: Writer, settings: Settings, n: int, state: str, minutes: int) -> str:
    at = T0 + timedelta(minutes=minutes)
    add_run(writer, settings, _id(n), f"run-{n}", state, created_at=T0, state_changed_at=at)
    return _id(n)


def test_derived_from_ended_and_waiting_runs_newest_first(
    authed_client: TestClient, settings: Settings, writer: Writer
) -> None:
    _ended(writer, settings, 1, "succeeded", 1)
    _ended(writer, settings, 2, "failed", 3)
    _ended(writer, settings, 3, "cancelled", 2)
    _ended(writer, settings, 4, "awaiting_review", 4)
    _ended(writer, settings, 5, "running", 5)  # no notification
    add_run(writer, settings, _id(6), "deleted", "succeeded", deleted_at=T0)  # no notification
    answer = authed_client.get(LIST)
    assert answer.status_code == 200
    assert answer.headers["cache-control"] == "no-store"
    body = answer.json()
    assert [(i["run_id"], i["kind"]) for i in body["items"]] == [
        (_id(4), "gate_waiting"),
        (_id(2), "run_failed"),
        (_id(3), "run_cancelled"),
        (_id(1), "run_succeeded"),
    ]
    first = body["items"][0]
    assert first == {
        "id": f"gate_waiting:{_id(4)}",
        "kind": "gate_waiting",
        "run_id": _id(4),
        "run_name": "run-4",
        "engine": "nextflow",
        "at": (T0 + timedelta(minutes=4)).isoformat(),
        "read": False,
    }
    assert body["unread"] == 4 and body["read_up_to"] is None


def test_at_most_50_and_after(
    authed_client: TestClient, settings: Settings, writer: Writer
) -> None:
    for n in range(55):
        _ended(writer, settings, n, "succeeded", n)
    body = authed_client.get(LIST).json()
    assert len(body["items"]) == 50
    assert body["items"][0]["run_id"] == _id(54) and body["items"][-1]["run_id"] == _id(5)
    assert body["unread"] == 55  # every unread item, not only those shown
    after = (T0 + timedelta(minutes=52)).isoformat()
    newer = authed_client.get(LIST, params={"after": after}).json()
    assert [i["run_id"] for i in newer["items"]] == [_id(54), _id(53)]
    assert authed_client.get(LIST, params={"after": "2026-11-10T09:00:00"}).status_code == 422


def test_mark_read_moves_the_mark_forward_only(
    authed_client: TestClient, settings: Settings, writer: Writer
) -> None:
    for n in range(3):
        _ended(writer, settings, n, "failed", n)
    up_to = (T0 + timedelta(minutes=1)).isoformat()
    answer = authed_client.post(MARK, json={"up_to": up_to})
    assert answer.status_code == 200
    body = answer.json()
    assert body["unread"] == 1 and body["read_up_to"] == up_to
    assert [i["read"] for i in body["items"]] == [False, True, True]
    assert authed_client.get(LIST).json()["unread"] == 1  # kept server-side
    older = authed_client.post(MARK, json={"up_to": T0.isoformat()}).json()
    assert older["read_up_to"] == up_to  # never backwards
    _ended(writer, settings, 9, "succeeded", 10)
    assert authed_client.get(LIST).json()["unread"] == 2


def test_an_ended_run_is_at_its_end_and_names_its_engine(
    authed_client: TestClient, settings: Settings, writer: Writer
) -> None:
    """Amended 2026-11-11 (api §5.9): an ended run is at `ended_at`, else `state_changed_at`, so
    runs adopted together keep their own times; `gate_waiting` keeps `state_changed_at`."""
    adopted = T0 + timedelta(hours=1)  # when Spectio adopted the runs below
    for n, minutes in ((1, 5), (2, 20)):
        add_run(
            writer,
            settings,
            _id(n),
            f"run-{n}",
            "succeeded",
            engine="snakemake",
            created_at=T0,
            state_changed_at=adopted,
            ended_at=T0 + timedelta(minutes=minutes),
        )
    _ended(writer, settings, 3, "failed", 10)  # no ended_at: its state_changed_at
    add_run(
        writer,
        settings,
        _id(4),
        "run-4",
        "awaiting_review",
        created_at=T0,
        state_changed_at=T0 + timedelta(minutes=15),
        ended_at=T0 + timedelta(minutes=30),
    )
    body = authed_client.get(LIST).json()
    assert [(i["run_id"], i["engine"], i["at"]) for i in body["items"]] == [
        (_id(2), "snakemake", (T0 + timedelta(minutes=20)).isoformat()),
        (_id(4), "nextflow", (T0 + timedelta(minutes=15)).isoformat()),
        (_id(3), "nextflow", (T0 + timedelta(minutes=10)).isoformat()),
        (_id(1), "snakemake", (T0 + timedelta(minutes=5)).isoformat()),
    ]
    after = (T0 + timedelta(minutes=12)).isoformat()
    assert [
        i["run_id"] for i in authed_client.get(LIST, params={"after": after}).json()["items"]
    ] == [_id(2), _id(4)]
    # Side effect of the watermark: a run adopted after the mark that ended before it reads read.
    marked = authed_client.post(MARK, json={"up_to": (T0 + timedelta(minutes=12)).isoformat()})
    body = marked.json()
    assert [i["read"] for i in body["items"]] == [False, False, True, True]
    assert body["unread"] == 2


def test_mark_read_refuses_a_bad_body(authed_client: TestClient) -> None:
    assert authed_client.post(MARK, json={}).status_code == 422
    assert authed_client.post(MARK, json={"up_to": "yesterday"}).status_code == 422
    assert authed_client.post(MARK, json={"up_to": T0.isoformat(), "x": 1}).status_code == 422


def test_needs_the_session_and_the_origin(
    authed_client: TestClient, settings: Settings, writer: Writer
) -> None:
    anon = client_for(settings, writer, signed_in=False)
    assert anon.get(LIST).status_code == 401
    assert anon.post(MARK, json={"up_to": T0.isoformat()}).status_code == 401
    refused = authed_client.post(MARK, json={"up_to": T0.isoformat()}, headers={"Origin": ""})
    assert refused.status_code == 403
