"""A demo server for the shots of batch P3-B13: the catalog on Launch, the AG Grid tables, an OME-Zarr.

Like `tiff_demo.py`, this seeds the store of a throwaway `spectio` server and serves the built screens
(`web/dist`: run `npx vite build` in `web/` first) on a loopback port, then runs `shots.py` against it.
No Nextflow or Snakemake is needed. It seeds:

- `catalog.toml` with three entries (a directory, a Git repository, a Snakemake workflow) and a copy of
  the synthetic Nextflow pipeline with `conf/test.yaml`, for the catalog picker on Launch (FU-P3-87e);
- seven finished, failed and running run records, for the runs list in AG Grid (FU-P3-101a);
- one finished run whose results hold `quant/counts_matrix.tsv` (30 rows, so the grid scrolls inside its
  frame) and `imaging/cells.ome.zarr`, a Zarr v2 OME-Zarr with two channels and two levels of raw and
  zlib chunks, for the table preview and the OME-Zarr viewer (FU-P3-102g).

    .venv/bin/python tools/media/b13_demo.py [--shot app-launch-catalog ...]

Run it from the repository root with the checkout's `.venv` (it imports `spectio_server`) and a Playwright
that finds Chromium (`PLAYWRIGHT_BROWSERS_PATH`). The paths are under `/srv/demo-b13`, and the sidebar names
`demo-hpc-login1` and `alice`, so that no host detail shows on the page (`fixtures.yaml`, `forbidden`).
"""

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import threading
import zlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import tiff_demo
import uvicorn
from sqlalchemy import update

from spectio.config import Settings, write_config
from spectio.runner.rundir import RunManifest, Workflow, make_run_dirs
from spectio_server.app import create_app
from spectio_server.auth.middleware import cookie_name
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.store.db import open_db
from spectio_server.store.runs import insert_run
from spectio_server.store.schema import runs
from spectio_server.store.writer import Writer

REPO = Path(__file__).resolve().parents[2]
ROOT = Path("/srv/demo-b13")
SYNTH = REPO / "tests/pipelines/synthetic"
IMAGING = "run_01K8T2F1XTVRB13RZ000000000"
LOGGED = "run_01K8T2F1XTVRB13R0000000000"  # the first of RUNS: its launch directory holds an engine log
ENGINE_LOG = """\
Nov-10 16:01:02.413 [main] INFO  nextflow.cli.CmdRun - Launching `main.nf` [treatA-ctrl] DSL2 - revision: 1.0.0
Nov-10 16:01:03.007 [main] INFO  nextflow.Session - Session UUID: 5d2e8c7a-0c1b-4f2e-9a43-6a1e3f0b7c11
Nov-10 16:01:03.512 [main] INFO  nextflow.executor.Executor - [warm up] executor > local
Nov-10 16:01:04.118 [Actor Thread 4] INFO  nextflow.Session - [3f/a1c20e] Submitted process > SPLIT (treatA_1)
Nov-10 16:01:09.640 [Actor Thread 9] INFO  nextflow.Session - [8b/04d7c1] Submitted process > ALIGN (treatA_1)
Nov-10 16:01:15.221 [Actor Thread 2] INFO  nextflow.Session - [c0/71e9aa] Submitted process > QC (treatA_1)
Nov-10 16:01:21.874 [Actor Thread 7] INFO  nextflow.Session - [e2/9b3f10] Submitted process > MERGE
Nov-10 16:01:27.309 [main] INFO  nextflow.Session - Workflow completed, 65 of 65 tasks succeeded
Nov-10 16:01:27.355 [main] DEBUG nextflow.Session - Session destroyed
"""
SHOTS = (
    "app-launch-catalog",
    "app-launch-catalog-manage",
    "app-runs-grid",
    "app-file-preview-grid",
    "app-file-preview-zarr",
    "app-file-preview-zarr-phone",  # FU-P3-102i, taken in batch P3-B16
    "app-run-engine-log",
)
CATALOG = """\
[pipelines.rnaseq-test]
label = "RNA-seq test"
engine = "nextflow"
location = "{pipeline}"
profile = "test"
params_file = "conf/test.yaml"

[pipelines.nf-core-rnaseq]
engine = "nextflow"
location = "nf-core/rnaseq"
revision = "3.27.0"
profile = "test"

[pipelines.liver-qc]
label = "Liver QC"
engine = "snakemake"
location = "/srv/demo-b13/pipelines/liver-qc"
"""
# (name, pipeline, engine, state, minutes ago, origin)
RUNS = [
    ("rnaseq-treatA-ctrl", "demo-lab/rnaseq", "nextflow", "succeeded", 35, "ui"),
    ("rnaseq-treatB-ctrl", "demo-lab/rnaseq", "nextflow", "running", 12, "ui"),
    ("liver-qc-batch-7", "demo-lab/liver-qc", "snakemake", "succeeded", 190, "ui"),
    ("rnaseq-treatC-ctrl", "demo-lab/rnaseq", "nextflow", "failed", 340, "ui"),
    ("liver-qc-batch-6", "demo-lab/liver-qc", "snakemake", "succeeded", 1500, "ui"),
    ("rnaseq-pilot", "demo-lab/rnaseq", "nextflow", "cancelled", 2900, "ui"),
    ("demo-imaging", "demo-lab/imaging", "nextflow", "succeeded", 4300, "ui"),
]


def counts_matrix() -> str:
    """Thirty samples: total reads, mapped reads and three rates, from a fixed formula."""
    rows = ["sample\ttotal\tmapped\tmapped_rate\tduplicate_rate\tgc_content"]
    for i in range(30):
        total = 1_200_000 + (i * 137_413) % 900_000
        rate = 0.90 + ((i * 7) % 9) / 100
        rows.append(
            f"{'ctrl' if i < 15 else 'treatA'}_{i % 15 + 1}\t{total}\t{int(total * rate)}\t{rate:.2f}"
            f"\t{0.05 + (i % 6) / 100:.2f}\t{0.44 + (i % 5) / 100:.2f}"
        )
    return "\n".join(rows) + "\n"


