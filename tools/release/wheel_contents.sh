#!/usr/bin/env bash
# The wheel-contents check: every entry of a wheel (or sdist) on stdin matches exactly one line of
# the list file, and every list line matches an entry — nothing more, nothing less. The list's
# `<name>-<version>.dist-info/METADATA` line names the version the list was written for; that
# version becomes a glob too, so a list written for 0.0.1 also proves a 0.0.1rc1 wheel. A sdist
# list (tests/packaging/test_wheel.sh builds them from a wheel list) has no dist-info line: pass
# its version as the third argument.
#
#   tools/release/wheel_contents.sh <name> <list-file> [<version>]   # entries on stdin
#
# Called by tests/packaging/test_wheel.sh and by .github/workflows/pypi-publish.yml (dev-env §12).
set -euo pipefail

usage() { echo "usage: $0 <name> <list-file> [<version>]    # entries on stdin" >&2; exit 2; }
[ $# -eq 2 ] || [ $# -eq 3 ] || usage
name=$1
list=$2

fail() { echo "$name: $*" >&2; exit 1; }
[ -f "$list" ] || fail "no such list file: $list"

if [ $# -eq 3 ]; then
  version=$3
else
  version=$(sed -n "s/^$name-\([^-]*\)\.dist-info\/METADATA\$/\1/p" "$list")
  [ -n "$version" ] ||
    fail "$list lists no $name-<version>.dist-info/METADATA (pass the version as the third argument)"
fi

# Bash 3.2 (macOS) has no mapfile and no associative arrays: plain indexed ones.
pats=()
while IFS= read -r pat; do pats+=("$pat"); done < <(grep -v "^#" "$list" | sed "s/${version//./\\.}/*/g")
hits=()
while IFS= read -r entry; do
  found=
  for i in "${!pats[@]}"; do
    # shellcheck disable=SC2053  # ${pats[$i]} is a glob
    if [[ $entry == ${pats[$i]} ]]; then hits[$i]=1; found=1; break; fi
  done
  [ -n "$found" ] || fail "carries $entry, which $list does not list"
done
for i in "${!pats[@]}"; do
  [ -n "${hits[$i]:-}" ] || fail "has nothing for ${pats[$i]} ($list)"
done
