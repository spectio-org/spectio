#!/usr/bin/env python3
"""Build tracker data (JSON) from the Spectio repo: pipeline.yaml, state.json, inbox, reviews."""
import json, re, sys, os, subprocess
from pathlib import Path
import yaml

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()  # before chdir, so a relative OUT means the caller's folder
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
# steps next-phase.md has no heading for (W0, triage, apply, GO): hand-kept in extras.json
for k, v in json.loads((Path(__file__).parent / "extras.json").read_text())["stepTitles"].items():
    titles.setdefault(k, v)

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

# ready: tools/autopilot/ready.py owns the rule; ask it about each step that could be ready
for s in steps:
    if s["status"] not in ("pending", "failed"):
        continue
    r = subprocess.run([sys.executable, "tools/autopilot/ready.py", "--only", s["id"], "--json"], capture_output=True, text=True)
    if r.returncode not in (0, 3):  # 3: nothing ready
        sys.exit(f"ready.py failed for {s['id']}: {r.stderr.strip()}")
    j = json.loads(r.stdout)
    if s["id"] in j["human_gates_reached"]:
        s["status"] = "thomas"
    elif j["batch"]:
        s["status"] = "ready"

# inbox
inbox = []
txt = open("docs/reviews/inbox.md").read()
parts, batch = re.split(r"\n### ", txt), "before W1"
for prev, part in zip(parts, parts[1:]):
    # the batch is the last "## <NAME> (date)" heading above the entry, e.g. "## TRIAGE1 (2026-10-27)"
    batch = ([batch] + re.findall(r"^## (\S+) \(", prev, re.M))[-1]
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
    cov = re.search(r"^- \*\*Covers:\*\*(.*)$", part, re.M)
    covers = len(re.findall(r"\]\(\.\./reviews/R", cov.group(1))) if cov else 0
    inbox.append({
        "n": n, "title": t, "status": status, "anchor": slug(head),
        "answer": (ans.group(1)[:420] if ans else None),
        "blocked": blocked.group(1)[:200] if blocked else None,
        "rec": rec.group(1)[:300] if rec else None,
        "batch": batch, "covers": covers,
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
    h1 = re.search(r"^# +(.+)$", t, re.M)
    title = re.sub(r"^\S+ · ", "", h1.group(1)) if h1 else f.name  # "# R1 · Consistency across specs"
    rounds.append({"id": rid, "file": str(f), "title": title, "counts": c, "total": sum(c.values())})

# git
def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout.strip()
head = git("rev-parse", "--short", "HEAD")
branch = git("rev-parse", "--abbrev-ref", "HEAD")
mainlog = git("log", "--first-parent", "--format=%h|%cI|%s", "origin/main", "-15").splitlines()

data = {
    "head": head, "branch": branch,
    "repo": "https://github.com/weber8thomas/spectio",
    "waves": waves, "steps": steps, "inbox": inbox, "rounds": rounds,
    "main": [dict(zip(["sha", "date", "msg"], l.split("|", 2))) for l in mainlog],
}

def inside(p):  # a regular file, not a symlink, and inside ROOT once resolved
    f = Path(p)
    return f.is_file() and not f.is_symlink() and f.resolve().is_relative_to(ROOT)

# markdown sources, embedded so the page can preview them without leaving it
docs = {}
for p in git("ls-files", "*.md").splitlines():
    if p.startswith(".claude/skills/") or p.startswith("spikes/") or not inside(p):
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
tracked = set(git("ls-files").splitlines())  # embed only media committed to the repository
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
            if full in tracked and inside(full) and f.suffix.lower() in MIME:
                if full not in imgs:
                    # a sketch.py figure ships an SVG next to its PNG, about half the size: embed that (16 MB page limit);
                    # inside <img> the SVG cannot load the Virgil font and falls back to cursive or serif, a deliberate trade-off
                    svg = f.with_suffix(".svg")
                    if f.suffix.lower() == ".png" and svg.as_posix() in tracked:
                        f = svg
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