def ome_zarr(folder: Path) -> None:
    """A Zarr v2 OME-Zarr (NGFF 0.4, axes c, y, x, uint16): two channels of the blobs of `tiff_demo`,
    level 0 in raw chunks, level 1 at half size in zlib chunks (no Blosc: the page refuses it)."""
    folder.mkdir(parents=True)
    w, h = tiff_demo.W, tiff_demo.H
    first = tiff_demo.cells()
    rows = [first[y * w * 2 : (y + 1) * w * 2] for y in range(h)]
    planes = [first, b"".join(reversed(rows))]  # channel 2: the same field, flipped top to bottom
    axes = [{"name": "c", "type": "channel"}, {"name": "y", "type": "space"}, {"name": "x", "type": "space"}]
    attrs = {
        "multiscales": [{"version": "0.4", "axes": axes, "datasets": [{"path": "0"}, {"path": "1"}]}],
        "omero": {"channels": [{"label": "DAPI", "color": "0000FF"}, {"label": "GFP", "color": "00FF00"}]},
    }
    (folder / ".zgroup").write_text(json.dumps({"zarr_format": 2}))
    (folder / ".zattrs").write_text(json.dumps(attrs))
    for level, compressor in enumerate((None, {"id": "zlib", "level": 1})):
        lw, lh = w >> level, h >> level
        (folder / str(level)).mkdir()
        meta = {"zarr_format": 2, "shape": [2, lh, lw], "chunks": [1, lh, lw], "dtype": "<u2"}
        meta |= {"compressor": compressor, "fill_value": 0, "order": "C", "filters": None}
        (folder / str(level) / ".zarray").write_text(json.dumps(meta))
        for c, plane in enumerate(planes):
            pixels = struct.unpack(f"<{w * h}H", plane)
            half = [pixels[(y << level) * w + (x << level)] for y in range(lh) for x in range(lw)]
            data = struct.pack(f"<{lw * lh}H", *half)
            (folder / str(level) / f"{c}.0.0").write_bytes(data if compressor is None else zlib.compress(data))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--shot", action="append", choices=SHOTS)
    wanted = set(ap.parse_args().shot or SHOTS)
    tiff_demo.demo_identity()
    shutil.rmtree(ROOT, ignore_errors=True)
    data_dir, db_dir, runs_root = ROOT / "data", ROOT / "db", ROOT / "runs"
    for p in (data_dir, db_dir, runs_root):
        p.mkdir(parents=True, mode=0o700)
    pipeline = ROOT / "pipelines" / "synthetic-rnaseq"
    (ROOT / "pipelines").mkdir()
    for part in ("data", "bin"):  # main.nf reads ../data, and bin/synth.py links to ../../bin
        shutil.copytree(SYNTH / part, ROOT / "pipelines" / part, symlinks=True)
    shutil.copytree(SYNTH / "nextflow", pipeline, symlinks=True)
    (pipeline / "conf" / "test.yaml").write_text("chunks: 2\nscale: 1\nseed: 7\n")
    os.environ["SPECTIO_CONFIG"] = str(data_dir / "spectio.toml")
    port = tiff_demo.free_port()
    settings = Settings(data_dir=data_dir, db_dir=db_dir, runs_root=runs_root, port=port, executor="local")
    write_config(settings)
    catalog = data_dir / "catalog.toml"
    catalog.write_text(CATALOG.format(pipeline=pipeline))
    catalog.chmod(0o600)
    engine, _ = open_db(db_dir)
    writer = Writer(engine)
    writer.submit(lambda c: ensure_tenancy(c, "me", settings.executor, {"runs_root": str(runs_root)}, "0.0.1")).result()
    now = datetime.now(UTC)
    results = None
    for i, (name, flow, eng, state, ago, origin) in enumerate(RUNS):
        run_id = IMAGING if name == "demo-imaging" else f"run_01K8T2F1XTVRB13R{i:010d}"
        paths = make_run_dirs(runs_root, run_id)
        created = now - timedelta(minutes=ago)
        manifest = RunManifest(
            run_id=run_id, name=name, params={}, profiles=[], created_at=created,
            workflow=Workflow.model_validate({"location": f"/pipelines/{flow.split('/')[1]}", "engine": eng}),
        )

        def seed(conn, manifest=manifest, state=state, origin=origin, flow=flow, created=created):
            insert_run(conn, manifest, source="local", runs_root=runs_root, now=created, state=state,
                       origin=origin, workflow_name=flow, workflow_version="1.0.0")

        writer.submit(seed).result()
        if run_id == LOGGED:
            (paths.launch_dir / ".nextflow.log").write_text(ENGINE_LOG)
        if run_id == IMAGING:
            results = paths.launch_dir / "results"
            (results / "quant").mkdir(parents=True)
            (results / "quant" / "counts_matrix.tsv").write_text(counts_matrix())
            ome_zarr(results / "imaging" / "cells.ome.zarr")
            writer.submit(lambda c: c.execute(update(runs).where(runs.c.id == IMAGING).values(results_dir=str(results)))).result()
    app = create_app(settings, writer, web_dir=REPO / "web" / "dist")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, lifespan="off", log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        threading.Event().wait(0.05)
    env = {
        **os.environ,
        "SPECTIO_URL": f"http://127.0.0.1:{port}",
        "SPECTIO_DEMO_RUN": IMAGING,
        "SPECTIO_DEMO_LOGGED_RUN": LOGGED,
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
