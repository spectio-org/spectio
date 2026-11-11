"""The across-runs performance routes (FU-P3-105e; api §5.5 owns them, schedulers §3.7 what
each column means): `GET /performance:summary`, `/performance/attempts` and
`/performance/facets`.

They read `attempt_metrics` only, never `sacct`, a file, the runner or the engine. Who may
read: the session, Host and Origin middleware, as every route (0.0.2 has no token, share-link
or embed session); every query, the row-count check included, keeps the rows of
`visible_projects`: in single-user mode the projects of the groups whose projects the one user
created (`ensure_tenancy`'s `personal`). Load: at most one query per principal (a session
stands for it in 0.0.2) and two per server at a time (`Gate`, else `429 rate-limited`); the
row count first, over 1,000,000 `422 range-too-wide`; every statement under the per-run
route's time budget (`performance.budget`). The statistics are `performance.stats`.
"""

import functools
import heapq
import re
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from itertools import groupby
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, available_timezones

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import Connection, Row, Select, func, select

from spectio_server.api import models
from spectio_server.api.performance import _chosen, _filter, budget, stats, too_wide
from spectio_server.api.problems import Invalid, Problem
from spectio_server.api.runs_read import Cursor, Limit, _cursor_of, _iso, _keyset, read
from spectio_server.auth.middleware import cookie_name
from spectio_server.failure import _last_attempt
from spectio_server.store.runs import first
from spectio_server.store.schema import attempt_metrics, environments, principals, projects, runs

router = APIRouter()
am = attempt_metrics.c

RANGES = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
RANGES["90d"] = timedelta(days=90)
MAX_DAYS, MAX_GROUPS, MAX_SCANNED, MAX_FACET = 366, 500, 1_000_000, 500  # inbox #139, 6a
MAX_HOURLY = timedelta(hours=48)
PER_PRINCIPAL, PER_SERVER, RETRY_AFTER_S = 1, 2, 5
ANOTHER = "another environment"
USER_ID = re.compile(r"usr_[0-9A-Z]{26}")  # `ids.new_id`

# The fixed maps from wire names to columns (api §5.5, Input checks)
GROUPS = {
    "process": ("process_or_rule", am.process_or_rule),
    "partition": ("partition", am.partition),
    "pipeline": ("pipeline", am.pipeline),
    "run": ("run_id", am.run_id),
}
PERIODS = ("hour", "day", "week")
FILTERS = {
    "pipeline": am.pipeline,
    "pipeline_version": am.pipeline_version,
    "process": am.process_or_rule,
    "partition": am.partition,
    "environment_id": am.environment_id,
    "engine": am.engine,
    "run_state": am.run_state,
}
SORTS = {  # a null sorts last: coalesced past every value
    "-ended_at": (am.ended_at, True, "time"),
    "cpu_eff": (func.coalesce(am.cpu_eff, 1e308), False, "number"),
    "mem_eff": (func.coalesce(am.mem_eff, 1e308), False, "number"),
    "-peak_rss_bytes": (func.coalesce(am.peak_rss_bytes, -1e308), True, "number"),
    "-realtime_s": (func.coalesce(am.realtime_s, -1e308), True, "number"),
    "-wait_s": (func.coalesce(am.wait_s, -1e308), True, "number"),
}
FACETS = {  # the answer's name: the filter it leaves out, the column
    "pipeline": ("pipeline", am.pipeline),
    "pipeline_version": ("pipeline_version", am.pipeline_version),
    "process_or_rule": ("process", am.process_or_rule),
    "partition": ("partition", am.partition),
    "environment": ("environment_id", am.environment_id),
    "engine": ("engine", am.engine),
}
HIDDEN = ("owner_id", "project_id", "environment_id")  # never in an answer
ITEM = [c for c in attempt_metrics.c if c.name not in HIDDEN]


@dataclass(frozen=True)
class Filters:
    """The filters on `ended_at` and the rows' identity; None is no filter."""

    since: datetime
    until: datetime
    pipeline: tuple[str, ...] | None = None
    pipeline_version: tuple[str, ...] | None = None
    process: tuple[str, ...] | None = None
    partition: tuple[str, ...] | None = None
    environment_id: tuple[str, ...] | None = None
    engine: tuple[str, ...] | None = None
    run_state: tuple[str, ...] | None = None
    state: str = "succeeded"
    owner_id: str | None = None
    attempts: str = "last"


