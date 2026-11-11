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
            f'<span class="sp-wave__title">{wave["title"]}</span></a>'
        )
    return '<div class="sp-waves" markdown>' + "".join(cells) + "</div>"


def _title(page: pathlib.Path) -> str:
    for line in page.read_text().splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return page.stem


def _table(pipeline, steps, page_dir: pathlib.Path) -> str:
    """One short section per wave: how many steps are done, then its pages, folded once the wave is done."""
    out = []
    for wave in pipeline["waves"]:
        ids = [s["id"] for s in wave["steps"]]
        done = sum(_status(steps, i) == "done" for i in ids)
        title = re.sub(r"\s*\(.*?\)", "", wave["title"]).strip()
        out.append(f'\n## {wave["id"]} · {title} {{ #{wave["id"].lower()} }}\n')
        out.append(f'<p class="sp-progress">{done} of {len(ids)} steps done</p>\n')
        order = {sid: n for n, sid in enumerate(ids)}
        pages = sorted((page_dir / wave["id"]).glob("*.md"), key=lambda f: (order.get(f.stem, len(order)), f.stem))
        if not pages:
            continue
        fold = "???" if done == len(ids) else "???+"
        out.append(f'{fold} note "Pages ({len(pages)})"\n')
        out += [f"    - [{_title(f)}]({wave['id']}/{f.name})" for f in pages]
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
