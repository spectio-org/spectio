#!/usr/bin/env python3
"""Spike T2: turn a raw capture (JSON lines) into a committed fixture.

usage: normalise.py RAW OUT --sub LITERAL=TOKEN [--sub ...]

Rules (applied to every string, recursively, longest literal first):
  * each --sub literal (launch dir, repo root, scratch dir, $HOME) -> its token (<launch>, <repo>, ...);
  * the host name and the user name -> <host> and <user>;
  * the values of keys that name a person, a host or a secret -> "<redacted>";
  * the Authorization header value (capture server) -> "<redacted>";
  * the string value of each --token-key key -> "<key>" (Snakemake: --token-key platform).
Timestamps, sequence numbers and IDs (session id, run name, workflow_id) are kept: they are not
personal, and the same-run check needs them.
"""
import argparse, getpass, json, os, re, socket, sys

REDACT_KEYS = {"userName", "user", "hostname", "homeDir", "authorization", "Authorization",
               "accessToken", "towerAccessToken", "token", "machineName"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("out")
    ap.add_argument("--sub", action="append", default=[])
    ap.add_argument("--slim", action="store_true",
                    help="nf-spectio captures: drop the trace record from onTaskPending/Submit/Start")
    ap.add_argument("--token-key", action="append", default=[],
                    help="replace the string value of this key by <key> (e.g. platform: the kernel string)")
    a = ap.parse_args()
    subs = [tuple(s.split("=", 1)) for s in a.sub]
    subs += [(os.path.expanduser("~"), "<home>")]
    host = re.compile(r"\b" + re.escape(socket.gethostname()) + r"\b")
    subs.sort(key=lambda p: -len(p[0]))
    user = getpass.getuser()

    def s(v: str) -> str:
        for lit, tok in subs:
            if lit:
                v = v.replace(lit, tok)
        v = host.sub("<host>", v)  # whole word only: a short host name ("vm") is a common substring
        # user name only as a path or word component, not inside unrelated words
        for pre, post in (("/", "/"), ("/", "\n"), (" ", " "), ("=", " ")):
            v = v.replace(pre + user + post, pre + "<user>" + post)
        return v

    def walk(o, key=None):
        if key in REDACT_KEYS and o not in (None, "", [], {}):
            return "<redacted>"
        if key in a.token_key and isinstance(o, str):
            return f"<{key}>"
        if isinstance(o, str):
            return s(o)
        if isinstance(o, list):
            return [walk(v) for v in o]
        if isinstance(o, dict):
            return {k: walk(v, k) for k, v in o.items()}
        return o

    n = 0
    with open(a.raw) as fi, open(a.out, "w") as fo:
        for line in fi:
            if line.strip():
                rec = json.loads(line)
                body = rec.get("body") if isinstance(rec.get("body"), dict) else {}
                if a.slim and body.get("hook") in ("onTaskPending", "onTaskSubmit", "onTaskStart"):
                    body.pop("trace", None)  # size only: the record is repeated on onTaskComplete
                fo.write(json.dumps(walk(rec), sort_keys=True) + "\n")
                n += 1
    print(f"{a.out}: {n} lines, {os.path.getsize(a.out)} bytes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
