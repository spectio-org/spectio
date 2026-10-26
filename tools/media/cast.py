#!/usr/bin/env python3
"""Generate an asciinema v2 cast from a YAML script, running every command for real.

Why not `asciinema rec`: a hand-typed recording cannot be regenerated when the
CLI changes, and its timing is whatever the typist did. Here the commands run
for real (so the output is true), while typing speed and pauses are synthetic
(so the cast is the same length every time and diffs stay readable).

Script format (tools/media/casts/*.yaml):

    title: Stop at the QC gate, then resume
    cols: 100
    rows: 26
    idle_time_limit: 1.5        # written to the header; players cap pauses at it
    typing_delay: 0.035         # seconds per typed character
    line_delay: 0.03            # seconds between output lines
    prompt: "$ "
    workdir: tmp                # "tmp" = fresh temp dir, or a path relative to the repo
    env: {WF: "{repo}/tests/..."}   # {repo} and {workdir} are substituted, then $VARS expanded
    setup: ["cp ... ."]         # run first, not shown
    replace: {"/long/path": "~"}    # applied to every output line ({workdir} -> . by default)
    steps:
      - comment: "stop at the qc gate"          # typed as "# stop at the qc gate"
      - run: "snakemake -s $WF --until qc_report"
        keep: "steps \\(|Finished"              # regex: only lines that match
        drop: "^\\[.*2026\\]$"                  # regex: lines removed
        head: 3                                  # keep the first N lines ...
        tail: 4                                  # ... and/or the last N, with "…" between
        ellipsis: false                          # no "…" line where output was cut
        expect_exit: 0                           # fail the build if the command fails
      - pause: 1.2
      - clear: true

Output is filtered, never rewritten: every printed line was printed by the command.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sanitize  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def _subst(value: str, ctx: dict[str, str]) -> str:
    for k, v in ctx.items():
        value = value.replace("{" + k + "}", v)
    return value


def _filter(lines: list[str], step: dict) -> list[str]:
    if step.get("keep"):
        rx = re.compile(step["keep"])
        lines = [ln for ln in lines if rx.search(ln)]
    if step.get("drop"):
        rx = re.compile(step["drop"])
        lines = [ln for ln in lines if not rx.search(ln)]
    head, tail = step.get("head"), step.get("tail")
    if head is not None or tail is not None:
        h, t = head or 0, tail or 0
        if len(lines) > h + t:
            gap = ["…"] if step.get("ellipsis", True) else []
            lines = lines[:h] + gap + (lines[-t:] if t else [])
    return lines


class Cast:
    def __init__(self, cols: int, rows: int, title: str, idle: float) -> None:
        self.header = {"version": 2, "width": cols, "height": rows, "title": title,
                       "idle_time_limit": idle, "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"}}
        self.events: list[list] = []
        self.t = 0.0

    def out(self, text: str, delay: float = 0.0) -> None:
        self.t += delay
        self.events.append([round(self.t, 3), "o", text])

    def dump(self) -> str:
        return "\n".join([json.dumps(self.header)] + [json.dumps(e, ensure_ascii=False) for e in self.events]) + "\n"


GREEN, DIM, BOLD, RESET = "\x1b[32m", "\x1b[2m", "\x1b[1m", "\x1b[0m"


def build(script: Path, out: Path) -> None:
    spec = yaml.safe_load(script.read_text())
    tmp = None
    if spec.get("workdir", "tmp") == "tmp":
        tmp = tempfile.mkdtemp(prefix="spectio-cast-")
        workdir = Path(tmp)
    else:
        workdir = (REPO / spec["workdir"]).resolve()
    ctx = {"repo": str(REPO), "workdir": str(workdir)}
    env = {**os.environ, **{k: os.path.expandvars(_subst(str(v), ctx)) for k, v in (spec.get("env") or {}).items()}}
    replace = {str(workdir) + "/": "", str(workdir): ".", **(spec.get("replace") or {})}
    replace = {_subst(k, ctx): v for k, v in replace.items()}

    typing = float(spec.get("typing_delay", 0.035))
    line_delay = float(spec.get("line_delay", 0.03))
    prompt = spec.get("prompt", "$ ")
    cast = Cast(int(spec.get("cols", 100)), int(spec.get("rows", 26)), spec.get("title", script.stem),
                float(spec.get("idle_time_limit", 1.5)))

    def sh(cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", "-o", "pipefail", "-c", cmd], cwd=workdir, env=env, capture_output=True, text=True)

    try:
        for cmd in spec.get("setup") or []:
            p = sh(_subst(cmd, ctx))
            if p.returncode:
                sys.exit(f"setup failed: {cmd}\n{p.stderr}")

        cast.out(f"{GREEN}{prompt}{RESET}", 0.3)
        for step in spec["steps"]:
            if "pause" in step:
                cast.out("", float(step["pause"]))
                continue
            if step.get("clear"):
                cast.out("\x1b[2J\x1b[H", 0.2)
                cast.out(f"{GREEN}{prompt}{RESET}", 0.1)
                continue
            if "comment" in step:
                for ch in f"# {step['comment']}":
                    cast.out(f"{DIM}{ch}{RESET}", typing)
                cast.out("\r\n", 0.25)
                cast.out(f"{GREEN}{prompt}{RESET}", 0.05)
                continue
            cmd = step["run"]
            for ch in cmd:
                cast.out(ch, typing)
            cast.out("\r\n", 0.35)
            p = sh(_subst(cmd, ctx))
            want = step.get("expect_exit", 0)
            if want is not None and p.returncode != want:
                sys.exit(f"step exited {p.returncode}, expected {want}: {cmd}\n{p.stdout[-2000:]}{p.stderr[-2000:]}")
            text = p.stdout + p.stderr
            for a, b in replace.items():
                text = text.replace(a, b)
            for ln in _filter(text.splitlines(), step):
                cast.out(ln[: cast.header["width"]] + "\r\n", line_delay)
            cast.out(f"{GREEN}{prompt}{RESET}", float(step.get("after", 0.8)))
        cast.out("", 1.0)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    text = cast.dump()
    found = sanitize.leaks(text)
    if found:
        sys.exit(f"{script.stem}: forbidden term in the cast: {found}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(cast.dump(), encoding="utf-8")
    print(f"-> {out}  ({cast.t:.1f} s, {len(cast.events)} events, {out.stat().st_size // 1024} KB)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("script", type=Path, nargs="+", help="tools/media/casts/<name>.yaml")
    ap.add_argument("--out-dir", type=Path, default=REPO / "docs" / "assets" / "casts")
    a = ap.parse_args()
    for s in a.script:
        build(s, a.out_dir / f"{s.stem}.cast")


if __name__ == "__main__":
    main()
