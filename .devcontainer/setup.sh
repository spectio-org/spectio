#!/usr/bin/env bash
# One-time setup of a Spectio codespace (docs/specs/dev-environment-and-testing.md §7.2).
# Pins come from dev/versions.env once step D3 writes it; the defaults below match §1 and §10.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f dev/versions.env ] && . dev/versions.env
NEXTFLOW_VERSION="${NEXTFLOW_VERSION:-26.10.3}"
SNAKEMAKE_VERSION="${SNAKEMAKE_VERSION:-9.27.1}"
mkdir -p "$HOME/.local/bin"; export PATH="$HOME/.local/bin:$PATH"

command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install --force mkdocs --with mkdocs-material
uv tool install --force "snakemake==${SNAKEMAKE_VERSION}"
if ! command -v nextflow >/dev/null; then
  (cd "$HOME/.local/bin" && export NXF_VER="$NEXTFLOW_VERSION" && curl -fsSL https://get.nextflow.io | bash && chmod +x nextflow)
fi
pip install --quiet pyyaml playwright
[ "${SPECTIO_SKIP_BROWSER:-0}" = 1 ] || python3 -m playwright install --with-deps chromium
echo "Spectio codespace ready: nextflow $NEXTFLOW_VERSION, snakemake $SNAKEMAKE_VERSION. Docs on port 8000."
