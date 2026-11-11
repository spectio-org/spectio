"""The across-runs routes (FU-P3-105e; api §5.5): `GET /performance:summary`,
`/performance/attempts` and `/performance/facets`. They read `attempt_metrics` only, of the
caller's projects only; input maps and caps, the row-count check and the time budget, the
`429` limits, `tz=`, `totals` and paging; the query plan of each filter on SQLite."""

import re
import sqlite3
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, insert, select, text, update

from spectio.config import Settings
from spectio_server.api import performance, performance_across
from spectio_server.auth.middleware import cookie_name
from spectio_server.store.schema import (
    attempt_metrics,
    environments,
    principals,
    projects,
    runs,
)
from spectio_server.store.writer import Writer

from .conftest import add_run
from .test_performance import job

API = "/api/v1"
ROUTES = ("/performance:summary", "/performance/attempts", "/performance/facets")
T0 = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
LATER = datetime(2099, 1, 1, tzinfo=UTC)
WINDOW = {"since": "2026-11-01T00:00:00Z", "until": "2026-11-12T00:00:00Z"}
RA, RB = "run_01K8T2F1XTVRES0000000000PA", "run_01K8T2F1XTVRES0000000000PB"
RC = "run_01K8T2F1XTVRES0000000000PC"
SUMMARY_ONLY = ("metrics", "group_by", "tz")


def rows(writer: Writer, run_id: str, *specs: dict[str, Any]) -> None:
    """Attempt rows of `run_id`, with its project and environment as 105a writes them."""

    def write(conn: Connection) -> None:
        run = conn.execute(
            select(runs.c.project_id, runs.c.environment_id).where(runs.c.id == run_id)
        ).one()
        for i, spec in enumerate(specs):
            values = {
                "project_id": run.project_id,
                "environment_id": run.environment_id,
                "pipeline": "lab/nextflow",
                "ended_at": T0 + timedelta(minutes=i),
                **spec,
            }
            job(conn, run_id, values.pop("n", i), values.pop("process", "ALIGN"), **values)

    writer.submit(write).result()


def stranger(conn: Connection, project: bool = True) -> None:
    """Another user, and a project of their group; newer than the server's own rows, which
    0.0.2 takes as the oldest (`store.runs.first`)."""
    mine = {"created_at": LATER, "created_by": "usr_THEIRS"}
    conn.execute(insert(principals).values(id="usr_THEIRS", kind="user", **mine))
    if project:
        conn.execute(
            insert(projects).values(
                id="prj_THEIRS", owning_group_id="grp_THEIRS", name="theirs", **mine
            )
        )


def two_runs(writer: Writer, settings: Settings) -> None:
    add_run(writer, settings, RA, "first", "succeeded")
    add_run(writer, settings, RB, "second", "succeeded")
    rows(writer, RA, {"cpu_eff": 0.2}, {"cpu_eff": 0.4}, {"process": "SORT", "cpu_eff": 0.9})
    rows(writer, RB, {"cpu_eff": 0.6, "partition": "gpu"}, {"cpu_eff": None})


def get(client: TestClient, path: str, **params: Any) -> dict[str, Any]:
    found = client.get(API + path, params={**WINDOW, **params})
    assert found.status_code == 200, found.text
    return found.json()  # type: ignore[no-any-return]


def refused(client: TestClient, path: str, status: int = 422, **params: Any) -> dict[str, Any]:
    found = client.get(API + path, params={**WINDOW, **params})
    assert found.status_code == status, found.text
    return found.json()  # type: ignore[no-any-return]


def test_summary_by_process(authed_client: TestClient, writer: Writer, settings: Settings) -> None:
    two_runs(writer, settings)
    found = get(authed_client, "/performance:summary", group_by="process")
    assert found["totals"] == {"jobs": 5, "runs": 2}
    assert found["scanned"] == 5 and found["truncated"] is False
    align, sort = found["groups"]  # largest n first
    assert align["key"] == {"process_or_rule": "ALIGN"}
    assert (align["n"], align["runs"]) == (4, 2)
    stats = align["stats"]["cpu_eff"]
    assert (stats["n"], stats["min"], stats["median"], stats["max"]) == (3, 0.2, 0.4, 0.6)
    assert stats["min_task"]["tag"] == "S0"
    assert sort["key"] == {"process_or_rule": "SORT"} and sort["n"] == 1


