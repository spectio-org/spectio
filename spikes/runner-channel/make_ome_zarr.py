"""Write a small OME-Zarr the demo can open with Spectio's own OmeZarrView.

Usage: python3 make_ome_zarr.py <dir>

Standard library only. The image is OME-Zarr v0.4 on a Zarr v2 store: a `.zgroup`, a `.zattrs`
with one `multiscales` of two levels (3 channels, 512x512 and 256x256, chunks 256x256, uint8,
compressed with zlib — one of the compressors web/src/runs/imaging/zarr.ts accepts, decoded by
codecs.ts with pako), and a `.zarray` plus the zlib chunks under each level's directory. The
`omero` channels give the viewer its names and colours.

"""

import argparse
import json
import os
import zlib

WIDTH = HEIGHT = 512  # of level 0
LEVELS = 2  # the two `multiscales` datasets: 512x512 and 256x256
CHANNELS = (("DAPI", "0000ff"), ("FITC", "00ff00"), ("TRITC", "ff0000"))  # label, 6-hex colour
CHUNK = 256  # on every level


def pixel(c: int, y: int, x: int, size: int) -> int:
    """One channel's gradient: distinct per channel, so the viewer's channels differ visibly."""
    if c == 0:  # horizontal
        return x * 255 // max(1, size - 1)
    if c == 1:  # vertical
        return y * 255 // max(1, size - 1)
    cx, cy = x - size // 2, y - size // 2  # radial
    return min(255, (cx * cx + cy * cy) * 255 // (size * size // 2)) if size > 1 else 0


def chunk_bytes(c: int, y0: int, x0: int, size: int) -> bytes:
    """One chunk of channel `c`: a C-ordered (CHUNK, CHUNK) tile of the (size, size) plane."""
    rows = []
    for y in range(y0, min(y0 + CHUNK, size)):
        rows.append(bytes(pixel(c, y, x, size) for x in range(x0, min(x0 + CHUNK, size))))
    return zlib.compress(b"".join(rows), 1)


def write_json(path: str, obj: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
        f.write("\n")


def make_zarr(dir_path: str) -> None:
    os.makedirs(dir_path, exist_ok=True)
    write_json(os.path.join(dir_path, ".zgroup"), {"zarr_format": 2})
    write_json(
        os.path.join(dir_path, ".zattrs"),
        {
            "multiscales": [
                {
                    "version": "0.4",
                    "name": "demo",
                    "axes": [
                        {"name": "c", "type": "channel"},
                        {"name": "y", "type": "space"},
                        {"name": "x", "type": "space"},
                    ],
                    "datasets": [{"path": "0"}, {"path": "1"}],
                }
            ],
            "omero": {"channels": [{"label": label, "color": color} for label, color in CHANNELS]},
        },
    )
    for level in range(LEVELS):
        size = WIDTH >> level
        level_dir = os.path.join(dir_path, str(level))
        os.makedirs(level_dir, exist_ok=True)
        write_json(
            os.path.join(level_dir, ".zarray"),
            {
                "zarr_format": 2,
                "shape": [len(CHANNELS), size, size],
                "chunks": [1, CHUNK, CHUNK],
                "dtype": "|u1",
                "compressor": {"id": "zlib", "level": 1},
                "fill_value": 0,
                "order": "C",
                "filters": None,
                "dimension_separator": ".",
            },
        )
        for c in range(len(CHANNELS)):
            for y0 in range(0, size, CHUNK):
                for x0 in range(0, size, CHUNK):
                    data = chunk_bytes(c, y0, x0, size)
                    with open(os.path.join(level_dir, f"{c}.{y0 // CHUNK}.{x0 // CHUNK}"), "wb") as f:
                        f.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dir", help="the .ome.zarr directory to write")
    args = parser.parse_args()
    make_zarr(args.dir)
    print(f"OME-Zarr written to {args.dir}")


if __name__ == "__main__":
    main()
