#!/usr/bin/env python3
"""Spike T2: summarise Tower captures (what LOG.md and the note quote). usage: FILE..."""
import collections, json, re, sys

for f in sys.argv[1:]:
    L = [json.loads(l) for l in open(f)]
    route = lambda r: re.sub(r"/trace/[^/]+/", "/trace/{id}/", r["path"].split("?")[0])
    print("#####", f.split("/")[-1])
    print(" sequence:", [(r["method"], route(r)) for r in L][:6], "... last:", [(r["method"], route(r)) for r in L][-2:])
    print(" counts:", dict(collections.Counter((r["method"], route(r)) for r in L)))
    print(" agent:", {r["agent"] for r in L}, "auth header on all:", all(r["auth"] for r in L))
    for r in L:
        b = r["body"] or {}
        if route(r) == "/trace/create":
            print(" create body:", b, "-> reply", r["reply"])
            print(" create query:", r["path"])
        elif route(r) == "/trace/{id}/begin":
            print(" begin keys:", sorted(b))
            w = b.get("workflow", {})
            print(" begin.workflow keys:", sorted(w))
            print(" ids: runName", w.get("runName"), "sessionId", w.get("sessionId"), "resume", w.get("resume"))
            print(" processNames:", b.get("processNames"))
            print(" dag present:", "dag" in b and b["dag"] is not None, "towerLaunch:", b.get("towerLaunch"))
        elif route(r) == "/trace/{id}/complete":
            print(" complete keys:", sorted(b), "workflow.success:", b.get("workflow", {}).get("success"),
                  "errorMessage:", (b.get("workflow", {}).get("errorMessage") or "")[:80])
            print(" complete progress:", {k: v for k, v in (b.get("progress") or {}).items() if not isinstance(v, (list, dict))})
    tasks = [t for r in L if route(r) == "/trace/{id}/progress" for t in (r["body"] or {}).get("tasks") or []]
    if tasks:
        print(" task keys:", sorted(tasks[0]))
        print(" task statuses:", dict(collections.Counter(t["status"] for t in tasks)))
        last = {}
        for t in tasks:
            last[t["taskId"]] = t
        print(" distinct taskIds:", len(last), "final statuses:", dict(collections.Counter(t["status"] for t in last.values())))
        odd = [(t["process"], t.get("tag"), t["status"], t.get("exit"), t.get("attempt"), t.get("errorAction"))
               for t in last.values() if t.get("attempt", 1) > 1 or t["status"] in ("FAILED", "ABORTED")]
        print(" failed/retried tasks:", odd)
        print(" cached?", sum(1 for t in last.values() if t["status"] == "CACHED"))
    pk = [sorted((r["body"] or {}).keys()) for r in L if route(r) == "/trace/{id}/progress"][:1]
    print(" progress body keys:", pk)
    prog = [(r["body"] or {}).get("progress") for r in L if route(r) == "/trace/{id}/progress"]
    if prog and prog[-1]:
        print(" progress keys:", sorted(prog[-1]))
