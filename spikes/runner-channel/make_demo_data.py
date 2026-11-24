"""Write the demo run's files into a `data/` directory: the kinds Spectio's viewers open.

Usage: python3 make_demo_data.py <data dir> [--big]

Standard library only. Writes `table.csv` (TableView), `multiqc_report.html` (ReportViewer),
`document.pdf` (no viewer: the demo shows it in an <iframe>), `gradient.png` (ImageView),
`multi-channel.ome.tif` (OmeTiffView; a classic little-endian TIFF, one plane per channel, with
the OME-XML the viewer reads) and `image.ome.zarr/` (OmeZarrView, via make_ome_zarr). `--big`
adds `big.bin`, 9 MiB, more than one runner read, for the chunked-read check.

"""

import argparse
import binascii
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_ome_zarr  # the sibling module, same directory

WIDTH = HEIGHT = 512
CHANNELS = (("DAPI", 0x0000FF), ("FITC", 0x00FF00), ("TRITC", 0xFF0000))  # name, RGB


def pixel(c: int, y: int, x: int) -> int:
    """One channel's gradient, the same image as the OME-Zarr's, so the two viewers agree."""
    return make_ome_zarr.pixel(c, y, x, WIDTH)


# --- CSV (TableView) ------------------------------------------------------------------------


def write_csv(dir_path: str) -> None:
    rows = [
        ["sample", "gene", "count", "condition"],
        ["S1", "BRCA1", "1240", "control"],
        ["S1", "TP53", "842", "control"],
        ["S1", "EGFR", "310", "control"],
        ["S2", "BRCA1", "1617", "treated"],
        ["S2", "TP53", "954", "treated"],
        ["S2", "EGFR", "421", "treated"],
        ["S3", "BRCA1", "988", "control"],
        ["S3", "TP53", "1176", "treated"],
        ["S3", "EGFR", "202", "control"],
    ]
    with open(os.path.join(dir_path, "table.csv"), "w", encoding="utf-8") as f:
        for row in rows:
            f.write(",".join(row) + "\n")


# --- HTML report (ReportViewer) ---------------------------------------------------------------


def write_report(dir_path: str) -> None:
    html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MultiQC report</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 24px; color: #222; }
  h1 { font-size: 22px; }
  table { border-collapse: collapse; margin-top: 16px; }
  th, td { border: 1px solid #ccc; padding: 4px 12px; text-align: left; }
  .good { color: #157a4b; font-weight: 600; }
</style>
</head>
<body>
<h1>MultiQC report</h1>
<p>A stand-in for the pipeline's own report: served from the login node through the runner
channel, with the same sandbox the product server sets.</p>
<table>
<tr><th>Section</th><th>Status</th></tr>
<tr><td>FastQC</td><td class="good">pass</td></tr>
<tr><td>STAR</td><td class="good">pass</td></tr>
<tr><td>MultiQC</td><td class="good">pass</td></tr>
</table>
</body>
</html>
"""
    with open(os.path.join(dir_path, "multiqc_report.html"), "w", encoding="utf-8") as f:
        f.write(html)


# --- PDF (no viewer: the demo page shows it in an <iframe>) ----------------------------------


def write_pdf(dir_path: str) -> None:
    """A minimal one-page PDF, its xref table's offsets computed, so every reader opens it."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = b"BT /F1 24 Tf 72 720 Td (Spectio runner-channel demo) Tj ET\n"
    objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream")
    binary = b"\x00\x01\x02\xff\xfe\x00binary bytes, as a real PDF's streams carry\n"  # NULs: binary
    objects.append(b"<< /Length " + str(len(binary)).encode() + b" >>\nstream\n" + binary + b"endstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]  # objects are numbered from 1
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += b"trailer << /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\n"
    out += b"startxref\n" + str(xref_at).encode() + b"\n%%EOF\n"
    with open(os.path.join(dir_path, "document.pdf"), "wb") as f:
        f.write(bytes(out))


# --- PNG (ImageView) --------------------------------------------------------------------------


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    )


def write_png(dir_path: str) -> None:
    """A truecolour PNG: the same gradient as the OME images' first channel."""
    rows = b"".join(b"\x00" + bytes(pixel(0, y, x) for x in range(WIDTH)) for y in range(HEIGHT))
    out = bytearray(b"\x89PNG\r\n\x1a\n")
    out += png_chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0))
    out += png_chunk(b"IDAT", zlib.compress(rows, 6))
    out += png_chunk(b"IEND", b"")
    with open(os.path.join(dir_path, "gradient.png"), "wb") as f:
        f.write(bytes(out))


