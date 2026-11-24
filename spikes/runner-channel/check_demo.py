#!/usr/bin/env python3
"""The spike's local end-to-end check (step 6 of the task).

Builds a temporary runner root (ui/ = the built demo bundle, data/ = the demo files), starts
server.py and runner.py on localhost, curl-checks every route the demo page calls — including
one file over 8 MiB, read in several runner commands — and stops both processes.

Usage: python3 check_demo.py <path to web/dist-demo>
"""

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = "spike-token-for-the-local-check"
RUNS = "/api/v1/runs/demo"
RESULTS = RUNS + "/results"

server_log = runner_log = []
failures = []
checks = 0


def ok(name: str, passed: bool, detail: str = "") -> None:
    global checks
    checks += 1
    suffix = f"  — {detail}" if detail else ""
    print(f"{'ok' if passed else 'FAIL'}  {name}{suffix}")
    if not passed:
        failures.append(name)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def curl(base: str, path: str, headers: dict | None = None, auth: str | None = TOKEN, out: str | None = None, as_is: bool = False) -> tuple[int, dict, bytes]:
    """One curl: (status, headers, body) — the body in `out` when given, else in memory."""
    cmd = ["curl", "-sS", "-D", "-", "-X", "GET", f"{base}{path}", "-w", "\n%{http_code}"]
    if as_is:
        cmd.insert(1, "--path-as-is")
    if auth:
        cmd += ["-H", f"Authorization: Bearer {auth}"]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    if out:
        cmd += ["-o", out]
    proc = subprocess.run(cmd, capture_output=True, text=False)
    blob = proc.stdout
    status = int(blob.rsplit(b"\n", 1)[-1])
    head = blob.rsplit(b"\n", 1)[0].decode("utf-8", "replace")
    headers_out: dict[str, str] = {}
    for line in head.split("\r\n")[1:]:
        if ": " in line:
            k, v = line.split(": ", 1)
            headers_out.setdefault(k.lower(), v)
    body = b""
    if out:
        if os.path.exists(out):
            body = open(out, "rb").read()
    else:
        # the body came after the headers, before the status line curl appended
        head_end = blob.find(b"\r\n\r\n") + 4
        body = blob[head_end:].rsplit(b"\n", 1)[0]
    return status, headers_out, body


