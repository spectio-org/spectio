#!/usr/bin/env bash
# End to end in local mode (P2 §10.8, gap G7; P1 Done when, Local mode): Spectio from its wheel on this
# machine, `spectio init --local` and `spectio serve --detach` in a temporary home, the synthetic `happy`
# launched through the HTTP API and checked by tests/slurm/e2e_client.py (its local checks), with the
# expect lines of tests/scenarios/happy-local{,-snakemake}.yaml. Prints `RESULT e2e-local-<engine> pass|fail`
# and exits 1 on a fail.
#
#   bash tests/local/e2e.sh launch nextflow     -profile test,local
#   bash tests/local/e2e.sh launch snakemake    workflow profile local, chunks=2
#
# Needs uv, Node (web/dist is built when missing), tmux, Nextflow (it builds nf-spectio into the wheel) and,
# for snakemake, Snakemake: SPECTIO_ENGINES_NEXTFLOW_CMD and SPECTIO_ENGINES_SNAKEMAKE_CMD, else PATH.
# The server's tmux session lives on a private socket (TMUX_TMPDIR in the temporary home). On a pass the
# home is removed; on a fail it is kept for a look and its path printed.
set -euo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
# shellcheck source=dev/versions.env
. "$repo/dev/versions.env"
TIMEOUT=${E2E_TIMEOUT:-900}

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

case "${1:-}:${2:-}" in
  launch:nextflow | launch:snakemake) engine=$2 ;;
  *) sed -n '8,9p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
case $engine in
  nextflow) golden=nextflow-$NEXTFLOW_VERSION; scenario=happy-local.yaml
    args=(--profile test --profile local) ;;
  # chunks=2: what run_scenarios.py gives Snakemake, as Nextflow's profile test does, for the golden counts
  snakemake) golden=snakemake-$SNAKEMAKE_VERSION; scenario=happy-local-snakemake.yaml
    args=(--profile local --params '{"chunks": 2}') ;;
esac
nextflow=${SPECTIO_ENGINES_NEXTFLOW_CMD:-$(command -v nextflow || true)}
snakemake=${SPECTIO_ENGINES_SNAKEMAKE_CMD:-$(command -v snakemake || true)}
[ -n "$nextflow" ] || { echo "e2e-local: no nextflow (it builds nf-spectio into the wheel)" >&2; exit 1; }
[ "$engine" = nextflow ] || [ -n "$snakemake" ] || { echo "e2e-local: no snakemake" >&2; exit 1; }
command -v tmux >/dev/null || { echo "e2e-local: no tmux (spectio serve --detach needs it)" >&2; exit 1; }

home=$(mktemp -d "${TMPDIR:-/tmp}/spectio-e2e-local.XXXXXX")
chmod 700 "$home"
mkdir -m 700 "$home/data" "$home/db" "$home/runs" "$home/tmux" "$home/dist"
# HOME stays: uv's cache and Nextflow's ~/.nextflow are reused; Spectio's own home (config, database,
# runs, tmux socket) is the temporary directory.
export TMUX_TMPDIR=$home/tmux SPECTIO_CONFIG=$home/data/spectio.toml
rc=1
finish() {
  tmux kill-session -t =spectio-server 2>/dev/null || true
  if [ "$rc" = 0 ]; then rm -rf "$home"; else echo "e2e-local: kept $home" >&2; fi
  echo "RESULT e2e-local-$engine $([ "$rc" = 0 ] && echo pass || echo fail)"
}
trap finish EXIT

if [ ! -f "$repo/web/dist/index.html" ]; then
  log "building web/dist"
  npm --prefix "$repo/web" ci --no-audit --no-fund --ignore-scripts >/dev/null
  npm --prefix "$repo/web" run build >/dev/null
fi
log "building the wheels and installing spectio with its server into $home/tools"
(cd "$repo" && NEXTFLOW=$nextflow uv build --quiet --all-packages --python "$PYTHON_VERSION" --out-dir "$home/dist")
UV_TOOL_DIR=$home/tools UV_TOOL_BIN_DIR=$home/bin uv tool install --quiet --python "$PYTHON_VERSION" \
  "$home/dist/spectio-0.0.1-py3-none-any.whl" --with "$home/dist/spectio_server-0.0.1-py3-none-any.whl" \
  --with "$home/dist/spectio_sdk-0.0.1-py3-none-any.whl"
export PATH=$home/bin:$PATH
spectio --version

log "spectio init --local and serve --detach"
# The head runs the engine through a login shell (P1 Assumption 13): name the binaries.
spectio init --local --data-dir "$home/data" --db-dir "$home/db" --runs-root "$home/runs" \
  --nextflow "$nextflow" ${snakemake:+--snakemake "$snakemake"}
spectio serve --detach >/dev/null  # its link is never logged: the client asks for its own
python3 "$repo/tests/slurm/e2e_client.py" launch "$engine" --config "$SPECTIO_CONFIG" \
  --location "$repo/tests/pipelines/synthetic/$engine" \
  --golden "$repo/tests/pipelines/synthetic/golden/$golden/happy.tsv" "${args[@]}" \
  --scenario "$repo/tests/scenarios/$scenario" --timeout "$TIMEOUT" && rc=0 || rc=$?
if [ "$rc" != 0 ]; then
  tmux capture-pane -p -S -200 -t =spectio-server: 2>/dev/null || true
  for f in "$home"/runs/*/launch/.spectio/head.out; do
    [ -f "$f" ] && { echo "--- tail $f"; tail -n 40 "$f"; }
  done
fi
exit "$rc"
