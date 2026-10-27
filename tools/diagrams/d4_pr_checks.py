#!/usr/bin/env python3
"""Figure for step D4: what runs on a pull request, and which three checks can block its merge.

Writes docs/assets/diagrams/d4_pr_checks_{light,dark}.{svg,png}.

Sources (branch autopilot/D4): .github/workflows/ci.yml (changes, security, pipelines-*, ci-ok),
security.yml and tools/ci/security.sh (gitleaks, osv-scanner, semgrep, actionlint, zizmor),
docs.yml (docs-gate, pr-body), claude-review.yml (spec-reviewer, security-reviewer), .github/CODEOWNERS;
docs/specs/dev-environment-and-testing.md §11 (required checks).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 880


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=44)
    t = theme

    s.heading(40, 52, "D4 · What runs on a pull request",
              "three required checks; everything path-filtered or advisory sits behind them · dev-environment §11")

    # -- the PR ------------------------------------------------------------------------------------
    s.page(60, 380, 90, 116, fill="input", lines=4)
    s.text(105, 530, "pull request", size=17)
    s.text(105, 552, "into `main` or", size=13.5, colour=t.dim)
    s.text(105, 570, "`autopilot/integration`", size=13.5, colour=t.dim)
    for y in (200, 440, 730):
        s.arrow(160, 438, 238, y, colour=t.muted, width=1.4)

    # -- docs.yml ----------------------------------------------------------------------------------
    s.shade(250, 120, 900, 150, fill="docs", opacity=0.45)
    s.text(272, 152, "`docs.yml`", size=17, anchor="start")
    s.text(272, 176, "every PR", size=14, anchor="start", colour=t.dim)
    a = s.button(500, 150, 170, "docs-gate", fill="docs")
    b = s.button(500, 200, 170, "pr-body", fill="docs")
    s.text(690, 170, "strict build, Mermaid, figures, media, Progress", size=14, anchor="start", colour=t.dim)
    s.text(690, 220, "Conventional Commit title, sections, sketch", size=14, anchor="start", colour=t.dim)

    # -- ci.yml ------------------------------------------------------------------------------------
    s.shade(250, 300, 900, 300, fill="neutral", opacity=0.55)
    s.text(272, 332, "`ci.yml`", size=17, anchor="start")
    s.text(272, 356, "every PR and push", size=14, anchor="start", colour=t.dim)
    s.magnifier(300, 410, 16)
    s.text(272, 470, "changes", size=15, anchor="start")
    s.text(272, 490, "git diff of the", size=12.5, anchor="start", colour=t.dim)
    s.text(272, 506, "merge commit", size=12.5, anchor="start", colour=t.dim)

    s.text(420, 340, "`security.yml` · always, no path filter", size=15, anchor="start")
    chips = (("secrets", "gitleaks"), ("deps", "osv-scanner"), ("SAST", "semgrep"), ("workflows", "actionlint + zizmor"))
    for i, (name, tool) in enumerate(chips):
        x = 420 + i * 150
        s.chip(x, 356, 138, name, fill="work")
        s.text(x + 69, 416, f"`{tool}`", size=12, colour=t.dim)
    s.lock(1040, 376, size=12)
    s.text(1062, 380, "pinned,", size=12.5, anchor="start", colour=t.dim)
    s.text(1062, 396, "SHA-256", size=12.5, anchor="start", colour=t.dim)

    s.text(420, 470, "pipelines · only when their paths changed", size=15, anchor="start")
    s.chip(420, 490, 150, "synthetic", fill="neutral")
    s.chip(590, 490, 150, "corpus", fill="neutral")
    s.text(760, 516, "skipped jobs count as passing", size=14, anchor="start", colour=t.dim)

    s.arrow(330, 410, 410, 376, colour=t.muted, width=1.3)
    s.arrow(330, 420, 410, 508, colour=t.muted, width=1.3)
    s.button(970, 548, 160, "ci-ok", fill="done")
    s.arrow(1000, 400, 1030, 542, colour=t.muted, width=1.3)
    s.arrow(722, 532, 964, 560, colour=t.muted, width=1.3)
    s.text(560, 572, "`ci-ok` fails only on failure or cancelled", size=13.5, anchor="start", colour=t.dim)

    # -- claude-review.yml -------------------------------------------------------------------------
    s.shade(250, 630, 900, 180, fill="yellow", opacity=0.45)
    s.text(272, 662, "`claude-review.yml`", size=17, anchor="start")
    s.text(272, 686, "advisory, never required", size=14, anchor="start", colour=t.dim)
    s.chip(500, 650, 200, "spec-reviewer", fill="docs")
    s.text(600, 712, "when `docs/**` changed", size=12.5, colour=t.dim)
    s.chip(740, 650, 220, "security-reviewer", fill="problem")
    s.text(850, 712, "when anything else changed", size=12.5, colour=t.dim)
    s.envelope(990, 655, 50, 34)
    s.text(1050, 670, "inline + summary", size=13, anchor="start", colour=t.dim)
    s.text(1050, 688, "comments", size=13, anchor="start", colour=t.dim)
    s.text(272, 760, "skipped without `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`; base branch checked out,",
           size=13, anchor="start", colour=t.dim)
    s.text(272, 780, "the PR read through git; no edit, push, merge or approval", size=13, anchor="start", colour=t.dim)

    # -- branch protection -------------------------------------------------------------------------
    s.shade(1200, 120, 400, 690, fill="done", opacity=0.3)
    s.text(1222, 152, "branch protection", size=19, anchor="start")
    s.text(1222, 176, "set by Thomas, not yet on (inbox #8)", size=13.5, anchor="start", colour=t.dim)
    s.text(1312, 240, "required checks:", size=15, anchor="start")
    s.button(1310, 250, 180, "docs-gate", fill="done")
    s.button(1310, 294, 180, "pr-body", fill="done")
    s.button(1310, 548, 180, "ci-ok", fill="done")
    s.gate(1400, 480, 120, 100, state="closed")
    s.arrow(1100, 165, 1300, 262, colour=t.good, width=1.6)
    s.arrow(1100, 215, 1300, 306, colour=t.good, width=1.6)
    s.arrow(1134, 563, 1300, 563, colour=t.good, width=1.6)
    s.text(1222, 616, "never a path-filtered job:", size=14, anchor="start")
    s.text(1222, 636, "a skipped check never reports", size=14, anchor="start", colour=t.dim)
    s.text(1222, 656, "and the PR waits forever", size=14, anchor="start", colour=t.dim)
    s.lock(1236, 708, size=12)
    s.text(1256, 712, "`CODEOWNERS`: `.github/`, `.claude/`,", size=13, anchor="start", colour=t.dim)
    s.text(1256, 732, "`pipeline.yaml`, scanner ignore files", size=13, anchor="start", colour=t.dim)
    s.text(1256, 752, "need Thomas's review", size=13, anchor="start", colour=t.dim)

    s.text(40, H - 30, "Sources: .github/workflows/{ci,security,docs,claude-review}.yml, tools/ci/security.sh, "
                       ".github/CODEOWNERS on autopilot/D4; dev-environment-and-testing.md §11 · "
                       "tools/diagrams/d4_pr_checks.py", size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "d4_pr_checks")
