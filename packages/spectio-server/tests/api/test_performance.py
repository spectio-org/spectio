"""`GET /runs/{id}/performance` (FU-P3-105d; api §5.5, schedulers §3.6 and §3.7): statistics
on read over the run's `attempt_metrics` rows, the caps and stride of the points,
`pending_accounting`, the waste lines and the cache of ended runs."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, insert, update

from spectio.config import Settings
from spectio_server import metrics
from spectio_server.api import performance
from spectio_server.store.schema import attempt_metrics, attempts, projects, runs, tasks
from spectio_server.store.writer import Writer

from .conftest import add_run

API = "/api/v1"
RUN = "run_01K8T2F1XTVRES0000000000P1"
T0 = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
SLURM_RUN = {  # `runs.environment` of a run launched on the built-in `slurm`
    "name": "slurm",
    "label": "SLURM (from spectio init)",
    "executor": "slurm",
    "slurm": {"partition": None, "account": None, "time_min": None, "mem_mib": None},
    "local": None,
    "state": "recorded",
}


def job(
    conn: Connection,
    run_id: str,
    n: int,
    process: str = "ALIGN",
    *,
    attempt: int = 1,
    state: str = "succeeded",
    native_id: str | None = None,
    **values: Any,
) -> None:
    """Task `n` of the run (created with its first attempt) and attempt `attempt`'s row."""
    task_id = f"tsk_{run_id[-2:]}{process}{n:05d}"
    if attempt == 1:
        conn.execute(
            insert(tasks).values(
                id=task_id,
                created_at=T0,
                run_id=run_id,
                process_or_rule=process,
                tag=f"S{n}",
                state=state,
            )
        )
    else:
        conn.execute(update(tasks).where(tasks.c.id == task_id).values(state=state))
    attempt_id = f"att_{task_id[4:]}_{attempt}"
    conn.execute(
        insert(attempts).values(
            id=attempt_id,
            created_at=T0 + timedelta(minutes=attempt),
            task_id=task_id,
            n=attempt,
            launch_n=1,
            state=state,
            native_id=native_id,
        )
    )
    row = {
        "attempt_id": attempt_id,
        "run_id": run_id,
        "task_id": task_id,
        "attempt": attempt,
        "tag": f"S{n}",
        "process_or_rule": process,
        "engine": "nextflow",
        "project_id": "prj_default",
        "run_state": "succeeded",
        "state": state,
        "source": "trace",
        **values,
    }
    conn.execute(insert(attempt_metrics).values(**row))


def cached_task(conn: Connection, run_id: str, n: int, process: str = "ALIGN") -> None:
    conn.execute(
        insert(tasks).values(
            id=f"tsk_{run_id[-2:]}c{n:05d}",
            created_at=T0,
            run_id=run_id,
            process_or_rule=process,
            tag=f"C{n}",
            state="cached",
        )
    )


def make(writer: Writer, settings: Settings, *rows: dict[str, Any], **run: Any) -> None:
    add_run(writer, settings, RUN, "perf", run.pop("state", "succeeded"), **run)

    def write(conn: Connection) -> None:
        for i, r in enumerate(rows):
            job(conn, RUN, r.pop("n", i), **r)

    writer.submit(write).result()


def perf(client: TestClient, query: str = "", run_id: str = RUN) -> dict[str, Any]:
    found = client.get(f"{API}/runs/{run_id}/performance{query}")
    assert found.status_code == 200, found.text
    return found.json()  # type: ignore[no-any-return]


