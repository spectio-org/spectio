#!/usr/bin/env bash
# Kubernetes scenarios on the kind profiles of dev/k8s/cluster.sh (docs/specs/dev-environment-and-testing.md §4.2).
# Each writes its fixtures to $FIXTURES (default .scenarios/k8s/fixtures; committed copies in tests/fixtures/k8s/)
# and fails on an unexpected outcome. Built from spike t4-ci (docs/research/spike-t4-ci-2026-10-28.md).
#
#   bash tests/k8s/scenarios.sh failures     k8s-mini or k8s-kueue: an OOMKilled pod, a Job and a Pod over their
#                                            deadline, a Job whose pod exits 3
#   bash tests/k8s/scenarios.sh nf25         synthetic Nextflow 25.10.9, -profile test,k8s, run as nf-head-25 with
#                                            its own token: happy run (exit 0), tool-error run (exit 1), 0 refused calls
#   bash tests/k8s/scenarios.sh nf26         the same on Nextflow 26.10.4 as nf-head-26; k8s-kueue only, because the
#                                            tool-error run goes through lq-main
#   bash tests/k8s/scenarios.sh kueue-wait   k8s-kueue: 3 one-CPU Jobs on a 1-CPU queue, 2 Workloads wait for quota
#   bash tests/k8s/scenarios.sh runner       k8s-kueue: the runner's work done with the spectio-runner token
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
here=$repo/tests/k8s
# shellcheck source=dev/versions.env
. "$repo/dev/versions.env"
NS=spectio-work
WORK=$repo/.scenarios/k8s
FIXTURES=${FIXTURES:-$WORK/fixtures}
PIPE=$repo/tests/pipelines/synthetic/nextflow
RUN_URL=${GITHUB_RUN_ID:+$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID}
mkdir -p "$WORK" "$FIXTURES"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die() { echo "::error::$*"; exit 1; }
k() { kubectl -n "$NS" "$@"; }

# fixture NAME [KEY=VALUE...]: the JSON on stdin, without managedFields and the last-applied annotation,
# plus a _fixture object (versions, source run), to $FIXTURES/NAME.json.
fixture() {
  local name=$1 meta
  shift
  meta=$(printf '%s\n' "kubernetes=${KIND_NODE_IMAGE%@*}" "source=${RUN_URL:-local}" "$@" |
    jq -R 'split("=") | {(.[0]): (.[1:] | join("="))}' | jq -s add)
  jq --argjson meta "$meta" 'del(.. | objects | .managedFields)
    | del(.. | objects | .annotations | objects | .["kubectl.kubernetes.io/last-applied-configuration"])
    | . + {_fixture: $meta}' >"$FIXTURES/$name.json"
  log "fixture $name: $(wc -c <"$FIXTURES/$name.json") bytes"
}

# list NAMES_JSON_FILE: the namespace's events whose involvedObject is one of the names
events_for() {
  k get events -o json | jq --slurpfile names "$1" '{kind: "List", items: [.items[] | select(.involvedObject.name as $n | $names[0] | index($n))]}'
}

scenario_failures() {
  k apply -f "$here/failures.yaml"
  k wait --for=condition=Failed job/fx-oom job/fx-job-deadline job/fx-exit3 --timeout=120s
  k wait --for=jsonpath='{.status.phase}'=Failed pod/fx-pod-deadline --timeout=60s
  sleep 2
  k get jobs -l spectio.io/run-id=fx-failures -o json | fixture failures-jobs
  k get pods -l spectio.io/run-id=fx-failures -o json | fixture failures-pods
  jq '[.items[].metadata.name] + ["fx-oom", "fx-job-deadline", "fx-pod-deadline", "fx-exit3"]' \
    "$FIXTURES/failures-pods.json" >"$WORK/fx-names.json"
  events_for "$WORK/fx-names.json" | fixture failures-events
  jq -e '[.items[] | select(.metadata.labels["job-name"] == "fx-oom") | .status.containerStatuses[0].state.terminated
          | select(.reason == "OOMKilled" and .exitCode == 137)] | length == 1' "$FIXTURES/failures-pods.json" >/dev/null ||
    die "failures: fx-oom is not OOMKilled with exit 137"
  jq -e '[.items[] | select(.metadata.name == "fx-pod-deadline") | .status.reason] == ["DeadlineExceeded"]' \
    "$FIXTURES/failures-pods.json" >/dev/null || die "failures: fx-pod-deadline has no DeadlineExceeded reason"
  echo "RESULT failures: $(jq -c '[.items[] | {pod: .metadata.name, reason: .status.reason,
    terminated: (.status.containerStatuses[0].state.terminated | {reason, exitCode})}]' "$FIXTURES/failures-pods.json")"
}

