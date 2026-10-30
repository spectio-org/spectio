#!/usr/bin/env python3
"""Inspect a pipeline, then launch it: step P3, P1 Task 17, 2026-10-30.

Writes docs/assets/diagrams/p3-t17-launch_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t17 at 3cbf735:
- packages/spectio-server/src/spectio_server/api/browser.py: on every request, before any route,
  a Host other than 127.0.0.1, localhost or [::1] is 400; Sec-Fetch-Site cross-site or same-site,
  or an Origin or Referer other than http://<Host>, is 403; a method other than GET and HEAD needs
  an Origin (403) and an application/json body (415) (fixed in d9dcc6d: CR-P3T17-01,
  SEC-P3T17-01 and SEC-P3T17-02 of round 1);
- api/workflows.py: resolve() takes an absolute path to a readable directory, or git_url(): an
  owner/repo name (GitHub), an https or ssh URL, no credentials, plain path parts, no control
  character; check_revision(): a revision is required and never starts with '-'; fetch(): git -c
  protocol.allow=never with https and ssh allowed again, GIT_TIMEOUT_S 300, once per revision into
  <data dir>/pipelines/<host>/<path>/<revision>; _open/_regular/_read: each part opened with
  O_NOFOLLOW from its parent's descriptor, a symlink is absent (SEC-P3T17-05 round 3 in 2d64827,
  SEC-P3T17-08 round 4 in 5e4d12f); MAX_FILE 1048576; load_yaml refuses aliases; _TOKENS is linear
  (SEC-P3T17-03 round 1 in d9dcc6d, CR-P3T17-03 round 2 in a837e46); ENTRY_FILES main.nf,
  Snakefile, workflow/Snakefile, engine None for both or neither; SchemaSource
  nextflow_schema.json, config.schema.yaml, inferred, none;
- api/runs_write.py: create_run checks the body whole (_check: one Snakemake profile at most),
  entry_files for the chosen engine (422 workflow.engine), _check_params (draft 7 or 2020-12, an
  empty Registry so no $ref is retrieved: SEC-P3T17-04 round 1 in d9dcc6d; inferred not
  enforced), then write_run_manifest, then one transaction (store/runs.py insert_run: workflows,
  workflow_versions, runs queued origin ui, run_inputs kind params, launches; then runner_commands
  kind launch, state pending); EngineConflict is a 422 on workflow.engine; 201 with Location;
- app.py: shared_host() (SLURM_CONF set, /etc/slurm/slurm.conf exists, sinfo on PATH, a /proc
  process of another uid >= 1000 with an account, not 65534); no_api_reason() is computed once in
  create_app and stored on app.state.no_api; serve.py start_text prints that same value
  (CR-P3T17-04 round 4 in 5e4d12f); otherwise every /api/v1 path answers 404 with the reason;
- open after round 5 (both reviewers approve), checked in the code at 3cbf735: no size cap on a
  clone (inbox #86 follow-up); shared_host runs once, at start (SEC-P3T17-07 round 4);
  _check_params does not catch RecursionError, so a schema {"$ref": "#"} is a 500 (SEC-P3T17-08
  round 3); _read does not catch an OSError from fstat or read (SEC-P3T17-09 round 5);
- the review counts and verdicts: the five rounds of `review-code`, review record
  docs/reviews/code/P3-t17.md. Blocker and major as the reviewers marked them; "major simplify"
  (CR-P3T17-02, round 1) counts as major.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1200
COL = (50, 355, 660, 965, 1270)  # five columns, 280 wide, 25 apart
CW = 280
ROW = 150  # the pictograms
TXT = ROW + 168  # the captions
NO = TXT + 128  # the refusals
FIX = NO + 50  # the findings fixed there
MID = 640  # the shared-host band
LOW = 880  # the review rounds

# (round, blocker, major, other, code-reviewer verdict, security-reviewer verdict)
ROUNDS = (
    ("R1", 2, 4, 8, "changes", "block"),
    ("R2", 0, 1, 6, "changes", "approve"),
    ("R3", 0, 2, 5, "approve", "changes"),
    ("R4", 0, 0, 7, "approve", "approve"),
    ("R5", 0, 0, 4, "approve", "approve"),
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


def person(s: Sketch, cx: float, top: float, size: float = 1.0) -> None:
    """A stick figure: one Unix user."""
    r = 7 * size
    s.circle(cx, top + r, r, fill="surface", width=1.6)
    s.line(cx, top + 2 * r, cx, top + 2 * r + 20 * size, amount=0.3, passes=1, width=1.8)
    s.line(cx - 11 * size, top + 2 * r + 8 * size, cx + 11 * size, top + 2 * r + 8 * size,
           amount=0.3, passes=1, width=1.6)
    for dx in (-8, 8):
        s.line(cx, top + 2 * r + 20 * size, cx + dx * size, top + 2 * r + 34 * size,
               amount=0.3, passes=1, width=1.6)


def sieve(s: Sketch, cx: float, top: float, w: float = 70, h: float = 46) -> None:
    s.poly([(cx - w / 2, top), (cx + w / 2, top), (cx + w * 0.14, top + h), (cx - w * 0.14, top + h)],
           fill="gate", amount=0.8)
    for dx, dy in ((-18, 12), (0, 12), (18, 12), (-9, 26), (9, 26)):
        s.dot(cx + dx, top + dy, 2.4, colour=s.t.dim)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=117)
    t = theme
    s.heading(50, 58, "P3 Task 17 · inspect a pipeline, then launch it",
              "`GET /api/v1/workflows:inspect` and `POST /api/v1/runs` · api 5 note of 2026-10-30 · "
              "dev-env 15.3 req. 4, 7 and 13 · a pipeline is read, never run, until it is launched")

    # 1 -- every request is checked -------------------------------------------------------------
    x = COL[0]
    s.browser(x, ROW, 156, 62, url="127.0.0.1")
    s.button(x + 30, ROW + 34, 96, "Load", fill="input", h=22)
    s.browser(x, ROW + 76, 156, 46, url="another site")
    s.arrow(x + 162, ROW + 30, x + 202, ROW + 52)
    s.arrow(x + 162, ROW + 100, x + 202, ROW + 72, dashed=True, colour=t.dim)
    s.cross(x + 182, ROW + 86, size=8)
    s.gate(x + 244, ROW + 98, w=60, h=70, state="open")
    s.text(x + 140, ROW + 150, "`api.browser`, before any route", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 1, "every request checked")
    lines(s, x, TXT + 30, ("Host `127.0.0.1`, `localhost` or `[::1]`",
                           "no request from another site:",
                           "Sec-Fetch-Site, Origin, Referer",
                           "a write: Origin and a JSON body"))
    refusal(s, x, NO, ("400 Host, 403 cross-site,", "415 a body that is not JSON"))
    fixed(s, x, FIX, ("fixed: R1 CR-P3T17-01,", "SEC-P3T17-01 and -02, DNS rebinding"))

    # 2 -- the location -------------------------------------------------------------------------
    x = COL[1]
    s.folder(x + 4, ROW + 4, 92, 56, fill="input", label="`/a/path`")
    s.link(x + 30, ROW + 96, size=15)
    s.text(x + 52, ROW + 101, "`owner/repo`", size=13, anchor="start")
    s.arrow(x + 102, ROW + 32, x + 160, ROW + 50, colour=t.dim)
    s.arrow(x + 150, ROW + 96, x + 168, ROW + 80)
    s.text(x + 130, ROW + 122, "`git`, once", size=12.5, colour=t.dim)
    s.folder(x + 166, ROW + 18, 112, 74, fill="cached", label="`pipelines`")
    s.text(x + 140, ROW + 150, "`data dir/pipelines/host/owner/repo/rev`", size=12.5, colour=t.dim)
    s.step(x + CW / 2, TXT, 2, "the location")
    lines(s, x, TXT + 30, ("an absolute path this account reads,",
                           "or `owner/repo`, an https or ssh URL",
                           "Git: a revision is required, fetched",
                           "once with `protocol.allow=never`, 300 s"))
    refusal(s, x, NO, ("422: credentials in the URL, `..`,", "a control character, a leading dash"))

    # 3 -- read, never run ----------------------------------------------------------------------
    x = COL[2]
    s.page(x + 14, ROW + 4, 70, 92, fill="surface", lines=4)
    s.magnifier(x + 76, ROW + 64, 18)
    s.link(x + 168, ROW + 30, size=16)
    s.cross(x + 168, ROW + 30, size=14)
    s.text(x + 168, ROW + 66, "a symlink", size=13, colour=t.dim)
    s.text(x + 168, ROW + 84, "is absent", size=13, colour=t.dim)
    s.text(x + 240, ROW + 34, "1 MiB", size=14, weight="bold")
    s.text(x + 240, ROW + 66, "per file,", size=13, colour=t.dim)
    s.text(x + 240, ROW + 84, "no aliases", size=13, colour=t.dim)
    s.text(x + 140, ROW + 150, "each part opened `O_NOFOLLOW`", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 3, "read, never run")
    lines(s, x, TXT + 30, ("`main.nf` or `Snakefile` names the engine,",
                           "none when both or neither",
                           "manifest name and version, profiles",
                           "schema: json, yaml, inferred or none"))
    refusal(s, x, NO, ("422: a file too large, bad YAML", "or JSON, a schema not a mapping"))
    fixed(s, x, FIX, ("fixed: R1 SEC-P3T17-03, R2 CR-P3T17-03,", "a linear `nextflow.config` scan;",
                      "R3 SEC-P3T17-05, R4 SEC-P3T17-08, symlinks"))

    # 4 -- the launch, checked whole ------------------------------------------------------------
    x = COL[3]
    s.page(x + 14, ROW + 4, 66, 88, fill="input", lines=4)
    s.text(x + 47, ROW + 110, "the body", size=12.5, colour=t.dim)
    s.arrow(x + 88, ROW + 44, x + 120, ROW + 44)
    sieve(s, x + 168, ROW + 16, w=84, h=58)
    s.arrow(x + 196, ROW + 50, x + 236, ROW + 34)
    s.tick(x + 256, ROW + 30, size=9)
    s.arrow(x + 168, ROW + 80, x + 168, ROW + 108, dashed=True, colour=t.dim)
    s.text(x + 200, ROW + 116, "422", size=14, weight="bold", colour=t.accent)
    s.text(x + 140, ROW + 150, "nothing is written before it passes", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 4, "`POST /runs`, checked whole")
    lines(s, x, TXT + 30, ("the location again, as inspect does",
                           "the chosen engine's file is there",
                           "Snakemake: one profile at most",
                           "params against the pipeline's schema"))
    refusal(s, x, NO, ("422 `errors`: a field, a message", "an inferred schema is not enforced"))
    fixed(s, x, FIX, ("fixed: R1 SEC-P3T17-04,", "no `$ref` retrieved, file or URL"))

    # 5 -- written, then leased -----------------------------------------------------------------
    x = COL[4]
    s.folder(x + 2, ROW + 4, 100, 70, fill="done", label="")
    s.page(x + 34, ROW + 22, 34, 44, fill="surface", lines=2)
    s.text(x + 52, ROW + 92, "run dir", size=12.5, colour=t.dim)
    s.bucket(x + 150, ROW + 10, 58, 52, fill="neutral")
    s.text(x + 150, ROW + 42, "DB", size=13, colour=t.dim)
    s.text(x + 150, ROW + 92, "one transaction", size=12.5, colour=t.dim)
    s.runner(x + 192, ROW + 30, w=86, h=46, label="runner")
    s.arrow(x + 182, ROW + 40, x + 196, ROW + 48, colour=t.dim)
    s.text(x + 140, ROW + 150, "201 and a `Location` header", size=13, colour=t.dim)
    s.step(x + CW / 2, TXT, 5, "written, then leased")
    lines(s, x, TXT + 30, ("the run directory and its manifest,",
                           "then workflow, version, run `queued`,",
                           "params, launch 1 and a `launch`",
                           "command the runner leases, Task 9"))
    refusal(s, x, NO, ("422 on `workflow.engine`: one engine", "per location, as api 7 says"))

    for cx in COL[:4]:
        s.arrow(cx + CW + 2, ROW + 50, cx + CW + 23, ROW + 50)

    # is the API mounted at all ---------------------------------------------------------------
    s.line(30, MID - 50, W - 30, MID - 50, dashed=True, colour=t.muted)
    s.text(50, MID - 60, "before all of this: is the API mounted at all? `create_app` decides once, "
           "at start, until sign-in, P1 Tasks 12 to 16", size=14, anchor="start", colour=t.dim)

    person(s, 90, MID + 10, 1.1)
    s.hpc_node(130, MID + 4, 54, 70, busy=1, slots=3)
    s.text(140, MID + 112, "one person's machine", size=15, weight="bold")
    s.text(140, MID + 134, "executor `local`", size=13.5, colour=t.dim)
    s.arrow(222, MID + 40, 290, MID + 40)
    s.gate(340, MID + 72, w=64, h=66, state="passed")
    s.text(400, MID + 26, "`/api/v1` mounted:", size=14, anchor="start")
    s.text(400, MID + 48, "inspect and runs", size=13.5, anchor="start", colour=t.dim)

    sx = 620
    s.text(sx, MID + 2, "looks shared when", size=15, anchor="start", weight="bold")
    lines(s, sx, MID + 28, ("the executor is not `local`",
                            "`SLURM_CONF` is set, or a `slurm.conf`",
                            "is in `/etc/slurm`, or `sinfo` on PATH",
                            "a process of another person, uid 1000",
                            "or above, not 65534, is in `/proc`",
                            "best effort: `hidepid` hides them"))
    s.arrow(sx - 18, MID + 70, sx - 60, MID + 70, dashed=True, colour=t.dim)
    s.text(sx - 39, MID + 90, "none", size=12.5, colour=t.dim)
    s.arrow(sx + 300, MID + 70, sx + 350, MID + 70, dashed=True, colour=t.dim)
    s.text(sx + 325, MID + 90, "any", size=12.5, colour=t.dim)

    nx = 990
    s.hpc_node(nx, MID + 4, 54, 70, busy=3)
    for i in range(3):
        person(s, nx + 82 + i * 30, MID + 18, 0.85)
    s.text(nx + 85, MID + 112, "a login node", size=15, weight="bold")
    s.text(nx + 85, MID + 134, "other Unix users", size=13.5, colour=t.dim)
    s.gate(nx + 226, MID + 72, w=64, h=66, state="closed")
    s.text(nx + 284, MID + 26, "every `/api/v1` path:", size=14, anchor="start")
    s.text(nx + 284, MID + 48, "404, with the reason", size=13.5, anchor="start", colour=t.dim)
    s.text(nx + 284, MID + 70, "and the start text", size=13.5, anchor="start", colour=t.dim)
    s.text(nx + 284, MID + 90, "says the same", size=13.5, anchor="start", colour=t.dim)

    s.text(620, MID + 168, "one scan feeds the routers and the start text, so the two always agree",
           size=13.5, anchor="start")
    fixed(s, 620, MID + 190, ("fixed: R4 CR-P3T17-04, the decision was made twice",))

    # the review rounds, to scale -------------------------------------------------------------
    s.line(30, LOW - 40, W - 30, LOW - 40, dashed=True, colour=t.muted)
    s.text(50, LOW, "5 review rounds, one cell per finding", size=17, anchor="start", weight="bold")
    s.text(50, LOW + 22, "code-reviewer and security-reviewer in parallel, each round", size=13.5,
           anchor="start", colour=t.dim)
    cell, gap, rh = 22, 3, 36
    for i, (rnd, blocker, major, other, cr, sec) in enumerate(ROUNDS):
        y = LOW + 48 + i * rh
        s.text(50, y + 16, rnd, size=15, anchor="start", weight="bold")
        groups = tuple((n, fill, "") for n, fill in ((blocker, "problem"), (major, "work"),
                                                      (other, "neutral")) if n)
        right = s.task_strip(90, y, groups, cell=cell, gap=gap, h=22)
        s.text(right + 6, y + 16, f"{blocker + major + other}", size=14, anchor="start")
        s.text(530, y + 16, f"CR {cr}, SEC {sec}", size=13.5, anchor="start",
               colour=t.ink if "approve" == cr == sec else t.dim)
        if cr == sec == "approve":
            s.tick(720, y + 10, size=7)
    ly = LOW + 48 + 5 * rh + 14
    for j, (fill, label) in enumerate((("problem", "blocker"), ("work", "major"),
                                       ("neutral", "minor or simplify"))):
        lx = 90 + j * 120
        s.poly([(lx, ly), (lx + 16, ly), (lx + 16, ly + 16), (lx, ly + 16)], fill=fill, amount=0.3)
        s.text(lx + 24, ly + 13, label, size=13, anchor="start", colour=t.dim)

    ox = 760
    s.shade(ox, LOW - 14, 790, 250, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.warning(ox + 28, LOW + 16, size=11)
    s.text(ox + 50, LOW + 22, "still open after round 5, both approve", size=15, anchor="start",
           weight="bold")
    open_items = (
        ("a clone has no size cap; each revision is kept", "inbox 86 follow-up"),
        ("the shared-host check runs once, at start:", "R4 SEC-P3T17-07"),
        ("    someone who logs in later is not seen", ""),
        ("a schema whose `$ref` points at itself is a 500", "R3 SEC-P3T17-08"),
        ("a read error after the open is a 500, not a 422", "R5 SEC-P3T17-09"),
        ("serving it at all before sign-in: Thomas decides", "inbox 86, reserved"),
    )
    for i, (what, where) in enumerate(open_items):
        y = LOW + 56 + i * 28
        if not what.startswith(" "):
            s.dot(ox + 30, y - 5, 3, colour=t.dim)
        s.text(ox + 46, y, what.strip(), size=13.5, anchor="start",
               colour=t.dim if what.startswith(" ") else t.ink)
        if where:
            s.text(ox + 770, y, where, size=12.5, anchor="end", colour=t.dim)

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(50, H - 16, "R1 to R5: the round a finding ID comes from; the reviewers number afresh "
           "each round", size=13, anchor="start", colour=t.dim)
    s.text(W - 50, H - 16, "source: spectio_server/api/browser.py, workflows.py, runs_write.py, app.py, "
           "serve.py · review record P3-t17 · P1 Task 17", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t17-launch")
