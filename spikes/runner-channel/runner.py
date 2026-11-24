"""Spike runner: runs on the login node under the user's own account, polls the central server
over outgoing HTTPS and answers its read commands from files under one root.

Usage: SPIKE_TOKEN=… python3 runner.py <server URL> <root> [--resolve host:ip] [--insecure]
Standard library only. Reads are confined to <root>: no `..`, no symlink anywhere on the path
(each component opened with O_NOFOLLOW from the root's descriptor), regular files only.
"""

import http.client
import json
import os
import socket
import ssl
import stat
import sys
import time
from urllib.parse import urlparse

MAX_LENGTH = 8 * 1024 * 1024 + 1
MAX_LIST = 1000


def open_under(root_fd: int, rel: str) -> int:
    """An fd for `rel` under the root, never through a symlink or `..`."""
    parts = [p for p in rel.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise PermissionError("'..' is not allowed")
    fd = os.dup(root_fd)
    try:
        for part in parts:
            nxt = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def answer(root_fd: int, cmd: dict) -> tuple[int, bytes, str]:
    try:
        fd = open_under(root_fd, cmd.get("path", ""))
    except FileNotFoundError:
        return 404, b"not found", "text/plain"
    except (PermissionError, OSError) as e:  # ELOOP for a symlink, EACCES for another's file
        return 403, f"refused: {e.strerror or e}".encode(), "text/plain"
    try:
        st = os.fstat(fd)
        if cmd["op"] == "stat":
            body = {"size": st.st_size, "mtime": st.st_mtime, "dir": stat.S_ISDIR(st.st_mode)}
            return 200, json.dumps(body).encode(), "application/json"
        if cmd["op"] == "list":
            if not stat.S_ISDIR(st.st_mode):
                return 400, b"not a directory", "text/plain"
            names = sorted(os.listdir(fd))[:MAX_LIST]
            return 200, json.dumps(names).encode(), "application/json"
        if not stat.S_ISREG(st.st_mode):
            return 400, b"not a regular file", "text/plain"
        length = min(int(cmd.get("length", 4096)), MAX_LENGTH)
        return 200, os.pread(fd, length, int(cmd.get("offset", 0))), "application/octet-stream"
    finally:
        os.close(fd)


def connection(url, resolve: str | None, insecure: bool) -> http.client.HTTPConnection:
    host, port = url.hostname, url.port or (443 if url.scheme == "https" else 80)
    target = resolve or host
    if url.scheme == "http":
        return http.client.HTTPConnection(target, port, timeout=60)
    ctx = ssl.create_default_context()
    if insecure:  # spike only: no DNS name yet, so the certificate cannot match
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    # the ingress routes on the Host header, sent with every request below
    return http.client.HTTPSConnection(target, port, timeout=60, context=ctx)


def main() -> None:
    url = urlparse(sys.argv[1].rstrip("/"))
    root = sys.argv[2]
    resolve = sys.argv[sys.argv.index("--resolve") + 1] if "--resolve" in sys.argv else None
    insecure = "--insecure" in sys.argv
    token = os.environ["SPIKE_TOKEN"]
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    headers = {
        "Authorization": f"Bearer {token}",
        "Host": url.hostname,
        "X-Runner-Host": socket.gethostname(),
    }
    base = url.path
    conn = connection(url, resolve, insecure)
    print(f"runner: polling {sys.argv[1]} for reads under {root}", flush=True)
    while True:
        try:
            conn.request("GET", f"{base}/runner/poll", headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            if resp.status == 204:
                continue
            if resp.status != 200:
                print(f"poll: {resp.status} {data[:200]!r}", flush=True)
                time.sleep(5)
                continue
            cmd = json.loads(data)
            t0 = time.monotonic()
            status, body, ctype = answer(root_fd, cmd)
            conn.request(
                "POST",
                f"{base}/runner/reply/{cmd['id']}",
                body=body,
                headers={**headers, "X-Status": str(status), "Content-Type": ctype},
            )
            conn.getresponse().read()
            ms = (time.monotonic() - t0) * 1000
            print(f"{cmd['op']} {cmd.get('path')!r} -> {status} {len(body)} B in {ms:.0f} ms", flush=True)
        except (OSError, http.client.HTTPException) as e:
            print(f"connection: {e}; again in 5 s", flush=True)
            conn.close()
            time.sleep(5)
            conn = connection(url, resolve, insecure)


if __name__ == "__main__":
    main()
