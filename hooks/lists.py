"""MkDocs hook: accept 2-space (and 3-space under "1.") nested lists, as GitHub renders them.

Python-Markdown nests a list only under 4 spaces, so sub-bullets written with 2 spaces render
as one flat list. For each top-level list block whose smallest indentation is under 4 spaces,
this hook re-indents the block by nesting level, 4 spaces per level (fenced code included,
so code under a list item stays inside it). Blocks already written with 4 spaces are untouched.
It also adds the blank line Python-Markdown needs between a paragraph and a list that follows it.
Fenced code at column 0 and everything outside lists are never changed.
"""
from __future__ import annotations

import re

ITEM = re.compile(r"^([-*+]|\d+[.)]) ")
FENCE = re.compile(r"^(```|~~~)")


def _fix_block(lines: list[str]) -> list[str]:
    indents = [len(l) - len(l.lstrip(" ")) for l in lines if l.strip() and l.startswith(" ")]
    if not indents or min(indents) >= 4:
        return lines
    # Re-indent by nesting: each item's content sits 4 spaces past its own marker.
    stack: list[tuple[int, int, int]] = []  # (item indent, content indent, new content indent)
    out = []
    for l in lines:
        if not l.strip():
            out.append(l)
            continue
        n = len(l) - len(l.lstrip(" "))
        body = l[n:]
        m = ITEM.match(body)
        if m:
            prev = out[-1] if out else ""
            while stack and stack[-1][0] >= n:
                stack.pop()
            new_n = stack[-1][2] if stack else 0
            prev_n = len(prev) - len(prev.lstrip(" "))
            text_before = prev.startswith(" ") and not ITEM.match(prev.lstrip(" ")) and not prev.lstrip().startswith(("```", "~~~", "|"))
            if prev.strip() and (text_before or prev_n > new_n):
                out.append("")  # Python-Markdown would otherwise merge this item into the line above
            stack.append((n, n + len(m.group(0)), new_n + 4))
            out.append(" " * new_n + body)
            continue
        owner = next((e for e in reversed(stack) if e[1] <= n), None)
        if owner is None:
            owner = next((e for e in reversed(stack) if e[0] < n), None)
        out.append(" " * (owner[2] + max(0, n - owner[1])) + body if owner else l)
    return out


def on_page_markdown(markdown: str, page, config, files):
    lines = markdown.split("\n")
    out: list[str] = []
    block: list[str] = []
    in_top_fence = False
    for line in lines:
        if in_top_fence:
            out.append(line)
            if FENCE.match(line):
                in_top_fence = False
            continue
        top = line[:1] not in ("", " ")
        if block:
            if not line.strip() or line.startswith(" ") or ITEM.match(line):
                block.append(line)
                continue
            out.extend(_fix_block(block))
            block = []
        if FENCE.match(line):
            in_top_fence = True
            out.append(line)
        elif top and ITEM.match(line):
            # GitHub starts a list right after a paragraph line; Python-Markdown needs a blank line.
            if out and out[-1].strip() and not out[-1].lstrip().startswith(("|", "<", "#")):
                out.append("")
            block.append(line)
        else:
            out.append(line)
    out.extend(_fix_block(block))
    return "\n".join(out)
