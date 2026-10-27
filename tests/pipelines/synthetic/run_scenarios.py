#!/usr/bin/env python3
"""Run the synthetic scenarios on Nextflow and/or Snakemake and check their expectations.

  python3 run_scenarios.py --engine nextflow --nextflow nextflow --workdir /tmp/spx [--only happy,flaky_retry] [--nightly]
  python3 run_scenarios.py --engine snakemake --workdir /tmp/spx

Writes <workdir>/<engine>/report.json and exits non-zero if any scenario fails.
Golden fixtures (golden/<engine>-<version>/<scenario>.tsv, local executor only):
  --golden record   writes them from this run
  --golden check    compares this run with them (a version without fixtures is skipped)
Extra executor arguments (e.g. a SLURM profile) go after `--`:
  python3 run_scenarios.py --engine nextflow -- -profile test,slurm
"""
from __future__ import annotations

import argparse, csv, glob, io, json, os, re, shutil, subprocess, sys, time
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
NF_MAIN = HERE / "nextflow" / "main.nf"
SMK_FILE = HERE / "snakemake" / "workflow" / "Snakefile"
SAMPLESHEET = HERE / "data" / "samplesheet.csv"
NF_STOP = {"qc": HERE / "nextflow/conf/stop_after_qc.config", "align": HERE / "nextflow/conf/stop_after_align.config"}
# --until runs only the targets' dependencies, not sibling branches (snakemake cli.py at v9.27.1), so the
# align gate names qc_report too: both stages before the gate are done, as in the Nextflow twin.
SMK_UNTIL = {"qc": ["qc_report"], "align": ["qc_report", "align_done"]}
GOLDEN = HERE / "golden"
GOLDEN_COLUMNS = ("run", "process", "status", "exit", "attempt", "tag", "count")


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
        cmd += ["--until", *SMK_UNTIL[run["stop_after"]]]
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


def nf_rows(trace: str) -> list[tuple]:
    """(process, tag, status, exit, attempt) per task row of a Nextflow trace."""
    return [(r["process"], r["tag"], r["status"], r["exit"], r["attempt"] or "1")
            for r in csv.DictReader(io.StringIO(trace), delimiter="\t")]


def smk_rows(log: str) -> list[tuple]:
    """(RULE, wildcards, status, exit, attempt) per job outcome in a Snakemake log.

    A job block ("rule x:", "localrule x:", "checkpoint x:") gives jobid, wildcards and the `attempt`
    resource; "Finished jobid: N" closes it as COMPLETED; "Error in rule x:" with its jobid closes it as
    FAILED, with the exit status of the "Command ... returned non-zero exit status K" line before it.
    """
    jobs, rows, cur, mode, exit_code = {}, [], None, None, "-"
    for line in log.splitlines():
        if m := re.match(r"(?:local)?(?:rule|checkpoint) (\w+):$", line):
            cur, mode = {"rule": m[1].upper(), "wc": "", "attempt": "1"}, "job"
        elif line.startswith("Error in rule "):
            mode = "error"
        elif m := re.match(r"\s+jobid: (\d+)$", line):
            if mode == "job":
                jobs[m[1]] = cur
            elif mode == "error" and m[1] in jobs:
                j = jobs[m[1]]
                rows.append((j["rule"], j["wc"], "FAILED", exit_code, j["attempt"]))
                mode, exit_code = None, "-"
        elif mode == "job" and (m := re.match(r"\s+wildcards: (.*)$", line)):
            cur["wc"] = m[1]
        elif mode == "job" and (m := re.search(r"^\s+resources: .*\battempt=(\d+)", line)):
            cur["attempt"] = m[1]
        elif m := re.search(r"non-zero exit status (\d+)", line):
            exit_code = m[1]
        elif (m := re.match(r"Finished jobid: (\d+) ", line)) and m[1] in jobs:
            j = jobs[m[1]]
            rows.append((j["rule"], j["wc"], "COMPLETED", "0", j["attempt"]))
    return rows


