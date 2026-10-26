#!/usr/bin/env python3
"""The docs gate (docs/specs/documentation-system.md §3.3 and §7.3).

  python3 tools/docs/check.py                      # all repository checks
  python3 tools/docs/check.py --skip build,mermaid # e.g. when CI runs those as separate steps
  python3 tools/docs/check.py --only pr-body --pr-title "feat(x): y" --pr-body body.md --changed changed.txt

Checks: build, mermaid, diagrams (freshness), media (manifest, sizes), progress (front matter), pr-body.
Exit 1 if any check fails; every failure is printed as a GitHub annotation.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
MEDIA_DIRS = ["docs/assets/shots", "docs/assets/casts", "docs/assets/media", "docs/assets/diagrams"]
VIDEO_MAX = 3 * 2**20
VIDEO_SECONDS = 30
MEDIA_EXT = {".png", ".webp", ".jpg", ".jpeg", ".gif", ".svg", ".cast", ".mp4", ".webm"}
PR_MEDIA_MAX = 5 * 2**20
STATUSES = {"running", "done", "blocked"}
REVIEWS = {None, "approve", "changes", "block"}
TITLE_RE = re.compile(r"^(feat|fix|docs|test|ci|chore|refactor|perf|build|revert|autopilot)(\([\w./-]+\))?!?: .+")
PR_SECTIONS = ["## Summary", "## Docs", "## Evidence", "## Checks"]

failures: list[str] = []


def fail(check: str, msg: str, file: str | None = None) -> None:
    failures.append(f"{check}: {msg}")
    loc = f" file={file}" if file else ""
    print(f"::error{loc}::[{check}] {msg}")


def check_build() -> None:
    with tempfile.TemporaryDirectory() as site:
        r = subprocess.run(["uvx", "--with", "mkdocs-material", "mkdocs", "build", "--strict", "-q", "-d", site],
                           cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        fail("build", "mkdocs build --strict failed:\n" + (r.stderr or r.stdout)[-3000:])


def check_mermaid() -> None:
    blocks = [(md, b) for md in sorted(DOCS.rglob("*.md"))
              for b in re.findall(r"```mermaid\n(.*?)```", md.read_text(), re.S)]
    with tempfile.TemporaryDirectory() as d:
        for i, (md, block) in enumerate(blocks):
            src = pathlib.Path(d, f"{i}.mmd")
            src.write_text(block)
            r = subprocess.run(["npx", "-y", "@mermaid-js/mermaid-cli@11", "-q", "-i", str(src), "-o", str(src.with_suffix(".svg"))],
                               capture_output=True, text=True)
            if r.returncode:
                fail("mermaid", f"block {i} does not render: {r.stderr[-400:]}", str(md.relative_to(ROOT)))
    print(f"mermaid: {len(blocks)} blocks checked")


def check_diagrams() -> None:
    """Re-run every figure script into a temporary folder (SVG only) and compare with the committed SVGs."""
    scripts = [p for p in sorted((ROOT / "tools/diagrams").glob("*.py")) if p.name != "sketch.py" and not p.name.startswith("_")]
    committed = ROOT / "docs/assets/diagrams"
    compared = 0
    with tempfile.TemporaryDirectory() as out:
        for s in scripts:
            r = subprocess.run([sys.executable, str(s), "--no-png", "--out", out], cwd=s.parent, capture_output=True, text=True)
            if r.returncode:
                fail("diagrams", f"{s.name} failed: {r.stderr[-400:]}", str(s.relative_to(ROOT)))
        for svg in sorted(pathlib.Path(out).glob("*.svg")):
            compared += 1
            ref = committed / svg.name
            if not ref.exists():
                fail("diagrams", f"{svg.name} is generated but not committed", f"docs/assets/diagrams/{svg.name}")
            elif hashlib.sha256(ref.read_bytes()).digest() != hashlib.sha256(svg.read_bytes()).digest():
                fail("diagrams", f"{svg.name} is stale: its script now draws something else (re-run it, commit SVG and PNG)",
                     f"docs/assets/diagrams/{svg.name}")
    print(f"diagrams: {len(scripts)} scripts re-run, {compared} SVGs compared")


def _duration(p: pathlib.Path) -> float | None:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def check_media_budget(base: str) -> None:
    """New or changed media against the base branch: at most 5 MB per PR."""
    r = subprocess.run(["git", "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD"],
                       cwd=ROOT, capture_output=True, text=True)
    media = [f for f in r.stdout.split() if pathlib.Path(f).suffix.lower() in MEDIA_EXT and not f.startswith("design/")]
    total = sum((ROOT / f).stat().st_size for f in media if (ROOT / f).exists())
    if total > PR_MEDIA_MAX:
        fail("media", f"this change adds {total / 2**20:.1f} MB of media (max 5 MB per PR)")
    print(f"media budget: {total / 2**20:.2f} MB new or changed against {base}")


def check_media() -> None:
    manifest_path = ROOT / "docs/assets/media.yaml"
    manifest = yaml.safe_load(manifest_path.read_text()) if manifest_path.exists() else {"media": []}
    listed = {}
    for m in manifest.get("media", []):
        for path in m.get("outputs", []):
            listed[path] = m
    for d in MEDIA_DIRS:
        for p in (ROOT / d).glob("*") if (ROOT / d).exists() else []:
            rel = str(p.relative_to(ROOT))
            if p.is_file() and rel not in listed:
                fail("media", "not listed in docs/assets/media.yaml (add it with its generator command)", rel)
            if p.suffix in {".mp4", ".webm"} and p.stat().st_size > VIDEO_MAX:
                fail("media", f"video is {p.stat().st_size / 2**20:.1f} MB (max 3 MB)", rel)
            if p.suffix in {".mp4", ".webm"}:
                d = _duration(p)
                if d is not None and d > VIDEO_SECONDS:
                    fail("media", f"video is {d:.1f} s long (max {VIDEO_SECONDS} s)", rel)
            if p.suffix == ".gif":
                fail("media", "GIF previews are for PR bodies: generate them outside docs/assets/", rel)
    for rel, m in listed.items():
        if not (ROOT / rel).exists():
            fail("media", f"listed but missing (generator: {m.get('generator')})", rel)
        if not m.get("generator"):
            fail("media", "no generator command", rel)
    tracked_gifs = subprocess.run(["git", "ls-files", "*.gif", "*.GIF"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    for g in tracked_gifs:
        fail("media", "GIF previews are for PR bodies and are not committed (git rm --cached it)", g)
    print(f"media: {len(listed)} outputs in the manifest")


def check_progress() -> None:
    pages = [p for p in (DOCS / "progress").glob("*/*.md")]
    for p in pages:
        text = p.read_text()
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        rel = str(p.relative_to(ROOT))
        if not m:
            fail("progress", "missing front matter", rel)
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        if fm.get("step") != p.stem or fm.get("wave") != p.parent.name:
            fail("progress", f"step/wave in front matter ({fm.get('step')}/{fm.get('wave')}) do not match the path", rel)
        if fm.get("status") not in STATUSES:
            fail("progress", f"status must be one of {sorted(STATUSES)}", rel)
        if fm.get("review") not in REVIEWS:
            fail("progress", "review must be approve, changes or block", rel)
        if fm.get("status") == "done" and fm.get("review") != "approve":
            fail("progress", "a done step needs review: approve", rel)
        for heading in ("## What changed", "## Evidence"):
            if heading not in text:
                fail("progress", f"missing section '{heading}'", rel)
    print(f"progress: {len(pages)} pages checked")


def check_pr_body(title: str, body_file: str, changed_file: str | None, labels: str) -> None:
    body = pathlib.Path(body_file).read_text()
    if not TITLE_RE.match(title):
        fail("pr-body", f"title is not a Conventional Commit: {title!r}")
    for s in PR_SECTIONS:
        if s not in body:
            fail("pr-body", f"missing section '{s}'")
    changed = pathlib.Path(changed_file).read_text().split() if changed_file else []
    kind = title.split(":", 1)[0].split("(")[0].rstrip("!")
    touches_mechanism = any(c.startswith(("docs/specs/", "tools/", "src/", "packages/")) for c in changed)
    has_figure = bool(re.search(r"!\[[^\]]*\]\([^)]*docs/assets/diagrams/[^)]+\.png", body))
    if kind in {"feat", "docs"} and touches_mechanism and not has_figure and "no-figure" not in labels.split(","):
        fail("pr-body", "a feat/docs PR that changes a mechanism needs a sketch figure (or the no-figure label with a reason)")
    print(f"pr-body: checked ({len(changed)} changed files)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only")
    ap.add_argument("--skip", default="")
    ap.add_argument("--pr-title")
    ap.add_argument("--pr-body")
    ap.add_argument("--changed")
    ap.add_argument("--labels", default="")
    ap.add_argument("--base", help="base ref for the per-PR media budget, e.g. origin/main")
    a = ap.parse_args()
    checks = {"build": check_build, "mermaid": check_mermaid, "diagrams": check_diagrams,
              "media": check_media, "progress": check_progress}
    wanted = a.only.split(",") if a.only else [c for c in [*checks, "pr-body"] if c not in a.skip.split(",")]
    for name in wanted:
        if name == "pr-body":
            if a.pr_body:
                check_pr_body(a.pr_title or "", a.pr_body, a.changed, a.labels)
            continue
        checks[name]()
        if name == "media" and a.base:
            check_media_budget(a.base)
    print(f"docs gate: {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
