"""Token and agent usage of the current Claude Code session, from its transcripts.

usage.py <outdir>     e.g. usage.py .autopilot/usage
The current session's top-level transcript under ~/.claude/projects/ is the one named after
$CLAUDE_CODE_SESSION_ID when that is set, otherwise the one whose records carry the repository root
(git rev-parse --show-toplevel) as "cwd"; with none or several, the script fails. Its numbers, with
its subagents and workflows, go to <outdir>/<transcript stem>.json. Each cloud session has its own
container, so a session snapshots itself before it ends and commits the file; build.py merges them all.
Each API response is counted once (deduplicated by message id). Tokens: input (uncached),
cache_write, cache_read, output.
"""
import json, os, pathlib, subprocess, sys, collections

KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
NAMES = ("input", "cache_write", "cache_read", "output")
LABEL = 80  # labels are task descriptions: keep them short

def scan(path):
    seen, tok, model, first, last, calls = set(), dict.fromkeys(NAMES, 0), collections.Counter(), None, None, 0
    for line in path.open():
        try: d = json.loads(line)
        except ValueError: continue
        ts = d.get("timestamp")
        if ts: first = first or ts; last = ts
        m = d.get("message")
        if not isinstance(m, dict) or not m.get("usage"): continue
        mid = m.get("id") or d.get("requestId") or d.get("uuid")
        if mid in seen: continue
        seen.add(mid); calls += 1
        for k, n in zip(KEYS, NAMES): tok[n] += m["usage"].get(k) or 0
        model[m.get("model", "?")] += 1
    return {"tokens": tok, "calls": calls, "model": model.most_common(1)[0][0] if model else None, "start": first, "end": last}

def first_cwd(path):
    with path.open() as f:
        for line in f:
            try: cwd = json.loads(line).get("cwd")
            except (ValueError, AttributeError): continue
            if cwd: return cwd

def transcript():
    projects = pathlib.Path.home() / ".claude" / "projects"
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if sid:
        found, how = list(projects.glob(f"*/{sid}.jsonl")), f"named {sid}.jsonl"
    else:
        root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
        found, how = [t for t in projects.glob("*/*.jsonl") if first_cwd(t) == root], f"started in {root}"
    if len(found) != 1:
        sys.exit(f"usage.py: {len(found)} transcripts {how} under {projects}, expected one; set CLAUDE_CODE_SESSION_ID")
    return found[0]

def main(outdir):
    main_t = transcript()
    rows, wfs = [], []
    r = scan(main_t); r.update(id=main_t.stem, kind="main", type="session", label="main session " + main_t.stem[:8]); rows.append(r)
    sdir = main_t.with_suffix("")
    for wf in sorted((sdir / "workflows").glob("wf_*.json")):
        w = json.loads(wf.read_text())
        wfs.append({k: w.get(k) for k in ("runId", "workflowName", "agentCount", "totalTokens", "totalToolCalls", "durationMs", "status", "timestamp")})
    names = {w["runId"]: w["workflowName"] for w in wfs}
    for t in sorted((sdir / "subagents").rglob("agent-*.jsonl")):
        meta = t.with_name(t.name.replace(".jsonl", ".meta.json"))
        meta = json.loads(meta.read_text()) if meta.exists() else {}
        r = scan(t)
        if not r["calls"]: continue
        wf = t.parent.name if t.parent.parent.name == "workflows" else None
        r.update(id=t.stem.removeprefix("agent-"), kind="workflow" if wf else "subagent",
                 type=meta.get("agentType", "general-purpose"), label=(meta.get("description") or (names.get(wf, wf) if wf else ""))[:LABEL],
                 workflow=names.get(wf, wf) if wf else None)
        rows.append(r)
    out = pathlib.Path(outdir) / (main_t.stem + ".json")
    json.dump({"agents": rows, "workflows": wfs}, open(out, "w"), indent=1)
    tot = collections.Counter()
    for r in rows: tot.update(r["tokens"])
    print(f"{out}: {len(rows)-1} agents ({sum(r['kind']=='subagent' for r in rows)} subagents, {sum(r['kind']=='workflow' for r in rows)} in {len(wfs)} workflows), {sum(r['calls'] for r in rows)} API calls, tokens {dict(tot)}")

if __name__ == "__main__":
    main(sys.argv[1])