def golden_text(engine: str, version: str, scenario: str, runs: list[tuple[int, list[tuple]]],
                target: tuple[str, str] | None) -> str:
    """Stable text for one scenario: run exit codes, then task outcomes per run.

    First-attempt COMPLETED and CACHED tasks are counted (tag `*`); every other outcome keeps its tag.
    With a target (process, sample), only the injected task is kept: after a fatal failure, which other
    tasks finished, were aborted or were cached depends on timing.
    """
    out = [f"# {engine} {version} · {scenario}"] + [f"# run {i}: exit {code}" for i, (code, _) in enumerate(runs, 1)]
    out.append("\t".join(GOLDEN_COLUMNS))
    counts = Counter()
    for i, (_, rows) in enumerate(runs, 1):
        for proc, tag, status, code, attempt in rows:
            if target and (proc != target[0] or target[1] not in tag):
                continue
            plain = status in ("COMPLETED", "CACHED") and attempt == "1"
            counts[(str(i), proc, status, code, attempt, "*" if plain else tag)] += 1
    out += ["\t".join(k + (str(n),)) for k, n in sorted(counts.items())]
    return "\n".join(out) + "\n"


def golden_target(sc: dict) -> tuple[str, str] | None:
    """The injected task of a scenario with a run that must fail, else None."""
    if not any((r.get("expect") or {}).get("exit") == "nonzero" for r in sc["runs"]):
        return None
    for r in sc["runs"]:
        p = r.get("params") or {}
        if p.get("fail_process"):
            return p["fail_process"].upper(), str(p.get("fail_sample", ""))
    return None


def engine_version(engine: str, binary: str) -> str:
    out = subprocess.run([binary, "-version" if engine == "nextflow" else "--version"],
                         capture_output=True, text=True).stdout
    m = re.search(r"version (\d+\.\d+\.\d+)", out) if engine == "nextflow" else re.match(r"\s*(\S+)", out)
    return m[1] if m else "unknown"


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
    ap.add_argument("--golden", choices=["record", "check"])
    ap.add_argument("extra", nargs="*")
    a = ap.parse_args()
    if a.golden and a.extra:
        ap.error("golden fixtures are recorded with the local executor only (no extra arguments)")
    version = engine_version(a.engine, a.nextflow if a.engine == "nextflow" else a.snakemake) if a.golden else ""
    golden_dir = GOLDEN / f"{a.engine}-{version}"
    if a.golden == "check" and not golden_dir.is_dir():
        print(f"note: no golden fixtures for {a.engine} {version}; golden check skipped", flush=True)

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
            errs, logs, outcomes = [], [], []
            for i, run in enumerate(sc["runs"]):
                if a.engine == "nextflow":
                    trace = launch / "results/pipeline_info/execution_trace.txt"
                    trace.unlink(missing_ok=True)  # never read the previous run's trace
                    code, log = run_nextflow(a.nextflow, launch, run, a.extra)
                    outcomes.append((code, nf_rows(trace.read_text()) if trace.exists() else []))
                else:
                    code, log = run_snakemake(a.snakemake, launch, run, a.extra)
                    outcomes.append((code, smk_rows(log)))
                (launch / f"run{i + 1}.log").write_text(log); logs.append(log)
                errs += [f"run{i + 1}: {e}" for e in check(run.get("expect", {}), launch, code, log, a.engine)]
            tasks = nf_tasks(launch) if a.engine == "nextflow" else smk_tasks("\n".join(logs))
            errs += check_tasks(sc.get("expect_tasks"), tasks, a.engine)
            hit = [f["id"] for f in faults if any(f["pattern"] in log for log in logs)]
            if not errs or not hit or seen:
                break
            seen += hit
            (launch.parent / f"{sc['id']}.fault-{hit[0]}.log").write_text("\n".join(logs))
        gold = golden_dir / f"{sc['id']}.tsv"
        text = golden_text(a.engine, version, sc["id"], outcomes, golden_target(sc))
        if a.golden == "record" and not errs:
            golden_dir.mkdir(parents=True, exist_ok=True); gold.write_text(text)
        elif a.golden == "check" and gold.exists() and gold.read_text() != text:
            (launch / "golden.actual.tsv").write_text(text)
            errs.append(f"differs from {gold.relative_to(HERE)} (see {launch / 'golden.actual.tsv'})")
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