# kubeconfig that authenticates as a ServiceAccount, with a bound token and no admin credentials
sa_kubeconfig() { # SA OUT
  local token cluster
  token=$(k create token "$1" --duration=2h)
  cluster=$(kubectl config current-context)
  kubectl config view --raw --minify >"$2"
  KUBECONFIG=$2 kubectl config set-credentials "$1" --token="$token" >/dev/null
  KUBECONFIG=$2 kubectl config set-context --current --user="$1" --namespace="$NS" >/dev/null
  KUBECONFIG=$2 kubectl config unset "users.$cluster" >/dev/null
}

# nf_run LABEL NFBIN [nextflow args...]: the synthetic pipeline on k8s from $WORK/LABEL; sets NF_RC.
# Environment passed to kind.config: KUBECONFIG, K8S_CLEANUP, K8S_QUEUE.
nf_run() {
  local label=$1 nf=$2 t=$SECONDS
  shift 2
  rm -rf "${WORK:?}/$label"
  mkdir -p "$WORK/$label"
  NF_RC=0
  (cd "$WORK/$label" && SPECTIO_RUN_ID=$label K8S_MOUNT=$repo "$nf" -trace nextflow.k8s.client \
    -c "$here/kind.config" run "$PIPE" -profile test,k8s --outdir results "$@" >run.log 2>&1) || NF_RC=$?
  log "nextflow $label: exit $NF_RC in $((SECONDS - t)) s"
  echo "::group::$label run.log (tail)"; tail -n 30 "$WORK/$label/run.log"; echo "::endgroup::"
}

