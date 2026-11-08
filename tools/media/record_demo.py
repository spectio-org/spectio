#!/usr/bin/env python3
"""Record a demo server's GET answers into web/demo/fixtures.json, for the public demo.

The demo build of the screens (`npm --prefix web run build:demo`) answers the API from this file
(web/src/demo/stub.ts). The server is the one of the live shots (README.md, "The public demo"):

    python3 tools/media/record_demo.py --base http://127.0.0.1:8766

It records /version, the runs list and summary, each run with its processes, stages, tasks, three
logs, launch template and results folders, the job files (list and text, every attempt) of a
sample of tasks (files_sample), and the inspection of each pipeline under
/g/demo-lab/pipelines. Lists are recorded whole (every page), so the stub can filter and page them
as the server does. The server asks for a sign-in: SPECTIO_SESSION_COOKIE=<name>=<value> is sent
with each request, as for the live shots; it is never written. Nothing is written
when the hygiene check of fixtures.yaml (sanitize.leaks) or the recorder's own host name or
kernel release hits; Nextflow's 'System: Linux <release>' banner line is cut to 'System: Linux'.
"""

from __future__ import annotations

import argparse
import json
import os
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
RESULTS_MAX_DIRS = 20  # results folders per run
MAX_BYTES = 1_500_000  # the brief's budget for the whole file


Answer = dict[str, Any]


Get = Callable[[str], Answer]
Task = dict[str, Any]


def recorder(base: str, cookie: str | None = None) -> tuple[dict[str, Answer], Get]:
    out: dict[str, Answer] = {}
    headers = {"Cookie": cookie} if cookie else {}

    def get(path: str) -> Answer:
        # the base is the operator's own --base (a loopback demo server)
        request = urllib.request.Request(base + "/api/v1" + path, headers=headers)  # noqa: S310
        try:
            r = urllib.request.urlopen(request, timeout=60)  # noqa: S310
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


def results(get: Get, path: str) -> None:
    """The run's results folders, the root first, as the results browser reads them."""
    todo = [""]
    for _ in range(RESULTS_MAX_DIRS):
        if not todo:
            return
        folder = todo.pop(0)
        # the screens ask for the root with no `path` (web/src/api.ts, query() drops "")
        query = f"?{urllib.parse.urlencode({'path': folder})}" if folder else ""
        answer = get(f"{path}/results{query}")
        if answer["status"] != 200:
            return
        for entry in json.loads(answer["body"])["entries"]:
            if entry["type"] == "dir":
                todo.append(f"{folder}/{entry['name']}".lstrip("/"))


def job_files(get: Get, task: Task) -> None:
    """Every attempt's files list, and the text of each present file (its last 64 KiB)."""
    for n in range(1, (task.get("attempt_n") or 0) + 1):
        base = f"/tasks/{urllib.parse.quote(task['id'])}/attempts/{n}/files"
        answer = get(base)
        if answer["status"] != 200:
            continue
        for file in json.loads(answer["body"])["files"]:
            if file["state"] == "present":
                parts = (urllib.parse.quote(part) for part in file["name"].split("/"))
                get(base + "/" + "/".join(parts))


def files_sample(runs: list[Task], tasks: dict[str, list[Task]]) -> list[Task]:
    """The tasks whose job files are recorded: in the newest Nextflow run, every failed run and
    every Snakemake run, the first task of each process, each failed task and the first retried
    task of each process. All of them would pass the budget (a Nextflow wrapper is ~10 kB)."""
    newest_nf = next((r["id"] for r in runs if r["workflow"]["engine"] == "nextflow"), None)
    picked: list[Task] = []
    for run in runs:
        snakemake = run["workflow"]["engine"] == "snakemake"
        if run["id"] != newest_nf and run["state"] != "failed" and not snakemake:
            continue
        first: set[str] = set()
        retried: set[str] = set()
        for task in tasks[run["id"]]:
            again = (task.get("attempt_n") or 0) > 1 and task["process"] not in retried
            if task["process"] not in first or task["state"] == "failed" or again:
                picked.append(task)
            first.add(task["process"])
            if again:
                retried.add(task["process"])
    return picked


def record(base: str, cookie: str | None = None) -> dict[str, Answer]:
    out, get = recorder(base, cookie)
    get("/version")
    get("/runs:summary?group_by=state")
    runs = whole_list(get, out, "/runs")
    tasks: dict[str, list[Task]] = {}
    for run in runs:
        path = "/runs/" + run["id"]
        for part in ("", "/processes", "/stages", ":launch-template"):
            get(path + part)
        tasks[run["id"]] = whole_list(get, out, path + "/tasks")
        for source in LOGS:  # the server serves the last 64 KiB of each, as the UI shows
            get(f"{path}/logs?{urllib.parse.urlencode({'source': source})}")
        results(get, path)
    for task in files_sample(runs, tasks):
        job_files(get, task)
    for location in PIPELINES:
        get("/workflows:inspect?" + urllib.parse.urlencode({"location": location}))
    return out


def neutral(text: str) -> str:
    """Nextflow's CmdRun banner without the recording host's kernel release (SEC-P3DEMO-02)."""
    return re.sub(r"\bSystem: Linux [^\s\"\\]+", "System: Linux", text)


def problems(text: str) -> list[str]:
    found = sanitize.leaks(text)
    host = socket.gethostname()
    if host != "login1" and re.search(rf"(?<![\w.-]){re.escape(host)}(?![\w-])", text):
        found.append(f"the recorder's host name {host!r}")
    if platform.release() in text:
        found.append(f"the recorder's kernel release {platform.release()!r}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:8766", help="the demo server")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    recorded = record(args.base.rstrip("/"), os.environ.get("SPECTIO_SESSION_COOKIE"))
    text = neutral(json.dumps(recorded, ensure_ascii=False, indent=1, sort_keys=True))
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
