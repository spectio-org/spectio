#!/usr/bin/env bash
# End to end on a SLURM cluster (P1 Task 22; docs/specs/dev-environment-and-testing.md §15.3 and §4.1):
# Spectio from its wheel on the login node, a head per run in its tmux session, the engines' task jobs
# in SLURM. Each launch prints `RESULT e2e-launch-<engine> pass|fail` and exits 1 on a fail.
#
#   bash tests/slurm/e2e.sh install            build the wheels and install spectio with its server into
#                                              $SLURM_DATA/tools (bin/spectio); needs Node, uv and Nextflow
#   bash tests/slurm/e2e.sh launch nextflow    the synthetic happy, -profile test,slurm
#   bash tests/slurm/e2e.sh launch snakemake   the synthetic happy, workflow profile slurm
#
# CLUSTER=mini (the default) is sind's slurm-mini (`bash dev/slurm/cluster.sh up mini`): every command runs as
# user spx on the submitter through `sind exec`, partition htc. CLUSTER=native is the one-node Slurm of
# dev/slurm/native.sh (cloud sessions, where sind cannot run): commands run on this host as $E2E_USER
# (default spx, created when missing; this needs root), partition debug, which the copied pipelines' slurm
# profiles are rewritten to. Either way the tools are in $SLURM_DATA/tools (dev/bootstrap.sh with
# SPECTIO_HOME=$SLURM_DATA/tools SPECTIO_BIN=$SLURM_DATA/tools/bin UV_PYTHON_INSTALL_DIR=$SLURM_DATA/tools/python,
# then `e2e.sh install`), and in native mode $SLURM_DATA must be a path $E2E_USER can reach (not under /root).
# Each launch starts from new directories under $SLURM_DATA/e2e/<engine> and a new database, and stops its
# server at the end; the checks are those of tests/slurm/e2e_client.py.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
# shellcheck source=dev/versions.env
. "$repo/dev/versions.env"
DATA=${SLURM_DATA:-$repo/.scenarios/slurm}
CLUSTER=${CLUSTER:-mini}
USER_=${E2E_USER:-spx}
TIMEOUT=${E2E_TIMEOUT:-1800}
[[ $DATA =~ ^/[A-Za-z0-9._/-]+$ ]] || { echo "SLURM_DATA must be a plain absolute path: $DATA" >&2; exit 1; }
case $CLUSTER in
  mini) PARTITION=htc ;;
  native) PARTITION=debug ;;
  *) echo "CLUSTER must be mini or native, not $CLUSTER" >&2; exit 2 ;;
esac

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
# inc HOME CMD...: CMD as the run's user on the login node, with the tools on PATH (env.sh) and HOME as given.
# On the submitter, sind exec's own environment (the node's PATH); here, nothing of this shell's but HOME and
# the system PATH.
# shellcheck disable=SC2016  # expanded by the inner bash
inc() {
  local home=$1 script='. "$0/env.sh" && cd "$0" && "$@"'
  shift
  if [ "$CLUSTER" = mini ]; then
    sind exec "$CLUSTER" -u spx -- env HOME="$home" bash -c "$script" "$DATA" "$@"
  else
    runuser -u "$USER_" -- env -i HOME="$home" PATH=/usr/local/bin:/usr/bin:/bin bash -c "$script" "$DATA" "$@"
  fi
}

install() {
  local dist=$DATA/dist
  export UV_PYTHON_INSTALL_DIR=${UV_PYTHON_INSTALL_DIR:-$DATA/tools/python}
  [ -x "$DATA/tools/bin/nextflow" ] || { echo "no $DATA/tools/bin/nextflow: run dev/bootstrap.sh first (see $0)" >&2; return 1; }
  log "building web/dist and the wheels"
  npm --prefix "$repo/web" ci --no-audit --no-fund --ignore-scripts >/dev/null
  npm --prefix "$repo/web" run build >/dev/null
  rm -rf "$dist"
  (cd "$repo" && NEXTFLOW=$DATA/tools/bin/nextflow uv build --quiet --all-packages --python "$PYTHON_VERSION" --out-dir "$dist")
  log "installing spectio, its server and SDK into $DATA/tools"
  UV_TOOL_DIR=$DATA/tools/uv-tools UV_TOOL_BIN_DIR=$DATA/tools/bin uv tool install --quiet --force \
    --python "$PYTHON_VERSION" "$dist/spectio-0.0.1-py3-none-any.whl" \
    --with "$dist/spectio_server-0.0.1-py3-none-any.whl" --with "$dist/spectio_sdk-0.0.1-py3-none-any.whl"
  "$DATA/tools/bin/spectio" --version
}

