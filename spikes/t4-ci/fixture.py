#!/usr/bin/env python3
"""Print one JSON document from stdin as a fenced, size-limited fixture block in the CI job log.

    kubectl get pods -o json | python3 fixture.py NAME [--max-bytes N] [--meta k=v ...]

The block is what extract_fixtures.py reads back from a downloaded job log:

    =====SPECTIO-FIXTURE-BEGIN name=NAME bytes=N items=K/T=====
    { ...pretty JSON... }
    =====SPECTIO-FIXTURE-END name=NAME=====

managedFields and the last-applied annotation are dropped (noise, and they hold no state). When the
document is over --max-bytes, items are dropped from the end of its `items` list until it fits, and
`_spike.truncated` says how many were kept; a document with no list to trim is cut to a stub.
"""
import argparse
import json
import sys

NOISE_ANNOTATIONS = ("kubectl.kubernetes.io/last-applied-configuration",)


def strip(obj):
    if isinstance(obj, dict):
        meta = obj.get("metadata")
        if isinstance(meta, dict):
            meta.pop("managedFields", None)
            ann = meta.get("annotations")
            if isinstance(ann, dict):
                for key in NOISE_ANNOTATIONS:
                    ann.pop(key, None)
        for value in obj.values():
            strip(value)
    elif isinstance(obj, list):
        for value in obj:
            strip(value)
    return obj


def render(doc):
    return json.dumps(doc, indent=1, sort_keys=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--max-bytes", type=int, default=60000)
    ap.add_argument("--meta", nargs="*", default=[], help="k=v pairs stored under _spike")
    args = ap.parse_args()

    raw = sys.stdin.read()
    try:
        doc = strip(json.loads(raw))
    except json.JSONDecodeError as err:
        doc = {"_spike": {"error": f"not JSON: {err}", "head": raw[:2000]}}
    if not isinstance(doc, dict):
        doc = {"items": doc}
    spike = doc.setdefault("_spike", {})
    spike.update(dict(kv.split("=", 1) for kv in args.meta))

    items = doc.get("items")
    total = len(items) if isinstance(items, list) else None
    text = render(doc)
    if len(text.encode()) > args.max_bytes:
        if isinstance(items, list):
            while items and len(render(doc).encode()) > args.max_bytes:
                items.pop()
            spike["truncated"] = f"kept {len(items)} of {total} items"
        else:
            doc = {"_spike": dict(spike, truncated=f"document of {len(text)} bytes over the limit")}
        text = render(doc)
    kept = len(doc["items"]) if isinstance(doc.get("items"), list) else "-"
    print(f"=====SPECTIO-FIXTURE-BEGIN name={args.name} bytes={len(text.encode())} items={kept}/{total if total is not None else '-'}=====")
    print(text)
    print(f"=====SPECTIO-FIXTURE-END name={args.name}=====")


if __name__ == "__main__":
    main()
