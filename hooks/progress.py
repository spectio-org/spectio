"""MkDocs hook: render pipeline progress from docs/playbooks/pipeline.yaml and .autopilot/state.json.

Placeholders replaced in page Markdown:
  <!-- spectio:progress-strip -->  compact per-wave strip (landing page)
  <!-- spectio:progress-table -->  one row per step, linking its Progress page when it exists

Spec: docs/specs/documentation-system.md §2 and §3.2.
"""
from __future__ import annotations

import json
import pathlib

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


def _table(pipeline, steps, page_dir: pathlib.Path) -> str:
    out = []
    for wave in pipeline["waves"]:
        out.append(f'\n## {wave["id"]} · {wave["title"]} {{ #{wave["id"].lower()} }}\n')
        out.append("| Step | Kind | Status | Page |\n|---|---|---|---|")
        for s in wave["steps"]:
            sid, st = s["id"], _status(steps, s["id"])
            page = page_dir / wave["id"] / f"{sid}.md"
            link = f"[{sid}]({wave['id']}/{sid}.md)" if page.exists() else "—"
            out.append(f"| {sid} | {s['kind']} | {ICON.get(st, st)} {st.replace('_', ' ')} | {link} |")
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


def on_nav(nav, config, files):
    """Put every docs/progress/<wave>/<step>.md page under the Progress tab, one section per wave,
    so step pages are in the navigation without editing mkdocs.yml for each new step."""
    from mkdocs.structure.nav import Section, _add_parent_links, _add_previous_and_next_links, _get_by_type
    from mkdocs.structure.pages import Page

    def find(items):
        for i in items:
            if isinstance(i, Section):
                if i.title == "Progress":
                    return i
                hit = find(i.children)
                if hit:
                    return hit
        return None

    progress = find(nav.items)
    if progress is None:
        return nav
    pipeline, _ = _load()
    titles = {w["id"]: w["title"] for w in pipeline["waves"]}
    by_wave: dict[str, list] = {}
    for f in files.documentation_pages():
        parts = pathlib.PurePosixPath(f.src_uri).parts
        if len(parts) == 3 and parts[0] == "progress":
            page = f.page or Page(None, f, config)
            by_wave.setdefault(parts[1], []).append(page)
    order = [w["id"] for w in pipeline["waves"]]
    for wave in sorted(by_wave, key=lambda w: order.index(w) if w in order else 99):
        pages = sorted(by_wave[wave], key=lambda p: p.file.src_uri)
        progress.children.append(Section(f"{wave} · {titles.get(wave, '')}".strip(" ·"), pages))
    _add_parent_links(nav.items)
    nav.pages = _get_by_type(nav.items, Page)
    _add_previous_and_next_links(nav.pages)
    return nav
