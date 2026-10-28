#!/usr/bin/env python3
"""Extract the fixture blocks that fixture.py printed from a GitHub Actions job log.

  python3 extract_fixtures.py JOB_LOG.txt OUT_DIR

The log is the plain text that the REST API (`GET /repos/{o}/{r}/actions/jobs/{id}/logs`) or the
GitHub tools return: each line starts with an ISO timestamp, which is stripped. Each block is
written to OUT_DIR/<name>.json after its sha256 is checked against the BEGIN line; a block whose
hash differs (a cut or wrapped log) is reported and not written. Exits 1 if any block failed.
"""
import hashlib, pathlib, re, sys

TS = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z ?")
BEGIN = re.compile(r"^----- BEGIN SPECTIO FIXTURE name=(\S+) bytes=(\d+) sha256=([0-9a-f]{64}) -----$")


def main() -> int:
    log, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    cur, body, bad = None, [], 0
    for line in log.read_text(errors="replace").splitlines():
        line = TS.sub("", line, count=1)
        if m := BEGIN.match(line):
            cur, body = m, []
        elif cur and line == f"----- END SPECTIO FIXTURE name={cur[1]} -----":
            text = "\n".join(body)
            if hashlib.sha256(text.encode()).hexdigest() == cur[3]:
                (out / f"{cur[1]}.json").write_text(text + "\n")
                print(f"ok   {cur[1]} ({cur[2]} bytes)")
            else:
                print(f"BAD  {cur[1]}: sha256 differs (log cut or reflowed)")
                bad += 1
            cur = None
        elif cur:
            body.append(line)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
