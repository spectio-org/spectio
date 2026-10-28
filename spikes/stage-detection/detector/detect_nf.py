#!/usr/bin/env python3
"""Spike: detect the big stages of a Nextflow run from its fully qualified process names.

Input: the ordered process names nf-spectio gets from `onProcessCreate` (all are known before
`onFlowBegin`, in script order), plus the pipeline name from the manifest (`nf-core/rnaseq` ->
scope `RNASEQ`). Optional: the pipeline source dir, for subworkflow `meta.yml` descriptions.

Algorithm (v1, throwaway; v0 is in LOG.md):
  1. Expand wrapper scopes: the scope every process sits under (`NFCORE_RNASEQ`), then the scope
     named after the pipeline (`RNASEQ`). Their children are the candidate groups. Without a
     manifest name (MANIFEST_NAME `-`), the pipeline scope is the child of the wrapper that holds
     more than half of the processes, if any.
  2. A child subworkflow is a group. Processes called directly form one group per run of
     consecutive direct calls in the same parent scope.
  3. Aliases: consecutive groups whose names differ only in their last word
     (`..._FORWARD`, `..._REVERSE`) are merged.
  4. A one-process direct group joins the previous group of the same parent scope (the next one
     if it is the first), except MULTIQC, which stays its own "Report" group.
  5. Cap: while there are more than MAX groups, merge the adjacent pair with the fewest
     processes, never across a parent scope while another pair exists, never the Report group.
  6. Name: the subworkflow name, humanised; description from meta.yml when present.
  7. No subworkflow at all (a flat pipeline), or fewer than 2 groups: no detected stages; the run
     shows its process list only (stage mode "none").

usage: detect_nf.py EVENTS.jsonl MANIFEST_NAME [PIPELINE_SRC_DIR] [--max N] [--json]
"""
import json
import pathlib
import sys

MAX = 8


def process_names(path):
    out = []
    for line in open(path):
        body = json.loads(line).get("body") or {}
        if body.get("hook") == "onProcessCreate":
            out.append(body["process"])
    return out


def humanise(scope):
    return " ".join(scope.lower().split("_")).capitalize()


def meta_description(src, scope):
    if not src:
        return None
    for kind in ("nf-core", "local"):
        meta = pathlib.Path(src, "subworkflows", kind, scope.lower(), "meta.yml")
        if meta.exists():
            for line in meta.read_text().splitlines():
                if line.startswith("description:"):
                    return line.split(":", 1)[1].strip().strip("\"'") or None
    return None


def is_report(g):
    return g["kind"] == "direct" and len(g["heads"]) == 1 and "MULTIQC" in g["heads"][0] \
        or g["kind"] == "sub" and g["heads"][0].startswith("MULTIQC")


