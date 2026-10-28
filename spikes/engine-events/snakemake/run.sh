#!/usr/bin/env bash
# Spike T2: run the synthetic Snakemake pipeline with the spectio logger plugin.
# usage: run.sh SNAKEMAKE_BIN WORKDIR NAME [extra --config k=v ...]
# Same flags as run_scenarios.py run_snakemake() (tests/pipelines/synthetic/run_scenarios.py:59-71).
set -u
SMK=$1 W=$2 NAME=$3; shift 3
HERE=$(cd "$(dirname "$0")" && pwd)
SYN=$(cd "$HERE/../../../tests/pipelines/synthetic" && pwd)
mkdir -p "$W"
cd "$W"
SPECTIO_EVENTS="$W/$NAME.raw.jsonl" PYTHONPATH="$HERE" "$SMK" -s "$SYN/snakemake/workflow/Snakefile" \
  --directory "$W" --cores 2 --retries 2 --rerun-incomplete --printshellcmds --logger spectio \
  --config outdir=results samples="$SYN/data/samplesheet.csv" chunks=2 "$@" > "$W/$NAME.out" 2>&1
echo "exit=$?"
