#!/usr/bin/env bash
# The kind cluster profiles of docs/specs/dev-environment-and-testing.md §4.2.
#
#   bash dev/k8s/cluster.sh up mini     k8s-mini: 1 node, namespace spectio-work with a ResourceQuota
#   bash dev/k8s/cluster.sh up kueue    k8s-kueue: 1 control plane + 2 workers, the same namespace, Kueue
#                                       (KUEUE_VERSION), a ClusterQueue and a LocalQueue, the visibility API
#   bash dev/k8s/cluster.sh down mini|kueue
#
# Tools (kind, kubectl) come from dev/bootstrap.sh at the pins of dev/versions.env. Docker must run on
# cgroup v2, so not in a Claude Code cloud session (spike D2): this runs in CI (pipelines-k8s.yml) and on a laptop.
# The repository is mounted into every node at its own path (kind extraMounts), so task pods that mount it
# as a hostPath see the pipeline and its work directory under .scenarios/ (tests/k8s/kind.config).
# The kind cluster is named after the profile (k8s-mini, k8s-kueue), or $CLUSTER.
# Built from spike t4-ci (docs/research/spike-t4-ci-2026-10-28.md).
set -euo pipefail
# shellcheck source=dev/lib.sh
. "$(dirname "$0")/../lib.sh"
here=$SPECTIO_REPO/dev/k8s
# The task image: params.python_image of the synthetic pipeline (its docker and k8s profiles), by digest.
TASK_IMAGE=$(grep -o -m1 "^params.python_image = 'python:3.12@sha256:[0-9a-f]\{64\}" \
  "$SPECTIO_REPO/tests/pipelines/synthetic/nextflow/nextflow.config") || { echo "no params.python_image digest" >&2; exit 1; }
TASK_IMAGE=docker.io/library/python@${TASK_IMAGE#*@}

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

kind_config() { # mini|kueue
  printf 'kind: Cluster\napiVersion: kind.x-k8s.io/v1alpha4\nnodes:\n'
  local roles=(control-plane)
  [ "$1" = kueue ] && roles+=(worker worker)
  for role in "${roles[@]}"; do
    printf '  - role: %s\n    extraMounts:\n      - hostPath: %s\n        containerPath: %s\n' \
      "$role" "$SPECTIO_REPO" "$SPECTIO_REPO"
  done
}

install_kueue() {
  local manifest=$SPECTIO_REPO/.scenarios/kueue-$KUEUE_VERSION.yaml t=$SECONDS
  mkdir -p "${manifest%/*}"
  curl -fsSL --retry 3 -o "$manifest" \
    "https://github.com/kubernetes-sigs/kueue/releases/download/v$KUEUE_VERSION/manifests.yaml"
  echo "$KUEUE_MANIFEST_SHA256  $manifest" | sha256sum -c --status || { echo "checksum failed: $manifest" >&2; return 1; }
  # server-side apply: the CRDs are too large for the client-side last-applied annotation
  kubectl apply --server-side -f "$manifest" >/dev/null
  kubectl -n kueue-system rollout status deployment/kueue-controller-manager --timeout=300s
  # the webhook answers a little after the deployment is Available: retry the queue objects
  for _ in $(seq 30); do
    kubectl apply -f "$here/kueue-queues.yaml" && break
    sleep 4
  done
  kubectl get -f "$here/kueue-queues.yaml" >/dev/null # fails if the retries never applied them
  kubectl wait --for=condition=Available apiservice/v1beta2.visibility.kueue.x-k8s.io --timeout=180s
  log "Kueue v$KUEUE_VERSION ready in $((SECONDS - t)) s"
}

up() { # mini|kueue
  local shape=$1 cluster=${CLUSTER:-k8s-$1} cfg t=$SECONDS
  cfg=$(mktemp)
  kind_config "$shape" >"$cfg"
  kind create cluster --name "$cluster" --image "$KIND_NODE_IMAGE" --config "$cfg" --wait 180s
  rm -f "$cfg"
  log "kind cluster $cluster up in $((SECONDS - t)) s"
  # Pre-pull the 1.6 GB task image in the background; with workers, skip the control plane (no tasks there).
  for node in $(kind get nodes --name "$cluster"); do
    [ "$shape" = kueue ] && [[ $node == *-control-plane ]] && continue
    ( docker exec "$node" crictl pull "$TASK_IMAGE" >/dev/null && log "task image pulled on $node" ) &
  done
  kubectl apply -f "$here/base.yaml"
  [ "$shape" = mini ] || install_kueue
  wait
  kubectl get nodes -o wide
}

case "${1:-}:${2:-}" in
  up:mini | up:kueue) up "$2" ;;
  down:mini | down:kueue) kind delete cluster --name "${CLUSTER:-k8s-$2}" ;;
  *) sed -n '2,8p' "$0"; exit 2 ;;
esac
