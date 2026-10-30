"""Spike first-look: synthetic spools -> real read_spool -> real projector -> real SQLite -> a page.

    uv run python spikes/first-look/demo.py [--port 8765] [--period 3]

Writes three runs (make_spool.py) under a fresh private temp directory, opens a real store there
(open_db, migrations), and every `--period` seconds reads each launch's spool with the real
reader and ingests it through the real writer and projector. One run keeps growing until it
ends. The page on http://127.0.0.1:<port>/ is read-only, and shows only what the database holds.
Throwaway: no auth, no launch, no head report, no API (see docs/research/2026-10-30-first-look-spike.md).
"""

import argparse
import html
import re
import sys
import tempfile
import threading
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from sqlalchemy import Engine, func, insert, select

from make_spool import Run, build, follow
from spectio.runner.spool import read_spool
from spectio_server.projector.ingest import ingest, load_cursor
from spectio_server.store.db import open_db
from spectio_server.store.schema import (attempts, environments, events, launches, projects,
                                         runs, spool_drops, tasks, workflow_versions, workflows)
from spectio_server.store.writer import Writer

ACTIVE = {"queued", "running", "cancelling"}
DONE = {"succeeded", "cached"}
_C0 = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]|\x1b\[[0-9;]*[A-Za-z]")


def esc(value: object) -> str:
    """Text from events is shown with C0 and ANSI control characters stripped (api §14.1)."""
    return html.escape(_C0.sub("", "" if value is None else str(value)))


# -- ingest --------------------------------------------------------------------------------


def seed(writer: Writer, runs_: list[Run]) -> dict[str, str]:
    """What the launch API (P1 Task 17) would write: project, workflows, queued runs, launches."""
    now = datetime.now(UTC)
    launch_ids = {r.id: f"lch_{r.id[4:]}" for r in runs_}

    def fn(conn):
        conn.execute(insert(projects).values(id="prj_demo", owning_group_id="grp_demo",
                                             created_at=now, name="demo"))
        conn.execute(insert(environments).values(id="env_local", kind="local", created_at=now))
        for i, wf in enumerate(sorted({r.workflow for r in runs_})):
            conn.execute(insert(workflows).values(id=f"wfl_{i}", project_id="prj_demo",
                                                  source="local", location=f"/w/{wf}", name=wf,
                                                  engine="nextflow", created_at=now))
            conn.execute(insert(workflow_versions).values(id=f"wfv_{i}", workflow_id=f"wfl_{i}",
                                                          revision="0.1.0", created_at=now))
        wfv = {wf: f"wfv_{i}" for i, wf in enumerate(sorted({r.workflow for r in runs_}))}
        for r in runs_:
            conn.execute(insert(runs).values(
                id=r.id, project_id="prj_demo", workflow_version_id=wfv[r.workflow],
                environment_id="env_local", name=r.name, state="queued", origin="ui",
                launch_dir=str(r.launch_dir), created_at=now))
            conn.execute(insert(launches).values(id=launch_ids[r.id], run_id=r.id, n=1,
                                                 launch_dir=str(r.launch_dir), created_at=now))

    writer.submit(fn).result()
    return launch_ids


def poll(writer: Writer, runs_: list[Run], launch_ids: dict[str, str], period: float) -> None:
    """The runner loop's job (P1 Task 9), reduced: read each spool, ingest it in one transaction."""
    while True:
        for r in runs_:
            lid = launch_ids[r.id]

            def fn(conn, r=r, lid=lid):
                batch = read_spool(r.launch_dir, r.id, 1, load_cursor(conn, lid))
                ingest(conn, lid, batch)
                return len(batch.events)

            n = writer.submit(fn).result()
            if n:
                print(f"ingested {n:3d} events of {r.name}", flush=True)
        time.sleep(period)


# -- reads ---------------------------------------------------------------------------------


def run_rows(conn):
    span = (select(events.c.run_id, func.min(events.c.engine_time).label("t0"),
                   func.max(events.c.engine_time).label("t1"))
            .group_by(events.c.run_id).subquery())
    retried = (select(tasks.c.run_id, func.count().label("n"))
               .join(attempts, attempts.c.task_id == tasks.c.id).where(attempts.c.n > 1)
               .group_by(tasks.c.run_id).subquery())
    q = (select(runs, workflows.c.name.label("workflow"), workflow_versions.c.revision,
                span.c.t0, span.c.t1, func.coalesce(retried.c.n, 0).label("retried"))
         .join(workflow_versions, workflow_versions.c.id == runs.c.workflow_version_id)
         .join(workflows, workflows.c.id == workflow_versions.c.workflow_id)
         .outerjoin(span, span.c.run_id == runs.c.id)
         .outerjoin(retried, retried.c.run_id == runs.c.id)
         .order_by(runs.c.created_at.desc(), runs.c.id.desc()))
    return conn.execute(q).all()


def fmt_time(t: datetime | None) -> str:
    return t.astimezone(UTC).strftime("%H:%M:%S") if t else "—"


def fmt_span(t0: datetime | None, t1: datetime | None) -> str:
    if not (t0 and t1):
        return "—"
    s = int((t1 - t0).total_seconds())
    return f"{s // 60} min {s % 60:02d} s"


def tally(counts: dict | None) -> tuple[int, int, int, int]:
    """done, running, failed, total over a task_counts map."""
    c = Counter(counts or {})
    return (sum(c[s] for s in DONE), c["running"] + c["submitted"], c["failed"],
            sum(c.values()))


def state_badge(state: str, sub: str = "") -> str:
    icon = {"running": "▷", "queued": "◷", "succeeded": "✓", "failed": "✕",
            "cancelled": "⊘", "cancelling": "⊘"}.get(state, "•")
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return f'<div class="st st-{esc(state)}">{icon} {esc(state.capitalize())}</div>{sub_html}'


# -- pages ---------------------------------------------------------------------------------

CSS = """
:root{--bg:#f6f6f9;--card:#fff;--line:#e6e6ee;--ink:#1d1d27;--mute:#6b6b7b;--acc:#6c47e8;
--run:#2563eb;--ok:#15803d;--bad:#dc2626;--warn:#b45309;--grey:#6b7280}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.45 Inter,system-ui,-apple-system,Segoe UI,sans-serif}
a{color:inherit;text-decoration:none}
.top{display:flex;align-items:center;gap:14px;margin:10px;padding:12px 18px;background:var(--card);
border:1px solid var(--line);border-radius:14px}
.logo{font-weight:700;font-size:20px;letter-spacing:-.02em}.logo b{color:var(--acc)}
.crumb{color:var(--mute);border-left:1px solid var(--line);padding-left:14px}
.pill{margin-left:auto;font-size:12px;border:1px solid var(--line);border-radius:8px;
padding:6px 10px;color:var(--mute)}
.wrap{display:flex;gap:16px;margin:0 10px 10px}
nav{width:200px;flex-shrink:0;background:var(--card);border:1px solid var(--line);
border-radius:14px;padding:12px;align-self:flex-start}
nav a{display:block;padding:10px 12px;border-radius:10px;font-weight:500}
nav a.on{background:#efeafe;color:var(--acc)}
main{flex:1;min-width:0}
h1{font-size:26px;margin:4px 0 2px}.lead{color:var(--mute);margin:0 0 14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow-x:auto;
margin-bottom:16px}
table{width:100%;border-collapse:collapse}th{text-align:left;font-weight:500;color:var(--mute);
font-size:12.5px;background:#fafafc;padding:10px 14px;border-bottom:1px solid var(--line)}
td{padding:11px 14px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.bar-running td:first-child{box-shadow:inset 3px 0 var(--run)}
.bar-succeeded td:first-child{box-shadow:inset 3px 0 var(--ok)}
.bar-failed td:first-child{box-shadow:inset 3px 0 var(--bad)}
.bar-queued td:first-child{box-shadow:inset 3px 0 var(--grey)}
.id{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mute)}
.sub{font-size:12.5px;color:var(--mute)}.st{font-weight:600}
.st-running{color:var(--run)}.st-succeeded{color:var(--ok)}.st-failed{color:var(--bad)}
.st-queued,.st-cancelled,.st-not-started{color:var(--grey)}.st-aborted{color:var(--grey)}
.st-pending,.st-submitted{color:var(--mute)}.red{color:var(--bad)}.amber{color:var(--warn)}
.head{padding:18px 20px;border-top:4px solid var(--run)}.head.failed{border-top-color:var(--bad)}
.head.succeeded{border-top-color:var(--ok)}
.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:14px 20px;padding:16px 20px;
border-top:1px solid var(--line)}.facts .k{font-size:12px;color:var(--mute)}
.chips{display:flex;gap:8px;flex-wrap:wrap;padding:12px 20px;border-top:1px solid var(--line)}
.chip{font-size:12.5px;font-weight:600;padding:3px 10px;border-radius:7px;background:#f0f0f5}
.c-succeeded{background:#e7f6ec;color:var(--ok)}.c-running{background:#e6efff;color:var(--run)}
.c-failed{background:#fdeaea;color:var(--bad)}.c-retried{background:#fdf2e2;color:var(--warn)}
.c-aborted{background:#eeeef2;color:var(--grey)}
.prog{display:inline-block;width:70px;height:6px;border-radius:3px;background:#e9e9f0;
vertical-align:middle;margin-right:8px;overflow:hidden}.prog i{display:block;height:100%;
background:var(--acc)}
h2{font-size:17px;margin:0;padding:14px 20px;border-bottom:1px solid var(--line)}
.att{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:6px;
padding:1px 7px;margin:0 4px 2px 0}
.log{background:#16161f;color:#a7f3d0;font:12px/1.6 ui-monospace,Menlo,monospace;padding:12px 16px;
margin:0;white-space:pre;overflow-x:auto}
.grid2{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:16px}
@media(max-width:900px){nav,.pill{display:none}.wrap{margin:0 16px 16px}.facts{grid-template-columns:1fr 1fr}
.grid2{display:block}.hide-sm{display:none}}
"""


def page(title: str, crumb: str, body: str, live: bool) -> bytes:
    refresh = '<meta http-equiv="refresh" content="3">' if live else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">{refresh}
<title>{esc(title)}</title><style>{CSS}</style></head><body>
<header class="top"><a class="logo" href="/">Spect<b>io</b></a><span class="crumb">{crumb}</span>
<span class="pill">spike first-look · synthetic spool · local store</span></header>
<div class="wrap"><nav><a class="on" href="/">Runs</a></nav><main>{body}</main></div>
</body></html>""".encode()


def runs_page(engine: Engine) -> bytes:
    with engine.connect() as conn:
        rows = run_rows(conn)
    active = sum(r.state in ACTIVE for r in rows)
    trs = []
    for r in rows:
        done, running, failed, total = tally(r.task_counts)
        if r.state == "running":
            sub = f"{running} tasks running"
        elif r.state == "failed" and r.failure:
            sub = f"{esc(r.failure.get('class'))}"
        else:
            sub = ""
        extra = []
        if failed:
            extra.append(f'<span class="red">{failed} failed</span>')
        if r.retried:
            extra.append(f'<span class="amber">{r.retried} retried</span>')
        trs.append(f"""<tr class="bar-{esc(r.state)}">
<td><a href="/runs/{esc(r.id)}"><b>{esc(r.name)}</b></a><div class="id hide-sm">{esc(r.id)}</div></td>
<td>{state_badge(r.state, sub)}</td>
<td class="hide-sm">{esc(r.workflow)} <span class="sub">{esc(r.revision)}</span>
<div class="sub">Nextflow {esc(r.engine_version or '?')}</div></td>
<td class="num">{done} / {total}<div class="sub">{' · '.join(extra) or 'known so far'}</div></td>
<td class="hide-sm">{fmt_time(r.t0)}</td><td class="hide-sm">{fmt_span(r.t0, r.t1)}</td>
<td class="num hide-sm">{r.last_seq}</td></tr>""")
    body = f"""<h1>Runs</h1><p class="lead">{len(rows)} runs · {active} active · projected from
the spool into SQLite{' · live, refreshes every 3 s' if active else ''}</p>
<div class="card"><table><tr><th>Run</th><th>State</th><th class="hide-sm">Workflow</th><th class="num">Tasks
</th><th class="hide-sm">Engine start (UTC)</th><th class="hide-sm">Engine span</th>
<th class="num hide-sm">Events</th></tr>{''.join(trs)}</table></div>"""
    return page("Runs · Spectio", "Runs", body, active > 0)


def detail_page(engine: Engine, run_id: str) -> bytes | None:
    with engine.connect() as conn:
        r = next((x for x in run_rows(conn) if x.id == run_id), None)
        if r is None:
            return None
        lch = conn.execute(select(launches).where(launches.c.run_id == run_id)).one()
        drops = conn.execute(select(spool_drops.c.reason, spool_drops.c.count)
                             .where(spool_drops.c.launch_id == lch.id)).all()
        order = [e.payload.get("process") for e in conn.execute(
            select(events.c.payload).where(
                events.c.run_id == run_id,
                events.c.type == "spectio.engine.nextflow.onProcessCreate")
            .order_by(events.c.seq))]
        att_rows = conn.execute(
            select(tasks.c.id, tasks.c.process_or_rule, tasks.c.tag, tasks.c.name,
                   tasks.c.state.label("task_state"), attempts.c.n, attempts.c.state,
                   attempts.c.exit, attempts.c.failure_class, attempts.c.ignored)
            .outerjoin(attempts, attempts.c.task_id == tasks.c.id)
            .where(tasks.c.run_id == run_id)
            .order_by(tasks.c.process_or_rule, tasks.c.tag, attempts.c.n)).all()
        log = conn.execute(select(events.c.seq, events.c.engine_time, events.c.type,
                                  events.c.payload).where(events.c.run_id == run_id)
                           .order_by(events.c.seq.desc()).limit(12)).all()
    by_task: dict[str, list] = defaultdict(list)
    for a in att_rows:
        by_task[a.id].append(a)
    procs: dict[str, Counter] = defaultdict(Counter)
    for rows_ in by_task.values():
        procs[rows_[0].process_or_rule][rows_[0].task_state] += 1
        procs[rows_[0].process_or_rule]["retried"] += sum(1 for a in rows_ if (a.n or 0) > 1)
    names = {tid: rows_[0].name for tid, rows_ in by_task.items()}
    ordered = list(dict.fromkeys(order)) + sorted(set(procs) - set(order))  # created, maybe idle

    done, running, failed, total = tally(r.task_counts)
    chips = "".join(f'<span class="chip c-{esc(s)}">{n} {esc(s)}</span>'
                    for s, n in sorted((r.task_counts or {}).items()))
    if r.retried:
        chips += f'<span class="chip c-retried">{r.retried} retried</span>'
    f = r.failure or {}
    failure = (f"{esc(f.get('class'))} · {esc(names.get(f.get('task_id'), '—'))} attempt "
               f"{esc(f.get('attempt_n'))}<div class='sub'>{esc(f.get('message'))}</div>"
               if f else "—")
    facts = [("Pipeline", f"{esc(r.workflow)} {esc(r.revision)}"),
             ("Engine", f"Nextflow {esc(r.engine_version or '?')}"),
             ("Engine start · last event (UTC)", f"{fmt_time(r.t0)} · {fmt_time(r.t1)}"),
             ("Engine span", fmt_span(r.t0, r.t1)),
             ("Run started · ended (store clock)",
              f"{fmt_time(r.started_at)} · {fmt_time(r.ended_at)}"),
             ("Head state (launch 1)", esc(lch.head_state or "—")),
             ("Engine session", f'<span class="id">{esc(lch.engine_session_id)}</span>'),
             ("Exit code", esc(lch.exit_code if lch.exit_code is not None else "—")),
             ("Launch directory", f'<span class="id">{esc(r.launch_dir)}</span>'),
             ("Events · projected seq", f"{r.last_seq} · {r.projected_seq}"),
             ("Spool drops", esc(", ".join(f"{k} {v}" for k, v in drops) or "none")),
             ("Failure", failure)]
    facts_html = "".join(f'<div><div class="k">{k}</div>{v}</div>' for k, v in facts)

    proc_rows = []
    for p in ordered:
        c = procs[p]
        n = sum(v for k, v in c.items() if k != "retried")
        d = sum(c[s] for s in DONE)
        pct = int(100 * d / n) if n else 0
        st = ("failed" if c["failed"] else "not started" if n == 0 else "succeeded" if d == n else
              "running" if c["running"] or c["submitted"] else "pending")
        proc_rows.append(f"""<tr><td><b class="id" style="color:var(--ink)">{esc(p)}</b></td>
<td><span class="st st-{st.replace(' ', '-')}">{st.capitalize()}</span></td>
<td><span class="prog"><i style="width:{pct}%"></i></span>{d} / {n}</td>
<td class="num">{c['running'] + c['submitted']}</td><td class="num">{c['pending']}</td>
<td class="num {'red' if c['failed'] else ''}">{c['failed']}</td>
<td class="num">{c['aborted']}</td>
<td class="num {'amber' if c['retried'] else ''}">{c['retried']}</td></tr>""")

    task_rows = []
    for p in ordered:
        for tid, rows_ in by_task.items():
            if rows_[0].process_or_rule != p:
                continue
            atts = "".join(
                f'<span class="att st-{esc(a.state)}">#{a.n} {esc(a.state)}'
                f'{f" · exit {a.exit}" if a.exit is not None else ""}'
                f'{f" · {esc(a.failure_class)}" if a.failure_class else ""}</span>'
                for a in rows_ if a.n is not None)
            task_rows.append(f"""<tr><td>{esc(rows_[0].name)}</td>
<td><span class="st st-{esc(rows_[0].task_state)}">{esc(rows_[0].task_state)}</span></td>
<td>{atts}</td></tr>""")

    log_lines = "\n".join(
        f"{e.seq:>4}  {fmt_time(e.engine_time)}  {esc(e.type.rsplit('.', 1)[-1]):<20}"
        f"  {esc(e.payload.get('name') or e.payload.get('process') or e.payload.get('to') or '')}"
        for e in log)
    state = esc(r.state)
    body = f"""<div class="card"><div class="head {state}"><h1 style="margin:0">{esc(r.name)}
<span class="id">{esc(r.id)}</span></h1>
<div>{state_badge(r.state)} <span class="sub">{done} / {total} tasks done · {running} running ·
{failed} failed</span></div></div>
<div class="facts">{facts_html}</div>
<div class="chips"><span class="sub">Tasks (runs.task_counts)</span>{chips}</div></div>
<div class="grid2"><div>
<div class="card"><h2>Processes, first-seen order</h2><table><tr><th>Process</th><th>State</th>
<th>Tasks done</th><th class="num">Running</th><th class="num">Pending</th>
<th class="num">Failed</th><th class="num">Aborted</th><th class="num">Retried</th></tr>
{''.join(proc_rows)}</table></div>
<div class="card"><h2>Tasks and attempts</h2><table><tr><th>Task</th><th>State</th>
<th>Attempts (launch 1)</th></tr>{''.join(task_rows)}</table></div></div>
<div><div class="card"><h2>Event log · last 12</h2><pre class="log">{log_lines}</pre></div></div>
</div>"""
    return page(f"{r.name} · Spectio", f'<a href="/">Runs</a> / {esc(r.name)}', body,
                r.state in ACTIVE)


def serve(engine: Engine, port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            m = re.fullmatch(r"/runs/(run_[0-9A-Z]{26})", self.path)
            out = runs_page(engine) if self.path == "/" else (
                detail_page(engine, m[1]) if m else None)
            self.send_response(200 if out else 404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(out or b"not found")

        def log_message(self, *args) -> None:
            pass

    print(f"open http://127.0.0.1:{port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--period", type=float, default=3.0, help="seconds between reads")
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="spectio-first-look-"))  # 0700
    (root / "db").mkdir(mode=0o700)
    print(f"data in {root}", flush=True)
    runs_, live, rest = build(root / "runs")
    engine, _ = open_db(root / "db")
    writer = Writer(engine)
    launch_ids = seed(writer, runs_)
    threading.Thread(target=poll, args=(writer, runs_, launch_ids, args.period),
                     daemon=True).start()
    threading.Thread(target=follow, args=(live, rest, args.period), daemon=True).start()
    try:
        serve(engine, args.port)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
