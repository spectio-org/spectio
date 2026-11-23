"""A demo server for the shots of batch P3-B14: the Catalog page, an OME-TIFF in the image viewer, the
Environments table view, and the Profile page.

Like `b13_demo.py`, this seeds the store of a throwaway `spectio` server and serves the built screens
(`web/dist`: run `npx vite build` in `web/` first) on a loopback port, then runs `shots.py` against it.
No Nextflow or Snakemake is needed. It seeds:

- `catalog.toml` with three entries, for the Catalog page and its entry form (FU-P3-87d);
- `environments.toml` with `two-cores` (the default) and `eight-cores` beside the built-in `local`, for the
  cards and table views and for Duplicate to edit (FU-P3-111);
- one finished run whose results hold `imaging/cells.ome.tif`, a tiled, uncompressed OME-TIFF of three
  16-bit channels written by hand, for the image viewer and its channel list (FU-P3-102e, -102f), and
  whose file page shows the breadcrumb of FU-P3-104;
- the Profile page (FU-P3-112) needs nothing: the server answers it from its own settings.

    .venv/bin/python tools/media/b14_demo.py [--shot app-catalog ...]

Run it from the repository root with the checkout's `.venv` (it imports `spectio_server`) and a Playwright
that finds Chromium (`PLAYWRIGHT_BROWSERS_PATH`). The paths are under `/srv/demo-b14`, the home directory
is `/srv/demo-b14/home`, and the sidebar and the Profile page name `demo-hpc-login1` and `alice`, so that
no host detail shows on a page (`fixtures.yaml`, `forbidden`).
"""

import argparse
import os
import shutil
import struct
import subprocess
import sys
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import tiff_demo
import uvicorn
from sqlalchemy import update

from spectio.config import Settings, write_config
from spectio.runner.rundir import RunManifest, Workflow, make_run_dirs
from spectio_server.api import me
from spectio_server.app import create_app
from spectio_server.auth.middleware import cookie_name
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.store.db import open_db
from spectio_server.store.runs import insert_run
from spectio_server.store.schema import runs
from spectio_server.store.writer import Writer

REPO = Path(__file__).resolve().parents[2]
ROOT = Path("/srv/demo-b14")
IMAGING = "run_01K8T2F1XTVRB14RZ000000000"
SHOTS = (
    "app-catalog",
    "app-catalog-entry",
    "app-environments-table",
    "app-environment-duplicate",
    "app-file-preview-ome-tiff",
    "app-profile",
    "app-profile-phone",
)
CATALOG = """\
[pipelines.rnaseq-test]
label = "RNA-seq test"
engine = "nextflow"
location = "/srv/demo-b14/pipelines/synthetic-rnaseq"
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
location = "/srv/demo-b14/pipelines/liver-qc"
"""
ENVIRONMENTS = """\
default = "two-cores"

[environments.two-cores]
label = "Two cores"
executor = "local"

[environments.two-cores.local]
cpus = 2
mem_mib = 4096

[environments.eight-cores]
label = "Eight cores"
executor = "local"

[environments.eight-cores.local]
cpus = 8
mem_mib = 16384
"""
TILE = 128  # 512 x 384 is 4 x 3 tiles
NAMES = (("DAPI", 0x0000FFFF), ("GFP", 0x00FF00FF), ("Actin", 0xFF00FFFF))


def signed(rgba: int) -> int:
    """OME-XML writes the colour as a signed 32-bit integer."""
    return rgba - (1 << 32) if rgba >= 1 << 31 else rgba


def ome_xml() -> str:
    channels = "".join(
        f'<Channel ID="Channel:0:{i}" Name="{name}" SamplesPerPixel="1" Color="{signed(rgba)}"/>'
        for i, (name, rgba) in enumerate(NAMES)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06">'
        '<Image ID="Image:0" Name="cells">'
        f'<Pixels ID="Pixels:0" DimensionOrder="XYCZT" Type="uint16" SizeX="{tiff_demo.W}" SizeY="{tiff_demo.H}" '
        f'SizeZ="1" SizeC="{len(NAMES)}" SizeT="1">{channels}<TiffData IFD="0" PlaneCount="{len(NAMES)}"/></Pixels>'
        "</Image></OME>"
    )


def planes() -> list[bytes]:
    """Three channels from the blobs of `tiff_demo`: as they are, flipped top to bottom, rolled by 100 columns."""
    w, h = tiff_demo.W, tiff_demo.H
    first = tiff_demo.cells()
    rows = [first[y * w * 2 : (y + 1) * w * 2] for y in range(h)]
    return [first, b"".join(reversed(rows)), b"".join(r[200:] + r[:200] for r in rows)]


