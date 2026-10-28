#!/usr/bin/env python3
"""GET slurmrestd endpoints with the caller's JWT and write each JSON answer to OUT_DIR/NAME.json.

  SLURM_JWT=... python3 rest_get.py URL OUT_DIR NAME=PATH ...

Runs inside a sind node as the cluster user (tests/slurm/scenarios.sh rest). The token is read from the
environment and sent as X-SLURM-USER-TOKEN; it is never printed or written. Prints one line per call:
NAME HTTP-STATUS BYTES.
"""
import getpass, os, sys, urllib.error, urllib.request


def main() -> int:
    url, out, calls = sys.argv[1], sys.argv[2], sys.argv[3:]
    headers = {"X-SLURM-USER-NAME": getpass.getuser(), "X-SLURM-USER-TOKEN": os.environ["SLURM_JWT"]}
    for call in calls:
        name, path = call.split("=", 1)
        try:
            with urllib.request.urlopen(urllib.request.Request(url + path, headers=headers), timeout=30) as r:
                code, body = r.status, r.read()
        except urllib.error.HTTPError as e:
            code, body = e.code, e.read()
        with open(os.path.join(out, name + ".json"), "wb") as f:
            f.write(body)
        print(name, code, len(body))
    return 0


if __name__ == "__main__":
    sys.exit(main())
