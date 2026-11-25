#!/usr/bin/env bash
# The synthetic pipeline `happy` through the API of the Spectio in minikube, for each engine (default both):
#
#   bash dev/minikube/smoke.sh [nextflow|snakemake]...
#
# 1. kubectl port-forward, then GET / and GET /api/v1/me from the host: both must answer 401 (the server runs and
#    wants a session; any other status, or no answer, fails the script).
# 2. tests/slurm/e2e_client.py, as tests/local/e2e.sh uses it, runs inside the pod: it signs in with a link it asks
#    `spectio login --print-link --json` for (never printed), launches the run with POST /api/v1/runs on the
#    `local` environment, polls it to its end and checks its tasks against the golden file. It prints
#    `ok` or `FAIL` per check.
# 3. tini is PID 1 of the container and no zombie process is left after the runs.
# The fixtures are copied into the pod's /tmp (an emptyDir), not into the image.
# Environment: MINIKUBE_PROFILE (spectio), PF_PORT (18080, a local port from 1024 to 65535), E2E_TIMEOUT (600 s).
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
# shellcheck source=dev/versions.env
. "$repo/dev/versions.env"
ctx=${MINIKUBE_PROFILE:-spectio}
pf_port=${PF_PORT:-18080}
case $pf_port in
  '' | *[!0-9]*) echo "smoke.sh: PF_PORT must be a number" >&2; exit 2 ;;
esac
[ "$pf_port" -ge 1024 ] && [ "$pf_port" -le 65535 ] || { echo "smoke.sh: PF_PORT must be from 1024 to 65535" >&2; exit 2; }
engines=("$@")
[ ${#engines[@]} -gt 0 ] || engines=(nextflow snakemake)
for engine in "${engines[@]}"; do
  case $engine in
    nextflow | snakemake) ;;
    *) echo "smoke.sh: unknown engine '$engine' (nextflow or snakemake)" >&2; exit 2 ;;
  esac
done
k() { kubectl --context "$ctx" -n spectio "$@"; }
fail=0

kubectl --context "$ctx" -n spectio port-forward svc/spectio "$pf_port:8080" >/dev/null 2>&1 &
pf=$!
trap 'kill $pf 2>/dev/null || true' EXIT
for _ in $(seq 20); do curl -s -o /dev/null "http://127.0.0.1:$pf_port/" && break; sleep 1; done
for path in / /api/v1/me; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$pf_port$path" || true)
  if [ "$code" = 401 ]; then echo "ok   GET $path -> 401 (no session)"
  else echo "FAIL GET $path -> HTTP $code, expected 401"; fail=1; fi
done

COPYFILE_DISABLE=1 tar --no-xattrs -C "$repo" -cf - tests/slurm/e2e_client.py tests/pipelines/synthetic tests/scenarios |
  k exec -i deploy/spectio -c spectio -- sh -c 'rm -rf /tmp/smoke && mkdir -p /tmp/smoke && tar -C /tmp/smoke -xf -'
for engine in "${engines[@]}"; do
  case $engine in
    nextflow) golden=nextflow-$NEXTFLOW_VERSION; scenario=happy-local.yaml; args=(--profile test --profile local) ;;
    snakemake) golden=snakemake-$SNAKEMAKE_VERSION; scenario=happy-local-snakemake.yaml
      args=(--profile local --params '{"chunks": 2}') ;;
  esac
  echo "===== $engine"
  k exec deploy/spectio -c spectio -- python3 /tmp/smoke/tests/slurm/e2e_client.py launch "$engine" \
    --config /var/lib/spectio/data/spectio.toml --location "/tmp/smoke/tests/pipelines/synthetic/$engine" \
    --golden "/tmp/smoke/tests/pipelines/synthetic/golden/$golden/happy.tsv" "${args[@]}" \
    --scenario "/tmp/smoke/tests/scenarios/$scenario" --timeout "${E2E_TIMEOUT:-600}" && echo "RESULT minikube-$engine pass" ||
    { echo "RESULT minikube-$engine fail"; fail=1; }
done

# tini reaps what the engine heads leave behind: PID 1 is tini, and nothing is a zombie
pid1=$(k exec deploy/spectio -c spectio -- cat /proc/1/comm)
zombies=$(k exec deploy/spectio -c spectio -- sh -c 'ps -eo stat | grep -c "^Z" || true')
if [ "$pid1" = tini ] && [ "$zombies" = 0 ]; then echo "ok   PID 1 is tini, 0 zombies"
else echo "FAIL PID 1 is '$pid1', $zombies zombies"; fail=1; fi
exit "$fail"
