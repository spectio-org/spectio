"""The read API and the run logs (P1 Task 18; api §5 notes of 2026-10-28, §7; arch §13.7)."""

import base64
import json
import os
import socket
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from spectio.config import Settings
from spectio.runner.rundir import make_run_dirs, run_paths
from spectio_server.app import NO_API
from spectio_server.store.schema import launches
from spectio_server.store.writer import Writer

from .conftest import add_run

RUNS = "/api/v1/runs"
T0 = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)
FLAKY_PROCESSES = [
    "MAKE_READS",
    "QC_STATS",
    "SPLIT",
    "ALIGN",
    "QC_REPORT",
    "MERGE",
    "COMPARE",
    "FINAL_REPORT",
]


def rid(n: int) -> str:
    return f"run_01K8T2F1XTVRES0000000001{n:02d}"


def three_runs(writer: Writer, settings: Settings) -> list[str]:
    """rnaseq-a running, rnaseq-b queued, sarek-c failed; created a minute apart, in that order."""
    ids = [rid(1), rid(2), rid(3)]
    add_run(writer, settings, ids[0], "rnaseq-a", "running", created_at=T0)
    add_run(writer, settings, ids[1], "rnaseq-b", "queued", created_at=T0 + timedelta(minutes=1))
    add_run(
        writer,
        settings,
        ids[2],
        "sarek-c",
        "failed",
        created_at=T0 + timedelta(minutes=2),
        ended_at=T0 + timedelta(minutes=3),
    )
    return ids


def problem(response: object, status: int, slug: str) -> dict[str, object]:
    assert response.status_code == status, response.text  # type: ignore[attr-defined]
    body = response.json()  # type: ignore[attr-defined]
    assert body["type"] == f"/problems/{slug}"
    return body  # type: ignore[no-any-return]


# --- Runs ------------------------------------------------------------------------------------


def test_run_detail_after_replay(authed_client: TestClient, replayed_flaky: str) -> None:
    response = authed_client.get(f"{RUNS}/{replayed_flaky}")
    assert response.status_code == 200, response.text
    run = response.json()
    assert (run["id"], run["name"], run["state"]) == (replayed_flaky, "rnaseq-flaky", "succeeded")
    assert run["task_counts"] == {"succeeded": 65}
    assert run["summary"]["tasks"] == {"done": 65, "total": 65, "failed": 0, "cached": 0}
    assert run["head"] is None  # no head report in a replay
    assert run["params"] == {"reads": 4}
    assert run["started_at"] is not None and run["ended_at"] is not None
    processes = authed_client.get(f"{RUNS}/{replayed_flaky}/processes").json()["items"]
    assert [p["process"] for p in processes] == FLAKY_PROCESSES
    assert sum(p["retries"] for p in processes) == 2  # two tasks retried once
    assert all(set(p) == {"process", "stage_id", "counts", "retries"} for p in processes)


def test_runs_paging(authed_client: TestClient, writer: Writer, settings: Settings) -> None:
    ids = three_runs(writer, settings)
    first = authed_client.get(RUNS, params={"limit": 2}).json()
    assert [r["id"] for r in first["items"]] == [ids[2], ids[1]]  # newest first
    assert first["next"]
    assert "params" not in first["items"][0]
    second = authed_client.get(RUNS, params={"limit": 2, "cursor": first["next"]}).json()
    assert [r["id"] for r in second["items"]] == [ids[0]]
    assert second["next"] is None
    problem(authed_client.get(RUNS, params={"cursor": "garbage"}), 422, "validation-failed")
    problem(authed_client.get(RUNS, params={"limit": 201}), 422, "validation-failed")


