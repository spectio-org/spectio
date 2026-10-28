#!/usr/bin/env bash
# Spike t4-ci scenarios, run after `cluster.sh up`. Each prints its fixtures as fenced JSON blocks
# (fixture.py) into the job log, and a one-line RESULT that the research note quotes.
#
#   bash spikes/t4-ci/scenarios.sh failures            plain OOMKilled / DeadlineExceeded / exit-3 objects
#   bash spikes/t4-ci/scenarios.sh nf-happy            synthetic Nextflow, -profile test,k8s, all tasks succeed
#   bash spikes/t4-ci/scenarios.sh nf25-happy          same on Nextflow 25.10.9 (bare Pods instead of Jobs)
#   bash spikes/t4-ci/scenarios.sh nf-oom              same, oom_real on QC_STATS S05 (memory limit kills it)
#   bash spikes/t4-ci/scenarios.sh kueue-wait          3 Jobs on a 1-CPU ClusterQueue: Workloads waiting for quota
#   bash spikes/t4-ci/scenarios.sh nf-kueue            synthetic Nextflow (2 samples) through lq-main
#   bash spikes/t4-ci/scenarios.sh rbac                the §4 ServiceAccounts: can-i matrix, runner exercise,
#                                                      Nextflow 26.10 and 25.10 heads run under their own SA
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
# shellcheck source=dev/versions.env
. "$repo/dev/versions.env"
NS=spectio-work
CLUSTER=${CLUSTER:-spx-t4}
export SPIKE_MOUNT=${SPIKE_MOUNT:-$(dirname "${RUNNER_TEMP:-/tmp/x}")}
WORK=${RUNNER_TEMP:-/tmp}/t4
PIPE=$repo/tests/pipelines/synthetic/nextflow
mkdir -p "$WORK"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
k() { kubectl -n "$NS" "$@"; }
fixture() { python3 "$here/fixture.py" "$@"; }
# events whose involvedObject name is in the JSON list on stdin's companion file $1
events_for() { # NAMES_JSON_FILE -> events JSON on stdout
  k get events -o json | jq --slurpfile names "$1" '{kind: "List", items: [.items[] | select(.involvedObject.name as $n | $names[0] | index($n))]}'
}

# nf_run LABEL NFBIN [nextflow args...]: run the synthetic pipeline on k8s from $WORK/LABEL.
# Env passed through: KUBECONFIG, SPIKE_CLEANUP, SPIKE_QUEUE. Sets NF_RC and NF_SECONDS.
nf_run() {
  local label=$1 nf=$2
  shift 2
  rm -rf "${WORK:?}/$label"; mkdir -p "$WORK/$label"
  local t=$SECONDS
  ( cd "$WORK/$label" && SPECTIO_RUN_ID=$label "$nf" -trace nextflow.k8s.client -c "$here/nextflow/kind.config" \
      run "$PIPE" -profile test,k8s --outdir results "$@" >run.log 2>&1 )
  NF_RC=$?
  NF_SECONDS=$((SECONDS - t))
  log "nextflow $label: exit $NF_RC in ${NF_SECONDS}s"
  echo "::group::$label run.log (tail)"; tail -n 40 "$WORK/$label/run.log"; echo "::endgroup::"
  if [ "$NF_RC" != 0 ]; then
    echo "::group::$label .nextflow.log (errors)"
    grep -n -E "ERROR|WARN|Exception|error code=" "$WORK/$label/.nextflow.log" | grep -v "API response" | head -n 60
    echo "::endgroup::"
  fi
}

trace_json() { # LABEL -> the Nextflow trace as JSON rows
  python3 -c '
import csv, json, sys
rows = list(csv.DictReader(open(sys.argv[1]), delimiter="\t"))
print(json.dumps({"kind": "NextflowTrace", "items": rows}))' "$WORK/$1/results/pipeline_info/execution_trace.txt" 2>/dev/null ||
    echo '{"kind": "NextflowTrace", "items": [], "_spike": {"error": "no trace file"}}'
}

