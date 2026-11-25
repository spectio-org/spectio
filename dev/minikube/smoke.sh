#!/usr/bin/env bash
# The synthetic pipeline `happy` through the API of the Spectio in minikube, for each engine (default both):
#
#   bash dev/minikube/smoke.sh [nextflow|snakemake]...
#
# 1. kubectl port-forward, then GET / and GET /api/v1/me from the host: the server answers (the second one
#    needs a session, so 401 is the right answer; a refused connection is not).
# 2. tests/slurm/e2e_client.py, as tests/local/e2e.sh uses it, runs inside the pod: it signs in with a link it asks
#    `spectio login --print-link --json` for (never printed), launches the run with POST /api/v1/runs on the
#    `local` environment, polls it to its end and checks its tasks against the golden file. It prints
#    `ok` or `FAIL` per check.
# The fixtures are copied into the pod's /tmp (an emptyDir), not into the image.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
# shellcheck source=dev/versions.env
. "$repo/dev/versions.env"
ctx=${MINIKUBE_PROFILE:-spectio}
k() { kubectl --context "$ctx" -n spectio "$@"; }
engines=("$@")
[ ${#engines[@]} -gt 0 ] || engines=(nextflow snakemake)

pf_port=${PF_PORT:-18080}
kubectl --context "$ctx" -n spectio port-forward svc/spectio "$pf_port:8080" >/dev/null 2>&1 &
pf=$!
trap 'kill $pf 2>/dev/null || true' EXIT
for _ in $(seq 20); do curl -s -o /dev/null "http://127.0.0.1:$pf_port/" && break; sleep 1; done
echo "GET /            -> HTTP $(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$pf_port/")"
echo "GET /api/v1/me   -> HTTP $(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$pf_port/api/v1/me")  (no session: 401 expected)"

COPYFILE_DISABLE=1 tar --no-xattrs -C "$repo" -cf - tests/slurm/e2e_client.py tests/pipelines/synthetic tests/scenarios |
  k exec -i deploy/spectio -c spectio -- sh -c 'rm -rf /tmp/smoke && mkdir -p /tmp/smoke && tar -C /tmp/smoke -xf -'
rc=0
for engine in "${engines[@]}"; do
  case $engine in
    nextflow) golden=nextflow-$NEXTFLOW_VERSION; scenario=happy-local.yaml; args=(--profile test --profile local) ;;
    snakemake) golden=snakemake-$SNAKEMAKE_VERSION; scenario=happy-local-snakemake.yaml
      args=(--profile local --params '{"chunks": 2}') ;;
    *) echo "unknown engine $engine" >&2; exit 2 ;;
  esac
  echo "===== $engine"
  k exec deploy/spectio -c spectio -- python3 /tmp/smoke/tests/slurm/e2e_client.py launch "$engine" \
    --config /var/lib/spectio/data/spectio.toml --location "/tmp/smoke/tests/pipelines/synthetic/$engine" \
    --golden "/tmp/smoke/tests/pipelines/synthetic/golden/$golden/happy.tsv" "${args[@]}" \
    --scenario "/tmp/smoke/tests/scenarios/$scenario" --timeout "${E2E_TIMEOUT:-600}" && echo "RESULT minikube-$engine pass" ||
    { echo "RESULT minikube-$engine fail"; rc=1; }
done
exit $rc