def test_statistics_are_hand_computed(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    """Quartiles by linear interpolation between the closest ranks (numpy's default): over
    1, 2, 4, 7 the positions 0.75, 1.5 and 2.25 give 1.75, 3 and 4.75."""
    make(
        writer,
        settings,
        {"cpu_eff": 0.4, "mem_eff": 0.5},
        {"cpu_eff": 0.1, "mem_eff": 0.5},
        {"cpu_eff": 0.7, "mem_eff": None},
        {"cpu_eff": 0.2, "mem_eff": None, "cpus": 4},
    )
    found = perf(authed_client, "?metrics=cpu_eff,mem_eff")
    assert (found["run_id"], found["total"], found["measured"]) == (RUN, 4, 4)
    (align,) = found["processes"]
    assert align["process_or_rule"] == "ALIGN"
    assert (align["n"], align["measured"], align["jobs"]) == (4, 4, {"done": 4, "total": 4})
    assert align["stats"]["cpu_eff"] == {
        "n": 4,
        "min": 0.1,
        "q1": 0.175,
        "median": 0.3,
        "q3": 0.475,
        "max": 0.7,
        "mean": 0.35,
        "min_task": {"task_id": f"tsk_{RUN[-2:]}ALIGN00001", "tag": "S1"},
        "max_task": {"task_id": f"tsk_{RUN[-2:]}ALIGN00002", "tag": "S2"},
    }
    assert align["stats"]["mem_eff"]["n"] == 2  # a null is not measured
    assert align["stats"]["mem_eff"]["min_task"]["tag"] == "S0"  # the first of equal values
    assert align["sources"] == {"trace": 4}
    assert align["requested"] == {
        "cpus": 4,
        "mem_bytes": None,
        "time_limit_s": None,
        "varies": False,
    }
    assert set(found["points"]["items"][0]) == {
        "task_id",
        "attempt",
        "process_or_rule",
        "tag",
        "partition",
        "source",
        "cpu_eff",
        "mem_eff",
    }


def test_a_metric_with_no_value_has_null_stats(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    make(writer, settings, {"cpu_eff": 0.5})
    (only,) = perf(authed_client, "?metrics=wait_s")["processes"]
    assert only["stats"] == {"wait_s": None}


def test_last_attempt_by_default_every_attempt_on_request(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    make(
        writer,
        settings,
        {"n": 0, "mem_eff": 0.1, "state": "failed"},
        {"n": 1, "mem_eff": 0.9},
    )
    writer.submit(lambda c: job(c, RUN, 0, attempt=2, mem_eff=0.5)).result()
    last = perf(authed_client, "?metrics=mem_eff")
    assert last["total"] == 2
    assert last["processes"][0]["stats"]["mem_eff"]["min"] == 0.5
    every = perf(authed_client, "?metrics=mem_eff&attempts=all")
    assert every["total"] == 3
    assert every["processes"][0]["stats"]["mem_eff"]["min"] == 0.1
    assert [(p["tag"], p["attempt"]) for p in every["points"]["items"]] == [
        ("S0", 1),
        ("S0", 2),
        ("S1", 1),
    ]


def test_points_are_capped_with_one_stride_and_stats_use_every_row(
    authed_client: TestClient, writer: Writer, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(performance, "POINTS_PER_PROCESS", 3)
    monkeypatch.setattr(performance, "POINTS_PER_ANSWER", 4)
    rows = [{"process": "A", "n": i, "cpu_eff": i / 10} for i in range(7)]
    rows += [{"process": "B", "n": i, "cpu_eff": 0.5} for i in range(3)]
    make(writer, settings, *rows)
    found = perf(authed_client)
    points = found["points"]
    # stride 3 gives 3 + 1 points; stride 2 would give 4 + 2, past the answer's cap
    assert (points["truncated"], points["stride"]) == (True, 3)
    assert [(p["process_or_rule"], p["tag"]) for p in points["items"]] == [
        ("A", "S0"),
        ("A", "S3"),
        ("A", "S6"),
        ("B", "S0"),
    ]
    a = next(p for p in found["processes"] if p["process_or_rule"] == "A")
    assert (a["stats"]["cpu_eff"]["n"], a["stats"]["cpu_eff"]["max"]) == (7, 0.6)


def test_under_the_caps_every_point_and_stride_one(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    make(writer, settings, {"cpu_eff": 0.5}, {"cpu_eff": 0.6})
    points = perf(authed_client)["points"]
    assert (len(points["items"]), points["truncated"], points["stride"]) == (2, False, 1)
    assert perf(authed_client, "?points=false")["points"] is None


def test_more_processes_than_the_cap(
    authed_client: TestClient, writer: Writer, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(performance, "MAX_PROCESSES", 1)
    make(writer, settings, {"process": "FIRST", "cpu_eff": 0.5}, {"process": "SECOND"})
    found = perf(authed_client)
    assert found["processes_truncated"] is True
    assert [p["process_or_rule"] for p in found["processes"]] == ["FIRST"]
    assert {p["process_or_rule"] for p in found["points"]["items"]} == {"FIRST"}


def test_process_filter(authed_client: TestClient, writer: Writer, settings: Settings) -> None:
    make(writer, settings, {"process": "A"}, {"process": "B"}, {"process": "C"})
    found = perf(authed_client, "?process=C&process=A&process=NONE")
    assert [p["process_or_rule"] for p in found["processes"]] == ["A", "C"]
    assert [p["pipeline_order"] for p in found["processes"]] == [0, 2]


def test_cached_tasks_are_counted_apart(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    make(writer, settings, {"cpu_eff": 0.5})
    writer.submit(lambda c: cached_task(c, RUN, 1)).result()
    found = perf(authed_client)
    assert (found["total"], found["cached"]) == (1, 1)
    assert found["processes"][0]["jobs"] == {"done": 2, "total": 2}


def test_waste_lines_from_three_jobs(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    rows = [{"process": "A", "mem_eff": 0.1, "cpu_eff": 0.9} for _ in range(3)]
    rows += [{"process": "B", "mem_eff": 0.1, "cpu_eff": 0.1} for _ in range(2)]
    rows += [{"process": "B", "mem_eff": 0.3, "cpu_eff": 0.24}]
    for i, r in enumerate(rows):
        r["n"] = i
    make(writer, settings, *rows)
    found = {p["process_or_rule"]: p["waste"] for p in perf(authed_client)["processes"]}
    assert found == {
        "A": [{"metric": "mem_eff", "below": 0.25, "jobs": 3}],
        "B": [{"metric": "cpu_eff", "below": 0.25, "jobs": 3}],
    }


def test_pending_accounting_counts_slurm_jobs_sacct_has_not_answered(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    make(
        writer,
        settings,
        {"native_id": "101"},
        {"native_id": "102", "source": "sacct"},
        {"native_id": None},  # no job ID: never asked
        environment=SLURM_RUN,
    )
    authed_client.app.state.accounting.enabled = True  # type: ignore[attr-defined]
    assert perf(authed_client)["pending_accounting"] == 1
    now = datetime.now(UTC)
    writer.submit(
        lambda c: c.execute(update(runs).where(runs.c.id == RUN).values(metrics_sacct_at=now))
    ).result()
    assert perf(authed_client)["pending_accounting"] == 0  # the sweep or the fill is done


def test_no_pending_accounting_with_accounting_off(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    make(writer, settings, {"native_id": "101"}, environment=SLURM_RUN)
    authed_client.app.state.accounting.enabled = False  # type: ignore[attr-defined]
    assert perf(authed_client)["pending_accounting"] == 0  # `accounting = false`, or no sacct


def test_a_local_run_has_no_pending_accounting(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    make(writer, settings, {"native_id": "4242"})
    assert perf(authed_client)["pending_accounting"] == 0


def test_a_run_with_no_rows(authed_client: TestClient, writer: Writer, settings: Settings) -> None:
    add_run(writer, settings, RUN, "empty", "running")
    found = perf(authed_client)
    assert found == {
        "run_id": RUN,
        "measured": 0,
        "total": 0,
        "cached": 0,
        "pending_accounting": 0,
        "processes_truncated": False,
        "processes": [],
        "points": {"items": [], "truncated": False, "stride": 1},
    }


def test_a_deleted_or_unknown_run_is_not_found(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    make(writer, settings, {"cpu_eff": 0.5})
    writer.submit(
        lambda c: c.execute(
            update(runs).where(runs.c.id == RUN).values(deleted_at=datetime.now(UTC))
        )
    ).result()
    for run_id in (RUN, "run_01K8T2F1XTVRES0000000000ZZ", "not-a-run"):
        found = authed_client.get(f"{API}/runs/{run_id}/performance")
        assert found.status_code == 404
        assert found.json()["type"] == "/problems/not-found"


def test_perf_tenancy_another_projects_run_reads_as_get_run_does(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    """0.0.2 is single-user: the run routes have no project scoping (the session is the
    check); this route reads the run's rows by run ID, as `GET /runs/{id}` reads the run."""
    make(writer, settings, {"cpu_eff": 0.5})

    def move(conn: Connection) -> None:
        conn.execute(insert(projects).values(id="prj_other", created_at=T0, owning_group_id="g"))
        conn.execute(update(runs).where(runs.c.id == RUN).values(project_id="prj_other"))

    writer.submit(move).result()
    assert authed_client.get(f"{API}/runs/{RUN}").status_code == 200
    assert perf(authed_client)["total"] == 1


def test_no_session_is_401(writer: Writer, settings: Settings) -> None:
    from .conftest import client_for

    anonymous = client_for(settings, writer, signed_in=False)
    assert anonymous.get(f"{API}/runs/{RUN}/performance").status_code == 401


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("?metrics=owner_id", "metrics"),
        ("?metrics=cpu_eff)--", "metrics"),
        ("?metrics=cpu_eff,mem_eff,wait_s,time_eff,realtime_s", "metrics"),
        ("?" + "&".join(f"process=P{i}" for i in range(21)), "process"),
        ("?process=" + "x" * 257, "process"),
        ("?attempts=first", "attempts"),
    ],
)
def test_refused_inputs(
    authed_client: TestClient, writer: Writer, settings: Settings, query: str, field: str
) -> None:
    make(writer, settings, {"cpu_eff": 0.5})
    found = authed_client.get(f"{API}/runs/{RUN}/performance{query}")
    assert found.status_code == 422
    assert found.json()["type"] == "/problems/validation-failed"
    assert found.json()["errors"][0]["field"] == field


def test_an_ended_run_is_cached_until_its_metrics_change(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    make(writer, settings, {"cpu_eff": 0.5})
    key = attempt_metrics.c.run_id == RUN
    first = perf(authed_client)
    writer.submit(
        lambda c: c.execute(update(attempt_metrics).where(key).values(cpu_eff=0.9))
    ).result()
    assert perf(authed_client) == first  # cached: no change was noted

    attempt_id = f"att_{RUN[-2:]}ALIGN00000_1"
    bench = {"s": "10", "cpu_time": "5", "max_rss": "1"}
    assert writer.submit(lambda c: metrics._apply_benchmark(c, attempt_id, bench)).result()
    found = perf(authed_client)
    assert found["points"]["items"][0]["source"] == "benchmark"  # dropped by the benchmark


def test_an_ended_run_is_dropped_from_the_cache_by_the_sweep(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    make(writer, settings, {"cpu_eff": 0.5})
    perf(authed_client)
    now = datetime.now(UTC)

    def swept(conn: Connection) -> None:
        conn.execute(update(attempt_metrics).values(cpu_eff=0.9))
        conn.execute(update(runs).where(runs.c.id == RUN).values(metrics_sacct_at=now))

    writer.submit(swept).result()
    assert perf(authed_client)["points"]["items"][0]["cpu_eff"] == 0.9


def test_a_live_run_is_not_cached(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    make(writer, settings, {"cpu_eff": 0.5}, state="running")
    perf(authed_client)
    writer.submit(lambda c: c.execute(update(attempt_metrics).values(cpu_eff=0.9))).result()
    assert perf(authed_client)["points"]["items"][0]["cpu_eff"] == 0.9


def test_the_cache_is_bounded() -> None:
    cache = performance.Cache(entries=2, points=10)
    for n in range(3):
        cache.put(("r", n), (0, None), {"n": n}, 1)
    assert cache.get(("r", 0), (0, None)) is None
    assert cache.get(("r", 2), (0, None)) == {"n": 2}
    cache.put(("big",), (0, None), {}, 11)  # larger than the whole cache: not kept
    assert cache.get(("big",), (0, None)) is None
    cache.put(("r", 3), (0, None), {}, 9)  # 1 + 9 fits; ("r", 1) is dropped first
    assert cache.get(("r", 1), (0, None)) is None


def test_a_change_during_a_read_is_not_cached() -> None:
    cache = performance.Cache()
    stamp = cache.stamp("run_a")
    cache.changed({"run_a": set()})  # committed while the answer was being computed
    cache.put(("run_a",), stamp, {"old": True}, 1)
    assert cache.get(("run_a",), cache.stamp("run_a")) is None


def test_a_forgotten_run_never_gets_a_stamp_back() -> None:
    cache = performance.Cache(runs=1)
    stamp = cache.stamp("run_a")
    cache.changed({"run_a": set()})
    cache.changed({"run_b": set()})  # run_a is forgotten
    assert cache.stamp("run_a") != stamp
