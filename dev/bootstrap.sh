#!/usr/bin/env bash
# Install the pinned toolchain of dev/versions.env (docs/specs/dev-environment-and-testing.md §1).
# The same script runs in the Claude Code cloud setup script, in CI and on a laptop.
#
#   bash dev/bootstrap.sh          install or update the tools; touches no daemon
#   bash dev/bootstrap.sh --ci     also start dockerd if needed and pre-pull the doctor's images
#
# Idempotent: a tool already at its pinned version is not downloaded again. Every download is
# checked against its sha256 in versions.env. Tools go to $SPECTIO_HOME (default
# ~/.local/share/spectio) and their commands are linked into $SPECTIO_BIN (default ~/.local/bin).
# Prerequisites, not installed here: Docker, Java 21, curl, tar, xz, sha256sum (dev/doctor.sh checks them).
# shellcheck disable=SC2317  # the install_* functions run through job(), which shellcheck cannot follow
set -euo pipefail
# shellcheck source=dev/lib.sh
. "$(dirname "$0")/lib.sh"

ci=0
case "${1:-}" in
  --ci) ci=1 ;;
  "") ;;
  *) echo "usage: bash dev/bootstrap.sh [--ci]" >&2; exit 2 ;;
esac
[ "$(uname -sm)" = "Linux x86_64" ] || { echo "bootstrap: only Linux x86_64 is supported (checksums are for linux/amd64)" >&2; exit 1; }
for cmd in curl tar xz sha256sum; do
  command -v "$cmd" >/dev/null || { echo "bootstrap: $cmd is required" >&2; exit 1; }
done

pkgs=$SPECTIO_HOME/pkgs
logs=$SPECTIO_HOME/logs
mkdir -p "$pkgs" "$logs" "$SPECTIO_BIN"

# fetch URL SHA256 DEST: download to a temporary file, check it, then move it into place.
fetch() {
  local tmp
  tmp=$(mktemp "$3.XXXXXX")
  if curl -fsSL --retry 3 -o "$tmp" "$1" && echo "$2  $tmp" | sha256sum -c --status; then
    mv "$tmp" "$3"
  else
    rm -f "$tmp"
    echo "download or checksum failed: $1" >&2
    return 1
  fi
}

# install_bin TOOL VERSION URL SHA256 [LINK]: a single executable, linked as LINK (default TOOL).
install_bin() {
  local dest=$pkgs/$1-$2/$1
  if [ ! -x "$dest" ]; then
    mkdir -p "${dest%/*}"
    fetch "$3" "$4" "$dest"
    chmod +x "$dest"
  fi
  ln -sfn "$dest" "$SPECTIO_BIN/${5:-$1}"
}

# install_tar TOOL VERSION URL SHA256 PATH...: a tarball (top directory stripped); each PATH
# inside it is linked into SPECTIO_BIN under its base name.
install_tar() {
  local dir=$pkgs/$1-$2 url=$3 sha=$4 path
  shift 4
  if [ ! -d "$dir" ]; then
    fetch "$url" "$sha" "$dir.tar"
    mkdir -p "$dir.tmp"
    tar -xf "$dir.tar" -C "$dir.tmp" --strip-components=1
    mv "$dir.tmp" "$dir"
    rm -f "$dir.tar"
  fi
  for path in "$@"; do ln -sfn "$dir/$path" "$SPECTIO_BIN/${path##*/}"; done
}

install_uv() {
  [ "$(uv --version 2>/dev/null | cut -d' ' -f2)" = "$UV_VERSION" ] && return 0
  install_tar uv "$UV_VERSION" \
    "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-gnu.tar.gz" \
    "$UV_SHA256" uv uvx
}

install_python_and_snakemake() {
  install_uv
  # --no-bin: do not put python3.13 on PATH in front of the system Python.
  uv python install --no-bin "$PYTHON_VERSION"
  uv tool install --python "$PYTHON_VERSION" "snakemake==$SNAKEMAKE_VERSION" \
    --with "snakemake-executor-plugin-slurm==$SNAKEMAKE_EXECUTOR_SLURM_VERSION" \
    --with "snakemake-executor-plugin-kubernetes==$SNAKEMAKE_EXECUTOR_KUBERNETES_VERSION"
}

