#!/usr/bin/env bash
# Spike: run an nf-core pipeline with -preview (no task runs), the spike nf-spectio bridge
# added through NXF_PLUGINS_DEFAULT (additive; -plugins and a -c plugins{} block replace the
# pipeline's own plugins list), and -with-dag. Captures onProcessCreate events via capture_server.py.
# usage: preview.sh PIPELINE_DIR RUN_DIR OUT.jsonl [extra nextflow args...]
set -u
HERE=$(cd "$(dirname "$0")" && pwd); SRC=$1 RUN=$2; OUT=$(realpath -m "$3"); shift 3
mkdir -p "$RUN"; cd "$RUN"; rm -rf .nextflow* work dag.mmd results
: > "$OUT.tmp"
python3 "$HERE/capture_server.py" 8766 "$OUT.tmp" & CAP=$!
sleep 1
NXF_PLUGINS_DEFAULT=nf-spectio@0.0.1 SPECTIO_ENDPOINT=http://127.0.0.1:8766/spectio/events NXF_ANSI_LOG=false \
  timeout 900 nextflow run "$SRC" -preview -profile test --outdir results -with-dag dag.mmd "$@" > run.log 2>&1
echo "exit=$?"
kill $CAP; mv "$OUT.tmp" "$OUT"
