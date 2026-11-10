"""A demo server with one finished run and one TIFF in its results, for the TIFF flat-view shots.

The TIFF screens need a file, not a pipeline: this script seeds the store of a throwaway
`spectio` server (the run record and `results/imaging/cells.tif`, written by hand as a
`publishDir` would), serves the built screens (`web/dist`: run `npx vite build` in `web/`
first) on a loopback port, and runs `shots.py` against it. No Nextflow or Snakemake is needed.

    .venv/bin/python tools/media/tiff_demo.py [--shot app-file-preview-tiff ...]

Run it from the repository root with the checkout's `.venv` (it imports `spectio_server`)
and a Playwright that finds Chromium (`PLAYWRIGHT_BROWSERS_PATH`). The runs root is
`/srv/demo-tiff` and the node and account the sidebar names are `demo-hpc-login1` and `alice`, so that
no host detail shows on the page (`fixtures.yaml`, `forbidden`).
"""

import argparse
import math
import os
import shutil
import socket
import struct
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import uvicorn
from sqlalchemy import update

from spectio.config import Settings, write_config
from spectio.runner.rundir import RunManifest, Workflow, make_run_dirs
from spectio_server.api import runs_read
from spectio_server.app import create_app
from spectio_server.auth.middleware import cookie_name
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.store.db import open_db
from spectio_server.store.runs import insert_run
from spectio_server.store.schema import runs
from spectio_server.store.writer import Writer

REPO = Path(__file__).resolve().parents[2]
ROOT = Path("/srv/demo-tiff")
RUN = "run_01K8T2F1XTVRTEFF0000000000"
W, H, ROWS = 512, 384, 16  # a 16-bit grayscale plane in strips of 16 rows


def cells() -> bytes:
    """Gaussian blobs of 700 to 2,600 on a dim floor: 16-bit, so the page stretches the contrast."""
    seed, blobs = 7, []
    for _ in range(30):  # a fixed pseudo-random scatter, the same file every run
        seed = seed * 1103515245 + 12345 & 0x7FFFFFFF
        bx = 30 + seed % (W - 60)
        seed = seed * 1103515245 + 12345 & 0x7FFFFFFF
        by = 30 + seed % (H - 60)
        seed = seed * 1103515245 + 12345 & 0x7FFFFFFF
        blobs.append((bx, by, 8 + seed % 9, 900 + 190 * (seed >> 8) % 1800))
    out = bytearray()
    for y in range(H):
        for x in range(W):
            v = 300 + 40 * math.sin(x / 23) * math.cos(y / 31)
            for bx, by, r, peak in blobs:
                d = ((x - bx) ** 2 + (y - by) ** 2) / (2 * r * r)
                if d < 12:
                    v += peak * math.exp(-d)
            out += struct.pack("<H", min(int(v), 65535))
    return bytes(out)


def tiff(path: Path) -> None:
    """A little-endian TIFF: one 16-bit grayscale image, no compression, strips of 16 rows."""
    data = cells()
    strips = [data[i : i + ROWS * W * 2] for i in range(0, len(data), ROWS * W * 2)]
    n = len(strips)
    entries = 9
    ifd_at = 8
    arrays_at = ifd_at + 2 + entries * 12 + 4
    offsets_at, counts_at = arrays_at, arrays_at + 4 * n
    data_at = counts_at + 4 * n
    tags = [  # (tag, type, count, value); type 3 SHORT, 4 LONG
        (256, 3, 1, W), (257, 3, 1, H), (258, 3, 1, 16), (259, 3, 1, 1), (262, 3, 1, 1),
        (273, 4, n, offsets_at), (277, 3, 1, 1), (278, 3, 1, ROWS), (279, 4, n, counts_at),
    ]
    body = b"II*\x00" + struct.pack("<I", ifd_at) + struct.pack("<H", entries)
    for tag, kind, count, value in tags:
        body += struct.pack("<HHII", tag, kind, count, value)
    body += struct.pack("<I", 0)
    body += b"".join(struct.pack("<I", data_at + i * ROWS * W * 2) for i in range(n))
    body += b"".join(struct.pack("<I", len(s)) for s in strips)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body + data)


def demo_identity() -> None:
    """The sidebar names the server's node and account: show demo-hpc-login1 and alice, not the capture host's."""
    runs_read.socket = SimpleNamespace(gethostname=lambda: "demo-hpc-login1")
    runs_read.pwd = SimpleNamespace(getpwuid=lambda uid: SimpleNamespace(pw_name="alice"))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


SHOTS = ("app-file-preview-tiff", "app-file-preview-tiff-phone")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--shot", action="append", choices=SHOTS)
    args = ap.parse_args()
    wanted = set(args.shot or SHOTS)
    demo_identity()
    shutil.rmtree(ROOT, ignore_errors=True)
    data_dir, db_dir, runs_root = ROOT / "data", ROOT / "db", ROOT / "runs"
    for p in (data_dir, db_dir, runs_root):
        p.mkdir(parents=True, mode=0o700)
    os.environ["SPECTIO_CONFIG"] = str(data_dir / "spectio.toml")
    port = free_port()
    settings = Settings(data_dir=data_dir, db_dir=db_dir, runs_root=runs_root, port=port, executor="local")
    write_config(settings)
    engine, _ = open_db(db_dir)
    writer = Writer(engine)
    writer.submit(lambda c: ensure_tenancy(c, "me", settings.executor, {"runs_root": str(runs_root)}, "0.0.1")).result()
    paths = make_run_dirs(runs_root, RUN)
    results = paths.launch_dir / "results"
    tiff(results / "imaging" / "cells.tif")
    manifest = RunManifest(
        run_id=RUN, name="demo-imaging", params={}, profiles=[], created_at=datetime.now(UTC),
        workflow=Workflow.model_validate({"location": "/pipelines/demo-imaging", "engine": "nextflow"}),
    )

    def seed(conn):
        insert_run(conn, manifest, source="local", runs_root=runs_root, now=manifest.created_at,
                   state="succeeded", origin="ui", workflow_name="demo-lab/imaging", workflow_version="1.0.0")
        conn.execute(update(runs).where(runs.c.id == RUN).values(results_dir=str(results)))

    writer.submit(seed).result()
    app = create_app(settings, writer, web_dir=REPO / "web" / "dist")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, lifespan="off", log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        threading.Event().wait(0.05)
    env = {
        **os.environ,
        "SPECTIO_URL": f"http://127.0.0.1:{port}",
        "SPECTIO_DEMO_RUN": RUN,
        "SPECTIO_SESSION_COOKIE": f"{cookie_name(f'127.0.0.1:{port}')}={app.state.sessions.create()}",
    }
    try:
        for shot in (s for s in SHOTS if s in wanted):  # the names come from SHOTS, not from argv
            subprocess.run([sys.executable, str(REPO / "tools/media/shots.py"), "run", "--shot", shot, "--theme", "both"],
                           check=True, env=env, cwd=REPO)
    finally:
        server.should_exit = True
        writer.close()
        engine.dispose()


if __name__ == "__main__":
    main()
