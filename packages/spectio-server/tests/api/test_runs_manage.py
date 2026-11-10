"""Runs table actions (FU-P3-115a; api §5 note of 2026-11-10): delete, pin and sort."""

import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from spectio.config import Settings
from spectio.runner.rundir import make_run_dirs, run_paths
from spectio_server.api import runs_manage
from spectio_server.store.schema import launches, runs
from spectio_server.store.writer import Writer

from .conftest import add_run

RUNS = "/api/v1/runs"
T0 = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)


def rid(n: int) -> str:
    return f"run_01K8T2F1XTVRES000000000{n:03d}"


def delete(client: TestClient, ids: list[str], **body: Any) -> Any:
    return client.post(f"{RUNS}:delete", json={"ids": ids, **body})


def listed(client: TestClient, **params: Any) -> list[str]:
    return [r["id"] for r in client.get(RUNS, params=params).json()["items"]]


def deleted_at(writer: Writer, run_id: str) -> datetime | None:
    query = select(runs.c.deleted_at).where(runs.c.id == run_id)
    return writer.submit(lambda c: c.execute(query).scalar_one()).result()  # type: ignore[no-any-return]


# --- Delete ----------------------------------------------------------------------------------


def test_delete_forgets_ended_runs_and_keeps_files(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    for n, state in ((1, "succeeded"), (2, "failed"), (3, "cancelled"), (4, "running")):
        add_run(writer, settings, rid(n), f"r{n}", state)
    paths = make_run_dirs(settings.runs_root, rid(1))
    response = delete(authed_client, [rid(1), rid(2), rid(3)])
    assert response.status_code == 200, response.text
    assert response.json() == {"deleted": [rid(1), rid(2), rid(3)], "directories": []}
    assert listed(authed_client) == [rid(4)]
    assert authed_client.get(f"{RUNS}/{rid(1)}").status_code == 404
    summary = authed_client.get(f"{RUNS}:summary").json()["groups"]
    assert summary == [{"key": "running", "count": 1}]
    assert deleted_at(writer, rid(1)) is not None  # soft: the rebuild must not add it back
    assert paths.work_dir.is_dir()  # nothing on disk by default
    assert delete(authed_client, [rid(1)]).status_code == 404  # already deleted


def test_delete_refuses_a_run_not_ended(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, rid(1), "a", "succeeded")
    add_run(writer, settings, rid(2), "b", "running")
    add_run(writer, settings, rid(3), "c", "cancelling")
    response = delete(authed_client, [rid(1), rid(2), rid(3)])
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["type"] == "/problems/run-not-ended"
    assert [e["field"] for e in body["errors"]] == [rid(2), rid(3)]
    assert deleted_at(writer, rid(1)) is None  # all or nothing


@pytest.mark.parametrize(
    "body",
    [
        {"ids": []},
        {"ids": ["run_x"]},
        {"ids": [rid(1), rid(1)]},
        {"ids": [rid(n) for n in range(201)]},
        {"ids": [rid(1)], "extra": 1},
        {"ids": [rid(1)], "directories": "yes"},
    ],
)
def test_delete_body_is_checked(
    authed_client: TestClient, writer: Writer, settings: Settings, body: dict[str, Any]
) -> None:
    add_run(writer, settings, rid(1), "a", "succeeded")
    response = authed_client.post(f"{RUNS}:delete", json=body)
    assert response.status_code == 422, response.text
    assert deleted_at(writer, rid(1)) is None


def test_delete_unknown_is_404(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, rid(1), "a", "succeeded")
    response = delete(authed_client, [rid(1), rid(9)])
    assert response.status_code == 404, response.text
    assert deleted_at(writer, rid(1)) is None


def test_delete_is_a_guarded_write(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, rid(1), "a", "succeeded")
    evil = {"Origin": "https://evil.example"}
    assert (
        authed_client.post(f"{RUNS}:delete", json={"ids": [rid(1)]}, headers=evil).status_code
        == 403
    )
    signed_out = TestClient(authed_client.app, base_url=str(authed_client.base_url))
    signed_out.headers["Origin"] = authed_client.headers["Origin"]
    assert delete(signed_out, [rid(1)]).status_code == 401
    assert deleted_at(writer, rid(1)) is None


def test_delete_directories(
    authed_client: TestClient,
    writer: Writer,
    settings: Settings,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    add_run(writer, settings, rid(1), "a", "succeeded")
    add_run(writer, settings, rid(2), "b", "failed")
    paths = make_run_dirs(settings.runs_root, rid(1))
    outside = tmp_path / "precious"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    (paths.work_dir / "link").symlink_to(outside)  # removed as a link, never followed
    (paths.work_dir / "file.txt").write_text("x")
    with caplog.at_level(logging.INFO, logger=runs_manage.__name__):
        response = delete(authed_client, [rid(1), rid(2)], directories=True)
    assert response.status_code == 200, response.text
    assert response.json()["directories"] == [
        {"id": rid(1), "result": "removed"},
        {"id": rid(2), "result": "missing"},
    ]
    assert not paths.run_dir.exists()
    assert (outside / "keep.txt").read_text() == "keep"
    assert settings.runs_root.is_dir()
    assert rid(1) in caplog.text and "removed" in caplog.text  # audited in the server log


def test_delete_directory_symlink_is_not_followed(
    authed_client: TestClient, writer: Writer, settings: Settings, tmp_path: Path
) -> None:
    """A run directory replaced by a symlink is not removed, nor what it points to."""
    add_run(writer, settings, rid(1), "a", "succeeded")
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "keep.txt").write_text("keep")
    (settings.runs_root / rid(1)).symlink_to(target)
    response = delete(authed_client, [rid(1)], directories=True)
    assert response.status_code == 200, response.text
    assert response.json()["directories"] == [{"id": rid(1), "result": "failed"}]
    assert (target / "keep.txt").read_text() == "keep"
    assert (settings.runs_root / rid(1)).is_symlink()


def test_delete_directory_not_private_is_kept(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, rid(1), "a", "succeeded")
    paths = make_run_dirs(settings.runs_root, rid(1))
    os.chmod(paths.run_dir, 0o755)  # noqa: S103 - the loose directory under test
    response = delete(authed_client, [rid(1)], directories=True)
    assert response.json()["directories"] == [{"id": rid(1), "result": "failed"}]
    assert paths.work_dir.is_dir()


def test_delete_directories_refused_for_a_terminal_run(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, rid(1), "a", "succeeded", origin="cli-observed")
    response = delete(authed_client, [rid(1)], directories=True)
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["type"] == "/problems/directory-not-removable"
    assert body["errors"][0]["field"] == rid(1)
    assert deleted_at(writer, rid(1)) is None
    assert delete(authed_client, [rid(1)]).status_code == 200  # its records only: allowed


def test_delete_directories_refused_while_the_head_lives(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    """An ended run whose head is not reported exited still writes in its directory."""
    launch_id = add_run(writer, settings, rid(1), "a", "cancelled")
    writer.submit(
        lambda c: c.execute(
            update(launches).where(launches.c.id == launch_id).values(head_native_id="4242")
        )
    ).result()
    paths = make_run_dirs(settings.runs_root, rid(1))
    response = delete(authed_client, [rid(1)], directories=True)
    assert response.status_code == 409, response.text
    assert response.json()["errors"][0]["field"] == rid(1)
    assert paths.run_dir.is_dir()


def test_delete_directories_refused_when_not_recorded_there(
    authed_client: TestClient, writer: Writer, settings: Settings, tmp_path: Path
) -> None:
    """A launch directory recorded elsewhere (the runs root changed) is never removed."""
    add_run(writer, settings, rid(1), "a", "succeeded", launch_dir=str(tmp_path / "x" / "launch"))
    response = delete(authed_client, [rid(1)], directories=True)
    assert response.status_code == 409, response.text
    assert response.json()["type"] == "/problems/directory-not-removable"


def test_delete_directories_of_a_lineage_together(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    """A Resume's child runs in its parent's directories: delete them together or not at all."""
    add_run(writer, settings, rid(1), "parent", "failed")
    parent = run_paths(settings.runs_root, rid(1))
    add_run(
        writer,
        settings,
        rid(2),
        "child",
        "succeeded",
        parent_run_id=rid(1),
        lineage_id=rid(1),
        launch_dir=str(parent.launch_dir),
        work_dir=str(parent.work_dir),
    )
    make_run_dirs(settings.runs_root, rid(1))
    for alone in (rid(1), rid(2)):
        response = delete(authed_client, [alone], directories=True)
        assert response.status_code == 409, response.text
        assert response.json()["errors"][0]["field"] == alone
    response = delete(authed_client, [rid(2), rid(1)], directories=True)
    assert response.status_code == 200, response.text
    assert not parent.run_dir.exists()


def test_deleted_child_leaves_resumed_as(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, rid(1), "parent", "failed")
    add_run(writer, settings, rid(2), "child", "failed", parent_run_id=rid(1), lineage_id=rid(1))
    assert delete(authed_client, [rid(2)]).status_code == 200
    assert authed_client.get(f"{RUNS}/{rid(1)}").json()["resumed_as"] == []


def test_refuses_removal_without_symlink_safe_rmtree(
    authed_client: TestClient,
    writer: Writer,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    add_run(writer, settings, rid(1), "a", "succeeded")
    paths = make_run_dirs(settings.runs_root, rid(1))
    monkeypatch.setattr(runs_manage, "SAFE_RMTREE", False)
    response = delete(authed_client, [rid(1)], directories=True)
    assert response.json()["directories"] == [{"id": rid(1), "result": "failed"}]
    assert paths.run_dir.is_dir()


# --- Pin -------------------------------------------------------------------------------------


def test_pin(authed_client: TestClient, writer: Writer, settings: Settings) -> None:
    add_run(writer, settings, rid(1), "a", "running", created_at=T0)
    add_run(writer, settings, rid(2), "b", "running", created_at=T0 + timedelta(hours=1))
    assert listed(authed_client) == [rid(2), rid(1)]
    response = authed_client.patch(f"{RUNS}/{rid(1)}", json={"pinned": True})
    assert response.status_code == 200, response.text
    assert (response.json()["id"], response.json()["pinned"]) == (rid(1), True)
    assert listed(authed_client) == [rid(1), rid(2)]  # pinned first
    items = authed_client.get(RUNS).json()["items"]
    assert [r["pinned"] for r in items] == [True, False]
    assert authed_client.patch(f"{RUNS}/{rid(1)}", json={"pinned": False}).json()["pinned"] is False
    assert listed(authed_client) == [rid(2), rid(1)]


@pytest.mark.parametrize("body", [{}, {"pinned": "yes"}, {"pinned": True, "name": "x"}])
def test_pin_body_is_checked(
    authed_client: TestClient, writer: Writer, settings: Settings, body: dict[str, Any]
) -> None:
    add_run(writer, settings, rid(1), "a", "running")
    assert authed_client.patch(f"{RUNS}/{rid(1)}", json=body).status_code == 422


def test_pin_unknown_or_deleted_is_404(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, rid(1), "a", "succeeded")
    delete(authed_client, [rid(1)])
    assert authed_client.patch(f"{RUNS}/{rid(1)}", json={"pinned": True}).status_code == 404
    assert authed_client.patch(f"{RUNS}/{rid(9)}", json={"pinned": True}).status_code == 404


def test_pin_is_a_guarded_write(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, rid(1), "a", "running")
    evil = {"Origin": "https://evil.example"}
    response = authed_client.patch(f"{RUNS}/{rid(1)}", json={"pinned": True}, headers=evil)
    assert response.status_code == 403
    assert listed(authed_client)  # unchanged
    assert authed_client.get(RUNS).json()["items"][0]["pinned"] is False


# --- Sort ------------------------------------------------------------------------------------


@pytest.fixture
def four_runs(writer: Writer, settings: Settings) -> list[str]:
    """Created 1 → 4; names d, b, a, c; durations 30 min, 2 h, none (running), 10 min."""
    specs = (
        ("d", "succeeded", T0, T0 + timedelta(minutes=30)),
        ("b", "failed", T0 + timedelta(hours=1), T0 + timedelta(hours=3)),
        ("a", "running", None, None),
        ("c", "cancelled", T0 + timedelta(hours=2), T0 + timedelta(hours=2, minutes=10)),
    )
    for n, (name, state, started, ended) in enumerate(specs, 1):
        add_run(
            writer,
            settings,
            rid(n),
            name,
            state,
            created_at=T0 + timedelta(minutes=n),
            started_at=started,
            ended_at=ended,
        )
    return [rid(n) for n in range(1, 5)]


@pytest.mark.parametrize(
    ("sort", "order"),
    [
        ("-created_at", [4, 3, 2, 1]),
        ("name", [3, 2, 4, 1]),
        ("-name", [1, 4, 2, 3]),
        ("state", [4, 2, 3, 1]),
        ("-state", [1, 3, 2, 4]),
        ("started_at", [1, 3, 2, 4]),  # 3 not started: its creation, T0 + 3 min
        ("-started_at", [4, 2, 3, 1]),
        ("duration", [4, 1, 2, 3]),  # not ended: last
        ("-duration", [2, 1, 4, 3]),  # not ended: last too
    ],
)
def test_sort(authed_client: TestClient, four_runs: list[str], sort: str, order: list[int]) -> None:
    assert listed(authed_client, sort=sort) == [rid(n) for n in order]
    pages: list[str] = []
    cursor = None
    while True:  # one row a page: the cursor walks the same order
        params: dict[str, Any] = {"sort": sort, "limit": 1}
        if cursor:
            params["cursor"] = cursor
        body = authed_client.get(RUNS, params=params).json()
        pages += [r["id"] for r in body["items"]]
        cursor = body["next"]
        if cursor is None:
            break
    assert pages == [rid(n) for n in order]


def test_sort_pinned_first_with_paging(
    authed_client: TestClient, writer: Writer, settings: Settings, four_runs: list[str]
) -> None:
    authed_client.patch(f"{RUNS}/{rid(1)}", json={"pinned": True})
    assert listed(authed_client, sort="name") == [rid(1), rid(3), rid(2), rid(4)]
    first = authed_client.get(RUNS, params={"sort": "name", "limit": 2}).json()
    rest = authed_client.get(RUNS, params={"sort": "name", "cursor": first["next"]}).json()
    assert [r["id"] for r in first["items"] + rest["items"]] == [rid(1), rid(3), rid(2), rid(4)]
    # Home's "recently ended" stays by end time
    assert listed(authed_client, sort="-ended_at") == [rid(2), rid(4), rid(1)]


@pytest.mark.parametrize("sort", ["workflow", "origin", "-pinned", "name;drop"])
def test_sort_whitelist(authed_client: TestClient, sort: str) -> None:
    assert authed_client.get(RUNS, params={"sort": sort}).status_code == 422


def test_cursor_of_another_sort_is_422(authed_client: TestClient, four_runs: list[str]) -> None:
    first = authed_client.get(RUNS, params={"sort": "name", "limit": 1}).json()
    response = authed_client.get(RUNS, params={"sort": "duration", "cursor": first["next"]})
    assert response.status_code == 422
