#!/usr/bin/env python3
"""The Playwright end-to-end skeleton: step T6, 2026-10-28.

Writes docs/assets/diagrams/t6-e2e_{light,dark}.{svg,png}.

Every fact comes from tests/e2e/ and docs/specs/dev-environment-and-testing.md §6.1 on branch autopilot/T6:
- where the tests point, first match wins (tests/e2e/base-url.ts): SPECTIO_E2E_BASE_URL (http or https, no user,
  password or query string); else SPECTIO_SCENARIO, the scenario JSON whose urls.spectio is used (no scenario writes
  it yet, so it is refused with that reason); else the static stand-in tests/e2e/static/index.html served by
  python3 -m http.server on 127.0.0.1:8710 (playwright.config.ts);
- projects unit, desktop (Desktop Chrome), phone (Pixel 7); `npx playwright test --list` on 2026-10-28:
  11 tests in 4 files, 9 in unit (base-url.unit.ts 6, boards.unit.ts 2, pin.unit.ts 1), the smoke test
  smoke.e2e.ts once on desktop and once on phone;
- screenshots tests/e2e/screens/<Board>--<project>.png, <Board> a board of design/ui-canvas (boards.ts); the stand-in
  plays RunsTable; traces on failure for the stand-in only;
- verified targets: the stand-in in CI (e2e.yml) and the Cloudflare docs preview https://spectio.pages.dev/;
- deferred (§6.1): the side-by-side report of real pages and board renders.
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1600, 960


def _runs_page(s: Sketch, x: float, y: float, w: float, *, size: float = 15) -> None:
    """The stand-in page as it renders: an h1 "Runs" and one line of text."""
    s.text(x, y, "Runs", size=size + 5, anchor="start", weight="bold")
    s.line(x, y + 16, x + w, y + 16, colour=s.t.muted, amount=0.4, passes=1, width=1.4)
    s.line(x, y + 28, x + w * 0.7, y + 28, colour=s.t.muted, amount=0.4, passes=1, width=1.4)


def _board(s: Sketch, x: float, y: float, w: float, h: float, *, faded: bool = False) -> None:
    """A UI board thumbnail: sidebar, top bar and a table of runs."""
    ink = s.t.muted if faded else None
    s.rect(Box(x, y, w, h, "docs"), colour=ink, dashed=faded)
    s.poly([(x + 4, y + 4), (x + w * 0.2, y + 4), (x + w * 0.2, y + h - 4), (x + 4, y + h - 4)],
           fill="neutral", colour=ink, amount=0.3, width=1.1)
    s.line(x + w * 0.24, y + 14, x + w - 8, y + 14, colour=s.t.muted, amount=0.3, passes=1, width=1.3)
    rows = int((h - 30) // 12)
    for i in range(rows):
        ry = y + 28 + i * 12
        s.line(x + w * 0.24, ry, x + w - 8, ry, colour=s.t.muted, amount=0.3, passes=1, width=1.0)
        s.dot(x + w * 0.28, ry - 4, 2.2, colour=s.t.muted if faded else s.t.good)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=66)
    t = theme
    s.heading(50, 58, "T6 · a Playwright skeleton the tier 4 tests will grow from",
              "`cd tests/e2e` then `npx playwright test` · Playwright 1.63.0, pinned in dev/versions.env")

    # 1 -- where the tests point -------------------------------------------------------
    x1 = 50
    s.text(x1, 140, "first match wins", size=16, anchor="start", weight="bold")
    # 1st: an explicit URL
    s.terminal(x1, 158, 470, 66, ("SPECTIO_E2E_BASE_URL=https://spectio.pages.dev/",), size=13.5)
    s.text(x1, 248, "1st · an explicit URL, `http` or `https`", size=15, anchor="start")
    s.cross(x1 + 10, 272, size=6)
    s.text(x1 + 26, 277, "refused with a user, password or query string:", size=13.5, anchor="start", colour=t.dim)
    s.text(x1 + 26, 296, "a credential would land in a trace or a report", size=13.5, anchor="start", colour=t.dim)
    # 2nd: a scenario JSON
    s.page(x1, 322, 48, 60, fill="input", lines=2)
    s.text(x1 + 24, 374, "json", size=12)
    s.text(x1 + 64, 342, "2nd · `SPECTIO_SCENARIO`, the file from `dev/scenario.py up`", size=15, anchor="start")
    s.text(x1 + 64, 364, "`.scenarios/<id>/scenario.json`, its `urls.spectio`", size=13.5, anchor="start",
           colour=t.dim)
    s.hourglass(x1 + 74, 388, size=7)
    s.text(x1 + 88, 393, "no scenario runs Spectio yet: refused, saying why", size=13.5, anchor="start",
           colour=t.warn)
    # 3rd: the stand-in page
    s.page(x1, 420, 48, 60, fill="done", lines=3)
    s.text(x1 + 64, 440, "3rd · otherwise the stand-in page `static/index.html`", size=15, anchor="start")
    s.text(x1 + 64, 462, "`python3 -m http.server` on `127.0.0.1:8710`", size=13.5, anchor="start", colour=t.dim)
    s.text(x1 + 64, 482, "the default, and what CI runs", size=13.5, anchor="start", colour=t.dim)
    s.step(x1 + 240, 530, 1, "where the tests point")

    # 2 -- three projects, one smoke test -----------------------------------------------
    x2 = 610
    s.browser(x2, 128, 280, 170, url="127.0.0.1:8710")
    _runs_page(s, x2 + 20, 70 + 128, 200)
    s.text(x2 + 20, 128 + 150, "title: Runs · Spectio", size=13, anchor="start", colour=t.dim)
    s.text(x2 + 140, 322, "`desktop` · Desktop Chrome", size=14.5)
    screen = s.phone(x2 + 340, 118, 100, 190)
    _runs_page(s, screen.x + 8, screen.y + 28, screen.w - 16, size=12)
    s.text(x2 + 390, 330, "`phone` · Pixel 7", size=14.5)
    checks = ("answers with a 2xx status", "its title names Spectio", "its `main` landmark is visible",
              "no script error is raised")
    s.text(x2, 364, "one smoke test, on both:", size=15, anchor="start", weight="bold")
    for i, c in enumerate(checks):
        cy = 390 + i * 22
        s.tick(x2 + 10, cy - 4, size=6)
        s.text(x2 + 26, cy, c, size=14, anchor="start")
    s.step(x2 + 230, 530, 2, "a desktop and a phone")

    # 3 -- screenshots named after the boards ------------------------------------------
    x3 = 1120
    _board(s, x3, 140, 150, 104)
    s.text(x3 + 75, 266, "`RunsTable.dc.html`", size=13.5)
    s.text(x3 + 75, 284, "a board of design/ui-canvas", size=12.5, colour=t.dim)
    s.arrow(x3 + 162, 192, x3 + 214, 192, colour=t.dim)
    s.text(x3 + 188, 180, "names", size=12.5, colour=t.dim)
    # the two PNGs the stand-in writes
    s.page(x3 + 226, 140, 120, 80, fill="input", lines=2)
    s.text(x3 + 232, 166, "Runs", size=14, anchor="start", weight="bold")
    s.page(x3 + 366, 132, 52, 96, fill="input", lines=4)
    s.text(x3 + 372, 156, "Runs", size=11, anchor="start", weight="bold")
    s.text(x3 + 226, 250, "`RunsTable--desktop.png`", size=12.5, anchor="start")
    s.text(x3 + 226, 268, "`RunsTable--phone.png`", size=12.5, anchor="start")
    s.text(x3 + 226, 288, "in tests/e2e/screens/", size=12.5, anchor="start", colour=t.dim)
    s.cross(x3 + 10, 334, size=6)
    s.text(x3 + 26, 339, "a name that is not a board is refused", size=13.5, anchor="start", colour=t.dim)
    s.text(x3 + 26, 358, "another target takes no screenshot: it is not that board", size=13.5, anchor="start",
           colour=t.dim)
    s.lock(x3 + 10, 396, 9, fill="docs")
    s.text(x3 + 26, 401, "trace kept on failure, for the stand-in only:", size=13.5, anchor="start")
    s.text(x3 + 26, 420, "a trace records headers and cookies", size=13.5, anchor="start", colour=t.dim)
    s.step(x3 + 215, 530, 3, "what it keeps")

    # the 11 tests, to scale ------------------------------------------------------------
    by = 590
    s.text(50, by, "11 tests pass, one cell per test", size=16, anchor="start", weight="bold")
    s.text(50, by + 22, "`npx playwright test --list`, 2026-10-28", size=13, anchor="start", colour=t.dim)
    # cell 34, gap 6, and gap * 4 between groups: unit spans 390..792, smoke 822..920
    right = s.task_strip(390, by - 18, ((6, "done", "base URL"), (2, "done", "board names"),
                                        (1, "done", "version pin"), (1, "input", "desktop"), (1, "input", "phone")),
                         cell=34, gap=6, h=30, label_size=13)
    s.line(390, by + 42, 792, by + 42, colour=t.muted, amount=0.4, passes=1, width=1.2)
    s.text(591, by + 62, "`unit`: 9, no browser", size=14)
    s.line(822, by + 42, 920, by + 42, colour=t.muted, amount=0.4, passes=1, width=1.2)
    s.text(871, by + 62, "smoke: 2", size=14)
    s.tick(right - 6, by - 4, size=8)

    # 4 -- verified targets --------------------------------------------------------------
    vy = 700
    s.terminal(50, vy, 300, 120, ("e2e.yml", "unit, desktop and phone", "stand-in page"), size=13)
    s.tick(330, vy + 100, size=9)
    s.text(200, vy + 146, "green in CI", size=15)
    s.browser(400, vy, 250, 120, url="spectio.pages.dev")
    s.text(420, vy + 66, "the docs site", size=14, anchor="start", colour=t.dim)
    s.phone(670, vy - 8, 66, 136)
    s.tick(760, vy + 100, size=9)
    s.text(568, vy + 146, "Cloudflare docs preview: desktop and phone pass, run locally", size=15)
    s.step(420, vy + 196, 4, "two targets verified")

    # deferred: the side-by-side report ---------------------------------------------------
    dx, dw = 870, 680
    s.shade(dx, vy - 30, dw, 246, fill="neutral", opacity=0.45, colour=t.muted, dashed=True)
    s.text(dx + 20, vy - 4, "deferred · the side-by-side report", size=16, anchor="start", weight="bold", colour=t.dim)
    s.rect(Box(dx + 40, vy + 26, 150, 96, "none"), colour=t.muted, dashed=True)
    s.text(dx + 54, vy + 56, "Runs", size=15, anchor="start", colour=t.muted)
    s.line(dx + 54, vy + 72, dx + 160, vy + 72, colour=t.muted, amount=0.4, passes=1, width=1.2)
    s.text(dx + 115, vy + 146, "real page", size=13.5, colour=t.dim)
    s.text(dx + 225, vy + 80, "vs", size=16, colour=t.dim)
    _board(s, dx + 260, vy + 26, 150, 96, faded=True)
    s.text(dx + 335, vy + 146, "board render", size=13.5, colour=t.dim)
    s.text(dx + 440, vy + 50, "the MVP UI is much", size=14, anchor="start", colour=t.dim)
    s.text(dx + 440, vy + 70, "simpler than the boards,", size=14, anchor="start", colour=t.dim)
    s.text(dx + 440, vy + 90, "so the pairs would not", size=14, anchor="start", colour=t.dim)
    s.text(dx + 440, vy + 110, "match yet", size=14, anchor="start", colour=t.dim)
    s.text(dx + 20, vy + 190, "also later: tier 4 journeys, destructive specs, the bundle and Compose", size=13,
           anchor="start", colour=t.dim)

    s.text(W - 50, H - 16, "source: tests/e2e/ · .github/workflows/e2e.yml · dev-environment-and-testing.md §6.1",
           size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "t6-e2e")
