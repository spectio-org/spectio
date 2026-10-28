#!/usr/bin/env bash
# SLURM scenarios on the sind profiles of dev/slurm/cluster.sh (docs/specs/dev-environment-and-testing.md §4.1).
# Each prints a RESULT line, writes its fixtures to $FIXTURES (default .scenarios/slurm/fixtures; committed
# copies in tests/fixtures/slurm/slurm-<version>/, with the runner's checkout path replaced by $REPO) and
# exits 1 on an unexpected outcome. $CLUSTER names the profile that is up (default site). Built from spike t3-ci (docs/research/spike-t3-ci-2026-10-28.md).
#
#   bash tests/slurm/scenarios.sh nextflow[:IDS]   the synthetic pipeline, -profile test,slurm, through
#   bash tests/slurm/scenarios.sh snakemake[:IDS]  run_scenarios.py on the submitter; IDS is a comma list of
#                                                  scenarios.yaml ids (default happy). The squeue and sacct
#                                                  records of each scenario's first failed task job are kept.
#   bash tests/slurm/scenarios.sh probes           slurm-site: OUT_OF_MEMORY, TIMEOUT, NODE_FAIL (power cut) and
#                                                  the pending reasons of schedulers-and-monitoring.md §3.5
#   bash tests/slurm/scenarios.sh heads            slurm-site: a Snakemake head submitted with sbatch runs happy
#   bash tests/slurm/scenarios.sh rest             slurm-rest: slurmrestd answers with a JWT; jobs, nodes, partitions
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
DATA=${SLURM_DATA:-$repo/.scenarios/slurm}
FIXTURES=${FIXTURES:-$DATA/fixtures}
CLUSTER=${CLUSTER:-site}
RUN_URL=${GITHUB_RUN_ID:+$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID}
# The Snakemake SLURM plugin waits 40 s before its first status check and after each check that sees a job
# finish (plugin v2.8.0 __init__.py:244-251, 1611-1617); 5 s keeps the staged pipeline from sleeping.
NF_ARGS=(-profile "test,slurm")
SMK_ARGS=(--workflow-profile "$DATA/synthetic/snakemake/profiles/slurm" --slurm-init-seconds-before-status-checks 5)
mkdir -p "$FIXTURES" "$DATA/work"
cp "$repo/tests/slurm/rest_get.py" "$DATA/"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die() { echo "::error::$*"; exit 1; }
# inc CMD...: run as user spx on the submitter, with the tools on PATH. inroot CMD...: as root.
# shellcheck disable=SC2016  # expanded by the inner bash
inc() { sind exec "$CLUSTER" -u spx -- bash -c '. "$0/env.sh" && cd "$0" && "$@"' "$DATA" "$@"; }
inroot() { sind exec "$CLUSTER" -- "$@"; }
SLURM_VERSION=$(inroot sinfo -V | awk '{print $2}')
# fixture NAME JOBS CMD...: the JSON that CMD prints (as root), kept to JOBS if given, to $FIXTURES/NAME.json.
fixture() {
  local name=$1 jobs=$2
  shift 2
  inroot "$@" | python3 "$repo/tests/slurm/fixture.py" "$FIXTURES/$name.json" --jobs "$jobs" \
    --meta "slurm=$SLURM_VERSION" "source=${RUN_URL:-local}" "command=$*"
}
# state JOBID: the job's sacct state (first word: "CANCELLED by 1001" is CANCELLED).
state() { inroot sacct -X -n -P -j "$1" -o State 2>/dev/null | head -n 1 | cut -d' ' -f1; }
# wait_state JOBID STATE...: poll until the job is in one of the states, at most 240 s.
wait_state() {
  local id=$1 st
  shift
  for _ in $(seq 80); do
    st=$(state "$id")
    for want in "$@"; do [ "$st" = "$want" ] && return 0; done
    sleep 3
  done
  die "job $id: still ${st:-unknown} after 240 s (wanted $*)"
}

