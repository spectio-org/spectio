#!/usr/bin/env python3
"""Assemble the dashboard page: build.py OUTDIR

Reads template.html and extras.json from this folder, data.json, docs.json and imgs.json (gen.py)
from OUTDIR, and every per-session usage snapshot in .autopilot/usage/ (usage.py), merged.
Writes OUTDIR/spectio-board.html.
"""
import json, sys, datetime
from pathlib import Path
here = Path(__file__).parent
out = Path(sys.argv[1])
d = json.loads((out / "data.json").read_text())
d["now"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
x = json.loads((here / "extras.json").read_text())
html = (here / "template.html").read_text()
docs = json.loads((out / "docs.json").read_text())
imgs = json.loads((out / "imgs.json").read_text())
usage, seen = {"agents": [], "workflows": []}, set()
for f in sorted((here.parents[1] / ".autopilot" / "usage").glob("*.json")):
    u = json.loads(f.read_text())
    for k, key in (("agents", "id"), ("workflows", "runId")):
        for r in u[k]:
            if (k, r[key]) not in seen:
                seen.add((k, r[key])); usage[k].append(r)
usage = usage if usage["agents"] else None
j = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
html = html.replace("/*DATA*/null", j(d)).replace("/*EXTRAS*/null", j(x)).replace("/*DOCS*/null", j(docs)).replace("/*IMGS*/null", j(imgs)).replace("/*USAGE*/null", j(usage))
(out / "spectio-board.html").write_text(html)
print("ok", len(html))
