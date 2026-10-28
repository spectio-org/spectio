#!/usr/bin/env bash
# Spike t4-ci: bring up k8s-mini / k8s-kueue (docs/specs/dev-environment-and-testing.md §4.2) on a
# GitHub-hosted ubuntu-24.04 runner. Throwaway; T4 proper would fold this into dev/scenario.py.
#
#   bash spikes/t4-ci/cluster.sh install        kind, kubectl, Nextflow 26.10.4 + 25.10.9 (pins and sha256
#                                               from dev/versions.env, checked like dev/bootstrap.sh does)
#   bash spikes/t4-ci/cluster.sh up mini|kueue  mini: 1 node; kueue: 1 control plane + 2 workers + Kueue
#   bash spikes/t4-ci/cluster.sh down
#
# Environment: SPIKE_MOUNT (host dir mounted into every node at the same path; default: parent of
# RUNNER_TEMP), CLUSTER (kind cluster name, default spx-t4).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
# shellcheck source=dev/versions.env
. "$repo/dev/versions.env"

CLUSTER=${CLUSTER:-spx-t4}
BIN=${SPIKE_BIN:-$HOME/.local/bin}
SPIKE_MOUNT=${SPIKE_MOUNT:-$(dirname "${RUNNER_TEMP:-/tmp/x}")}
# Kueue v0.20.3 = KUEUE_VERSION in dev/versions.env. The release publishes no checksum file for
# manifests.yaml; this is the sha256 of the download on 2026-10-28 ("computed", as versions.env says).
KUEUE_MANIFEST_SHA256=646840e4c4bcefd92ddcfcb233a55fe73416a0038ce9eb8d42322b2ef5fd1d54
# python:3.12 by digest, the image of the `k8s` profile (tests/pipelines/synthetic/nextflow/nextflow.config).
TASK_IMAGE=docker.io/library/python@sha256:98d8fe4e28bb2efeed9d9bce6a4705e80a6764367b65aea1dc4b96ded7b05620

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

fetch() { # URL SHA256 DEST
  local tmp
  tmp=$(mktemp "$3.XXXXXX")
  curl -fsSL --retry 3 -o "$tmp" "$1"
  echo "$2  $tmp" | sha256sum -c --status || { rm -f "$tmp"; echo "checksum failed: $1" >&2; return 1; }
  mv "$tmp" "$3"
}

install() {
  mkdir -p "$BIN"
  fetch "https://github.com/kubernetes-sigs/kind/releases/download/v$KIND_VERSION/kind-linux-amd64" "$KIND_SHA256" "$BIN/kind"
  fetch "https://dl.k8s.io/release/v$KUBECTL_VERSION/bin/linux/amd64/kubectl" "$KUBECTL_SHA256" "$BIN/kubectl"
  local nf=https://github.com/nextflow-io/nextflow/releases/download
  fetch "$nf/v$NEXTFLOW_VERSION/nextflow-$NEXTFLOW_VERSION-dist" "$NEXTFLOW_SHA256" "$BIN/nextflow"
  fetch "$nf/v$NEXTFLOW_25_10_VERSION/nextflow-$NEXTFLOW_25_10_VERSION-dist" "$NEXTFLOW_25_10_SHA256" "$BIN/nextflow-$NEXTFLOW_25_10_VERSION"
  chmod +x "$BIN"/kind "$BIN"/kubectl "$BIN"/nextflow "$BIN/nextflow-$NEXTFLOW_25_10_VERSION"
  [ -z "${GITHUB_PATH:-}" ] || echo "$BIN" >>"$GITHUB_PATH"
  export PATH="$BIN:$PATH"
  kind version; kubectl version --client | head -n 1
  nextflow -v; "nextflow-$NEXTFLOW_25_10_VERSION" -v
}

kind_config() { # mini|kueue
  printf 'kind: Cluster\napiVersion: kind.x-k8s.io/v1alpha4\nnodes:\n'
  local roles=(control-plane)
  [ "$1" = kueue ] && roles+=(worker worker)
  for role in "${roles[@]}"; do
    printf '  - role: %s\n    extraMounts:\n      - hostPath: %s\n        containerPath: %s\n' \
      "$role" "$SPIKE_MOUNT" "$SPIKE_MOUNT"
  done
}

up() {
  local shape=${1:?mini or kueue}
  log "docker: $(docker version --format '{{.Server.Version}}') cgroup v$(docker info --format '{{.CgroupVersion}}'); nproc $(nproc); $(free -g | awk '/Mem:/{print $2" GB RAM"}'); $(df -h / | awk 'NR==2{print $4" free on /"}')"
  kind_config "$shape" >"${RUNNER_TEMP:-/tmp}/kind-$CLUSTER.yaml"
  cat "${RUNNER_TEMP:-/tmp}/kind-$CLUSTER.yaml"
  local t=$SECONDS
  kind create cluster --name "$CLUSTER" --image "${KIND_NODE_IMAGE}" \
    --config "${RUNNER_TEMP:-/tmp}/kind-$CLUSTER.yaml" --wait 180s
  log "kind cluster $CLUSTER ($shape) up in $((SECONDS - t)) s"
  # Pre-pull the 1.6 GB task image on every node in the background (kubelet would pull it on first use).
  # With workers, the control plane is assumed tainted (no tasks there) [to be validated]: skip it.
  for node in $(kind get nodes --name "$CLUSTER" | grep -v -- "$([ "$shape" = kueue ] && echo -control-plane || echo '^$')"); do
    ( docker exec "$node" crictl pull "$TASK_IMAGE" >/dev/null 2>&1 && log "pulled task image on $node" ) &
  done
  kubectl apply -f "$here/manifests/base.yaml"
  if [ "$shape" = kueue ]; then
    t=$SECONDS
    fetch "https://github.com/kubernetes-sigs/kueue/releases/download/v$KUEUE_VERSION/manifests.yaml" \
      "$KUEUE_MANIFEST_SHA256" "${RUNNER_TEMP:-/tmp}/kueue-$KUEUE_VERSION.yaml"
    # server-side apply: the CRDs are too large for the client-side last-applied annotation
    kubectl apply --server-side -f "${RUNNER_TEMP:-/tmp}/kueue-$KUEUE_VERSION.yaml" >/dev/null
    kubectl -n kueue-system rollout status deployment/kueue-controller-manager --timeout=300s
    # the webhook answers a little after the deployment is Available: retry the queue objects
    for _ in $(seq 30); do
      kubectl apply -f "$here/manifests/kueue-queues.yaml" && break
      sleep 4
    done
    kubectl wait --for=condition=Available apiservice/v1beta2.visibility.kueue.x-k8s.io --timeout=180s
    log "Kueue v$KUEUE_VERSION ready in $((SECONDS - t)) s"
    kubectl api-versions | grep -i kueue
  fi
  wait
  kubectl get nodes -o wide
}

down() { kind delete cluster --name "$CLUSTER"; }

case "${1:-}" in
  install) install ;;
  up) up "${2:-}" ;;
  down) down ;;
  *) sed -n '2,12p' "$0"; exit 2 ;;
esac