# engine ENGINE IDS: run_scenarios.py, one id at a time, then the records of the id's first failed task job.
scenario_engine() {
  local engine=$1 ids=${2:-happy} id since rc jobs failed first results=()
  local extra=("${NF_ARGS[@]}")
  [ "$engine" = nextflow ] || extra=("${SMK_ARGS[@]}")
  for id in ${ids//,/ }; do
    since=$(inroot date -u +%Y-%m-%dT%H:%M:%S)
    rc=0
    inc python3 "$DATA/synthetic/run_scenarios.py" --engine "$engine" --only "$id" \
      --workdir "$DATA/work/$engine-$id" -- "${extra[@]}" || rc=$?
    for f in "$DATA/work/$engine-$id/$engine"/*/run*.log; do
      [ -f "$f" ] && { echo "::group::tail $f"; tail -n 30 "$f"; echo "::endgroup::"; }
    done
    # Known gap (spike finding 1): the SLURM executor logs no task exit code and the task's Slurm job ends
    # 1:0, so run_scenarios.py cannot see 137 for Snakemake. Accept exactly that error, nothing else.
    if [ "$rc" != 0 ] && [ "$engine" = snakemake ] && python3 - "$DATA/work/$engine-$id/$engine/report.json" <<'EOF'
import json, sys
errs = [e for r in json.load(open(sys.argv[1])) for e in r["errors"]]
sys.exit(0 if errs and all(e.startswith("QC_STATS: exit code 137 not seen") for e in errs) else 1)
EOF
    then
      echo "KNOWN GAP: the only failed check is the Snakemake exit code 137, which the SLURM executor does not log"
      rc=0
    fi
    [ "$rc" = 0 ] || die "$engine $id: run_scenarios.py failed (report: $DATA/work/$engine-$id/$engine/report.json)"
    # Filter states here, not with sacct -s (spike finding 6).
    jobs=$(inroot sacct -X -n -P -a -S "$since" -o JobIDRaw,State,ExitCode)
    [ -n "$jobs" ] || die "$engine $id: no Slurm job since $since"
    failed=$(echo "$jobs" | grep -v '|COMPLETED|' || true)
    [ "$id" = happy ] || [ -n "$failed" ] || die "$engine $id: every task job ended COMPLETED"
    if [ -n "$failed" ]; then
      # the first job that failed by itself, not one the engine cancelled while cleaning up
      first=$(echo "$failed" | grep -m1 -E '\|(FAILED|OUT_OF_MEMORY|TIMEOUT|NODE_FAIL)\|' || echo "$failed" | head -n 1)
      first=${first%%|*}
      fixture "$engine-$id-squeue" "$first" squeue --json --states=all
      fixture "$engine-$id-sacct" "$first" sacct --json -j "$first"
    fi
    results+=("$id=pass;not-completed:[$([ -z "$failed" ] || echo "$failed" | cut -d'|' -f2,3 | sort | uniq -c | awk '{printf "%s×%s ", $1, $2}')]")
  done
  echo "RESULT $engine: ${results[*]}"
}

# reason JSON JOBID: the job's state_reason and state_description in a squeue --json document
reason() {
  python3 -c 'import json, sys
j = [j for j in json.load(open(sys.argv[1]))["jobs"] if str(j["job_id"]) == sys.argv[2]][0]
st = j["job_state"]
print(",".join(st) if isinstance(st, list) else st, j["state_reason"], "|", j.get("state_description", ""))' "$@"
}

scenario_probes() {
  local oom tmo cap1 cap2 res1 res2 res3 ptl dep never held adm maint nf t nf_after f=$FIXTURES/squeue-pending-reasons.json
  inc mkdir -p "$DATA/work/probes"
  # Real OOM under ConstrainRAMSpace=yes: 400 MiB touched with a 100 MiB limit.
  oom=$(inc sbatch --parsable -p htc --mem=100M -J probe-oom -o /dev/null \
    --wrap "python3 -c 'b = b\"x\" * (400 << 20); import time; time.sleep(5)'")
  tmo=$(inc sbatch --parsable -p htc -t 1 -J probe-timeout -o /dev/null --wrap 'sleep 600')
  # Association limit: account capped has MaxJobs=1.
  cap1=$(inc sbatch --parsable -p htc -A capped -J probe-cap1 -o /dev/null --wrap 'sleep 90')
  cap2=$(inc sbatch --parsable -p htc -A capped -J probe-cap2 -o /dev/null --wrap 'sleep 5')
  # Two-CPU jobs on htc, whose CPUs the jobs above partly hold: some must wait (Resources, then Priority).
  res1=$(inc sbatch --parsable -p htc -c 2 -J probe-res1 -o /dev/null --wrap 'sleep 30')
  res2=$(inc sbatch --parsable -p htc -c 2 -J probe-res2 -o /dev/null --wrap 'sleep 5')
  res3=$(inc sbatch --parsable -p htc -c 2 -J probe-res3 -o /dev/null --wrap 'sleep 5')
  ptl=$(inc sbatch --parsable -p htc -t 120 -J probe-partlimit -o /dev/null --wrap 'true')   # MaxTime=60
  dep=$(inc sbatch --parsable -p htc -d "afterok:$cap1" -J probe-dep -o /dev/null --wrap 'true')
  never=$(inc sbatch --parsable -p htc -d "afterok:$oom" -J probe-depnever -o /dev/null --wrap 'true')
  held=$(inc sbatch --parsable -p htc -H -J probe-held -o /dev/null --wrap 'true')
  # Maintenance reservation on the only bigmem node.
  inroot scontrol create reservation ReservationName=maint StartTime=now Duration=30 \
    Nodes=worker-2 Users=root Flags=MAINT,IGNORE_JOBS
  maint=$(inc sbatch --parsable -p bigmem -J probe-maint -o /dev/null --wrap 'hostname')
  # An administrator's hold on a job that waits for the reservation.
  adm=$(inc sbatch --parsable -p bigmem -J probe-adminhold -o /dev/null --wrap 'true')
  inroot scontrol hold "$adm"
  sleep 25   # the OOM job fails and the scheduler sets the pending reasons
  inroot squeue -a -o '%.8i %.16j %.9P %.8T %.45r'
  fixture squeue-pending-reasons "$cap1,$cap2,$res1,$res2,$res3,$ptl,$dep,$never,$held,$adm,$maint" squeue --json
  local seen=() want
  for j in "$cap2:AssocMaxJobsLimit" "$ptl:PartitionTimeLimit" "$dep:Dependency" "$never:DependencyNeverSatisfied" \
    "$held:JobHeldUser" "$adm:JobHeldAdmin" "$maint:ReqNodeNotAvail"; do
    want=${j#*:}
    reason "$f" "${j%%:*}" | grep -q "^PENDING $want " || die "probes: job ${j%%:*} is not pending with $want: $(reason "$f" "${j%%:*}")"
    seen+=("$want")
  done
  reason "$f" "$maint" | grep -q "Reserved for maintenance" || die "probes: no 'Reserved for maintenance' on $maint"
  local res=""
  for j in $res1 $res2 $res3; do res+="$(reason "$f" "$j" | awk '{print $1 "/" $2}') "; done
  [[ $res == *PENDING/Resources* ]] || die "probes: no two-CPU job pending with Resources: $res"
  [[ $res == *PENDING/Priority* ]] || die "probes: no two-CPU job pending with Priority: $res"
  seen+=("res:[${res% }]")
  # Cancelled by root: the record that schedulers §3.5 maps to cancelled_external.
  inroot scancel "$ptl" "$dep" "$never" "$held" "$adm"
  inroot scontrol delete ReservationName=maint
  wait_state "$oom" OUT_OF_MEMORY
  wait_state "$maint" COMPLETED
  # NODE_FAIL: a job that is not requeued runs on worker-2, then worker-2 loses power.
  nf=$(inc sbatch --parsable -p bigmem --no-requeue -J probe-nodefail -o /dev/null --wrap 'sleep 600')
  wait_state "$nf" RUNNING
  sind power cut "worker-2.$CLUSTER"
  t=$SECONDS
  wait_state "$nf" NODE_FAIL
  nf_after=$((SECONDS - t))
  log "NODE_FAIL seen $nf_after s after the power cut"
  fixture sinfo-node-down "" sinfo --json
  sind power on "worker-2.$CLUSTER"
  wait_state "$tmo" TIMEOUT
  wait_state "$cap2" COMPLETED
  local cancelled
  cancelled=$(inroot sacct -X -n -P -j "$held" -o State | head -n 1)
  [ "$cancelled" = "CANCELLED by 0" ] || die "probes: job $held is '$cancelled', not 'CANCELLED by 0'"
  local ids="$oom,$tmo,$cap1,$cap2,$maint,$nf,$ptl,$dep,$never,$held,$adm"
  fixture sacct-probes "$ids" sacct --json -j "$ids"
  inroot sacct -X -j "$ids" -o JobID,JobName%16,State,ExitCode,Reason%30
  for _ in $(seq 40); do [ "$(inroot sinfo -h -n worker-2 -o %T)" = idle ] && break; sleep 3; done
  [ "$(inroot sinfo -h -n worker-2 -o %T)" = idle ] || die "probes: worker-2 not idle 120 s after power on"
  fixture sinfo "" sinfo --json
  echo "RESULT probes: pending=${seen[*]} oom=$(state "$oom") timeout=$(state "$tmo") node_fail=$(state "$nf") after $nf_after s; root scancel=$cancelled"
}

scenario_heads() {
  local out=$DATA/work/heads rc=0 log
  inc mkdir -p "$out"
  inc sbatch --wait -p bigmem -c 1 --mem=2000M -t 30 -J spectio-head-snakemake -o "$out/snakemake.%j.out" \
    --wrap ". $DATA/env.sh && python3 $DATA/synthetic/run_scenarios.py --engine snakemake --only happy --workdir $out/snakemake -- ${SMK_ARGS[*]}" || rc=$?
  tail -n 30 "$out"/snakemake.*.out
  log=$(grep -h -m1 "SLURM job context" "$out"/snakemake/snakemake/happy/run*.log || true)
  inroot sacct -X -a -n -P --name spectio-head-snakemake -o JobID,State,ExitCode
  [ "$rc" = 0 ] || die "heads: the Snakemake head job failed (sbatch --wait exit $rc)"
  echo "RESULT heads: snakemake head in sbatch: happy pass, head $(inroot sacct -X -a -n -P --name spectio-head-snakemake -o State,ExitCode | tail -n 1); plugin says: ${log:-nothing}"
}

scenario_rest() {
  local out=$DATA/work/rest a b v n imp rootjob rootst
  local -A path=([jobs]=/slurm/v0.0.45/jobs [nodes]=/slurm/v0.0.45/nodes [partitions]=/slurm/v0.0.45/partitions
    [slurmdb-jobs]=/slurmdb/v0.0.45/jobs)
  inc mkdir -p "$out"
  a=$(inc sbatch --parsable -J rest-ok -o /dev/null --wrap 'true')
  b=$(inc sbatch --parsable -J rest-exit3 -o /dev/null --wrap 'exit 3')
  wait_state "$a" COMPLETED
  wait_state "$b" FAILED
  # The token lives only in the environment of this one command, inside the submitter.
  # shellcheck disable=SC2016  # expanded by the inner bash
  inc bash -c 'export "$(scontrol token lifespan=300)" && python3 "$1/rest_get.py" http://api:6820 "$2" \
    ping-v0.0.43=/slurm/v0.0.43/ping ping-v0.0.44=/slurm/v0.0.44/ping ping-v0.0.45=/slurm/v0.0.45/ping \
    "${@:3}"' sh "$DATA" "$out" "jobs=${path[jobs]}" "nodes=${path[nodes]}" "partitions=${path[partitions]}" \
    "slurmdb-jobs=${path[slurmdb-jobs]}" | tee "$out/codes.txt"
  awk '$2 != 200 {b = 1} END {exit b}' "$out/codes.txt" || die "rest: a GET did not answer 200"
  # spx's token with X-SLURM-USER-NAME root must not act as root: it tries to cancel a held job of root's.
  # (Run 40679302148: a GET of ping with that header answers 200, so the check is on the effect.)
  rootjob=$(inroot sbatch --parsable -H -J rest-root -o /dev/null --wrap true)
  # shellcheck disable=SC2016  # expanded by the inner bash
  imp=$(inc bash -c 'export "$(scontrol token lifespan=300)" && REST_USER=root python3 "$1/rest_get.py" http://api:6820 "$2" \
    "impersonate-root=DELETE /slurm/v0.0.45/job/$3"' sh "$DATA" "$out" "$rootjob" | awk '{print $2}')
  rootst=$(inroot squeue -h -j "$rootjob" -o %T)
  inroot scancel "$rootjob"
  [ "$rootst" = PENDING ] || die "rest: spx's token as root cancelled root's job $rootjob (HTTP $imp, now ${rootst:-gone})"
  # A call without a token must be refused.
  v=$(inc python3 -c 'import urllib.request as u, urllib.error as e
try: print(u.urlopen("http://api:6820/slurm/v0.0.45/ping", timeout=10).status)
except e.HTTPError as x: print(x.code)')
  [ "$v" = 401 ] || die "rest: a call without a token answered $v, not 401"
  for n in jobs nodes partitions slurmdb-jobs; do
    python3 "$repo/tests/slurm/fixture.py" "$FIXTURES/rest-$n.json" --jobs "$a,$b" \
      --meta "slurm=$SLURM_VERSION" "source=${RUN_URL:-local}" "request=GET ${path[$n]}" <"$out/$n.json"
  done
  echo "RESULT rest: $(tr '\n' ' ' <"$out/codes.txt")no-token=$v spx-token-as-root:DELETE-root-job=$imp,root-job=$rootst"
}

case "${1:-}" in
  nextflow* | snakemake*) s=$1; [[ $s == *:* ]] || s=$s:; scenario_engine "${s%%:*}" "${s#*:}" ;;
  probes | heads | rest) "scenario_$1" ;;
  *) sed -n '2,15p' "$0"; exit 2 ;;
esac
