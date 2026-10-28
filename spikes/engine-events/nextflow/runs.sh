#!/usr/bin/env bash
# Spike T2: Nextflow captures through -with-tower (and nf-spectio when PLUGIN=1).
# usage: runs.sh NEXTFLOW_BIN SCRATCH PORT [extra nextflow args...]
# Three runs in one launch dir: flaky (ALIGN S07 fails on attempt 1, retried), tool error
# (COMPARE treatA, exit 1, not retried, run fails), then -resume without the fault.
# Each run's requests are split into their own raw file by the capture server log position.
set -u
NF=$1 S=$2 PORT=$3; shift 3
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
MAIN=$REPO/tests/pipelines/synthetic/nextflow/main.nf
V=$("$NF" -version 2>/dev/null | sed -n 's/.*version \([0-9.]*\).*/\1/p' | head -1)
L=$S/nf/$V
rm -rf "$L"; mkdir -p "$L"; cd "$L"
python3 "$HERE/../capture_server.py" "$PORT" "$L/capture.jsonl" & SRV=$!
sleep 1
export TOWER_ACCESS_TOKEN=dummy-token-t2 NXF_ANSI_LOG=false
# PLUGIN=1: also load nf-spectio (installed by nf-spectio/build.sh), posting to /spectio/events
PLUG=()
if [ "${PLUGIN:-0}" = 1 ]; then export SPECTIO_ENDPOINT="http://localhost:$PORT/spectio/events"; PLUG=(-plugins nf-spectio@0.0.1); fi
run() {  # run NAME args...
  local name=$1; shift
  local before; before=$(wc -l < "$L/capture.jsonl" 2>/dev/null || echo 0)
  "$NF" run "$MAIN" -profile test,local --outdir results -with-tower "http://localhost:$PORT" "${PLUG[@]}" "$@" > "$L/$name.out" 2>&1
  echo "$name exit=$?"
  sleep 2
  tail -n +"$((before + 1))" "$L/capture.jsonl" > "$L/$name.raw.jsonl"
}
run flaky "$@" --fail_mode flaky --fail_process ALIGN --fail_sample S07
run toolerr "$@" --fail_mode exit --fail_process COMPARE --fail_sample treatA
run resume "$@" -resume
kill $SRV
"$NF" log > "$L/nextflow-log.txt" 2>&1
# One fixture per observer and run: Tower routes (/trace/...) and nf-spectio (/spectio/events).
for n in flaky toolerr resume; do
  grep '"path": "/trace' "$L/$n.raw.jsonl" > "$L/$n.tower.raw.jsonl" || true
  grep '"path": "/spectio' "$L/$n.raw.jsonl" > "$L/$n.plugin.raw.jsonl" || true
  for o in tower plugin; do
    [ -s "$L/$n.$o.raw.jsonl" ] || continue
    slim=(); [ "$o" = plugin ] && slim=(--slim)
    python3 "$HERE/../normalise.py" "$L/$n.$o.raw.jsonl" "$HERE/../fixtures/nextflow-${V}_${o}_$n.jsonl" \
      --sub "$L=<launch>" --sub "$REPO=<repo>" --sub "$S=<scratch>" --sub "dummy-token-t2=<token>" "${slim[@]}"
  done
done
