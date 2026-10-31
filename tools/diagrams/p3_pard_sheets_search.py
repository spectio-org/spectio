#!/usr/bin/env python3
"""UI parity D, run detail sheets, searchable logs, a test pipeline in Launch: step P3-parD, 2026-10-31.

Writes docs/assets/diagrams/p3-pard-sheets-search_{light,dark}.{svg,png}.

Thomas asked (2026-10-31): "steps & stages pas clickable, pas de détails", "logs pas searchable",
"pas de wf par défaut de test dans launch pour tester".

Every fact comes from branch autopilot/P3-parD at 846f4621 (base 5ce1f893):
- 50ff24cd, web/src/runs/DetailSheet.tsx: Detail is a stage, a process or a task; a Mantine Drawer,
  position right, 560 px on a desktop and full screen on the phone, aria-modal, returnFocus, Close;
  `views` is a stack, the shown one last, "Back to <previous>"; CountChips "<n> of <all> done",
  running, pending, failed, cached, retried; "Open in Tasks" (onTasks, ?tab=tasks&process=);
  ProcessTasks pages GET /tasks?process= 50 at a time with "Load more tasks"; TaskView facts ID,
  Name, Tag, State, Process (a link back to the process), Stage, and the note "Not in Spectio 0.0.1
  yet: ... exit code, duration and resources. They arrive with P1 Tasks 28 and 29.";
- web/src/runs/RunDetailPage.tsx: OpenProcess and OpenTask buttons on every process and task row,
  "Stage details" in each open stage, WhyItFailed "First to fail: <task> · Process <name>",
  runSearch keeps ?tab=tasks&process=; RunHeader.tsx: the succeeded, running, pending and failed
  chips are buttons (onChip, a Tasks filter), cached and retried stay plain; the Pipeline directory
  fact gets a Copy button;
- web/src/runs/LogViewer.tsx: a search field "Search the <log>", the query lands 150 ms after
  typing, every match a <mark>, the counter "n / m" (aria-live polite) or "No match", previous and
  next buttons, Enter, Shift+Enter, Escape clears; the level segments All, INFO, WARN, ERROR with
  their counts; the figure's log lines, query and counts are the test's, LogViewer.test.tsx:9-15
  and :50-58 (ALIGN: 4 matches, "1 / 4");
- web/src/launch/TryPipelines.tsx: "Try a test pipeline", the distinct workflow.location of
  GET /runs?limit=50, newest first, at most five; none: "No pipeline has run on this server yet."
  and the docs link "How to get the synthetic test pipelines"; LaunchPage.tsx pick(): a path that
  starts with "/" is filled and loaded at once, a repository is filled and the Revision field
  focused; routes.tsx launchSearch, /launch?location=; HomePage.tsx "Your pipelines" rows are links
  to /launch?location=;
- tests/pipelines/synthetic/nextflow/nextflow_schema.json and
  tests/pipelines/synthetic/snakemake/workflow/schemas/config.schema.yaml: the groups and each
  engine's keys drawn (Snakemake names them samples and fail_rule; its Resources has time_limit_s only);
  test_launch.py asserts the four group titles for both engines;
- 2a45be98 (R1 CR-P3PARD-01, -04, -05, -06, each with a test written first): focusTasks;
  splitLines; First to fail follows page.next, up to 5 pages of 50; Load more's `loading` guard,
  aria-busy and disabled;
- 846f4621, the simplifier: LogViewer Line has one render path, 9 lines out and 1 in;
  pytest 511 passed and 15 deselected, tsc --noEmit clean, vitest 175 of 175;
- the review rounds, from the step's reviewer reports (docs/reviews/code/P3-parD.md):
  R1 CR approve, 01 to 08 minor, 01 04 05 06 fixed; R1 SEC approve, 01 to 03 minor, open;
  R2 CR approve, 07 minor, open (a new 07, the disabled button); R2 SEC approve, no finding.
Illustrative, not from a run: the run counts in the header chips, the pipeline locations in
Home and Launch, and the task IDs.
"""

from __future__ import annotations

import base64
import re
from xml.sax.saxutils import escape

from sketch import MONO, REPO_ROOT, Sketch, Theme, main_for

W, H = 1600, 2310
S1, S2, S3, S4 = 150, 890, 1420, 2010  # the four sections' title lines

_ICONS = dict(re.findall(r'^\s+(\w+): "([^"]+)",', (REPO_ROOT / "web/src/icons.tsx").read_text(), re.M))
_LOGOS = {k: base64.b64encode((REPO_ROOT / f"web/src/assets/logos/logo-{k}.png").read_bytes()).decode()
          for k in ("nf-core", "nextflow", "snakemake")}
# theme.ts code-failed, code-review, code-ok, code-progress: the same in both themes
TINT = {"failed": "#F59A9A", "review": "#F5C779", "ok": "#7FD3AA", "progress": "#9CC2FB"}
MARK, MARK_NOW = "#5c4d1a", "#b8860b"  # a match, and the current match, on the dark viewer
CW = 7.2  # a monospace character at 12 px