@dataclass
class Tally:
    jobs: int = 0
    groups: int = 0
    runs: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class Asked:
    filters: Filters
    environment: tuple[str, ...] | None  # names, read into `environment_id` with the caller
    user: str | None


class Gate:
    """At most `each` queries per principal and `total` per server at a time (api §5.5)."""

    def __init__(self, each: int = PER_PRINCIPAL, total: int = PER_SERVER) -> None:
        self.each, self.total = each, total
        self._lock = threading.Lock()
        self._busy: dict[str, int] = {}

    @contextmanager
    def slot(self, who: str) -> Iterator[None]:
        with self._lock:
            if sum(self._busy.values()) >= self.total or self._busy.get(who, 0) >= self.each:
                raise Problem(
                    429,
                    "rate-limited",
                    "Too many queries",
                    f"At most {self.each} performance query per user and {self.total} per"
                    " server at a time.",
                    headers={"Retry-After": str(RETRY_AFTER_S)},
                )
            self._busy[who] = self._busy.get(who, 0) + 1
        try:
            yield
        finally:
            with self._lock:
                self._busy[who] -= 1
                if not self._busy[who]:
                    del self._busy[who]


def _time(value: str | None, field: str) -> datetime | None:
    if value is None:
        return None
    try:
        at = datetime.fromisoformat(value)
    except ValueError:
        raise Invalid(field, "not an ISO 8601 date-time") from None
    if at.utcoffset() is None:
        raise Invalid(field, "an explicit offset is needed, such as Z or +01:00")
    return at


def asked(
    range_: Annotated[Literal["24h", "7d", "30d", "90d"], Query(alias="range")] = "30d",
    since: Annotated[str | None, Query(max_length=64)] = None,
    until: Annotated[str | None, Query(max_length=64)] = None,
    pipeline: Annotated[list[str] | None, Query()] = None,
    pipeline_version: Annotated[list[str] | None, Query()] = None,
    process: Annotated[list[str] | None, Query()] = None,
    partition: Annotated[list[str] | None, Query()] = None,
    environment: Annotated[list[str] | None, Query()] = None,
    engine: Annotated[list[Literal["nextflow", "snakemake"]] | None, Query()] = None,
    run_state: Annotated[list[models.RunState] | None, Query()] = None,
    state: Literal["succeeded", "failed", "all"] = "succeeded",
    user: Annotated[str | None, Query(max_length=64)] = None,
    attempts: Literal["last", "all"] = "last",
) -> Asked:
    """The filters every across-runs route takes: `until` defaults to now, `since` to `until`
    less `range`."""
    end = _time(until, "until") or datetime.now(UTC)
    start = _time(since, "since") or end - RANGES[range_]
    if start >= end:
        raise Invalid("until", "must be after since")
    if end - start > timedelta(days=MAX_DAYS):
        raise Invalid("until", f"at most {MAX_DAYS} days after since")
    if user not in (None, "me") and not USER_ID.fullmatch(user or ""):
        raise Invalid("user", "me or a usr_ ID")
    lists: dict[str, Sequence[str] | None] = {
        "pipeline": pipeline,
        "pipeline_version": pipeline_version,
        "process": process,
        "partition": partition,
        "engine": engine,
        "run_state": run_state,
    }
    found = {name: _filter(values, name) for name, values in lists.items()}
    filters = Filters(start, end, state=state, attempts=attempts, **found)  # type: ignore[arg-type]
    return Asked(filters, _filter(environment, "environment"), user)


Query_ = Annotated[Asked, Depends(asked)]


def where(f: Filters, visible: list[str], without: str | None = None) -> list[Any]:
    """The conditions of `f` (all but `without`'s) on the caller's projects, each on a
    column the five indexes of 105a lead with or a residual filter on their rows."""
    found = [am.project_id.in_(visible), am.ended_at >= f.since, am.ended_at < f.until]
    for name, column in FILTERS.items():
        values = getattr(f, name)
        if values is not None and name != without:
            found.append(column.in_(values))
    if f.state != "all":
        found.append(am.state == f.state)
    if f.owner_id is not None:
        found.append(am.owner_id == f.owner_id)
    return found


def last(f: Filters) -> list[Any]:
    """`attempts=last`: each task's last attempt, as §3.6's aggregate."""
    return [am.attempt_id == _last_attempt(am.task_id)] if f.attempts == "last" else []


