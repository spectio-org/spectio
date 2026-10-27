# shellcheck shell=bash
# Shared by dev/bootstrap.sh and dev/doctor.sh; sourced, never run.
# Spec: docs/specs/dev-environment-and-testing.md §1 (toolchain) and §2 (cloud sessions).

SPECTIO_REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=dev/versions.env
. "$SPECTIO_REPO/dev/versions.env"

# Tools live in SPECTIO_HOME, one directory per tool and version; their commands are linked
# into SPECTIO_BIN, which most shells already have on PATH.
SPECTIO_HOME=${SPECTIO_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/spectio}
SPECTIO_BIN=${SPECTIO_BIN:-$HOME/.local/bin}
NPM_PREFIX=$SPECTIO_HOME/npm
export PATH="$SPECTIO_BIN:$PATH"
export NODE_PATH=$NPM_PREFIX/node_modules

docker_up() { docker info >/dev/null 2>&1; }

# Start dockerd where nothing else will: as root on a machine without systemd, as in a Claude
# Code cloud session, where Docker is installed but not running (spike D2). The mirror avoids
# Docker Hub's anonymous rate limit on the shared egress (spike D2, "Network").
ensure_dockerd() {
  docker_up && return 0
  if [ "$(id -u)" = 0 ] && [ ! -d /run/systemd/system ] && command -v dockerd >/dev/null; then
    mkdir -p "$SPECTIO_HOME"
    setsid nohup dockerd --registry-mirror=https://mirror.gcr.io \
      >"$SPECTIO_HOME/dockerd.log" 2>&1 </dev/null &
    for _ in $(seq 30); do docker_up && return 0; sleep 1; done
  fi
  echo "the Docker daemon is not running; start it (log: $SPECTIO_HOME/dockerd.log)" >&2
  return 1
}

# Docker runs containers on cgroup v1: sind and kind cannot start there (spike D2).
cgroup_v1() { [ "$(docker info --format '{{.CgroupVersion}}' 2>/dev/null)" = 1 ]; }

# ensure_image NAME:TAG@sha256:DIGEST
# Makes NAME:TAG a local image with exactly that digest. Docker Hub images are pulled from
# Google's mirror first, then from Docker Hub, both by digest.
ensure_image() {
  local name=${1%@*} digest=${1#*@} repo src
  repo=${name%:*}
  docker image inspect --format '{{join .RepoDigests " "}}' "$name" 2>/dev/null |
    grep -q "@$digest" && return 0
  case $repo in
    *.*/*) src=$repo ;;                          # a registry host is given (ghcr.io/...)
    */*) src=mirror.gcr.io/$repo ;;
    *) src=mirror.gcr.io/library/$repo ;;
  esac
  if ! docker pull -q "$src@$digest" >/dev/null; then
    [ "$src" != "$repo" ] || return 1
    src=$repo
    docker pull -q "$src@$digest" >/dev/null || return 1
  fi
  docker tag "$src@$digest" "$name"
}
