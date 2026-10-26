#!/usr/bin/env bash
# Block accidental commits of regenerated docs media (screenshots, combined captures).
# Port of depictio's scripts/check-screenshot-churn.sh (MIT, 0d1aa0a).
#
# Re-running tools/media/shots.py or combo.py rewrites every image in place,
# even when nothing visible changed (encoder noise, a font hinting difference),
# and the rewrite gets swept into unrelated commits. depictio once shipped 64
# thumbnails of broken dashboards this way.
#
# Regenerating is legitimate; it just has to be deliberate, and only after you
# have looked at the new images. Opt in with:
#
#   SPECTIO_ALLOW_SCREENSHOT_UPDATE=1 git commit ...
#
# Usage: as a pre-commit hook, or in CI with a base ref:
#   tools/media/check_churn.sh                 # staged files
#   tools/media/check_churn.sh origin/main     # files changed against a ref
# A few files (THRESHOLD, default 3) pass: that is a targeted update, not churn.
set -euo pipefail

if [ "${SPECTIO_ALLOW_SCREENSHOT_UPDATE:-0}" != "0" ]; then
    exit 0
fi

DIRS=(docs/assets/shots docs/assets/media)
THRESHOLD="${SPECTIO_SCREENSHOT_CHURN_THRESHOLD:-3}"

if [ $# -ge 1 ]; then
    if git merge-base "$1" HEAD >/dev/null 2>&1; then
        changed=$(git diff --name-only --diff-filter=M "$1"...HEAD -- "${DIRS[@]}")
    else  # shallow or unrelated histories: compare the trees directly
        changed=$(git diff --name-only --diff-filter=M "$1" HEAD -- "${DIRS[@]}")
    fi
else
    changed=$(git diff --cached --name-only --diff-filter=M -- "${DIRS[@]}")
fi

[ -z "$changed" ] && exit 0
count=$(printf '%s\n' "$changed" | wc -l | tr -d '[:space:]')
[ "$count" -le "$THRESHOLD" ] && exit 0

echo "Blocked: ${count} existing screenshot or capture file(s) rewritten."
echo
printf '%s\n' "$changed" | sed 's/^/  /'
echo
echo "A mass rewrite is usually regeneration noise. If the update IS intended,"
echo "look at the new images, then:"
echo "  SPECTIO_ALLOW_SCREENSHOT_UPDATE=1 git commit ..."
echo
echo "Otherwise drop the churn:"
echo "  git restore --staged --worktree -- ${DIRS[*]}"
exit 1
