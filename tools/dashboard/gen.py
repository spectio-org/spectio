#!/usr/bin/env python3
"""Build tracker data (JSON) from the Spectio repo: pipeline.yaml, state.json, inbox, reviews."""
import json, re, sys, os, subprocess
from pathlib import Path
import yaml

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
os.chdir(ROOT)

pipe = yaml.safe_load(open("docs/playbooks/pipeline.yaml"))
state = json.load(open(".autopilot/state.json"))["steps"]

def slug(h):
    s = h.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")

# step titles from next-phase.md headings "### R1 · Title"
titles, anchors = {}, {}
for line in open("docs/playbooks/next-phase.md"):
    m = re.match(r"### (\w+) · (.+)", line.rstrip())
    if m:
        titles[m.group(1)] = m.group(2).replace(" ∥", "")
        anchors[m.group(1)] = slug(line[4:].rstrip())
titles.update({
    "F1": "Specs, agents and skills", "F2": "Synthetic test pipelines",
    "F3": "Real pipeline corpus and CI", "F4": "Authentication spec",
    "F5": "Documentation system and tools", "F6": "Telemetry spec",
    "F7": "Autopilot budget and status line",
    "TRIAGE1": "Triage W1 findings", "APPLY1": "Apply W1 findings to the specs",
    "TRIAGE2": "Triage R3 and R6", "APPLY2": "Apply R3 and R6",
    "TRIAGE3": "Triage spike findings", "APPLY3": "Apply spike findings",
    "GO": "Go / no-go for implementation",
})

waves, steps = [], []
for w in pipe["waves"]:
    waves.append({"id": w["id"], "title": w["title"], "depends_on": w.get("depends_on", [])})
    for s in w["steps"]:
        sid = s["id"]
        st = state.get(sid, {})
        deps = list(s.get("depends_on", []))
        outs = [o for o in st.get("outputs", []) if o.endswith(".md") and "*" not in o]
        prog = f"docs/progress/{w['id']}/{sid}.md"
        steps.append({
            "id": sid, "wave": w["id"], "kind": s["kind"], "title": titles.get(sid, sid),
            "status": st.get("status", "pending"), "start": st.get("started_at"),
            "end": st.get("finished_at"), "notes": st.get("notes", ""),
            "deps": deps, "outputs": outs,
            "progress": prog if Path(prog).exists() else None,
            "prompt": anchors.get(s.get("prompt_ref", "")),
            "worktree": bool(s.get("worktree")), "question": s.get("question"),
            "writes": s.get("writes", []), "rounds": s.get("rounds", []),
        })

# ready / blocked: wave deps + step deps
done = {s["id"] for s in steps if s["status"] == "done"}
wave_done = {w["id"]: all(s["status"] == "done" for s in steps if s["wave"] == w["id"]) for w in waves}
for s in steps:
    if s["status"] != "pending":
        continue
    w = next(x for x in waves if x["id"] == s["wave"])
    ok = all(wave_done[d] for d in w["depends_on"]) and all(d in done for d in s["deps"])
    s["status"] = "ready" if ok else "pending"
    if s["kind"] == "human_gate" and ok:
        s["status"] = "thomas"

# inbox
inbox = []
txt = open("docs/reviews/inbox.md").read()
for part in re.split(r"\n### ", txt)[1:]:
    head = part.split("\n")[0]
    m = re.match(r"#(\d+) · (.+)", head)
    if not m:
        continue
    n, t = int(m.group(1)), m.group(2)
    answers = list(re.finditer(r"\*\*(?:Answer|Reading) \(Thomas[^)]*\):\*\*\s*(.+)", part))
    ans = answers[-1] if answers else None
    if ans:
        # the entry's state is the italic marker ending its last answer: *Handled.*, *Decided.*, *Open (...)*, *Deferred.*, *Partly handled.*
        mk = re.findall(r"\*([^*]+)\*\s*$", ans.group(1).strip())
        mk = mk[-1].strip().lower() if mk else ""
        if mk.startswith("open"):
            status = "open"
        elif mk.startswith("deferred"):
            status = "deferred"
        elif "partly" in mk or "open" in mk:
            status = "partial"
        else:
            status = "answered"
    elif t.lower().startswith("assumed"):
        status = "assumed"
    else:
        status = "open"
    blocked = re.search(r"\*\*Blocked:\*\*\s*(.+)", part)
    rec = re.search(r"\*\*Recommendation:\*\*\s*(.+)", part)
    covers = len(re.findall(r"\]\(\.\./reviews/R", part.split("\n- **", 2)[1] if "**Covers:**" in part else ""))
    inbox.append({
        "n": n, "title": t, "status": status, "anchor": slug(head),
        "answer": (ans.group(1)[:420] if ans else None),
        "blocked": blocked.group(1)[:200] if blocked else None,
        "rec": rec.group(1)[:300] if rec else None,
        "batch": "TRIAGE1" if n >= 11 else "early",
        "covers": covers,
        "not001": bool(re.search(r"[Nn]ot needed for 0\.0\.1", part)),
    })

