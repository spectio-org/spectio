#!/usr/bin/env python3
"""Run the synthetic scenarios on Nextflow and/or Snakemake and check their expectations.

  python3 run_scenarios.py --engine nextflow --nextflow nextflow --workdir /tmp/spx [--only happy,flaky_retry] [--nightly]
  python3 run_scenarios.py --engine snakemake --workdir /tmp/spx

Writes <workdir>/<engine>/report.json and exits non-zero if any scenario fails.
Extra executor arguments (e.g. a SLURM profile) go after `--`:
  python3 run_scenarios.py --engine nextflow -- -profile test,slurm
"""
from __future__ import annotations

import argparse, csv, glob, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
NF_MAIN = HERE / "nextflow" / "main.nf"
SMK_FILE = HERE / "snakemake" / "workflow" / "Snakefile"
SAMPLESHEET = HERE / "data" / "samplesheet.csv"
NF_STOP = {"qc": HERE / "nextflow/conf/stop_after_qc.config", "align": HERE / "nextflow/conf/stop_after_align.config"}
SMK_UNTIL = {"qc": "qc_report", "align": "align_done"}


def write_samplesheet(dest: Path, exclude: list[str]) -> Path:
    rows = list(csv.DictReader(open(SAMPLESHEET)))
    rows = [r for r in rows if r["sample"] not in exclude]
    with open(dest, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    return dest


def run_nextflow(nf: str, launch: Path, run: dict, extra: list[str]) -> tuple[int, str]:
    cmd = [nf, "-q", "run", str(NF_MAIN), "--outdir", "results"]
    cmd += extra or ["-profile", "test,local"]
    if run.get("resume"):
        cmd.append("-resume")
    if run.get("stop_after"):
        cmd += ["-c", str(NF_STOP[run["stop_after"]])]
    if run.get("samplesheet_exclude"):
        cmd += ["--input", str(write_samplesheet(launch / "samplesheet_v2.csv", run["samplesheet_exclude"]))]
    for k, v in (run.get("params") or {}).items():
        cmd += [f"--{k}", str(v)]
    p = subprocess.run(cmd, cwd=launch, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def run_snakemake(smk: str, launch: Path, run: dict, extra: list[str]) -> tuple[int, str]:
    cfg = {"outdir": "results", "samples": str(SAMPLESHEET), "chunks": 2}
    cfg.update(run.get("params") or {})
    if run.get("samplesheet_exclude"):
        cfg["samples"] = str(write_samplesheet(launch / "samplesheet_v2.csv", run["samplesheet_exclude"]))
    cmd = [smk, "-s", str(SMK_FILE), "--directory", str(launch), "--cores", "2", "--retries", "2",
           "--rerun-incomplete", "--printshellcmds"]
    cmd += extra
    if run.get("stop_after"):
        cmd += ["--until", SMK_UNTIL[run["stop_after"]]]
    cmd += ["--config"] + [f"{k}={v}" for k, v in cfg.items()]
    p = subprocess.run(cmd, cwd=launch, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def nf_tasks(launch: Path) -> dict:
    trace = launch / "results/pipeline_info/execution_trace.txt"
    out: dict = {}
    if not trace.exists():
        return out
    for row in csv.DictReader(open(trace), delimiter="\t"):
        t = out.setdefault(row["process"], {"completed": 0, "failed": 0, "cached": 0, "exit_codes": set(), "max_attempt": 0})
        st = row["status"]
        if st == "COMPLETED": t["completed"] += 1
        elif st == "FAILED": t["failed"] += 1; t["exit_codes"].add(int(row["exit"]) if row["exit"].lstrip("-").isdigit() else -1)
        elif st == "CACHED": t["cached"] += 1
        t["max_attempt"] = max(t["max_attempt"], int(row["attempt"] or 1))
    return out


def smk_tasks(log: str) -> dict:
    out: dict = {}
    for rule in re.findall(r"Finished jobid: \d+ \(Rule: (\w+)\)", log):
        out.setdefault(rule.upper(), {"completed": 0, "failed": 0, "exit_codes": set(), "max_attempt": 1})["completed"] += 1
    for rule in re.findall(r"Error in rule (\w+):", log):
        t = out.setdefault(rule.upper(), {"completed": 0, "failed": 0, "exit_codes": set(), "max_attempt": 1})
        t["failed"] += 1
    for code in re.findall(r"non-zero exit status (\d+)", log):
        for t in out.values():
            if t["failed"]:
                t["exit_codes"].add(int(code))
    return out


def nf_cached(launch: Path) -> int:
    """Cached tasks of the last run, from the trace (the quiet summary line differs between Nextflow versions)."""
    trace = launch / "results/pipeline_info/execution_trace.txt"
    if not trace.exists():
        return 0
    return sum(1 for row in csv.DictReader(open(trace), delimiter="\t") if row["status"] == "CACHED")


def check(expect: dict, launch: Path, code: int, log: str, engine: str) -> list[str]:
    errs = []
    want = expect.get("exit")
    if want == 0 and code != 0: errs.append(f"exit {code}, expected 0")
    if want == "nonzero" and code == 0: errs.append("exit 0, expected non-zero")
    res = launch / "results"
    for f in expect.get("present", []):
        if not (res / f).exists(): errs.append(f"missing {f}")
    for f in expect.get("absent", []):
        if (res / f).exists(): errs.append(f"unexpected {f}")
    for f, needle in (expect.get("not_contains") or {}).items():
        if (res / f).exists() and needle in (res / f).read_text(): errs.append(f"{f} still contains {needle}")
    if engine == "nextflow" and "cached_min" in expect and nf_cached(launch) < expect["cached_min"]:
        errs.append(f"cached={nf_cached(launch)} < {expect['cached_min']}")
    return errs


def check_tasks(want: dict, tasks: dict, engine: str) -> list[str]:
    errs = []
    for proc, exp in (want or {}).items():
        t = tasks.get(proc, {"completed": 0, "failed": 0, "exit_codes": set(), "max_attempt": 0})
        for k in ("completed", "failed"):
            if k in exp and t[k] != exp[k]: errs.append(f"{proc}.{k}={t[k]} expected {exp[k]}")
        if "completed_min" in exp and t["completed"] < exp["completed_min"]: errs.append(f"{proc}.completed={t['completed']} < {exp['completed_min']}")
        if engine == "nextflow" and "max_attempt" in exp and t["max_attempt"] != exp["max_attempt"]:
            errs.append(f"{proc}.max_attempt={t['max_attempt']} expected {exp['max_attempt']}")
        for c in exp.get("exit_codes", []):
            if c not in t["exit_codes"]: errs.append(f"{proc}: exit code {c} not seen (saw {sorted(t['exit_codes'])})")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["nextflow", "snakemake"], required=True)
    ap.add_argument("--nextflow", default=os.environ.get("NXF_BIN", "nextflow"))
    ap.add_argument("--snakemake", default=os.environ.get("SMK_BIN", "snakemake"))
    ap.add_argument("--workdir", default="/tmp/spectio-scenarios")
    ap.add_argument("--only")
    ap.add_argument("--nightly", action="store_true")
    ap.add_argument("extra", nargs="*")
    a = ap.parse_args()

    scenarios = yaml.safe_load(open(HERE / "scenarios.yaml"))["scenarios"]
    if a.only: scenarios = [s for s in scenarios if s["id"] in a.only.split(",")]
    elif not a.nightly: scenarios = [s for s in scenarios if not s.get("nightly")]
    base = Path(a.workdir) / a.engine
    base.mkdir(parents=True, exist_ok=True)
    faults = yaml.safe_load(open(HERE / "scenarios.yaml")).get("engine_faults", {}).get(a.engine, [])
    results = []
    for sc in scenarios:
        if sc.get("engines") and a.engine not in sc["engines"]:
            continue
        launch = base / sc["id"]
        t0 = time.time(); seen = []
        for _attempt in range(2):  # a scenario is repeated once, only when a known engine fault shows up
            shutil.rmtree(launch, ignore_errors=True); launch.mkdir(parents=True)
            errs, logs = [], []
            for i, run in enumerate(sc["runs"]):
                if a.engine == "nextflow":
                    code, log = run_nextflow(a.nextflow, launch, run, a.extra)
                else:
                    code, log = run_snakemake(a.snakemake, launch, run, a.extra)
                (launch / f"run{i + 1}.log").write_text(log); logs.append(log)
                errs += [f"run{i + 1}: {e}" for e in check(run.get("expect", {}), launch, code, log, a.engine)]
            tasks = nf_tasks(launch) if a.engine == "nextflow" else smk_tasks("\n".join(logs))
            errs += check_tasks(sc.get("expect_tasks"), tasks, a.engine)
            hit = [f["id"] for f in faults if any(f["pattern"] in log for log in logs)]
            if not errs or not hit or seen:
                break
            seen += hit
            (launch.parent / f"{sc['id']}.fault-{hit[0]}.log").write_text("\n".join(logs))
        ok = not errs
        results.append({"id": sc["id"], "ok": ok, "seconds": round(time.time() - t0, 1), "errors": errs,
                        "engine_faults": seen,
                        "tasks": {k: {**v, "exit_codes": sorted(v["exit_codes"])} for k, v in tasks.items()}})
        mark = ("PASS" if ok else "FAIL") + ("*" if seen else " ")
        note = f"  [repeated after known engine fault: {', '.join(seen)}]" if seen else ""
        print(f"{mark} {a.engine:9s} {sc['id']:30s} {results[-1]['seconds']:7.1f}s  {'; '.join(errs)}{note}", flush=True)
    (base / "report.json").write_text(json.dumps(results, indent=2))
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