# LogViewer.test.tsx:9-15, the fixture lines, each with its level tint (level())
LOG = (("Oct-31 10:00:01 [main] INFO  nextflow.cli.CmdRun - N E X T F L O W", None),
       ("Oct-31 10:00:02 [Task submitter] INFO  ALIGN (S01) submitted", None),
       ("Oct-31 10:00:03 [Task monitor] WARN  ALIGN (S02) exit 137, retrying (1/3)", "review"),
       ("Oct-31 10:00:04 [Task monitor] ERROR ALIGN (S02) terminated", "failed"),
       ("Oct-31 10:00:05 [Task monitor] INFO  align done", None))

# (round, CR verdict, CR cells (id, fixed), SEC verdict, SEC cells)
ROUNDS = (
    ("R1", "approve", (("01", True), ("02", False), ("03", False), ("04", True), ("05", True),
                       ("06", True), ("07", False), ("08", False)),
     "approve", (("01", False), ("02", False), ("03", False))),
    ("R2", "approve", (("07", False),), "approve", ()),
)


# -- small helpers -----------------------------------------------------------------------------------

def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str, *, amount: float = 0.3) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=amount)


def stroke(s: Sketch, x1: float, y: float, x2: float, *, width: float = 1.2) -> None:
    """A ruled stroke standing for a line of text."""
    s.line(x1, y, x2, y, colour=s.t.muted, amount=0.3, passes=1, width=width)


def icon(s: Sketch, x: float, y: float, size: float, name: str, *, colour: str | None = None) -> None:
    """One of the app's line icons, top-left at x, y."""
    k = size / 24
    s.raw(f'<path d="{_ICONS[name]}" transform="translate({x:.1f} {y:.1f}) scale({k:.3f})" fill="none" '
          f'stroke="{colour or s.t.ink}" stroke-width="1.6" stroke-linecap="round" '
          f'stroke-linejoin="round" vector-effect="non-scaling-stroke"/>')


def tile(s: Sketch, x: float, y: float, size: float, name: str) -> None:
    s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" rx="{size * 0.3:.1f}" '
          f'fill="{s.t.fill("neutral")}" stroke="{s.t.muted}" stroke-width="1"/>')
    pad = size * 0.18
    icon(s, x + pad, y + pad, size - 2 * pad, name)


def logo(s: Sketch, x: float, y: float, size: float, key: str) -> None:
    """A pipeline's mark as the app draws it: the bundled PNG on white."""
    s.raw(f'<rect x="{x - 2:.1f}" y="{y - 2:.1f}" width="{size + 4:.1f}" height="{size + 4:.1f}" rx="4" '
          f'fill="#ffffff" stroke="{s.t.muted}" stroke-width="0.8"/>')
    s.raw(f'<image x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" '
          f'href="data:image/png;base64,{_LOGOS[key]}"/>')


def mono(s: Sketch, x: float, y: float, text: str, *, size: float = 12, colour: str | None = None,
         cw: float | None = None, weight: str = "normal") -> None:
    """Monospace text; with `cw`, set to exactly cw per character so marks can sit under it."""
    fit = f' textLength="{len(text) * cw:.1f}" lengthAdjust="spacingAndGlyphs"' if cw and text else ""
    s.raw(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO}" font-size="{size}" font-weight="{weight}" '
          f'fill="{colour or s.t.ink}" xml:space="preserve"{fit}>{escape(text)}</text>')


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5,
          anchor: str = "start", first: bool = True, step: float = 20) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * step, row, size=size, anchor=anchor, colour=s.t.ink if i == 0 and first else s.t.dim)


def pin(s: Sketch, x: float, y: float, title: str, rows: tuple[str, ...], *, fixed: bool) -> None:
    """A finding pinned where it hits: a tick when fixed on the branch, a dot when left open."""
    if fixed:
        s.tick(x + 7, y - 5, size=7, colour=s.t.good)
    else:
        s.dot(x + 7, y - 5, 4, colour=s.t.dim)
    s.text(x + 22, y, title, size=13.5, anchor="start", colour=s.t.accent if fixed else s.t.ink)
    for i, row in enumerate(rows):
        s.text(x + 22, y + 20 + i * 19, row, size=12.5, anchor="start", colour=s.t.dim)


def section(s: Sketch, y: float, title: str, sub: str, sub_x: float) -> None:
    s.text(50, y, title, size=19, anchor="start", weight="bold")
    s.text(sub_x, y, sub, size=13.5, anchor="start", colour=s.t.dim)


def chip(s: Sketch, x: float, y: float, text: str, fill: str, *, button: bool = False, size: float = 11.5) -> float:
    """A count chip; a button gets a heavier outline. Returns its right edge."""
    w = len(text) * size * 0.52 + 16
    s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="20" rx="10" fill="{s.t.fill(fill)}" '
          f'stroke="{s.t.ink if button else s.t.muted}" stroke-width="{1.4 if button else 0.8}"/>')
    s.text(x + w / 2, y + 14.5, text, size=size)
    return x + w


