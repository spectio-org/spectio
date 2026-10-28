#!/usr/bin/env bash
# Install Nextflow 26.10.4 / 25.10.9 and Snakemake 9.27.1 the way dev/bootstrap.sh does, into $E.
set -u
R=/home/user/spectio/.claude/worktrees/agent-aca1328f0b7770526
. "$R/dev/versions.env"
E=/tmp/claude-0/-home-user-spectio/6396c38c-2a61-53ee-956c-4203b452f099/scratchpad/eng
mkdir -p "$E"; cd "$E"
GH=https://github.com/nextflow-io/nextflow/releases/download
(
for pair in "$NEXTFLOW_VERSION $NEXTFLOW_SHA256" "$NEXTFLOW_25_10_VERSION $NEXTFLOW_25_10_SHA256"; do
  set -- $pair
  curl -fsSL --retry 3 -o "nextflow-$1" "$GH/v$1/nextflow-$1-dist" && echo "$2  nextflow-$1" | sha256sum -c && chmod +x "nextflow-$1"
done
) &
uv python install --no-bin "$PYTHON_VERSION" >/dev/null 2>&1
uv venv --quiet --python "$PYTHON_VERSION" smk
uv pip sync --quiet --python smk/bin/python --require-hashes "$R/dev/snakemake.lock.txt"
smk/bin/snakemake --version
wait
ls -la
