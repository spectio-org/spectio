#!/usr/bin/env bash
# One wheel with the UI and both bridges (P1 Task 21, architecture §7.3 and §6).
#
#   bash tests/packaging/test_wheel.sh      prints `RESULT wheel pass`, or `RESULT wheel fail`
#
# Builds the screens (npm ci --ignore-scripts, vite build), then `uv build --all-packages`, which
# builds each sdist and each wheel from its sdist, so a pass also proves the sdists carry the
# prebuilt UI and bridges, and checks that each wheel lists exactly its file in
# tests/packaging/contents/ and each sdist the same files under src/ (see sdist_list; the glob
# check itself is tools/release/wheel_contents.sh). Installs `spectio` alone with `uv tool install`
# into a temporary UV_TOOL_DIR and checks its version, its bridges through importlib.resources and
# its size; installs the three wheels into a venv and checks that the server finds the packaged
# screens. Needs Node, Java and Nextflow ($NEXTFLOW, for engine-bridges/nf-spectio/build.sh) and
# the Snakemake logger module (P1 Task 7). Publishes nothing.
set -euo pipefail

repo=$(cd "$(dirname "$0")/../.." && pwd)
. "$repo/dev/versions.env"
tmp=$(mktemp -d "${TMPDIR:-/tmp}/tmp.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
dist=$tmp/dist
MAX_MB=80 # architecture §6: the `spectio` environment, without [server]

fail() { echo "FAIL $*" >&2; echo "RESULT wheel fail"; exit 1; }

# The version under test: packages/spectio/pyproject.toml, the line tools/release/set-version.sh
# writes (dev-env §12). PEP 440 normalised (0.0.1-rc1 -> 0.0.1rc1), the form uv build puts into
# the file names and hatchling into METADATA.
version=$(sed -n 's/^version = "\([^"]*\)"$/\1/p' "$repo/packages/spectio/pyproject.toml")
[ -n "$version" ] || fail "no version line in packages/spectio/pyproject.toml"
version=$(uv run --no-project --with "packaging==$PACKAGING_VERSION" python -c \
  'import sys; from packaging.version import Version; print(Version(sys.argv[1]))' "$version") ||
  fail "normalising the version $version"

# The sdist's files, from the wheel's list: its files under <name>-<version>/src/, without
# dist-info, plus PKG-INFO and pyproject.toml; hatchling (a package with hatch_build.py) also adds
# the repository's .gitignore, and only-include adds hatch_build.py.
sdist_list() {
  local n=$1-$version
  printf '%s\n' "$n/PKG-INFO" "$n/pyproject.toml"
  [ ! -f "$repo/packages/${1//_/-}/hatch_build.py" ] || printf '%s\n' "$n/.gitignore" "$n/hatch_build.py"
  grep -v -e '^#' -e '\.dist-info/' -e '/$' "$repo/tests/packaging/contents/$1.wheel.txt" | sed "s|^|$n/src/|"
}
# The regular files of the tarball $1 (uv_build also lists directories).
tar_files() { python3 -I -c 'import sys, tarfile; [print(m.name) for m in tarfile.open(sys.argv[1]) if m.isfile()]' "$1"; }

echo "== Building the screens (web/dist)"
npm --prefix "$repo/web" ci --no-audit --no-fund --ignore-scripts >/dev/null
npm --prefix "$repo/web" run build >/dev/null

echo "== uv build --all-packages"
(cd "$repo" && uv build --quiet --all-packages --python "$PYTHON_VERSION" --out-dir "$dist") ||
  fail "uv build --all-packages"

runner=$dist/spectio-$version-py3-none-any.whl
server=$dist/spectio_server-$version-py3-none-any.whl
sdk=$dist/spectio_sdk-$version-py3-none-any.whl
for f in "$runner" "$server" "$sdk"; do [ -f "$f" ] || fail "no $(basename "$f")"; done

# Nothing more, nothing less: no untracked local file in an sdist, no wheel without its bridges or
# screens. The wheel lists carry their own version (the dist-info METADATA line), so a list
# written for 0.0.1 also proves a 0.0.1rc1 wheel; the sdist lists have no dist-info line, so their
# version is passed by hand (tools/release/wheel_contents.sh).
contents=$repo/tools/release/wheel_contents.sh
for name in spectio spectio_server spectio_sdk; do
  sdist_list "$name" >"$tmp/$name.sdist.txt"
  "$contents" "$name" "$tmp/$name.sdist.txt" "$version" < <(tar_files "$dist/$name-$version.tar.gz")
  "$contents" "$name" "$repo/tests/packaging/contents/$name.wheel.txt" \
    < <(unzip -Z1 "$dist/$name-$version-py3-none-any.whl")
done

echo "== uv tool install spectio (without [server])"
export UV_TOOL_DIR=$tmp/tools UV_TOOL_BIN_DIR=$tmp/bin
uv tool install --quiet --python "$PYTHON_VERSION" "$runner" --with "$sdk" || fail "uv tool install"
version_out=$(env -u SPECTIO_BRIDGES_DIR "$UV_TOOL_BIN_DIR/spectio" --version) || fail "spectio --version"
[ "$version_out" = "spectio $version" ] || fail "spectio --version printed '$version_out', not 'spectio $version'"

# The runner finds both bridges in its own package (importlib.resources), not in this checkout.
env -u SPECTIO_BRIDGES_DIR "$UV_TOOL_DIR/spectio/bin/python" -I -c '
import sys
from spectio.runner.engines import NF_SPECTIO_DIR, SNAKEMAKE_LOGGER, bridge
for name in (NF_SPECTIO_DIR, SNAKEMAKE_LOGGER):
    path = bridge(name).resolve()
    if not str(path).startswith(sys.argv[1]):
        sys.exit(f"{name} found at {path}")
' "$(cd "$UV_TOOL_DIR/spectio" && pwd -P)" || fail "the runner does not find its packaged bridges"

mb=$(du -sm "$UV_TOOL_DIR/spectio" | cut -f1)
echo "   spectio environment: ${mb} MB (limit ${MAX_MB} MB)"
[ "$mb" -lt "$MAX_MB" ] || fail "the spectio environment is ${mb} MB, not under ${MAX_MB} MB"

echo "== the three wheels in one venv: the server finds its packaged screens"
uv venv --quiet --python "$PYTHON_VERSION" "$tmp/server"
uv pip install --quiet --python "$tmp/server/bin/python" "$sdk" "$runner" "$server" ||
  fail "uv pip install of the three wheels"
"$tmp/server/bin/python" -I -c '
import sys
from spectio_server import static
ok = static.built(static.DIST) and str(static.DIST.resolve()).startswith(sys.argv[1])
sys.exit(None if ok else f"the screens come from {static.DIST}")
' "$(cd "$tmp/server" && pwd -P)" || fail "the server does not read its packaged screens"

echo "RESULT wheel pass"
