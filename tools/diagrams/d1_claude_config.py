#!/usr/bin/env python3
"""Figure for step D1: what loads from .claude, and the frontmatter check that guards it.

Writes docs/assets/diagrams/d1_claude_config_{light,dark}.{svg,png}.

Counts come from the step's own runs (docs/progress/W3/D1.md, Evidence):
- `claude -p --debug-file` on Claude Code 2.1.311 listed 14 project agents; the debug log
  says "project: 22" skills; 18 skills were in the model's list, 4 set
  `disable-model-invocation: true` (review-round, apply-findings, verify-claims, spike);
- `python3 tools/claude/check_frontmatter.py` on .claude: 14 agents, 22 skills, 0 problems;
- the four fixture cases, run through `claude plugin validate --strict` and through the check.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1640, 790
AGENTS, SKILLS, SLASH_ONLY = 14, 22, 4
CASES = (  # (fixture, caught by `claude plugin validate --strict`, caught by the check): exit 1 = caught
    ("unclosed quote in the YAML", True, True),
    ("`name: [broken` (PyYAML rejects it)", False, True),
    ("agent with no `description`", True, True),
    ("agent with no `name` (does not load)", False, True),
    ("unknown field, e.g. a typo", False, True),
)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=41)
    t = theme

    s.heading(40, 52, "D1 · Agents and skills: what loads, and the check that keeps it so",
              "Claude Code 2.1.311 · tools/claude/check_frontmatter.py · .github/workflows/claude-config.yml")

    # -- 1. the .claude folder, to scale -----------------------------------------------------------
    s.shade(30, 110, 520, 560, fill="neutral", opacity=0.5)
    s.folder(56, 130, 150, 70, label=".claude/")
    s.text(56, 238, f"agents/ · {AGENTS} files", size=17, anchor="start")
    for i in range(AGENTS):
        s.page(56 + (i % 7) * 64, 254 + (i // 7) * 70, 44, 56, fill="input", lines=2)
    s.text(56, 420, f"skills/ · {SKILLS} folders", size=17, anchor="start")
    for i in range(SKILLS):
        slash = i >= SKILLS - SLASH_ONLY
        s.folder(56 + (i % 8) * 58, 436 + (i // 8) * 48, 46, 34, fill="docs" if not slash else "gate")
    s.text(56, 600, f"{SKILLS - SLASH_ONLY} in Claude's skill list (violet)", size=14, anchor="start", colour=t.dim)
    s.text(56, 622, f"{SLASH_ONLY} slash-only: `disable-model-invocation: true` (yellow)", size=14,
           anchor="start", colour=t.dim)
    s.step(290, 690, 1, "a headless run loaded all of them")

    # -- 2. the check --------------------------------------------------------------------------------
    s.shade(580, 110, 470, 560, fill="docs", opacity=0.3)
    s.magnifier(640, 168, 26)
    s.text(690, 160, "check_frontmatter.py", size=18, anchor="start")
    s.text(690, 182, "PyYAML, rules from the Claude Code docs", size=13.5, anchor="start", colour=t.dim)
    rules = (
        "`---` on line 1, closed, parses, a mapping",
        "agent `name`: set, unique, no `:`, no leading `-`",
        "`description` on every agent and skill",
        "only documented fields",
        "a `SKILL.md` in every skill folder",
    )
    for k, rule in enumerate(rules):
        s.tick(616, 250 + k * 40, size=7)
        s.text(636, 256 + k * 40, rule, size=14.5, anchor="start")
    s.arrow(552, 390, 600, 390)
    s.terminal(604, 470, 422, 150, (
        "$ python3 tools/claude/check_frontmatter.py",
        f"{AGENTS} agent(s), {SKILLS} skill(s) checked",
        "in .claude: 0 problem(s)",
        "$ echo $?",
        "0             (1 on a broken fixture)",
    ), size=12.5)
    s.step(815, 690, 2, "CI: claude-config on every PR")

    # -- 3. why not `claude plugin validate` -----------------------------------------------------
    s.shade(1080, 110, 530, 560, fill="work", opacity=0.25)
    s.text(1104, 148, "the same broken fixtures", size=18, anchor="start")
    s.text(1104, 170, "✓ caught (exit 1) · ✗ missed (exit 0)", size=13.5, anchor="start", colour=t.dim)
    s.text(1430, 214, "validate", size=13.5, weight="bold")
    s.text(1540, 214, "check", size=13.5, weight="bold")
    for k, (case, by_validate, by_check) in enumerate(CASES):
        y = 262 + k * 56
        s.text(1104, y, case, size=14.5, anchor="start")
        for cx, caught in ((1430, by_validate), (1540, by_check)):
            if caught:
                s.tick(cx, y - 5, size=9, colour=t.good)
            else:
                s.cross(cx, y - 5, size=10)
    s.text(1104, 548, "`--strict` passed the three crossed fixtures", size=14, anchor="start", colour=t.dim)
    s.text(1104, 570, "with exit 0; the sub-agents docs say an agent", size=14, anchor="start", colour=t.dim)
    s.text(1104, 592, "with no `name` is skipped silently at load time", size=14, anchor="start", colour=t.dim)
    s.step(1345, 690, 3, "so CI uses the small check")

    s.text(40, H - 30, "Sources: docs/progress/W3/D1.md (Evidence) · https://code.claude.com/docs/en/sub-agents.md and "
                       "skills.md, read 2026-10-27 · tools/diagrams/d1_claude_config.py", size=12.5,
           anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "d1_claude_config")