pod_table() { # LABEL: one line per pod of the run
  k get pods -l "spectio.io/run-id=$1" -o json | jq -r '
    .items[] | [.metadata.labels["nextflow.io/taskName"] // .metadata.name, .metadata.name, .spec.nodeName // "-", .status.phase,
      (.status.containerStatuses[0].state.terminated | if . then "\(.reason) exit=\(.exitCode)" else "-" end)] | @tsv' | sort | column -t -s $'\t'
}

scenario_failures() {
  k apply -f "$here/manifests/failures.yaml"
  k wait --for=condition=Failed job/fx-oom job/fx-job-deadline job/fx-exit3 --timeout=120s
  k wait --for=jsonpath='{.status.phase}'=Failed pod/fx-pod-deadline --timeout=60s
  sleep 2
  k get jobs -l spectio.io/run-id=fx-failures -o json | fixture k8s-failures-jobs --meta kubernetes="$KIND_NODE_IMAGE"
  k get pods -l spectio.io/run-id=fx-failures -o json | fixture k8s-failures-pods --meta kubernetes="$KIND_NODE_IMAGE"
  k get pods -l spectio.io/run-id=fx-failures -o json | jq '[.items[].metadata.name] + ["fx-oom","fx-job-deadline","fx-pod-deadline","fx-exit3"]' >"$WORK/fx-names.json"
  events_for "$WORK/fx-names.json" | fixture k8s-failures-events
  echo "RESULT failures: $(k get pods -l spectio.io/run-id=fx-failures -o json | jq -c '[.items[] | {pod: .metadata.name, phase: .status.phase, reason: .status.reason, terminated: (.status.containerStatuses[0].state.terminated | {reason, exitCode})}]')"
  echo "RESULT failures-jobs: $(k get jobs -l spectio.io/run-id=fx-failures -o json | jq -c '[.items[] | {job: .metadata.name, failed: [.status.conditions[]? | select(.type=="Failed") | {reason, message}]}]')"
}

nf_fixtures() { # LABEL PROCESS SAMPLE: the run's objects, and one task's objects in full
  local label=$1 proc=$2 sample=$3
  trace_json "$label" | fixture "$label-trace"
  echo "::group::$label pods"; pod_table "$label"; echo "::endgroup::"
  # Nextflow 26.10 creates Jobs (K8sConfig.groovy L224 at v26.10.4), 25.10 Pods (L218 at v25.10.9)
  k get jobs -l "spectio.io/run-id=$label" -o json | jq -c '{n: (.items | length)}' | sed "s/^/RESULT $label-jobs: /"
  k get pods -l "spectio.io/run-id=$label" -o json |
    jq --arg p "$proc" --arg s "$sample" '{kind: "List", items: [.items[] | select(.metadata.labels["nextflow.io/processName"] == $p and ((.metadata.labels["nextflow.io/taskName"] // "") | contains($s)))]}' \
    >"$WORK/$label-task-pods.json"
  fixture "$label-task-pods" <"$WORK/$label-task-pods.json"
  jq '[.items[] | .metadata.name, (.metadata.labels["job-name"] // empty)] | unique' "$WORK/$label-task-pods.json" >"$WORK/$label-task-names.json"
  k get jobs -o json | jq --slurpfile names "$WORK/$label-task-names.json" '{kind: "List", items: [.items[] | select(.metadata.name as $n | $names[0] | index($n))]}' |
    fixture "$label-task-jobs"
  events_for "$WORK/$label-task-names.json" | fixture "$label-task-events"
  # every event of the run, reasons only, to size what a runner must keep
  k get pods -l "spectio.io/run-id=$label" -o json | jq '[.items[] | .metadata.name, (.metadata.labels["job-name"] // empty)] | unique' >"$WORK/$label-names.json"
  echo "RESULT $label-event-reasons: $(events_for "$WORK/$label-names.json" | jq -c '[.items[] | "\(.involvedObject.kind)/\(.reason)"] | group_by(.) | map({(.[0]): length}) | add')"
}

