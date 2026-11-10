#!/usr/bin/env bash
# Spike module-run (#161): `nextflow module run` with nf-spectio, on a local module and on one
# registry module. Prints the spool events and where the run wrote its files.
#   NEXTFLOW=/path/to/nextflow-26.10.4-dist spikes/module-run/nf_module_run.sh OUT_DIR
# Needs Java 21. The registry part needs https://registry.nextflow.io (and GitHub for the module
# files); it runs the registry module with -stub-run, so FastQC itself is not needed.
set -euo pipefail
OUT=$(mkdir -p "${1:?usage: nf_module_run.sh OUT_DIR}" && cd "$1" && pwd)
NF=${NEXTFLOW:-nextflow}
REPO=$(cd "$(dirname "$0")/../.." && pwd)
export NXF_HOME=${NXF_HOME:-$OUT/nxfhome} NXF_ANSI_LOG=false NXF_PLUGINS_DIR=$OUT/plugins
NEXTFLOW=$NF "$REPO/engine-bridges/nf-spectio/build.sh" "$NXF_PLUGINS_DIR"

events() { python3 -c '
import json, sys, glob
for f in sorted(glob.glob(sys.argv[1] + "/.spectio/events/*.jsonl")):
    for line in open(f):
        e = json.loads(line); d = e["data"]
        print(e["type"], d.get("runName"), d.get("sessionId"), d.get("process") or "", d.get("workDir") or "")
' "$1"; }

# 1. A local module made by `nextflow module create`, driven (SPECTIO_* set, -plugins).
mkdir -p "$OUT/local" && cd "$OUT/local"
[ -d modules/spectio/hello ] || "$NF" module create spectio/hello
SPECTIO_RUN_ID=run_01K8T6NFSPEC000000000000M1 SPECTIO_LAUNCH_N=1 SPECTIO_SPOOL_DIR=$PWD/.spectio/events \
  "$NF" module run ./modules/spectio/hello -plugins nf-spectio@0.0.1 -with-trace -name spk-local --greeting Hi
events "$PWD"; ls -a

# 2. The same module from a terminal: NXF_PLUGINS_DEFAULT, no SPECTIO_* variable (architecture §13.8).
mkdir -p "$OUT/term" && cd "$OUT/term"
NXF_PLUGINS_DEFAULT=nf-spectio@0.0.1 "$NF" module run "$OUT/local/modules/spectio/hello" --greeting Yo
events "$PWD"

# 3. A registry module, pinned, in stub mode, its inputs from a params file.
mkdir -p "$OUT/registry" && cd "$OUT/registry"
"$NF" module view -o json nf-core/fastqc > fastqc-view.json
printf '@r\nACGT\n+\nIIII\n' | gzip > s1.fastq.gz
echo '{"meta":{"id":"pj"},"reads":"s1.fastq.gz"}' > params.json
SPECTIO_RUN_ID=run_01K8T6NFSPEC000000000000M2 SPECTIO_LAUNCH_N=1 SPECTIO_SPOOL_DIR=$PWD/.spectio/events \
  "$NF" module run nf-core/fastqc -version 0.0.0-6d1763b -stub-run -plugins nf-spectio@0.0.1 -with-trace \
  -params-file params.json
events "$PWD"; cat modules/nf-core/fastqc/.module-info; ls -a
