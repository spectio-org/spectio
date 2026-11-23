#!/usr/bin/env bash
# Sets the release version of the four published Python projects (dev-environment-and-testing.md
# §12, "Publishing"): rewrites `version = "..."` in their pyproject.toml files, pins the workspace
# dependencies that a published wheel carries, and refreshes both uv.lock files.
#
#   tools/release/set-version.sh 0.0.1
#   tools/release/set-version.sh 0.0.1rc1    # the first RC (dev-env §15.2)
#
# release-please no longer rewrites these files (release-please-config.json has `extra-files: []`):
# run this script, in its own PR, before the `Release-As:` commit (dev-env §15.2), so the release tag and the packages stay in step. The pins
# (`spectio==<version>` in spectio-server, `spectio-sdk==<version>` in spectio and spectio-server)
# are what a wheel's METADATA carries: an rc installed from PyPI must resolve them from PyPI, not
# pull the 0.0.0 `spectio` placeholder of tools/release/pypi-placeholders/.
set -euo pipefail

usage() { echo "usage: $0 <version>    # PEP 440, e.g. 0.0.1 or 0.0.1rc1" >&2; exit 2; }
[ $# -eq 1 ] || usage
version=$1
[ "$version" = "${version#v}" ] || { echo "$0: '$version' starts with v: a PEP 440 version has none" >&2; exit 2; }
# The charset of a PEP 440 version (packaging PEP 440 "Normalization"), and the only bytes this
# script puts into sed scripts, so no metacharacter can come in through the argument.
[[ $version =~ ^[0-9A-Za-z._+!-]+$ ]] || { echo "$0: '$version' is no PEP 440 version" >&2; exit 2; }

repo=$(cd "$(dirname "$0")/../.." && pwd)
declare -a projects=(
  packages/spectio
  packages/spectio-sdk
  packages/spectio-server
  engine-bridges/snakemake-logger-plugin-spectio
)

# sed -i is not portable (BSD wants an argument): rewrite through a copy, keeping the file's mode.
rewrite() { # rewrite <file> <sed args...>
  local file=$1
  shift
  local tmp
  tmp=$(mktemp "${TMPDIR:-/tmp}/tmp.XXXXXX")
  sed "$@" "$file" >"$tmp"
  cat "$tmp" >"$file"
  rm -f "$tmp"
}

for project in "${projects[@]}"; do
  file=$repo/$project/pyproject.toml
  rewrite "$file" "s/^version = \"[^\"]*\"\$/version = \"$version\"/"
  grep -q "^version = \"$version\"\$" "$file" ||
    { echo "$0: $project/pyproject.toml has no version line to rewrite" >&2; exit 1; }
done

pin() { # pin <file> <dependency>: "dep" or "dep==<old>" becomes "dep==$version"
  local file=$1 dep=$2
  rewrite "$file" -E "s/^    \"$dep(==[^\"]*)?\",$/    \"$dep==$version\",/"
  grep -q "^    \"$dep==$version\",\$" "$file" ||
    { echo "$0: $dep is not pinned to $version in $file" >&2; exit 1; }
}
pin "$repo/packages/spectio-server/pyproject.toml" spectio
pin "$repo/packages/spectio-server/pyproject.toml" spectio-sdk
pin "$repo/packages/spectio/pyproject.toml" spectio-sdk

echo "== uv lock (the root workspace)"
(cd "$repo" && uv lock)
echo "== uv lock (engine-bridges/snakemake-logger-plugin-spectio)"
(cd "$repo/engine-bridges/snakemake-logger-plugin-spectio" && uv lock)
echo "version set: $version (the four pyproject.toml, the pins, and both uv.lock)"