scenario_nf_happy() {
  SPIKE_CLEANUP=false nf_run nf26-happy nextflow
  echo "RESULT nf26-happy: exit=$NF_RC seconds=$NF_SECONDS tasks=$(trace_json nf26-happy | jq -c '[.items[] | .status] | group_by(.) | map({(.[0]): length}) | add')"
  nf_fixtures nf26-happy QC_STATS S01
}

scenario_nf25_happy() { # Nextflow 25.10.9 creates bare Pods; it needs the plugin named (see rbac)
  SPIKE_CLEANUP=false nf_run nf25-happy "nextflow-$NEXTFLOW_25_10_VERSION" -plugins nf-k8s@1.2.3
  echo "RESULT nf25-happy: exit=$NF_RC seconds=$NF_SECONDS tasks=$(trace_json nf25-happy | jq -c '[.items[] | .status] | group_by(.) | map({(.[0]): length}) | add')"
  nf_fixtures nf25-happy QC_STATS S01
}

scenario_nf_oom() {
  SPIKE_CLEANUP=false nf_run nf26-oom nextflow --fail_mode oom_real --fail_process QC_STATS --fail_sample S05
  echo "RESULT nf26-oom: exit=$NF_RC seconds=$NF_SECONDS S05=$(trace_json nf26-oom | jq -c '[.items[] | select(.process=="QC_STATS" and .tag=="S05") | {attempt, status, exit, peak_rss}]')"
  nf_fixtures nf26-oom QC_STATS S05
  echo "RESULT nf26-oom-pods: $(jq -c '[.items[] | {pod: .metadata.name, mem: .spec.containers[0].resources.limits.memory, terminated: (.status.containerStatuses[0].state.terminated | {reason, exitCode})}]' "$WORK/nf26-oom-task-pods.json")"
}

visibility() { # lq|cq NAME
  if [ "$1" = lq ]; then
    kubectl get --raw "/apis/visibility.kueue.x-k8s.io/v1beta2/namespaces/$NS/localqueues/$2/pendingworkloads"
  else
    kubectl get --raw "/apis/visibility.kueue.x-k8s.io/v1beta2/clusterqueues/$2/pendingworkloads"
  fi
}

scenario_kueue_wait() {
  k apply -f "$here/manifests/kueue-wait.yaml"
  # wait until the state is settled: one admitted, two with QuotaReserved=False, and the ClusterQueue
  # status counting them (run 1 dumped after 1 s and caught one Workload with no QuotaReserved yet)
  local admitted=0 waiting=0 cq_pending=0
  for _ in $(seq 60); do
    admitted=$(k get workloads -o json | jq '[.items[] | select(.status.conditions[]? | .type=="Admitted" and .status=="True")] | length')
    waiting=$(k get workloads -o json | jq '[.items[] | select(.status.conditions[]? | .type=="QuotaReserved" and .status=="False")] | length')
    cq_pending=$(kubectl get clusterqueue cq-tight -o jsonpath='{.status.pendingWorkloads}')
    [ "$admitted" -ge 1 ] && [ "$waiting" -ge 2 ] && [ "${cq_pending:-0}" -ge 2 ] && break
    sleep 2
  done
  log "kueue-wait: admitted=$admitted waiting=$waiting clusterqueue.pendingWorkloads=$cq_pending"
  k get workloads -o json | fixture kueue-workloads --meta kueue="v$KUEUE_VERSION"
  visibility lq lq-tight | fixture kueue-pending-lq-tight --meta kueue="v$KUEUE_VERSION"
  visibility cq cq-tight | fixture kueue-pending-cq-tight --meta kueue="v$KUEUE_VERSION"
  kubectl get clusterqueue cq-tight -o json | fixture kueue-clusterqueue-cq-tight
  k get localqueue lq-tight -o json | fixture kueue-localqueue-lq-tight
  k get jobs -l spectio.io/run-id=fx-kueue -o json | fixture kueue-jobs
  k get workloads -o json | jq '[.items[].metadata.name] + ["fx-kq-1","fx-kq-2","fx-kq-3"]' >"$WORK/kq-names.json"
  events_for "$WORK/kq-names.json" | fixture kueue-events
  echo "RESULT kueue-wait: $(k get workloads -o json | jq -c '[.items[] | {wl: .metadata.name, conditions: [.status.conditions[]? | {type, status, reason}]}]')"
  echo "RESULT kueue-positions: $(visibility lq lq-tight | jq -c '[.items[] | {name: .metadata.name, positionInLocalQueue, positionInClusterQueue}]')"
  k delete -f "$here/manifests/kueue-wait.yaml" --wait=true
}

