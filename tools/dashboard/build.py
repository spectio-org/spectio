#!/usr/bin/env python3
"""Assemble the dashboard page: build.py OUTDIR

Reads template.html from this folder, data.json, docs.json and imgs.json (gen.py)
from OUTDIR, and every per-session usage snapshot in .autopilot/usage/ (usage.py), merged.
Writes OUTDIR/spectio-board.html.
"""
import json, re, sys, datetime
from pathlib import Path
here = Path(__file__).parent
out = Path(sys.argv[1])
d = json.loads((out / "data.json").read_text())
d["now"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
html = (here / "template.html").read_text()
docs = json.loads((out / "docs.json").read_text())
imgs = json.loads((out / "imgs.json").read_text())
# rows are deduplicated by ID; on a duplicate the row with more calls, then the later end, wins
rank = {"agents": lambda r: (r["calls"], r.get("end") or ""), "workflows": lambda r: (r.get("totalToolCalls") or 0, r.get("timestamp") or "")}
rows = {"agents": {}, "workflows": {}}
for f in sorted((here.parents[1] / ".autopilot" / "usage").glob("*.json")):
    u = json.loads(f.read_text())
    for k, key in (("agents", "id"), ("workflows", "runId")):
        for r in u[k]:
            r.pop("summary", None)  # guard: snapshots from other branches may still carry the workflow's prompt summary
            old = rows[k].get(r[key])
            if old is None or rank[k](r) > rank[k](old):
                rows[k][r[key]] = r
usage = {k: list(v.values()) for k, v in rows.items()} if rows["agents"] else None
# every "<" escaped, so no embedded text can close the <script> element
j = lambda o: json.dumps(o, ensure_ascii=False).replace("<", "\\u003c")
subs = {"DATA": d, "DOCS": docs, "IMGS": imgs, "USAGE": usage}
html = re.sub(r"/\*(DATA|DOCS|IMGS|USAGE)\*/null", lambda m: j(subs[m.group(1)]), html)  # one pass: inserted data is never re-scanned
(out / "spectio-board.html").write_text(html)
print("ok", len(html))
