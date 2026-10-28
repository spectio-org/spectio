#!/usr/bin/env python3
"""Call slurmrestd endpoints with the caller's JWT and write each JSON answer to OUT_DIR/NAME.json.

  SLURM_JWT=... python3 rest_get.py URL OUT_DIR NAME=PATH ...    (GET; "NAME=DELETE PATH" for a DELETE)

Runs inside a sind node as the cluster user (tests/slurm/scenarios.sh rest). X-SLURM-USER-NAME is the
caller, or $REST_USER (to check that a token cannot act as another user). The token is read from the
environment and sent as X-SLURM-USER-TOKEN; it is never printed or written. Prints one line per call:
NAME HTTP-STATUS BYTES.
"""
import getpass, os, sys, urllib.error, urllib.request


def main() -> int:
    url, out, calls = sys.argv[1], sys.argv[2], sys.argv[3:]
    headers = {"X-SLURM-USER-NAME": os.environ.get("REST_USER") or getpass.getuser(),
               "X-SLURM-USER-TOKEN": os.environ["SLURM_JWT"]}
    for call in calls:
        name, path = call.split("=", 1)
        method, _, rest = path.partition(" ")
        method, path = (method, rest) if rest else ("GET", path)
        req = urllib.request.Request(url + path, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                code, body = r.status, r.read()
        except urllib.error.HTTPError as e:
            code, body = e.code, e.read()
        with open(os.path.join(out, name + ".json"), "wb") as f:
            f.write(body)
        print(name, code, len(body))
    return 0


if __name__ == "__main__":
    sys.exit(main())
