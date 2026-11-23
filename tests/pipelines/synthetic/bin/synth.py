#!/usr/bin/env python3
"""Deterministic task bodies shared by the Nextflow and Snakemake scenario pipelines.

Every subcommand is tiny and seeded, so both engines produce identical outputs for the
same inputs. Failure injection lives here too, so both engines fail the same way.

Every subcommand also writes log lines that do not depend on the run, so the task's stdout and
stderr have something to show: INFO lines on stdout (arguments, inputs, progress, outputs), one
WARN line on stderr, and ERROR lines on stderr when it fails. SYNTH_VERBOSITY sets how many:
  quiet    nothing but the ERROR lines
  normal   (the default) 5 to 20 lines on stdout, the WARN line on stderr
  loud     1000 progress lines on stdout and 1000 DEBUG lines on stderr, each stream above 64 KiB
The outputs are the same at every level.

Subcommands:
  reads    SAMPLE N_READS SEED OUT            write a fake reads file (one read per line)
  stats    READS OUT_JSON                     per-sample QC metrics (reads, gc, dup rate, q30)
  report   OUT_TSV OUT_JSON OUT_HTML JSON...  MultiQC-like general stats table, data JSON, HTML
  split    READS N_CHUNKS OUT_DIR             scatter reads into chunks (dynamic fan-out)
  align    CHUNK OUT                          fake alignment of one chunk -> mapped count
  merge    OUT_TSV FILE...                    gather per-chunk counts into a counts matrix
  compare  COUNTS GROUP_A GROUP_B OUT_TSV     fake differential comparison between groups
  fail     MODE [ATTEMPT] [GB]                inject a failure: exit | oom | oom_once | oom_real | timeout | flaky
"""
import hashlib, json, os, random, sys, time


STEPS = {"quiet": 0, "normal": 3, "loud": 1000}  # progress lines; loud adds as many DEBUG lines
SHOWN_INPUTS = 3  # input files named one per line; the rest are counted


def _log(level, msg):
    # INFO on stdout, the rest on stderr; flushed line by line, so a task killed with SIGKILL
    # (fail oom) keeps what it wrote
    print(f"{level:<5} {msg}", file=sys.stdout if level == "INFO" else sys.stderr, flush=True)


def _describe(path):
    if os.path.isdir(path):
        return f"{path}/ ({len(os.listdir(path))} files)"
    with open(path, "rb") as fh:
        lines = sum(1 for _ in fh)
    return f"{path} ({lines} lines, {os.path.getsize(path)} bytes)"


def _rng(*parts):
    return random.Random(int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16))


def reads(sample, n, seed, out):
    r = _rng(sample, seed)
    with open(out, "w") as fh:
        for _ in range(int(n)):
            fh.write("".join(r.choice("ACGT") for _ in range(50)) + "\n")


def stats(path, out):
    seqs = [l.strip() for l in open(path) if l.strip()]
    n = len(seqs)
    gc = sum(s.count("G") + s.count("C") for s in seqs) / max(1, n * 50)
    dup = 1 - len(set(seqs)) / max(1, n)
    sample = os.path.basename(path).split(".")[0]
    q30 = round(0.80 + _rng(sample, "q30").random() * 0.18, 4)
    json.dump({"sample": sample, "reads": n, "gc": round(gc, 4), "dup_rate": round(dup, 4), "q30": q30}, open(out, "w"))


def report(out_tsv, out_json, out_html, *jsons):
    rows = [json.load(open(j)) for j in jsons]
    rows.sort(key=lambda r: r["sample"])
    cols = ["sample", "reads", "gc", "dup_rate", "q30"]
    with open(out_tsv, "w") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")
    json.dump({"report_general_stats_data": [{r["sample"]: {k: r[k] for k in cols[1:]} for r in rows}]}, open(out_json, "w"), indent=1)
    trs = "".join(f"<tr>{''.join(f'<td>{r[c]}</td>' for c in cols)}</tr>" for r in rows)
    open(out_html, "w").write(f"<!doctype html><title>QC report</title><h1>QC report</h1><table><tr>{''.join(f'<th>{c}</th>' for c in cols)}</tr>{trs}</table>")