def main() -> int:
    dist = os.path.abspath(sys.argv[1])
    root = tempfile.mkdtemp(prefix="spike-rc-root-")
    shutil.copytree(dist, os.path.join(root, "ui"))
    subprocess.run([sys.executable, os.path.join(HERE, "make_demo_data.py"), os.path.join(root, "data"), "--big"], check=True)
    data = os.path.join(root, "data")
    # a file whose name is not a Zarr key, for the key check's own 422 (a missing key 404s first,
    # as the product server's `open_raw` with missing="not-found" does)
    with open(os.path.join(data, "image.ome.zarr", "0", "not a key"), "w") as f:
        f.write("not a key\n")
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    body_file = os.path.join(tempfile.mkdtemp(prefix="spike-rc-bodies-"), "body")

    env = {**os.environ, "SPIKE_TOKEN": TOKEN, "PORT": str(port)}
    server = subprocess.Popen([sys.executable, os.path.join(HERE, "server.py")], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    runner = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "runner.py"), base, root, "--insecure"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(50):  # /health needs no auth; the runner takes a moment to start
            try:
                status, _, _ = curl(base, "/health", auth=None)
                if status == 200:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        else:
            print("server never answered /health")
            return 2

        # -- auth -----------------------------------------------------------------------
        status, _, _ = curl(base, "/", auth=None)
        ok("no auth: GET / is refused", status == 401, f"{status}")
        status, _, _ = curl(base, RUNS, auth=None)
        ok("no auth: the run's routes are refused", status == 401, f"{status}")

        # login: the token in the query, a cookie back (curl shows the raw reply)
        proc = subprocess.run(
            ["curl", "-sS", "-i", f"{base}/login?token=wrong"], capture_output=True, text=True,
        )
        ok("login with a wrong token: 403", proc.stdout.startswith("HTTP/1.1 403"), proc.stdout.splitlines()[0])
        proc = subprocess.run(
            ["curl", "-sS", "-i", f"{base}/login?token={TOKEN}"], capture_output=True, text=True,
        )
        set_cookie = next((l for l in proc.stdout.splitlines() if l.lower().startswith("set-cookie:")), "")
        cookie = set_cookie.split(":", 1)[1].strip() if set_cookie else ""
        cookie_value = cookie.split(";")[0] if cookie else ""
        ok("login with the token: 303 to /", proc.stdout.startswith("HTTP/1.1 303"), proc.stdout.split("\r\n")[0])
        ok(
            "the cookie is HttpOnly, Secure, SameSite=Strict",
            all(flag in cookie for flag in ("HttpOnly", "Secure", "SameSite=Strict")),
            cookie,
        )
        ok("the cookie has a session id", cookie_value.startswith("spike_session=") and len(cookie_value) > 30, cookie_value)
        sid = cookie_value.split("=", 1)[1]
        status, headers, _ = curl(base, RUNS, auth=None, headers={"Cookie": f"spike_session={sid}"})
        ok("the cookie opens the run's routes", status == 200, f"{status}")
        status, _, _ = curl(base, RUNS, auth=None, headers={"Cookie": "spike_session=not-a-session"})
        ok("a made-up cookie is refused", status == 401, f"{status}")

        # -- the run and its listing ----------------------------------------------------
        status, _, body = curl(base, RUNS)
        run = json.loads(body) if status == 200 else {}
        ok("the run's JSON: id, name, state", run.get("id") == "demo" and run.get("name") == "Demo run" and run.get("state") == "succeeded", body[:120].decode("utf-8", "replace"))

        status, _, body = curl(base, RESULTS)
        results = json.loads(body) if status == 200 else {}
        names = sorted(e["name"] for e in results.get("entries", []))
        ok("the listing: one entry per file", names == ["big.bin", "document.pdf", "gradient.png", "image.ome.zarr", "multi-channel.ome.tif", "multiqc_report.html", "table.csv"], str(names))
        ok("the listing: the report, found and titled", results.get("reports") == [{"path": "multiqc_report.html", "title": "MultiQC report", "group": None}], str(results.get("reports")))
        ok("the listing: the root it answers with", results.get("root") == "/home/demo/runs/demo/results", str(results.get("root")))

        status, _, _ = curl(base, RESULTS + "?path=no-such-dir")
        ok("a missing folder below the root: 404", status == 404, f"{status}")

        # -- stat -------------------------------------------------------------------------
        status, _, body = curl(base, RESULTS + "/stat/table.csv")
        stat = json.loads(body) if status == 200 else {}
        size = os.path.getsize(os.path.join(data, "table.csv"))
        ok("stat table.csv: file, its size", stat.get("type") == "file" and stat.get("size") == size, body[:120].decode("utf-8", "replace"))
        status, _, body = curl(base, RESULTS + "/stat/image.ome.zarr")
        stat = json.loads(body) if status == 200 else {}
        ok("stat image.ome.zarr: a dir", stat.get("type") == "dir", body[:120].decode("utf-8", "replace"))
        status, _, body = curl(base, RESULTS + "/stat/missing.txt")
        ok("stat a missing file: 404, a problem", status == 404 and body.decode().startswith('{"type": "/problems/'), f"{status} {body[:60]}")
        status, _, body = curl(base, RESULTS + "/stat/../../etc/passwd", as_is=True)
        ok("stat a .. path: 422, refused", status == 422, f"{status}")

        # -- text --------------------------------------------------------------------------
        status, headers, body = curl(base, RESULTS + "/text/table.csv")
        ok("text table.csv: 200, text/plain, no-store", status == 200 and headers.get("content-type", "").startswith("text/plain") and headers.get("cache-control") == "no-store", f"{status} {headers.get('content-type')}")
        ok("text table.csv: the file's bytes", body == open(os.path.join(data, "table.csv"), "rb").read(), f"{len(body)} bytes")
        ok("text table.csv: the sandbox CSP", headers.get("content-security-policy") == "sandbox; default-src 'none'", headers.get("content-security-policy"))
        status, headers, body = curl(base, RESULTS + "/text/table.csv?tail=10")
        ok("text with a small tail: the last 10 bytes", status == 200 and body == open(os.path.join(data, "table.csv"), "rb").read()[-10:], body[-24:].decode("utf-8", "replace"))
        status, headers, body = curl(base, RESULTS + "/text/table.csv", headers={"Range": "bytes=0-9"})
        ok("text with a range: 206 with Content-Range", status == 206 and headers.get("content-range", "").startswith("bytes 0-9/"), f"{status} {headers.get('content-range')}")
        ok("text with a range: those bytes", body == open(os.path.join(data, "table.csv"), "rb").read()[:10], body.decode("utf-8", "replace"))
        status, _, _ = curl(base, RESULTS + "/text/table.csv", headers={"Range": f"bytes=999999999-" })
        ok("text with a range past the end: 422", status == 422, f"{status}")
        status, _, body = curl(base, RESULTS + "/text/document.pdf")
        ok("text of a binary: 415, a problem", status == 415 and body.decode().startswith('{"type": "/problems/'), f"{status}")

        # -- raw: an image --------------------------------------------------------------------
        png = open(os.path.join(data, "gradient.png"), "rb").read()
        status, headers, body = curl(base, RESULTS + "/raw/gradient.png?as=image", headers={"Sec-Fetch-Dest": "image"})
        ok("raw as=image with Sec-Fetch-Dest: image: 200, image/png", status == 200 and headers.get("content-type") == "image/png", f"{status} {headers.get('content-type')}")
        ok("raw as=image: the file's bytes, signature checked", body == png, f"{len(body)} of {len(png)}")
        ok("raw as=image: Vary: Sec-Fetch-Dest", headers.get("vary") == "Sec-Fetch-Dest", headers.get("vary"))
        status, headers, body = curl(base, RESULTS + "/raw/gradient.png?as=image")
        ok("raw as=image without the dest header: an attachment", status == 200 and headers.get("content-type") == "application/octet-stream" and "attachment" in headers.get("content-disposition", ""), f"{status} {headers.get('content-type')} {headers.get('content-disposition')}")
        status, _, _ = curl(base, RESULTS + "/raw/gradient.png", headers={"Sec-Fetch-Dest": "script"})
        ok("raw to a script: 422", status == 422, f"{status}")
        status, _, body = curl(base, RESULTS + "/raw/table.csv?as=image", headers={"Sec-Fetch-Dest": "image"})
        ok("raw as=image of a non-image: an attachment", status == 200 and "attachment" in curl(base, RESULTS + "/raw/table.csv?as=image", headers={"Sec-Fetch-Dest": "image"})[1].get("content-disposition", ""), f"{status}")

        # -- raw: a TIFF, one closed range -------------------------------------------------------
        # the imaging reads are fetches: the browser sends Sec-Fetch-Dest: empty, and so does curl here
        tif = open(os.path.join(data, "multi-channel.ome.tif"), "rb").read()
        status, headers, body = curl(base, RESULTS + "/raw/multi-channel.ome.tif?as=tiff", headers={"Range": "bytes=0-15", "Sec-Fetch-Dest": "empty"})
        ok("raw as=tiff with a closed range: 206 with Content-Range", status == 206 and headers.get("content-range") == f"bytes 0-15/{len(tif)}", f"{status} {headers.get('content-range')}")
        ok("raw as=tiff: those bytes, the TIFF head", body == tif[:16] and body[:4] == b"II*\x00", body[:4].decode("latin-1"))
        ok("raw as=tiff: Accept-Ranges: bytes", headers.get("accept-ranges") == "bytes", headers.get("accept-ranges"))
        status, _, _ = curl(base, RESULTS + "/raw/multi-channel.ome.tif?as=tiff", headers={"Sec-Fetch-Dest": "empty"})
        ok("raw as=tiff without a range: 422", status == 422, f"{status}")
        status, _, _ = curl(base, RESULTS + "/raw/multi-channel.ome.tif?as=tiff", headers={"Range": "bytes=15-0", "Sec-Fetch-Dest": "empty"})
        ok("raw as=tiff with a reversed range: 422", status == 422, f"{status}")
        status, _, _ = curl(base, RESULTS + "/raw/gradient.png?as=tiff", headers={"Range": "bytes=0-15", "Sec-Fetch-Dest": "empty"})
        ok("raw as=tiff of a PNG: 422, not the TIFF its name says", status == 422, f"{status}")

        # -- raw: a Zarr key -------------------------------------------------------------------
        zattrs = open(os.path.join(data, "image.ome.zarr", ".zattrs"), "rb").read()
        status, headers, body = curl(base, RESULTS + "/raw/image.ome.zarr/.zattrs?as=zarr", headers={"Sec-Fetch-Dest": "empty"})
        ok("raw as=zarr of a key, whole: 200", status == 200 and body == zattrs, f"{status} {len(body)} of {len(zattrs)}")
        zarray = open(os.path.join(data, "image.ome.zarr", "0", ".zarray"), "rb").read()
        status, headers, body = curl(base, RESULTS + "/raw/image.ome.zarr/0/.zarray?as=zarr", headers={"Range": "bytes=0-15", "Sec-Fetch-Dest": "empty"})
        ok("raw as=zarr of a key, ranged: 206 with Content-Range", status == 206 and body == zarray[:16] and headers.get("content-range") == f"bytes 0-15/{len(zarray)}", f"{status} {headers.get('content-range')}")
        chunk = open(os.path.join(data, "image.ome.zarr", "0", "0.0.0"), "rb").read()
        status, _, body = curl(base, RESULTS + "/raw/image.ome.zarr/0/0.0.0?as=zarr", headers={"Sec-Fetch-Dest": "empty"})
        ok("raw as=zarr of a chunk: the file's bytes", status == 200 and body == chunk, f"{status} {len(body)} of {len(chunk)}")
        status, _, _ = curl(base, RESULTS + "/raw/image.ome.zarr/0/evil%20key?as=zarr", headers={"Sec-Fetch-Dest": "empty"})
        ok("raw as=zarr of a key that is not there: 404", status == 404, f"{status}")
        status, _, _ = curl(base, RESULTS + "/raw/image.ome.zarr/0/not%20a%20key?as=zarr", headers={"Sec-Fetch-Dest": "empty"})
        ok("raw as=zarr of a key that is not a key: 422", status == 422, f"{status}")

        # -- raw: the report and the PDF ---------------------------------------------------------
        status, headers, body = curl(base, RESULTS + "/raw/multiqc_report.html")
        ok("raw of the report: 200, text/html", status == 200 and headers.get("content-type", "").startswith("text/html"), f"{status} {headers.get('content-type')}")
        ok("raw of the report: the sandbox report CSP", headers.get("content-security-policy", "").startswith("sandbox allow-scripts allow-downloads; default-src 'none'"), headers.get("content-security-policy", "")[:60])
        pdf = open(os.path.join(data, "document.pdf"), "rb").read()
        status, headers, body = curl(base, RESULTS + "/raw/document.pdf")
        ok("raw of the PDF: 200, application/pdf, inline (the demo's difference)", status == 200 and headers.get("content-type") == "application/pdf" and "attachment" not in headers.get("content-disposition", ""), f"{status} {headers.get('content-type')}")
        ok("raw of the PDF: the file's bytes", body == pdf, f"{len(body)} of {len(pdf)}")
        status, headers, body = curl(base, RESULTS + "/raw/table.csv")
        ok("raw of a plain file: an attachment", status == 200 and headers.get("content-type") == "application/octet-stream" and headers.get("content-disposition", "").startswith("attachment"), f"{status}")
        status, _, _ = curl(base, RESULTS + "/raw/missing.bin")
        ok("raw of a missing file: 404", status == 404, f"{status}")

        # -- a file over 8 MiB: several runner commands -------------------------------------------
        big_path = os.path.join(data, "big.bin")
        big = open(big_path, "rb").read()
        digest = hashlib.sha256(big).hexdigest()
        status, headers, _ = curl(base, RESULTS + "/raw/big.bin", out=body_file)
        served = open(body_file, "rb").read()
        ok("raw of big.bin, 9 MiB: 200, the whole file", status == 200 and headers.get("content-length") == str(len(big)) and hashlib.sha256(served).hexdigest() == digest, f"{status} {len(served)} of {len(big)}")

        # -- the static UI, through the runner ------------------------------------------------------
        html = open(os.path.join(root, "ui", "demo.html"), "rb").read()
        status, headers, body = curl(base, "/")
        ok("GET /: the demo page, text/html", status == 200 and headers.get("content-type") == "text/html; charset=utf-8" and body == html, f"{status} {headers.get('content-type')}")
        asset = sorted(os.listdir(os.path.join(root, "ui", "assets")))[0]
        js = open(os.path.join(root, "ui", "assets", asset), "rb").read()
        status, headers, body = curl(base, f"/assets/{asset}")
        ok("GET /assets/…: served with its type", status == 200 and headers.get("content-type", "").startswith("text/javascript") and body == js, f"{status} {headers.get('content-type')}")
        status, _, _ = curl(base, "/../etc/passwd", as_is=True)
        ok("a traversal path under ui/: 404", status == 404, f"{status}")

        # -- the runner's own view --------------------------------------------------------------------
        status, _, body = curl(base, "/api/runner")
        info = json.loads(body) if status == 200 else {}
        ok("the runner is connected", status == 200 and info.get("host") and info.get("ago", 99) < 60, body.decode("utf-8", "replace")[:80])

        # the runner's own log lines are counted once it is stopped, below
    finally:
        runner.terminate()
        runner.wait(timeout=10)
        server.terminate()
        server.wait(timeout=10)
        log = runner.stdout.read().decode("utf-8", "replace")
        served_log = server.stdout.read().decode("utf-8", "replace")
        if os.path.exists(root):
            shutil.rmtree(root, ignore_errors=True)

    big_reads = [l for l in log.split("\n") if "file 'data/big.bin'" in l]
    ok("big.bin, 9 MiB, was read in several runner commands", len(big_reads) == 2, f"{len(big_reads)} commands")
    ok("every runner read was at most 8 MiB + 1", all(int(m.group(1)) <= 8 * 1024 * 1024 + 1 for m in (re.search(r"-> 200 (\d+) B", l) for l in big_reads) if m), "")
    print(f"\n{checks - len(failures)}/{checks} checks passed" + (f"; failures: {failures}" if failures else ""))
    if failures:
        print("\n--- runner log (tail) ---")
        print("\n".join(log.split("\n")[-12:]))
        print("\n--- server log (tail) ---")
        print("\n".join(served_log.split("\n")[-12:]))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
