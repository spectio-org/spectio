#!/usr/bin/env bash
# One wheel with the UI and both bridges (P1 Task 21, architecture §7.3 and §6).
#
#   bash tests/packaging/test_wheel.sh      prints `RESULT wheel pass`, or `RESULT wheel fail`
#
# Builds the screens (npm ci --ignore-scripts, vite build), then `uv build --all-packages`, which
# builds each sdist and each wheel from its sdist, so a pass also proves the sdists carry the
# prebuilt UI and bridges. Installs `spectio` alone with `uv tool install` into a temporary
# UV_TOOL_DIR and checks its version, its bridges through importlib.resources and its size;
# installs the three wheels into a venv and checks that the server finds the packaged screens.
# Needs Node, Java and Nextflow ($NEXTFLOW, for engine-bridges/nf-spectio/build.sh) and the
# Snakemake logger module (P1 Task 7). Publishes nothing.
set -euo pipefail

repo=$(cd "$(dirname "$0")/../.." && pwd)
. "$repo/dev/versions.env"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
dist=$tmp/dist
MAX_MB=80 # architecture §6: the `spectio` environment, without [server]

fail() { echo "FAIL $*" >&2; echo "RESULT wheel fail"; exit 1; }
lists() { unzip -Z1 "$1" | grep -x "$2" >/dev/null || fail "$(basename "$1") does not list $2"; }
tar_lists() { tar -tzf "$1" | grep -x "$2" >/dev/null || fail "$(basename "$1") does not list $2"; }

echo "== Building the screens (web/dist)"
npm --prefix "$repo/web" ci --no-audit --no-fund --ignore-scripts >/dev/null
npm --prefix "$repo/web" run build >/dev/null

echo "== uv build --all-packages"
(cd "$repo" && uv build --quiet --all-packages --python "$PYTHON_VERSION" --out-dir "$dist") ||
  fail "uv build --all-packages"

runner=$dist/spectio-0.0.1-py3-none-any.whl
server=$dist/spectio_server-0.0.1-py3-none-any.whl
sdk=$dist/spectio_sdk-0.0.1-py3-none-any.whl
for f in "$runner" "$server" "$sdk"; do [ -f "$f" ] || fail "no $(basename "$f")"; done

lists "$runner" spectio/_bridges/nf-spectio-0.0.1/classes/META-INF/MANIFEST.MF
lists "$runner" spectio/_bridges/nf-spectio-0.0.1/classes/META-INF/extensions.idx
lists "$runner" spectio/_bridges/snakemake_logger_plugin_spectio/__init__.py
lists "$server" spectio_server/web/index.html
tar_lists "$dist/spectio-0.0.1.tar.gz" spectio-0.0.1/src/spectio/_bridges/nf-spectio-0.0.1/classes/META-INF/MANIFEST.MF
tar_lists "$dist/spectio_server-0.0.1.tar.gz" spectio_server-0.0.1/src/spectio_server/web/index.html
if unzip -Z1 "$runner" | grep '__pycache__\|\.pyc$' >/dev/null; then fail "the wheel carries bytecode"; fi

echo "== uv tool install spectio (without [server])"
export UV_TOOL_DIR=$tmp/tools UV_TOOL_BIN_DIR=$tmp/bin
uv tool install --quiet --python "$PYTHON_VERSION" "$runner" --with "$sdk" || fail "uv tool install"
version=$(env -u SPECTIO_BRIDGES_DIR "$UV_TOOL_BIN_DIR/spectio" --version) || fail "spectio --version"
[ "$version" = "spectio 0.0.1" ] || fail "spectio --version printed '$version'"

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