scenario_nf_kueue() {
  # sample the queue while Nextflow runs: how many of its Jobs wait in Kueue, and their positions
  # and keep the first moment with 3 or more waiting: the visibility answer and those Workloads
  rm -f "$WORK/nf-kueue-pending.json" "$WORK/nf-kueue-pending-wl.json"
  ( for _ in $(seq 200); do
      vis=$(visibility lq lq-main 2>/dev/null)
      printf '%s %s\n' "$(date -u +%H:%M:%S)" "$(echo "$vis" | jq -c '[.items[] | .positionInLocalQueue]')"
      if [ ! -s "$WORK/nf-kueue-pending.json" ] && [ "$(echo "$vis" | jq '.items | length')" -ge 3 ]; then
        echo "$vis" >"$WORK/nf-kueue-pending.json"
        k get workloads -o json | jq --argjson v "$vis" '([$v.items[].metadata.name]) as $p | {kind: "List", items: [.items[] | select(.metadata.name as $n | $p | index($n))]}' \
          >"$WORK/nf-kueue-pending-wl.json"
      fi
      sleep 2
    done ) >"$WORK/nf-kueue-samples.txt" 2>&1 &
  local sampler=$!
  SPIKE_CLEANUP=false SPIKE_QUEUE=lq-main nf_run nf26-kueue nextflow --input "$here/nextflow/mini-samplesheet.csv"
  kill "$sampler" 2>/dev/null
  echo "::group::nf26-kueue pending positions every 2 s"; cat "$WORK/nf-kueue-samples.txt"; echo "::endgroup::"
  fixture nf26-kueue-pending-visibility --meta kueue="v$KUEUE_VERSION" <"$WORK/nf-kueue-pending.json"
  fixture nf26-kueue-pending-workloads --meta kueue="v$KUEUE_VERSION" <"$WORK/nf-kueue-pending-wl.json"
  echo "RESULT nf26-kueue: exit=$NF_RC seconds=$NF_SECONDS max_pending=$(sed 's/^[^ ]* //' "$WORK/nf-kueue-samples.txt" | jq -s 'map(length) | max')"
  echo "RESULT nf26-kueue-job-labels: $(k get jobs -l spectio.io/run-id=nf26-kueue -o json | jq -c '[.items[0].metadata.labels, .items[0].spec.suspend]')"
  k get workloads -o json | fixture nf26-kueue-workloads --meta kueue="v$KUEUE_VERSION" --max-bytes 40000
  nf_fixtures nf26-kueue ALIGN S07
}

# kubeconfig that authenticates as a ServiceAccount (a bound token), same cluster
sa_kubeconfig() { # SA OUT
  local token
  token=$(k create token "$1" --duration=2h)
  kubectl config view --raw --minify >"$2"
  KUBECONFIG=$2 kubectl config set-credentials "$1" --token="$token" >/dev/null
  KUBECONFIG=$2 kubectl config set-context --current --user="$1" --namespace="$NS" >/dev/null
  KUBECONFIG=$2 kubectl config unset "users.kind-$CLUSTER" >/dev/null
}