def test_runs_filter_state_and_q(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    ids = three_runs(writer, settings)
    found = authed_client.get(RUNS, params={"state": "running,queued"}).json()["items"]
    assert [r["id"] for r in found] == [ids[1], ids[0]]
    found = authed_client.get(RUNS, params={"q": "rnaseq"}).json()["items"]
    assert [r["name"] for r in found] == ["rnaseq-b", "rnaseq-a"]
    assert authed_client.get(RUNS, params={"q": "%"}).json()["items"] == []  # no LIKE pattern
    body = problem(
        authed_client.get(RUNS, params={"state": "running,lost"}), 422, "validation-failed"
    )
    assert body["errors"][0]["field"] == "state"  # type: ignore[index]


def test_runs_summary_by_state(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, rid(1), "a", "running")
    add_run(writer, settings, rid(2), "b", "running")
    add_run(writer, settings, rid(3), "c", "failed")
    body = authed_client.get(f"{RUNS}:summary", params={"group_by": "state"}).json()
    assert sorted(body["groups"], key=lambda g: g["key"]) == [
        {"key": "failed", "count": 1},
        {"key": "running", "count": 2},
    ]
    problem(
        authed_client.get(f"{RUNS}:summary", params={"group_by": "x"}), 422, "validation-failed"
    )


def test_version_behind_session(
    client: TestClient, authed_client: TestClient, settings: Settings
) -> None:
    """TODO(P1 Task 16): with no session cookie → 401. Until sign-in is built, the API is not
    mounted on a shared machine, and other sites and hosts are refused (inbox #86, #87)."""
    absent = problem(client.get("/api/v1/version"), 404, "not-found")
    assert NO_API in str(absent["detail"])
    problem(
        authed_client.get("/api/v1/version", headers={"Host": "evil.example"}),
        400,
        "host-not-allowed",
    )
    cross = {"Sec-Fetch-Site": "cross-site"}
    problem(authed_client.get("/api/v1/version", headers=cross), 403, "cross-site")
    body = authed_client.get("/api/v1/version").json()
    assert body == {
        "version": version("spectio"),
        "node": socket.gethostname(),
        "runs_root": str(settings.runs_root),
        "account": body["account"],
        "executor": "local",
    }
    assert body["account"]


def test_runs_sort_ended(authed_client: TestClient, writer: Writer, settings: Settings) -> None:
    add_run(writer, settings, rid(1), "a", "succeeded", ended_at=T0 + timedelta(hours=2))
    add_run(writer, settings, rid(2), "b", "running")
    add_run(writer, settings, rid(3), "c", "failed", ended_at=T0 + timedelta(hours=1))
    found = authed_client.get(RUNS, params={"sort": "-ended_at", "limit": 1}).json()
    assert [r["id"] for r in found["items"]] == [rid(1)]
    rest = authed_client.get(RUNS, params={"sort": "-ended_at", "cursor": found["next"]}).json()
    assert [r["id"] for r in rest["items"]] == [rid(3)]  # no run that has not ended
    problem(authed_client.get(RUNS, params={"sort": "name"}), 422, "validation-failed")


def test_stages_ordered(authed_client: TestClient, seeded_stages: str) -> None:
    items = authed_client.get(f"{RUNS}/{seeded_stages}/stages").json()["items"]
    assert [(s["id"], s["position"], s["state"]) for s in items] == [
        ("detected:1", 1, "running"),
        ("align", 2, "not_started"),
    ]
    assert items[0] == {
        "id": "detected:1",
        "position": 1,
        "name": "Quality control",
        "source": "detected",
        "state": "running",
        "task_counts": {"running": 1},
    }


def test_stages_empty(authed_client: TestClient, replayed_flaky: str) -> None:
    assert authed_client.get(f"{RUNS}/{replayed_flaky}/stages").json() == {"items": []}
    processes = authed_client.get(f"{RUNS}/{replayed_flaky}/processes").json()["items"]
    assert {p["stage_id"] for p in processes} == {None}


def test_stages_source(authed_client: TestClient, seeded_stages: str) -> None:
    items = authed_client.get(f"{RUNS}/{seeded_stages}/stages").json()["items"]
    assert {s["source"] for s in items} == {"declared", "detected"}
    processes = authed_client.get(f"{RUNS}/{seeded_stages}/processes").json()["items"]
    assert [(p["process"], p["stage_id"]) for p in processes] == [
        ("NFCORE_RNASEQ:RNASEQ:FASTQC", "detected:1"),
        ("NFCORE_RNASEQ:RNASEQ:ALIGN:STAR", "align"),
        ("NFCORE_RNASEQ:RNASEQ:MULTIQC", None),
    ]
    assert processes[0]["counts"] == {"running": 1}


def test_run_versions_and_origin(
    authed_client: TestClient, replayed_flaky: str, writer: Writer, settings: Settings
) -> None:
    run = authed_client.get(f"{RUNS}/{replayed_flaky}").json()
    assert run["origin"] == "ui"
    assert run["workflow"] == {
        "engine": "nextflow",
        "engine_version": "26.10.4",  # pinned from the start event
        "location": "/pipelines/nextflow",
        "name": "lab/nextflow",
        "version": "1.2.0",  # the manifest version read at launch
    }
    add_run(writer, settings, rid(9), "smk", "queued", engine="snakemake")
    smk = authed_client.get(f"{RUNS}/{rid(9)}").json()["workflow"]
    assert (smk["engine"], smk["version"], smk["engine_version"]) == ("snakemake", None, None)


def test_queued_run_head_null(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    launch_id = add_run(writer, settings, rid(1), "q", "queued")
    run = authed_client.get(f"{RUNS}/{rid(1)}").json()
    assert (run["state"], run["head"]) == ("queued", None)
    writer.submit(
        lambda c: c.execute(
            update(launches)
            .where(launches.c.id == launch_id)
            .values(head_native_id="4242", head_state="running")
        )
    ).result()
    head = authed_client.get(f"{RUNS}/{rid(1)}").json()["head"]
    assert head == {
        "session": "4242",
        "node": socket.gethostname(),
        "alive": True,
        "exit_code": None,
    }


def test_run_unknown_404(authed_client: TestClient) -> None:
    for path in (rid(7), f"{rid(7)}/processes", f"{rid(7)}/stages", f"{rid(7)}/tasks", "nope"):
        problem(authed_client.get(f"{RUNS}/{path}"), 404, "not-found")


def test_tasks_filter_and_paging(authed_client: TestClient, seeded_stages: str) -> None:
    url = f"{RUNS}/{seeded_stages}/tasks"
    first = authed_client.get(url, params={"limit": 2}).json()
    assert [t["process"] for t in first["items"]] == [
        "NFCORE_RNASEQ:RNASEQ:FASTQC",
        "NFCORE_RNASEQ:RNASEQ:ALIGN:STAR",
    ]
    rest = authed_client.get(url, params={"limit": 2, "cursor": first["next"]}).json()
    assert [t["id"] for t in rest["items"]] == ["tsk_02"] and rest["next"] is None
    running = authed_client.get(url, params={"state": "running"}).json()["items"]
    assert [t["id"] for t in running] == ["tsk_00"]
    star = authed_client.get(url, params={"process": "NFCORE_RNASEQ:RNASEQ:ALIGN:STAR"}).json()
    assert [t["id"] for t in star["items"]] == ["tsk_01"]
    assert set(running[0]) == {"id", "process", "tag", "name", "state", "stage_id"}


def test_task_cursor_is_one_id(authed_client: TestClient, seeded_stages: str) -> None:
    """A task's ID is its sort key: the cursor carries it once (CR-P3T18-05)."""
    first = authed_client.get(f"{RUNS}/{seeded_stages}/tasks", params={"limit": 1}).json()
    raw = base64.urlsafe_b64decode(first["next"] + "=" * (-len(first["next"]) % 4))
    assert json.loads(raw) == first["items"][0]["id"]


# --- Logs ------------------------------------------------------------------------------------


def launch_dir(settings: Settings, run_id: str) -> Path:
    make_run_dirs(settings.runs_root, run_id)
    return run_paths(settings.runs_root, run_id).launch_dir


def test_logs_tail_and_sources(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, rid(1), "nf", "running")
    add_run(writer, settings, rid(2), "smk", "running", engine="snakemake")
    nf = launch_dir(settings, rid(1))
    head = bytes(range(256)) * 400  # 100 KiB
    (nf / ".spectio" / "head.out").write_bytes(head)
    (nf / ".spectio" / "head.err").write_text("err\n")
    (nf / ".nextflow.log").write_text("nextflow log\n")
    smk = launch_dir(settings, rid(2))
    (smk / ".snakemake" / "log").mkdir(parents=True)
    old, new = (
        smk / ".snakemake" / "log" / "a.snakemake.log",
        smk / ".snakemake" / "log" / "b.snakemake.log",
    )
    old.write_text("old\n")
    new.write_text("new\n")
    os.utime(old, (1, 1))

    out = authed_client.get(f"{RUNS}/{rid(1)}/logs", params={"source": "head-out"})
    assert out.status_code == 200, out.text
    assert out.headers["content-type"] == "text/plain; charset=utf-8"
    assert out.headers["x-content-type-options"] == "nosniff"
    assert out.content == head[-65536:].decode("utf-8", "replace").encode()
    assert authed_client.get(f"{RUNS}/{rid(1)}/logs", params={"source": "head-err"}).text == "err\n"
    assert (
        authed_client.get(f"{RUNS}/{rid(1)}/logs", params={"source": "engine"}).text
        == "nextflow log\n"
    )
    assert authed_client.get(f"{RUNS}/{rid(2)}/logs", params={"source": "engine"}).text == "new\n"
    problem(
        authed_client.get(f"{RUNS}/{rid(2)}/logs", params={"source": "head-out"}),
        404,
        "log-not-found",
    )
    problem(
        authed_client.get(f"{RUNS}/{rid(1)}/logs", params={"source": "x"}), 422, "validation-failed"
    )


def test_logs_confined(
    authed_client: TestClient, tmp_path: Path, writer: Writer, settings: Settings
) -> None:
    """A symlink is never followed, in or out of the launch directory (checking-scenarios §11.1)."""
    add_run(writer, settings, rid(1), "nf", "running")
    add_run(writer, settings, rid(2), "smk", "running", engine="snakemake")
    nf = launch_dir(settings, rid(1))
    (nf / ".nextflow.log").symlink_to("/etc/passwd")
    (nf / ".spectio" / "head.out").symlink_to(nf / ".spectio" / "run.json")  # in the tree
    smk = launch_dir(settings, rid(2))
    secrets = tmp_path / "secrets"
    (secrets / "log").mkdir(parents=True)
    (secrets / "log" / "x.snakemake.log").write_text("root:x:0:0\n")
    (smk / ".snakemake").symlink_to(secrets)
    for run_id, source in ((rid(1), "engine"), (rid(1), "head-out"), (rid(2), "engine")):
        response = authed_client.get(f"{RUNS}/{run_id}/logs", params={"source": source})
        problem(response, 404, "log-not-found")
        assert "root:" not in response.text
    fifo = nf / ".spectio" / "head.err"
    os.mkfifo(fifo)
    problem(
        authed_client.get(f"{RUNS}/{rid(1)}/logs", params={"source": "head-err"}),
        404,
        "log-not-found",
    )


@pytest.mark.parametrize("bad", ["%00", "a" * 300])
def test_logs_bad_run_id(authed_client: TestClient, bad: str) -> None:
    problem(authed_client.get(f"{RUNS}/{bad}/logs", params={"source": "engine"}), 404, "not-found")


@pytest.mark.parametrize("value", [["2026-10-30T08:00:00", "run_x"], [1, 2], {"a": 1}, "x"])
def test_forged_cursor_is_422(authed_client: TestClient, value: object) -> None:
    """A cursor is opaque: one this server did not give is a 422, never a 500."""
    cursor = base64.urlsafe_b64encode(json.dumps(value).encode()).decode()
    problem(authed_client.get(RUNS, params={"cursor": cursor}), 422, "validation-failed")
