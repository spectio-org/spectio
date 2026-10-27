#!/usr/bin/env bash
# The four security checks of docs/specs/dev-environment-and-testing.md §11, the same in CI
# (.github/workflows/security.yml) and on a laptop. Linux x86_64 only, like the CI matrix.
#
#   bash tools/ci/security.sh all                     # every check, from the repository root
#   bash tools/ci/security.sh secrets|deps|sast|workflows
#   SECRETS_LOG_OPTS="base..head" bash tools/ci/security.sh secrets   # only these commits (CI on PRs)
#
# Each check exits non-zero on a finding. Exceptions are reviewed entries, with a reason, in the
# tool's own ignore file: .gitleaksignore / .gitleaks.toml, osv-scanner.toml, .semgrepignore,
# .github/zizmor.yml. Inline suppression comments do not count.
set -euo pipefail

# Pinned tools. Release binaries are checked against the SHA-256 of their release's checksums file.
GITLEAKS_VERSION=8.30.1
GITLEAKS_SHA256=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb  # gitleaks_8.30.1_linux_x64.tar.gz
OSV_SCANNER_VERSION=2.7.0
OSV_SCANNER_SHA256=160c6253e2922e9e0a6a9771c5c4c40a4b3c6090b34a3cdd5e80c96cc2e4218b  # osv-scanner_linux_amd64
ACTIONLINT_VERSION=1.7.12
ACTIONLINT_SHA256=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8  # actionlint_1.7.12_linux_amd64.tar.gz
ZIZMOR_VERSION=1.31.1    # PyPI, run with uvx
SEMGREP_VERSION=1.182.1  # PyPI, run with uvx

BIN="${SPECTIO_TOOLS_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/spectio/tools}"
mkdir -p "$BIN"

# fetch URL SHA256 [TAR_MEMBER]: download once into $BIN under its checksum (so a version bump never
# reuses an old binary), re-verify it on every run, unpack, and set TOOL to the binary's path.
fetch() {
  local url=$1 sum=$2 member=${3:-} file="$BIN/$2"
  if [ ! -f "$file" ]; then curl -fsSL --retry 3 -o "$file.part" "$url"; mv "$file.part" "$file"; fi
  echo "$sum  $file" | sha256sum -c --quiet - || { echo "checksum mismatch for $url" >&2; rm -f "$file"; exit 2; }
  if [ -n "$member" ]; then
    mkdir -p "$file.d"; tar -xzf "$file" -C "$file.d" "$member"; TOOL="$file.d/$member"
  else
    chmod +x "$file"; TOOL=$file
  fi
}

secrets() {
  fetch "https://github.com/gitleaks/gitleaks/releases/download/v$GITLEAKS_VERSION/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" "$GITLEAKS_SHA256" gitleaks
  # Without SECRETS_LOG_OPTS: the whole history (weekly, and locally).
  # --ignore-gitleaks-allow: an inline `gitleaks:allow` comment does not hide a finding.
  "$TOOL" git --no-banner --redact --verbose --ignore-gitleaks-allow ${SECRETS_LOG_OPTS:+--log-opts="$SECRETS_LOG_OPTS"} .
}

deps() {
  fetch "https://github.com/google/osv-scanner/releases/download/v$OSV_SCANNER_VERSION/osv-scanner_linux_amd64" "$OSV_SCANNER_SHA256"
  # Every lockfile in the tree: package-lock.json today, uv.lock once the Python packages exist.
  local rc=0
  "$TOOL" scan source --recursive . || rc=$?
  # 128 means "no packages found": a pass only while no lockfile is tracked.
  if [ "$rc" -eq 128 ] && [ -z "$(git ls-files -- '*package-lock.json' '*uv.lock')" ]; then
    echo "osv-scanner: no lockfile found, nothing to audit"; rc=0
  fi
  return "$rc"
}

sast() {
  # --severity accepts INFO, WARNING or ERROR (`semgrep scan --help`, 1.182.1; docs.semgrep.dev/cli-reference,
  # read 2026-10-27). ERROR, the highest, stands for the "high or critical" bar of §11.
  # --disable-nosem: an inline `nosemgrep` comment does not hide a finding. semgrep also reads a .semgrepignore in
  # any directory (`semgrep scan --help`); only the root one is allowed.
  if git ls-files -- '*.semgrepignore' | grep -vx '.semgrepignore'; then
    echo "a .semgrepignore outside the repository root hides code from SAST; move its entries to /.semgrepignore" >&2
    return 1
  fi
  uvx --from "semgrep==$SEMGREP_VERSION" semgrep scan --metrics off --error --severity ERROR --disable-nosem \
    --config p/python --config p/javascript
}

workflows() {
  fetch "https://github.com/rhysd/actionlint/releases/download/v$ACTIONLINT_VERSION/actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz" "$ACTIONLINT_SHA256" actionlint
  command -v shellcheck >/dev/null || echo "note: shellcheck not found, actionlint skips the shell checks of run: blocks"
  local rc=0
  "$TOOL" || rc=1
  # Online audits when GH_TOKEN or GITHUB_TOKEN is set (CI), offline otherwise. Fails on low severity and above.
  uvx "zizmor==$ZIZMOR_VERSION" --min-severity low . || rc=1
  return "$rc"
}

case "${1:-}" in
  secrets|deps|sast|workflows) "$1" ;;
  all) rc=0; for c in secrets deps sast workflows; do echo "== $c"; "$c" || { echo "== $c: FAILED"; rc=1; }; done; exit "$rc" ;;
  *) echo "usage: $0 {secrets|deps|sast|workflows|all}" >&2; exit 2 ;;
esac
