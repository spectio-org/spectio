#!/usr/bin/env python3
"""Round map for review R6-contract: the 0.0.1 screens plugged into the API draft.

Writes docs/assets/diagrams/r6_contract_map_{light,dark}.{svg,png}.

Scope and findings come from the round's two reviewer reports (R6-contract,
2026-10-27): spec-reviewer SR-080 to SR-091 (12 majors) and ux-reviewer UX-270
to UX-291 (17 majors, 5 minors), both against the OpenAPI draft
(spikes/openapi-draft/openapi.yaml). Left: the five 0.0.1 screens. Right: the
draft as a socket panel, one socket per endpoint group. A solid cable is a need
the draft serves (the ux-reviewer's coverage table); a dashed cable ends at a
socket with no resource. Dashed sockets below the panel are endpoints that
api §5 lists but the draft cut dropped. Every one of the 34 findings is pinned
once; SR-054 and SR-062 are R3 blockers the round extends, drawn as held.
The bars at the bottom are to scale: 34 findings, and the 43 `x-spec-gap`
entries of the draft (40 placed in R6 findings, 3 only in R3 findings).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1200
B, M, N = "blocker", "major", "minor"

ROW_TOP, ROW_H, ROW_GAP = 142, 160, 10  # screen rows
SCREEN_R = 600  # right edge of the screens column
PX0, PX1 = 965, 1572  # API panel
SOCK_X = 1012  # socket centre
PIN_X = 1222  # panel finding list

# (name, pictogram, findings pinned on the screen); a finding is (id, severity, note)
SCREENS = (
    ("Launch", "launch", (
        ("UX-276", M, "file checks, Recheck, Browse"),
        ("UX-277", M, "Snakemake launch body"),
    )),
    ("Runs list", "list", (
        ("UX-270", M, "workflow name per run"),
        ("UX-271", M, "row summary, N+1 calls"),
        ("UX-272", M, "task totals and percent"),
        ("UX-273", M, "started, duration"),
    )),
    ("Run detail", "detail", (
        ("UX-287", N, "failures by class"),
        ("UX-288", N, "meta strip fields"),
        ("UX-289", N, "pause after stage"),
        ("UX-290", N, "legend against enums"),
    )),
    ("Gate review", "gate", (
        ("UX-283", M, "who decided, when, why"),
        ("UX-284", M, "0.0.1 gate actions"),
    )),
    ("Relaunch", "relaunch", (
        ("UX-280", M, "resource overrides"),
        ("UX-281", M, "relaunch preview"),
        ("UX-282", M, "lineage and compare"),
        ("UX-291", N, "compare outcome, CPU-hours"),
    )),
)

# (key, label, path hint, missing, findings)
SOCKETS = (
    ("workflows", "workflows", "`/workflows`", False, (
        ("SR-086", M, "local source, name, location"),
    )),
    ("runs", "runs", "`/runs`", False, (
        ("SR-081", M, "actions, relaunch, lineage"),
        ("SR-087", M, "launch body: gates, links"),
        ("SR-088", M, "name, tags, task counts"),
        ("SR-062", B, "R3: relaunch at a gate"),
    )),
    ("stages", "stages", "no resource", True, (
        ("SR-082", M, "no resource, no state enum"),
    )),
    ("tasks", "tasks, logs", "`/tasks`", False, (
        ("SR-083", M, "task state enum"),
        ("SR-089", M, "which log, which attempt"),
    )),
    ("gates", "gates, checks", "`/gates`", False, (
        ("SR-085", M, "check values, thresholds"),
    )),
    ("events", "events, SSE", "`/events`", False, (
        ("SR-084", M, "frames, sequence, schemas"),
    )),
    ("ingest", "ingest", "contract missing", True, (
        ("SR-080", M, "batch and ack invented"),
        ("SR-054", B, "R3: ingest contract parked"),
    )),
)

# screen index -> sockets its needs plug into (coverage table); stages is the gap
CABLES = (
    (0, ("workflows", "runs")),
    (1, ("runs", "gates", "events")),
    (2, ("runs", "stages", "tasks", "gates", "events")),
    (3, ("runs", "gates")),
    (4, ("runs", "stages", "tasks")),
)

# endpoints in api §5 that the draft cut dropped: (path, finding, screen badge)
DROPPED = (
    ("`runs:summary`", "UX-274", "2"),
    ("`/version`", "UX-275", "all"),
    ("`manifest`", "UX-278", "1"),
    ("`samplesheets`", "UX-279", "5"),
    ("`gate items`", "UX-285", "4"),
    ("`artifacts`", "UX-286", "3"),
)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=61)
    t = theme
    sev_colour = {B: t.accent, M: t.warn, N: t.muted}

    def pin(px: float, py: float, sev: str) -> None:
        c = sev_colour[sev]
        s.poly([(px - 7, py + 2), (px + 7, py + 2), (px, py + 17)], fill=c, colour=c, width=1.2, amount=0.3)
        s.circle(px, py, 9, fill=c, colour=c, width=1.4)
        s.dot(px, py, 3.2, colour=t.bg)

    def tag(x: float, y: float, fid: str, sev: str) -> None:
        """The finding ID; a blocker's sits in a red-edged pill so it does not rely on hue alone."""
        if sev == B:
            s.shade(x - 4, y - 16, 11 * len(fid) + 6, 22, fill="problem", opacity=1, colour=t.accent)
        ink = {B: t.ink, M: t.warn, N: t.dim}[sev]
        s.text(x, y, fid, size=15, anchor="start", colour=ink,
               weight="bold" if sev == B else "normal")

    def finding(x: float, y: float, fid: str, sev: str, note: str) -> None:
        pin(x, y - 6, sev)
        tag(x + 15, y, fid, sev)
        s.text(x + 96, y, note, size=13.5, anchor="start", colour=t.dim)

    def cell(x: float, y: float, fill: str, w: float = 14, h: float = 18, dashed: bool = False) -> None:
        dash = ' stroke-dasharray="3 3"' if dashed else ""
        stroke = t.muted if dashed else t.ink
        s.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" rx="2" fill="{t.fill(fill)}" '
              f'stroke="{stroke}" stroke-width="0.9"{dash}/>')

    def socket(cx: float, cy: float, size: float = 46, *, missing: bool = False) -> None:
        """A wall outlet: two slots and an earth hole; dashed and empty when the draft has none."""
        x, y = cx - size / 2, cy - size / 2
        if missing:
            s.frame(x, y, size, size, fill="none", colour=t.accent, dashed=True)
            s.text(cx, cy + 7, "?", size=20, colour=t.accent, weight="bold")
            return
        s.frame(x, y, size, size, fill="input")
        for dx in (-8, 8):
            s.raw(f'<rect x="{cx + dx - 2.5:.1f}" y="{cy - 12:.1f}" width="5" height="13" rx="1.5" fill="{t.ink}"/>')
        s.dot(cx, cy + 10, 3.4)

    def cable(x1: float, y1: float, x2: float, y2: float, *, gap: bool = False) -> None:
        """A drooping cable from a screen to a socket; dashed when it plugs into nothing."""
        colour = t.warn if gap else t.dim
        dash = ' stroke-dasharray="8 6"' if gap else ""
        bend = (x2 - x1) * 0.45
        n = 28
        pts = []
        for i in range(n + 1):
            u = i / n
            a, b, c, d = (1 - u) ** 3, 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u ** 2, u ** 3
            pts.append((a * x1 + b * (x1 + bend) + c * (x2 - bend) + d * x2, a * y1 + b * y1 + c * y2 + d * y2))
        for _ in range(2):
            path = " ".join(f"{'M' if i == 0 else 'L'}{px + s._jitter(0.8):.1f},{py + s._jitter(0.8):.1f}"
                            for i, (px, py) in enumerate(pts))
            s.raw(f'<path d="{path}" fill="none" stroke="{colour}" stroke-width="1.5" '
                  f'stroke-linecap="round" stroke-linejoin="round"{dash}/>')
        s.dot(x1, y1, 3.5, colour=colour)
        s.dot(x2, y2, 3.5, colour=colour)

    def screen(kind: str, x: float, y: float) -> None:
        w, h = 150, 96
        s.browser(x, y, w, h)
        top = y + 28
        if kind == "launch":
            for k in range(2):
                s.frame(x + 14, top + 10 + k * 18, 122, 11, fill="input", colour=t.muted)
            s.frame(x + 84, top + 48, 52, 13, fill="done", colour=t.good)
        elif kind == "list":
            dots = (t.good, t.warn, t.accent, t.good)
            for k in range(4):
                ly = top + 12 + k * 14
                s.dot(x + 16, ly, 3.5, colour=dots[k])
                s.line(x + 26, ly, x + 78, ly, colour=t.muted, amount=0.3, passes=1, width=1.3)
                fills = (("done",) * 3, ("done", "gate", "empty"), ("done", "problem", "empty"), ("done",) * 3)[k]
                for i, f in enumerate(fills):
                    cell(x + 88 + i * 16, ly - 5, "none" if f == "empty" else f, w=13, h=10, dashed=f == "empty")
        elif kind == "detail":
            for k in range(3):
                s.line(x + 12 + k * 34, top + 10, x + 38 + k * 34, top + 10, colour=t.muted, amount=0.3,
                       passes=1, width=1.6)
            cell(x + 12, top + 26, "done", w=24, h=24)
            cell(x + 40, top + 26, "done", w=24, h=24)
            s.gate(x + 84, top + 54, 30, 32, state="closed")
            cell(x + 106, top + 26, "none", w=24, h=24, dashed=True)
        elif kind == "gate":
            s.gate(x + 44, top + 62, 50, 48, state="closed")
            for k in range(3):
                ly = top + 16 + k * 16
                if k == 1:
                    s.cross(x + 92, ly, size=4.5)
                else:
                    s.tick(x + 92, ly, size=5, width=1.8)
                s.line(x + 102, ly, x + 136, ly, colour=t.muted, amount=0.3, passes=1, width=1.3)
        elif kind == "relaunch":
            for k in range(4):
                ly = top + 12 + k * 13
                if k in (1, 3):
                    s.shade(x + 12, ly - 5, 72, 10, fill="recomputed", opacity=0.9)
                s.line(x + 16, ly, x + 80, ly, colour=t.muted, amount=0.3, passes=1, width=1.2)
            s.arc(x + 116, top + 54, x + 116, top + 8, lift=24, width=2)
        else:
            raise ValueError(kind)

    # -- header ------------------------------------------------------------------
    s.heading(40, 54, "R6 · the API draft against the 0.0.1 screens",
              "34 findings: 0 blockers, 29 majors, 5 minors · blockers held in R3: SR-054, SR-062")

    lx, ly = 830, 52
    pin(lx, ly - 4, B)
    tag(lx + 15, ly + 5, "R3 blocker", B)
    pin(lx + 165, ly - 4, M)
    s.text(lx + 180, ly + 5, "major", size=15, anchor="start", colour=t.dim)
    pin(lx + 260, ly - 4, N)
    s.text(lx + 275, ly + 5, "minor", size=15, anchor="start", colour=t.dim)
    cable(lx + 350, ly, lx + 400, ly)
    s.text(lx + 410, ly + 5, "served", size=15, anchor="start", colour=t.dim)
    cable(lx + 485, ly, lx + 535, ly, gap=True)
    s.text(lx + 545, ly + 5, "no resource", size=15, anchor="start", colour=t.dim)
    s.prefix_key(lx - 11, ly + 38, ("SR", "UX"))

    # -- the screens -----------------------------------------------------------------
    s.text(48, ROW_TOP - 10, "the 0.0.1 screens", size=14, anchor="start", colour=t.dim)
    starts = []
    for j, (name, kind, items) in enumerate(SCREENS):
        y0 = ROW_TOP + 8 + j * (ROW_H + ROW_GAP)
        s.shade(30, y0, SCREEN_R - 30, ROW_H, fill="neutral", opacity=0.55)
        screen(kind, 50, y0 + 18)
        s.step(125, y0 + 140, j + 1, name, size=17)
        for i, (fid, sev, note) in enumerate(items):
            finding(232, y0 + 36 + i * 32, fid, sev, note)
        starts.append(y0)

    # -- the API panel ----------------------------------------------------------------
    rows = []
    y = ROW_TOP + 70
    for key, label, hint, missing, items in SOCKETS:
        rh = max(66, 28 * len(items) + 24) + (24 if key == "ingest" else 0)
        rows.append((y, rh))
        y += rh
    panel_bottom = y + 6
    s.frame(PX0, ROW_TOP + 8, PX1 - PX0, panel_bottom - ROW_TOP - 8, fill="neutral")
    s.text(PX0 + 20, ROW_TOP + 40, "the API draft", size=20, anchor="start")
    s.text(PX0 + 20, ROW_TOP + 62, "`openapi.yaml`, 0.0.1 cut", size=13, anchor="start", colour=t.dim)
    finding(PIN_X, ROW_TOP + 36, "SR-090", M, "conventions: lists, errors, IDs")
    finding(PIN_X, ROW_TOP + 64, "SR-091", M, "browser threat on loopback")

    sock_y = {}
    for (key, label, hint, missing, items), (ry, rh) in zip(SOCKETS, rows):
        s.line(PX0 + 12, ry, PX1 - 12, ry, colour=t.muted, amount=0.6, passes=1, width=1)
        cy = ry + (rh - (24 if key == "ingest" else 0)) / 2
        sock_y[key] = cy
        socket(SOCK_X, cy, missing=missing)
        s.text(SOCK_X + 38, cy - 2, label, size=18, anchor="start")
        s.text(SOCK_X + 38, cy + 18, hint, size=12.5, anchor="start", colour=t.accent if missing else t.dim)
        top = cy - 28 * (len(items) - 1) / 2
        for i, (fid, sev, note) in enumerate(items):
            finding(PIN_X, top + 6 + i * 28, fid, sev, note)

    # -- cables, spread where several land on one socket ------------------------------
    incoming: dict[str, int] = {}
    for _, keys in CABLES:
        for k in keys:
            incoming[k] = incoming.get(k, 0) + 1
    seen: dict[str, int] = {}
    for j, keys in CABLES:
        y0 = starts[j]
        for i, k in enumerate(keys):
            n = incoming[k]
            m = seen.get(k, 0)
            seen[k] = m + 1
            ey = sock_y[k] + (m - (n - 1) / 2) * 8
            sy = y0 + 46 + (i - (len(keys) - 1) / 2) * 16 + 34
            cable(SCREEN_R + 4, sy, SOCK_X - 27, ey, gap=k == "stages")

    # -- the runner plugs into ingest from below --------------------------------------
    ingest_y = sock_y["ingest"]
    rx, ry = 975, panel_bottom + 70
    s.line(SOCK_X, ingest_y + 23, SOCK_X, ry, colour=t.warn, dashed=True, width=1.6, amount=0.6)
    s.dot(SOCK_X, ingest_y + 23, 3.5, colour=t.warn)
    s.runner(rx, ry, 120, 46, label="runner")
    s.terminal(rx - 8, ry + 64, 190, 56, ("$ nextflow run",), size=12)
    s.arrow(rx + 150, ry + 62, rx + 126, ry + 46, colour=t.dim, width=1.4)
    s.text(rx + 2, ry + 148, "the engine bridge posts batches", size=13, anchor="start", colour=t.dim)

    # -- endpoints the draft dropped -----------------------------------------------------
    gx, gy = 1205, panel_bottom + 26
    s.shade(gx, gy, PX1 - gx, 222, fill="neutral", opacity=0.55, colour=t.muted, dashed=True)
    s.text(gx + 16, gy + 26, "in the api spec, dropped by the draft", size=15, anchor="start", colour=t.dim)
    for i, (path, fid, badge) in enumerate(DROPPED):
        col, row = i % 2, i // 2
        x = gx + 16 + col * 186
        y = gy + 44 + row * 58
        s.frame(x, y, 30, 30, fill="none", colour=t.muted, dashed=True)
        s.text(x + 40, y + 13, path, size=12.5, anchor="start", colour=t.ink)
        pin(x + 48, y + 30, M)
        tag(x + 63, y + 36, fid, M)
        r = 11 if badge == "all" else 9
        bx = x + 150
        s.circle(bx, y + 31, r, colour=t.dim, width=1.2)
        s.text(bx, y + 35 if badge != "all" else y + 34.5, badge, size=12 if badge != "all" else 10.5,
               colour=t.dim)

    # -- counts, to scale -----------------------------------------------------------------
    cy0 = 1080
    s.text(40, cy0 + 14, "34 findings", size=16, anchor="start")
    x = 190
    for k in range(34):
        cell(x + k * 17, cy0, t.warn if k < 29 else t.muted)
    s.text(x + 34 * 17 + 10, cy0 + 14, "29 majors, 5 minors, 0 blockers", size=14, anchor="start", colour=t.dim)
    s.text(40, cy0 + 50, "43 draft gaps", size=16, anchor="start")
    for k in range(43):
        cell(x + k * 17, cy0 + 36, t.good if k < 40 else "cached")
    s.text(x + 43 * 17 + 10, cy0 + 50, "all placed: 40 in R6 findings, 3 only in R3 findings",
           size=14, anchor="start", colour=t.dim)

    s.text(40, H - 22, "Source: R6-contract reviewer reports, 2026-10-27 · spec-reviewer SR-080 to SR-091, "
                       "ux-reviewer UX-270 to UX-291 and its coverage table · tools/diagrams/r6_contract_map.py",
           size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "r6_contract_map")
