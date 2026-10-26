#!/usr/bin/env bash
# Run the Spectio autopilot unattended until a human gate, a block, or the budget.
# Usage: tools/autopilot/run.sh [--until W2] [--budget-usd 50] [--max-turns 80]
# Requires: Claude Code signed in (claude auth login), git remote with push access if PRs are wanted,
# and the permission rules from docs/playbooks/autopilot.md §4 in your settings.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

UNTIL=""; BUDGET="${AUTOPILOT_BUDGET_USD:-50}"; TURNS="${AUTOPILOT_MAX_TURNS:-80}"
while [ $# -gt 0 ]; do
  case "$1" in
    --until) UNTIL="--until $2"; shift 2;;
    --budget-usd) BUDGET="$2"; shift 2;;
    --max-turns) TURNS="$2"; shift 2;;
    *) echo "unknown option $1" >&2; exit 2;;
  esac
done

mkdir -p .autopilot/runs
LOG=".autopilot/runs/$(date -u +%Y%m%dT%H%M%SZ).jsonl"

GOAL="/goal Run the autopilot skill (/autopilot ${UNTIL}) tick after tick. The goal is met when the \
latest AUTOPILOT status line printed in this conversation shows nothing ready and every remaining \
step is done, waiting_human or blocked${UNTIL:+, or the --until target is done}. It is impossible if two \
consecutive ticks finish no step and change no state. Each tick must end by printing the AUTOPILOT \
status line. Stop after ${TURNS} turns."

# Auto mode: a classifier reviews actions instead of prompting; anything that would still prompt is denied.
claude -p "$GOAL" \
  --permission-mode auto \
  --permission-prompts none \
  --max-budget-usd "$BUDGET" \
  --output-format stream-json --verbose \
  | tee "$LOG" \
  | jq -rj 'select(.type=="assistant") | .message.content[]? | select(.type=="text") | .text + "\n"'

echo
echo "Log: $LOG"
jq -r 'select(.type=="result") | "result: \(.subtype)  cost: $\(.total_cost_usd)  turns: \(.num_turns)"' "$LOG" | tail -1
