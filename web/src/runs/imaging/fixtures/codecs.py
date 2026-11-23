"""Writes codecs.json: Zarr v2 chunks compressed by the real numcodecs (FU-P3-102h).

Run from the repository root:
    uv run --no-project --with numcodecs==0.15.1 --with numpy==2.3.4 \
        python web/src/runs/imaging/fixtures/codecs.py

Each case holds one chunk of n values (value i as in `values` below, so the test rebuilds the
expected bytes) compressed with one numcodecs configuration: Blosc with each inner codec and each
shuffle (Blosc 1.21 splits blosclz, lz4 and zlib blocks by byte and makes one block of these
chunks; zstd keeps the forced 4096-byte blocks: several blocks, the last one short), a block whose
values are not a multiple of 8 (Blosc then stores it without its bit shuffle), a stored
(memcpyed) chunk, and the plain LZ4 and Zstd codecs. Blosc's zstd chunks are not the same bytes
from one run to the next (c-blosc 1.21.6); each run's decode to the same values.
"""

import base64
import json
import pathlib
from collections.abc import Iterator

import numcodecs  # type: ignore[import-untyped]
import numpy as np
from numcodecs import LZ4, Blosc, Zstd
from numcodecs.abc import Codec  # type: ignore[import-untyped]

# 4096-byte blocks of u2 (zstd): two full ones and one of 904 values
N = 5000


def values(dtype: str, n: int) -> np.ndarray:
    i = np.arange(n)
    v = ((i % 64) * 13 + (i // 64) * 5) % 1000
    return {"u1": v % 251, "u2": v, "u4": v * 65537}[dtype].astype("<" + dtype)


def cases() -> Iterator[tuple[str, str, int, Codec]]:
    for cname in ["blosclz", "lz4", "lz4hc", "zlib", "zstd"]:
        for shuffle, word in [
            (Blosc.NOSHUFFLE, "noshuffle"),
            (Blosc.SHUFFLE, "shuffle"),
            (Blosc.BITSHUFFLE, "bitshuffle"),
        ]:
            yield (
                f"blosc {cname} {word}",
                "u2",
                N,
                Blosc(cname=cname, clevel=5, shuffle=shuffle, blocksize=4096),
            )
    yield "blosc lz4 shuffle u4", "u4", N, Blosc(cname="lz4", clevel=5, shuffle=Blosc.SHUFFLE)
    yield (
        "blosc blosclz bitshuffle u1",
        "u1",
        N,
        Blosc(cname="blosclz", clevel=9, shuffle=Blosc.BITSHUFFLE),
    )
    yield (
        "blosc stored (clevel 0)",
        "u2",
        N,
        Blosc(cname="lz4", clevel=0, shuffle=Blosc.SHUFFLE, blocksize=4096),
    )
    yield (
        "blosc lz4 bitshuffle, 4100 values",
        "u2",
        4100,
        Blosc(cname="lz4", clevel=5, shuffle=Blosc.BITSHUFFLE),
    )
    yield "lz4", "u2", N, LZ4(acceleration=1)
    yield "zstd", "u2", N, Zstd(level=3)


out = {
    "generator": "web/src/runs/imaging/fixtures/codecs.py",
    "numcodecs": numcodecs.__version__,
    "blosc": numcodecs.blosc.VERSION_STRING,
    "cases": [
        {
            "name": name,
            "dtype": dtype,
            "values": n,
            "compressor": codec.get_config(),
            "data": base64.b64encode(codec.encode(values(dtype, n))).decode(),
        }
        for name, dtype, n, codec in cases()
    ],
}
path = pathlib.Path(__file__).with_name("codecs.json")
path.write_text(json.dumps(out, indent=1) + "\n")
print(f"wrote {len(out['cases'])} cases to {path}")
