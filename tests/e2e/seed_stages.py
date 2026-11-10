"""Seed a run directory with the rnaseq preview events, for the stages check of the Playwright
smoke (P1 Task 27, Step 4): `spectio serve` adds it to the index at boot (Task 11), adopts its
ended head and replays its spool, and the run shows 8 detected stages above its processes.

    uv run python tests/e2e/seed_stages.py <runs_root>

The events are `tests/pipelines/real/stages/events/rnaseq-3.27.0_star_salmon_preview_events.jsonl`
(onFlowCreate, 67 onProcessCreate, onFlowBegin, onFlowComplete), written as the spool of launch 1
of run SEEDED; head.pid names a head that has ended (no such process) and head.exit says 0.

The run's `params.outdir` is `results`, which holds the reports of `tests/fixtures/results` for the
report viewer's check (P1 Task 31, req. 14): a real MultiQC 1.35 report at
`multiqc/multiqc_report.html` and a hostile one at `hostile/hostile_report.html`; and a hostile SVG
at `hostile/hostile_image.svg` for the file preview's check (FU-P3-85c, api §5.3); and a 200 KiB
`logs/big.log`, over one 64 KiB read, for its Load more focus check; and `imaging/cells.ome.tif`,
a small OME-TIFF (2 channels, 3 Z planes, 64 x 48 px) for the WebGL viewer's CSP check (FU-P3-102e);
and `imaging/cells.ome.zarr`, a Zarr v2 OME-Zarr (2 channels, 64 x 48 px, a Blosc level and a zlib
level) for the same check through the page's Zarr store (FU-P3-102g).
"""

import gzip
import json
import socket
import struct
import sys
import zlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from spectio.runner.rundir import (
    RunManifest,
    Workflow,
    make_run_dirs,
    private_dir,
    write_file,
    write_run_manifest,
)

SEEDED = "run_01K8T27SEEDED0000000000000"
EVENTS = (
    Path(__file__).resolve().parents[1]
    / "pipelines/real/stages/events/rnaseq-3.27.0_star_salmon_preview_events.jsonl"
)
RESULTS = Path(__file__).resolve().parents[1] / "fixtures/results"
T0 = datetime(2026, 10, 28, 7, 0, tzinfo=UTC)


def spool_lines() -> bytes:
    lines = []
    for n, line in enumerate(EVENTS.read_text().splitlines(), 1):
        body = json.loads(line)["body"]
        data = {k: v for k, v in body.items() if k not in ("hook", "instant", "seq")}
        event = {
            "v": 1,
            "id": f"evt_01K8T27SEEDED{n:012d}",
            "run": SEEDED,
            "launch": 1,
            "producer": "nf-spectio/0.0.1",
            "seq": n,
            "time": (T0 + timedelta(seconds=n)).isoformat().replace("+00:00", "Z"),
            "type": f"nextflow.{body['hook']}",
            "data": data,
        }
        lines.append(json.dumps(event) + "\n")
    return "".join(lines).encode()


