#!/usr/bin/env bash
# Prove that the pinned toolchain works (docs/specs/dev-environment-and-testing.md §1, "Checks").
# Prints each tool and its version against dev/versions.env, then runs one smoke test per layer.
# Exits 1 on the first failure, naming the tool.
#
#   bash dev/doctor.sh
#   SPECTIO_DOCTOR_STRICT=1 bash dev/doctor.sh   a skipped layer fails too (CI, where all must run)
#
# sind and kind are skipped, with the reason, when Docker runs on cgroup v1 (Claude Code cloud
# sessions, spike D2); they run in CI.
# shellcheck disable=SC2015  # "a && b || fail ...": fail exits, so it is the else branch
set -uo pipefail
# shellcheck source=dev/lib.sh
. "$(dirname "$0")/lib.sh"

work=$(mktemp -d)
realm=spx-doctor-$$          # one sind realm and kind cluster per run: parallel runs never collide (§5)
sind_up=0 kind_up=0
cleanup() {
  [ "$sind_up" = 0 ] || sind --realm "$realm" delete realm >/dev/null 2>&1
  [ "$kind_up" = 0 ] || kind delete cluster --name "$realm" >/dev/null 2>&1
  rm -rf "$work"
}
trap cleanup EXIT

skipped=0
row() { printf '%-5s %-17s %s\n' "$@"; }
ok() { row ok "$1" "$2"; }
fail() {
  row FAIL "$1" "$2"
  [ -s "$work/log" ] && tail -n 20 "$work/log" | sed 's/^/      | /'
  echo "doctor: FAILED: $1"
  exit 1
}
skip() {
  if [ "${SPECTIO_DOCTOR_STRICT:-0}" = 1 ]; then
    : >"$work/log"
    fail "$1" "skipped, and SPECTIO_DOCTOR_STRICT=1: $2"
  fi
  row skip "$1" "$2"
  skipped=$((skipped + 1))
}
# pinned TOOL WANT GOT: the found version must equal the pin.
pinned() {
  [ -n "$3" ] || fail "$1" "not found; run: bash dev/bootstrap.sh"
  [ "$3" = "$2" ] || fail "$1" "found $3, pinned $2 in dev/versions.env; run: bash dev/bootstrap.sh"
  ok "$1" "$3"
}
# run CMD...: run quietly, output to $work/log, which fail() shows.
run() { "$@" >"$work/log" 2>&1; }

echo "spectio doctor: $SPECTIO_REPO, pins from dev/versions.env"
echo "--- versions"
ensure_dockerd 2>"$work/log" || fail docker "daemon not running"
v=$(docker version --format '{{.Server.Version}}' 2>/dev/null)
[ "${v%%.*}" -ge "$DOCKER_MIN_MAJOR" ] 2>/dev/null || fail docker "found ${v:-none}, need >= $DOCKER_MIN_MAJOR"
ok docker "$v (cgroup v$(docker info --format '{{.CgroupVersion}}'))"

v=$(java -version 2>&1 | sed -n 's/.*version "\([0-9]*\).*/\1/p' | head -n 1)
[ "$v" = "$JAVA_MAJOR" ] || fail java "found major ${v:-none}, need $JAVA_MAJOR"
ok java "$(java -version 2>&1 | sed -n 's/.*version "\(.*\)".*/\1/p' | head -n 1)"

pinned uv "$UV_VERSION" "$(uv --version 2>/dev/null | cut -d' ' -f2)"
py=$(uv python find --managed-python "$PYTHON_VERSION" 2>/dev/null)
read -r v sqlite < <("${py:-false}" -c 'import sys, sqlite3; print(sys.version.split()[0], sqlite3.sqlite_version)' 2>/dev/null)
pinned python "$PYTHON_VERSION" "${v:-}"
[ "$(printf '%s\n' "$SQLITE_MIN_VERSION" "$sqlite" | sort -V | head -n 1)" = "$SQLITE_MIN_VERSION" ] ||
  fail sqlite "Python $PYTHON_VERSION embeds SQLite $sqlite, need >= $SQLITE_MIN_VERSION"
ok sqlite "$sqlite"
pinned node "$NODE_VERSION" "$(node --version 2>/dev/null | tr -d v)"
pinned playwright "$PLAYWRIGHT_VERSION" "$(node -p "require('playwright/package.json').version" 2>/dev/null)"
nf_version() { "$1" -v 2>/dev/null | sed -n 's/^nextflow version \([0-9]*\.[0-9]*\.[0-9]*\).*/\1/p'; }
pinned nextflow "$NEXTFLOW_VERSION" "$(nf_version nextflow)"
for v in "$NEXTFLOW_25_10_VERSION" "$NEXTFLOW_25_04_VERSION"; do
  pinned "nextflow-$v" "$v" "$(nf_version "nextflow-$v")"
