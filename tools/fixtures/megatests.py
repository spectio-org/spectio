#!/usr/bin/env python3
"""Real nf-core test outputs as fixtures (dev-environment-and-testing.md, fixture corpus).

nf-core runs every release's full-size test ("megatest") on AWS and publishes the results in a public bucket:
  s3://nf-core-awsmegatests/<pipeline>/results-<release commit>/
This tool resolves a pipeline's latest release tag to its commit (git ls-remote), lists that results prefix,
and downloads the small QC files Spectio's checks and boards read (MultiQC data tables, pipeline_info, tool
summaries). Nothing is uploaded; only files below --max-bytes are fetched.

  python3 tools/fixtures/megatests.py list rnaseq sarek            # inventory only
  python3 tools/fixtures/megatests.py fetch rnaseq --out /tmp/corpus
  python3 tools/fixtures/megatests.py curate rnaseq --out /tmp/corpus   # small subset into tests/fixtures/megatests/

`curate` keeps, per pipeline, what a check binding or a board reads: the MultiQC general statistics (taken from
multiqc_data.json when no .txt was published), one execution trace, the params file, the software versions and
the few tool tables named in CURATE, under 600 kB per pipeline.
"""
from __future__ import annotations
import argparse, fnmatch, json, pathlib, re, subprocess, sys, urllib.parse, urllib.request
import time
import xml.etree.ElementTree as ET

BUCKET = "https://nf-core-awsmegatests.s3-eu-west-1.amazonaws.com"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
KEEP = ["*multiqc*_data/*.txt", "*multiqc*_data/multiqc_data.json",
        "*/pipeline_info/execution_trace*.txt", "*/pipeline_info/params_*.json", "*/pipeline_info/*software*versions.yml",
        "*/pipeline_info/*samplesheet*", "*summary*.csv", "*summary*.tsv", "*_mqc.tsv", "*_mqc.csv", "*metrics_summary.csv",
        "*.mosdepth.summary.txt", "*quast*/report.tsv", "*busco*summary*", "*checkm*summary*", "*_plddt*.tsv"]


def releases(pipe: str) -> list[tuple[str, str]]:
    """Release tags, newest first, with their commits."""
    out = subprocess.run(["git", "ls-remote", "--tags", "--refs", f"https://github.com/nf-core/{pipe}"],
                         capture_output=True, text=True, check=True).stdout
    tags = [(l.split("refs/tags/")[1], l.split()[0]) for l in out.splitlines() if re.search(r"refs/tags/v?\d+(\.\d+)*$", l)]
    return sorted(tags, key=lambda t: [int(x) for x in re.findall(r"\d+", t[0])], reverse=True)


def pick_release(pipe: str, tries: int = 6) -> tuple[str, str, list[tuple[str, int]]]:
    """The newest release whose megatest results include MultiQC data (some uploads are partial)."""
    first = None
    for tag, sha in releases(pipe)[:tries]:
        keys = list_keys(f"{pipe}/results-{sha}/")
        first = first or (tag, sha, keys)
        if any("multiqc" in k.lower() and "_data/" in k for k, _ in keys):
            return tag, sha, keys
    return first


def list_keys(prefix: str) -> list[tuple[str, int]]:
    keys, token = [], None
    while True:
        q = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token: q["continuation-token"] = token
        with urllib.request.urlopen(f"{BUCKET}/?{urllib.parse.urlencode(q)}", timeout=60) as r:
            root = ET.fromstring(r.read())
        keys += [(c.find("s3:Key", NS).text, int(c.find("s3:Size", NS).text)) for c in root.findall("s3:Contents", NS)]
        if root.findtext("s3:IsTruncated", namespaces=NS) != "true":
            return keys
        token = root.findtext("s3:NextContinuationToken", namespaces=NS)


FIXTURES = pathlib.Path(__file__).resolve().parents[2] / "tests/fixtures/megatests"
CURATE = {  # extra tool tables per pipeline (glob, relative to the results prefix), at most 6 files each
    "sarek": ["*/reports/mosdepth/*/*.recal.mosdepth.summary.txt"],
    "viralrecon": ["*/multiqc*_data/summary_variants_metrics_mqc.csv", "*/multiqc*_data/summary_assembly_metrics_mqc.csv",
                   "platform_nanopore/*/quast/report.tsv"],
    "airrflow": ["repertoire_comparison/Sequence_numbers_summary/*.tsv", "pipeline_info/samplesheet.valid.tsv"],
    "rnaseq": ["*/multiqc*_data/multiqc_star.txt", "*/multiqc*_data/multiqc_salmon.txt", "*/multiqc*_data/qualimap_rnaseq_genome_results.txt"],
    "ampliseq": ["*/multiqc*_data/multiqc_cutadapt.txt", "overall_summary.tsv", "*/overall_summary.tsv"],
    "scrnaseq": ["aligner_cellranger/*/multiqc*_data/multiqc_cellranger*.txt"],
    "taxprofiler": ["*multiqc*_data/multiqc_kraken*.txt", "*multiqc*_data/multiqc_bracken*.txt"],
    "rnafusion": ["*multiqc*_data/multiqc_star.txt"],
}