# scenario_nf 26|25: happy run, then a tool-error run that makes the head kill the tasks in flight, both
# under the head's own token. Fails unless the exit codes are 0 and 1 and no API call was refused.
scenario_nf() {
  local v=$1 nf sa=nf-head-$1 queue="" version kc=$WORK/kc-nf-head-$1 extra=()
  if [ "$v" = 26 ]; then
    nf=nextflow version=$NEXTFLOW_VERSION queue=lq-main
  else
    nf=nextflow-$NEXTFLOW_25_10_VERSION version=$NEXTFLOW_25_10_VERSION extra=(-plugins "nf-k8s@$NF_K8S_25_10_VERSION")
  fi
  kubectl apply -f "$here/rbac.yaml" >/dev/null
  sa_kubeconfig "$sa" "$kc"
  KUBECONFIG=$kc K8S_CLEANUP=false nf_run "nf$v-happy" "$nf" "${extra[@]}"
  local happy_rc=$NF_RC
  KUBECONFIG=$kc K8S_QUEUE=$queue nf_run "nf$v-error" "$nf" --input "$here/mini-samplesheet.csv" \
    --fail_mode exit --fail_process ALIGN --fail_sample S07 "${extra[@]}"
  local error_rc=$NF_RC

  # One task's objects: QC_STATS of sample S01. 26.10 creates a Job per task, 25.10 a bare Pod.
  k get pods -l "spectio.io/run-id=nf$v-happy,nextflow.io/processName=QC_STATS" -o json |
    jq '[.items[] | select(.metadata.labels["nextflow.io/taskName"] // "" | test("(^|[^0-9A-Za-z])S01([^0-9]|$)"))][0]' |
    fixture "nf-$version-task-pod" "nextflow=$version"
  local pod job
  pod=$(jq -er .metadata.name "$FIXTURES/nf-$version-task-pod.json") || die "nf$v: no QC_STATS S01 pod"
  job=$(jq -r '.metadata.labels["job-name"] // empty' "$FIXTURES/nf-$version-task-pod.json")
  [ -z "$job" ] || k get job "$job" -o json | fixture "nf-$version-task-job" "nextflow=$version"
  jq -n --arg p "$pod" --arg j "$job" '[$p, $j] - [""]' >"$WORK/nf$v-names.json"
  events_for "$WORK/nf$v-names.json" | fixture "nf-$version-task-events" "nextflow=$version"

  # API calls: none refused; report any granted verb neither run used (the Role would not be minimal).
  local used granted
  used=$(for r in happy error; do python3 "$here/api_calls.py" "$WORK/nf$v-$r/.nextflow.log"; done | jq -s -c '
    {refused: (map(.refused) | add), used: (map(.used | keys) | add | unique)}')
  granted=$(k get role "$sa" -o json | jq -c '[.rules[] | .apiGroups[0] as $g | .resources[] as $r | .verbs[]
    | (if $g == "" then "" else $g + ":" end) + $r + " " + .] | sort')
  echo "RESULT nf$v: happy exit=$happy_rc error exit=$error_rc $used unused-grants=$(jq -n -c --argjson g "$granted" --argjson u "$used" '$g - $u.used')"
  [ "$happy_rc" = 0 ] && [ "$error_rc" = 1 ] || die "nf$v: exit codes $happy_rc/$error_rc, expected 0/1"
  [ "$(jq -c .refused <<<"$used")" = "[]" ] || die "nf$v: the $sa Role refused API calls"
}

visibility() { kubectl get --raw "/apis/visibility.kueue.x-k8s.io/v1beta2/namespaces/$NS/localqueues/$1/pendingworkloads"; }

scenario_kueue_wait() {
  k apply -f "$here/kueue-wait.yaml"
  # Wait for a settled state: the visibility API lists a Workload before its QuotaReserved=False condition
  # is set (spike t4-ci, run 1).
  local admitted=0 waiting=0
  for _ in $(seq 60); do
    k get workloads -o json >"$WORK/workloads.json"
    admitted=$(jq '[.items[] | select(.status.conditions[]? | .type == "Admitted" and .status == "True")] | length' "$WORK/workloads.json")
    waiting=$(jq '[.items[] | select(.status.conditions[]? | .type == "QuotaReserved" and .status == "False")] | length' "$WORK/workloads.json")
    [ "$admitted" -ge 1 ] && [ "$waiting" -ge 2 ] && break
    sleep 2
  done
  [ "$admitted" -ge 1 ] && [ "$waiting" -ge 2 ] || die "kueue-wait: admitted=$admitted waiting=$waiting, expected 1 and 2"
  fixture kueue-workloads "kueue=v$KUEUE_VERSION" <"$WORK/workloads.json"
  visibility lq-tight | fixture kueue-pending-workloads "kueue=v$KUEUE_VERSION"
  echo "RESULT kueue-wait: $(jq -c '[.items[] | {name: .metadata.name, positionInLocalQueue, positionInClusterQueue}]' \
    "$FIXTURES/kueue-pending-workloads.json")"
  k delete -f "$here/kueue-wait.yaml" --wait=true >/dev/null
}

# The runner's own work, with its token: start a head Job under nf-head-26, follow it, read the quota and the
# Kueue Workloads and queue positions, then delete the Job. Anything outside its Role must be refused.
scenario_runner() {
  local kc=$WORK/kc-runner failed=0 step
  kubectl apply -f "$here/rbac.yaml" >/dev/null
  sa_kubeconfig spectio-runner "$kc"
  kubectl create job runner-probe -n "$NS" --image="$BUSYBOX_IMAGE" --dry-run=client -o json -- echo head-ok |
    jq '.spec.template.spec.serviceAccountName = "nf-head-26"
      | .spec.template.spec.containers[0].resources = {requests: {cpu: "100m", memory: "16Mi"}}' >"$WORK/runner-probe.json"
  allowed() {
    if KUBECONFIG=$kc "$@" >"$WORK/runner-step.log" 2>&1; then echo "ok      $*"
    else echo "REFUSED $* ($(tail -n 1 "$WORK/runner-step.log"))"; failed=1; fi
  }
  allowed kubectl create -f "$WORK/runner-probe.json"
  allowed kubectl wait --for=condition=complete job/runner-probe --timeout=90s
  allowed kubectl get pods -l job-name=runner-probe
  allowed kubectl logs job/runner-probe
  allowed kubectl get events
  allowed kubectl get resourcequotas,limitranges
  allowed kubectl get workloads.kueue.x-k8s.io
  allowed kubectl get --raw "/apis/visibility.kueue.x-k8s.io/v1beta2/namespaces/$NS/localqueues/lq-main/pendingworkloads"
  allowed kubectl delete job runner-probe --wait=true
  for step in "create pods" "get secrets" "list nodes"; do
    # shellcheck disable=SC2086  # "verb resource" pairs
    if [ "$(KUBECONFIG=$kc kubectl auth can-i $step 2>/dev/null)" = no ]; then echo "denied  $step"
    else echo "ALLOWED $step"; failed=1; fi
  done
  [ "$failed" = 0 ] || die "runner: the spectio-runner Role is not sufficient or not tight"
  echo "RESULT runner: sufficient and tight"
}

case "${1:-}" in
  failures) scenario_failures ;;
  nf25) scenario_nf 25 ;;
  nf26) scenario_nf 26 ;;
  kueue-wait) scenario_kueue_wait ;;
  runner) scenario_runner ;;
  *) sed -n '2,15p' "$0"; exit 2 ;;
esac