def count_query(f: Filters, visible: list[str]) -> Select[Any]:
    """The rows in the filters, before `attempts=last`: the rows a query scans."""
    return select(func.count()).select_from(attempt_metrics).where(*where(f, visible))


def summary_query(
    f: Filters, visible: list[str], keys: list[str], chosen: list[str]
) -> Select[Any]:
    """In the order of the groups' columns then `ended_at`, so that each group's rows, a
    period's included, come together."""
    columns = [GROUPS[k][1] for k in keys if k in GROUPS]
    metrics = [am[m] for m in chosen]
    labelled = [c.label(f"_g{i}") for i, c in enumerate(columns)]
    query = select(am.task_id, am.tag, am.run_id.label("_run"), am.ended_at, *labelled, *metrics)
    return query.where(*where(f, visible), *last(f)).order_by(*columns, am.ended_at)


def attempts_query(
    f: Filters, visible: list[str], sort: str, cursor: str | None, limit: int
) -> tuple[Select[Any], list[tuple[Any, bool, str]]]:
    key, descending, kind = SORTS[sort]
    keys = [(key, descending, kind), (am.attempt_id, descending, "text")]
    labelled = [k.label(f"_key{i}") for i, (k, _, _) in enumerate(keys)]
    query = select(*ITEM, *labelled).where(*where(f, visible), *last(f))
    return _keyset(query, keys, cursor, limit), keys


def facet_query(f: Filters, visible: list[str], name: str) -> Select[Any]:
    own, column = FACETS[name]
    query = select(column).distinct().where(*where(f, visible, without=own), column.is_not(None))
    return query.order_by(column).limit(MAX_FACET + 1)


def count(conn: Connection, f: Filters, visible: list[str]) -> int:
    return int(conn.execute(count_query(f, visible)).scalar_one())


def _mine(conn: Connection) -> tuple[str, list[str], list[str]]:
    """The principal, its groups and `visible_projects` (single-user mode, 0.0.2)."""
    me = first(conn, principals)
    groups = select(projects.c.owning_group_id).where(projects.c.created_by == me).distinct()
    found = list(conn.execute(groups).scalars())
    visible = select(projects.c.id).where(projects.c.owning_group_id.in_(found))
    return me, found, list(conn.execute(visible).scalars())


@contextmanager
def across(request: Request, q: Asked) -> Iterator[tuple[Connection, Filters, list[str], int]]:
    """The gate, a connection under the budget, the caller's filters and projects, and the
    row-count check (`422 range-too-wide` over MAX_SCANNED)."""
    gate: Gate = request.app.state.performance_gate
    who = request.cookies.get(cookie_name(request.headers.get("host")), "")
    with gate.slot(who), read(request) as conn, budget(conn, "the performance across runs"):
        me, groups, visible = _mine(conn)
        f = q.filters
        if q.user is not None:
            f = replace(f, owner_id=me if q.user == "me" else q.user)
        if q.environment is not None:
            names = select(environments.c.id).where(
                environments.c.name.in_(q.environment),
                environments.c.owning_group_id.in_(groups),
            )
            f = replace(f, environment_id=tuple(conn.execute(names).scalars()))
        if (n := count(conn, f, visible)) > MAX_SCANNED:
            raise too_wide(f"{n} attempt rows in the range, over {MAX_SCANNED}", count=n)
        yield conn, f, visible, n


@functools.cache
def _zones() -> frozenset[str]:
    return frozenset(available_timezones()) | {"UTC"}


def _keys(group_by: str | None, f: Filters) -> list[str]:
    keys = list(dict.fromkeys(k.strip() for k in (group_by or "process").split(",")))
    for key in keys:
        if key not in GROUPS and key not in PERIODS:
            raise Invalid("group_by", f"unknown key {key[:64]!r}")
    if len(keys) > 2 or sum(k in PERIODS for k in keys) > 1:
        raise Invalid("group_by", "at most 2 keys, one of them a period")
    if "hour" in keys and f.until - f.since > MAX_HOURLY:
        raise Invalid("group_by", "hour needs a range of at most 48 h")
    return keys


def _period(at: datetime, kind: str, zone: ZoneInfo) -> str:
    """The start of `at`'s hour, day or week (from Monday) in `zone`, with its offset."""
    local = at.astimezone(zone).replace(tzinfo=None, minute=0, second=0, microsecond=0)
    if kind != "hour":
        local = local.replace(hour=0) - timedelta(days=local.weekday() if kind == "week" else 0)
    return local.replace(tzinfo=zone).isoformat()