def split(path, n_chunks, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    seqs = [l for l in open(path) if l.strip()]
    sample = os.path.basename(path).split(".")[0]
    k = max(1, int(n_chunks))
    for i in range(k):
        with open(os.path.join(out_dir, f"{sample}.chunk{i:04d}.txt"), "w") as fh:
            fh.writelines(seqs[i::k])


def align(chunk, out):
    seqs = [l.strip() for l in open(chunk) if l.strip()]
    mapped = sum(1 for s in seqs if s.count("A") >= 10)
    name = os.path.basename(chunk)
    open(out, "w").write(f"{name.split('.')[0]}\t{name}\t{len(seqs)}\t{mapped}\n")


def merge(out_tsv, *files):
    per = {}
    for f in files:
        for line in open(f):
            sample, _chunk, total, mapped = line.rstrip("\n").split("\t")
            t, m = per.get(sample, (0, 0))
            per[sample] = (t + int(total), m + int(mapped))
    with open(out_tsv, "w") as fh:
        fh.write("sample\ttotal\tmapped\tmapped_rate\n")
        for s in sorted(per):
            t, m = per[s]
            fh.write(f"{s}\t{t}\t{m}\t{round(m / max(1, t), 4)}\n")


def compare(counts, group_a, group_b, out_tsv):
    a, b = group_a.split(","), group_b.split(",")
    rate = {l.split("\t")[0]: float(l.split("\t")[3]) for l in list(open(counts))[1:]}
    ma = sum(rate.get(s, 0) for s in a) / max(1, len(a))
    mb = sum(rate.get(s, 0) for s in b) / max(1, len(b))
    open(out_tsv, "w").write(f"group_a\tgroup_b\tmean_a\tmean_b\tdelta\n{group_a}\t{group_b}\t{ma:.4f}\t{mb:.4f}\t{ma - mb:.4f}\n")


def _failed(mode, attempt, msg):
    _log("ERROR", f"synthetic failure: {msg}")
    _log("ERROR", f"synth fail: injected by fail_mode={mode} on attempt {attempt}")


def fail(mode, attempt="1", gb="2"):
    if mode == "exit":
        _failed(mode, attempt, "tool exited with code 1")
        sys.exit(1)
    if mode == "oom":  # what a scheduler-enforced OOM kill looks like to the engine
        _failed(mode, attempt, "simulated OOM kill (exit 137)")
        os.kill(os.getpid(), 9)
    if mode == "oom_once":  # OOM on the first attempt only: a retry with more memory succeeds
        if int(attempt) == 1:
            _failed(mode, attempt, "simulated OOM kill on attempt 1 (exit 137)")
            os.kill(os.getpid(), 9)
        return
    if mode == "oom_real":  # really allocate memory; killed by Slurm / Kubernetes / docker limits
        _log("INFO", f"synth fail: allocating {gb} GiB")
        blocks = []
        for _ in range(int(float(gb) * 1024)):
            blocks.append(bytearray(1024 * 1024))
        time.sleep(5)
        return
    if mode == "timeout":
        _log("INFO", "synth fail: sleeping past the time limit")
        time.sleep(3600)
        return
    if mode == "flaky":
        if int(attempt) == 1:
            _failed(mode, attempt, "flaky on attempt 1")
            sys.exit(1)
        return
    if mode in ("none", ""):
        return
    sys.exit(f"unknown failure mode {mode}")


def main(cmd, args):
    verbosity = os.environ.get("SYNTH_VERBOSITY", "normal")
    if verbosity not in STEPS:
        sys.exit(f"unknown SYNTH_VERBOSITY {verbosity!r}: one of {', '.join(STEPS)}")
    steps = STEPS[verbosity]
    inputs = [a for a in args if os.path.exists(a)]
    if steps:
        _log("INFO", f"synth {cmd}: arguments {' '.join(args)}")
        _log("WARN", f"synth {cmd}: a synthetic task; its data are not real")
        for a in inputs[:SHOWN_INPUTS]:
            _log("INFO", f"synth {cmd}: input {_describe(a)}")
        if len(inputs) > SHOWN_INPUTS:
            _log("INFO", f"synth {cmd}: and {len(inputs) - SHOWN_INPUTS} more inputs")
    for i in range(1, steps + 1):
        block = hashlib.sha256(f"{cmd}|{i}".encode()).hexdigest()[:40]
        _log("INFO", f"synth {cmd}: step {i:04d}/{steps} processed block {block}")
        if verbosity == "loud":
            _log("DEBUG", f"synth {cmd}: step {i:04d}/{steps} buffer state {block}")
    globals()[cmd](*args)
    if steps:
        for a in args:
            if a not in inputs and os.path.exists(a):
                _log("INFO", f"synth {cmd}: wrote {_describe(a)}")
        _log("INFO", f"synth {cmd}: done")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
