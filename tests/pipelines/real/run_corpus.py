#!/usr/bin/env python3
"""Run one or more real pipelines from corpus.yaml with their own test datasets.

  python3 run_corpus.py --list
  python3 run_corpus.py --engine nextflow --name demo [--limits private] [--nextflow nextflow]
  python3 run_corpus.py --engine snakemake --name rna-seq-star-deseq2 [--workdir DIR]
  python3 run_corpus.py --tier pr                                 # everything in a tier
  python3 run_corpus.py --matrix nightly                          # CI matrix (pipelines-real.yml)

Every invocation first validates corpus.yaml (pinned refs, plain-token paths and args) and exits on an error.

Each run writes <workdir>/<name>/result.json (exit code, duration, outputs found, Nextflow trace
summary). Without --workdir, the workdir is a fresh private directory (mode 0700) under ${TMPDIR:-/tmp},
printed at the start and kept for debugging (`rm -rf "${TMPDIR:-/tmp}"/spectio-corpus-*` removes them).
Later these runs are launched through Spectio instead of directly (same entries).
"""
from __future__ import annotations

import argparse, json, os, re, shutil, stat, subprocess, sys, tempfile, time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
CORPUS = yaml.safe_load(open(HERE / "corpus.yaml"))


# Entries are pinned (a release tag or a commit SHA, never a branch), and every value that reaches a command line
# is a plain token: the CI matrix passes repo, directory, snakefile and args into workflow inputs.
PINNED = re.compile(r"v?\d+(\.\d+)*|[0-9a-f]{40}")
PATH = re.compile(r"[A-Za-z0-9._/-]+")
ARG = re.compile(r"[A-Za-z0-9._/=:,-]+")


def validate(corpus: dict) -> list[str]:
    """Return one message per invalid field; an empty list means the corpus is valid."""
    errs = []
    for section, ref_key, name_of in (("nfcore", "version", lambda e: e["name"]),
                                      ("snakemake_catalog", "tag", lambda e: e["repo"])):
        for e in corpus[section]:
            n = f"{section} entry {name_of(e)}"
            if not PINNED.fullmatch(str(e.get(ref_key, ""))):
                errs.append(f"{n}: {ref_key} {e.get(ref_key)!r} is neither a release tag nor a 40-hex commit SHA")
            for key in ("repo", "directory", "snakefile"):
                if key in e and not PATH.fullmatch(str(e[key])):
                    errs.append(f"{n}: {key} {e[key]!r} has characters outside [A-Za-z0-9._/-]")
            bad = [t for t in str(e.get("args", "")).split() if not ARG.fullmatch(t)]
            if bad:
                errs.append(f"{n}: args tokens {bad} have characters outside [A-Za-z0-9._/=:,-]")
    return errs


def matrix(corpus: dict, tier: str) -> tuple[list, list]:
    """The CI matrix for a tier: nightly includes pr, manual includes everything."""
    want = {"pr": {"pr"}, "nightly": {"pr", "nightly"}, "manual": {"pr", "nightly", "manual"}}[tier]
    nf = [e for e in corpus["nfcore"] if e["tier"] in want]
    smk = [dict(e, name=e["repo"].split("/")[1]) for e in corpus["snakemake_catalog"] if e["tier"] in want]
    return nf, smk


def clone(url: str, ref: str, dest: Path, submodules: bool = False) -> None:
    """Shallow clone at a tag or branch, or at a full commit SHA (for repositories with no release tag)."""
    if re.fullmatch(r"[0-9a-f]{40}", ref):
        try:
            subprocess.run(["git", "init", "-q", str(dest)], check=True)
            subprocess.run(["git", "-C", str(dest), "fetch", "-q", "--depth", "1", url, ref], check=True)
            subprocess.run(["git", "-C", str(dest), "checkout", "-q", "FETCH_HEAD"], check=True)
            if submodules:
                subprocess.run(["git", "-C", str(dest), "submodule", "update", "-q", "--init", "--recursive", "--depth", "1"], check=True)
        except subprocess.CalledProcessError:
            shutil.rmtree(dest, ignore_errors=True)  # a half-made checkout would be reused by the next run
            raise
    else:
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", ref,
                        *(["--recurse-submodules", "--shallow-submodules"] if submodules else []), url, str(dest)], check=True)


def nf_entry(e, wd: Path, nf: str, limits: str, nf_version: str | None) -> dict:
    out = wd / "results"
    cfg = wd / "limits.config"
    if limits == "auto":  # this machine: all CPUs, and less than the free memory the local executor checks against
        meminfo = dict(l.split(":", 1) for l in Path("/proc/meminfo").read_text().splitlines() if ":" in l)
        avail_kb = int(meminfo.get("MemAvailable", meminfo["MemTotal"]).split()[0])
        mem_gb = max(1, int(avail_kb / 2**20 * 0.8))
        lim = {"cpus": os.cpu_count(), "memory": f"{mem_gb}.GB", "time": "6.h"}
    else:
        lim = CORPUS["runner_limits"][limits]
    cfg.write_text(f"process.resourceLimits = [cpus: {lim['cpus']}, memory: {lim['memory']}, time: {lim['time']}]\n")
    # Clone with git instead of `nextflow run nf-core/x -r v`: Nextflow reads the manifest through the
    # GitHub API, which rate-limits anonymous calls (60/h) and is refused behind some proxies.
    src = wd / "src"
    if not src.exists():
        clone(f"https://github.com/nf-core/{e['name']}.git", e["version"], src)
    cmd = [nf, "run", str(src), "-profile", "test,docker", "--outdir", str(out), "-c", str(cfg), *e.get("args", "").split()]
    # Per-entry environment from corpus.yaml, e.g. NXF_SYNTAX_PARSER=v1 for releases the strict parser rejects.
    env = dict(os.environ, **e.get("env", {}), **({"NXF_VER": nf_version} if nf_version else {}))
    return {"cmd": cmd, "env": env, "cwd": wd}