def link(s: Sketch, x: float, y: float, text: str, *, size: float = 12.5, arrow: bool = True) -> None:
    """A link-button: the accent colour, underlined, an arrow icon after it."""
    s.text(x, y, text, size=size, anchor="start", colour=s.t.accent)
    w = len(text.replace("`", "")) * size * 0.56
    s.line(x, y + 3, x + w, y + 3, colour=s.t.accent, amount=0.2, passes=1, width=0.9)
    if arrow:
        icon(s, x + w + 7, y - 10, 12, "arrowRight", colour=s.t.accent)


def cursor(s: Sketch, x: float, y: float) -> None:
    """A mouse pointer, its tip at x, y."""
    s.poly([(x, y), (x, y + 17), (x + 4.5, y + 13), (x + 8, y + 20), (x + 10.5, y + 19), (x + 7, y + 12),
            (x + 12.5, y + 12)], fill="surface", amount=0.15, width=1.4)


# -- 1 · the run page and its sheet ------------------------------------------------------------------

def run_page(s: Sketch, x: float, y: float, w: float, h: float) -> tuple[float, float]:
    """The run page; returns where the ALIGN row's name sits."""
    t = s.t
    s.browser(x, y, w, h, url="/runs/run_…")
    s.text(x + 16, y + 56, "rnaseq run", size=15, anchor="start", weight="bold")
    stroke(s, x + 16, y + 72, x + 190)
    # the count chips: four are buttons
    cx, failed_at = x + 16, 0.0
    for text, fill, btn in (("14 succeeded", "done", True), ("1 running", "input", True),
                            ("1 failed", "problem", True), ("1 cached", "neutral", False),
                            ("2 retried", "gate", False)):
        cx = chip(s, cx, y + 86, text, fill, button=btn) + 6
        if text.endswith("failed"):
            failed_at = cx - 14
    cursor(s, failed_at, y + 100)
    s.text(x + 16, y + 128, "Pipeline directory", size=11.5, anchor="start", colour=t.dim)
    mono(s, x + 130, y + 128, "/…/rnaseq", size=11.5)
    s.button(x + 214, y + 114, 50, "Copy", fill="surface", h=20)
    # Why it failed
    bar(s, x + 14, y + 146, w - 28, 66, "problem", amount=0.2)
    icon(s, x + 24, y + 156, 16, "alert")
    s.text(x + 46, y + 169, "Why it failed", size=13, anchor="start", weight="bold")
    stroke(s, x + 46, y + 182, x + 300)
    s.text(x + 24, y + 203, "First to fail:", size=12, anchor="start")
    mono(s, x + 104, y + 203, "ALIGN (S09)", size=11.5)
    s.text(x + 196, y + 203, "·", size=12, anchor="start")
    link(s, x + 208, y + 203, "Process ALIGN", size=12)
    # the stages: QC folded, Align open
    sy = y + 240
    icon(s, x + 18, sy - 12, 14, "chevronRight", colour=t.dim)
    s.text(x + 38, sy, "1 · QC", size=13, anchor="start")
    s.text(x + w - 20, sy, "12 of 12", size=12, anchor="end", colour=t.dim)
    s.line(x + 14, sy + 12, x + w - 14, sy + 12, colour=t.muted, amount=0.2, passes=1, width=0.8)
    sy += 36
    icon(s, x + 18, sy - 12, 14, "chevronDown", colour=t.dim)
    s.text(x + 38, sy, "2 · Align", size=13, anchor="start", weight="bold")
    s.text(x + w - 20, sy, "3 of 5", size=12, anchor="end", colour=t.dim)
    link(s, x + 38, sy + 26, "Stage details", size=12)
    # the Align stage's process table
    ty = sy + 58
    for k, head in enumerate(("Process", "State", "Done")):
        s.text(x + 38 + k * 150, ty, head, size=11.5, anchor="start", colour=t.dim)
    s.line(x + 34, ty + 8, x + w - 20, ty + 8, colour=t.muted, amount=0.2, passes=1, width=0.8)
    rx, ry = x + 38, ty + 32
    bar(s, x + 30, ry - 19, w - 50, 28, "input", amount=0.1)
    s.raw(f'<text x="{rx:.1f}" y="{ry:.1f}" font-family="{MONO}" font-size="12" fill="{t.accent}" '
          f'text-decoration="underline">ALIGN</text>')
    chip(s, x + 188, ry - 14, "running", "input")
    s.text(x + 338, ry, "3 / 5", size=12, anchor="start")
    cursor(s, rx + 30, ry - 6)
    return x + w - 14, ry - 5


