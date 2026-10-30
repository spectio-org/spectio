#!/usr/bin/env bash
# Spike first-look: the local demo with a real Nextflow and the spike T2 plugin nf-spectio 0.0.1.
#
#   spikes/first-look/run-local.sh [--port N] [--synthetic]
#       install Nextflow (pinned) and the plugin if absent, uv sync, start the demo; then open the
#       printed URL and use "New run". Ctrl-C stops it.
#   spikes/first-look/run-local.sh --cli [--samples N] [--fail] [--port N]
#       the same, but also launch one dummy run from this shell (its Nextflow output shows here);
#       the demo keeps serving after the run ends, until Ctrl-C.
#
# Everything it installs goes under $SPECTIO_FIRST_LOOK_HOME (default ~/.cache/spectio-first-look):
# the Nextflow launcher, NXF_HOME (with the plugin) and one data directory per start.
# Nothing is written to ~/.nextflow. Clean up: rm -rf "$SPECTIO_FIRST_LOOK_HOME".
set -euo pipefail

NF_VERSION=${NF_VERSION:-26.10.4}  # pinned; 25.10.9 also works (spike T2 used both)
PORT=8765 MODE=ui SAMPLES=3 FAIL=false SYNTH=()
while [ $# -gt 0 ]; do
  case $1 in
    --port) PORT=$2; shift ;;
    --cli) MODE=cli ;;
    --samples) SAMPLES=$2; shift ;;
    --fail) FAIL=true ;;
    --synthetic) SYNTH=(--synthetic) ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (see --help)" >&2; exit 2 ;;
  esac
  shift
done

HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
BASE=${SPECTIO_FIRST_LOOK_HOME:-$HOME/.cache/spectio-first-look}
export NXF_HOME=$BASE/nxf-home NXF_ANSI_LOG=false
NF=$BASE/nextflow-$NF_VERSION
say() { printf '\033[1m==> %s\033[0m\n' "$*"; }

# 1. Prerequisites: Java 17+ (Nextflow 26.10 needs it), uv, curl, a free port.
command -v java >/dev/null || { echo "java not found: install Java 17+ (21 is the pin)" >&2; exit 1; }
JAVA_MAJOR=$(java -version 2>&1 | sed -n 's/.*version "\([0-9]*\).*/\1/p' | head -1)
[ "${JAVA_MAJOR:-0}" -ge 17 ] || { echo "Java $JAVA_MAJOR found, Nextflow $NF_VERSION needs 17+" >&2; exit 1; }
command -v uv >/dev/null || { echo "uv not found: https://docs.astral.sh/uv/" >&2; exit 1; }
python3 -c "import socket,sys; s=socket.socket(); s.bind(('127.0.0.1', int(sys.argv[1])))" "$PORT" \
  2>/dev/null || { echo "port $PORT is in use: pass --port N" >&2; exit 1; }

# 2. Nextflow: the -dist launcher of the pinned version, checked against dev/versions.env.
mkdir -p "$BASE" && chmod 700 "$BASE"
if [ ! -x "$NF" ]; then
  # shellcheck disable=SC1091
  . "$REPO/dev/versions.env"
  case $NF_VERSION in
    "$NEXTFLOW_VERSION") SHA=$NEXTFLOW_SHA256 ;;
    "$NEXTFLOW_25_10_VERSION") SHA=$NEXTFLOW_25_10_SHA256 ;;
    *) echo "no checksum for Nextflow $NF_VERSION in dev/versions.env" >&2; exit 1 ;;
  esac
  say "downloading Nextflow $NF_VERSION"
  curl -fsSL --retry 3 -o "$NF.part" \
    "https://github.com/nextflow-io/nextflow/releases/download/v$NF_VERSION/nextflow-$NF_VERSION-dist"
  GOT=$( (sha256sum "$NF.part" 2>/dev/null || shasum -a 256 "$NF.part") | cut -d' ' -f1)
  [ "$GOT" = "$SHA" ] || { echo "checksum mismatch for $NF.part: $GOT" >&2; exit 1; }
  chmod +x "$NF.part" && mv "$NF.part" "$NF"
fi
say "$("$NF" -version 2>/dev/null | sed -n 's/^ *\(version .*\)/Nextflow \1/p')"

# 3. The plugin: compiled with the Groovy compiler inside the Nextflow jar, into NXF_HOME/plugins.
PLUGIN_DIR=$NXF_HOME/plugins/nf-spectio-0.0.1
if [ ! -d "$PLUGIN_DIR" ] || [ "$HERE/nf-spectio/src/spectio/SpectioPlugin.groovy" -nt "$PLUGIN_DIR" ]; then
  say "building nf-spectio 0.0.1"
  "$HERE/nf-spectio/build.sh" "$NF" "$NXF_HOME/plugins" >/dev/null 2>&1 \
    || { echo "plugin build failed: run $HERE/nf-spectio/build.sh $NF $NXF_HOME/plugins" >&2; exit 1; }
fi

# 4. Python: the workspace (spectio, spectio-server, spectio-sdk).
say "uv sync"
(cd "$REPO" && uv sync --quiet)

# 5. The demo.
DATA=$BASE/data/$(date +%Y%m%d-%H%M%S)
mkdir -p "$BASE/data" && chmod 700 "$BASE/data"
DEMO=(uv run --project "$REPO" python "$HERE/demo.py" --nextflow "$NF" --port "$PORT" --data "$DATA" ${SYNTH[@]+"${SYNTH[@]}"})
URL=http://127.0.0.1:$PORT/
if [ "$MODE" = ui ]; then
  say "demo on $URL (Ctrl-C to stop); data in $DATA"
  exec "${DEMO[@]}"
fi

"${DEMO[@]}" > "$DATA.log" 2>&1 &
DEMO_PID=$!
trap 'kill $DEMO_PID 2>/dev/null || true' EXIT
for _ in $(seq 60); do curl -fs -o /dev/null "$URL" && break; sleep 0.5; done
curl -fs -o /dev/null "$URL" || { echo "demo did not start, see $DATA.log" >&2; exit 1; }
say "demo on $URL; log in $DATA.log"

# Register the run (what `spectio run` would ask the server), then start Nextflow from here.
REPLY=$(curl -fsS -H 'Content-Type: application/json' \
  -d "{\"samples\": $SAMPLES, \"fail\": $FAIL}" "${URL}api/launches")
field() { python3 -c 'import json,sys; v=json.loads(sys.argv[1])[sys.argv[2]]; print(*v, sep="\n") if isinstance(v, list) else print(v)' "$REPLY" "$1"; }
LAUNCH_DIR=$(field launch_dir)
ARGS=(); while IFS= read -r a; do ARGS+=("$a"); done < <(field args)  # bash 3.2 (macOS) too
say "run page: $(field page)"
say "launch directory: $LAUNCH_DIR"
cd "$LAUNCH_DIR"
set +e
SPECTIO_ENDPOINT=$(field endpoint) "$NF" "${ARGS[@]}"
say "nextflow exited $?; the demo keeps serving $URL until Ctrl-C"
wait $DEMO_PID
