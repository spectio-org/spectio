#!/usr/bin/env bash
# Runner disk and memory probe for pipelines-real.yml (results: docs/research/corpus-ci-2026-10-27.md).
#   runner_probe.sh free            remove toolchains the corpus jobs never use and the preloaded Docker images (sudo;
#                                   GitHub-hosted runners only, never on a laptop)
#   runner_probe.sh sample          print CPU and memory, then sample free memory and disk every 5 s in the background
#   runner_probe.sh summary NAME    write resources.json (and Nextflow's view of memory, when a .nextflow.log exists)
#                                   and append both to the job summary
# Files: $RUNNER_TEMP/samples.txt, $RUNNER_TEMP/res/resources.json, $RUNNER_TEMP/res/resources.txt.
set -euo pipefail
: "${RUNNER_TEMP:?RUNNER_TEMP must be set}"

case "${1:-}" in
  free)
    df -h /
    sudo rm -rf /usr/local/lib/android /usr/share/dotnet /opt/ghc /usr/local/.ghcup /opt/hostedtoolcache/CodeQL \
      /usr/share/swift /usr/local/share/boost /usr/local/share/powershell /usr/local/julia* /opt/az /opt/microsoft
    docker image prune -af > /dev/null
    df -h /
    ;;
  sample)
    grep -E 'MemTotal|MemAvailable|SwapTotal' /proc/meminfo; nproc
    (while :; do
       echo "$(date +%s) $(awk '/^MemAvailable/ {print $2}' /proc/meminfo) $(df -k --output=avail / | tail -1)"
       sleep 5
     done) > "$RUNNER_TEMP/samples.txt" 2>&1 &
    ;;
  summary)
    name=${2:?usage: runner_probe.sh summary NAME}
    mkdir -p "$RUNNER_TEMP/res"
    total=$(awk '/^MemTotal/ {print $2}' /proc/meminfo)
    awk -v total="$total" -v name="$name" 'NR == 1 {a0 = $2; d0 = $3; amin = $2; dmin = $3; t0 = $1}
      {if ($2 < amin) amin = $2; if ($3 < dmin) dmin = $3; t1 = $1}
      END {g = 1048576; printf "{\"name\": \"%s\", \"mem_total_gb\": %.2f, \"mem_avail_start_gb\": %.2f, \"mem_avail_min_gb\": %.2f, \"run_peak_gb\": %.2f, \"disk_free_start_gb\": %.1f, \"disk_free_min_gb\": %.1f, \"sampled_s\": %d}\n",
           name, total / g, a0 / g, amin / g, (a0 - amin) / g, d0 / g, dmin / g, t1 - t0}' \
      "$RUNNER_TEMP/samples.txt" > "$RUNNER_TEMP/res/resources.json"
    # Nextflow's local executor caps tasks at the memory it reads from the OS (LocalPollingMonitor); nf-core jobs only.
    logs=("$RUNNER_TEMP"/corpus/*/.nextflow.log)
    if [ -f "${logs[0]}" ]; then
      grep -h -m1 'local task monitor' "${logs[@]}" > "$RUNNER_TEMP/res/resources.txt" || true
    fi
    { echo '```'; cat "$RUNNER_TEMP/res/resources.json" "$RUNNER_TEMP/res/resources.txt" 2>/dev/null || true; echo '```'; } \
      >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
    cat "$RUNNER_TEMP/res/resources.json"
    ;;
  *)
    echo "usage: runner_probe.sh free | sample | summary NAME" >&2; exit 2 ;;
esac