def sheet(s: Sketch, x: float, y: float, w: float, h: float) -> tuple[float, float]:
    """The process view in the side sheet; returns where its first task row is."""
    t = s.t
    # the page behind, dimmed
    s.raw(f'<rect x="{x - 24:.1f}" y="{y:.1f}" width="24" height="{h:.1f}" fill="{t.muted}" opacity="0.45"/>')
    bar(s, x, y, w, h, "surface", amount=0.25)
    s.text(x + 18, y + 32, "ALIGN", size=17, anchor="start", weight="bold")
    s.cross(x + w - 22, y + 24, size=6, colour=t.ink)
    mono(s, x + 18, y + 60, "NFCORE:RNASEQ:ALIGN", size=11.5, colour=t.dim)
    chip(s, x + 18, y + 72, "running", "input")
    s.text(x + 90, y + 87, "Stage 2 · Align", size=12, anchor="start", colour=t.dim)
    cx = x + 18
    for text, fill in (("3 of 5 done", "done"), ("1 running", "input"), ("0 pending", "neutral")):
        cx = chip(s, cx, y + 104, text, fill) + 6
    cx = x + 18
    for text, fill in (("1 failed", "problem"), ("1 cached", "neutral"), ("2 retried", "gate")):
        cx = chip(s, cx, y + 130, text, fill) + 6
    s.button(x + 18, y + 162, 118, "Open in Tasks", fill="surface", h=26)
    s.text(x + 18, y + 216, "Tasks", size=13, anchor="start", weight="bold")
    rows = (("ALIGN (S01)", "succeeded", "done"), ("ALIGN (S02)", "running", "input"))
    for i, (name, word, fill) in enumerate(rows):
        ry = y + 230 + i * 34
        bar(s, x + 14, ry, w - 28, 28, "neutral", amount=0.15)
        mono(s, x + 24, ry + 19, name, size=11.5)
        chip(s, x + w - 104, ry + 4, word, fill)
    s.button(x + 14, y + 304, 136, "Load more tasks", fill="surface", h=26)
    s.text(x + 160, y + 322, "50 at a time", size=12, anchor="start", colour=t.dim)
    s.text(x + 18, y + 360, "a right sheet, 560 px; full screen on a phone", size=12, anchor="start",
           colour=t.dim)
    s.text(x + 18, y + 378, "aria-modal: Escape or Close, focus back", size=12, anchor="start", colour=t.dim)
    s.text(x + 18, y + 396, "on the row that opened it", size=12, anchor="start", colour=t.dim)
    return x + w - 14, y + 278


def task_view(s: Sketch, x: float, y: float, w: float, h: float) -> None:
    t = s.t
    bar(s, x, y, w, h, "surface", amount=0.25)
    s.text(x + 16, y + 32, "ALIGN (S02)", size=16, anchor="start", weight="bold")
    icon(s, x + 14, y + 48, 13, "chevronLeft", colour=t.accent)
    s.text(x + 30, y + 59, "Back to ALIGN", size=12, anchor="start", colour=t.accent)
    facts = (("ID", "tsk_2"), ("Name", "ALIGN (S02)"), ("Tag", "S02"))
    fy = y + 92
    for i, (k, v) in enumerate(facts):
        s.text(x + 16, fy + i * 24, k, size=12, anchor="start", colour=t.dim)
        mono(s, x + 90, fy + i * 24, v, size=11.5)
    fy += 3 * 24
    s.text(x + 16, fy, "State", size=12, anchor="start", colour=t.dim)
    chip(s, x + 90, fy - 14, "running", "input")
    s.text(x + 16, fy + 24, "Process", size=12, anchor="start", colour=t.dim)
    link(s, x + 90, fy + 24, "ALIGN", size=12)
    s.text(x + 16, fy + 48, "Stage", size=12, anchor="start", colour=t.dim)
    s.text(x + 90, fy + 48, "Stage 2 · Align", size=12, anchor="start")
    ny = fy + 72
    bar(s, x + 12, ny, w - 24, 112, "gate", amount=0.2)
    lines(s, x + 22, ny + 22, ("Not in Spectio 0.0.1 yet:", "its files, its work directory,",
                               "exit code, duration and", "resources. They arrive with",
                               "P1 Tasks 28 and 29."), size=12, step=18)