can_i() { # SA verb resource[/subresource]
  local got res=${3%%/*} sub=
  [ "$res" = "$3" ] || sub=${3#*/}
  got=$(kubectl auth can-i "$2" "$res" ${sub:+--subresource="$sub"} -n "$NS" --as="system:serviceaccount:$NS:$1" 2>/dev/null)
  printf '%-12s %-8s %-48s %s\n' "$1" "$2" "$3" "${got:-no}"
}

# rbac_head TAG NFBIN SA QUEUE [extra nextflow args]: run the mini pipeline twice (success, then a tool
# error that makes the head kill in-flight tasks) under the SA's own token, with three Role sets:
# spec (rbac-spec.yaml only), additions (spec + rbac-head-additions.yaml), minimal (rbac-head-minimal.yaml
# only). QUEUE, when set, sends the success run through Kueue, so its Jobs wait suspended with no pod.
rbac_head() {
  local tag=$1 nf=$2 sa=$3 queue=$4 kc="$WORK/kc-$3"
  shift 4
  sa_kubeconfig "$sa" "$kc"
  KUBECONFIG=$kc kubectl auth whoami -o jsonpath='{.status.userInfo.username}{"\n"}' 2>/dev/null || true
  for pass in spec additions minimal; do
    case $pass in
      additions) kubectl apply -f "$here/manifests/rbac-head-additions.yaml" >/dev/null ;;
      minimal)
        k delete rolebinding "$sa" "$sa-additions" >/dev/null
        kubectl apply -f "$here/manifests/rbac-head-minimal.yaml" >/dev/null
        ;;
    esac
    echo "::group::can-i --list $sa (pass $pass)"
    kubectl auth can-i --list -n "$NS" --as="system:serviceaccount:$NS:$sa" | grep -v -E "selfsubject|^ +\[/"
    echo "::endgroup::"
    KUBECONFIG=$kc SPIKE_CLEANUP=true SPIKE_QUEUE=$queue nf_run "$tag-$pass-ok" "$nf" \
      --input "$here/nextflow/mini-samplesheet.csv" "$@"
    local ok_rc=$NF_RC ok_s=$NF_SECONDS
    KUBECONFIG=$kc SPIKE_CLEANUP=true nf_run "$tag-$pass-err" "$nf" --input "$here/nextflow/mini-samplesheet.csv" \
      --fail_mode exit --fail_process ALIGN --fail_sample S07 "$@"
    local err_rc=$NF_RC refused
    for run in ok err; do
      python3 "$here/api_calls.py" "$WORK/$tag-$pass-$run/.nextflow.log" >"$WORK/$tag-$pass-$run.api.json"
      fixture "$tag-$pass-$run-api" <"$WORK/$tag-$pass-$run.api.json"
    done
    refused=$(jq -s -c 'map(.refused) | add' "$WORK/$tag-$pass-ok.api.json" "$WORK/$tag-$pass-err.api.json")
    echo "RESULT rbac $tag role=$pass: ok-run exit=$ok_rc (${ok_s}s, queue=${queue:-none}), err-run exit=$err_rc (expect 1); refused=$refused; used=$(jq -s -c '{ok: .[0].used, err: .[1].used}' "$WORK/$tag-$pass-ok.api.json" "$WORK/$tag-$pass-err.api.json")"
    grep -h "Unable to delete" "$WORK/$tag-$pass-ok/.nextflow.log" "$WORK/$tag-$pass-err/.nextflow.log" | head -n 3
    if [ "$ok_rc" = 0 ] && [ "$err_rc" = 1 ] && [ "$refused" = "[]" ]; then
      echo "RESULT rbac $tag role=$pass: SUFFICIENT"
    else
      echo "RESULT rbac $tag role=$pass: NOT sufficient"
    fi
  done
  # the cluster is shared by both heads: restore the spec bindings for the next one
  kubectl delete -f "$here/manifests/rbac-head-additions.yaml" -f "$here/manifests/rbac-head-minimal.yaml" --ignore-not-found >/dev/null
  kubectl apply -f "$here/manifests/rbac-spec.yaml" >/dev/null
}

