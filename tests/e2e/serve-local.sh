#!/usr/bin/env bash
# Try Spectio on this machine (P1 Task 20): `spectio init --local` in a fresh temporary directory,
# then `spectio serve` in the foreground. Prints the address to open; Ctrl-C stops the server and
# removes the directory. Builds web/dist first when it is missing.
#
#   bash tests/e2e/serve-local.sh [--port N]
#
# There is no sign-in link yet (P1 Tasks 12 to 16, inbox #80): the server listens on 127.0.0.1
# only, in local mode, and serves the screens to anyone on this machine who opens the address.
set -euo pipefail

usage() { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; }

port=""
while [ $# -gt 0 ]; do
  case "$1" in
    --port)
      [ $# -ge 2 ] || { echo "serve-local: --port needs a number" >&2; exit 2; }
      port=$2; shift 2 ;;
    --port=*) port=${1#--port=}; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "serve-local: unknown option $1 (try --help)" >&2; exit 2 ;;
  esac
done
case "$port" in
  "") ;;
  *[!0-9]*) echo "serve-local: --port must be a number, not $port" >&2; exit 2 ;;
  *) [ "$port" -ge 1 ] && [ "$port" -le 65535 ] || { echo "serve-local: --port must be 1 to 65535" >&2; exit 2; } ;;
esac

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
# shellcheck source=/dev/null
. "$repo/dev/versions.env"

if [ ! -f "$repo/web/dist/index.html" ]; then
  echo "== The screens are not built: building web/dist (npm ci --ignore-scripts, then vite build)"
  npm --prefix "$repo/web" ci --no-audit --no-fund --ignore-scripts
  npm --prefix "$repo/web" run build
fi

home=$(mktemp -d "${TMPDIR:-/tmp}/spectio-local.XXXXXX")
chmod 700 "$home"
server=""
stop() {
  trap - INT TERM EXIT
  if [ -n "$server" ] && kill -0 "$server" 2>/dev/null; then
    echo
    echo "== Stopping the server"
    kill -TERM "$server" 2>/dev/null || true
    wait "$server" 2>/dev/null || true
  fi
  rm -rf "$home"
  echo "== Removed $home"
}
trap stop EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

spectio() { uv run --locked --project "$repo" --python "$PYTHON_VERSION" spectio "$@"; }
export SPECTIO_CONFIG=$home/data/spectio.toml

mkdir -m 700 "$home/data" "$home/db" "$home/runs"
# Until the wheel carries the bridges (P1 Task 21), build nf-spectio here when Nextflow is found.
nextflow=${SPECTIO_ENGINES_NEXTFLOW_CMD:-$(command -v nextflow || true)}
if [ -z "${SPECTIO_BRIDGES_DIR:-}" ] && [ -n "$nextflow" ]; then
  echo "== Building nf-spectio with $nextflow"
  NEXTFLOW=$nextflow bash "$repo/engine-bridges/nf-spectio/build.sh" "$home/bridges" >/dev/null
  export SPECTIO_BRIDGES_DIR=$home/bridges
fi
echo "== spectio init --local in $home"
spectio init --local --data-dir "$home/data" --db-dir "$home/db" --runs-root "$home/runs" \
  ${port:+--port "$port"}
port=$(sed -n 's/^port *= *\([0-9][0-9]*\).*/\1/p' "$SPECTIO_CONFIG" | head -n 1)

echo "== spectio serve"
# Not through the shell function: $! must be uv itself, which passes SIGTERM on to the server.
uv run --locked --project "$repo" --python "$PYTHON_VERSION" spectio serve &
server=$!
url="http://127.0.0.1:$port/"
for _ in $(seq 1 100); do
  if curl -fsS -o /dev/null "${url}api/v1/version" 2>/dev/null; then
    cat <<EOF

  Spectio is running. Open $url
  Runs go under $home/runs. No sign-in link yet: the server answers on 127.0.0.1 only.
  Press Ctrl-C to stop it; the temporary directory is removed.

EOF
    wait "$server"
    exit $?
  fi
  kill -0 "$server" 2>/dev/null || { echo "serve-local: spectio serve exited" >&2; exit 1; }
  sleep 0.2
done
echo "serve-local: no answer on $url after 20 s" >&2
exit 1
