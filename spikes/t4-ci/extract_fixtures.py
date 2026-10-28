#!/usr/bin/env python3
"""Write the fixture blocks of a GitHub Actions job log back to files.

    python3 extract_fixtures.py JOB_LOG.txt OUT_DIR

Reads the plain-text log of one job (the web UI's "Download log archive", `gh run view --log`, or the
REST endpoint /repos/{owner}/{repo}/actions/jobs/{job_id}/logs). Each line may start with the runner's
ISO timestamp, which is removed. Every block printed by fixture.py becomes OUT_DIR/<name>.json; a block
whose JSON does not parse (a cut log) is written as <name>.broken.txt and reported, and the exit code is 1.
"""
import json
import pathlib
import re
import sys

STAMP = re.compile(r"^\ufeff?\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z ")
BEGIN = re.compile(r"=====SPECTIO-FIXTURE-BEGIN name=(\S+) ")
END = "=====SPECTIO-FIXTURE-END name="


def main(log_path, out_dir):
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name, buf, bad, n = None, [], 0, 0
    for line in pathlib.Path(log_path).read_text(errors="replace").splitlines():
        line = STAMP.sub("", line)
        m = BEGIN.search(line)
        if m:
            name, buf = m.group(1), []
            continue
        if name and line.startswith(END):
            text = "\n".join(buf)
            try:
                doc = json.loads(text)
                (out / f"{name}.json").write_text(json.dumps(doc, indent=1) + "\n")
                n += 1
            except json.JSONDecodeError as err:
                (out / f"{name}.broken.txt").write_text(text)
                print(f"broken: {name}: {err}", file=sys.stderr)
                bad += 1
            name = None
            continue
        if name:
            buf.append(line)
    print(f"{n} fixtures written to {out}, {bad} broken")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