install_node_and_playwright() {
  if [ "$(node --version 2>/dev/null)" != "v$NODE_VERSION" ]; then
    install_tar node "$NODE_VERSION" \
      "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.xz" \
      "$NODE_SHA256" bin/node bin/npm bin/npx
  fi
  if [ "$(node -p "require('playwright/package.json').version" 2>/dev/null)" != "$PLAYWRIGHT_VERSION" ]; then
    npm install --prefix "$NPM_PREFIX" --save-exact --no-audit --no-fund "playwright@$PLAYWRIGHT_VERSION"
  fi
  # Cloud sessions ship this version's Chromium (PLAYWRIGHT_BROWSERS_PATH); elsewhere download it.
  if ! node -e "process.exit(require('fs').existsSync(require('playwright').chromium.executablePath()) ? 0 : 1)"; then
    if [ "$ci" = 1 ]; then
      node "$NPM_PREFIX/node_modules/playwright/cli.js" install --with-deps chromium
    else
      node "$NPM_PREFIX/node_modules/playwright/cli.js" install chromium
    fi
  fi
}

install_nextflow() {
  local nf=https://github.com/nextflow-io/nextflow/releases/download
  install_bin nextflow "$NEXTFLOW_VERSION" "$nf/v$NEXTFLOW_VERSION/nextflow-$NEXTFLOW_VERSION-dist" "$NEXTFLOW_SHA256"
  install_bin nextflow "$NEXTFLOW_25_10_VERSION" "$nf/v$NEXTFLOW_25_10_VERSION/nextflow-$NEXTFLOW_25_10_VERSION-dist" \
    "$NEXTFLOW_25_10_SHA256" "nextflow-$NEXTFLOW_25_10_VERSION"
  install_bin nextflow "$NEXTFLOW_25_04_VERSION" "$nf/v$NEXTFLOW_25_04_VERSION/nextflow-$NEXTFLOW_25_04_VERSION-dist" \
    "$NEXTFLOW_25_04_SHA256" "nextflow-$NEXTFLOW_25_04_VERSION"
}

install_cluster_tools() {
  install_bin sind "$SIND_VERSION" \
    "https://github.com/GSI-HPC/sind/releases/download/v$SIND_VERSION/sind-linux-amd64" "$SIND_SHA256"
  install_bin kind "$KIND_VERSION" \
    "https://github.com/kubernetes-sigs/kind/releases/download/v$KIND_VERSION/kind-linux-amd64" "$KIND_SHA256"
  install_bin kubectl "$KUBECTL_VERSION" \
    "https://dl.k8s.io/release/v$KUBECTL_VERSION/bin/linux/amd64/kubectl" "$KUBECTL_SHA256"
  install_tar helm "$HELM_VERSION" "https://get.helm.sh/helm-v$HELM_VERSION-linux-amd64.tar.gz" "$HELM_SHA256" helm
}

# Run each job in the background with its own log; report every job, fail if any failed.
names=() pids=()
job() {
  names+=("$1")
  ( set -e; "${@:2}" ) >"$logs/$1.log" 2>&1 &
  pids+=($!)
}

job python+snakemake install_python_and_snakemake
job node+playwright install_node_and_playwright
job nextflow install_nextflow
job sind+kind+kubectl+helm install_cluster_tools
failed=0
if [ "$ci" = 1 ] && ! ensure_dockerd; then
  echo "FAIL  docker (the daemon is needed to pre-pull images)"
  failed=1
elif [ "$ci" = 1 ]; then
  job image:hello-world ensure_image "$HELLO_WORLD_IMAGE"
  if cgroup_v1; then
    echo "bootstrap: Docker runs on cgroup v1, so the sind and kind images are not pre-pulled (spike D2)"
  else
    for image in "$BUSYBOX_IMAGE" "$KIND_NODE_IMAGE" "$SIND_NODE_IMAGE" "$SIND_DNS_IMAGE"; do
      name=${image%@*}
      job "image:${name##*/}" ensure_image "$image"
    done
  fi
fi

for i in "${!names[@]}"; do
  if wait "${pids[$i]}"; then
    echo "ok    ${names[$i]}"
  else
    echo "FAIL  ${names[$i]} (log: $logs/${names[$i]}.log)"
    tail -n 5 "$logs/${names[$i]}.log" | sed 's/^/      /'
    failed=1
  fi
done

# GitHub Actions: put the tools on PATH for the next steps.
[ -z "${GITHUB_PATH:-}" ] || echo "$SPECTIO_BIN" >>"$GITHUB_PATH"

status="done"
[ "$failed" = 0 ] || status=FAILED
echo "bootstrap: $status in ${SECONDS}s; tools in $SPECTIO_HOME, commands in $SPECTIO_BIN"
if [ "$ci" = 1 ] && [ "$SECONDS" -gt 300 ]; then
  echo "bootstrap: WARNING: over the 5-minute budget of a cached cloud setup script (§2)"
fi
exit "$failed"