# What dev/slurm/cluster.sh up does for sind, here for the native cluster: the JDK, the pipelines and env.sh in
# $SLURM_DATA, the pipelines' partition htc replaced by debug in the copy, and the run's user.
native_prepare() {
  [ "$(id -u)" = 0 ] || { echo "CLUSTER=native needs root (runuser, useradd)" >&2; return 1; }
  sinfo -h -p "$PARTITION" -o %a | grep -qx up || { echo "no partition $PARTITION up: bash dev/slurm/native.sh up" >&2; return 1; }
  id -u "$USER_" >/dev/null 2>&1 || useradd -m -s /bin/bash "$USER_"
  if [ ! -x "$DATA/tools/jdk/bin/java" ]; then
    local jdk
    jdk=$(readlink -f "${JAVA_HOME:-$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")}")
    mkdir -p "$DATA/tools/jdk" && cp -a "$jdk/." "$DATA/tools/jdk/"
  fi
  rm -rf "$DATA/synthetic" && cp -a "$repo/tests/pipelines/synthetic" "$DATA/synthetic"
  sed -i 's/\bhtc\b/debug/' "$DATA/synthetic/nextflow/nextflow.config" "$DATA/synthetic/snakemake/profiles/slurm/config.yaml"
  cp "$repo/dev/slurm/env.sh" "$DATA/env.sh"
  chmod -R a+rX "$DATA/tools" "$DATA/synthetic" "$DATA/env.sh"
}

launch() { # nextflow|snakemake
  local engine=$1 e=$DATA/e2e/$1 db=/tmp/spectio-e2e-$1-db golden profiles=() scenario=() rc=0
  local cfg=$DATA/e2e/$1/data/spectio.toml
  case $engine in
    nextflow) golden=nextflow-$NEXTFLOW_VERSION; profiles=(--profile test --profile slurm)
      scenario=(--scenario "$DATA/e2e/happy-slurm-mini.yaml") ;;
    # chunks=2: what run_scenarios.py gives Snakemake, as Nextflow's profile test does, for the golden counts
    snakemake) golden=snakemake-$SNAKEMAKE_VERSION; profiles=(--profile slurm --params '{"chunks": 2}') ;;
    *) echo "launch nextflow|snakemake, not $engine" >&2; return 2 ;;
  esac
  [ "$CLUSTER" = mini ] || native_prepare
  [ -x "$DATA/tools/bin/spectio" ] || { echo "no $DATA/tools/bin/spectio: run $0 install" >&2; return 1; }
  # The client, its golden and the scenario go into the data directory, which the nodes mount.
  rm -rf "$e"
  mkdir -p "$e/home" "$e/data" "$e/runs" "$e/bin"
  chmod 700 "$e/home" "$e/data" "$e/runs"
  cp "$repo/tests/slurm/e2e_client.py" "$repo/tests/scenarios/happy-slurm-mini.yaml" "$DATA/e2e/"
  cp "$repo/tests/pipelines/synthetic/golden/$golden/happy.tsv" "$e/golden.tsv"
  # The engines through env.sh: the head runs them under `env -i` and a login shell (P1 Assumption 13),
  # whose PATH has neither them nor Java here.
  for tool in nextflow snakemake; do
    printf '#!/usr/bin/env bash\n. %s/env.sh\nexec %s/tools/bin/%s "$@"\n' "$DATA" "$DATA" "$tool" >"$e/bin/$tool"
    chmod 755 "$e/bin/$tool"
  done
  [ "$CLUSTER" = mini ] || chown -R "$USER_" "$DATA/e2e"
  inc "$e/home" command -v tmux >/dev/null || { echo "no tmux on the login node" >&2; return 1; }
  inc "$e/home" rm -rf "$db"
  log "spectio init and serve --detach as $([ "$CLUSTER" = mini ] && echo spx || echo "$USER_"), partition $PARTITION"
  inc "$e/home" env SPECTIO_CONFIG="$cfg" SPECTIO_RUNNER_HEAD_WATCH_S=5 \
    SPECTIO_ENGINES_EXTRA_ARGS_SNAKEMAKE="--slurm-init-seconds-before-status-checks 5" \
    spectio init --data-dir "$e/data" --db-dir "$db" --runs-root "$e/runs" --partition "$PARTITION" \
    --nextflow "$e/bin/nextflow" --snakemake "$e/bin/snakemake"
  # A first link is printed: never into the log, the client asks for its own.
  inc "$e/home" env SPECTIO_CONFIG="$cfg" spectio serve --detach >/dev/null
  inc "$e/home" env SPECTIO_CONFIG="$cfg" python3 "$DATA/e2e/e2e_client.py" launch "$engine" --config "$cfg" \
    --location "$DATA/synthetic/$engine" --golden "$e/golden.tsv" "${profiles[@]}" "${scenario[@]}" \
    --timeout "$TIMEOUT" || rc=$?
  if [ "$rc" != 0 ]; then
    echo "::group::server pane"; inc "$e/home" tmux capture-pane -p -S -200 -t =spectio-server: || true; echo "::endgroup::"
    for f in "$e"/runs/*/launch/.spectio/head.out; do
      [ -f "$f" ] && { echo "::group::tail $f"; tail -n 40 "$f"; echo "::endgroup::"; }
    done
  fi
  inc "$e/home" tmux kill-session -t =spectio-server || true
  echo "RESULT e2e-launch-$engine $([ "$rc" = 0 ] && echo pass || echo fail)"
  return "$rc"
}

case "${1:-}:${2:-}" in
  install:) install ;;
  launch:nextflow | launch:snakemake) launch "$2" ;;
  *) sed -n '2,9p' "$0"; exit 2 ;;
esac
