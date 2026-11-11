"""MkDocs hook: render pipeline progress from docs/playbooks/pipeline.yaml and .autopilot/state.json.

Placeholders replaced in page Markdown:
  <!-- spectio:progress-strip -->  compact per-wave strip (landing page)
  <!-- spectio:progress-table -->  per wave, the steps done and the links to its Progress pages

Spec: docs/specs/documentation-system.md §2 and §3.2.
"""
from __future__ import annotations

import json
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
ICON = {
    "done": ":material-check-circle:{ .sp-ok }",
    "running": ":material-progress-clock:{ .sp-run }",
    "waiting_human": ":material-account-clock:{ .sp-wait }",
    "blocked": ":material-alert-octagon:{ .sp-bad }",
    "failed": ":material-close-circle:{ .sp-bad }",
    "pending": ":material-circle-outline:{ .sp-muted }",
}


def _load():
    pipeline = yaml.safe_load((ROOT / "docs/playbooks/pipeline.yaml").read_text())
    state_path = ROOT / ".autopilot/state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"steps": {}}
    return pipeline, state.get("steps", {})


def _status(steps, sid):
    return steps.get(sid, {}).get("status", "pending")


def _strip(pipeline, steps, base: str = "") -> str:
    cells = []
    for wave in pipeline["waves"]:
        ids = [s["id"] for s in wave["steps"]]
        done = sum(_status(steps, i) == "done" for i in ids)
        pct = round(100 * done / len(ids)) if ids else 0
        cells.append(
            f'<a class="sp-wave" href="{base}progress/#{wave["id"].lower()}">'
            f'<span class="sp-wave__id">{wave["id"]}</span>'
            f'<span class="sp-wave__bar"><span style="width:{pct}%"></span></span>'
            f'<span class="sp-wave__count">{done}/{len(ids)}</span>'
            f'<span class="sp-wave__title">{_short(wave["title"])}</span></a>'
        )
    return '<div class="sp-waves" markdown>' + "".join(cells) + "</div>"


def _short(title: str) -> str:
    """A wave's title up to its first comma or parenthesis: "Foundations", "Synthesis"."""
    return re.split(r"[,(]", title, maxsplit=1)[0].strip()


def _title(page: pathlib.Path) -> str:
    """A step page's heading without its step id, notes in italics or names."""
    for line in page.read_text().splitlines():
        if line.startswith("# "):
            t = re.sub(r"\s*\*\(.*?\)\*", "", line[2:])
            t = re.sub(r"\bThomas's\s+|\s*\bThomas\b", "", t)
            return re.sub(r"^[A-Z0-9-]+(?: [A-Z0-9-]+)?\s*[·:]\s*", "", t).strip()
    return page.stem


def _table(pipeline, steps, page_dir: pathlib.Path) -> str:
    """One folded line per wave: its short title and steps done; open it for the wave's pages."""
    out = []
    for wave in pipeline["waves"]:
        ids = [s["id"] for s in wave["steps"]]
        done = sum(_status(steps, i) == "done" for i in ids)
        order = {sid: n for n, sid in enumerate(ids)}
        pages = sorted((page_dir / wave["id"]).glob("*.md"), key=lambda f: (order.get(f.stem, len(order)), f.stem))
        kind, fold = ("success", "???") if done == len(ids) else ("info", "???+")
        out.append(f'\n<a id="{wave["id"].lower()}" class="sp-progress"></a>\n')
        out.append(f'{fold} {kind} "{wave["id"]} · {_short(wave["title"])} · {done} of {len(ids)} done"\n')
        out += [f"    - [{_title(f)}]({wave['id']}/{f.name})" for f in pages] or ["    No page yet."]
    return "\n".join(out) + "\n"


def on_page_markdown(markdown: str, page, config, files):
    if "<!-- spectio:progress-" not in markdown:
        return markdown
    pipeline, steps = _load()
    if "<!-- spectio:progress-strip -->" in markdown:
        depth = page.file.src_uri.count("/") + (0 if page.file.src_uri.endswith("index.md") or page.file.src_uri == "index.md" else 1)
        base = "../" * depth
        markdown = markdown.replace("<!-- spectio:progress-strip -->", _strip(pipeline, steps, base))
    if "<!-- spectio:progress-table -->" in markdown:
        page_dir = pathlib.Path(config["docs_dir"]) / "progress"
        markdown = markdown.replace("<!-- spectio:progress-table -->", _table(pipeline, steps, page_dir))
    return markdown
