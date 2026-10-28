#!/usr/bin/env python3
"""Write one Slurm JSON document from stdin as a fixture file.

  sacct --json -j 12 | python3 fixture.py OUT.json [--jobs 12,13] [--meta key=value ...]

With --jobs, only the jobs whose job_id (or array job id) is listed are kept. A "_fixture" object records
--meta (Slurm version, source run). Refuses to write a document that looks like it holds a credential
(a JWT or a key block), so that no token reaches the artifacts or the committed copies.
"""
import argparse, json, re, sys

SECRET = re.compile(r"eyJ[\w-]{10,}\.[\w-]{10,}|SLURM_JWT|PRIVATE KEY")


def job_ids(job: dict) -> set[str]:
    ids = {str(job.get("job_id"))}
    arr = job.get("array_job_id")                  # squeue / scontrol: {"set": .., "number": ..}
    if isinstance(arr, dict) and arr.get("set"):
        ids.add(str(arr.get("number")))
    arr = (job.get("array") or {}).get("job_id")   # sacct
    if arr:
        ids.add(str(arr))
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--jobs", default="")
    ap.add_argument("--meta", nargs="*", default=[])
    a = ap.parse_args()
    raw = sys.stdin.read()
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"fixture {a.out}: not JSON ({e}); first bytes: {raw[:300]!r}", file=sys.stderr)
        return 1
    want = {j for j in a.jobs.split(",") if j}
    if want and isinstance(doc.get("jobs"), list):
        doc["jobs"] = [j for j in doc["jobs"] if job_ids(j) & want]
    doc["_fixture"] = dict(m.split("=", 1) for m in a.meta)
    text = json.dumps(doc, indent=1, sort_keys=True) + "\n"
    if SECRET.search(text):
        print(f"fixture {a.out}: looks like it holds a credential; not written", file=sys.stderr)
        return 1
    with open(a.out, "w") as f:
        f.write(text)
    print(f"fixture {a.out}: {len(text.encode())} bytes, {len(doc.get('jobs') or [])} jobs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