def _groups(
    rows: Iterator[Row[Any]], keys: list[str], zone: ZoneInfo, chosen: list[str], tally: Tally
) -> Iterator[dict[str, Any]]:
    """Each group's statistics as its rows stream in, one group in memory at a time."""
    columns = [k for k in keys if k in GROUPS]

    def key_of(r: Row[Any]) -> tuple[Any, ...]:
        found = []
        for k in keys:
            if k in GROUPS:
                found.append(getattr(r, f"_g{columns.index(k)}"))
            else:
                found.append(_period(r.ended_at, k, zone))
        return tuple(found)

    for key, group in groupby(rows, key_of):
        mine = list(group)
        runs_of = {r._run for r in mine}
        tally.runs |= runs_of
        tally.jobs, tally.groups = tally.jobs + len(mine), tally.groups + 1
        names = [GROUPS[k][0] if k in GROUPS else "period_start" for k in keys]
        yield {
            "key": dict(zip(names, key, strict=True)),
            "runs": len(runs_of),
            "n": len(mine),
            "stats": {m: stats(mine, m) for m in chosen},
        }


@router.get("/performance:summary", response_model=models.PerformanceSummary)
def summary(
    request: Request,
    q: Query_,
    group_by: Annotated[str | None, Query(max_length=64)] = None,
    tz: Annotated[str, Query(max_length=64)] = "UTC",
    metrics: Annotated[str | None, Query(max_length=1024)] = None,
) -> dict[str, Any]:
    chosen, keys = _chosen(metrics), _keys(group_by, q.filters)
    if tz not in _zones():
        raise Invalid("tz", "not an IANA time zone")
    tally = Tally()
    with across(request, q) as (conn, f, visible, scanned):
        rows = conn.execute(summary_query(f, visible, keys, chosen))
        groups = _groups(iter(rows), keys, ZoneInfo(tz), chosen, tally)
        kept = heapq.nlargest(MAX_GROUPS, groups, key=lambda g: g["n"])  # stable on ties
    return {
        "totals": {"jobs": tally.jobs, "runs": len(tally.runs)},
        "groups": kept,
        "truncated": tally.groups > MAX_GROUPS,
        "scanned": scanned,
    }


@router.get("/performance/attempts", response_model=models.PerformanceAttempts)
def attempt_rows(
    request: Request,
    q: Query_,
    sort: Annotated[str, Query(max_length=32)] = "-ended_at",
    limit: Limit = 50,
    cursor: Cursor = None,
) -> dict[str, Any]:
    if sort not in SORTS:
        raise Invalid("sort", f"one of {', '.join(SORTS)}")
    with across(request, q) as (conn, f, visible, _):
        query, keys = attempts_query(f, visible, sort, cursor, limit)
        found = conn.execute(query).all()
        page = {r.run_id for r in found[:limit]}
        names: dict[str, str | None] = dict(
            conn.execute(select(runs.c.id, runs.c.name).where(runs.c.id.in_(page))).all()
        )
    items = []
    for r in found[:limit]:
        item = {c.name: getattr(r, c.name) for c in ITEM}
        for name in ("submitted_at", "started_at", "ended_at"):
            item[name] = _iso(item[name])
        items.append({**item, "run_name": names.get(r.run_id)})
    next_ = _cursor_of(found[limit - 1], keys) if len(found) > limit else None
    return {"items": items, "next": next_}


@router.get("/performance/facets", response_model=models.PerformanceFacets)
def facets(request: Request, q: Query_) -> dict[str, Any]:
    answer: dict[str, Any] = {"truncated": []}
    with across(request, q) as (conn, f, visible, _):
        for name in FACETS:
            values = list(conn.execute(facet_query(f, visible, name)).scalars())
            if len(values) > MAX_FACET:
                answer["truncated"].append(name)
            answer[name] = values[:MAX_FACET]
        _, groups, _ = _mine(conn)
        readable = select(environments.c.id, environments.c.name).where(
            environments.c.id.in_(answer["environment"]),
            environments.c.owning_group_id.in_(groups),
        )
        named: dict[str, str | None] = dict(conn.execute(readable).all())
    answer["environment"] = [
        {"id": e, "name": named.get(e) or ANOTHER} for e in answer["environment"]
    ]
    return answer
