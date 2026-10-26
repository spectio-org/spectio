#!/usr/bin/env python3
"""Write the /versions page of the dev previews from the Cloudflare Pages deployments API.

  CLOUDFLARE_API_TOKEN=… CLOUDFLARE_ACCOUNT_ID=… \
  python3 tools/previews/versions_page.py --project spectio --out site/versions/index.html \
      --current-alias pr-42 --current-sha <sha>

Every deployment keeps its own URL, so the page lists them all, newest first, grouped by kind
(releases, waves, main, PRs). Spec: docs/specs/dev-environment-and-testing.md §7.1.
API: GET /accounts/{account}/pages/projects/{project}/deployments. The fields read here (url, created_on,
deployment_trigger.metadata.branch / commit_hash / commit_message) were checked against the live project on 2026-10-26.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import pathlib
import re
import sys
import urllib.request

API = "https://api.cloudflare.com/client/v4"


def fetch(project: str, max_pages: int = 10) -> list[dict]:
    token, account = os.environ["CLOUDFLARE_API_TOKEN"], os.environ["CLOUDFLARE_ACCOUNT_ID"]
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        req = urllib.request.Request(f"{API}/accounts/{account}/pages/projects/{project}/deployments?page={page}&per_page=25",
                                     headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:  # project not created yet: first deploy
                return out
            raise
        batch = data.get("result") or []
        out += batch
        if len(batch) < 25:
            break
    return out


def kind(alias: str) -> str:
    if re.fullmatch(r"v\d+-\d+-\d+.*", alias):
        return "release"
    if alias.startswith("wave-"):
        return "wave"
    if alias.startswith("pr-"):
        return "pr"
    return "main" if alias in ("main", "production") else "other"


def rows(deployments: list[dict]) -> list[dict]:
    out = []
    for d in deployments:
        meta = (d.get("deployment_trigger") or {}).get("metadata") or {}
        alias = meta.get("branch") or ("main" if d.get("environment") == "production" else "?")
        out.append({
            "alias": alias, "kind": kind(alias), "url": d.get("url", ""),
            "created": (d.get("created_on") or "")[:16].replace("T", " "),
            "sha": (meta.get("commit_hash") or "")[:7], "message": (meta.get("commit_message") or "").splitlines()[0][:90] if meta.get("commit_message") else "",
        })
    return out


TITLES = {"release": "Releases", "wave": "Validated waves", "main": "main", "pr": "Pull requests", "other": "Other"}


def render(items: list[dict], current: dict | None) -> str:
    def table(k: str) -> str:
        sel = [i for i in items if i["kind"] == k]
        if not sel:
            return ""
        trs = "".join(
            f"<tr><td><code>{html.escape(i['alias'])}</code></td><td>{html.escape(i['created'])}</td>"
            f"<td><code>{html.escape(i['sha'])}</code></td><td>{html.escape(i['message'])}</td>"
            f"<td><a href=\"{html.escape(i['url'])}\">open</a></td></tr>" for i in sel)
        return f"<h2>{TITLES[k]} <span class=n>{len(sel)}</span></h2><table><thead><tr><th>Preview</th><th>Deployed (UTC)</th><th>Commit</th><th>Message</th><th></th></tr></thead><tbody>{trs}</tbody></table>"
    cur = ""
    if current:
        cur = (f"<p class=cur>This build: <code>{html.escape(current['alias'])}</code> at <code>{html.escape(current['sha'][:7])}</code>. "
               "It appears in the list from the next deploy on.</p>")
    body = "".join(table(k) for k in ("release", "wave", "main", "pr", "other")) or "<p>No deployment yet.</p>"
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Spectio · preview versions</title><link rel=icon href="../assets/brand/favicon.svg">
<style>
:root{{--ink:#0F1020;--dim:#4D5065;--line:#DFE1EA;--accent:#6344B2;--bg:#fff;--sub:#F7F7FB}}
@media (prefers-color-scheme:dark){{:root{{--ink:#F1F2F8;--dim:#C4C7D4;--line:#2A2D45;--accent:#BEA4FA;--bg:#11121F;--sub:#171A2E}}}}
body{{margin:0;font:15px/1.5 Inter,system-ui,sans-serif;color:var(--ink);background:var(--bg)}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:26px;margin:8px 0 4px}} h2{{font-size:18px;margin:32px 0 8px}} .n{{color:var(--dim);font-weight:400}}
p{{color:var(--dim)}} a{{color:var(--accent)}} code{{font:13px "JetBrains Mono",monospace}}
.wrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}} td:nth-child(4){{white-space:normal}}
th{{color:var(--dim);font-weight:600;background:var(--sub)}} .cur{{background:var(--sub);padding:8px 12px;border-radius:6px}}
</style></head><body><main>
<p><a href="../">← back to the docs</a></p>
<h1>Preview versions</h1>
<p>Every dev preview stays online at its own URL; nothing is overwritten. Releases, validated waves, main and pull requests, newest first.</p>
{cur}<div class=wrap>{body}</div>
</main></body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--current-alias")
    ap.add_argument("--current-sha", default="")
    ap.add_argument("--from-json", help="read deployments from a file instead of the API (tests)")
    a = ap.parse_args()
    deployments = json.loads(pathlib.Path(a.from_json).read_text())["result"] if a.from_json else fetch(a.project)
    items = rows(deployments)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    current = {"alias": a.current_alias, "sha": a.current_sha} if a.current_alias else None
    out.write_text(render(items, current))
    print(f"versions: {len(items)} deployments listed -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
