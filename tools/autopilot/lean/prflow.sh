#!/bin/bash
# usage: prflow.sh <step> <title>   (run from the worktree)
set -e
S=${SCRATCH:?set SCRATCH to your scratchpad}
B=$(git merge-base HEAD ${BASE:-origin/autopilot/integration})
step=$1; title=$2; body=$S/${step#P3-}-pr-body.md
[ -f docs-pr-body.md ] && mv docs-pr-body.md "$body"
git log --format=%b $B..HEAD | grep -q b3Fft8 && { echo TYPO; exit 1; }
git diff --name-only $B..HEAD | grep -E "^\.github|pipeline.yaml|tests/slurm/e2e" && echo "WARN reserved path"
git push -q -u origin autopilot/$step 2>&1 | tail -2
python3 tools/docs/check.py --only pr-body --pr-title "$title" --pr-body "$body" --changed <(git diff --name-only $B..HEAD) --labels no-figure | tail -2
grep -c "Type:" "$body"
