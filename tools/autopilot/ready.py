#!/usr/bin/env python3
"""Compute the autopilot's next batch from docs/playbooks/pipeline.yaml and .autopilot/state.json.

Usage:
  python3 tools/autopilot/ready.py [--until STEP_OR_WAVE] [--only ID,ID] [--max-parallel N] [--json]

Prints the AUTOPILOT status line and the ready batch. Exit code 0 when something is ready,
3 when nothing is ready (done, waiting on a human, or blocked). Deterministic, so the
orchestrator never has to work out dependencies by reasoning.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SINGLE_WRITER = {"apply", "triage"}


def load():
    pipeline = yaml.safe_load((ROOT / "docs/playbooks/pipeline.yaml").read_text())
    state = json.loads((ROOT / ".autopilot/state.json").read_text())
    return pipeline, state


def ordered_steps(pipeline):
    for wave in pipeline["waves"]:
        for step in wave["steps"]:
            yield wave, step


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--until")
    ap.add_argument("--only")
    ap.add_argument("--max-parallel", type=int)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    pipeline, state = load()
    st = state["steps"]
    defaults = pipeline.get("defaults", {})
    retries = defaults.get("retries", 2)
    max_parallel = args.max_parallel or defaults.get("max_parallel", 6)
    only = set(args.only.split(",")) if args.only else None

    waves = {w["id"]: w for w in pipeline["waves"]}
    wave_done = {wid: all(st[s["id"]]["status"] in ("done", "skipped") for s in w["steps"]) for wid, w in waves.items()}

    # Scope for --until: everything up to and including the named step or wave.
    in_scope = set()
    for wave, step in ordered_steps(pipeline):
        in_scope.add(step["id"])
        if args.until in (step["id"], wave["id"]) and args.until == step["id"]:
            break
        if args.until == wave["id"] and step is wave["steps"][-1]:
            break

    ready, gates = [], []
    for wave, step in ordered_steps(pipeline):
        sid = step["id"]
        s = st[sid]
        if only and sid not in only:
            continue
        if args.until and sid not in in_scope:
            continue
        status_ok = s["status"] == "pending" or (s["status"] == "failed" and s["attempts"] < retries)
        if not status_ok:
            continue
        if not all(wave_done.get(w, False) for w in wave.get("depends_on", [])):
            continue
        if not all(st[d]["status"] in ("done", "skipped") for d in step.get("depends_on", [])):
            continue
        if step["kind"] == "human_gate":
            gates.append(sid)
            continue
        ready.append({"id": sid, "wave": wave["id"], "kind": step["kind"], "worktree": bool(step.get("worktree")),
                      "prompt_ref": step.get("prompt_ref"), "rounds": step.get("rounds"), "writes": step.get("writes", [])})

    # Build the batch: at most one single-writer step, and never alongside other spec writers.
    batch, writer_taken = [], False
    for r in ready:
        if len(batch) >= max_parallel:
            break
        if r["kind"] in SINGLE_WRITER:
            if writer_taken or batch:
                continue
            batch.append(r)
            writer_taken = True
            break
        if writer_taken:
            break
        batch.append(r)

    counts = {k: 0 for k in ("done", "running", "failed", "blocked", "waiting_human", "pending", "skipped")}
    for s in st.values():
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    total = len(st)
    current = next((w["id"] for w in pipeline["waves"] if not wave_done[w["id"]]), "complete")
    waiting = [k for k, v in st.items() if v["status"] == "waiting_human"] + gates
    line = (f"AUTOPILOT  wave={current}  done={counts['done']}/{total}  running={counts['running']}  "
            f"failed={counts['failed']}  blocked={counts['blocked']}  waiting_human={len(set(waiting))}")
    nxt = ", ".join(b["id"] for b in batch) or "none"
    budget_file = pathlib.Path(".autopilot/budget.json")
    if budget_file.exists():  # governor status, see tools/autopilot/budget.py
        sys.path.insert(0, str(pathlib.Path(__file__).parent))
        import budget
        line += "  " + budget.status_line(budget.load(budget.BUDGET, None))

    if args.json:
        print(json.dumps({"status_line": line, "batch": batch, "human_gates_reached": gates,
                          "waiting_human": sorted(set(waiting))}, indent=2))
    else:
        print(line)
        print(f"next ready: {nxt}" + (f"        human gate reached: {', '.join(gates)}" if gates else ""))
    return 0 if batch else 3


if __name__ == "__main__":
    sys.exit(main())