def detect(names, manifest_name, src=None, cap=MAX):
    split = [n.split(":") for n in names]

    # 1. wrapper scopes
    depth = 0
    while len({s[depth] for s in split}) == 1 and all(len(s) > depth + 1 for s in split):
        depth += 1
    if manifest_name != "-":
        pipeline_scope = manifest_name.split("/")[-1].upper().replace("-", "_")
    else:
        counts = {}
        for s in split:
            if len(s) > depth + 1:
                counts[s[depth]] = counts.get(s[depth], 0) + 1
        top = max(counts, key=counts.get) if counts else None
        pipeline_scope = top if top and counts[top] * 2 > len(split) else None

    def locate(parts):
        """(parent scope, group head, is subworkflow) for one process."""
        if len(parts) > depth + 1 and parts[depth] == pipeline_scope:
            return parts[depth], parts[depth + 1], len(parts) > depth + 2
        return ":".join(parts[:depth]), parts[depth], len(parts) > depth + 1

    # 2. groups in first-seen order
    groups = []
    for name, parts in zip(names, split):
        parent, head, is_sub = locate(parts)
        last = groups[-1] if groups else None
        if is_sub:
            hit = next((g for g in groups if g["kind"] == "sub" and g["parent"] == parent
                        and g["heads"] == [head]), None)
            if hit is None:
                hit = {"kind": "sub", "parent": parent, "heads": [head], "processes": []}
                groups.append(hit)
            hit["processes"].append(name)
        elif last and last["kind"] == "direct" and last["parent"] == parent \
                and "MULTIQC" not in head and not any("MULTIQC" in h for h in last["heads"]):
            last["heads"].append(head)
            last["processes"].append(name)
        else:
            groups.append({"kind": "direct", "parent": parent, "heads": [head], "processes": [name]})

    # 3. aliases
    out = []
    for g in groups:
        p = out[-1] if out else None
        if p and p["kind"] == g["kind"] == "sub" and p["parent"] == g["parent"] \
                and p["heads"][0].rsplit("_", 1)[0] == g["heads"][0].rsplit("_", 1)[0]:
            p["heads"] += g["heads"]
            p["processes"] += g["processes"]
        else:
            out.append(g)
    groups = out

    # 4. lone direct processes
    i = 0
    while i < len(groups):
        g = groups[i]
        if g["kind"] == "direct" and len(g["processes"]) == 1 and not is_report(g):
            same = [j for j in (i - 1, i + 1) if 0 <= j < len(groups)
                    and groups[j]["parent"] == g["parent"] and not is_report(groups[j])]
            if same:
                t = groups[same[0]]
                t.setdefault("attached", []).append(g["heads"][0])
                t["processes"] = (t["processes"] + g["processes"]) if same[0] < i \
                    else (g["processes"] + t["processes"])
                del groups[i]
                continue
        i += 1

    # 5. cap
    while len(groups) > cap:
        pairs = [i for i in range(len(groups) - 1)
                 if not is_report(groups[i]) and not is_report(groups[i + 1])]
        same = [i for i in pairs if groups[i]["parent"] == groups[i + 1]["parent"]]
        i = min(same or pairs, key=lambda i: len(groups[i]["processes"]) + len(groups[i + 1]["processes"]))
        a, b = groups[i], groups.pop(i + 1)
        a["heads"] += b["heads"]
        a["processes"] += b["processes"]
        a.setdefault("attached", []).extend(b.get("attached", []))
        a["kind"] = "sub"

    # 7. flat pipelines
    if len(groups) < 2 or not any(g["kind"] == "sub" for g in groups):
        return []

    # 6. stage list in the shape of spectio.yml stages[] (display only)
    stages = []
    for n, g in enumerate(groups, 1):
        if is_report(g):
            name = "Report"
        elif g["kind"] == "direct":
            name = ", ".join(humanise(h) for h in g["heads"])
        else:
            name = " + ".join(humanise(h) for h in g["heads"])
        desc = [d for d in (meta_description(src, h) for h in g["heads"]) if d]
        stages.append({"id": f"detected:{n}", "name": name, "source": "detected",
                       "match": g["processes"], "description": " / ".join(desc) or None,
                       "attached_processes": g.get("attached", [])})
    return stages


def main(argv):
    cap = MAX
    if "--max" in argv:
        k = argv.index("--max")
        cap = int(argv[k + 1])
        argv = argv[:k] + argv[k + 2:]
    args = [a for a in argv if not a.startswith("--")]
    events, manifest = args[0], args[1]
    src = args[2] if len(args) > 2 else None
    names = process_names(events)
    stages = detect(names, manifest, src, cap)
    if "--json" in argv:
        json.dump(stages, sys.stdout, indent=1)
        print()
        return
    print(f"# {manifest}: {len(names)} processes -> {len(stages)} detected stages (cap {cap})")
    for s in stages:
        extra = f"  [+ {', '.join(s['attached_processes'])}]" if s["attached_processes"] else ""
        d = " (meta.yml)" if s["description"] else ""
        print(f"{s['id']:<12} {len(s['match']):>3}  {s['name']}{d}{extra}")


if __name__ == "__main__":
    main(sys.argv[1:])
