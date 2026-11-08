#!/usr/bin/env bash
# Run the synthetic pipeline (tests/pipelines/synthetic, profile test,local) with nf-spectio
# writing the spool, as a driven run's head would (api §14.1). Exits with Nextflow's code.
#
#   run_local.sh LAUNCH_DIR [NEXTFLOW_ARGS...]     e.g. --fail_mode exit --fail_process COMPARE
#   run_local.sh --terminal LAUNCH_DIR [NEXTFLOW_ARGS...]
#
# Env: NEXTFLOW (default nextflow), SPECTIO_RUN_ID, SPECTIO_LAUNCH_N (default 1),
# SPECTIO_SPOOL_DIR (default LAUNCH_DIR/.spectio/events). The plugin is built into a temporary
# NXF_PLUGINS_DIR, removed on exit; ~/.nextflow/plugins is not touched. --terminal: a run started
# by hand (architecture §13.8), no SPECTIO_* variable, the plugin enabled with
# NXF_PLUGINS_DEFAULT=nf-spectio@<ver> as the guide says, never -plugins.
set -euo pipefail
TERMINAL=
if [ "${1:-}" = --terminal ]; then TERMINAL=1; shift; fi
[ $# -ge 1 ] || { echo "usage: run_local.sh [--terminal] LAUNCH_DIR [NEXTFLOW_ARGS...]" >&2; exit 2; }
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
LAUNCH=$(cd "$1" && pwd)
shift
NF=${NEXTFLOW:-nextflow}

PLUGINS=$(mktemp -d)
trap 'rm -rf "$PLUGINS"' EXIT
NEXTFLOW=$NF "$HERE/../build.sh" "$PLUGINS"

export NXF_PLUGINS_DIR=$PLUGINS NXF_ANSI_LOG=false
cd "$LAUNCH"
PIPELINE=$REPO/tests/pipelines/synthetic/nextflow/main.nf
if [ -n "$TERMINAL" ]; then
  unset SPECTIO_RUN_ID SPECTIO_LAUNCH_N SPECTIO_SPOOL_DIR
  NXF_PLUGINS_DEFAULT=nf-spectio@0.0.1 "$NF" -q run "$PIPELINE" -profile test,local \
    --outdir results "$@"
  exit
fi
export SPECTIO_RUN_ID=${SPECTIO_RUN_ID:?set SPECTIO_RUN_ID (run_ and a ULID)}
export SPECTIO_LAUNCH_N=${SPECTIO_LAUNCH_N:-1}
export SPECTIO_SPOOL_DIR=${SPECTIO_SPOOL_DIR:-$LAUNCH/.spectio/events}
"$NF" -q run "$PIPELINE" -profile test,local --outdir results -plugins "nf-spectio@0.0.1" "$@"
