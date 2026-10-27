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
# .github/zizmor.yml.
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

# fetch NAME URL SHA256 [TAR_MEMBER]: download once into $BIN, verify, unpack.
fetch() {
  local name=$1 url=$2 sum=$3 member=${4:-} tmp
  [ -x "$BIN/$name" ] && return 0
  tmp=$(mktemp)
  curl -fsSL --retry 3 -o "$tmp" "$url"
  echo "$sum  $tmp" | sha256sum -c --quiet - || { echo "checksum mismatch for $url" >&2; rm -f "$tmp"; exit 2; }
  if [ -n "$member" ]; then tar -xzf "$tmp" -C "$BIN" "$member"; else mv "$tmp" "$BIN/$name"; fi
  chmod +x "$BIN/$name"
  rm -f "$tmp"
}

secrets() {
  fetch gitleaks "https://github.com/gitleaks/gitleaks/releases/download/v$GITLEAKS_VERSION/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" "$GITLEAKS_SHA256" gitleaks
  # Without SECRETS_LOG_OPTS: the whole history (weekly, and locally).
  "$BIN/gitleaks" git --no-banner --redact --verbose ${SECRETS_LOG_OPTS:+--log-opts="$SECRETS_LOG_OPTS"} .
}

deps() {
  fetch osv-scanner "https://github.com/google/osv-scanner/releases/download/v$OSV_SCANNER_VERSION/osv-scanner_linux_amd64" "$OSV_SCANNER_SHA256"
  # Every lockfile in the tree: package-lock.json today, uv.lock once the Python packages exist.
  local rc=0
  "$BIN/osv-scanner" scan source --recursive . || rc=$?
  if [ "$rc" -eq 128 ]; then echo "osv-scanner: no lockfile found, nothing to audit"; rc=0; fi
  return "$rc"
}

sast() {
  # ERROR is Semgrep's highest rule severity (INFO, WARNING, ERROR): the "high or critical" bar of §11.
  uvx --from "semgrep==$SEMGREP_VERSION" semgrep scan --metrics off --error --severity ERROR \
    --config p/python --config p/javascript
}

workflows() {
  fetch actionlint "https://github.com/rhysd/actionlint/releases/download/v$ACTIONLINT_VERSION/actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz" "$ACTIONLINT_SHA256" actionlint
  command -v shellcheck >/dev/null || echo "note: shellcheck not found, actionlint skips the shell checks of run: blocks"
  local rc=0
  "$BIN/actionlint" || rc=1
  # Online audits when GH_TOKEN or GITHUB_TOKEN is set (CI), offline otherwise. Fails on low severity and above.
  uvx "zizmor==$ZIZMOR_VERSION" --min-severity low . || rc=1
  return "$rc"
}

case "${1:-}" in
  secrets|deps|sast|workflows) "$1" ;;
  all) rc=0; for c in secrets deps sast workflows; do echo "== $c"; "$c" || { echo "== $c: FAILED"; rc=1; }; done; exit "$rc" ;;
  *) echo "usage: $0 {secrets|deps|sast|workflows|all}" >&2; exit 2 ;;
esac