def ome_tiff(path: Path) -> None:
    """A little-endian OME-TIFF: three 16-bit grayscale planes (one IFD each), 128-pixel tiles, no
    compression, the OME-XML in the first IFD's ImageDescription."""
    w, h = tiff_demo.W, tiff_demo.H
    buf = bytearray(b"II*\x00\x00\x00\x00\x00")
    link = 4  # where the previous IFD's "next IFD" offset sits
    for i, plane in enumerate(planes()):
        tiles = []
        for ty in range(h // TILE):
            for tx in range(w // TILE):
                tiles.append(b"".join(plane[((ty * TILE + y) * w + tx * TILE) * 2 :][: TILE * 2] for y in range(TILE)))
        offsets, counts = [], []
        for tile in tiles:
            offsets.append(len(buf))
            counts.append(len(tile))
            buf += tile
        offsets_at, counts_at = len(buf), len(buf) + 4 * len(tiles)
        buf += struct.pack(f"<{len(tiles)}I", *offsets) + struct.pack(f"<{len(tiles)}I", *counts)
        description = (ome_xml().encode() + b"\x00") if i == 0 else b""
        description_at = len(buf)
        buf += description + (b"\x00" if len(description) % 2 else b"")
        short = lambda tag, value: struct.pack("<HHIHH", tag, 3, 1, value, 0)  # noqa: E731
        entries = [short(256, w), short(257, h), short(258, 16), short(259, 1), short(262, 1)]
        if description:
            entries.append(struct.pack("<HHII", 270, 2, len(description), description_at))
        entries += [short(277, 1), short(322, TILE), short(323, TILE)]
        entries += [struct.pack("<HHII", 324, 4, len(tiles), offsets_at), struct.pack("<HHII", 325, 4, len(tiles), counts_at)]
        entries.append(short(339, 1))
        ifd_at = len(buf)
        struct.pack_into("<I", buf, link, ifd_at)
        buf += struct.pack("<H", len(entries)) + b"".join(entries) + struct.pack("<I", 0)
        link = ifd_at + 2 + 12 * len(entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(buf))


@contextmanager
def running():
    """A seeded server on a loopback port; yields (the environment for `shots.py`, the port)."""
    tiff_demo.demo_identity()
    me.pwd = SimpleNamespace(getpwuid=lambda uid: SimpleNamespace(pw_name="alice"))  # the Profile page's account
    shutil.rmtree(ROOT, ignore_errors=True)
    data_dir, db_dir, runs_root, home = ROOT / "data", ROOT / "db", ROOT / "runs", ROOT / "home"
    for p in (data_dir, db_dir, runs_root, home):
        p.mkdir(parents=True, mode=0o700)
    os.environ["HOME"] = str(home)  # Path.home() names the observed runs directory
    os.environ["SPECTIO_CONFIG"] = str(data_dir / "spectio.toml")
    port = tiff_demo.free_port()
    settings = Settings(data_dir=data_dir, db_dir=db_dir, runs_root=runs_root, port=port, executor="local")
    write_config(settings)
    for name, text in (("catalog.toml", CATALOG), ("environments.toml", ENVIRONMENTS)):
        (data_dir / name).write_text(text)
        (data_dir / name).chmod(0o600)
    engine, _ = open_db(db_dir)
    writer = Writer(engine)
    writer.submit(lambda c: ensure_tenancy(c, "me", settings.executor, {"runs_root": str(runs_root)}, "0.0.1")).result()
    paths = make_run_dirs(runs_root, IMAGING)
    results = paths.launch_dir / "results"
    ome_tiff(results / "imaging" / "cells.ome.tif")
    manifest = RunManifest(
        run_id=IMAGING, name="demo-imaging", params={}, profiles=[], created_at=datetime.now(UTC),
        workflow=Workflow.model_validate({"location": "/pipelines/demo-imaging", "engine": "nextflow"}),
    )

    def seed(conn):
        insert_run(conn, manifest, source="local", runs_root=runs_root, now=manifest.created_at,
                   state="succeeded", origin="ui", workflow_name="demo-lab/imaging", workflow_version="1.0.0")
        conn.execute(update(runs).where(runs.c.id == IMAGING).values(results_dir=str(results)))

    writer.submit(seed).result()
    app = create_app(settings, writer, web_dir=REPO / "web" / "dist")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, lifespan="off", log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        threading.Event().wait(0.05)
    env = {
        **os.environ,
        "SPECTIO_URL": f"http://127.0.0.1:{port}",
        "SPECTIO_DEMO_RUN": IMAGING,
        "SPECTIO_SESSION_COOKIE": f"{cookie_name(f'127.0.0.1:{port}')}={app.state.sessions.create()}",
    }
    try:
        yield env, port
    finally:
        server.should_exit = True
        writer.close()
        engine.dispose()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--shot", action="append", choices=SHOTS)
    wanted = set(ap.parse_args().shot or SHOTS)
    with running() as (env, _):
        for shot in (s for s in SHOTS if s in wanted):  # the names come from SHOTS, not from argv
            subprocess.run([sys.executable, str(REPO / "tools/media/shots.py"), "run", "--shot", shot, "--theme", "both"],
                           check=True, env=env, cwd=REPO)


if __name__ == "__main__":
    main()
