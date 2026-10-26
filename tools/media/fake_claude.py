#!/usr/bin/env python3
"""Stand-in for `claude -p` used only by casts/budget-loop.yaml, inside a throwaway copy of the repo.

Marks the first ready step of .autopilot/state.json done, raises .autopilot/usage.json seven_day by
1.5 points (and refreshes "at"), and prints a stream-json assistant line and a result line.
Refuses to run inside the real Spectio checkout.
"""
import json
import os
import subprocess
import sys
import time

top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
real = os.environ.get("SPECTIO_REAL_REPO", "/home/claude/spectio")
if not top or os.path.realpath(top) in {os.path.realpath(real), "/home/claude/spectio"}:
    sys.exit("fake claude: refusing to run outside a throwaway copy of the repo")

ready = json.loads(subprocess.run([sys.executable, "tools/autopilot/ready.py", "--json"],
                                  capture_output=True, text=True).stdout or "{}")
batch = ready.get("batch") or []
state = json.load(open(".autopilot/state.json"))
step = batch[0]["id"] if batch else None
if step:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["steps"].setdefault(step, {}).update({"status": "done", "finished_at": now, "notes": "demo tick"})
    json.dump(state, open(".autopilot/state.json", "w"), indent=2)

usage = json.load(open(".autopilot/usage.json"))
usage["seven_day"]["used_percentage"] = round(usage["seven_day"]["used_percentage"] + 1.5, 1)
usage["at"] = time.time()
json.dump(usage, open(".autopilot/usage.json", "w"))

print(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "text", "text": f"step {step}: done, exit check passed"}]}}))
print(json.dumps({"type": "result", "subtype": "success", "total_cost_usd": 3.0, "num_turns": 4}))
