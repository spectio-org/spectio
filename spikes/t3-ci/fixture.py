#!/usr/bin/env python3
"""Print one Slurm JSON document from stdin as a size-limited fixture block for the CI log.

  sacct --json -j 12 | python3 fixture.py NAME [--jobs 12,13] [--max-bytes 49152]

With --jobs, only the jobs whose job_id (or array job id) is listed are kept. If the result is still
over --max-bytes, list entries are dropped from the end and "_spike_truncated" is set. The block is
fenced by marker lines that extract_fixtures.py finds again in a downloaded job log:

  ----- BEGIN SPECTIO FIXTURE name=NAME bytes=N sha256=HEX -----
  ... indented JSON ...
  ----- END SPECTIO FIXTURE name=NAME -----
"""
import argparse, hashlib, json, sys


def job_ids(job: dict) -> set[str]:
    ids = {str(job.get("job_id"))}
    arr = job.get("array_job_id")          # squeue / scontrol: {"set": .., "number": ..}
    if isinstance(arr, dict) and arr.get("set"):
        ids.add(str(arr.get("number")))
    arr = (job.get("array") or {}).get("job_id")   # sacct
    if arr:
        ids.add(str(arr))
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--jobs", default="")
    ap.add_argument("--max-bytes", type=int, default=49152)
    a = ap.parse_args()
    raw = sys.stdin.read()
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"fixture {a.name}: not JSON ({e}); first bytes: {raw[:300]!r}")
        return 1
    want = {j for j in a.jobs.split(",") if j}
    if want and isinstance(doc.get("jobs"), list):
        doc["jobs"] = [j for j in doc["jobs"] if job_ids(j) & want]
    text = json.dumps(doc, indent=1, sort_keys=True)
    while len(text.encode()) > a.max_bytes:
        lists = [k for k, v in doc.items() if isinstance(v, list) and len(v) > 1]
        if not lists:
            break
        k = max(lists, key=lambda k: len(json.dumps(doc[k])))
        doc[k] = doc[k][:-1]
        doc["_spike_truncated"] = True
        text = json.dumps(doc, indent=1, sort_keys=True)
    digest = hashlib.sha256(text.encode()).hexdigest()
    print(f"----- BEGIN SPECTIO FIXTURE name={a.name} bytes={len(text.encode())} sha256={digest} -----")
    print(text)
    print(f"----- END SPECTIO FIXTURE name={a.name} -----")
    return 0


if __name__ == "__main__":
    sys.exit(main())