def ome_zarr(folder: Path, width: int = 64, height: int = 48, channels: int = 2) -> None:
    """A Zarr v2 OME-Zarr (NGFF 0.4, axes c, y, x, uint8): level 0 in Blosc chunks stored as
    memcpyed (header flag 0x02, https://github.com/Blosc/c-blosc/blob/main/README_HEADER.rst),
    so numcodecs' WebAssembly decoder runs; level 1 at half size in zlib chunks."""
    folder.mkdir()
    axes = [
        {"name": "c", "type": "channel"},
        {"name": "y", "type": "space"},
        {"name": "x", "type": "space"},
    ]
    attrs = {
        "multiscales": [
            {"version": "0.4", "axes": axes, "datasets": [{"path": "0"}, {"path": "1"}]}
        ],
        "omero": {
            "channels": [{"label": "DNA", "color": "0000FF"}, {"label": "Actin", "color": "00FF00"}]
        },
    }
    (folder / ".zgroup").write_text(json.dumps({"zarr_format": 2}))
    (folder / ".zattrs").write_text(json.dumps(attrs))
    blosc = {"id": "blosc", "cname": "lz4", "clevel": 5, "shuffle": 0, "blocksize": 0}
    for level, (w, h, compressor) in enumerate(
        [(width, height, blosc), (width // 2, height // 2, {"id": "zlib", "level": 1})]
    ):
        (folder / str(level)).mkdir()
        meta = {"zarr_format": 2, "shape": [channels, h, w], "chunks": [1, h, w], "dtype": "|u1"}
        meta |= {"compressor": compressor, "fill_value": 0, "order": "C", "filters": None}
        (folder / str(level) / ".zarray").write_text(json.dumps(meta))
        for c in range(channels):
            plane = bytes((x * 4 + y * 2 + c * 100) % 256 for y in range(h) for x in range(w))
            n = len(plane)
            chunk = (
                struct.pack("<BBBBIII", 2, 1, 0x02, 1, n, n, 16 + n) + plane
                if level == 0
                else zlib.compress(plane)
            )
            (folder / str(level) / f"{c}.0.0").write_bytes(chunk)


def ome_tiff(width: int = 64, height: int = 48, channels: int = 2, planes: int = 3) -> bytes:
    """A little-endian OME-TIFF, one uncompressed 8-bit strip per plane, Z fastest (XYZCT)."""
    xml = (
        '<?xml version="1.0"?><OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06">'
        '<Image ID="Image:0" Name="cells"><Pixels ID="Pixels:0" DimensionOrder="XYZCT" Type="uint8"'
        f' SizeX="{width}" SizeY="{height}" SizeZ="{planes}" SizeC="{channels}" SizeT="1">'
        + "".join(f'<Channel ID="Channel:0:{c}" SamplesPerPixel="1"/>' for c in range(channels))
        + "<TiffData/></Pixels></Image></OME>\0"
    ).encode()
    count = channels * planes
    pixels = width * height
    out = bytearray(b"II*\0" + struct.pack("<I", 8))
    data_at = 8 + count * (2 + 10 * 12 + 4)
    xml_at = data_at + count * pixels
    for i in range(count):
        tags = [(256, 4, 1, width), (257, 4, 1, height), (258, 3, 1, 8), (259, 3, 1, 1)]
        tags += [(262, 3, 1, 1), (270, 2, len(xml) if i == 0 else 1, xml_at if i == 0 else 0)]
        tags += [(273, 4, 1, data_at + i * pixels), (277, 3, 1, 1), (278, 4, 1, height)]
        tags += [(279, 4, 1, pixels)]
        out += struct.pack("<H", len(tags))
        for tag, kind, n, value in tags:
            out += struct.pack("<HHI", tag, kind, n) + struct.pack(
                "<I" if kind == 4 or n > 1 else "<Hxx", value
            )
        out += struct.pack("<I", len(out) + 4 if i + 1 < count else 0)
    for i in range(count):
        out += bytes((x * 4 + i * 40) % 256 for x in range(pixels))
    return bytes(out + xml)


def main(runs_root: Path) -> None:
    paths = make_run_dirs(runs_root, SEEDED)
    manifest = RunManifest(
        run_id=SEEDED,
        name="rnaseq-stages-seeded",
        workflow=Workflow(location="/pipelines/nf-core-rnaseq", engine="nextflow"),
        params={"outdir": "results"},
        profiles=["test"],
        created_at=T0,
    )
    write_run_manifest(paths.run_dir, manifest)
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    with private_dir(runs_root, SEEDED, "launch", ".spectio", "events") as fd:
        write_file(fd, "nf-spectio-1-0001.jsonl", spool_lines())
    with private_dir(runs_root, SEEDED, "launch", ".spectio") as fd:
        pid = 4194303  # above Linux's default pid_max: never a live process
        host = socket.gethostname()
        write_file(fd, "head.pid", f"{pid} {pid} 1 {boot} {host}\n".encode())
        write_file(fd, "head.exit", f"0 {int(T0.timestamp()) + 90}\n".encode())
    results = paths.launch_dir / "results"
    (results / "multiqc").mkdir(parents=True)
    (results / "hostile").mkdir()
    report = gzip.decompress((RESULTS / "multiqc-1.35_custom_content_report.html.gz").read_bytes())
    (results / "multiqc" / "multiqc_report.html").write_bytes(report)
    (results / "multiqc" / "align_mqc.tsv").write_bytes((RESULTS / "align_mqc.tsv").read_bytes())
    (results / "hostile" / "hostile_report.html").write_bytes(
        (RESULTS / "hostile_report.html").read_bytes()
    )
    (results / "hostile" / "hostile_image.svg").write_bytes(
        (RESULTS / "hostile_image.svg").read_bytes()
    )
    (results / "logs").mkdir()
    big = "".join(f"line {i:06d} {'x' * 51}\n" for i in range(200 * 1024 // 64))
    (results / "logs" / "big.log").write_text(big)
    (results / "imaging").mkdir()
    (results / "imaging" / "cells.ome.tif").write_bytes(ome_tiff())
    ome_zarr(results / "imaging" / "cells.ome.zarr")
    print(SEEDED)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
