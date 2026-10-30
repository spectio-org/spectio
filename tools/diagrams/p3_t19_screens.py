#!/usr/bin/env python3
"""The screens, served beside the API, and the launch form: step P3, P1 Task 19, 2026-10-30.

Writes docs/assets/diagrams/p3-t19-screens_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t19 at ae5e988:
- packages/spectio-server/src/spectio_server/app.py: create_app(settings, writer, web_dir=static.DIST);
  reason = no_api_reason(settings), once; static.install only when reason is None and
  static.built(web_dir); otherwise "/" stays the plain page, with static.NOT_BUILT when the API is
  mounted, else the reason and "The screens are served with it."; TODO(P1 Task 16): behind the session;
- packages/spectio-server/src/spectio_server/static.py: DIST = parents[4] / "web" / "dist"
  (TODO(P1 Task 21): the wheel ships the screens); ROUTES "/", "/runs", "/launch", "/runs/{run_id}"
  answer index.html with Cache-Control no-cache; "/assets/{name}": ASSET one plain name, TYPES .js
  .css .svg .png .woff2, read(dist, "assets", name), public max-age=31536000 immutable; HEADERS: CSP
  (default-src 'none', script-src 'self', style-src 'self' 'unsafe-inline', connect-src 'self',
  frame-ancestors 'none') and nosniff; read() calls workflows._open (each step O_NOFOLLOW, the file
  O_NONBLOCK) and keeps regular files only (simplifier commit ae5e988, CR-P3T19-03);
  NOT_BUILT: "run `npm --prefix web ci && npm --prefix web run build`";
- packages/spectio-server/tests/api/test_web.py: the four routes, the asset types and caches, ten
  paths that answer 404, a symlinked file or assets directory, a FIFO, Host 400 and cross-site 403 on
  the screens, the API without the screens, the plain page on a shared host;
- web/src/routes.tsx: Home, Runs, Launch, Run; all but Launch say "This screen comes with P1 Task 20";
- web/src/launch/LaunchPage.tsx: Revision only when the Pipeline field is not an absolute path;
  load() calls inspect, then setEngine(guessEngine(engine_files)); edit() aborts the inspect in flight,
  setLoaded(null) and setEngine(null) (749f621, CR-P3T19-01); reason() keeps Launch focusable with
  aria-disabled and its reason; submit() posts launch() then onLaunched(run.id) to /runs/$id;
  paramValue: an enum sends the raw option whose text matches (749f621, CR-P3T19-02);
- web/src/launch/guessEngine.ts and web/src/api.ts ENGINE_FILES: main.nf nextflow; Snakefile,
  workflow/Snakefile snakemake; both or neither: null;
- web/src/launch/schemaFields.ts: one section per $defs or definitions group in allOf order, else the
  top-level properties; hidden fields skipped; no schema: name and value rows (KeyValueRows);
- web/src/launch/LaunchPage.test.tsx: "an integer enum is sent as its integer, not its text"
  (enum [1, 2], pick "2", params {level: 2});
- .github/workflows/ci.yml: job web, npm ci --ignore-scripts, npm test, npm run build, in ci-ok;
- the review rounds: the step's worker report of 2026-10-30, review record docs/reviews/code/P3-t19.md.
  Round 1: code-reviewer approve with CR-P3T19-01 to -06 (five minor, one simplify),
  security-reviewer approve with SEC-P3T19-01 to -03 (minor). Round 2: both approve, no finding.
  Fixed on the branch: CR-01 and CR-02 in 749f621, CR-03 by the simplifier in ae5e988. Still in the
  code at ae5e988: DIST found four levels up (SEC-01), the "not built" text runs npm ci with scripts
  (SEC-02), no Referrer-Policy (SEC-03), static.py carries only TODO(P1 Task 21) (CR-04).
  CR-05 (the live shot) and CR-06 (the Progress section) are docs-step items. No blocker, no major.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1420
TOP = 118  # the serving band
SRV = 520  # what the server answers
FORM = 770  # the launch form, its pictograms
FCOL = (50, 440, 830, 1220)  # four columns, 340 wide
FW = 340
LOW = 1150  # the review rounds

# (round, fixed, left open, code-reviewer verdict, security-reviewer verdict)
ROUNDS = (("R1", 3, 6, "approve", "approve"), ("R2", 0, 0, "approve", "approve"))


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, rows: tuple[str, ...], *, fixed: bool) -> None:
    """A finding pinned where it hits: a tick when the branch fixed it, a warning when it is open."""
    if fixed:
        s.tick(x + 8, y - 5, size=7)
    else:
        s.warning(x + 8, y - 5, size=8)
    s.text(x + 24, y, fid, size=13, anchor="start", weight="bold", colour=s.t.accent)
    for i, row in enumerate(rows):
        s.text(x + 24, y + 19 + i * 18, row, size=12.5, anchor="start", colour=s.t.dim)


def field(s: Sketch, x: float, y: float, w: float, label: str, value: str, *,
          dashed: bool = False) -> None:
    """A text input with its label above it."""
    s.text(x, y, label, size=12.5, anchor="start", colour=s.t.dim)
    if dashed:  # shown only in some cases
        s.shade(x, y + 6, w, 24, fill="surface", opacity=1.0, colour=s.t.dim, dashed=True)
    else:
        s.poly([(x, y + 6), (x + w, y + 6), (x + w, y + 30), (x, y + 30)], fill="surface", amount=0.4)
    s.text(x + 8, y + 23, value, size=12.5, anchor="start")


def toggle(s: Sketch, x: float, y: float, w: float, label: str, *, pressed: bool) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + 26), (x, y + 26)], fill="input" if pressed else "surface",
           amount=0.4, width=2.2 if pressed else 1.4)
    if pressed:
        s.tick(x + 14, y + 13, size=5, width=2)
    s.text(x + (w + (14 if pressed else 0)) / 2, y + 18, label, size=12.5,
           weight="bold" if pressed else "normal")


def plain_page(s: Sketch, x: float, y: float, w: float, h: float, rows: tuple[str, ...]) -> None:
    """The plain text page `/` keeps when the screens are not served."""
    s.page(x, y, w, h, fill="neutral", lines=0)
    for i, row in enumerate(rows):
        s.text(x + 8, y + 22 + i * 16, row, size=11, anchor="start", colour=s.t.dim)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=119)
    t = theme
    s.heading(50, 58, "P3 Task 19 · the screens, served beside the API, and the launch form",
              "`web/dist` at `/` by `spectio_server.static` · React, Mantine, TanStack Router · "
              "ui-spec 4.6 and 4.11 · inbox 88 · served only where the API is served")

    # the serving band ---------------------------------------------------------------------------
    s.terminal(50, TOP, 330, 92, ("$ npm --prefix web ci", "$ npm --prefix web run build"), size=12.5)
    s.text(215, TOP + 116, "Vite writes hashed assets", size=13, colour=t.dim)
    s.arrow(390, TOP + 46, 430, TOP + 46)
    s.folder(440, TOP - 4, 170, 104, fill="input")
    s.text(525, TOP + 30, "`web/dist`", size=13)
    s.page(470, TOP + 42, 34, 44, fill="surface", lines=2)
    s.page(512, TOP + 42, 34, 44, fill="surface", lines=2)
    s.page(554, TOP + 42, 34, 44, fill="surface", lines=2)
    s.text(525, TOP + 122, "beside `packages/`, until Task 21", size=13, colour=t.dim)
    s.text(525, TOP + 140, "ships it in the wheel", size=13, colour=t.dim)
    pin(s, 440, TOP + 172, "SEC-P3T19-01", ("found four levels up from the", "module, no owner check"),
        fixed=False)

    s.arrow(620, TOP + 46, 680, TOP + 46)
    s.hpc_node(690, TOP + 6, 54, 72, busy=1, slots=3)
    s.cog(770, TOP + 30, 11, fill="docs")
    s.text(722, TOP + 104, "`spectio serve`", size=13.5)
    s.text(722, TOP + 124, "`create_app` decides", size=13, colour=t.dim)
    s.text(722, TOP + 142, "once, at start", size=13, colour=t.dim)

    ox = 900  # the three outcomes
    s.arrow(800, TOP + 30, ox - 10, TOP + 30)
    s.arrow(800, TOP + 46, ox - 10, TOP + 140, dashed=True, colour=t.dim)
    s.arrow(800, TOP + 60, ox - 10, TOP + 250, dashed=True, colour=t.dim)

    s.gate(ox + 34, TOP + 58, w=50, h=52, state="passed")
    s.browser(ox + 80, TOP - 4, 200, 76, url="127.0.0.1 /launch")
    toggle(s, ox + 96, TOP + 36, 84, "Nextflow", pressed=True)
    s.poly([(ox + 192, TOP + 36), (ox + 266, TOP + 36), (ox + 266, TOP + 62), (ox + 192, TOP + 62)],
           fill="surface", amount=0.4)
    s.text(ox + 300, TOP + 16, "API mounted and built:", size=14, anchor="start", weight="bold")
    lines(s, ox + 300, TOP + 38, ("the screens at `/`, `/runs`,", "`/launch` and `/runs/id`",
                                  "Home and Runs: Task 20"), size=13)

    y2 = TOP + 112
    s.gate(ox + 34, y2 + 58, w=50, h=52, state="closed")
    plain_page(s, ox + 80, y2, 200, 78, ("Spectio is running.", "looks shared, a process",
                                         "of uid 1001 runs here", "The screens are served with it."))
    s.text(ox + 300, y2 + 16, "API not mounted:", size=14, anchor="start", weight="bold")
    lines(s, ox + 300, y2 + 38, ("a shared host, inbox 86", "`/` says why, the plain page",
                                 "`/launch` and `/assets` 404"), size=13)

    y3 = TOP + 222
    s.warning(ox + 34, y3 + 32, size=13)
    plain_page(s, ox + 80, y3, 200, 78, ("The screens are not built:", "run `npm --prefix web ci`",
                                         "then start spectio serve", "again"))
    s.text(ox + 300, y3 + 16, "`web/dist` missing:", size=14, anchor="start", weight="bold")
    lines(s, ox + 300, y3 + 38, ("`/` says how to build it,", "the API answers as before",
                                 "`/launch` 404"), size=13)

    # what the server answers --------------------------------------------------------------------
    s.line(30, SRV - 46, W - 30, SRV - 46, dashed=True, colour=t.muted)
    s.text(50, SRV - 56, "when served, `spectio_server.static` answers only these, and the "
           "browser checks of Task 17 run first", size=14, anchor="start", colour=t.dim)

    x = 50
    s.page(x, SRV, 46, 58, fill="surface", lines=3)
    s.text(x + 23, SRV + 76, "`index.html`", size=12)
    s.text(x + 66, SRV + 16, "4 routes", size=15, anchor="start", weight="bold")
    lines(s, x + 66, SRV + 38, ("`/` `/runs` `/launch` `/runs/id`", "`Cache-Control: no-cache`",
                                "no other fallback"), size=13)

    x = 420
    for i, ext in enumerate(("js", "css", "svg")):
        s.page(x + i * 30, SRV + i * 6, 34, 46, fill="cached", lines=0)
        s.text(x + 17 + i * 30, SRV + 34 + i * 6, ext, size=11)
    s.text(x + 118, SRV + 16, "`/assets/name`", size=15, anchor="start", weight="bold")
    lines(s, x + 118, SRV + 38, ("one plain name, a web type", "opened `O_NOFOLLOW` each step,",
                                 "regular files, a FIFO never waits", "cached a year, `immutable`"),
          size=13)
    pin(s, x + 118, SRV + 140, "CR-P3T19-03", ("simplify: one walk, `workflows._open`,",
                                               "not a second copy, ae5e988"), fixed=True)

    x = 860
    s.link(x + 20, SRV + 18, size=15)
    s.cross(x + 20, SRV + 18, size=13)
    s.text(x + 20, SRV + 64, "404", size=15, weight="bold", colour=t.accent)
    s.text(x + 52, SRV + 16, "everything else", size=15, anchor="start", weight="bold")
    lines(s, x + 52, SRV + 38, ("`/index.html`, `/nope`, `/launch/x`", "a dot name, a subfolder, `..`",
                                "a symlinked file or `assets`"), size=13)

    x = 1250
    s.lock(x + 18, SRV + 20, size=16, fill="done")
    s.text(x + 44, SRV + 16, "every answer", size=15, anchor="start", weight="bold")
    lines(s, x + 44, SRV + 38, ("a CSP: this origin only,", "no inline script, `nosniff`",
                                "Host 400, cross-site 403"), size=13)
    pin(s, x + 44, SRV + 120, "SEC-P3T19-03", ("no Referrer-Policy yet",), fixed=False)

    # the launch form ----------------------------------------------------------------------------
    s.line(30, FORM - 52, W - 30, FORM - 52, dashed=True, colour=t.muted)
    s.text(50, FORM - 62, "on `/launch`, in this order", size=14, anchor="start", colour=t.dim)
    STEP = FORM + 150
    TXT = STEP + 30
    PIN = TXT + 104

    x = FCOL[0]
    field(s, x + 10, FORM + 4, 200, "Pipeline", "`nf-core/rnaseq`")
    field(s, x + 222, FORM + 4, 104, "Revision", "`3.14.0`", dashed=True)
    s.arrow(x + 274, FORM + 74, x + 274, FORM + 42, colour=t.dim)
    s.text(x + 274, FORM + 92, "appears", size=12.5, colour=t.dim)
    field(s, x + 10, FORM + 60, 200, "or a path", "`/g/lab/pipelines/x`")
    s.step(x + FW / 2, STEP, 1, "the pipeline")
    lines(s, x, TXT, ("an absolute path, `owner/repo`,", "an https or ssh URL",
                      "Revision only for a repository,", "required there, UX-G2-08"))

    x = FCOL[1]
    s.button(x + 6, FORM + 16, 70, "Load", fill="surface", h=30)
    s.arrow(x + 82, FORM + 31, x + 112, FORM + 31)
    s.page(x + 118, FORM, 54, 70, fill="surface", lines=3)
    s.magnifier(x + 162, FORM + 50, 14)
    s.text(x + 145, FORM + 104, "`main.nf`", size=12.5)
    s.arrow(x + 190, FORM + 31, x + 214, FORM + 31)
    toggle(s, x + 220, FORM + 6, 112, "Nextflow", pressed=True)
    toggle(s, x + 220, FORM + 42, 112, "Snakemake", pressed=False)
    s.text(x + 276, FORM + 98, "`aria-pressed`", size=12.5, colour=t.dim)
    s.step(x + FW / 2, STEP, 2, "Load, then a guess")
    lines(s, x, TXT, ("`workflows:inspect` reads, never runs", "`main.nf`: Nextflow",
                      "`Snakefile`, `workflow/Snakefile`: Snakemake", "both or neither: you choose"))
    pin(s, x, PIN, "CR-P3T19-01", ("an edit aborts the inspect and now", "forgets the guess too, 749f621"),
        fixed=True)

    x = FCOL[2]
    for i, (title, n) in enumerate((("Input", 2), ("Options", 2))):
        y = FORM + i * 58
        s.text(x + 10, y + 10, title, size=12.5, anchor="start", weight="bold")
        for j in range(n):
            s.poly([(x + 10 + j * 108, y + 18), (x + 110 + j * 108, y + 18), (x + 110 + j * 108, y + 40),
                    (x + 10 + j * 108, y + 40)], fill="surface", amount=0.4)
    s.text(x + 66, FORM + 92, "`level`", size=12.5, anchor="end")
    s.poly([(x + 74, FORM + 78), (x + 124, FORM + 78), (x + 124, FORM + 100), (x + 74, FORM + 100)],
           fill="input", amount=0.4)
    s.text(x + 92, FORM + 95, "2", size=13)
    s.text(x + 114, FORM + 94, "v", size=11, colour=t.dim)
    s.page(x + 240, FORM - 2, 56, 72, fill="docs", lines=3)
    s.text(x + 268, FORM + 90, "the schema", size=12.5, colour=t.dim)
    s.arrow(x + 236, FORM + 30, x + 226, FORM + 30, colour=t.dim)
    s.step(x + FW / 2, STEP, 3, "the parameters")
    lines(s, x, TXT, ("one section per `$defs` group,", "or the top-level properties",
                      "no schema: name and value rows", "a value is sent only when set"))
    pin(s, x, PIN, "CR-P3T19-02", ("enum 1 or 2 now sends `level: 2`,", "it sent the text, a 422, 749f621"),
        fixed=True)

    x = FCOL[3]
    s.button(x + 6, FORM + 18, 80, "Launch", fill="done", h=32)
    s.arrow(x + 92, FORM + 34, x + 140, FORM + 34)
    s.text(x + 116, FORM + 24, "201", size=12.5, colour=t.dim)
    s.browser(x + 146, FORM, 184, 72, url="/runs/run_01K8")
    s.text(x + 238, FORM + 54, "Task 20", size=13, colour=t.dim)
    s.text(x + 46, FORM + 72, "`POST /api/v1/runs`", size=12.5)
    s.text(x + 46, FORM + 98, "not ready: a reason beside it", size=12.5, anchor="start", colour=t.dim)
    s.step(x + FW / 2, STEP, 4, "Launch, then the run")
    lines(s, x, TXT, ("stays focusable, `aria-disabled`,", "its reason in `aria-describedby`",
                      "a 422 lands on its own field", "then the run page, Task 20"))

    for cx in FCOL[:3]:
        s.arrow(cx + FW + 8, FORM + 34, cx + FW + 40, FORM + 34)

    # the review rounds, to scale ----------------------------------------------------------------
    s.line(30, LOW - 40, W - 30, LOW - 40, dashed=True, colour=t.muted)
    s.text(50, LOW, "2 review rounds, one cell per finding", size=17, anchor="start", weight="bold")
    s.text(50, LOW + 22, "code-reviewer and security-reviewer in parallel, then the simplifier",
           size=13.5, anchor="start", colour=t.dim)
    cell, rh = 22, 38
    for i, (rnd, fixed, left, cr, sec) in enumerate(ROUNDS):
        y = LOW + 46 + i * rh
        s.text(50, y + 16, rnd, size=15, anchor="start", weight="bold")
        groups = tuple((n, fill, "") for n, fill in ((fixed, "done"), (left, "neutral")) if n)
        right = s.task_strip(90, y, groups, cell=cell, gap=3, h=22) if groups else 90
        s.text(right + 6, y + 16, f"{fixed + left}" if groups else "no finding", size=14, anchor="start")
        s.text(400, y + 16, f"CR {cr}, SEC {sec}", size=13.5, anchor="start")
        s.tick(580, y + 10, size=7)
    ly = LOW + 46 + 2 * rh + 6
    for j, (fill, label) in enumerate((("done", "fixed on the branch"), ("neutral", "minor, left open"))):
        lx = 90 + j * 190
        s.poly([(lx, ly), (lx + 16, ly), (lx + 16, ly + 16), (lx, ly + 16)], fill=fill, amount=0.3)
        s.text(lx + 24, ly + 13, label, size=13, anchor="start", colour=t.dim)
    s.text(50, ly + 46, "no blocker, no major · the simplifier: 14 lines out, 8 in, same 503 tests",
           size=13.5, anchor="start")
    s.text(50, ly + 68, "CI job `web`: `npm ci --ignore-scripts`, `npm test`, `npm run build`, "
           "in `ci-ok`", size=13.5, anchor="start", colour=t.dim)

    bx = 760
    s.shade(bx, LOW - 18, 790, 196, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.warning(bx + 28, LOW + 10, size=11)
    s.text(bx + 50, LOW + 16, "left open after round 2, both approve", size=15, anchor="start",
           weight="bold")
    open_items = (
        ("`web/dist` found four levels up, no owner check", "SEC-P3T19-01"),
        ("the build hint runs `npm ci` with install scripts on", "SEC-P3T19-02"),
        ("no Referrer-Policy on the screens", "SEC-P3T19-03"),
        ("inbox 88 says Task 16 TODO in `static.py` too", "CR-P3T19-04"),
        ("the live shot needs a running serve, by hand", "CR-P3T19-05"),
        ("the Progress section waits for the docs step", "CR-P3T19-06"),
    )
    for i, (what, fid) in enumerate(open_items):
        y = LOW + 44 + i * 24
        s.dot(bx + 30, y - 5, 3, colour=t.dim)
        s.text(bx + 46, y, what, size=13.5, anchor="start")
        s.text(bx + 770, y, fid, size=12.5, anchor="end", colour=t.dim)

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(50, H - 16, "a tick: fixed on the branch · a warning: left open", size=13, anchor="start",
           colour=t.dim)
    s.text(W - 50, H - 16, "source: spectio_server/app.py, static.py, web/src/launch, routes.tsx, "
           "ci.yml at ae5e988 · review record P3-t19 · P1 Task 19", size=12.5, anchor="end",
           colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t19-screens")
