#!/usr/bin/env python3
"""Spike T2: summarise nf-spectio captures and compare them with the Tower capture of the same run.
usage: analyse_plugin.py PLUGIN.jsonl [TOWER.jsonl]"""
import collections, json, sys

P = [json.loads(l)["body"] for l in open(sys.argv[1])]
print("#####", sys.argv[1].split("/")[-1])
print(" hooks:", dict(collections.Counter(b["hook"] for b in P)))
print(" ids:", {(b["runName"], b["sessionId"]) for b in P})
print(" flow/process order:", [(b["hook"], b.get("process")) for b in P
                               if b["hook"].startswith(("onFlow", "onProcess"))])
for b in P:
    if b["hook"] in ("onTaskComplete", "onTaskCached") and b.get("process") == "QC_STATS":
        print(" ", b["hook"], "QC_STATS outputs:", b["outputs"]); break
for b in P:
    if b["hook"] in ("onTaskComplete", "onTaskCached") and b.get("process") == "SPLIT":
        print(" ", b["hook"], "SPLIT outputs:", b["outputs"]); break
odd = [(b["hook"], b["process"], b["tag"], b["status"], b["attempt"], b["exitStatus"], b["errorAction"], b["taskId"])
       for b in P if b["hook"].startswith("onTask") and (b.get("attempt", 1) > 1 or b.get("errorAction"))]
print(" failed/retried:", odd)
print(" onFlowError:", [b for b in P if b["hook"] == "onFlowError"])
print(" handler status vs trace status on failed attempts:",
      [(b["process"], b["status"], (b.get("trace") or {}).get("status"), b["exitStatus"])
       for b in P if b["hook"] == "onTaskComplete" and b.get("errorAction")])
print(" handler statuses per hook:", dict(collections.Counter((b["hook"], b.get("status")) for b in P if b["hook"].startswith("onTask"))))
print(" pending never submitted:", {(b["process"], b["tag"]) for b in P if b["hook"] == "onTaskPending"}
      - {(b["process"], b["tag"]) for b in P if b["hook"] == "onTaskSubmit"})
print(" onFlowComplete:", [(b.get("success"), b.get("exitStatus"), (b.get("errorMessage") or "")[:60]) for b in P if b["hook"] == "onFlowComplete"])
pub = [b for b in P if b["hook"] == "onFilePublish"]
print(" onFilePublish:", len(pub), pub[0] if pub else None)
# the last event per process before its onProcessTerminate
term = [i for i, b in enumerate(P) if b["hook"] == "onProcessTerminate"]
for i in term:
    proc = P[i]["process"]
    later = [b["hook"] for b in P[i + 1:] if b.get("process") == proc and b["hook"].startswith("onTask")]
    if later:
        print("  task events of", proc, "AFTER its onProcessTerminate:", collections.Counter(later))
if len(sys.argv) > 2:
    T = [json.loads(l) for l in open(sys.argv[2])]
    create = next(r["body"] for r in T if r["path"] == "/trace/create")
    print(" tower create ids:", create["runName"], create["sessionId"])
    same = {(b["runName"], b["sessionId"]) for b in P} == {(create["runName"], create["sessionId"])}
    print(" SAME RUN:", same)
    tt = {t["taskId"] for r in T if "/progress" in r["path"] or "/complete" in r["path"] for t in (r["body"] or {}).get("tasks") or []}
    pt = {int(b["taskId"]) for b in P if b["hook"].startswith("onTask") and b.get("taskId")}
    print(" taskIds tower:", len(tt), "plugin:", len(pt), "equal:", tt == pt)