# --- OME-TIFF (OmeTiffView) --------------------------------------------------------------------


OME_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06">'
    '<Image ID="Image:0" Name="demo">'
    "<Pixels "
    'DimensionOrder="XYCZT" Type="uint8" '
    f'SizeX="{WIDTH}" SizeY="{HEIGHT}" SizeZ="1" SizeC="{len(CHANNELS)}" SizeT="1" '
    'Interleaved="false">'
    + "".join(
        f'<Channel ID="Channel:0:{c}" Name="{name}" Color="{color - (1 << 32)}" SamplesPerPixel="1"/>'
        for c, (name, color) in enumerate(CHANNELS)
    )
    + "</Pixels></Image></OME>"
)


def write_ome_tiff(dir_path: str) -> None:
    """A classic little-endian TIFF, one IFD per channel plane, the OME-XML on the first: what
    web/src/runs/imaging/viv.ts `loadOmeTiff` checks (Sizes equal the IFD's, planes <= IFDs)."""
    planes = [bytes(pixel(c, y, x) for y in range(HEIGHT) for x in range(WIDTH)) for c in range(len(CHANNELS))]
    out = bytearray(b"II*\x00" + struct.pack("<I", 0))  # the first IFD's offset, filled below
    plane_at = []
    for plane in planes:
        plane_at.append(len(out))
        out += plane
    xml_at = len(out)
    out += OME_XML.encode("utf-8") + b"\x00"
    ifd_at = []
    next_at = []  # where each IFD's `next IFD` field sits, patched once all offsets are known
    for c in range(len(CHANNELS)):
        ifd_at.append(len(out))
        entries = [
            (256, 3, 1, WIDTH),  # ImageWidth
            (257, 3, 1, HEIGHT),  # ImageLength
            (258, 3, 1, 8),  # BitsPerSample
            (259, 3, 1, 1),  # Compression: none
            (262, 3, 1, 1),  # Photometric: BlackIsZero
            (273, 4, 1, plane_at[c]),  # StripOffsets
            (277, 3, 1, 1),  # SamplesPerPixel
            (278, 3, 1, HEIGHT),  # RowsPerStrip: one strip
            (279, 4, 1, len(planes[c])),  # StripByteCounts
        ]
        if c == 0:  # the OME-XML the viewer reads is on the first plane only
            entries.append((270, 2, len(OME_XML) + 1, xml_at))  # ImageDescription
        entries.sort(key=lambda e: e[0])
        out += struct.pack("<H", len(entries))
        for tag, kind, count, value in entries:
            if kind == 3 and count == 1:  # a SHORT fits its field's low half
                out += struct.pack("<HHI", tag, kind, count) + struct.pack("<HH", value, 0)
            else:
                out += struct.pack("<HHII", tag, kind, count, value)
        next_at.append(len(out))
        out += struct.pack("<I", 0)
    for c, at in enumerate(next_at):
        nxt = ifd_at[c + 1] if c + 1 < len(CHANNELS) else 0
        out[at : at + 4] = struct.pack("<I", nxt)
    out[4:8] = struct.pack("<I", ifd_at[0])
    with open(os.path.join(dir_path, "multi-channel.ome.tif"), "wb") as f:
        f.write(bytes(out))


# --- all ---------------------------------------------------------------------------------------


def make_data(dir_path: str, big: bool) -> None:
    os.makedirs(dir_path, exist_ok=True)
    write_csv(dir_path)
    write_report(dir_path)
    write_pdf(dir_path)
    write_png(dir_path)
    write_ome_tiff(dir_path)
    make_ome_zarr.make_zarr(os.path.join(dir_path, "image.ome.zarr"))
    if big:
        # 9 MiB: more than the 8 MiB + 1 of one runner read, so the channel reads it in pieces
        chunk = b"0123456789abcdef"
        with open(os.path.join(dir_path, "big.bin"), "wb") as f:
            for _ in range((9 << 20) // len(chunk)):
                f.write(chunk)
    print(f"demo data written to {dir_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dir", help="the `data` directory to write")
    parser.add_argument("--big", action="store_true", help="also write big.bin, 9 MiB")
    args = parser.parse_args()
    make_data(args.dir, args.big)


if __name__ == "__main__":
    main()