def curate(pipe: str, corpus: pathlib.Path) -> None:
    src = corpus / pipe
    meta = json.loads((src / "SOURCE.json").read_text())
    dst = FIXTURES / pipe
    if dst.exists():
        for f in sorted(dst.rglob("*"), reverse=True):
            f.unlink() if f.is_file() else f.rmdir()
    dst.mkdir(parents=True, exist_ok=True)
    picked: list[pathlib.Path] = []
    gs = sorted(src.rglob("multiqc_general_stats.txt"))
    if gs:
        picked.append(gs[0])
    else:
        js = sorted(src.rglob("multiqc_data.json"))
        if js:
            data = json.loads(js[0].read_text())
            rows = {}
            g = data.get("report_general_stats_data", [])
            blocks = g.items() if isinstance(g, dict) else ((str(i), b) for i, b in enumerate(g))  # MultiQC ≥ 1.2x: {module: {sample: …}}
            for module, block in blocks:
                for sample, vals in block.items():
                    if isinstance(vals, dict):
                        rows.setdefault(sample, {}).update({f"{module}-{k}": v for k, v in vals.items()})
            cols = sorted({c for v in rows.values() for c in v})
            out = dst / "multiqc_general_stats.txt"
            out.write_text("Sample\t" + "\t".join(cols) + "\n" + "".join(
                s + "\t" + "\t".join(str(v.get(c, "")) for c in cols) + "\n" for s, v in sorted(rows.items())))
    for pat in ["*/execution_trace*.txt", "execution_trace*.txt"]:
        tr = sorted(src.rglob(pat.split("/")[-1]))
        if tr:
            picked.append(tr[0]); break
    for name in ["params_*.json", "*software*versions.yml"]:
        f = sorted(src.rglob(name))
        if f:
            picked.append(f[0])
    for pat in CURATE.get(pipe, []):
        picked += sorted(p for p in src.rglob("*") if p.is_file() and fnmatch.fnmatch(str(p.relative_to(src)), pat))[:6]
    total = 0
    for f in dict.fromkeys(picked):
        rel = f.relative_to(src)
        if total + f.stat().st_size > 600_000:
            continue
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        # nf-core's params files carry their Slack webhook URL (hook_url); never commit it (security.sh secrets).
        out.write_bytes(re.sub(rb'("hook_url": ")[^"]*"', rb'\1REDACTED"', f.read_bytes()))
        total += f.stat().st_size
    meta["curated"] = sorted(str(p.relative_to(dst)) for p in dst.rglob("*") if p.is_file())
    (dst / "SOURCE.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(f"{pipe}: {len(meta['curated'])} files, {sum(p.stat().st_size for p in dst.rglob('*') if p.is_file()) // 1024} kB")


def get(url: str, dest: pathlib.Path, tries: int = 4) -> None:
    for i in range(tries):
        try:
            tmp = dest.with_suffix(dest.suffix + ".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.rename(dest)
            return
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "fetch", "curate"])
    ap.add_argument("pipelines", nargs="+")
    ap.add_argument("--out", default="corpus")
    ap.add_argument("--max-bytes", type=int, default=8 * 2**20)
    a = ap.parse_args()
    for pipe in a.pipelines:
        if a.cmd == "curate":
            curate(pipe, pathlib.Path(a.out))
            continue
        tag, sha, keys = pick_release(pipe)
        keep = [(k, s) for k, s in keys if s and s <= a.max_bytes and any(fnmatch.fnmatch(k, p) for p in KEEP)]
        gs = [k for k, _ in keep if k.endswith(("multiqc_general_stats.txt", "multiqc_data.json"))]
        print(f"{pipe} {tag} {sha[:7]}: {len(keys)} objects, {len(keep)} kept, multiqc tables={len(gs)}")
        if a.cmd == "list":
            for k in gs: print("   ", k)
            continue
        base = pathlib.Path(a.out) / pipe
        for k, s in keep:
            dest = base / k.split(f"results-{sha}/", 1)[1]
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                get(f"{BUCKET}/{urllib.parse.quote(k)}", dest)
        (base / "SOURCE.json").write_text(json.dumps({"pipeline": f"nf-core/{pipe}", "release": tag, "commit": sha,
                                                     "prefix": f"{BUCKET}/{pipe}/results-{sha}/", "files": len(keep)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
