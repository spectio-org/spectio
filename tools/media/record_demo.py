#!/usr/bin/env python3
"""Record a demo server's GET answers into web/demo/fixtures.json, for the public demo.

The demo build of the screens (`npm --prefix web run build:demo`) answers the API from this file
(web/src/demo/stub.ts). The server is the one of the live shots (README.md, "The public demo"):

    python3 tools/media/record_demo.py --base http://127.0.0.1:8766

It records /version, the runs list and summary, each run with its processes, stages, tasks and
three logs, and the inspection of each pipeline under /g/demo-lab/pipelines. Lists are recorded
whole (every page), so the stub can filter and page them as the server does. Nothing is written
when the hygiene check of fixtures.yaml (sanitize.leaks) or the recorder's own host name or
kernel release hits; Nextflow's 'System: Linux <release>' banner line is cut to 'System: Linux'.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sanitize

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web" / "demo" / "fixtures.json"
PIPELINES = [
    "/g/demo-lab/pipelines/synthetic",
    "/g/demo-lab/pipelines/synthetic-smk",
    "/g/demo-lab/pipelines/nf-core-demo",
]
LOGS = ("head-out", "head-err", "engine")
MAX_BYTES = 1_500_000  # the brief's budget for the whole file


Answer = dict[str, Any]


def recorder(base: str) -> tuple[dict[str, Answer], Callable[[str], Answer]]:
    out: dict[str, Answer] = {}

    def get(path: str) -> Answer:
        try:
            # the base is the operator's own --base (a loopback demo server)
            r = urllib.request.urlopen(base + "/api/v1" + path, timeout=60)  # noqa: S310
        except urllib.error.HTTPError as e:
            r = e
        with r:
            out[path] = {
                "status": r.status,
                "type": r.headers.get("content-type"),
                "body": r.read().decode(),
            }
        return out[path]

    return out, get


def whole_list(get: Callable[[str], Answer], out: dict[str, Answer], path: str) -> list[Answer]:
    """Every page of a list, stored at `path` as one page with `next: null`."""
    items: list[dict[str, Any]] = []
    cursor = None
    while True:
        query = {"limit": "200", **({"cursor": cursor} if cursor else {})}
        page_path = f"{path}?{urllib.parse.urlencode(query)}"
        answer = get(page_path)
        del out[page_path]
        if answer["status"] != 200:
            raise SystemExit(f"{page_path}: HTTP {answer['status']}")
        page = json.loads(answer["body"])
        items += page["items"]
        cursor = page["next"]
        if not cursor:
            break
    out[path] = {**answer, "body": json.dumps({"items": items, "next": None})}
    return items


def record(base: str) -> dict[str, Answer]:
    out, get = recorder(base)
    get("/version")
    get("/runs:summary?group_by=state")
    for run in whole_list(get, out, "/runs"):
        path = "/runs/" + run["id"]
        for part in ("", "/processes", "/stages"):
            get(path + part)
        whole_list(get, out, path + "/tasks")
        for source in LOGS:  # the server serves the last 64 KiB of each, as the UI shows
            get(f"{path}/logs?{urllib.parse.urlencode({'source': source})}")
    for location in PIPELINES:
        get("/workflows:inspect?" + urllib.parse.urlencode({"location": location}))
    return out


def neutral(text: str) -> str:
    """Nextflow's CmdRun banner without the recording host's kernel release (SEC-P3DEMO-02)."""
    return re.sub(r"\bSystem: Linux [^\s\"\\]+", "System: Linux", text)


def problems(text: str) -> list[str]:
    found = sanitize.leaks(text)
    host = socket.gethostname()
    if host != "login1" and host in text:
        found.append(f"the recorder's host name {host!r}")
    if platform.release() in text:
        found.append(f"the recorder's kernel release {platform.release()!r}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:8766", help="the demo server")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    text = neutral(json.dumps(record(args.base.rstrip("/")), ensure_ascii=False, indent=1, sort_keys=True))
    found = problems(text)
    if found:
        print("not written, the hygiene check hits:", *found, sep="\n  ", file=sys.stderr)
        return 1
    size = len(text.encode())
    if size > MAX_BYTES:
        print(f"not written: {size} bytes, over {MAX_BYTES}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text + "\n", encoding="utf-8")
    print(f"{args.out}: {len(json.loads(text))} answers, {size} bytes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
