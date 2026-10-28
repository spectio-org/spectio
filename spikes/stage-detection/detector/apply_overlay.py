#!/usr/bin/env python3
"""Spike: apply a declared spectio.yml overlay (stages[].match globs) to a run's process or rule
names, as the server would: each name gets the first stage whose glob matches (fnmatchcase on the
fully qualified Nextflow name or the Snakemake rule name; `*` also crosses `:`); names matched by
no stage go to "Other"; a name matched by two stages is an overlap (refused by
`spectio workflow validate`, checking-scenarios §12.3).

usage: apply_overlay.py OVERLAY.yml (EVENTS.jsonl | RULES.txt) [DETECTED.json]
"""
import fnmatch
import json
import sys

import yaml


def names(path):
    if path.endswith(".jsonl"):
        out = []
        for line in open(path):
            b = json.loads(line).get("body") or {}
            if b.get("hook") == "onProcessCreate":
                out.append(b["process"])
        return out
    return [l.strip() for l in open(path) if l.strip()]


def main(overlay, source, detected=None):
    stages = yaml.safe_load(open(overlay))["stages"]
    assign, overlaps, other = {}, [], []
    for n in names(source):
        hits = [s["id"] for s in stages if any(fnmatch.fnmatchcase(n, g) for g in s["match"])]
        if len(hits) > 1:
            overlaps.append((n, hits))
        if hits:
            assign.setdefault(hits[0], []).append(n)
        else:
            other.append(n)
    det = {}
    if detected:
        for s in json.load(open(detected)):
            for n in s["match"]:
                det[n] = s["name"]
    print(f"# {overlay.split('/')[-1]} on {source.split('/')[-1]}")
    for s in stages:
        got = assign.get(s["id"], [])
        src = sorted({det[n] for n in got if n in det})
        line = f"{s['id']:<13} {len(got):>3}  {s['name']}"
        if detected:
            line += f"   <- detected: {'; '.join(src) if src else '-'}"
        print(line)
    print(f"{'Other':<13} {len(other):>3}  {', '.join(o.split(':')[-1] for o in other) or '-'}")
    print(f"overlaps: {overlaps or 'none'}")


if __name__ == "__main__":
    main(*sys.argv[1:])
