#!/bin/bash
# Pushes the spike server to the dev namespace and waits for the new pod.
# Run from a shell that is logged in to the cluster (kubectl OIDC opens the browser once).
set -euo pipefail
N=datasci-spectio-dev-internal
D=$(cd "$(dirname "$0")" && pwd)
kubectl -n $N create configmap runner-channel-spike --from-file=server.py="$D/server.py" \
  --dry-run=client -o yaml | kubectl -n $N apply -f -
kubectl -n $N rollout restart deploy/runner-channel-spike
kubectl -n $N rollout status deploy/runner-channel-spike --timeout=180s
