#!/usr/bin/env python3
"""Fail when an agent or skill under .claude has frontmatter Claude Code would not load as intended.

Usage: python3 tools/claude/check_frontmatter.py [ROOT]   (ROOT defaults to .claude)

Rules (docs/specs/dev-environment-and-testing.md §11):
- agents/**/*.md and skills/<name>/SKILL.md start with a YAML frontmatter block on line 1, closed by `---`;
- the block parses as a YAML mapping;
- agents have a `name` (no leading `-`, no `:`, at most 256 characters), unique across agents, and a `description`;
- skills have a `description` (a repository rule: Claude Code would fall back to the first body line);
- every directory under skills/ has a SKILL.md;
- every field is one Claude Code documents (it ignores unknown fields silently, so a typo would go unnoticed).
Sources: https://code.claude.com/docs/en/sub-agents.md and https://code.claude.com/docs/en/skills.md (2026-10-27).
"""
import pathlib
import sys

import yaml

AGENT_FIELDS = {
    "name", "description", "tools", "disallowedTools", "model", "permissionMode", "maxTurns",
    "autoCompactWindow", "skills", "mcpServers", "hooks", "memory", "background", "omitClaudeMd",
    "effort", "isolation", "color", "initialPrompt", "experimental",
}
SKILL_FIELDS = {
    "name", "description", "when_to_use", "argument-hint", "arguments", "disable-model-invocation",
    "user-invocable", "allowed-tools", "disallowed-tools", "model", "effort", "context", "agent",
    "background", "hooks", "paths", "shell", "metadata", "license", "compatibility",
}


def frontmatter(path):
    """Return (mapping, None) or (None, problem)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].rstrip() != "---":
        return None, "no frontmatter (line 1 must be `---`)"
    end = next((i for i, line in enumerate(lines[1:], 1) if line.rstrip() == "---"), None)
    if end is None:
        return None, "frontmatter is not closed by `---`"
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" (file line {mark.line + 2})" if mark else ""  # +1 for 0-based, +1 for the opening `---`
        return None, f"YAML does not parse{where}: {getattr(e, 'problem', None) or e}"
    if not isinstance(data, dict):
        return None, "frontmatter is not a mapping"
    return data, None


def problems(data, known):
    out = [f"unknown field `{k}`" for k in data if k not in known]
    if not (isinstance(data.get("description"), str) and data["description"].strip()):
        out.append("`description` is missing or empty")
    return out


def check(root):
    errors, names = [], {}
    agents = sorted((root / "agents").rglob("*.md"))  # Claude Code scans agents/ recursively
    for path in agents:
        rel = path.relative_to(root)
        data, err = frontmatter(path)
        if err:
            errors.append(f"{rel}: {err}")
            continue
        errors += [f"{rel}: {p}" for p in problems(data, AGENT_FIELDS)]
        name = data.get("name")
        if not (isinstance(name, str) and name.strip()):
            errors.append(f"{rel}: `name` is missing or empty (the agent would not load)")
        elif name.startswith("-") or ":" in name or len(name) > 256:
            errors.append(f"{rel}: `name` {name!r} starts with `-`, contains `:` or is over 256 characters")
        elif name in names:
            errors.append(f"{rel}: `name` {name} is also used by {names[name]}")
        else:
            names[name] = rel
    skill_dirs = sorted(p for p in (root / "skills").glob("*") if p.is_dir())
    for d in skill_dirs:
        path = d / "SKILL.md"
        rel = path.relative_to(root)
        if not path.is_file():
            errors.append(f"{d.relative_to(root)}: no SKILL.md")
            continue
        data, err = frontmatter(path)
        if err:
            errors.append(f"{rel}: {err}")
            continue
        errors += [f"{rel}: {p}" for p in problems(data, SKILL_FIELDS)]
    for e in errors:
        print(e)
    print(f"{len(agents)} agent(s), {len(skill_dirs)} skill(s) checked in {root}: {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(check(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".claude")))
