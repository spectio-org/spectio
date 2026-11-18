#!/usr/bin/env python3
"""The pipeline catalog built, the OME-TIFF viewer and its channels, a refused sacct window made
final, and a pass on the run pages, Environments, Profile and the runs table: batch P3-B14 (steps
FU-P3-87a, -87b, -87c, -87d, -102e, -102f, -106b, -104, -111, -112, -115a, wave W5), 2026-11-10.

Writes docs/assets/diagrams/p3-b14-catalog-viewer-pages_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B14 at bf240d20 (the 11 PRs squash-merged into
autopilot/integration between 95d4a651 and bf240d20; the steps of batches P3-B12 and P3-B13 in that
range are not drawn; the batch code-simplifier changed nothing). Steps are numbered in merge order:
- 1, FU-P3-87a, PR 223: packages/spectio/src/spectio/catalog.py (FILE "catalog.toml", MAX_ENTRIES
  100, `Entry` name, label, engine nextflow or snakemake, location, revision, profile,
  params_file; read and written by `spectio.envfile` beside environments.toml);
  spectio/locations.py (`check_location`, `check_revision` "a Git repository needs a revision",
  `check_params_file` ".json, .yaml or .yml", `git_url` "credentials do not belong in the URL",
  "not a URL"); api/workflows.py calls them; record docs/reviews/code/P3-fu87a.md (SEC-P3FU87A-01
  major fixed in 9acea98e; 6 + 1 minors);
- 2, FU-P3-106b, PR 224: packages/spectio/src/spectio/runner/sacct.py (TOO_WIDE "Too wide of a date
  range in query" read from the first MAX_STDERR 4096 bytes, `TooWide`, SITE_LIMIT
  "max_query_time_range"); spectio_server/failure.py (only the jobs whose `since` is the call's
  lowest -S are given up, the others asked again); before it, a non-zero exit was retried under the
  back-off until the give-up; test `test_sacct_site_limit_gives_up_only_the_oldest_run` (jobs
  8812401 and 8812402, 2 calls, the recent run's row OUT_OF_MEMORY); record P3-fu106b.md
  (SEC-P3FU106B-01 major fixed in ff2c12f1; 4 minors);
- 3, FU-P3-87b, PR 225: spectio_server/api/catalog.py (GET and POST /catalog, GET, PUT and DELETE
  /catalog/{name}, ETag and If-Match, 409 catalog-entry-exists); api/workflows.py
  (MAX_PARAMS_FILE 256 KiB, MAX_DEPTH 32, `read_params` "<file> cannot be read: not YAML",
  `values: null` and an `error`, never a refusal); record P3-fu87b.md (CR-P3FU87B-01 blocker and
  SEC-P3FU87B-01 major, fixed test first);
- 4, FU-P3-87c, PR 226: design/ui-canvas LiteCatalog, LiteCatalogEntry, LiteCatalogStates and
  MLiteCatalog new, LiteLaunch, MLiteLaunch and LiteTopbar with the picker; record P3-fu87c.md
  (minors only; ux-reviewer approve 0/0/8);
- 5, FU-P3-102e, PR 227: web/src/runs/imaging/OmeView.tsx, viv.ts (CACHE_MAX 256 MiB of tiles),
  walk.ts (LEVELS_MAX 20); Viv 0.23.0, deck.gl 9.4.1, luma.gl 9.4.2; chunk OmeView-*.js 1,232.7 kB
  (340.7 kB gzip); `npm audit --omit=dev` 17 (3 moderate, 14 high) then 0; THIRD_PARTY_NOTICES.txt
  203 runtime packages; record P3-fu102e.md (blockers CR-01 with SEC-01, CR-02; majors CR-03, CR-04
  with SEC-09, SEC-02, SEC-03, SEC-04 fixed; SEC-05 open as a deferral, inbox 148);
- 6, FU-P3-87d, PR 228: web/src/catalog/ CatalogPage.tsx, CatalogList.tsx, CatalogForm.tsx (Add
  pipeline; Label, Engine, Pipeline, Revision, Default profile, Params file); the example entry is
  LaunchCatalog.test.tsx:17-18 (rnaseq-test, nf-core/rnaseq 3.27.0); record P3-fu87d.md (minors
  only, CR-02 fixed test first);
- 7, FU-P3-102f, PR 230: imaging/Channels.tsx (Show channel, contrast, Reset contrast), url-state.ts
  (KEYS z, t, ch, zoom, x, y; CHANNELS_ON 6; replaceState); record P3-fu102f.md (CR-P3FU102F-01
  blocker not reproduced, CR-P3FU102F-02 major fixed test first);
- 8, FU-P3-104, PR 237: web/src/shell/TopBar.tsx `crumbsFor` (Home, Runs, the run, Results or Work
  directory, the file name from `stat`, "File" until then), RunHeader.tsx `sp-text-link`; record
  P3-fu104.md (CR-P3FU104-01 and -02 majors fixed);
- 9, FU-P3-111, PR 238: web/src/environments/EnvironmentsPage.tsx (KIND_ICONS slurm server, local
  terminal; "Show environments as" Cards or Table, `?view=table`; "Duplicate to edit" to
  /environments/new?from=<name>, `<name>-copy`); RESERVED local and slurm in
  spectio/environments.py; record P3-fu111.md (minors only, CR-02 fixed);
- 10, FU-P3-112, PR 241: spectio_server/api/me.py (`GET /me`: principal user and uid, session
  started_at, paths config_file, data_dir, db_dir, observed_dir); auth/routes.py
  (`POST /auth/session:sign-out`, 204); web/src/profile/ProfilePage.tsx (cards Who the server runs
  as, This session, Config paths, Theme with Light, Dark, System); record P3-fu112.md
  (CR-P3FU112-01 major fixed in ab646741);
- 11, FU-P3-115a, PR 242: spectio_server/api/runs_manage.py (`POST /runs:delete`, MAX_DELETE 200,
  409 run-not-ended and directory-not-removable, `remove_run_dir` rmtree relative to the runs
  root's descriptor, the lineage root removed too; `PATCH /runs/{run_id}` pinned); runs_read.py
  (pinned runs first); migration 0012_run_pinned; record P3-fu115a.md (minors only, 2 fixed);
- lines per step: `git show --numstat <merge> -- . ':!docs' ':!.autopilot'`, split into tests
  (paths with `test`, `tests/` or `fixtures`), boards (`design/`), lockfile and notices
  (`package.json`, `package-lock.json`, `THIRD_PARTY_NOTICES`, the wheel manifest) and the rest;
- pytest: `uv run --locked pytest -q --collect-only` at each step's merge and its first parent, run
  2026-11-10 for this figure (1,433 at 9f11c6d9 before step 1; +57, +6, +62, +1, +6 and +42 in steps
  1, 2, 3, 6, 10 and 11; 1,607 at bf240d20); web cases added: lines that open an `it(` or `test(`
  in the step's diff of .ts and .tsx files (vitest not run: web/node_modules not installed);
- the batch simplifier: no change at bf240d20, its gate pytest 1,603 passed and 4 skipped, ruff,
  mypy, lint-imports and `uv lock --check` pass.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 2000, 2610
COLS = tuple(40 + i * 490 for i in range(4))
CW = 450
R1, R2, R3, LOW = 165, 810, 1555, 2210  # each row's step names; LOW the bottom band


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13) -> float:
    for i, row in enumerate(rows):
        s.text(x, y + i * 20, row, size=size, anchor="start", colour=s.t.ink if i == 0 else s.t.dim)
    return y + 20 * len(rows)


def pin(s: Sketch, x: float, y: float, fid: str, tag: str, what: str, status: str, *,
        w: float = CW, state: str = "fixed") -> float:
    """A blocker or major pinned where it hit: its ID, what it was, how it ended."""
    h = 62
    fill = {"fixed": "done", "open": "problem", "none": "neutral"}[state]
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.5, width=1.2)
    if state == "fixed":
        s.tick(x + 14, y + 13, size=5.5)
    elif state == "open":
        s.warning(x + 14, y + 14, size=7)
    else:
        s.circle(x + 14, y + 14, 5.5)
    s.text(x + 28, y + 19, fid, size=12, anchor="start", weight="bold")
    s.text(x + w - 8, y + 19, tag, size=11.5, anchor="end",
           colour=s.t.accent if "blocker" in tag else s.t.dim)
    s.text(x + 10, y + 38, what, size=12, anchor="start")
    s.text(x + 10, y + 55, status, size=12, anchor="start", colour=s.t.dim)
    return y + h + 8


def note(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, w: float = CW,
         warn: bool = False) -> float:
    """A dashed note: the rounds and what is open."""
    h = 12 + 19 * len(rows)
    s.shade(x, y, w, h, fill="neutral", opacity=0.45, colour=s.t.muted, dashed=True)
    ox = 22 if warn else 0
    if warn:
        s.warning(x + 16, y + 17, size=7)
    for i, row in enumerate(rows):
        s.text(x + 10 + (ox if i == 0 else 0), y + 22 + i * 19, row, size=12, anchor="start",
               colour=s.t.ink if i == 0 else s.t.dim)
    return y + h


def band(s: Sketch, y: float, title: str) -> None:
    s.line(30, y, W - 30, y, dashed=True, colour=s.t.muted)
    s.text(50, y - 10, title, size=14.5, anchor="start", colour=s.t.dim)


def cell(s: Sketch, x: float, y: float, w: float, h: float, fill: str = "surface") -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.3, width=1.1)


def chip(s: Sketch, x: float, y: float, w: float, label: str, fill: str, *, h: float = 20,
         size: float = 10.5) -> None:
    cell(s, x, y, w, h, fill)
    s.text(x + w / 2, y + h / 2 + size * 0.38, label, size=size)


def small(s: Sketch, x: float, y: float, text: str, *, size: float = 11, dim: bool = True,
          anchor: str = "start") -> None:
    s.text(x, y, text, size=size, anchor=anchor, colour=s.t.dim if dim else s.t.ink)


def head(s: Sketch, x: float, y: float, title: str) -> None:
    s.text(x, y, title, size=14.5, anchor="start", weight="bold")


def picture(s: Sketch, x: float, y: float, w: float, h: float) -> None:
    """An image: a frame and three blobs of colour."""
    cell(s, x, y, w, h, "neutral")
    for cx, cy, r, fill in ((0.3, 0.4, 0.16, "bar_blue"), (0.62, 0.55, 0.2, "bar_green"),
                            (0.45, 0.72, 0.12, "bar_violet")):
        s.circle(x + w * cx, y + h * cy, h * r, fill=fill, width=1.0)


def slider(s: Sketch, x: float, y: float, w: float, at: float) -> None:
    s.line(x, y, x + w, y, colour=s.t.muted, passes=1, amount=0.2, width=2)
    s.circle(x + w * at, y, 4.5, fill="input", width=1.1)


def switch(s: Sketch, x: float, y: float, on: bool) -> None:
    cell(s, x, y, 22, 12, "done" if on else "neutral")
    s.dot(x + (16 if on else 6), y + 6, 4, colour=s.t.ink if on else s.t.muted)


def chevron(s: Sketch, x: float, y: float) -> None:
    s.line(x, y - 4, x + 4, y, colour=s.t.dim, passes=1, amount=0.1, width=1.2)
    s.line(x + 4, y, x, y + 4, colour=s.t.dim, passes=1, amount=0.1, width=1.2)


def crumbs(s: Sketch, x: float, y: float, parts: tuple[str, ...], *, last_fill: str = "done") -> float:
    """A breadcrumb row; the last part, the current page, sits on a fill."""
    for i, part in enumerate(parts):
        wpx = 7.2 * len(part) + 8
        if i == len(parts) - 1:
            cell(s, x - 3, y - 13, wpx, 18, last_fill)
        s.text(x, y, part, size=11.5, anchor="start", colour=s.t.ink if i == len(parts) - 1 else s.t.dim)
        x += wpx
        if i < len(parts) - 1:
            chevron(s, x - 2, y - 4)
            x += 10
    return x


def pushpin(s: Sketch, cx: float, cy: float, *, on: bool = True) -> None:
    s.circle(cx, cy - 3, 4.5, fill="problem" if on else "surface", width=1.1)
    s.line(cx, cy + 1, cx, cy + 9, colour=s.t.ink if on else s.t.muted, passes=1, amount=0.1, width=1.4)


def trash(s: Sketch, x: float, y: float, w: float = 26, h: float = 30) -> None:
    s.line(x - 3, y, x + w + 3, y, passes=1, amount=0.2, width=1.6)
    s.line(x + w * 0.35, y - 4, x + w * 0.65, y - 4, passes=1, amount=0.2, width=1.6)
    s.poly([(x, y + 2), (x + w, y + 2), (x + w - 3, y + h), (x + 3, y + h)], fill="neutral",
           amount=0.3, width=1.3)
    for k in (0.33, 0.66):
        s.line(x + w * k, y + 8, x + w * k, y + h - 5, colour=s.t.dim, passes=1, amount=0.1, width=1)


def avatar(s: Sketch, cx: float, cy: float, r: float = 13) -> None:
    s.circle(cx, cy, r, fill="docs", width=1.3)
    s.circle(cx, cy - r * 0.25, r * 0.32, width=1.1)
    s.line(cx - r * 0.5, cy + r * 0.55, cx + r * 0.5, cy + r * 0.55, passes=1, amount=0.2, width=1.2)


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4, width=1.2)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=1414)
    t = theme
    s.heading(50, 58, "P3-B14 · the pipeline catalog built, the OME-TIFF viewer and its channels, "
              "a final sacct refusal, and a pass on the run pages",
              "wave W5 · 11 steps · 2026-11-10 · PRs 223 to 228, 230, 237, 238, 241 and 242 into "
              "`autopilot/integration` · steps numbered in merge order")

    # ================================================================================================
    # row 1: FU-P3-87, the catalog, server first
    band(s, R1 - 38, "FU-P3-87 the pipeline catalog, built server first: the file and its checks, "
         "the routes, the boards, the page · steps 1, 3, 4 and 6 · Launch's picker came in batch P3-B13")
    top = R1 + 20
    cap = top + 270

    # 1 -- FU-P3-87a ----------------------------------------------------------------------------
    x = COLS[0]
    head(s, x, R1, "FU-P3-87a · PR 223 · server")
    s.folder(x + 2, top + 6, 216, 136, fill="gate")
    s.page(x + 14, top + 30, 92, 76, fill="neutral", lines=3)
    s.page(x + 116, top + 30, 92, 76, fill="input", lines=3)
    small(s, x + 60, top + 124, "`environments.toml`", size=9, anchor="middle")
    small(s, x + 162, top + 124, "`catalog.toml`", size=9, anchor="middle", dim=False)
    small(s, x + 110, top + 162, "one reader, `envfile`, at most 100 entries", size=10.5,
          anchor="middle")
    s.arrow(x + 224, top + 80, x + 258, top + 80)
    s.text(x + 300, top + 16, "`spectio.locations`", size=11)
    s.gate(x + 296, top + 118, w=58, h=52, state="open")
    for i, label in enumerate(("location", "revision", "params file")):
        s.tick(x + 346, top + 58 + i * 22, size=4.5)
        small(s, x + 356, top + 62 + i * 22, label, size=11, dim=False)
    small(s, x + 250, top + 146, "also called by inspect", size=10.5)
    small(s, x + 250, top + 162, "and `POST /runs`", size=10.5)
    chip(s, x + 2, top + 190, 170, "`https://u:pw@host/r`", "problem", h=22, size=10)
    s.cross(x + 186, top + 201, size=6)
    small(s, x + 202, top + 205, "credentials do not belong in the URL", size=10.5)
    s.step(x + CW / 2, cap, 1, "the catalog file and the shared checks", size=18)
    y = lines(s, x, cap + 28, ("an entry: name, label, engine, location, revision,",
                               "profile and params file, one table each",
                               "a bad value makes the file invalid, never a 500"))
    y = pin(s, x, y + 6, "SEC-P3FU87A-01", "r1 major",
            "`urlsplit`'s error quoted the URL, credentials and all",
            "fixed test first: a fixed message, not a URL")
    note(s, x, y, ("2 rounds · CR approve, SEC approve",
                   "7 minors open, none blocking"))

    # 3 -- FU-P3-87b ----------------------------------------------------------------------------
    x = COLS[1]
    head(s, x, R1, "FU-P3-87b · PR 225 · server")
    s.terminal(x + 2, top + 4, 236, 140, ("GET    /catalog", "POST   /catalog",
                                          "GET    /catalog/<name>", "PUT    /catalog/<name>",
                                          "DELETE /catalog/<name>"), size=11, line_h=18)
    small(s, x + 252, top + 24, "PUT and DELETE", size=11, dim=False)
    small(s, x + 252, top + 40, "need If-Match, the ETag", size=10.5)
    small(s, x + 252, top + 64, "a name twice: 409", size=11, dim=False)
    small(s, x + 252, top + 80, "`catalog-entry-exists`", size=10)
    small(s, x + 252, top + 104, "each write logged with", size=10.5)
    small(s, x + 252, top + 120, "its old and new value", size=10.5)
    s.page(x + 2, top + 158, 52, 62, fill="input", lines=3)
    small(s, x + 28, top + 238, "`conf/test.yaml`", size=9.5, anchor="middle")
    s.arrow(x + 62, top + 190, x + 112, top + 190)
    small(s, x + 87, top + 180, "inspect", size=10, anchor="middle")
    chip(s, x + 118, top + 158, 114, "`values`: its map", "done", h=22, size=10.5)
    chip(s, x + 118, top + 192, 114, "`values: null`", "problem", h=22, size=10.5)
    small(s, x + 240, top + 174, "every top-level key", size=10.5)
    small(s, x + 240, top + 207, "and the words: cannot", size=10.5)
    small(s, x + 240, top + 222, "be read: not YAML", size=10.5)
    s.step(x + CW / 2, cap, 3, "the catalog routes, a params file in inspect", size=18)
    y = lines(s, x, cap + 28, ("list, add, read, replace and delete an entry",
                               "a params file: at most 256 KiB, 32 levels deep",
                               "whatever goes wrong: words, never a refusal"))
    y = pin(s, x, y + 6, "CR-P3FU87B-01", "r1 blocker",
            "a file with `NaN`, `.inf` or a date key: inspect answered 500",
            "fixed test first: `values: null` and an error")
    y = pin(s, x, y, "SEC-P3FU87B-01", "r1 major",
            "a YAML key that is not a string raised TypeError: 500",
            "fixed test first, in `read_params` and `inspect_dir`")
    note(s, x, y, ("2 rounds · CR approve, SEC approve",
                   "open: `schema_of` still accepts NaN, 4 minors"))

    # 4 -- FU-P3-87c ----------------------------------------------------------------------------
    x = COLS[2]
    head(s, x, R1, "FU-P3-87c · PR 226 · boards")
    for i, name in enumerate(("LiteCatalog", "LiteCatalogEntry", "LiteCatalogStates")):
        bx, by = x + 2 + i * 118, top + 4
        s.browser(bx, by, 108, 92)
        for r in range(3):
            cell(s, bx + 10, by + 40 + r * 15, 88 - (r % 2) * 22, 10, "input" if i == 0 else
                 ("surface" if i == 1 else ("problem" if r == 1 else "neutral")))
        small(s, bx + 54, by + 110, name, size=10, anchor="middle", dim=False)
    s.phone(x + 362, top, 64, 116)
    for r in range(3):
        cell(s, x + 376, top + 32 + r * 16, 36, 10, "input")
    small(s, x + 394, top + 132, "MLiteCatalog", size=10, anchor="middle", dim=False)
    small(s, x + 2, top + 150, "new, plus the picker drawn in:", size=11, dim=False)
    for i, name in enumerate(("LiteLaunch", "MLiteLaunch", "LiteTopbar")):
        chip(s, x + 2 + i * 104, top + 160, 96, name, "docs", h=20, size=10.5)
    s.page(x + 2, top + 196, 134, 46, fill="surface", lines=0)
    small(s, x + 10, top + 214, "Loaded card", size=10, dim=False)
    chip(s, x + 10, top + 220, 100, "Save to catalog", "docs", h=16, size=9.5)
    small(s, x + 146, top + 214, "Save to catalog sits inside the", size=10.5)
    small(s, x + 146, top + 230, "Loaded card, desktop and phone", size=10.5)
    s.step(x + CW / 2, cap, 4, "the catalog boards and the Launch picker", size=18)
    y = lines(s, x, cap + 28, ("four boards new, three gain the picker",
                               "the phone sheet covers the tab bar, Escape closes",
                               "design only: no product code, no test run"))
    note(s, x, y + 6, ("no blocker, no major · 2 rounds",
                       "CR approve, SEC skipped, ux approve 0/0/8",
                       "2 minors open: nf-core hidden fields, to be",
                       "validated; small gaps against ui-spec 4.7.1"), warn=True)

    # 6 -- FU-P3-87d ----------------------------------------------------------------------------
    x = COLS[3]
    head(s, x, R1, "FU-P3-87d · PR 228 · web")
    s.browser(x + 2, top + 4, 250, 150, url="/catalog")
    s.text(x + 14, top + 50, "Catalog", size=12, anchor="start", weight="bold")
    chip(s, x + 166, top + 36, 78, "Add pipeline", "done", h=20, size=10)
    for r, (name, sub) in enumerate((("rnaseq-test · Nextflow", "`nf-core/rnaseq` `3.27.0`"),
                                     ("a second entry", "a path: no revision"))):
        ry = top + 64 + r * 42
        cell(s, x + 12, ry, 232, 36, "surface")
        small(s, x + 20, ry + 15, name, size=10.5, dim=False)
        small(s, x + 20, ry + 30, sub, size=9.5)
        chip(s, x + 200, ry + 8, 36, "Edit", "neutral", h=18, size=9.5)
    s.arrow(x + 258, top + 80, x + 290, top + 80)
    s.page(x + 296, top + 10, 150, 176, fill="surface", lines=0)
    small(s, x + 306, top + 32, "`/catalog/new`", size=10, dim=False)
    for i, field in enumerate(("Label", "Engine", "Pipeline", "Revision", "Default profile",
                               "Params file")):
        small(s, x + 306, top + 52 + i * 22, field, size=10)
        cell(s, x + 390, top + 42 + i * 22, 48, 14, "input")
    small(s, x + 2, top + 176, "reached from Home and Manage catalog on Launch,", size=10.5)
    small(s, x + 2, top + 192, "the sidebar marks Launch · it mirrors Environments", size=10.5)
    trash(s, x + 6, top + 208, 20, 24)
    small(s, x + 36, top + 222, "Delete asks first; nothing was deleted: only for", size=10.5)
    small(s, x + 36, top + 238, "412 and the two catalog file refusals", size=10.5)
    s.step(x + CW / 2, cap, 6, "the Catalog page, its list and its form", size=18)
    y = lines(s, x, cap + 28, ("`/catalog`, `/catalog/new`, `/catalog/<name>`",
                               "a changed file in another tab: Reload",
                               "the server refuses what the form lets through"))
    note(s, x, y + 6, ("no blocker, no major · 2 rounds",
                       "CR approve, SEC approve · the Delete fix test first",
                       "7 minors open: repeated Environments code,",
                       "list semantics, test gaps, the e2e target"))

    # ================================================================================================
    # row 2: FU-P3-102 imaging, FU-P3-106 SLURM
    band(s, R2 - 38, "FU-P3-102 imaging, steps 5 and 7: an OME-TIFF in Viv, then its channels and its "
         "view in the URL · FU-P3-106 SLURM, step 2")
    top = R2 + 20
    cap = top + 270

    # 5 -- FU-P3-102e (double width) ----------------------------------------------------------------
    x = COLS[0]
    wide = COLS[1] + CW - x
    head(s, x, R2, "FU-P3-102e · PR 227 · web")
    s.page(x + 2, top + 30, 70, 88, fill="input", lines=0)
    for i in range(4):
        cell(s, x + 12 + i * 4, top + 56 + i * 8, 44, 30, "surface")
    small(s, x + 37, top + 136, "`cells.ome.tif`", size=10, anchor="middle", dim=False)
    s.arrow(x + 80, top + 74, x + 140, top + 74)
    small(s, x + 110, top + 50, "the page's", size=9.5, anchor="middle")
    small(s, x + 110, top + 62, "own GeoTIFF", size=9.5, anchor="middle")
    small(s, x + 110, top + 94, "never a URL", size=9.5, anchor="middle")
    s.browser(x + 146, top + 4, 270, 196)
    picture(s, x + 158, top + 40, 170, 120)
    small(s, x + 158, top + 182, "Z", size=10.5, dim=False)
    slider(s, x + 172, top + 178, 64, 0.4)
    small(s, x + 248, top + 182, "T", size=10.5, dim=False)
    slider(s, x + 262, top + 178, 64, 0.1)
    for i, fill in enumerate(("bar_blue", "bar_green", "bar_violet", "bar_orange", "cached", "work")):
        s.circle(x + 352, top + 48 + i * 18, 5.5, fill=fill, width=1)
        s.line(x + 364, top + 48 + i * 18, x + 404, top + 48 + i * 18, colour=t.muted, passes=1,
               amount=0.2, width=1.6)
    small(s, x + 380, top + 168, "6 on", size=10.5, anchor="middle", dim=False)
    small(s, x + 380, top + 184, "at first", size=10, anchor="middle")
    small(s, x + 158, top + 222, "Viv in WebGL 2, a lazy chunk of 1,232.7 kB, 340.7 kB gzip", size=10.5)
    small(s, x + 158, top + 238, "tile cache 256 MiB, at most 20 resolution levels", size=10.5)
    # the fallback
    s.arrow(x + 424, top + 110, x + 470, top + 110, dashed=True, colour=t.muted)
    sc = s.phone(x + 476, top + 20, 76, 136)
    picture(s, sc.x + 4, sc.y + 20, sc.w - 8, 44)
    small(s, x + 514, top + 176, "the flat view", size=10.5, anchor="middle", dim=False)
    small(s, x + 514, top + 192, "of 102d3", size=10, anchor="middle")
    small(s, x + 562, top + 50, "on a phone,", size=10.5)
    small(s, x + 562, top + 66, "without WebGL 2,", size=10.5)
    small(s, x + 562, top + 82, "after a deck error,", size=10.5)
    small(s, x + 562, top + 98, "or with no OME-XML", size=10.5)
    # the audit, to scale
    ax = x + 700
    small(s, ax, top + 22, "`npm audit --omit=dev`, one cell an advisory", size=11, dim=False)
    small(s, ax, top + 48, "before", size=10.5)
    s.task_strip(ax + 52, top + 36, ((14, "problem", ""), (3, "work", "")), cell=8, gap=1.5, h=16)
    small(s, ax + 52, top + 70, "14 high, 3 moderate", size=10)
    small(s, ax, top + 98, "after", size=10.5)
    small(s, ax + 52, top + 98, "found 0", size=10.5, dim=False)
    s.tick(ax + 112, top + 94, size=5)
    small(s, ax, top + 122, "three overrides: `zod` `4.6.7`,", size=10.5)
    small(s, ax, top + 138, "`fflate` `0.8.3`, `image-size` `2.0.3`", size=10.5)
    s.page(ax, top + 156, 34, 44, fill="docs", lines=3)
    small(s, ax + 44, top + 174, "notices: 203 runtime", size=10.5)
    small(s, ax + 44, top + 190, "packages, in the wheel", size=10.5)
    s.step(x + wide / 2, cap, 5, "the OME-TIFF viewer with Viv", size=18)
    y = lines(s, x, cap + 28, ("Viv `0.23.0`, deck.gl `9.4.1`, luma.gl `9.4.2`, exact pins · Z and T, "
                               "the first 6 channels on, contrast from percentiles",
                               "one viewer at a time, its WebGL context released on unmount · "
                               "the CSP unchanged: zero violations in Chromium",
                               "2 rounds, 18 findings, several found by both reviewers · "
                               "every blocker and major fixed but one, kept open as a deferral"))
    y0 = y + 6
    half = (wide - 16) / 2
    left = (("CR-P3FU102E-01, SEC-01", "r1 blocker", "the audit gate: 17 advisories, 14 high",
             "fixed: three overrides, found 0", "fixed"),
            ("CR-P3FU102E-02", "r1 blocker", "an .ome.tif with no OME-XML: could not be decoded",
             "fixed: the flat view, Viv never called", "fixed"),
            ("CR-P3FU102E-03", "r1 major", "after a deck error, its WebGL context stayed alive",
             "fixed: the cleanups finalize deck, client, pool", "fixed"),
            ("CR-P3FU102E-04, SEC-09", "r1 major", "resolution levels uncapped, shapes wrap at 32",
             "fixed: at most 20 levels", "fixed"))
    right = (("SEC-P3FU102E-02", "r1 major", "OME-XML sizes unchecked: negative, or past the IFD",
              "fixed: positive, equal to the first IFD, capped", "fixed"),
             ("SEC-P3FU102E-03", "r1 major", "deck.gl's tile cache had no bound",
              "fixed: `maxCacheSize` from 256 MiB of tiles", "fixed"),
             ("SEC-P3FU102E-04", "r1 major", "no third-party notices for 155 new packages",
              "fixed: a notices file, a test for each package", "fixed"),
             ("SEC-P3FU102E-05", "r1 major", "the CSP run on Firefox and WebKit has not happened",
              "open deferral, inbox 148, to be validated", "open"))
    for col, items in ((x, left), (x + half + 16, right)):
        yy = y0
        for fid, tag, what, status, state in items:
            yy = pin(s, col, yy, fid, tag, what, status, w=half, state=state)

    # 7 -- FU-P3-102f -----------------------------------------------------------------------------
    x = COLS[2]
    head(s, x, R2, "FU-P3-102f · PR 230 · web")
    s.browser(x + 2, top + 4, 446, 178)
    picture(s, x + 14, top + 40, 196, 128)
    s.text(x + 224, top + 48, "Channels", size=11.5, anchor="start", weight="bold")
    for i, (on, fill) in enumerate(((True, "bar_blue"), (False, "bar_green"), (True, "bar_violet"))):
        ry = top + 62 + i * 38
        switch(s, x + 224, ry, on)
        s.circle(x + 260, ry + 6, 5.5, fill=fill, width=1)
        small(s, x + 272, ry + 11, f"channel {i + 1}", size=10.5, dim=False)
        slider(s, x + 224, ry + 26, 120, 0.2 + 0.25 * i)
        chip(s, x + 352, ry + 18, 88, "Reset contrast", "neutral", h=16, size=9.5)
    cell(s, x + 2, top + 194, 446, 24, "input")
    s.text(x + 10, top + 211, "`/runs/<id>/results/file?path=<file>&z=&t=&ch=&zoom=&x=&y=`", size=10.5,
           anchor="start")
    s.arrow(x + 120, top + 192, x + 120, top + 160, colour=t.accent)
    small(s, x + 128, top + 179, "Reload", size=10.5)
    small(s, x + 2, top + 238, "written with a history replace, read back on load: Reload keeps "
          "the view", size=10.5)
    s.step(x + CW / 2, cap, 7, "the channels panel, the view in the URL", size=18)
    y = lines(s, x, cap + 28, ("show, colour and contrast per channel, 6 on at most",
                               "the URL's `z`, `t`, `ch`, `zoom`, `x`, `y`; others kept",
                               "a value out of range is dropped, the default used"))
    y = pin(s, x, y + 6, "CR-P3FU102F-01", "r1 blocker",
            "Reload was said to lose the view",
            "did not reproduce: the router keeps unknown keys", state="none")
    y = pin(s, x, y, "CR-P3FU102F-02", "r1 major",
            "the URL's `ch` applied to an RGB image",
            "fixed test first: RGB ignores `ch`")
    note(s, x, y, ("2 rounds · CR approve, SEC skipped",
                   "4 minors open; a router regression test added"))

    # 2 -- FU-P3-106b -----------------------------------------------------------------------------
    x = COLS[3]
    head(s, x, R2, "FU-P3-106b · PR 224 · slurm")
    # two runs on a time line
    s.line(x + 10, top + 30, x + 440, top + 30, colour=t.muted, passes=1, amount=0.3)
    small(s, x + 10, top + 18, "launched long ago", size=10.5)
    small(s, x + 440, top + 18, "an hour ago", size=10.5, anchor="end")
    s.dot(x + 30, top + 30, 5, colour=t.accent)
    s.dot(x + 410, top + 30, 5, colour=t.good)
    small(s, x + 30, top + 48, "old run, `8812401`", size=10, anchor="start", dim=False)
    small(s, x + 410, top + 48, "recent run, `8812402`", size=10, anchor="end", dim=False)
    s.terminal(x + 2, top + 60, 260, 46, ("sacct -j 8812401,8812402 -S <oldest>",), size=10.5)
    s.arrow(x + 268, top + 84, x + 300, top + 84)
    s.hpc_node(x + 306, top + 58, 44, 56, busy=0, slots=3)
    s.cross(x + 328, top + 86, size=9)
    small(s, x + 360, top + 74, "slurmdbd:", size=10.5, dim=False)
    small(s, x + 360, top + 90, "too wide of a", size=10.5)
    small(s, x + 360, top + 106, "date range", size=10.5)
    # split
    s.arrow(x + 60, top + 112, x + 60, top + 140)
    cell(s, x + 2, top + 144, 214, 50, "problem")
    small(s, x + 12, top + 162, "old run: final, unavailable", size=10.5, dim=False)
    small(s, x + 12, top + 180, "`max_query_time_range`", size=10)
    s.arrow(x + 230, top + 112, x + 260, top + 140)
    cell(s, x + 232, top + 144, 216, 50, "done")
    small(s, x + 242, top + 162, "recent run: asked again,", size=10.5, dim=False)
    small(s, x + 242, top + 180, "narrower `-S`, row `OUT_OF_MEMORY`", size=10)
    small(s, x + 2, top + 216, "before: any non-zero exit retried under the back-off", size=10.5)
    small(s, x + 2, top + 232, "until the give-up, 24 h after the job ended", size=10.5)
    s.step(x + CW / 2, cap, 2, "a refused sacct window is final", size=18)
    y = lines(s, x, cap + 28, ("read from the first 4,096 bytes of sacct's error",
                               "only the jobs whose launch set `-S` give up",
                               "the others back under the limiter's back-off"))
    y = pin(s, x, y + 6, "SEC-P3FU106B-01", "r1 major",
            "one old run gave up the whole batch, recent runs too",
            "fixed test first: only the oldest run, 2 calls")
    note(s, x, y, ("2 rounds · CR approve, SEC changes fixed",
                   "4 minors open; the exact error line",
                   "to be validated on `slurm-mini`"), warn=True)

    # ================================================================================================
    # row 3: the run pages, Environments, Profile, the runs table
    band(s, R3 - 38, "FU-P3-104, -111, -112 and -115a, steps 8 to 11: the breadcrumb, Environments, "
         "a Profile page, delete and pin runs")
    top = R3 + 20
    cap = top + 270

    # 8 -- FU-P3-104 ------------------------------------------------------------------------------
    x = COLS[0]
    head(s, x, R3, "FU-P3-104 · PR 237 · web")
    s.browser(x + 2, top + 4, 446, 70)
    crumbs(s, x + 14, top + 56, ("Home", "Runs", "the run", "Results", "cells.tif"))
    small(s, x + 2, top + 102, "before, on a file page", size=10.5)
    end = crumbs(s, x + 14, top + 124, ("Home", "Runs", "the run", "Results", "File"),
                 last_fill="problem")
    small(s, end + 6, top + 124, "a fixed word", size=10.5)
    small(s, x + 2, top + 154, "after: the name the `stat` route answered, never the", size=10.5)
    small(s, x + 2, top + 170, "URL's path; File only until `stat` answers", size=10.5)
    small(s, x + 2, top + 202, "Work directory has its own crumb, like Results", size=10.5)
    small(s, x + 2, top + 232, "Resume of", size=11.5)
    s.text(x + 72, top + 232, "run `<short id>`", size=11.5, anchor="start", colour=t.accent)
    s.line(x + 72, top + 236, x + 176, top + 236, colour=t.accent, passes=1, amount=0.2, width=1.3)
    small(s, x + 196, top + 232, "a bare link takes `--sp-text-link`", size=10.5)
    s.step(x + CW / 2, cap, 8, "the breadcrumb names the file", size=18)
    y = lines(s, x, cap + 28, ("the run is named once in the breadcrumb",
                               "a URL's text is never a label",
                               "the table caption and two links: FU-P3-104b"))
    y = pin(s, x, y + 6, "CR-P3FU104-01", "r1 major",
            "a file page's breadcrumb ended with the word File",
            "fixed: the name from `stat`, a vitest added")
    y = pin(s, x, y, "CR-P3FU104-02", "r1 major",
            "caption and two bare links left open, no record",
            "fixed: handed off as FU-P3-104b")
    note(s, x, y, ("2 rounds · CR approve, SEC skipped",
                   "2 minors open"))

    # 9 -- FU-P3-111 ------------------------------------------------------------------------------
    x = COLS[1]
    head(s, x, R3, "FU-P3-111 · PR 238 · web")
    s.browser(x + 2, top + 4, 446, 166, url="`/environments?view=table`")
    small(s, x + 14, top + 48, "Show environments as", size=10.5)
    chip(s, x + 150, top + 36, 54, "Cards", "surface", h=18, size=10)
    chip(s, x + 204, top + 36, 54, "Table", "input", h=18, size=10)
    for c, (name, kind, fill) in enumerate((("slurm", "SLURM", "neutral"), ("local", "Local", "neutral"))):
        cx0 = x + 14 + c * 214
        cell(s, cx0, top + 64, 204, 96, "surface")
        if c == 0:
            s.hpc_node(cx0 + 10, top + 74, 24, 32, busy=2, slots=2)
        else:
            cell(s, cx0 + 8, top + 76, 30, 26, "neutral")
            chevron(s, cx0 + 14, top + 89)
            s.line(cx0 + 22, top + 94, cx0 + 31, top + 94, colour=t.ink, passes=1, amount=0.1, width=1.3)
        s.text(cx0 + 46, top + 86, name, size=11.5, anchor="start", weight="bold")
        chip(s, cx0 + 46, top + 92, 46, kind, "input", h=16, size=9.5)
        chip(s, cx0 + 96, top + 92, 52, "Built-in", fill, h=16, size=9.5)
        chip(s, cx0 + 10, top + 128, 104, "Duplicate to edit", "docs", h=20, size=10)
    s.arrow(x + 70, top + 172, x + 70, top + 200)
    s.page(x + 2, top + 204, 196, 40, fill="surface", lines=0)
    small(s, x + 10, top + 220, "`/environments/new?from=slurm`", size=9.5, dim=False)
    small(s, x + 10, top + 236, "name `slurm-copy`, values filled", size=10)
    small(s, x + 210, top + 196, "a server for SLURM, a terminal for", size=10.5)
    small(s, x + 210, top + 212, "Local, beside the text badge; the", size=10.5)
    small(s, x + 210, top + 228, "table: one `<table>`, actions per row", size=10.5)
    s.step(x + CW / 2, cap, 9, "Environments: kind icons, cards or a table", size=18)
    y = lines(s, x, cap + 28, ("Cards or Table, kept in `?view=table`",
                               "a built-in stays read only: Duplicate to edit",
                               "no server change"))
    note(s, x, y + 6, ("no blocker, no major · 2 rounds",
                       "CR approve, SEC skipped, ux approve 0/0/5",
                       "fixed test first: New no longer reads the list",
                       "4 minors open, among them `shownView`"))

    # 10 -- FU-P3-112 -----------------------------------------------------------------------------
    x = COLS[2]
    head(s, x, R3, "FU-P3-112 · PR 241 · web and server")
    s.browser(x + 2, top + 4, 446, 166, url="/profile")
    avatar(s, x + 426, top + 15, 10)
    small(s, x + 408, top + 19, "the avatar", size=10, anchor="end")
    cards = (("Who the server runs as", ("Unix user, UID",)),
             ("This session", ("Started",)),
             ("Config paths", ("config, data, db,", "observed")),
             ("Theme", ("Light, Dark, System",)))
    for i, (title, rows) in enumerate(cards):
        cx0 = x + 12 + (i % 2) * 216
        cy0 = top + 40 + (i // 2) * 64
        cell(s, cx0, cy0, 208, 58, "surface")
        s.text(cx0 + 8, cy0 + 16, title, size=10.5, anchor="start", weight="bold")
        for r, row in enumerate(rows):
            small(s, cx0 + 8, cy0 + 32 + r * 14, row, size=10)
    chip(s, x + 284, top + 78, 146, "Sign out of this session", "problem", h=16, size=9.5)
    chip(s, x + 152, top + 124, 52, "Copy", "neutral", h=16, size=9.5)
    small(s, x + 2, top + 194, "`GET /me`: the Unix user, the session's start and", size=10.5,
          dim=False)
    small(s, x + 2, top + 210, "the paths, never a file's contents", size=10.5)
    small(s, x + 2, top + 232, "`POST /auth/session:sign-out`, 204: this session", size=10.5,
          dim=False)
    small(s, x + 2, top + 248, "revoked, its cookie cleared", size=10.5)
    s.step(x + CW / 2, cap, 10, "a Profile page, in single-user mode too", size=18)
    y = lines(s, x, cap + 28, ("reached from the avatar of the top bar",
                               "both routes behind the session and the Origin rule",
                               "the sign-out: a scope extension, assumed"))
    y = pin(s, x, y + 6, "CR-P3FU112-01", "r1 major",
            "phone: Copy keys at 40 px, Sign out at natural width",
            "fixed in `ab646741`, checked in Chrome at 360 px")
    note(s, x, y, ("CR changes, the fix not re-reviewed: to be validated",
                   "SEC approve · ux changes, focus fixed test first",
                   "open: SSE streams survive a sign-out, SEC-01"), warn=True)

    # 11 -- FU-P3-115a ----------------------------------------------------------------------------
    x = COLS[3]
    head(s, x, R3, "FU-P3-115a · PR 242 · server")
    s.terminal(x + 2, top + 4, 250, 66, ("POST /runs:delete", "ids, up to 200, directories"),
               size=10.5, line_h=16)
    small(s, x + 2, top + 92, "the runs list, pinned first", size=10.5, dim=False)
    for r, (pinned, fill) in enumerate(((True, "done"), (False, "done"), (False, "problem"))):
        ry = top + 100 + r * 24
        cell(s, x + 2, ry, 250, 22, "surface")
        cell(s, x + 2, ry, 5, 22, fill)
        pushpin(s, x + 20, ry + 10, on=pinned)
        s.line(x + 36, ry + 11, x + 120 + (r % 2) * 40, ry + 11, colour=t.muted, passes=1,
               amount=0.2, width=1.6)
    small(s, x + 2, top + 194, "`PATCH /runs/<id>` sets `pinned`, migration", size=10.5)
    small(s, x + 2, top + 210, "`0012_run_pinned`", size=10.5)
    s.arrow(x + 258, top + 36, x + 290, top + 36)
    s.folder(x + 296, top + 10, 70, 56, fill="gate")
    s.cross(x + 331, top + 42, size=10)
    s.folder(x + 376, top + 10, 70, 56, fill="neutral")
    s.cross(x + 411, top + 42, size=10)
    small(s, x + 331, top + 82, "its directory", size=10, anchor="middle")
    small(s, x + 411, top + 82, "lineage root", size=10, anchor="middle")
    small(s, x + 270, top + 108, "only one Spectio made,", size=10.5)
    small(s, x + 270, top + 124, "rmtree under the runs root's", size=10.5)
    small(s, x + 270, top + 140, "descriptor, no symlink", size=10.5)
    small(s, x + 270, top + 166, "409 refusals:", size=10.5, dim=False)
    small(s, x + 270, top + 182, "`run-not-ended`, or", size=10.5)
    small(s, x + 270, top + 198, "`directory-not-removable`:", size=10.5)
    small(s, x + 270, top + 214, "a live head, a shared one,", size=10.5)
    small(s, x + 270, top + 230, "started from a terminal", size=10.5)
    s.step(x + CW / 2, cap, 11, "delete and pin runs, server side", size=18)
    y = lines(s, x, cap + 28, ("ended runs are marked deleted, then gone from lists",
                               "a Resume child takes its lineage root with it",
                               "the web side is FU-P3-115b"))
    note(s, x, y + 6, ("no blocker, no major · 2 rounds",
                       "CR approve, SEC approve with 3 minors",
                       "fixed: the lineage root, deleted children's heads",
                       "open: CR-P3FU115A-03 to -06, SEC-03"))

    # ================================================================================================
    # the batch simplifier, the lines and the tests
    band(s, LOW - 20, "batch simplify, before and after, then the batch to scale · re-review: "
         "not needed")
    y0 = LOW + 8

    x = 50
    s.text(x, y0 + 12, "`code-simplifier`: no change", size=14, anchor="start", weight="bold")
    small(s, x, y0 + 38, "before, `bf240d20`", size=12.5)
    s.page(x, y0 + 48, 180, 80, fill="surface", lines=4)
    s.text(x + 206, y0 + 96, "=", size=22, colour=t.dim)
    small(s, x + 232, y0 + 38, "after, `bf240d20`", size=12.5)
    s.page(x + 232, y0 + 48, 180, 80, fill="done", lines=4)
    lines(s, x, y0 + 156, ("-0 +0 · read in full: `runs_manage.py`, both",
                           "`catalog.py`, `me.py` and `locations.py`",
                           "skipped: one shared lookup in `api/catalog.py`,",
                           "a helper to save about one line",
                           "web left alone: 5 exports used in their own",
                           "file only, a public-surface choice"), size=12)

    # lines per step, to scale
    x = 590
    k = 0.22
    s.text(x, y0 + 12, f"lines per step outside docs, to scale, {k} px a line", size=14,
           anchor="start", weight="bold")
    sizes = ((1, "87a", 316, 245, 0, 0, 167), (2, "106b", 77, 100, 0, 0, 39),
             (3, "87b", 707, 433, 0, 0, 70), (4, "87c", 0, 0, 787, 0, 8),
             (5, "102e", 444, 432, 0, 10178, 84), (6, "87d", 550, 327, 0, 0, 8),
             (7, "102f", 358, 189, 0, 0, 59), (8, "104", 50, 34, 0, 0, 26),
             (9, "111", 167, 112, 59, 0, 54), (10, "112", 511, 244, 254, 0, 19),
             (11, "115a", 512, 448, 0, 0, 45))
    mid = x + 120
    for i, (n, name, code, tests, boards, lock, rem) in enumerate(sizes):
        ry = y0 + 28 + i * 21
        s.text(mid - 46, ry + 12, f"{n} · {name}", size=11.5, anchor="end", colour=t.dim)
        bar(s, mid - 2 - rem * k, ry, rem * k, 14, "problem")
        ox = mid + 2
        for n_, fill in ((code, "done"), (tests, "input"), (boards, "docs")):
            if n_:
                bar(s, ox, ry, n_ * k, 14, fill)
                ox += n_ * k
        total = code + tests + boards
        if lock:
            bar(s, ox, ry, 110, 14, "neutral")
            s.line(ox + 50, ry - 3, ox + 44, ry + 17, colour=t.ink, passes=1, amount=0.1, width=1.4)
            s.line(ox + 58, ry - 3, ox + 52, ry + 17, colour=t.ink, passes=1, amount=0.1, width=1.4)
            ox += 110
            s.text(ox + 6, ry + 12, f"+{total}, +{lock:,} lockfile, notices · -{rem}",
                   size=11, anchor="start")
        else:
            s.text(ox + 6, ry + 12, f"+{total} -{rem}", size=11, anchor="start")
    s.line(mid, y0 + 22, mid, y0 + 264, colour=t.muted, passes=1, amount=0.2)
    s.text(mid - 6, y0 + 284, "removed", size=11, anchor="end", colour=t.dim)
    for lx, fill, label in ((mid + 8, "done", "code, schema, CSS"), (mid + 150, "input", "tests"),
                            (mid + 218, "docs", "boards"), (mid + 296, "neutral", "lockfile, notices")):
        bar(s, lx, y0 + 274, 18, 12, fill)
        s.text(lx + 24, y0 + 284, label, size=11, anchor="start", colour=t.dim)

    # the tests, to scale
    x = 1290
    k = 0.28
    s.text(x, y0 + 12, f"pytest cases collected, to scale, {k} px a case", size=14,
           anchor="start", weight="bold")
    runs_t = (("before step 1, `9f11c6d9`", 1433, "bar_grey"), ("head `bf240d20`", 1607, "bar_green"),
              ("after simplify", 1607, "bar_green"))
    for i, (label, n, fill) in enumerate(runs_t):
        by = y0 + 28 + i * 26
        s.text(x, by + 14, label, size=11.5, anchor="start")
        bar(s, x + 150, by, n * k, 18, fill)
        s.text(x + 156 + n * k, by + 14, f"{n:,}", size=11.5, anchor="start")
    small(s, x, y0 + 124, "added per step, 2 px a case", size=12, dim=False)
    added = (("1 · 87a", 57), ("2 · 106b", 6), ("3 · 87b", 62), ("6 · 87d", 1),
             ("10 · 112", 6), ("11 · 115a", 42))
    for i, (label, n) in enumerate(added):
        by = y0 + 134 + i * 17
        s.text(x + 92, by + 11, label, size=11, anchor="end", colour=t.dim)
        bar(s, x + 100, by, n * 2, 12, "input")
        s.text(x + 106 + n * 2, by + 11, f"+{n}", size=11, anchor="start")
    small(s, x + 300, y0 + 146, "web cases added, from", size=11)
    small(s, x + 300, y0 + 162, "the diff: 5 · 18, 6 · 12,", size=11)
    small(s, x + 300, y0 + 178, "7 · 10, 8 · 1, 9 · 9,", size=11)
    small(s, x + 300, y0 + 194, "10 · 8; vitest not run,", size=11)
    small(s, x + 300, y0 + 210, "no `node_modules`", size=11)
    s.tick(x + 8, y0 + 254, size=6)
    small(s, x + 24, y0 + 260, "the simplifier's gate: 1,603 passed, 4 skipped; ruff,", size=11.5,
          dim=False)
    small(s, x + 24, y0 + 277, "mypy, lint-imports, `uv lock --check` pass", size=11.5)

    s.text(50, H - 52, "pins: every blocker and major of the batch, fixed, not reproduced or kept "
           "open as a deferral · r1: the first code review round · step 4 has no product code",
           size=13.5, anchor="start", colour=t.dim)
    s.prefix_key(50, H - 28, ("CR", "SEC"))
    s.text(W - 50, H - 12, "source: packages spectio catalog.py, locations.py, runner/sacct.py · "
           "spectio_server api catalog.py, workflows.py, me.py, runs_manage.py · web catalog, "
           "runs/imaging, shell, environments, profile · review records P3-fu87a to P3-fu115a",
           size=12, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b14-catalog-viewer-pages")
