#!/usr/bin/env python3
"""Re-check the T3 facts that TRIAGE3 uses, from the committed SLURM fixtures.

Usage: python3 -I <this file> <fixtures dir> [check ...]
  fixtures dir: tests/fixtures/slurm/slurm-26.05.5 (branch autopilot/T3, or its merge).
Checks: scenarios, probes, pending (default: all).
"""
import glob
import json
import os
import sys


def num(x):
    return x.get("number") if isinstance(x, dict) and x.get("set") else None


def row(j):
    ec = j.get("exit_code") or {}
    return (j["job_id"], j["name"][:40], "/".join(j["state"]["current"]), j["state"].get("reason"),
            f'{num(ec.get("return_code"))}:{num((ec.get("signal") or {}).get("id")) or 0}',
            "/".join(ec.get("status") or []), "kill_request_user=" + repr(j.get("kill_request_user")),
            "elapsed=%s limit_min=%s" % (j["time"]["elapsed"], num(j["time"]["limit"])))


def scenarios(d):
    for f in sorted(glob.glob(os.path.join(d, "*-sacct.json"))):
        doc = json.load(open(f))
        print("##", os.path.basename(f), "|", doc["_fixture"]["command"])
        for j in doc["jobs"]:
            print("  ", *row(j))


def probes(d):
    doc = json.load(open(os.path.join(d, "sacct-probes.json")))
    for j in doc["jobs"]:
        print("  ", *row(j))
    print("non-empty kill_request_user:", sum(1 for j in doc["jobs"] if j.get("kill_request_user")),
          "of", len(doc["jobs"]))


def pending(d):
    doc = json.load(open(os.path.join(d, "squeue-pending-reasons.json")))
    for j in doc["jobs"]:
        print("  ", j["job_id"], j["name"][:30], "/".join(j["job_state"]), "state_reason=" + repr(j["state_reason"]),
              "state_description=" + repr(j["state_description"]))


CHECKS = {"scenarios": scenarios, "probes": probes, "pending": pending}
if __name__ == "__main__":
    d = sys.argv[1]
    for n in sys.argv[2:] or list(CHECKS):
        print(f"# {n}")
        CHECKS[n](d)
