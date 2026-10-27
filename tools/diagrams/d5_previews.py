#!/usr/bin/env python3
"""Dev previews end to end: step D5, 2026-10-27.

Writes docs/assets/diagrams/d5-previews_{light,dark}.{svg,png}.

Every value comes from the live runs of previews.yml on PR #13 (branch autopilot/D5):
- run 40522381183, head 950e1de: deployment https://4367baf3.spectio.pages.dev, alias pr-13;
- run 40523119556, head 086a84b: deployment https://8c909d6d.spectio.pages.dev, same alias;
  its /versions page read 51 deployments over 3 API pages (result_info.total_pages = 3);
- after the second push both hash URLs answered 200, each with its own build SHA in the footer.
The Codespaces path is checked statically only; its live start is to be validated (spec §7.2).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 940


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=55)
    t = theme
    s.heading(60, 62, "Dev previews: every push stays online at its own URL",
              "previews.yml on PR 13, two pushes, 2026-10-27 · Codespaces on demand for the full stack")

    # 1 -- the events ------------------------------------------------------------
    ex = 70
    for i, (label, fill) in enumerate((("push to PR 13", "input"), ("Thomas labels wave-approved", "gate"),
                                       ("push main or a tag", "neutral"))):
        y = 150 + i * 84
        s.page(ex, y, 46, 58, fill=fill)
        s.text(ex + 60, y + 34, label, size=15, anchor="start")
    s.step(160, 420, 1, "an event on GitHub")

    # 2 -- GitHub Actions -----------------------------------------------------------
    tx, ty = 370, 150
    s.terminal(tx, ty, 330, 220, (
        "previews.yml",
        "mkdocs build --strict",
        "  footer: build 086a84b",
        "versions_page.py",
        "  51 deployments, 3 pages",
        "wrangler pages deploy",
        "  --branch pr-13",
    ), size=13)
    s.step(tx + 165, 420, 2, "build in Actions")
    s.arrow(324, 260, tx - 10, 260)
    s.text(346, 248, "alias", size=13, colour=t.dim)

    # 3 -- Cloudflare Pages: deployments kept --------------------------------------
    cx = 790
    s.frame(cx, 130, 400, 270, fill="docs", dashed=True, colour=t.muted)
    s.text(cx + 18, 158, "Cloudflare Pages · project spectio", size=15, anchor="start", weight="bold")
    s.browser(cx + 20, 178, 360, 74, url="4367baf3.spectio.pages.dev")
    s.text(cx + 40, 236, "build 950e1de · first push", size=14, anchor="start", colour=t.dim)
    s.tick(cx + 352, 230)
    s.browser(cx + 20, 266, 360, 74, url="8c909d6d.spectio.pages.dev")
    s.text(cx + 40, 324, "build 086a84b · second push", size=14, anchor="start", colour=t.dim)
    s.tick(cx + 352, 318)
    s.link(cx + 40, 370)
    s.text(cx + 58, 375, "pr-13.spectio.pages.dev follows the latest", size=14, anchor="start")
    s.arrow(cx + 340, 360, cx + 340, 344)
    s.step(cx + 200, 420, 3, "each deployment kept")
    s.arrow(tx + 342, 300, cx - 10, 300)
    s.text(tx + 395, 288, "upload", size=13, colour=t.dim)

    # 4 -- /versions ---------------------------------------------------------------
    vx = 1270
    s.browser(vx, 150, 310, 220, url="pr-13.spectio.pages.dev/versions/")
    rows = (("main", "e61ece3"), ("pr-13", "950e1de"), ("pr-12", "332abd0"), ("pr-11", "978e3f9"))
    s.text(vx + 18, 208, "Preview versions", size=17, anchor="start", weight="bold")
    for i, (alias, sha) in enumerate(rows):
        y = 240 + i * 30
        s.text(vx + 22, y, f"`{alias}`", size=13, anchor="start")
        s.text(vx + 120, y, f"`{sha}`", size=13, anchor="start", colour=t.dim)
        s.text(vx + 250, y, "open", size=13, anchor="start", colour=t.accent)
    s.step(vx + 155, 420, 4, "/versions lists them all")
    s.arc(cx + 120, 124, tx + 250, 142, lift=40, dashed=True)
    s.text(cx - 20, 104, "deployments API, read before each deploy", size=13, colour=t.dim)

    # 5 -- the PR comment ---------------------------------------------------------
    s.envelope(370, 470, 70, 48, fill="input")
    s.text(456, 490, "PR comment, updated in place", size=15, anchor="start", weight="bold")
    s.text(456, 514, "hash URL with its build SHA · alias · /versions · Open in Codespaces", size=14,
           anchor="start", colour=t.dim)
    s.arrow(tx + 20, 380, 395, 462)
    s.step(700, 556, 5, "links back on the PR")

    # 6 -- Codespaces on demand -----------------------------------------------------
    s.frame(60, 600, 1520, 290, fill="neutral", dashed=True, colour=t.muted)
    s.text(84, 632, "On demand: GitHub Codespaces, the full stack", size=17, anchor="start", weight="bold")
    s.text(84, 656, "checked statically on 2026-10-27; the live start, its time and the prebuild quota are to be validated",
           size=14, anchor="start", colour=t.dim)
    s.button(110, 712, 230, "Open in Codespaces", fill="done")
    s.text(225, 776, "from the PR comment", size=13, colour=t.dim)
    s.arrow(354, 727, 470, 727)
    s.terminal(480, 684, 460, 170, (
        "devcontainer.json  Python 3.13, Java 21, Node 24",
        "setup.sh   Nextflow 26.10.3, Snakemake 9.27.1",
        "start.sh   mkdocs serve -a 0.0.0.0:8000",
    ), size=13)
    s.arrow(952, 760, 1080, 760)
    s.text(1016, 746, "port 8000", size=13, colour=t.dim)
    s.browser(1090, 690, 300, 150, url="codespace-8000.app.github.dev")
    s.text(1240, 772, "docs, live reload", size=15)
    s.hourglass(1440, 765)
    s.text(1462, 770, "start time", size=13, anchor="start", colour=t.dim)
    s.text(1462, 790, "not measured", size=13, anchor="start", colour=t.dim)

    s.text(W - 60, H - 22, "source: previews.yml runs 40522381183 and 40523119556, PR 13", size=12.5,
           anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "d5-previews")
