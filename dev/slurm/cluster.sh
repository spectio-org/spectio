#!/usr/bin/env bash
# The sind cluster profiles of docs/specs/dev-environment-and-testing.md §4.1.
#
#   bash dev/slurm/cluster.sh up mini    slurm-mini: controller, submitter, 1 worker, no accounting
#   bash dev/slurm/cluster.sh up site    slurm-site: + db (slurmdbd), partitions htc and bigmem, accounts
#                                        lab and capped (MaxJobs=1)
#   bash dev/slurm/cluster.sh up rest    slurm-rest: slurm-site + an api node (slurmrestd with JWT)
#   bash dev/slurm/cluster.sh down mini|site|rest
#
# The data directory $SLURM_DATA (default .scenarios/slurm) is mounted into every node at its own path. The
# tools must be installed in it, so that the engines run on the submitter as on a login node:
#   SPECTIO_HOME=$SLURM_DATA/tools SPECTIO_BIN=$SLURM_DATA/tools/bin \
#     UV_PYTHON_INSTALL_DIR=$SLURM_DATA/tools/python bash dev/bootstrap.sh
# Docker must run on cgroup v2, so not in a Claude Code cloud session (spike D2): this runs in CI
# (pipelines-slurm.yml) and on a laptop. No key is written to the host: sind creates the munge key and
# the JWT key inside the containers. The cluster is named after the profile, in the sind realm $SIND_REALM
# (default sind; dev/scenario.py sets spx-<id>).
# Built from spike t3-ci (docs/research/spike-t3-ci-2026-10-28.md).
set -euo pipefail
# shellcheck source=dev/lib.sh
. "$(dirname "$0")/../lib.sh"
here=$SPECTIO_REPO/dev/slurm
DATA=${SLURM_DATA:-$SPECTIO_REPO/.scenarios/slurm}
# DATA goes into sed and into the sind config: a plain absolute path only.
[[ $DATA =~ ^/[A-Za-z0-9._/-]+$ ]] || { echo "SLURM_DATA must be a plain absolute path: $DATA" >&2; exit 1; }

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

up() { # mini|site|rest
  local profile=$1 cfg=$DATA/$1.yaml src=$here/site.yaml t=$SECONDS
  [ "$profile" = mini ] && src=$here/mini.yaml
  [ -x "$DATA/tools/bin/nextflow" ] && [ -x "$DATA/tools/bin/snakemake" ] && [ -x "$DATA/tools/bin/sind" ] || {
    echo "the tools are not in $DATA/tools; see the header of $0" >&2; return 1; }
  chmod 755 "$DATA"
  # The JDK: $JAVA_HOME is often a symlink (runner tool cache), so copy what it points to.
  if [ ! -x "$DATA/tools/jdk/bin/java" ]; then
    local jdk
    jdk=$(readlink -f "${JAVA_HOME:-$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")}")
    [ -x "$jdk/bin/java" ] || { echo "no JDK found: set JAVA_HOME or put java on PATH" >&2; return 1; }
    mkdir -p "$DATA/tools/jdk" && cp -a "$jdk/." "$DATA/tools/jdk/"
  fi
  rm -rf "$DATA/synthetic" && cp -a "$SPECTIO_REPO/tests/pipelines/synthetic" "$DATA/synthetic"
  cp "$here/env.sh" "$DATA/env.sh"
  ensure_image "$SIND_NODE_IMAGE" && ensure_image "$SIND_DNS_IMAGE"
  sed -e "s|@NAME@|$profile|" -e "s|@IMAGE@|${SIND_NODE_IMAGE%@*}|" -e "s|@UID@|$(id -u)|" -e "s|@DATA@|$DATA|g" \
    "$src" >"$cfg"
  [ "$profile" = rest ] && printf '  - role: api                  # slurmrestd, JWT (Slurm 26.05 images only)\n    memory: 512m\n' >>"$cfg"
  sind create cluster --config "$cfg"
  log "sind cluster $profile up in $((SECONDS - t)) s"
  sind exec "$profile" -- sinfo -V
  sind exec "$profile" -- sinfo -o '%P %a %l %D %N %c %m'
  [ "$profile" = mini ] || sind exec "$profile" -- sacctmgr -n -P show assoc format=cluster,account,user,maxjobs
}

case "${1:-}:${2:-}" in
  up:mini | up:site | up:rest) up "$2" ;;
  down:mini | down:site | down:rest) sind delete cluster "$2" ;;
  *) sed -n '2,9p' "$0"; exit 2 ;;
esac