done
pinned snakemake "$SNAKEMAKE_VERSION" "$(snakemake --version 2>/dev/null)"
smk_python=$(uv tool dir 2>/dev/null)/snakemake/bin/python
pinned smk-slurm "$SNAKEMAKE_EXECUTOR_SLURM_VERSION" \
  "$("$smk_python" -c 'import importlib.metadata as m; print(m.version("snakemake-executor-plugin-slurm"))' 2>/dev/null)"
pinned sind "$SIND_VERSION" "$(sind version 2>/dev/null | cut -d' ' -f2)"
pinned kind "$KIND_VERSION" "$(kind version 2>/dev/null | cut -d' ' -f2 | tr -d v)"
pinned kubectl "$KUBECTL_VERSION" "$(kubectl version --client 2>/dev/null | sed -n 's/^Client Version: v//p')"
pinned helm "$HELM_VERSION" "$(helm version --short 2>/dev/null | sed 's/^v//; s/+.*//')"

echo "--- smoke tests"
# docker: run hello-world, pinned by digest.
t=$SECONDS
run ensure_image "$HELLO_WORLD_IMAGE" || fail docker "cannot pull $HELLO_WORLD_IMAGE"
run docker run --rm "${HELLO_WORLD_IMAGE%@*}" && grep -q 'Hello from Docker!' "$work/log" ||
  fail docker "docker run hello-world failed"
ok docker "docker run hello-world ($((SECONDS - t))s)"

if cgroup_v1; then
  reason="Docker runs on cgroup v1 here; sind and kind need cgroup v2 (spike D2). They run in CI."
  skip sind "$reason"
  skip kind "$reason"
else
  # sind: a controller and a worker, then a job that must finish (sbatch --wait).
  t=$SECONDS
  for image in "$SIND_NODE_IMAGE" "$SIND_DNS_IMAGE"; do
    run ensure_image "$image" || fail sind "cannot pull $image"
  done
  sind_up=1
  printf 'kind: Cluster\nname: doctor\ndefaults:\n  image: %s\n' "${SIND_NODE_IMAGE%@*}" >"$work/sind.yaml"
  run sind --realm "$realm" create cluster --config "$work/sind.yaml" --data volume ||
    fail sind "sind create cluster failed"
  run sind --realm "$realm" exec doctor -- bash -c 'cd /data && sbatch --wait -o doctor.out --wrap hostname && cat doctor.out' ||
    fail sind "sbatch --wait --wrap hostname failed"
  ok sind "cluster up, sbatch --wait --wrap hostname ran on $(tail -n 1 "$work/log") ($((SECONDS - t))s)"

  # kind: a one-node cluster, then a Job that must complete.
  t=$SECONDS
  for image in "$KIND_NODE_IMAGE" "$BUSYBOX_IMAGE"; do
    run ensure_image "$image" || fail kind "cannot pull $image"
  done
  kind_up=1
  run kind create cluster --name "$realm" --image "${KIND_NODE_IMAGE%@*}" --wait 180s ||
    fail kind "kind create cluster failed"
  run kind load docker-image "${BUSYBOX_IMAGE%@*}" --name "$realm" || fail kind "kind load docker-image failed"
  k() { kubectl --context "kind-$realm" "$@"; }
  run k create job doctor --image="${BUSYBOX_IMAGE%@*}" -- echo spectio-doctor-ok &&
    run k wait --for=condition=complete job/doctor --timeout=120s &&
    run k logs job/doctor && grep -q spectio-doctor-ok "$work/log" ||
    fail kind "the Job did not complete"
  ok kind "cluster up, Job completed ($((SECONDS - t))s)"
fi

# nextflow: the synthetic fixture pipeline (§10.1), test profile, local executor.
t=$SECONDS
mkdir -p "$work/nf"
(cd "$work/nf" && run nextflow run "$SPECTIO_REPO/tests/pipelines/synthetic/nextflow" -profile test,local) ||
  fail nextflow "nextflow run tests/pipelines/synthetic/nextflow -profile test,local failed"
ok nextflow "synthetic pipeline, test,local ($((SECONDS - t))s)"

# snakemake: a dry run of the synthetic twin.
t=$SECONDS
run snakemake -n -s "$SPECTIO_REPO/tests/pipelines/synthetic/snakemake/workflow/Snakefile" \
  --directory "$work/smk" --cores 1 || fail snakemake "snakemake -n on the synthetic Snakefile failed"
ok snakemake "dry run of the synthetic Snakefile ($((SECONDS - t))s)"

# playwright: headless Chromium opens a page.
t=$SECONDS
run node -e '
  const { chromium } = require("playwright");
  (async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    await page.goto("about:blank");
    console.log("chromium " + browser.version());
    await browser.close();
  })().catch((e) => { console.error(e); process.exit(1); });' || fail playwright "Chromium did not open about:blank"
ok playwright "$(tail -n 1 "$work/log") opened about:blank ($((SECONDS - t))s)"

echo "doctor: all layers passed ($skipped skipped)"
