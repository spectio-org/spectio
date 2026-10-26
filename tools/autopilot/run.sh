#!/usr/bin/env bash
# Run the Spectio autopilot unattended, one headless tick at a time, under a budget.
#
#   tools/autopilot/run.sh --weekly 30                 # use at most 30 points of the weekly window
#   tools/autopilot/run.sh --until-exhausted           # eat the rest of the 5-hour window, stop when it resets
#   tools/autopilot/run.sh --until-exhausted --window seven_day --deadline 18:00
#   tools/autopilot/run.sh --weekly 20 --now 42        # no status-line reading yet: say where you are (/usage)
#   tools/autopilot/run.sh --until W3 --tick-usd 15    # no plan budget, a per-tick USD cap only
#
# The loop, not the model, enforces the budget (docs/playbooks/autopilot.md §6):
#   before each tick  budget.py check --kinds <kinds of the ready batch>  -> go (N steps fit) | wait | stop
#   each tick         claude -p "/autopilot --max-parallel N" piped through budget.py ingest-stream
#   stop when         budget used, deadline, plan limit hit, nothing ready, or two ticks without progress
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

UNTIL=""; TICK_USD="${AUTOPILOT_TICK_USD:-25}"; MAX_TICKS="${AUTOPILOT_MAX_TICKS:-40}"
BUDGET_ARGS=(); HAVE_BUDGET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --until) UNTIL="--until $2"; shift 2;;
    --tick-usd) TICK_USD="$2"; shift 2;;
    --max-ticks) MAX_TICKS="$2"; shift 2;;
    --weekly|--five-hour|--window|--deadline|--now|--pct-per-usd|--margin) BUDGET_ARGS+=("$1" "$2"); HAVE_BUDGET=1; shift 2;;
    --until-exhausted|--no-stop-at-reset) BUDGET_ARGS+=("$1"); HAVE_BUDGET=1; shift;;
    -h|--help) sed -n 2,15p "$0"; exit 0;;
    *) echo "unknown option $1" >&2; exit 2;;
  esac
done

B="python3 tools/autopilot/budget.py"
mkdir -p .autopilot/runs
if [ "$HAVE_BUDGET" = 1 ]; then $B start "${BUDGET_ARGS[@]}"; else $B off >/dev/null; fi

done_count() { { python3 tools/autopilot/ready.py --json || true; } | jq -r ".status_line" | sed -E "s/.*done=([0-9]+).*/\\1/"; }
stalled=0
for tick in $(seq 1 "$MAX_TICKS"); do
  batch_json=$(python3 tools/autopilot/ready.py $UNTIL --json || true)
  kinds=$(jq -r '[.batch[].kind] | join(",")' <<<"$batch_json")
  if [ -z "$kinds" ]; then
    echo "nothing ready: $(jq -r '.status_line' <<<"$batch_json")"; break
  fi

  set +e; decision=$($B check --kinds "$kinds"); rc=$?; set -e
  echo "tick $tick  batch=[$kinds]  $decision"
  if [ $rc -eq 4 ]; then
    until_ts=$(jq -r '.wait_until' <<<"$decision")
    secs=$(( ${until_ts%.*} - $(date +%s) ))
    echo "waiting $((secs / 60)) min for the five-hour window to reset ($(jq -r '.wait_until_local' <<<"$decision"))"
    sleep "$(( secs > 0 ? secs : 60 ))"
    continue
  elif [ $rc -ne 0 ]; then
    echo "stop: $(jq -r '.reason' <<<"$decision")"; break
  fi
  fits=$(jq -r '.fits' <<<"$decision")

  before=$(done_count)
  LOG=".autopilot/runs/$(date -u +%Y%m%dT%H%M%SZ)-tick$tick.jsonl"
  # Auto mode: a classifier reviews actions instead of prompting; anything that would still prompt is denied.
  claude -p "/autopilot ${UNTIL} --max-parallel ${fits}" \
    --permission-mode auto --permission-prompts none \
    --max-budget-usd "$TICK_USD" \
    --output-format stream-json --verbose \
    | $B ingest-stream --kind tick \
    | tee "$LOG" \
    | jq -rj 'select(.type=="assistant") | .message.content[]? | select(.type=="text") | .text + "\n"' || true
  jq -r --arg t "$tick" 'select(.type=="result") | "tick \($t): \(.subtype)  cost $\(.total_cost_usd)  turns \(.num_turns)"' "$LOG" | tail -1 || true

  after=$(done_count)
  if [ "$after" = "$before" ]; then stalled=$((stalled + 1)); else stalled=0; fi
  if [ $stalled -ge 2 ]; then echo "stop: two ticks without a finished step"; break; fi
done

python3 tools/autopilot/ready.py || true