def test_summary_filters_and_two_keys(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    two_runs(writer, settings)
    found = get(authed_client, "/performance:summary", group_by="partition,run", partition="gpu")
    assert [g["key"] for g in found["groups"]] == [{"partition": "gpu", "run_id": RB}]
    assert get(authed_client, "/performance:summary", process="NONE")["groups"] == []
    assert get(authed_client, "/performance:summary", engine="snakemake")["totals"]["jobs"] == 0
    assert get(authed_client, "/performance:summary", environment="local")["totals"]["jobs"] == 5


def test_summary_periods_in_tz(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    """23:30 UTC on 9 November is 10 November in Paris: the day boundaries follow `tz=`."""
    add_run(writer, settings, RA, "first", "succeeded")
    late = datetime(2026, 11, 9, 23, 30, tzinfo=UTC)
    rows(writer, RA, {"ended_at": late, "cpu_eff": 0.5}, {"ended_at": T0, "cpu_eff": 0.7})
    utc = get(authed_client, "/performance:summary", group_by="day")
    assert [g["key"]["period_start"] for g in utc["groups"]] == [
        "2026-11-09T00:00:00+00:00",
        "2026-11-10T00:00:00+00:00",
    ]
    paris = get(authed_client, "/performance:summary", group_by="day", tz="Europe/Paris")
    assert [(g["key"]["period_start"], g["n"]) for g in paris["groups"]] == [
        ("2026-11-10T00:00:00+01:00", 2)
    ]
    week = get(authed_client, "/performance:summary", group_by="week")
    assert [g["key"]["period_start"] for g in week["groups"]] == ["2026-11-09T00:00:00+00:00"]
    refused(authed_client, "/performance:summary", group_by="hour")  # 11 days: over 48 h
    hours = {"since": "2026-11-10T00:00:00Z", "until": "2026-11-11T00:00:00Z"}
    found = authed_client.get(f"{API}/performance:summary", params={"group_by": "hour", **hours})
    assert [g["key"]["period_start"] for g in found.json()["groups"]] == [
        "2026-11-10T08:00:00+00:00"
    ]


def test_summary_caps_groups(authed_client: TestClient, writer: Writer, settings: Settings) -> None:
    add_run(writer, settings, RA, "first", "succeeded")
    many = [{"process": f"P{i:03d}", "cpu_eff": 0.5} for i in range(501)]
    rows(writer, RA, *many, {"process": "P250", "n": 999, "cpu_eff": 0.1})
    found = get(authed_client, "/performance:summary", group_by="process")
    assert found["truncated"] is True and len(found["groups"]) == 500
    assert found["groups"][0]["key"] == {"process_or_rule": "P250"}  # n 2, first


def test_attempts_last_or_all(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, RA, "first", "succeeded")
    rows(
        writer,
        RA,
        {"n": 1, "state": "failed", "cpu_eff": 0.1},
        {"n": 1, "attempt": 2, "cpu_eff": 0.8},
    )
    assert get(authed_client, "/performance:summary", state="all")["totals"]["jobs"] == 1
    every = get(authed_client, "/performance:summary", state="all", attempts="all")
    assert every["totals"]["jobs"] == 2
    assert get(authed_client, "/performance:summary", state="failed")["totals"]["jobs"] == 0


def test_attempts_pages(authed_client: TestClient, writer: Writer, settings: Settings) -> None:
    two_runs(writer, settings)
    seen, cursor = [], None
    while True:
        page = get(
            authed_client,
            "/performance/attempts",
            limit=2,
            **({"cursor": cursor} if cursor else {}),
        )
        seen += page["items"]
        if (cursor := page["next"]) is None:
            break
    assert len(seen) == 5
    ended = [i["ended_at"] for i in seen]
    assert ended == sorted(ended, reverse=True)  # -ended_at by default
    first = seen[0]
    assert first["run_name"] == "first" and first["tag"] == "S2"
    assert "owner_id" not in first and "environment_id" not in first
    by_cpu = get(authed_client, "/performance/attempts", sort="cpu_eff", limit=4)
    assert [i["cpu_eff"] for i in by_cpu["items"]] == [0.2, 0.4, 0.6, 0.9]
    last = get(authed_client, "/performance/attempts", sort="cpu_eff", cursor=by_cpu["next"])
    assert [i["cpu_eff"] for i in last["items"]] == [None]  # nulls last
    refused(authed_client, "/performance/attempts", cursor="bm90IGEgY3Vyc29y")


def test_facets_each_without_its_own(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    two_runs(writer, settings)
    found = get(authed_client, "/performance/facets", process="SORT")
    assert found["process_or_rule"] == ["ALIGN", "SORT"]  # its own filter apart
    assert found["partition"] == []  # SORT ran with no partition
    assert found["pipeline"] == ["lab/nextflow"] and found["engine"] == ["nextflow"]
    (env,) = found["environment"]
    assert env["name"] == "local" and env["id"].startswith("env_")
    assert found["truncated"] == []


def test_environment_of_another_group_is_not_named(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    add_run(writer, settings, RA, "first", "succeeded")

    def theirs(conn: Connection) -> None:
        stranger(conn, project=False)
        conn.execute(
            insert(environments).values(
                id="env_THEIRS", owning_group_id="grp_THEIRS", name="gpu", kind="slurm",
                created_at=LATER, created_by="usr_THEIRS",
            )
        )  # fmt: skip

    writer.submit(theirs).result()
    rows(writer, RA, {"environment_id": "env_THEIRS"})
    found = get(authed_client, "/performance/facets")
    assert found["environment"] == [{"id": "env_THEIRS", "name": "another environment"}]
    assert get(authed_client, "/performance:summary", environment="gpu")["totals"]["jobs"] == 0


def test_nothing_matches(authed_client: TestClient) -> None:
    assert get(authed_client, "/performance:summary")["groups"] == []
    assert get(authed_client, "/performance/attempts") == {"items": [], "next": None}
    assert get(authed_client, "/performance/facets")["process_or_rule"] == []
    assert authed_client.get(f"{API}/performance:summary").status_code == 200  # range=30d


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"metrics": "owner_id"}, "metrics"),
        ({"metrics": "cpu_eff) or 1=1 --"}, "metrics"),
        ({"metrics": "cpu_eff,mem_eff,wait_s,realtime_s,time_eff"}, "metrics"),
        ({"group_by": "owner_id"}, "group_by"),
        ({"group_by": "process,day,run"}, "group_by"),
        ({"process": [f"p{i}" for i in range(21)]}, "process"),
        ({"partition": "x" * 257}, "partition"),
        ({"state": "running"}, "state"),
        ({"user": "root"}, "user"),
        ({"tz": "../../etc/passwd"}, "tz"),
        ({"since": "2026-11-01T00:00:00", "until": "2026-11-12T00:00:00Z"}, "since"),
        ({"since": "2026-11-12T00:00:00Z", "until": "2026-11-01T00:00:00Z"}, "until"),
        ({"since": "2025-11-01T00:00:00Z", "until": "2026-11-12T00:00:00Z"}, "until"),
    ],
)
def test_input_checks(authed_client: TestClient, params: dict[str, Any], field: str) -> None:
    for path in ROUTES[:1] if field in SUMMARY_ONLY else ROUTES:
        found = refused(authed_client, path, **params)
        assert found["type"] == "/problems/validation-failed"
        assert found["errors"][0]["field"] == field, (path, found)


