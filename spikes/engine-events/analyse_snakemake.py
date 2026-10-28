#!/usr/bin/env python3
"""Spike T2: summarise Snakemake logger fixtures (what LOG.md and the note quote). usage: FILE..."""
import collections, json, sys

for f in sys.argv[1:]:
    L = [json.loads(l) for l in open(f)]
    ev = lambda name: [l for l in L if l["event"] == name]
    print("#####", f.split("/")[-1], dict(collections.Counter(l["event"] for l in L)))
    print(" untyped (event None) messages:",
          collections.Counter(l["msg"].split("\n")[0][:50] for l in ev("None")).most_common(12))
    print(" progress totals seen:", [l["extra"]["total"] for l in ev("progress")][:1],
          "->", sorted({l["extra"]["total"] for l in ev("progress")}))
    print(" run_info stats total:", [l["extra"]["stats"].get("total") for l in ev("run_info")])
    cp = [(l["extra"]["jobid"], l["extra"]["rule_name"]) for l in ev("job_info") if l["extra"].get("is_checkpoint")]
    print(" checkpoint job_info:", len(cp), cp[:2])
    if ev("job_info"):
        print(" job_info keys:", sorted(ev("job_info")[0]["extra"]))
        print(" job_info resources example:", ev("job_info")[0]["extra"]["resources"])
    for e in ev("job_error")[:1]:
        print(" job_error keys:", sorted(e["extra"]))
    for e in ev("workflow_started"):
        print(" workflow_started keys:", sorted(e["extra"]), "workflow_id:", e["extra"].get("workflow_id"))
    ji = collections.Counter(l["extra"]["jobid"] for l in ev("job_info"))
    again = {j: c for j, c in ji.items() if c > 1}
    print(" jobids with >1 job_info (retries):", again)
    for j in again:
        seq = [(l["event"], l["msg"][:40]) for l in L
               if l["extra"].get("jobid") == j or l["extra"].get("job_id") == j
               or j in (l["extra"].get("jobs") or []) or f"job {j}." in (l["msg"] or "")]
        print("  job", j, "sequence:", seq)
    print(" job_finished count:", len(ev("job_finished")), "job_info count:", len(ev("job_info")))
    # which job_info carry no output (dynamic?), and align count
    print(" align job_info:", sum(1 for l in ev("job_info") if l["extra"]["rule_name"] == "align"))
    errs = [l["msg"][:120] for l in ev("error")]
    print(" error events:", errs)
