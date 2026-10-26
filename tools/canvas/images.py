#!/usr/bin/env python3
"""Real test images for the UI boards (design/ui-canvas/images/), read from public OME-Zarr and nf-core test data.

Boards that show images (plates, slides, IMC ROIs, spots, volumes, satellite tiles, Xenium) use these real
thumbnails instead of drawn placeholders. Every output is listed in design/ui-canvas/images/SOURCES.md with its
source, the resolution level read, the channels and the licence.

Sources:
  - IDR OME-NGFF samples (https://idr.github.io/ome-ngff-samples/), read as OME-Zarr over HTTPS: only the
    pyramid level needed is fetched.
  - nf-core/test-datasets branches (git, sparse), for the pipelines' own test images.

  uv run --with "zarr>=3" --with "fsspec[http]" --with aiohttp --with tifffile --with imagecodecs \\
         --with pillow --with numpy --with pyarrow python tools/canvas/images.py [--only name,...] [--data DIR]

Deterministic: the same sources give the same files (fixed levels, crops and contrast windows).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "design/ui-canvas/images"
IDR = "https://livingobjects.ebi.ac.uk/idr/zarr/"
SO = {"client_kwargs": {"trust_env": True}}
TESTDATA = "https://github.com/nf-core/test-datasets"
LOG: list[dict] = []


# ---------- helpers ----------------------------------------------------------------------------------------------
def zgroup(path: str):
    import zarr
    return zarr.open_group(IDR + path, mode="r", storage_options=SO)


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def norm(a: np.ndarray, lo: float | None = None, hi: float | None = None, p=(1, 99.7)) -> np.ndarray:
    a = a.astype(np.float32)
    lo = np.percentile(a, p[0]) if lo is None else lo
    hi = np.percentile(a, p[1]) if hi is None else hi
    return np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)


def composite(planes: list[np.ndarray], colors: list[str], windows=None) -> np.ndarray:
    rgb = np.zeros(planes[0].shape + (3,), np.float32)
    for i, (pl, c) in enumerate(zip(planes, colors)):
        w = windows[i] if windows else (None, None)
        rgb += norm(pl, *w)[..., None] * hex_rgb(c)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def save(img: np.ndarray | Image.Image, name: str, source: str, note: str, licence: str, max_side: int | None = None,
         quality: int = 82) -> None:
    im = img if isinstance(img, Image.Image) else Image.fromarray(img)
    if max_side and max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / f"{name}.webp", "WEBP", quality=quality, method=6)
    LOG.append({"file": f"{name}.webp", "size": f"{im.size[0]}×{im.size[1]}", "source": source, "note": note, "licence": licence})


def outlines(labels: np.ndarray) -> np.ndarray:
    l = labels
    e = np.zeros_like(l, bool)
    e[1:, :] |= l[1:, :] != l[:-1, :]
    e[:, 1:] |= l[:, 1:] != l[:, :-1]
    return e & (l > 0)


def overlay(rgb: np.ndarray, mask: np.ndarray, color="#FFD54F", alpha=0.9) -> np.ndarray:
    out = rgb.astype(np.float32)
    out[mask] = out[mask] * (1 - alpha) + hex_rgb(color) * 255 * alpha
    return out.astype(np.uint8)


def testdata(branch: str, paths: list[str], data: pathlib.Path) -> pathlib.Path:
    """Sparse checkout of nf-core/test-datasets@branch into data/<branch> (blobs fetched only for `paths`)."""
    d = data / branch
    if not d.exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout", "-b", branch,
                        TESTDATA, str(d)], check=True)
    subprocess.run(["git", "-C", str(d), "checkout", "-q", "HEAD", "--", *paths], check=True)
    return d


CC_BY = "CC BY 4.0 (IDR study licence) [to be validated per study]"


# ---------- outputs ----------------------------------------------------------------------------------------------
def plate(data):
    """HCS plate (idr0001, yeast GFP screen): one thumbnail per well (field 0, mid z) + one well at full size.
    One contrast window for the whole plate (percentiles over all wells), so dim or empty wells look dim."""
    g = zgroup("v0.4/idr0001A/2551.zarr")
    wells = [w["path"] for w in g.attrs["plate"]["wells"]]
    src = "IDR idr0001-graml-sysgro, plate JL_120731_S6A (2551.zarr)"
    arr = {w: g[f"{w}/0/4"][:, 8] for w in wells}  # level 4 (65×86), z = 8 of 16
    win = [(float(np.percentile(np.stack([a[c] for a in arr.values()]), 0.5)),
            float(np.percentile(np.stack([a[c] for a in arr.values()]), 99.8))) for c in (0, 1)]
    for w, a in arr.items():
        save(composite([a[0], a[1]], ["#3DDC84", "#2B4590"], win), "plate-idr0001-" + w.replace("/", ""),
             src, f"well {w}, field 0, level 4, z 8; GFP green, Cascade blue blue; plate-wide contrast", CC_BY)
    a = g["C/5/0/1"][:, 8]
    save(composite([a[0], a[1]], ["#3DDC84", "#2B4590"], win), "plate-idr0001-viewer-C5", src,
         "well C5, field 0, level 1 (520×688), z 8", CC_BY)
    stats = {w: {"gfp_mean": round(float(a[0].mean()), 1), "blue_mean": round(float(a[1].mean()), 1)} for w, a in arr.items()}
    (OUT / "plate-idr0001.json").write_text(json.dumps({"window": win, "wells": stats}, indent=1))


def cellpainting(data):
    g = zgroup("v0.5/idr0033A/BR00109990_C2.zarr/0")
    ch = g.attrs["ome"]["omero"]["channels"] if "ome" in g.attrs else g.attrs["omero"]["channels"]
    a = g["1"][:]
    cols = ["#4F7BFF", "#3DDC84", "#FF5A5A", "#FFA53D", "#3DD6F5"]
    src = "IDR idr0033-rohban-pathways (Cell Painting), plate BR00109990 well C2"
    save(composite(list(a), cols), "cellpainting-idr0033-C2", src,
         "level 1 (776×1040), 5 channels: " + ", ".join(c["label"] for c in ch), CC_BY, max_side=900)
    for i, c in enumerate(ch):
        save((norm(a[i]) * 255).astype(np.uint8), f"cellpainting-idr0033-C2-ch{i + 1}", src,
             f"channel {c['label']}, level 1, grey", CC_BY, max_side=320)


def imc(data):
    g = zgroup("v0.4/idr0076A/10501752.zarr")
    names = [c["label"] for c in g.attrs["omero"]["channels"]]
    a = g["0"][:]
    pick = {"DNA1-191Ir": "#4F7BFF", "panCK-175Lu": "#3DDC84", "CD45-162Dy": "#FF5A5A", "SMA-148Nd": "#FFA53D"}
    planes = [a[names.index(k)] for k in pick]
    rgb = composite(planes, list(pick.values()))
    src = "IDR idr0076-ali-metabric (imaging mass cytometry, breast cancer), image 10501752"
    save(rgb, "imc-idr0076", src, "level 0 (494×464): DNA1 blue, panCK green, CD45 red, SMA orange", CC_BY)
    lab = g["labels/0/0"][:]
    lab = lab.reshape(lab.shape[-2:])
    save(overlay(rgb, outlines(lab)), "imc-idr0076-mask", src, "same with the cell mask outlines (labels/0)", CC_BY)
    save((norm(a[names.index("ArAr80-80ArAr")]) * 255).astype(np.uint8), "imc-idr0076-argon", src,
         "background channel ArAr80 (grey), used for the 'background' check", CC_BY)
    g2 = zgroup("v0.4/idr0054A/5025551.zarr")
    n2 = [c["label"] for c in g2.attrs["omero"]["channels"]]
    b = g2["2"][0, :, 0]
    pick2 = {"DNA1-191/193Ir": "#4F7BFF", "CD3-170Er": "#FF5A5A", "CD19-169Tm": "#3DDC84", "CD68-171Yb": "#FFA53D"}
    save(composite([b[n2.index(k)] for k in pick2], list(pick2.values())), "imc-idr0054",
         "IDR idr0054-segura-tonsilhyperion (IMC, human tonsil), image 5025551",
         "level 2 (675×675): DNA1 blue, CD3 red, CD19 green, CD68 orange", CC_BY)
    d = testdata("imcyto", ["inputs/20191121_BRAC3438.6f_ROI_1.ome.tiff"], data)
    import tifffile
    t = tifffile.imread(d / "inputs/20191121_BRAC3438.6f_ROI_1.ome.tiff")
    import re
    meta = tifffile.TiffFile(d / "inputs/20191121_BRAC3438.6f_ROI_1.ome.tiff").ome_metadata
    m = re.findall(r'Channel[^>]*Name="([^"]+)"', meta)
    pick3 = {"191Ir": "#4F7BFF", "148Nd": "#3DDC84", "168Er": "#FF5A5A"}
    save(composite([t[m.index(k)] for k in pick3], list(pick3.values())), "imc-imcyto-roi1",
         "nf-core/test-datasets@imcyto inputs/20191121_BRAC3438.6f_ROI_1.ome.tiff",
         "500×498, 191Ir blue, 148Nd green, 168Er red", "MIT (nf-core/test-datasets) [to be validated for the data]")


def slide(data):
    g = zgroup("v0.4/idr0073A/9798462.zarr")
    src = "IDR idr0073-schaadt-immuneinfiltrates, whole slide 9798462 (21115×16433)"
    ov = g["5"][0, :, 0]
    save(np.moveaxis(ov, 0, -1), "slide-idr0073-overview", src, "level 5 (513×659), RGB as stored", CC_BY)
    lv = g["4"][0, :, 0]  # 1027×1319
    rgb = np.moveaxis(lv, 0, -1)
    rows, cols = 9, 14
    th, tw = rgb.shape[0] // rows, rgb.shape[1] // cols
    for r in range(rows):
        for c in range(cols):
            save(rgb[r * th:(r + 1) * th, c * tw:(c + 1) * tw], f"slide-idr0073-r{r + 1}c{c + 1}", src,
                 f"tile r{r + 1} c{c + 1} of a 9×14 grid on level 4", CC_BY)
    hi = g["1"][0, :, 0, 3072:4096, 4096:5120]
    save(np.moveaxis(hi, 0, -1), "slide-idr0073-viewer", src, "level 1 crop 1024×1024 at y 3072, x 4096", CC_BY)


def labels3d(data):
    g = zgroup("v0.4/idr0062A/6001240.zarr")
    a = g["0"][:, 118]
    rgb = composite([a[1], a[0]], ["#4F7BFF", "#FFD54F"], [(0, 1500), (0, 1500)])
    src = "IDR idr0062-blin-nuclearsegmentation, image 6001240 (2 ch, 236 z)"
    save(rgb, "nuclei-idr0062", src, "z 118, level 0 (275×271): DAPI blue, LaminB1 yellow", CC_BY)
    lab = g["labels/0/0"][..., 118, :, :] if g["labels/0/0"].ndim == 3 else g["labels/0/0"][0, 118]
    save(overlay(rgb, outlines(np.asarray(lab)), "#FF4FA3"), "nuclei-idr0062-labels", src, "same with labels/0 outlines", CC_BY)
    for z in (40, 80, 118, 160, 200):
        b = g["1"][:, z]
        save(composite([b[1], b[0]], ["#4F7BFF", "#FFD54F"], [(0, 1500), (0, 1500)]), f"nuclei-idr0062-z{z}", src,
             f"z {z}, level 1", CC_BY)


def volume(data):
    g = zgroup("v0.5/idr0066/ExpA_VIP_ASLM_on.zarr")
    v = g["4"][::2]  # (969, 128, 128)
    src = "IDR idr0066-voigt-mesospim, ExpA_VIP_ASLM_on (light-sheet, cleared mouse brain, tdTomato)"
    lo, hi = 0, 1507
    save((norm(v.max(0), lo, hi) * 255).astype(np.uint8), "lightsheet-idr0066-mip-xy", src, "level 4, every 2nd z, max over z", CC_BY)
    save((norm(v.max(1), lo, hi) * 255).astype(np.uint8), "lightsheet-idr0066-mip-xz", src, "level 4, max over y", CC_BY)
    save((norm(v[v.shape[0] // 2], lo, hi) * 255).astype(np.uint8), "lightsheet-idr0066-xy-mid", src, "level 4, middle z", CC_BY)
    for i, z in enumerate((200, 400, 600, 800)):
        s = g["3"][2 * z]
        save((norm(s, lo, hi) * 255).astype(np.uint8), f"lightsheet-idr0066-z{2 * z}", src, f"level 3 (256×256), z {2 * z}", CC_BY)


def spots(data):
    d = testdata("molkart", ["test_data/input_data/nuclear.tiff", "test_data/input_data/membrane.tiff",
                             "test_data/input_data/spots.txt"], data)
    import tifffile
    nuc = tifffile.imread(d / "test_data/input_data/nuclear.tiff")
    mem = tifffile.imread(d / "test_data/input_data/membrane.tiff")
    rgb = composite([nuc, mem], ["#4F7BFF", "#9AA3B8"])
    src = "nf-core/test-datasets@molkart test_data/input_data (nuclear.tiff, membrane.tiff, spots.txt)"
    lic = "MIT (nf-core/test-datasets) [to be validated for the data]"
    save(rgb, "molkart-image", src, "360×360, nuclear blue, membrane grey", lic)
    rows = [l.split("\t") for l in (d / "test_data/input_data/spots.txt").read_text().splitlines() if l.strip()]
    genes = {}
    for r in rows:
        genes[r[3]] = genes.get(r[3], 0) + 1
    top = sorted(genes, key=genes.get, reverse=True)[:6]
    pal = ["#FF5A5A", "#3DDC84", "#FFA53D", "#3DD6F5", "#FF4FA3", "#FFD54F"]
    im = Image.fromarray(rgb).convert("RGB")
    dr = ImageDraw.Draw(im)
    for x, y, z, gene, *_ in rows:
        if gene in top:
            col = pal[top.index(gene)]
            x, y = float(x), float(y)
            dr.ellipse([x - 1.6, y - 1.6, x + 1.6, y + 1.6], fill=col)
    save(im, "molkart-spots", src, "same with spots of the 6 most frequent genes: " + ", ".join(f"{g} {genes[g]}" for g in top), lic)
    (OUT / "molkart-spots.json").write_text(json.dumps({"genes": genes, "top": top, "palette": pal[:len(top)], "spots": len(rows)}, indent=1))


def lunaphore(data):
    d = testdata("mcmicro", ["data/prestitched/lunaphore_example.ome.tiff", "data/prestitched/markers-lunaphore_example.csv"], data)
    import tifffile
    t = tifffile.imread(d / "data/prestitched/lunaphore_example.ome.tiff")
    src = "nf-core/test-datasets@mcmicro data/prestitched/lunaphore_example.ome.tiff (markers DAPI, Cy5, TRITC, TNNT2, WGA)"
    save(composite([t[0], t[3], t[4]], ["#4F7BFF", "#FF5A5A", "#3DDC84"]), "mcmicro-lunaphore", src,
         "1000×1000: DAPI blue, TNNT2 red, WGA green", "MIT (nf-core/test-datasets) [to be validated for the data]", max_side=700)


def xenium(data):
    """Xenium (nf-core/spatialxe test data): DAPI, protein composite, transcripts and cell boundaries; metrics as JSON."""
    import zipfile
    import tifffile
    import pyarrow.parquet as pq
    d = testdata("spatialaxe", ["Xenium_V1_Protein_Human_Kidney_tiny_outs.zip"], data)
    k = d / "kidney"
    if not k.exists():
        zipfile.ZipFile(d / "Xenium_V1_Protein_Human_Kidney_tiny_outs.zip").extractall(k)
    src = "nf-core/test-datasets@spatialaxe Xenium_V1_Protein_Human_Kidney_tiny_outs.zip (10x Genomics sample data)"
    lic = "10x Genomics sample data, CC BY 4.0 [to be validated]"
    f = 1  # pyramid level 1 = 1/2 resolution; Xenium pixel 0.2125 µm
    lvl = lambda name: tifffile.TiffFile(k / "morphology_focus" / name).series[0].levels[f].asarray()
    dapi = lvl("ch0000_dapi.ome.tif")
    dapi = dapi.max(0) if dapi.ndim == 3 else dapi
    prot = lvl("ch0001_atp1a1_cd45_e-cadherin.ome.tif")
    prot = prot.max(0) if prot.ndim == 3 else prot
    vim = lvl("ch0003_alphasma_vimentin.ome.tif")
    vim = vim.max(0) if vim.ndim == 3 else vim
    sig = norm(prot) > 0.25  # tissue = where the protein stain is; the image is larger than the decoded region
    rows, cols = np.where(sig.mean(1) > 0.02)[0], np.where(sig.mean(0) > 0.02)[0]
    y0, y1, x0, x1 = int(rows.min()), int(rows.max()) + 1, int(cols.min()), int(cols.max()) + 1
    crop = (slice(y0, y1), slice(x0, x1))
    dapi, prot, vim = dapi[crop], prot[crop], vim[crop]
    base = composite([dapi], ["#4F7BFF"])
    save(base, "xenium-kidney-dapi", src, f"DAPI, level 1 (1/2), max over z, cropped to the transcripts (x {x0}-{x1}, y {y0}-{y1})", lic, max_side=900)
    save(composite([dapi, prot, vim], ["#4F7BFF", "#3DDC84", "#FF5A5A"]), "xenium-kidney-protein", src,
         "DAPI blue, ATP1A1/CD45/E-cadherin green, αSMA/vimentin red", lic, max_side=900)
    t = pq.read_table(k / "transcripts.parquet").to_pandas() if False else pq.read_table(k / "transcripts.parquet").to_pydict()
    px = 0.2125 * 2
    genes = {}
    for g, isg in zip(t["feature_name"], t["is_gene"]):
        if isg:
            genes[g] = genes.get(g, 0) + 1
    top = sorted(genes, key=genes.get, reverse=True)[:6]
    pal = ["#FF5A5A", "#3DDC84", "#FFA53D", "#3DD6F5", "#FF4FA3", "#FFD54F"]
    im = Image.fromarray((base * 0.8).astype(np.uint8)).convert("RGB")
    dr = ImageDraw.Draw(im)
    for x, y, g, q in zip(t["x_location"], t["y_location"], t["feature_name"], t["qv"]):
        if g in top and q >= 20:
            X, Y = x / px - x0, y / px - y0
            dr.ellipse([X - 1.2, Y - 1.2, X + 1.2, Y + 1.2], fill=pal[top.index(g)])
    b = pq.read_table(k / "cell_boundaries.parquet").to_pydict()
    poly = {}
    for c, x, y in zip(b["cell_id"], b["vertex_x"], b["vertex_y"]):
        poly.setdefault(c, []).append((x / px - x0, y / px - y0))
    for pts in poly.values():
        dr.line(pts + pts[:1], fill="#E8E8F0", width=1)
    save(im, "xenium-kidney-transcripts", src, "transcripts with qv ≥ 20 of the 6 most frequent genes, cell boundaries", lic, max_side=900)
    import csv
    m = list(csv.DictReader(open(k / "metrics_summary.csv")))[0]
    qv = np.array(t["qv"], dtype=float)
    cells = pq.read_table(k / "cells.parquet").to_pydict()
    (OUT / "xenium-kidney.json").write_text(json.dumps({
        "metrics_summary": {kk: m[kk] for kk in ["panel_name", "region_area", "num_cells_detected", "total_high_quality_decoded_transcripts",
                                                  "fraction_transcripts_decoded_q20", "median_transcripts_per_cell", "median_genes_per_cell",
                                                  "fraction_empty_cells", "adjusted_negative_control_probe_rate", "fraction_transcripts_assigned"]},
        "top_genes": {g: genes[g] for g in top}, "palette": pal, "transcripts": len(qv),
        "qv_hist": np.histogram(qv, bins=[0, 10, 20, 30, 40, 100])[0].tolist(),
        "transcripts_per_cell_hist": np.histogram(cells["transcript_counts"], bins=[0, 10, 20, 40, 80, 160, 10000])[0].tolist()}, indent=1))


def rangeland(data):
    """Landsat scenes of the nf-core/rangeland test data: true-colour thumbnails and cloud fraction from QA_PIXEL."""
    import tarfile
    import tifffile
    d = testdata("rangeland", ["Landsat_collection2/Landsat_data.tar.gz"], data)
    x = d / "landsat"
    if not x.exists():
        tarfile.open(d / "Landsat_collection2/Landsat_data.tar.gz").extractall(x)
    scenes = sorted(p for p in (x / "181036").iterdir() if p.is_dir())
    src = "nf-core/test-datasets@rangeland Landsat_collection2 (USGS Landsat 4/5 Collection 2, path/row 181/036)"
    lic = "USGS Landsat: public domain"
    info = []
    for p in scenes:
        n = p.name
        band = lambda b: tifffile.imread(p / f"{n}_B{b}.TIF")
        qa = tifffile.imread(p / f"{n}_QA_PIXEL.TIF").astype(np.uint16)
        fill = (qa & 1) > 0
        cloud = ((qa >> 3) & 1) | ((qa >> 1) & 1)
        shadow = (qa >> 4) & 1
        valid = (~fill).sum()
        cf = float(cloud[~fill].sum() / max(valid, 1))
        sf = float(shadow[~fill].sum() / max(valid, 1))
        date = n.split("_")[3]
        info.append({"scene": n, "sensor": n[:4], "date": f"{date[:4]}-{date[4:6]}-{date[6:]}", "cloud": round(cf, 3),
                     "shadow": round(sf, 3), "valid": round(float(valid / qa.size), 3)})
        rgb = np.stack([norm(band(3), p=(2, 98)), norm(band(2), p=(2, 98)), norm(band(1), p=(2, 98))], -1)
        save((rgb * 255).astype(np.uint8), f"landsat-{date}", src, f"{n}: bands 3-2-1, cloud {cf:.0%}", lic, max_side=240, quality=78)
    (OUT / "landsat-scenes.json").write_text(json.dumps(info, indent=1))


OUTPUTS = {"xenium": xenium, "rangeland": rangeland, "plate": plate, "cellpainting": cellpainting, "imc": imc, "slide": slide, "labels3d": labels3d,
           "volume": volume, "spots": spots, "lunaphore": lunaphore}


def write_sources() -> None:
    old = json.loads((OUT / "sources.json").read_text()) if (OUT / "sources.json").exists() else []
    by = {e["file"]: e for e in old}
    by.update({e["file"]: e for e in LOG})
    entries = sorted(by.values(), key=lambda e: e["file"])
    (OUT / "sources.json").write_text(json.dumps(entries, indent=1, ensure_ascii=False))
    lines = ["# Real test images used by the UI boards", "",
             "Generated by `tools/canvas/images.py`; do not edit by hand. Thumbnails only: the source files stay where they are.", "",
             "| File | Size | Source | What it shows | Licence |", "|---|---|---|---|---|"]
    lines += [f"| `{e['file']}` | {e['size']} | {e['source']} | {e['note']} | {e['licence']} |" for e in entries]
    (OUT / "SOURCES.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only")
    ap.add_argument("--data", default=str(ROOT / ".cache/testdata"), help="where nf-core/test-datasets branches are cloned")
    a = ap.parse_args()
    data = pathlib.Path(a.data)
    data.mkdir(parents=True, exist_ok=True)
    for name in (a.only.split(",") if a.only else OUTPUTS):
        print("…", name, flush=True)
        OUTPUTS[name](data)
    write_sources()
    print(f"{len(LOG)} images written to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