def failed_scan(s: Sketch, x: float, y: float) -> None:
    """CR-P3PARD-05 to scale: 1 px per failed task searched for First to fail."""
    t = s.t
    s.text(x, y, "failed tasks searched, 1 px each, pages of 50", size=12.5, anchor="start", colour=t.dim)
    for k, (label, n) in enumerate((("before", 50), ("after", 250))):
        by = y + 14 + k * 26
        s.text(x, by + 13, label, size=12, anchor="start")
        for p in range(n // 50):
            bar(s, x + 52 + p * 50, by, 50, 16, "input" if k else "neutral", amount=0.1)
        s.text(x + 52 + n + 8, by + 13, str(n), size=12, anchor="start", colour=t.dim)


def run_detail(s: Sketch) -> None:
    section(s, S1, "1 · the run page: every stage, process and task opens its detail",
            "Thomas, 2026-10-31: steps and stages not clickable, no details", 730)
    top = S1 + 30
    ax, ay = run_page(s, 50, top, 480, 430)
    sx, sy = 600, top
    tx, ty = sheet(s, sx, sy, 400, 430)
    s.arrow(ax + 4, ay, sx - 30, ay, colour=s.t.accent)
    task_view(s, 1060, top + 40, 270, 390)
    s.arrow(tx + 4, ty, 1054, top + 60, colour=s.t.accent)
    # where Open in Tasks leads
    s.text(1350, top + 30, "Open in Tasks", size=13.5, anchor="start", weight="bold")
    lines(s, 1350, top + 52, ("the sheet closes; the Tasks tab", "on that process, every state:",
                              "`?tab=tasks&process=`", "", "a count chip in the header:", "the Tasks tab on its filter,",
                              "Succeeded, Running, Pending", "or Failed; cached and", "retried stay plain"),
          size=12.5, first=False, step=19)
    s.line(1340, top + 18, 1340, top + 210, colour=s.t.muted, amount=0.3, passes=1, width=1)
    cy = top + 460
    s.step(290, cy, 1, "click a row, a chip or a link", size=16)
    s.step(800, cy, 2, "the sheet: counts, its tasks", size=16)
    s.step(1195, cy, 3, "a task: what 0.0.1 serves", size=16)
    s.text(1195, cy + 20, "each view stacks; Back pops it", size=12.5, colour=s.t.dim)
    py = cy + 58
    pin(s, 50, py, "R1 CR-P3PARD-06, minor", ("a double click on Load more fetched the same", "page twice: rows twice, duplicate keys;",
                                             "fixed in 2a45be98: one page in flight,", "aria-busy meanwhile"), fixed=True)
    pin(s, 440, py, "R2 CR-P3PARD-07, minor, open", ("the native disabled moves keyboard focus", "to the body: the next Tab starts again",
                                                    "at the top of the sheet; the guard", "alone would do"), fixed=False)
    pin(s, 830, py, "R1 CR-P3PARD-01, minor", ("a chip on the Tasks view already shown", "left the URL unchanged and focus pending;",
                                             "fixed: focusTasks focuses the panel", "at once"), fixed=True)
    pin(s, 1220, py, "R1 CR-P3PARD-05, minor", ("First to fail looked in the first 50", "failed tasks only; fixed: it follows",
                                              "page.next; past 250 the line is left out"), fixed=True)
    failed_scan(s, 1242, py + 84)


# -- 2 · the searchable logs -------------------------------------------------------------------------

def viewer_line(s: Sketch, x: float, y: float, text: str, tint: str | None, query: str, current: int,
                seen: int) -> int:
    """One log line with its matches marked; returns the matches counted so far."""
    colour = TINT.get(tint or "", s.t.term_ink)
    starts = [m.start() for m in re.finditer(re.escape(query), text, re.I)]
    for i in starts:
        s.raw(f'<rect x="{x + i * CW - 1:.1f}" y="{y - 11:.1f}" width="{len(query) * CW + 2:.1f}" height="15" '
              f'rx="2" fill="{MARK_NOW if seen == current else MARK}"/>')
        seen += 1
    mono(s, x, y, text, size=12, colour=colour, cw=CW)
    return seen


def logs_browser(s: Sketch, x: float, y: float, w: float, h: float) -> None:
    t = s.t
    s.browser(x, y, w, h, url="/runs/run_…?tab=logs&source=engine")
    tx = x + 16
    for tab in ("Summary", "Tasks", "Parameters", "Logs"):
        s.text(tx, y + 56, tab, size=12.5, anchor="start", weight="bold" if tab == "Logs" else "normal",
               colour=t.ink if tab == "Logs" else t.dim)
        if tab == "Logs":
            s.line(tx, y + 63, tx + 32, y + 63, width=2.4, amount=0.2, passes=1)
        tx += {"Summary": 74, "Tasks": 52, "Parameters": 92}.get(tab, 0)
    # the search field, the counter, previous and next
    fy = y + 84
    bar(s, x + 16, fy, 260, 30, "surface", amount=0.15)
    icon(s, x + 24, fy + 7, 16, "search", colour=t.dim)
    mono(s, x + 48, fy + 20, "ALIGN", size=12.5)
    s.line(x + 92, fy + 7, x + 92, fy + 23, colour=t.ink, amount=0.1, passes=1, width=1.2)
    s.text(x + 292, fy + 20, "1 / 4", size=14, anchor="start", weight="bold")
    for k, name in enumerate(("chevronLeft", "chevronRight")):
        bx = x + 340 + k * 34
        bar(s, bx, fy + 1, 28, 28, "surface", amount=0.15)
        icon(s, bx + 6, fy + 7, 16, name)
    # the level segments, with the fixture's counts
    gx = x + 430
    for label, n, fill in (("All", 5, "input"), ("INFO", 3, "surface"), ("WARN", 1, "gate"), ("ERROR", 1, "problem")):
        gw = 34 + len(label) * 8
        bar(s, gx, fy + 1, gw, 28, fill, amount=0.15)
        s.text(gx + 10, fy + 20, label, size=12, anchor="start", weight="bold" if label == "All" else "normal")
        s.text(gx + gw - 8, fy + 20, str(n), size=12, anchor="end", colour=t.dim)
        gx += gw + 4
    # the viewer
    vx, vy, vw = x + 16, fy + 46, w - 32
    vh = 30 + len(LOG) * 22
    s.raw(f'<rect x="{vx:.1f}" y="{vy:.1f}" width="{vw:.1f}" height="{vh:.1f}" rx="6" fill="{t.term_bg}"/>')
    seen = 0
    for i, (text, tint) in enumerate(LOG):
        seen = viewer_line(s, vx + 12, vy + 26 + i * 22, text, tint, "ALIGN", 0, seen)
    s.text(vx, vy + vh + 22, "the lines from the step's test: `ALIGN` matches 4 times, case-insensitive; "
           "the current match is the brighter one", size=12, anchor="start", colour=t.dim)


def newline_fix(s: Sketch, x: float, y: float) -> None:
    """CR-P3PARD-04: a final newline used to add an empty line."""
    t = s.t
    s.text(x, y, "a log that ends with a newline", size=13.5, anchor="start", weight="bold")
    mono(s, x + 212, y, r'"INFO a\nINFO b\n"', size=12, colour=t.dim)
    for k, (label, rows, n) in enumerate((("before", ("INFO a", "INFO b", ""), 3), ("after", ("INFO a", "INFO b"), 2))):
        bx = x + k * 210
        s.text(bx, y + 30, label, size=12.5, anchor="start", colour=t.dim)
        vh = 14 + 3 * 18
        s.raw(f'<rect x="{bx:.1f}" y="{y + 40:.1f}" width="120" height="{vh}" rx="5" fill="{t.term_bg}"/>')
        for i, row in enumerate(rows):
            ly = y + 58 + i * 18
            mono(s, bx + 10, ly, row or " ", size=11.5, colour=t.term_ink)
            if not row:
                s.raw(f'<rect x="{bx + 8:.1f}" y="{ly - 11:.1f}" width="104" height="14" rx="2" fill="none" '
                      f'stroke="{TINT["failed"]}" stroke-dasharray="3 3"/>')
        s.text(bx + 130, y + 62, f"All {n}", size=13, anchor="start", colour=t.accent if n == 3 else t.ink)
        s.text(bx + 130, y + 82, f"INFO {n}", size=13, anchor="start", colour=t.accent if n == 3 else t.ink)
    s.arrow(x + 186, y + 74, x + 204, y + 74, colour=t.dim)


def logs(s: Sketch) -> None:
    t = s.t
    section(s, S2, "2 · the logs: search, a counter, the levels",
            "Thomas, 2026-10-31: logs not searchable", 500)
    top = S2 + 30
    logs_browser(s, 50, top, 900, 330)
    kx = 1000
    s.text(kx, top + 14, "the keys, in the field", size=13.5, anchor="start", weight="bold")
    for i, (key, says) in enumerate((("Enter", "the next match"), ("Shift Enter", "the previous one"),
                                     ("Escape", "clears the search"))):
        ky = top + 42 + i * 26
        bar(s, kx, ky - 15, 92, 21, "neutral", amount=0.1)
        s.text(kx + 46, ky, key, size=12.5)
        s.text(kx + 104, ky, says, size=12.5, anchor="start")
    lines(s, kx, top + 132, ("the query lands 150 ms after the last key;",
                             "the counter is a polite live region, or No match;",
                             "a level button shows only those lines,",
                             "and the search follows it"), size=12.5, first=False, step=19)
    newline_fix(s, kx, top + 232)
    py = top + 400
    pin(s, kx, py - 26, "R1 CR-P3PARD-04, minor", ("fixed in 2a45be98, here and in the Summary's tail",), fixed=True)
    pin(s, 50, py, "R1 CR-P3PARD-02, minor, open", ("every line gets the query's length, so every line",
                                                   "re-renders on each new query, not only the matches"), fixed=False)
    pin(s, 500, py, "R1 CR-P3PARD-03, minor, open", ("the Summary's 6-line tail has no search; the brief",
                                                    "asked for it in every log viewer"), fixed=False)


# -- 3 · Launch: a test pipeline -------------------------------------------------------------------

def home(s: Sketch, x: float, y: float, w: float, h: float) -> tuple[float, float]:
    t = s.t
    s.browser(x, y, w, h, url="/")
    tile(s, x + 14, y + 42, 24, "route")
    s.text(x + 46, y + 59, "Your pipelines", size=13, anchor="start", weight="bold")
    s.text(x + 14, y + 88, "Pipeline directories of your recent runs:", size=11.5, anchor="start", colour=t.dim)
    s.text(x + 14, y + 104, "open one in Launch.", size=11.5, anchor="start", colour=t.dim)
    rows = (("nextflow", "/…/synthetic/nextflow"), ("snakemake", "/…/synthetic/snakemake"),
            ("nf-core", "nf-core/rnaseq"))
    for i, (key, where) in enumerate(rows):
        ry = y + 124 + i * 34
        logo(s, x + 16, ry, 18, key)
        s.raw(f'<text x="{x + 46:.1f}" y="{ry + 14:.1f}" font-family="{MONO}" font-size="11.5" '
              f'fill="{t.accent}" text-decoration="underline">{escape(where)}</text>')
    cursor(s, x + 228, y + 132)
    return x + w, y + 140


def launch_page(s: Sketch, x: float, y: float, w: float, h: float) -> None:
    t = s.t
    s.browser(x, y, w, h, url="/launch?location=…")
    s.text(x + 16, y + 54, "Launch a workflow", size=13.5, anchor="start", weight="bold")
    px, pw = x + 14, w - 28
    bar(s, px, y + 70, pw, 196, "surface", amount=0.2)
    tile(s, px + 10, y + 80, 24, "route")
    s.text(px + 42, y + 97, "Pipeline", size=13, anchor="start", weight="bold")
    s.text(px + 12, y + 128, "Try a test pipeline", size=12, anchor="start", colour=t.dim, weight="bold")
    items = (("nextflow", "spectio/synthetic-scenarios", "/…/synthetic/nextflow"),
             ("nf-core", "nf-core/rnaseq", "nf-core/rnaseq"))
    ix = px + 140
    for key, name, where in items:
        iw = 40 + len(name) * 6.8
        bar(s, ix, y + 112, iw, 26, "neutral", amount=0.1)
        logo(s, ix + 6, y + 116, 16, key)
        s.text(ix + 28, y + 130, name, size=11.5, anchor="start", weight="bold")
        ix += iw + 8
    cursor(s, px + 300, y + 137)
    s.text(px + 12, y + 166, "Pipeline", size=11.5, anchor="start", colour=t.dim)
    bar(s, px + 12, y + 174, pw - 120, 26, "input", amount=0.15)
    mono(s, px + 20, y + 191, "/…/synthetic/nextflow", size=11.5)
    s.button(px + pw - 98, y + 173, 84, "Load", fill="surface", h=28)
    logo(s, px + 14, y + 222, 16, "nextflow")
    s.text(px + 38, y + 235, "spectio/synthetic-scenarios", size=12, anchor="start", weight="bold")
    s.tick(px + 236, y + 230, size=5, colour=t.good)
    s.text(px + 246, y + 235, "Loaded", size=12, anchor="start")
    s.text(px + 310, y + 235, "4 parameter groups, profiles local, slurm, test", size=11.5, anchor="start",
           colour=t.dim)
    lines(s, x + 16, y + 292, ("picked: a path that starts with `/` is filled and loaded at once;",
                               "a repository is filled and the Revision field takes the focus"),
          size=12.5, first=False, step=19)


def schema(s: Sketch, x: float, y: float) -> None:
    t = s.t
    s.text(x, y, "the synthetic pipelines' schemas", size=13.5, anchor="start", weight="bold")
    s.page(x, y + 16, 34, 44, fill="docs", lines=3)
    s.page(x + 42, y + 16, 34, 44, fill="docs", lines=3)
    lines(s, x + 90, y + 34, ("`nextflow_schema.json`", "`config.schema.yaml`"), size=12.5, first=False, step=18)
    s.text(x, y + 84, "the same four groups, each engine's own keys:", size=12.5, anchor="start",
           colour=t.dim)
    nx, sx = x + 16, x + 216
    s.text(nx, y + 108, "Nextflow", size=12, anchor="start", weight="bold", colour=t.dim)
    s.text(sx, y + 108, "Snakemake", size=12, anchor="start", weight="bold", colour=t.dim)
    groups = (("Input/output options", ("input, outdir",), ("samples, outdir",)),
              ("Scenario", ("chunks, scale, seed",), ("chunks, scale, seed",)),
              ("Failure injection", ("fail_mode, fail_process,", "fail_sample, fail_gb"),
               ("fail_mode, fail_rule,", "fail_sample, fail_gb")),
              ("Resources", ("time_limit_s, python_image",), ("time_limit_s",)))
    gy = y + 132
    for g, nf, smk in groups:
        s.dot(x + 6, gy - 5, 3.5, colour=t.ink)
        s.text(x + 16, gy, g, size=12.5, anchor="start")
        for i, keys in enumerate(nf):
            mono(s, nx, gy + 19 * (i + 1), keys, size=11, colour=t.dim)
        for i, keys in enumerate(smk):
            mono(s, sx, gy + 19 * (i + 1), keys, size=11, colour=t.dim)
        gy += 19 * (max(len(nf), len(smk)) + 1) + 6


def launch(s: Sketch) -> None:
    t = s.t
    section(s, S3, "3 · Launch: try a pipeline this server ran",
            "Thomas, 2026-10-31: no default test workflow in Launch", 470)
    top = S3 + 30
    hx, hy = home(s, 50, top, 330, 240)
    s.arrow(hx + 8, hy, hx + 60, hy, colour=t.accent)
    s.text(hx + 34, hy - 12, "a link", size=12, colour=t.dim)
    launch_page(s, 450, top, 680, 340)
    schema(s, 1170, top + 14)
    s.step(215, top + 268, 1, "Home: open one in Launch", size=16)
    lines(s, 50, top + 296, ("`/launch?location=` opens Launch on it", "",
                             "Try a test pipeline: the distinct", "pipelines of the last 50 runs,",
                             "newest first, at most five;", "none: a link to the docs on the",
                             "synthetic test pipelines"), size=12.5, first=False, step=19)
    s.step(790, top + 366, 2, "Launch: pick one, it loads", size=16)
    py = top + 420
    pin(s, 450, py, "R1 SEC-P3PARD-01, minor, open", ("a crafted `/launch?location=` link loads",
                                                     "a planted pipeline under a name it chooses;",
                                                     "Launch still needs a click"), fixed=False)
    pin(s, 820, py, "R1 SEC-P3PARD-02, minor, open", ("no upper bound on chunks, scale, fail_gb",
                                                     "or time_limit_s: a large fan-out or",
                                                     "allocation on a shared login node"), fixed=False)
    pin(s, 1190, py, "R1 SEC-P3PARD-03, minor, open", ("`python_image` takes any string: a mutable",
                                                      "tag can replace the digest pin"), fixed=False)


# -- 4 · the review rounds ---------------------------------------------------------------------------

def rounds(s: Sketch) -> None:
    t = s.t
    x0 = 50
    s.text(x0, S4, "4 · two review rounds, one cell per finding", size=19, anchor="start", weight="bold")
    cx_cr, cx_sec, cx_v = x0 + 60, x0 + 380, x0 + 520
    s.text(cx_cr, S4 + 36, "code-reviewer", size=12.5, anchor="start", colour=t.dim)
    s.text(cx_sec, S4 + 36, "security", size=12.5, anchor="start", colour=t.dim)
    s.text(cx_v, S4 + 36, "verdicts", size=12.5, anchor="start", colour=t.dim)
    cell = 32
    for i, (rnd, crv, cr, secv, sec) in enumerate(ROUNDS):
        y = S4 + 52 + i * 48
        s.text(x0, y + 22, rnd, size=15, anchor="start", weight="bold")
        for j, (n, fixed) in enumerate(cr):
            cx = cx_cr + j * (cell + 4)
            bar(s, cx, y, cell, cell, "neutral", amount=0.2)
            if fixed:
                s.tick(cx + cell / 2, y + cell / 2 - 3, size=6, colour=t.good)
            s.text(cx + cell / 2, y + cell + 13, n, size=10.5, colour=t.dim)
        for j, (n, _) in enumerate(sec):
            cx = cx_sec + j * (cell + 4)
            bar(s, cx, y, cell, cell, "neutral", amount=0.2)
            s.text(cx + cell / 2, y + cell + 13, n, size=10.5, colour=t.dim)
        if not sec:
            s.text(cx_sec, y + 22, "none", size=13, anchor="start", colour=t.dim)
        s.text(cx_v, y + 22, f"{crv}, {secv}", size=13.5, anchor="start")
    ky = S4 + 52 + 2 * 48 + 22
    bar(s, x0, ky - 14, 18, 18, "neutral", amount=0.15)
    s.text(x0 + 26, ky, "minor, every one", size=13, anchor="start")
    s.tick(x0 + 190, ky - 5, size=6, colour=t.good)
    s.text(x0 + 204, ky, "fixed on the branch, a test written first", size=13, anchor="start")
    lines(s, x0, ky + 28, ("IDs restart in each round: R2's 07 is new, the disabled button; R1's 07 and 08",
                           "ask for the e2e result and the inventory on the Progress page"),
          size=12.5, first=False)
    s.terminal(800, S4 + 20, 750, 190, (
        "fixes 2a45be98: CR-P3PARD-01, 04, 05, 06",
        "simplifier 846f4621: LogViewer Line, one render path,",
        "  9 lines out, 1 in",
        "pytest                     511 passed, 15 deselected",
        "tsc --noEmit               clean",
        "vitest                     175 of 175"), size=12.5)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=94)
    s.heading(50, 58, "P3 UI parity D · run detail sheets, searchable logs, a test pipeline in Launch",
              "web/src and the synthetic pipelines' schemas · what Thomas asked on 2026-10-31 · two review rounds")
    run_detail(s)
    s.line(30, S2 - 40, W - 30, S2 - 40, dashed=True, colour=theme.muted)
    logs(s)
    s.line(30, S3 - 40, W - 30, S3 - 40, dashed=True, colour=theme.muted)
    launch(s)
    s.line(30, S4 - 40, W - 30, S4 - 40, dashed=True, colour=theme.muted)
    rounds(s)
    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(50, H - 16, "a tick: fixed on the branch · a dot: left open · R1, R2: the round · counts, "
           "paths and IDs illustrative; the log lines and the sheet's counts from the step's tests",
           size=12.5, anchor="start", colour=theme.dim)
    s.text(W - 50, H - 16, "source: web/src at 846f4621 · P3-parD reviews, rounds 1 and 2",
           size=12.5, anchor="end", colour=theme.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-pard-sheets-search")
