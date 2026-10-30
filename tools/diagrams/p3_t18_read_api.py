#!/usr/bin/env python3
"""Read runs, tail logs, cancel, watch live: step P3, P1 Task 18, 2026-10-30.

Writes docs/assets/diagrams/p3-t18-read-api_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t18 at 562510b (BASE 87aaa59):
- packages/spectio-server/src/spectio_server/api/runs_read.py: GET /runs (sort -created_at or
  -ended_at, state, q a name prefix, Limit 1 to 200 default 50, Cursor max_length 512, `{items,
  next}`), /runs:summary, /runs/{id}, /processes, /stages, /tasks; every read opens its own
  connection on the writer's engine (SQLite WAL readers never wait); Invalid("cursor", ...) for a
  cursor this server did not give, a naive time in it too (ec75d07); run_row 404 not-found;
- api/logs.py: TAIL 65536; sources head-out, head-err (`.spectio/head.out`, `.spectio/head.err`)
  and engine (`.nextflow.log`, or the newest regular `.snakemake/log/*.log`); private_dir(runs_root,
  run_id, "launch"); each part opened O_NOFOLLOW from its parent's descriptor; fstat S_ISREG;
  otherwise 404 log-not-found;
- api/cancel.py: CANCELLABLE queued, running: move to cancelling with source "api", actor_kind
  "person", actor_principal_id first(principals) (SEC-P3T18-01 in 562510b); runner_commands kind
  cancel for the last launch, created_by that principal; 202; 200 unchanged otherwise; origin
  cli-observed: 422 not-in-this-version;
- store/writer.py: note_change records run and task IDs in conn.info; after the commit,
  Writer._committed calls on_commit; a failed job drops them; app.py wires on_commit to
  Stream.notify; store/runs.py insert_run calls note_change (CR-P3T18-01 in 562510b);
- api/stream.py: INTERVAL_S 1.0, KEEP_ALIVE_S 15.0, QUEUE_SIZE 64, MAX_CLIENTS 32; frame `event:
  spectio.run.delta` with run_id, seq_through, counts, changed.tasks; a full queue drops the
  subscriber; Stream.clients counts open connections, dropped ones included; open() with no await
  after the check; _Response frees the slot in a finally (CR-P3T18-02, SEC-P3T18-02 in 562510b);
  over the cap 429 rate-limited;
- api/problems.py framework(): 400 becomes 422 validation-failed on body, 404 not-found, any
  other status type about:blank with the status phrase, headers kept (SEC-P3T18-04 in 562510b);
  api/browser.py (4bddad3, FU-P3-17): transfer-encoding 411 length-required, Content-Length over
  MAX_BODY 1048576 413 request-too-large; runs_write.py MAX_DEPTH 32 of params; workflows.py
  MAX_LOCATION 4096; spectio/runner/loop.py (df61c4e, FU-P3-14): a Snakemake end skips the 60 s
  spool grace;
- tests/api/test_stream.py test_client_cap_holds_under_concurrent_opens: 40 opens at once,
  200 x MAX_CLIENTS and 429 x 8; the worker's report: before the fix all 40 got 200;
- the review rounds: the two rounds of `review-code` for P3-t18 (record
  docs/reviews/code/P3-t18.md): R1 CR 5 and SEC 7, R2 CR 3 and SEC 1, all minor or simplify, both
  approve each round; five R1 findings fixed in 562510b; the simplifier changed nothing; its
  baseline at 562510b: 484 passed, 15 deselected, ruff, mypy, lint-imports and uv lock clean.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1290
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
ROW = 150  # the pictograms
TXT = ROW + 168  # the captions
NO = TXT + 128  # the refusals
FIX = NO + 50  # the findings fixed there
MID = 630  # the cap, to scale, and the refusals
LOW = 960  # the review rounds

# (round, fixed in 562510b, left open, code-reviewer verdict, security-reviewer verdict)
ROUNDS = (
    ("R1", 5, 7, "approve", "approve"),
    ("R2", 0, 4, "approve", "approve"),
)


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def refusal(s: Sketch, x: float, y: float, rows: tuple[str, ...]) -> None:
    s.cross(x + 14, y - 5, size=9)
    for i, row in enumerate(rows):
        s.text(x + 34, y + i * 20, row, size=13, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def fixed(s: Sketch, x: float, y: float, rows: tuple[str, ...]) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 18, row, size=12, anchor="start", colour=s.t.accent)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=118)
    t = theme
    s.heading(50, 58, "P3 Task 18 · read the runs, tail a log, cancel, watch it live",
              "`/api/v1` runs, tasks, logs, cancel and `/events/stream` · api 5, 7, 8.3 and 8.5 · "
              "inbox 86 and 87 · local only, one Unix user, no sign-in yet")

    # 1 -- read the runs ------------------------------------------------------------------------
    x = COL[0]
    s.browser(x, ROW, 270, 126, url="`/api/v1/runs`")
    for i, (name, fill) in enumerate((("rnaseq-3", "work"), ("rnaseq-2", "done"),
                                      ("sarek-1", "problem"))):
        y = ROW + 38 + i * 24
        bar(s, x + 14, y, 14, 14, fill)
        s.text(x + 38, y + 12, name, size=12.5, anchor="start")
        s.line(x + 130, y + 7, x + 196, y + 7, amount=0.3, passes=1, colour=t.muted)
    s.link(x + 232, ROW + 104, size=11)
    s.text(x + 232, ROW + 86, "`next`", size=12, colour=t.dim)
    s.text(x + 140, ROW + 150, "each read its own connection, never waits", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 1, "read the runs")
    lines(s, x, TXT + 30, ("`GET /runs`, newest first, 50 a page",
                           "by state, a name prefix, up to 200",
                           "`next`: an opaque cursor",
                           "one run, its processes, stages, tasks"))
    refusal(s, x, NO, ("422: a bad state, a cursor this", "server did not give; 404 no run"))

    # 2 -- the last 64 KiB of a log -------------------------------------------------------------
    x = COL[1]
    s.folder(x + 2, ROW + 6, 120, 92, fill="input", label="")
    s.text(x + 62, ROW + 116, "launch dir", size=12.5, colour=t.dim)
    for i in range(3):
        s.page(x + 18 + i * 32, ROW + 34, 26, 34, fill="surface", lines=2)
    s.lock(x + 112, ROW + 92, size=12)
    s.arrow(x + 128, ROW + 52, x + 160, ROW + 52)
    s.page(x + 168, ROW + 4, 76, 104, fill="surface", lines=0)
    for i in range(6):
        s.line(x + 178, ROW + 22 + i * 12, x + 232, ROW + 22 + i * 12, amount=0.3, passes=1,
               colour=t.muted)
    s.shade(x + 172, ROW + 66, 68, 38, fill="docs", opacity=0.7)
    s.text(x + 206, ROW + 124, "the last 64 KiB", size=12.5, colour=t.dim)
    s.text(x + 140, ROW + 150, "every part opened `O_NOFOLLOW`", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 2, "the end of a log")
    lines(s, x, TXT + 30, ("`head-out`, `head-err` or `engine`",
                           "engine: `.nextflow.log`, or the newest",
                           "Snakemake log; regular files only",
                           "dir from the runs root and the run ID"))
    refusal(s, x, NO, ("404 `log-not-found`: missing, a", "symlink, not private, not a file"))

    # 3 -- cancel -------------------------------------------------------------------------------
    x = COL[2]
    s.button(x + 4, ROW + 6, 82, "Cancel", fill="problem", h=30)
    s.arrow(x + 92, ROW + 21, x + 166, ROW + 21)
    for i, (label, fill) in enumerate((("running", "work"), ("cancelling", "gate"),
                                       ("cancelled", "neutral"))):
        y = ROW + 8 + i * 36
        bar(s, x + 172, y, 100, 26, fill)
        s.text(x + 222, y + 18, label, size=13)
    s.runner(x + 4, ROW + 56, w=86, h=46, label="runner")
    s.arrow(x + 94, ROW + 79, x + 118, ROW + 79, colour=t.dim)
    s.page(x + 122, ROW + 58, 34, 44, fill="surface", lines=2)
    s.text(x + 139, ROW + 122, "`.spectio/cancel`", size=12, colour=t.dim)
    s.text(x + 140, ROW + 150, "202 with the run, `cancelling`", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 3, "cancel")
    lines(s, x, TXT + 30, ("`POST /runs/ID:cancel`, queued or running",
                           "a `cancel` command for the last launch",
                           "the runner writes `.spectio/cancel`, then",
                           "signals; `cancelled` once the head ends"))
    refusal(s, x, NO, ("200 unchanged: already cancelling,", "ended; 422 for a cli-observed run"))
    fixed(s, x, FIX, ("fixed: R1 SEC-P3T18-01, the event says", "source `api`, actor `person`: who acted"))

    # 4 -- every commit noted -------------------------------------------------------------------
    x = COL[3]
    s.cog(x + 34, ROW + 40, 16, fill="docs")
    s.text(x + 34, ROW + 92, "writer thread", size=12.5, colour=t.dim)
    s.arrow(x + 62, ROW + 40, x + 104, ROW + 40)
    s.bucket(x + 140, ROW + 14, 64, 56, fill="neutral")
    s.text(x + 140, ROW + 50, "DB", size=13, colour=t.dim)
    s.text(x + 140, ROW + 92, "commit", size=12.5, colour=t.dim)
    s.arrow(x + 176, ROW + 40, x + 214, ROW + 40)
    s.page(x + 220, ROW + 10, 50, 62, fill="input", lines=3)
    s.text(x + 245, ROW + 92, "changes", size=12.5, colour=t.dim)
    s.text(x + 140, ROW + 150, "`note_change`, then `on_commit`", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 4, "every commit noted")
    lines(s, x, TXT + 30, ("a job notes the run and its tasks",
                           "inside its transaction; after the",
                           "commit they go to the stream, which",
                           "only records them: never blocks"))
    refusal(s, x, NO, ("a job that fails sends nothing", "its changes are dropped"))
    fixed(s, x, FIX, ("fixed: R1 CR-P3T18-01, a new run too:", "`insert_run` notes it"))

    # 5 -- live, at most once a second ----------------------------------------------------------
    x = COL[4]
    s.hourglass(x + 22, ROW + 30, size=12)
    s.text(x + 22, ROW + 66, "1 s", size=13, weight="bold")
    s.arrow(x + 42, ROW + 30, x + 80, ROW + 30)
    s.envelope(x + 86, ROW + 16, 44, 30, fill="done")
    s.arrow(x + 136, ROW + 24, x + 166, ROW + 10)
    s.arrow(x + 136, ROW + 38, x + 166, ROW + 62)
    s.browser(x + 172, ROW, 106, 46, url="")
    s.browser(x + 172, ROW + 56, 106, 46, url="")
    s.text(x + 225, ROW + 120, "open tabs", size=12.5, colour=t.dim)
    s.text(x + 140, ROW + 150, "`spectio.run.delta`, one per run", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 5, "live, once a second")
    lines(s, x, TXT + 30, ("`GET /events/stream`, server-sent",
                           "per changed run: its task counts",
                           "and the IDs of the tasks that moved",
                           "a keep-alive line after 15 s quiet"))
    refusal(s, x, NO, ("429 `rate-limited` past 32 streams;", "64 frames behind: dropped, reconnects"))
    fixed(s, x, FIX, ("fixed: R1 CR-P3T18-02, SEC-P3T18-02,", "the cap holds, below"))

    s.arrow(COL[2] + CW + 2, ROW + 50, COL[3] + 4, ROW + 50)
    s.arrow(COL[3] + CW + 2, ROW + 50, COL[4] - 2, ROW + 50)

    # the cap, to scale -------------------------------------------------------------------------
    s.line(30, MID - 50, W - 30, MID - 50, dashed=True, colour=t.muted)
    s.text(50, MID - 12, "40 streams opened at once, one cell each", size=17, anchor="start",
           weight="bold")
    s.text(50, MID + 10, "`test_client_cap_holds_under_concurrent_opens`, cap 32", size=13.5,
           anchor="start", colour=t.dim)
    cell, gap = 17, 3
    for i, (label, groups) in enumerate((
        ("before", ((40, "done", "200, all of them"),)),
        ("after", ((32, "done", "200"), (8, "problem", "429"))),
    )):
        y = MID + 40 + i * 70
        s.text(50, y + 16, label, size=15, anchor="start", weight="bold")
        s.task_strip(120, y, groups, cell=cell, gap=gap, h=22, label_size=13)
    cap_x = 120 + 32 * (cell + gap) - gap / 2
    s.line(cap_x, MID + 32, cap_x, MID + 160, dashed=True, colour=t.accent)
    s.text(cap_x, MID + 24, "32", size=13, weight="bold", colour=t.accent)
    lines(s, 50, MID + 194, ("the handler checks `clients` and takes a slot with no `await` between,",
                             "a dropped client keeps its slot until its connection ends, and the",
                             "response frees it in a `finally`, even if its body never started"))

    # every refusal a problem document ----------------------------------------------------------
    px = 1000
    s.shade(px - 20, MID - 30, 590, 310, fill="neutral", opacity=0.35, colour=t.muted, dashed=True)
    s.text(px, MID - 2, "every refusal a problem document", size=17, anchor="start", weight="bold")
    s.text(px, MID + 20, "FU-P3-17, `application/problem+json`", size=13.5, anchor="start",
           colour=t.dim)
    rows = (
        ("a body it cannot parse", "422 `validation-failed`, `body`"),
        ("an unknown `/api/v1` path", "404 `not-found`"),
        ("a wrong method", "405 `about:blank`, Allow kept"),
        ("a chunked body", "411 `length-required`"),
        ("a body over 1 MiB", "413 `request-too-large`"),
        ("params deeper than 32", "422 on `params`"),
        ("a location over 4096 chars", "422 on `location`"),
    )
    for i, (what, answer) in enumerate(rows):
        y = MID + 54 + i * 27
        s.text(px, y, what, size=13.5, anchor="start")
        s.arrow(px + 216, y - 5, px + 244, y - 5, colour=t.dim)
        s.text(px + 252, y, answer, size=13, anchor="start", colour=t.dim)
    fixed(s, px, MID + 254, ("fixed: R1 SEC-P3T18-04, the first three were bare JSON",))

    # the review rounds, to scale ---------------------------------------------------------------
    s.line(30, LOW - 40, W - 30, LOW - 40, dashed=True, colour=t.muted)
    s.text(50, LOW, "2 review rounds, one cell per finding", size=17, anchor="start", weight="bold")
    s.text(50, LOW + 22, "no blocker, no major: minor or simplify", size=13.5, anchor="start",
           colour=t.dim)
    cell, gap, rh = 22, 3, 38
    for i, (rnd, done, left, cr, sec) in enumerate(ROUNDS):
        y = LOW + 50 + i * rh
        s.text(50, y + 16, rnd, size=15, anchor="start", weight="bold")
        groups = tuple((n, fill, "") for n, fill in ((done, "done"), (left, "neutral")) if n)
        right = s.task_strip(90, y, groups, cell=cell, gap=gap, h=22)
        s.text(right + 6, y + 16, f"{done + left}", size=14, anchor="start")
        both = "both approve" if cr == sec == "approve" else f"CR {cr}, SEC {sec}"
        s.text(460, y + 16, both, size=13.5, anchor="start")
        s.tick(570, y + 10, size=7)
    ly = LOW + 50 + 2 * rh + 6
    for j, (fill, label) in enumerate((("done", "fixed in 562510b"), ("neutral", "left open"))):
        lx = 90 + j * 170
        bar(s, lx, ly, 16, 16, fill)
        s.text(lx + 24, ly + 13, label, size=13, anchor="start", colour=t.dim)
    s.terminal(50, LOW + 166, 540, 92, ("$ uv run --locked pytest -q",
                                         "484 passed, 15 deselected",
                                         "ruff, mypy, lint-imports, uv lock: clean"), size=12.5)

    ox = 640
    s.shade(ox, LOW - 14, 910, 290, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.warning(ox + 28, LOW + 10, size=11)
    s.text(ox + 50, LOW + 16, "still open after round 2, both approve", size=15, anchor="start",
           weight="bold")
    open_items = (
        ("no session and no `can` check yet; every run goes to every tab", "R1 SEC-07, Task 16"),
        ("the log reader does not check the file's owner; Task 25 needs it", "R1 SEC-05"),
        ("a delta frame has no size bound: a large scatter, 32 slow tabs", "R1 SEC-03"),
        ("a time bound on schema patterns, now FU-P3-20", "R1 SEC-06, CR-04"),
        ("the OpenAPI snapshot is untyped, and holds the package version", "R1 CR-03"),
        ("the task cursor repeats the ID: a cursor format to decide", "R1 CR-05"),
        ("the cap test needs ASGI 2.3; under 2.4 a close is seen late", "R2 CR-04"),
        ("a status outside `HTTPStatus` would be a 500, unreachable today", "R2 SEC-05"),
    )
    for i, (what, where) in enumerate(open_items):
        y = LOW + 46 + i * 26
        s.dot(ox + 30, y - 5, 3, colour=t.dim)
        s.text(ox + 46, y, what, size=13.5, anchor="start")
        s.text(ox + 890, y, where, size=12.5, anchor="end", colour=t.dim)

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(50, H - 16, "R1, R2: the round a finding ID comes from; SEC-07 is SEC-P3T18-07 and so on; "
           "also carried: FU-P3-14, a Snakemake end skips the 60 s spool grace",
           size=13, anchor="start", colour=t.dim)
    s.text(W - 50, H - 40, "source: spectio_server/api/runs_read.py, logs.py, cancel.py, stream.py, "
           "problems.py, store/writer.py at 562510b", size=12.5, anchor="end", colour=t.dim)
    s.text(W - 50, H - 16, "review record P3-t18 · P1 Task 18", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t18-read-api")
