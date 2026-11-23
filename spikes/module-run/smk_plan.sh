#!/usr/bin/env bash
# Spike module-run (#161): the jobs Snakemake plans for a rule target, --until and --allowed-rules
# on the synthetic corpus pipeline, from an empty working directory (dry run, nothing executes).
#   SMK=/path/to/snakemake spikes/module-run/smk_plan.sh RULE
set -euo pipefail
RULE=${1:?usage: smk_plan.sh RULE}
SMK=${SMK:-snakemake}
REPO=$(cd "$(dirname "$0")/../.." && pwd)
WF=$REPO/tests/pipelines/synthetic/snakemake/workflow/Snakefile
for mode in "$RULE" "--until $RULE" "--allowed-rules $RULE" "$RULE --allowed-rules $RULE" "--until $RULE --allowed-rules $RULE" "--forcerun $RULE"; do
  D=$(mktemp -d)
  echo "=== snakemake -n $mode"
  # shellcheck disable=SC2086
  "$SMK" -s "$WF" -d "$D" -n $mode 2>&1 | awk '/^Job stats:/{p=1} p&&/^$/{exit} p' || true
  "$SMK" -s "$WF" -d "$D" -n $mode 2>&1 | grep -E "Nothing to be done|MissingInput|Error" | head -3 || true
  rm -rf "$D"
done
