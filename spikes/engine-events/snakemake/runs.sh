#!/usr/bin/env bash
# Spike T2: the Snakemake captures, then their fixtures. usage: runs.sh SNAKEMAKE_BIN SCRATCH
set -u
B=$1 S=$2
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
FIX=$HERE/../fixtures
V=$("$B" --version)
rm -rf "$S/smk"
# 1. checkpoint `split` + align S07 fails on attempt 1 and succeeds on attempt 2 (flaky_retry)
bash "$HERE/run.sh" "$B" "$S/smk/flaky" flaky fail_mode=flaky fail_rule=align fail_sample=S07 &
# 2. compare treatA fails on all 3 attempts (tool_error_then_fixed_resume), then a plain rerun
( bash "$HERE/run.sh" "$B" "$S/smk/toolerr" toolerr fail_mode=exit fail_rule=compare fail_sample=treatA
  bash "$HERE/run.sh" "$B" "$S/smk/toolerr" rerun ) &
wait
norm() { python3 "$HERE/../normalise.py" "$1" "$2" --sub "$3=<launch>" --sub "$REPO=<repo>" --sub "$S=<scratch>" --token-key platform; }
norm "$S/smk/flaky/flaky.raw.jsonl" "$FIX/snakemake-${V}_checkpoint_flaky_retry.jsonl" "$S/smk/flaky"
norm "$S/smk/toolerr/toolerr.raw.jsonl" "$FIX/snakemake-${V}_tool_error.jsonl" "$S/smk/toolerr"
norm "$S/smk/toolerr/rerun.raw.jsonl" "$FIX/snakemake-${V}_tool_error_rerun.jsonl" "$S/smk/toolerr"