scenario_rbac() {
  kubectl apply -f "$here/manifests/rbac-spec.yaml"
  echo "::group::can-i matrix (spec Roles)"
  for c in "create jobs" "delete jobs" "watch jobs" "get pods/log" "watch events" "list resourcequotas" "list limitranges" \
           "get persistentvolumeclaims" "create pods" "get secrets" "create pods/exec" "list nodes" \
           "list workloads.kueue.x-k8s.io" "get localqueues.visibility.kueue.x-k8s.io/pendingworkloads"; do
    # shellcheck disable=SC2086
    can_i spectio-runner $c
  done
  for sa in nf-head-26 nf-head-25; do
    for c in "create jobs" "get jobs/status" "create pods" "delete pods" "get pods/status" "watch pods" "get pods/log" \
             "get secrets" "create configmaps" "create pods/exec"; do
      # shellcheck disable=SC2086
      can_i "$sa" $c
    done
  done
  echo "::endgroup::"
  for sa in spectio-runner nf-head-26 nf-head-25; do
    echo "::group::can-i --list $sa"
    kubectl auth can-i --list -n "$NS" --as="system:serviceaccount:$NS:$sa"
    echo "::endgroup::"
  done

  # The runner's own job, done for real with its token: create the head Job under nf-head-26, read
  # its pod and log and the events, read the quota, then delete the Job.
  local kc="$WORK/kc-runner"
  sa_kubeconfig spectio-runner "$kc"
  kubectl create job runner-head-probe -n "$NS" --image="$BUSYBOX_IMAGE" --dry-run=client -o json -- echo head-ok |
    jq '.spec.template.spec.serviceAccountName = "nf-head-26" | .spec.template.metadata.labels["spectio.io/run-id"] = "runner-probe"
        | .spec.template.spec.containers[0].resources = {requests: {cpu: "100m", memory: "16Mi"}}' >"$WORK/runner-head-probe.json"
  local steps=()
  step() { local name=$1; shift; if KUBECONFIG=$kc "$@" >"$WORK/runner-step.log" 2>&1; then steps+=("$name:ok"); else steps+=("$name:REFUSED($(tail -n 1 "$WORK/runner-step.log" | cut -c1-120))"); fi; }
  step create-job kubectl create -f "$WORK/runner-head-probe.json"
  step wait-job kubectl wait --for=condition=complete job/runner-head-probe --timeout=90s
  step list-pods kubectl get pods -l spectio.io/run-id=runner-probe
  step pod-log kubectl logs job/runner-head-probe
  step events kubectl get events
  step quota kubectl get resourcequotas
  step limitranges kubectl get limitranges
  step delete-job kubectl delete job runner-head-probe --wait=true
  # §4: the runner watches Workload objects and, optionally, reads the visibility API
  step workloads kubectl get workloads.kueue.x-k8s.io
  step visibility kubectl get --raw "/apis/visibility.kueue.x-k8s.io/v1beta2/namespaces/$NS/localqueues/lq-main/pendingworkloads"
  echo "RESULT rbac runner: ${steps[*]}"

  rbac_head nf26 nextflow nf-head-26 lq-main
  # Nextflow 25.10.9 does not start the k8s executor plugin by itself ("Unknown executor name: k8s",
  # run 1); nf-k8s@1.2.3 is the version its own log lists among its core plugins.
  rbac_head nf25 "nextflow-$NEXTFLOW_25_10_VERSION" nf-head-25 "" -plugins nf-k8s@1.2.3
}

case "${1:-}" in
  failures) scenario_failures ;;
  nf-happy) scenario_nf_happy ;;
  nf25-happy) scenario_nf25_happy ;;
  nf-oom) scenario_nf_oom ;;
  kueue-wait) scenario_kueue_wait ;;
  nf-kueue) scenario_nf_kueue ;;
  rbac) scenario_rbac ;;
  *) sed -n '2,12p' "$0"; exit 2 ;;
esac
