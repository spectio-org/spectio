#!/usr/bin/env python3
"""Re-check the T2 facts that TRIAGE3 accepts, from the committed fixtures on origin/spike/engine-events.

Usage (from the repository root): python3 -I <this file> <check>   (or "all")
Reads the fixtures with `git show`, so nothing is checked out. Prints one block per check.
"""
import collections
import json
import subprocess
import sys

REF = "origin/spike/engine-events"
FX = "spikes/engine-events/fixtures/"


def load(name):
    out = subprocess.run(["git", "show", f"{REF}:{FX}{name}.jsonl"], capture_output=True, text=True, check=True).stdout
    return [json.loads(line) for line in out.splitlines() if line.strip()]


PLUGIN = [f"nextflow-{v}_plugin_{r}" for v in ("26.10.4", "25.10.9") for r in ("flaky", "toolerr", "resume")]
TOWER = [f"nextflow-{v}_tower_{r}" for v in ("26.10.4", "25.10.9") for r in ("flaky", "toolerr", "resume")]


def after_terminate():  # row 1
    for f in PLUGIN:
        terminated, late = set(), collections.Counter()
        for rec in load(f):
            b = rec["body"]
            if b["hook"] == "onProcessTerminate":
                terminated.add(b["process"])
            elif b["hook"].startswith("onTask") and b.get("process") in terminated:
                late[(b["process"], b["hook"])] += 1
        print(f, "task events after their process's onProcessTerminate:", dict(late))


def downstream_terminate():  # row 2
    for f in [p for p in PLUGIN if "toolerr" in p]:
        created, term = [], []
        for rec in load(f):
            b = rec["body"]
            if b["hook"] == "onProcessCreate":
                created.append(b["process"])
            if b["hook"] == "onProcessTerminate":
                term.append(b["process"])
        print(f, "created", len(created), "terminated", len(term), "never terminated:", sorted(set(created) - set(term)))


def outputs():  # row 3
    for f in ("nextflow-26.10.4_plugin_flaky", "nextflow-25.10.9_plugin_flaky", "nextflow-26.10.4_plugin_resume"):
        shown = 0
        for rec in load(f):
            b = rec["body"]
            if b["hook"] in ("onTaskComplete", "onTaskCached") and b.get("outputs") and b.get("process") == "SPLIT":
                print(f, b["hook"], b["name"], {k: (v["name"], v["type"], v["value"]) for k, v in b["outputs"].items()})
                shown += 1
                if shown == 1:
                    break


def flow_end():  # rows 5, 6, 27
    for f in PLUGIN:
        seq = [(r["body"]["hook"], r["body"].get("success"), r["body"].get("errorMessage")) for r in load(f)
               if r["body"]["hook"] in ("onFlowComplete", "onFlowError")]
        print(f, seq)
    for f in TOWER:
        print(f, "PUT complete:", sum(1 for r in load(f) if r["path"].endswith("/complete")))


def failed_status():  # rows 7, 9
    for f in PLUGIN:
        for rec in load(f):
            b = rec["body"]
            tr = b.get("trace") or {}
            if b["hook"] == "onTaskComplete" and tr.get("status") != "COMPLETED":
                print(f, b["name"], "handler.status=", b.get("status"), "trace.status=", tr.get("status"),
                      "exit=", b.get("exitStatus"), "errorAction=", b.get("errorAction"))


def resume():  # row 8
    for f in [p for p in PLUGIN if "resume" in p]:
        c = collections.Counter(r["body"]["hook"] for r in load(f))
        print(f, dict(c))


def pending_only():  # row 9
    for f in [p for p in PLUGIN if "toolerr" in p]:
        hooks = collections.defaultdict(list)
        for rec in load(f):
            b = rec["body"]
            if b["hook"].startswith("onTask"):
                hooks[b["taskId"]].append(b["hook"])
        print(f, "tasks with onTaskPending and nothing after:",
              sum(1 for h in hooks.values() if h == ["onTaskPending"]))
    for f in [t for t in TOWER if "toolerr" in t]:
        last = {}
        for rec in load(f):
            for t in rec["body"].get("tasks") or []:
                last[(t["process"], t.get("tag"))] = t["status"]
        print(f, "last Tower status not COMPLETED:", {k: v for k, v in last.items() if v != "COMPLETED"})


def tower_begin_and_tasks():  # rows 10, 11
    for f in TOWER:
        recs = load(f)
        begin = next(r["body"] for r in recs if r["path"].endswith("/begin"))
        keys = set()
        for r in recs:
            for t in r["body"].get("tasks") or []:
                keys |= set(t)
        print(f, "begin has dag:", "dag" in begin, "| task keys include script, env:", {"script", "env"} <= keys)


def smk():  # rows 15-19, 23
    recs = load("snakemake-9.27.1_checkpoint_flaky_retry")
    c = collections.Counter(r.get("event") for r in recs)
    print("event counts:", dict(c))
    je = [r for r in recs if r.get("event") == "job_error"]
    print("job_error keys:", sorted(je[0]["extra"]), "| has exit code key:",
          any(k in je[0]["extra"] for k in ("exitcode", "exit_code", "returncode")))
    print("job_error per jobid:", collections.Counter(r["extra"]["jobid"] for r in je))
    print("error texts with an exit status:", [r["msg"][-45:] for r in recs if r.get("event") == "error"])
    msgs = collections.Counter(r["msg"] for r in recs if r.get("event") in (None, "None"))
    print("restart messages:", {m: n for m, n in msgs.items() if m.startswith("Trying to restart")})
    print("checkpoint messages:", {m: n for m, n in msgs.items() if "checkpoint" in m or "DAG of jobs" in m})
    temp = {m: n for m, n in msgs.items() if m.startswith("Removing temporary output")}
    print("temp removal messages:", len(temp), "logged twice:", sum(1 for n in temp.values() if n == 2))
    totals = [r["extra"]["total"] for r in recs if r.get("event") == "progress"]
    print("progress.total first/last:", totals[0], totals[-1], "distinct:", len(set(totals)))
    ws = next(r for r in recs if r.get("event") == "workflow_started")
    print("workflow_started identity keys:", sorted(k for k in ws["extra"] if k in ("host", "user", "cmd", "cwd", "rundir", "platform")))


def smk_attempts():  # row 16: one JOB_ERROR per failed attempt (tool error: 3 attempts)
    recs = load("snakemake-9.27.1_tool_error")
    print("job_error per jobid:", dict(collections.Counter(r["extra"]["jobid"] for r in recs if r.get("event") == "job_error")))
    print("restart messages:", [r["msg"] for r in recs if r.get("event") in (None, "None") and r["msg"].startswith("Trying")])


CHECKS = {f.__name__: f for f in (after_terminate, downstream_terminate, outputs, flow_end, failed_status, resume,
                                   pending_only, tower_begin_and_tasks, smk, smk_attempts)}

if __name__ == "__main__":
    names = list(CHECKS) if sys.argv[1:] in ([], ["all"]) else sys.argv[1:]
    for n in names:
        print(f"## {n}")
        CHECKS[n]()
