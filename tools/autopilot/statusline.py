#!/usr/bin/env python3
"""Claude Code status line that also records plan usage for the autopilot budget governor.

Claude Code pipes a JSON object to the status-line command after each assistant message
(https://code.claude.com/docs/en/statusline.md). For Pro and Max subscribers it carries
rate_limits.five_hour / seven_day with used_percentage and resets_at, and cost.total_cost_usd.
This script writes those fields to .autopilot/usage.json (atomically) and prints a short line.

Install (in your own settings; agents cannot change their settings):
  "statusLine": {"type": "command", "command": "python3 tools/autopilot/statusline.py", "refreshInterval": 60}
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import time


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("spectio")
        return
    root = pathlib.Path(data.get("workspace", {}).get("project_dir") or os.getcwd())
    out = root / ".autopilot" / "usage.json"
    limits = data.get("rate_limits") or {}
    record = {
        "at": time.time(),
        "session_id": data.get("session_id"),
        "cost_usd": (data.get("cost") or {}).get("total_cost_usd"),
        "five_hour": limits.get("five_hour"),
        "seven_day": limits.get("seven_day"),
    }
    if out.parent.is_dir():
        fd, tmp = tempfile.mkstemp(dir=out.parent, prefix=".usage.")
        with os.fdopen(fd, "w") as fh:
            json.dump(record, fh)
        os.replace(tmp, out)

    def pct(w):
        return f"{w['used_percentage']:.0f}%" if isinstance(w, dict) and "used_percentage" in w else "?"

    model = (data.get("model") or {}).get("display_name", "")
    print(f"{model}  5h {pct(record['five_hour'])}  7d {pct(record['seven_day'])}")


if __name__ == "__main__":
    main()