def smk_entry(e, wd: Path, smk: str) -> dict:
    repo = wd / "repo"
    if not repo.exists():
        clone(f"https://github.com/{e['repo']}.git", e["tag"], repo, e.get("submodules", False))
    cmd = [smk, "--snakefile", e.get("snakefile", "workflow/Snakefile"), "--directory", e["directory"], *e["args"].split()]
    if "--sdm" not in e["args"] and "-n" not in e["args"].split():
        cmd += ["--sdm", "conda"]
    return {"cmd": cmd, "env": dict(os.environ), "cwd": repo}


def make_workdir(arg: str | None) -> Path:
    """A fresh private directory, or the given one if this user owns it and nobody else can write to it
    or swap it: its resolved parents must belong to this user or root, and be sticky if others can write."""
    if not arg:
        return Path(tempfile.mkdtemp(prefix="spectio-corpus-"))
    path = Path(arg)
    old_umask = os.umask(0o077)  # missing parents are created private too
    try:
        path.mkdir(parents=True, exist_ok=True)
    finally:
        os.umask(old_umask)
    real = Path(os.path.realpath(path))  # checked and returned, so a symlink on the way cannot be swapped later
    st = os.lstat(real)
    bad = path.is_symlink() or st.st_uid != os.getuid() or st.st_mode & 0o022
    for d in real.parents:
        s = os.stat(d)
        bad = bad or s.st_uid not in (0, os.getuid()) or (s.st_mode & 0o022 and not s.st_mode & stat.S_ISVTX)
    if bad:
        sys.exit(f"--workdir {path}: must be a directory you own that others cannot write to (chmod go-w), not a symlink, under directories that only you or root can change")
    return real


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--matrix", choices=["pr", "nightly", "manual"], help="print the CI matrix (GITHUB_OUTPUT lines) for a tier")
    ap.add_argument("--engine", choices=["nextflow", "snakemake"])
    ap.add_argument("--name")
    ap.add_argument("--tier", choices=["pr", "nightly", "manual"])
    ap.add_argument("--workdir")
    ap.add_argument("--limits", choices=["private", "public", "auto"], default="private")
    ap.add_argument("--nextflow", default=os.environ.get("NXF_BIN", "nextflow"))
    ap.add_argument("--nf-version")
    ap.add_argument("--snakemake", default=os.environ.get("SMK_BIN", "snakemake"))
    a = ap.parse_args()

    errs = validate(CORPUS)
    if errs:
        sys.exit("corpus.yaml is invalid:\n  " + "\n  ".join(errs))
    if a.matrix:
        nf, smk = matrix(CORPUS, a.matrix)
        print("nfcore=" + json.dumps(nf))
        print("smk=" + json.dumps(smk))
        return 0
    entries = [("nextflow", e, e["name"]) for e in CORPUS["nfcore"]] + \
              [("snakemake", e, e["repo"].split("/")[1]) for e in CORPUS["snakemake_catalog"]]
    if a.list:
        for eng, e, n in entries:
            print(f"{eng:9s} {n:32s} {(e.get('version') or e.get('tag'))[:8]:8s} {e['tier']:8s} {e['class']}")
        return 0
    sel = [(eng, e, n) for eng, e, n in entries
           if (not a.engine or eng == a.engine) and (not a.name or n == a.name) and (not a.tier or e["tier"] == a.tier)]
    if not sel:
        sys.exit("nothing selected")
    failures = 0
    workdir = make_workdir(a.workdir)
    print(f"workdir: {workdir}", flush=True)
    for eng, e, n in sel:
        if eng == "nextflow" and a.nf_version and tuple(map(int, a.nf_version.split("."))) < tuple(map(int, e["min_nf"].split("."))):
            print(f"SKIP {n}: needs Nextflow >= {e['min_nf']}"); continue
        wd = workdir / n; wd.mkdir(parents=True, exist_ok=True)
        spec = nf_entry(e, wd, a.nextflow, a.limits, a.nf_version) if eng == "nextflow" else smk_entry(e, wd, a.snakemake)
        t0 = time.time()
        # Stream to run.log, so a run killed by a full disk or the job timeout still leaves its log.
        with open(wd / "run.log", "w") as log:
            p = subprocess.run(spec["cmd"], cwd=spec["cwd"], env=spec["env"], stdout=log, stderr=subprocess.STDOUT)
        res = {"engine": eng, "name": n, "exit": p.returncode, "seconds": round(time.time() - t0), "cmd": spec["cmd"]}
        if eng == "nextflow":
            res["outputs"] = sorted(str(x.relative_to(wd / "results")) for x in (wd / "results").glob("*")) if (wd / "results").exists() else []
        (wd / "result.json").write_text(json.dumps(res, indent=2))
        print(f"{'PASS' if p.returncode == 0 else 'FAIL'}  {eng:9s} {n:32s} {res['seconds']:6d}s")
        failures += p.returncode != 0
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
