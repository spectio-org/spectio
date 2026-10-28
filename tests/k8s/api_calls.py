#!/usr/bin/env python3
"""Summarise the Kubernetes API calls a Nextflow head made, from its .nextflow.log run with
`-trace nextflow.k8s.client`, as RBAC (resource, verb) pairs, and list every refused request.

    python3 api_calls.py .nextflow.log

K8sClient logs "[K8s] API response <METHOD> <path>" at trace level after each successful request
(plugins/nf-k8s/src/main/nextflow/k8s/client/K8sClient.groovy, trace() L672-L674 at v26.10.4), and
raises "Request <METHOD> <path> returned an error code=<n>" on a 4xx/5xx (L664-L668).
Output: one JSON object {"used": {"pods/status get": 12, ...}, "refused": [...]}.
"""
import json
import re
import sys
from collections import Counter

OK = re.compile(r"\[K8s\] API response (GET|POST|PUT|PATCH|DELETE) (\S+)")
ERR = re.compile(r"Request (GET|POST|PUT|PATCH|DELETE) (\S+) returned an error code=(\d+)")


def rbac(method, path):
    path, _, query = path.partition("?")
    parts = [p for p in path.split("/") if p]
    # /api/v1/... or /apis/<group>/<version>/...
    group = "" if parts[0] == "api" else parts[1]
    rest = parts[2:] if parts[0] == "api" else parts[3:]
    if rest[:1] == ["namespaces"]:
        rest = rest[2:]
    resource = rest[0] if rest else "?"
    name = rest[1] if len(rest) > 1 else None
    sub = rest[2] if len(rest) > 2 else None
    if sub:
        resource = f"{resource}/{sub}"
    if group:
        resource = f"{group}:{resource}"
    verb = {"POST": "create", "PUT": "update", "PATCH": "patch", "DELETE": "delete"}.get(method)
    if verb is None:
        verb = "watch" if "watch=true" in query else ("get" if name else "list")
    return f"{resource} {verb}"


def main(path):
    used, refused = Counter(), []
    for line in open(path, errors="replace"):
        m = OK.search(line)
        if m:
            used[rbac(m.group(1), m.group(2))] += 1
            continue
        m = ERR.search(line)
        if m:
            refused.append({"call": rbac(m.group(1), m.group(2)), "code": int(m.group(3)), "path": m.group(2)})
    # one entry per distinct refusal, with a count
    seen = Counter((r["call"], r["code"]) for r in refused)
    print(json.dumps({"used": dict(sorted(used.items())),
                      "refused": [{"call": c, "code": k, "count": n} for (c, k), n in sorted(seen.items())]},
                     indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
