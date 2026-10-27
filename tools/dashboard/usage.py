"""Token and agent usage of the Claude Code sessions of one project, from their transcripts.

usage.py <~/.claude/projects/<slug>> <out.json>
Each cloud session has its own container, so a session snapshots its own numbers before it ends:
usage.py ~/.claude/projects/<slug> .autopilot/usage/<session-id>.json, committed. build.py merges them all.
Each API response is counted once (deduplicated by message id). Tokens: input (uncached),
cache_write, cache_read, output.
"""
import json, pathlib, sys, collections

KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
NAMES = ("input", "cache_write", "cache_read", "output")

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

def main(root, out):
    root = pathlib.Path(root); rows, wfs = [], []
    for main_t in sorted(root.glob("*.jsonl")):
        r = scan(main_t); r.update(id=main_t.stem, kind="main", type="session", label="main session " + main_t.stem[:8]); rows.append(r)
        sdir = root / main_t.stem
        for wf in sorted((sdir / "workflows").glob("wf_*.json")):
            w = json.loads(wf.read_text())
            wfs.append({k: w.get(k) for k in ("runId", "workflowName", "summary", "agentCount", "totalTokens", "totalToolCalls", "durationMs", "status", "timestamp")})
        names = {w["runId"]: w["workflowName"] for w in wfs}
        for t in sorted((sdir / "subagents").rglob("agent-*.jsonl")):
            meta = t.with_name(t.name.replace(".jsonl", ".meta.json"))
            meta = json.loads(meta.read_text()) if meta.exists() else {}
            r = scan(t)
            if not r["calls"]: continue
            wf = t.parent.name if t.parent.parent.name == "workflows" else None
            r.update(id=t.stem.removeprefix("agent-"), kind="workflow" if wf else "subagent",
                     type=meta.get("agentType", "general-purpose"), label=meta.get("description") or (names.get(wf, wf) if wf else ""),
                     workflow=names.get(wf, wf) if wf else None)
            rows.append(r)
    json.dump({"agents": rows, "workflows": wfs}, open(out, "w"), indent=1)
    tot = collections.Counter()
    for r in rows: tot.update(r["tokens"])
    print(f"{len(rows)-1} agents ({sum(r['kind']=='subagent' for r in rows)} subagents, {sum(r['kind']=='workflow' for r in rows)} in {len(wfs)} workflows), {sum(r['calls'] for r in rows)} API calls, tokens {dict(tot)}")

if __name__ == "__main__":
    main(*sys.argv[1:3])
