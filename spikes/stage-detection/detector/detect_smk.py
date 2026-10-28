#!/usr/bin/env python3
"""Spike: detect the big stages of a Snakemake workflow from its rule files.

The logger plugin sees a rule *name* per job (`job_info.rule_name`), not the file it comes from,
and the `rulegraph` record at start only holds the rules of the DAG before any checkpoint. So
the rule -> stage map is built from the source: `workflow_started.snakefile_main` names the
main Snakefile, for Spectio-launched and terminal-started runs alike.

Algorithm (throwaway):
  1. From the main Snakefile, follow every `include:` with a literal path, in source order,
     depth first, conditional ones included (over-approximation: rules that never run just get
     no jobs). Paths are relative to the including file.
  2. Each file that defines rules (`rule`, `checkpoint`, `use rule ... as`, indented or not)
     is a group, in include order; rules of the main Snakefile form their own group.
  3. Files under a sub-directory of rules/ (rules/ashleys/*.smk) are one group per directory.
  4. Cap: while more than MAX groups, merge the adjacent pair with the fewest rules.
  5. Name: the file stem humanised. Rules not found (dynamic includes, modules) -> "Other".
  With --defined (the rules `snakemake --list-rules` prints with the run's config, i.e. at
  launch), rules of conditional includes that this config does not define are dropped before
  grouping. The main Snakefile's group (usually only `all`) goes last, as "Final targets".

usage: detect_smk.py MAIN_SNAKEFILE [--max N] [--json] [--defined RULES.txt]
"""
import json
import pathlib
import re
import sys

MAX = 8
INCLUDE = re.compile(r"""^\s*include:\s*["']([^"']+)["']""")
RULE = re.compile(r"^\s*(?:local)?(?:rule|checkpoint)\s+(\w+)\s*:")
USE_AS = re.compile(r"^\s*use rule\s+.*\bas\s+(\w+)")
CHECKPOINT = re.compile(r"^\s*(?:local)?checkpoint\s+(\w+)\s*:")
MODULE = re.compile(r"^\s*module\s+(\w+)\s*:")


def walk(path, seen, files):
    path = path.resolve()
    if path in seen or not path.exists():
        return
    seen.add(path)
    rules, checkpoints, modules = [], [], []
    for line in path.read_text().splitlines():
        m = INCLUDE.match(line)
        if m:
            # rules of this file defined before the include stay in this file's group
            walk(path.parent / m.group(1), seen, files)
            continue
        for rx, bucket in ((RULE, rules), (USE_AS, rules)):
            m = rx.match(line)
            if m:
                bucket.append(m.group(1))
        m = CHECKPOINT.match(line)
        if m:
            checkpoints.append(m.group(1))
        m = MODULE.match(line)
        if m:
            modules.append(m.group(1))
    files.append({"file": path, "rules": rules, "checkpoints": checkpoints, "modules": modules})


def detect(main, cap=MAX, defined=None):
    main = pathlib.Path(main).resolve()
    files = []
    walk(main, set(), files)
    order = {}
    # walk() appends a file after its includes; re-order by first include (pre-order)
    pre = []

    def pre_walk(path, seen):
        path = path.resolve()
        if path in seen or not path.exists():
            return
        seen.add(path)
        pre.append(path)
        for line in path.read_text().splitlines():
            m = INCLUDE.match(line)
            if m:
                pre_walk(path.parent / m.group(1), seen)

    pre_walk(main, set())
    order = {p: i for i, p in enumerate(pre)}
    files.sort(key=lambda f: order[f["file"]])

    rules_dir = main.parent / "rules"
    groups = []
    for f in files:
        if defined is not None:
            f["rules"] = [r for r in dict.fromkeys(f["rules"]) if r in defined]
            f["checkpoints"] = [r for r in f["checkpoints"] if r in defined]
        if not f["rules"]:
            continue
        rel = f["file"].relative_to(main.parent)
        if f["file"] == main:
            key, label = "main", "Final targets"
        elif f["file"].parent != rules_dir and rules_dir in f["file"].parents:
            key = str(f["file"].parent.relative_to(main.parent))
            label = f["file"].parent.name
        else:
            key, label = str(rel), f["file"].stem
        if groups and groups[-1]["key"] == key:
            groups[-1]["rules"] += f["rules"]
            groups[-1]["checkpoints"] += f["checkpoints"]
            groups[-1]["files"].append(str(rel))
        else:
            groups.append({"key": key, "labels": [label], "rules": list(f["rules"]),
                           "checkpoints": list(f["checkpoints"]), "files": [str(rel)]})

    groups.sort(key=lambda g: g["key"] == "main")  # stable: main group last
    while len(groups) > cap:
        pairs = [i for i in range(len(groups) - 1) if "main" not in (groups[i]["key"], groups[i + 1]["key"])]
        i = min(pairs, key=lambda i: len(groups[i]["rules"]) + len(groups[i + 1]["rules"]))
        a, b = groups[i], groups.pop(i + 1)
        for k in ("labels", "rules", "checkpoints", "files"):
            a[k] += b[k]

    def humanise(s):
        return s.replace("_", " ").replace("-", " ").strip().capitalize()

    return [{"id": f"detected:{n}", "name": " + ".join(humanise(l) for l in g["labels"]),
             "source": "detected", "match": g["rules"], "files": g["files"],
             "checkpoints": g["checkpoints"]}
            for n, g in enumerate(groups, 1)]


def main(argv):
    cap = MAX
    if "--max" in argv:
        k = argv.index("--max")
        cap = int(argv[k + 1])
        argv = argv[:k] + argv[k + 2:]
    seen = None
    if "--defined" in argv:
        k = argv.index("--defined")
        seen = [l.strip() for l in open(argv[k + 1]) if l.strip()]
        argv = argv[:k] + argv[k + 2:]
    args = [a for a in argv if not a.startswith("--")]
    stages = detect(args[0], cap, set(seen) if seen is not None else None)
    if "--json" in argv:
        json.dump(stages, sys.stdout, indent=1)
        print()
        return
    total = len({r for s in stages for r in s["match"]})
    print(f"# {args[0]}: {total} rules -> {len(stages)} detected stages (cap {cap})")
    for s in stages:
        cp = f"  checkpoints: {', '.join(s['checkpoints'])}" if s["checkpoints"] else ""
        print(f"{s['id']:<12} {len(s['match']):>3}  {s['name']}{cp}")
    if seen is not None:
        known = {r for s in stages for r in s["match"]}
        other = [r for r in seen if r not in known]
        print(f"rules defined (--list-rules): {len(seen)}; in no stage (-> Other): {other or 'none'}")


if __name__ == "__main__":
    main(sys.argv[1:])