def test_sort_is_a_fixed_map(authed_client: TestClient) -> None:
    found = refused(authed_client, "/performance/attempts", sort="-run_id")
    assert found["errors"][0]["field"] == "sort"


# --- Who may read (api §5.5, §6) -------------------------------------------------------------


def test_perf_tenancy_another_project(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    """A project of another group is not the caller's: its rows count nowhere."""
    two_runs(writer, settings)
    add_run(writer, settings, RC, "theirs", "succeeded")

    def theirs(conn: Connection) -> None:
        stranger(conn)
        conn.execute(update(runs).where(runs.c.id == RC).values(project_id="prj_THEIRS"))

    writer.submit(theirs).result()
    rows(writer, RC, {"process": "SECRET", "partition": "hidden"})
    assert get(authed_client, "/performance:summary")["totals"] == {"jobs": 5, "runs": 2}
    facets = get(authed_client, "/performance/facets")
    assert "SECRET" not in facets["process_or_rule"] and "hidden" not in facets["partition"]
    items = get(authed_client, "/performance/attempts", limit=200)["items"]
    assert {i["run_id"] for i in items} == {RA, RB}


def test_perf_tenancy_moved_run(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    """A run moved to another group's project (api §4: the rows move in the same transaction)
    leaves the caller's answers, and comes back with the move back."""
    two_runs(writer, settings)
    mine = writer.submit(lambda c: c.execute(select(runs.c.project_id)).scalars().first()).result()

    def move(conn: Connection, to: str) -> None:
        if to == "prj_THEIRS":
            stranger(conn)
        conn.execute(update(runs).where(runs.c.id == RB).values(project_id=to))
        am = attempt_metrics.c
        conn.execute(update(attempt_metrics).where(am.run_id == RB).values(project_id=to))

    writer.submit(lambda c: move(c, "prj_THEIRS")).result()
    found = get(authed_client, "/performance:summary", group_by="run")
    assert [g["key"]["run_id"] for g in found["groups"]] == [RA]
    writer.submit(lambda c: move(c, str(mine))).result()
    assert get(authed_client, "/performance:summary")["totals"] == {"jobs": 5, "runs": 2}


def test_perf_tenancy_deleted_run(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    two_runs(writer, settings)
    deleted = authed_client.post(f"{API}/runs:delete", json={"ids": [RB]})
    assert deleted.status_code == 200, deleted.text
    assert get(authed_client, "/performance:summary")["totals"] == {"jobs": 3, "runs": 1}
    items = get(authed_client, "/performance/attempts")["items"]
    assert {i["run_id"] for i in items} == {RA}
    assert get(authed_client, "/performance/facets")["partition"] == []


def test_perf_tenancy_share_link(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    """0.0.2 has no share-link or embed session: a request with anything but the session
    cookie (a share token in the query, a bearer header) is `401`, before any row is read."""
    two_runs(writer, settings)
    authed_client.cookies.clear()
    for path in ROUTES:
        found = authed_client.get(
            API + path, params={"share": "shr_x"}, headers={"Authorization": "Bearer spk_x"}
        )
        assert found.status_code == 401, (path, found.text)
        assert "groups" not in found.json() and "items" not in found.json()


# --- Load (api §5.5) -------------------------------------------------------------------------


def test_three_concurrent_queries_give_one_429(
    authed_client: TestClient, writer: Writer, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At most one query per principal (in 0.0.2 a signed-in session stands for it) and two
    per server: of three sessions' concurrent queries, one is `429` with `Retry-After`."""
    two_runs(writer, settings)
    inside, release = threading.Semaphore(0), threading.Event()
    real = performance_across.count

    def slow(*args: Any) -> int:
        inside.release()
        release.wait(10)
        return real(*args)

    monkeypatch.setattr(performance_across, "count", slow)
    app = authed_client.app
    clients = []
    for _ in range(3):
        c = TestClient(
            app, base_url=str(authed_client.base_url), headers=dict(authed_client.headers)
        )
        name = cookie_name(f"127.0.0.1:{settings.port}")
        c.cookies.set(name, app.state.sessions.create())  # type: ignore[attr-defined]
        clients.append(c)
    answers: list[Any] = []

    def hold(c: TestClient) -> threading.Thread:
        thread = threading.Thread(
            target=lambda: answers.append(c.get(f"{API}/performance:summary"))
        )
        thread.start()
        assert inside.acquire(timeout=10)
        return thread

    first = hold(clients[0])
    again = clients[0].get(f"{API}/performance/attempts")  # one per principal
    second = hold(clients[1])
    third = clients[2].get(f"{API}/performance/facets")  # two per server
    release.set()
    for thread in (first, second):
        thread.join(10)
    assert again.status_code == 429 and again.json()["type"] == "/problems/rate-limited"
    assert third.status_code == 429 and third.headers["Retry-After"].isdigit()
    assert sorted(a.status_code for a in answers) == [200, 200]
    assert clients[2].get(f"{API}/performance/facets").status_code == 200  # freed


BIG = 1_200_000
UNUSED_BY_THE_COUNTS = (  # the counts search (project_id, ended_at) and (run_id) only
    "ix_attempt_metrics_project_process",
    "ix_attempt_metrics_project_pipeline",
    "ix_attempt_metrics_project_partition",
    "ix_attempt_metrics_project_pipeline_ended",
)


def test_1_2_million_rows_answer_422_within_the_budget(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    """1,200,000 rows in the range (one run): the row-count check answers `422 range-too-wide`
    with the count on all four routes, within the time budget, before any row is read."""
    add_run(writer, settings, RA, "big", "succeeded")
    project = writer.submit(lambda c: c.execute(select(runs.c.project_id)).scalar()).result()
    assert settings.db_dir is not None
    raw = sqlite3.connect(str(writer.engine.url.database))
    try:  # the rows only, no tasks or attempts: nothing past the count reads them
        raw.execute("PRAGMA foreign_keys=OFF")
        for index in UNUSED_BY_THE_COUNTS:  # a smaller file, written faster
            raw.execute(f"DROP INDEX {index}")
        for chunk in range(0, BIG, BIG // 6):  # the WAL kept small: a checkpoint per chunk
            with raw:
                raw.execute(
                    "WITH RECURSIVE i(n) AS (SELECT ? UNION ALL SELECT n + 1 FROM i WHERE n < ?)"
                    " INSERT INTO attempt_metrics (attempt_id, run_id, task_id, attempt,"
                    " process_or_rule, project_id, run_state, state, ended_at)"
                    " SELECT printf('a%07d', n), ?, 't', 1, 'ALIGN', ?, 'succeeded', 'succeeded',"
                    " strftime('%Y-%m-%d %H:%M:%S', '2026-11-05', printf('+%d seconds', n / 4))"
                    " || '.000000' FROM i",
                    (chunk, chunk + BIG // 6 - 1, RA, project),
                )
            raw.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        raw.close()
    stored = writer.submit(lambda c: c.execute(select(attempt_metrics.c.ended_at)).first()).result()
    assert stored is not None and stored[0].tzinfo is not None  # the column type reads them
    for path in (*ROUTES, f"/runs/{RA}/performance"):
        start = time.monotonic()
        found = authed_client.get(API + path, params=WINDOW if "runs/" not in path else {})
        took = time.monotonic() - start
        assert found.status_code == 422, (path, found.text)
        assert found.json()["type"] == "/problems/range-too-wide"
        assert found.json()["count"] == BIG
        assert took < performance.BUDGET_S, (path, took)


# --- Query plans (api §5.5: every filter on an index) ----------------------------------------


@pytest.mark.parametrize(
    ("filters", "index"),
    [
        ({}, "ix_attempt_metrics_project_ended"),
        ({"process": ["ALIGN"]}, "ix_attempt_metrics_project_process"),
        ({"pipeline": ["lab/nextflow"]}, "ix_attempt_metrics_project_pipeline_ended"),
        (
            {"pipeline": ["lab/nextflow"], "process": ["ALIGN"]},
            "ix_attempt_metrics_project_pipeline",
        ),
        ({"partition": ["cpu"]}, "ix_attempt_metrics_project_partition"),
        ({"pipeline_version": ["1"], "engine": ["nextflow"]}, "ix_attempt_metrics_project_ended"),
        (
            {"environment_id": ["env_x"], "run_state": ["failed"]},
            "ix_attempt_metrics_project_ended",
        ),
        ({"state": "failed", "owner_id": "usr_x"}, "ix_attempt_metrics_project_ended"),
    ],
)
def test_each_filter_uses_an_index(writer: Writer, filters: dict[str, Any], index: str) -> None:
    """The count runs on the filter's index; every route's statement searches an index of
    105a, never a full scan of the table."""
    across = performance_across
    f = across.Filters(since=T0 - timedelta(days=1), until=T0, **filters)
    visible = ["prj_a", "prj_b"]
    statements = [
        across.count_query(f, visible),
        across.summary_query(f, visible, ["process", "day"], ["cpu_eff"]),
        across.attempts_query(f, visible, "-ended_at", None, 50)[0],
        across.attempts_query(f, visible, "cpu_eff", None, 50)[0],
        *(across.facet_query(f, visible, name) for name in across.FACETS),
    ]
    for n, statement in enumerate(statements):
        compiled = statement.compile(writer.engine, compile_kwargs={"literal_binds": True})
        with writer.engine.connect() as conn:
            plan = " | ".join(r[-1] for r in conn.execute(text(f"EXPLAIN QUERY PLAN {compiled}")))
        main = plan.split(" | ")[0]
        assert re.search(
            r"SEARCH attempt_metrics USING (COVERING )?INDEX ix_attempt_metrics_project", plan
        ), plan
        assert not re.search(r"SCAN attempt_metrics(?! USING)", plan), plan
        if n == 0:
            assert f"INDEX {index} (" in main, plan