# findings per round
rounds = []
for f in sorted(Path("docs/reviews").glob("R[0-9]*.md"), key=lambda p: (int(re.match(r"R(\d+)", p.stem).group(1)), p.stem)):
    t = f.read_text()
    st = re.findall(r"\*\*Status:\*\* ([a-z][a-z ,]*)", t)
    sev = re.findall(r"^### [A-Z0-9-]+ \[?(blocker|major|minor)", t, re.M | re.I)
    c = {}
    for x in st:
        x = x.strip().rstrip(",")
        k = "assumed" if "assumed" in x else x.split(",")[0].split()[0]
        if k == "triaged":  # round-level header line, not a finding
            continue
        c[k] = c.get(k, 0) + 1
    rid = f.stem.split("-")[0]
    rounds.append({"id": rid, "file": str(f), "counts": c, "total": sum(c.values())})

# git
def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()
head = git("rev-parse", "--short", "HEAD")
branch = git("rev-parse", "--abbrev-ref", "HEAD")
mainlog = git("log", "--first-parent", "--format=%h|%cI|%s", "origin/main", "-15").splitlines()

data = {
    "generated": git("log", "-1", "--format=%cI"),
    "head": head, "branch": branch,
    "repo": "https://github.com/weber8thomas/spectio",
    "waves": waves, "steps": steps, "inbox": inbox, "rounds": rounds,
    "main": [dict(zip(["sha", "date", "msg"], l.split("|", 2))) for l in mainlog],
}
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1))

# markdown sources, embedded so the page can preview them without leaving it
docs = {}
for p in git("ls-files", "*.md").splitlines():
    if p.startswith(".claude/skills/") or p.startswith("spikes/"):
        continue
    docs[p] = Path(p).read_text(errors="replace")
(OUT.parent / "docs.json").write_text(json.dumps(docs, ensure_ascii=False))
print(f"{len(docs)} md files embedded")

# local media referenced by those files, as data URIs (light and dark variants, HTML <img>/<video> too)
import base64, posixpath
MIME = {".png": "image/png", ".webp": "image/webp", ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".mp4": "video/mp4", ".webm": "video/webm"}
def bases(p):
    # markdown images resolve against the file's folder; raw HTML against the MkDocs page URL (docs/a/b.md -> /a/b/)
    d = posixpath.dirname(p)
    page = d if posixpath.basename(p) == "index.md" else posixpath.join(d, posixpath.splitext(posixpath.basename(p))[0])
    return [d, page]
imgs, figs = {}, {}
for p, txt in docs.items():
    srcs = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", txt) + re.findall(r"<(?:img|video|source)\b[^>]*?\s(?:src|poster)=\"([^\"]+)\"", txt)
    srcs += re.findall(r"<video\b[^>]*?\sposter=\"([^\"]+)\"", txt)
    for src in srcs:
        if re.match(r"(https?|data):", src):
            continue
        for b in bases(p):
            full = posixpath.normpath(posixpath.join(b, src.split("#")[0]))
            f = Path(full)
            if f.is_file() and f.suffix.lower() in MIME:
                if full not in imgs:
                    imgs[full] = f"data:{MIME[f.suffix.lower()]};base64," + base64.b64encode(f.read_bytes()).decode()
                figs.setdefault(p, [])
                if full not in figs[p]:
                    figs[p].append(full)
                break
(OUT.parent / "imgs.json").write_text(json.dumps(imgs))
data["figs"] = figs
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1))
print(f"{len(imgs)} media embedded, {sum(map(len, imgs.values()))//1024} KB, {len(figs)} docs with figures")
print(f"{len(steps)} steps, {len(inbox)} inbox, {len(rounds)} rounds -> {OUT}")
