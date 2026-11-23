"""The image check of the raw route's image mode (api §5.3, step 7 of the table; dev-env §15.3
req. 14, note of 2026-11-08).

`check` reads the first chunk of a raster file, the bytes then sent as the start of the body:
its signature must be the one the MIME Sniffing standard gives for the type its name says
(https://mimesniff.spec.whatwg.org/#matching-an-image-type-pattern), and the size its header
declares must be at most `MAX_PIXELS`. A header not found in the chunk is refused. The check is
advisory: it keeps a mislabelled file out of an `<img>`; the safety against sniffing is
`nosniff` and the CSP `sandbox`. An SVG has no signature check (its cap is the route's 5 MiB).
Pure functions on bytes: no file system.
"""

import struct

from spectio_server.files.confine import NotAllowed

MEDIA = {  # a name's suffix, lower case → the type an image is served with
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}
SVG = "image/svg+xml"
MAX_PIXELS = 50_000_000  # 50 megapixels (assumed decimal)

_SOF = frozenset(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}  # JPEG start of frame, SOF0 to SOF15
_NO_LENGTH = frozenset({0x01, *range(0xD0, 0xD8)})  # TEM, RST0 to RST7: no segment length


class _Mismatch(Exception):
    pass


def check(media: str, head: bytes) -> None:
    """Raise NotAllowed unless `head` starts as an image of type `media` that declares at most
    `MAX_PIXELS`; an SVG passes."""
    if media == SVG:
        return
    try:
        width, height = _SIZE[media](head)
    except (_Mismatch, struct.error, IndexError):
        raise NotAllowed("not the image its name says") from None
    if width * height > MAX_PIXELS:
        raise NotAllowed(f"image too large to decode: {width} x {height}")


def _need(found: bool) -> None:
    if not found:
        raise _Mismatch


def _png(head: bytes) -> tuple[int, int]:
    _need(head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR")
    width, height = struct.unpack_from(">II", head, 16)
    return width, height


def _gif(head: bytes) -> tuple[int, int]:
    _need(head[:6] in (b"GIF87a", b"GIF89a"))
    width, height = struct.unpack_from("<HH", head, 6)
    return width, height


def _webp(head: bytes) -> tuple[int, int]:
    _need(head[:4] == b"RIFF" and head[8:14] == b"WEBPVP")
    kind = head[12:16]
    if kind == b"VP8 ":  # lossy: frame tag (3 bytes), start code, then 14-bit sizes
        _need(head[23:26] == b"\x9d\x01\x2a")
        width, height = struct.unpack_from("<HH", head, 26)
        return width & 0x3FFF, height & 0x3FFF
    if kind == b"VP8L":  # lossless: signature 0x2f, then width - 1 and height - 1 on 14 bits
        _need(head[20] == 0x2F)
        (bits,) = struct.unpack_from("<I", head, 21)
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if kind == b"VP8X":  # extended: flags (4 bytes), then canvas width - 1 and height - 1 on 24
        _need(len(head) >= 30)
        width = int.from_bytes(head[24:27], "little") + 1
        return width, int.from_bytes(head[27:30], "little") + 1
    raise _Mismatch


def _jpeg(head: bytes) -> tuple[int, int]:
    """The size in the first start-of-frame segment, walking the segments from the start."""
    _need(head[:3] == b"\xff\xd8\xff")
    at = 2
    while True:
        _need(head[at] == 0xFF)
        while head[at] == 0xFF:  # fill bytes
            at += 1
        marker = head[at]
        at += 1
        if marker in _NO_LENGTH:
            continue
        _need(marker not in (0xD8, 0xD9, 0xDA))  # a second start, the end or a scan: no frame
        (length,) = struct.unpack_from(">H", head, at)
        if marker in _SOF:
            height, width = struct.unpack_from(">HH", head, at + 3)
            return width, height
        _need(length >= 2)
        at += length


_SIZE = {"image/png": _png, "image/gif": _gif, "image/webp": _webp, "image/jpeg": _jpeg}
