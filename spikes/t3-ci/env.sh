# shellcheck shell=bash
# Sourced inside the sind nodes (submitter, and batch jobs through sbatch's default --export=ALL).
# The tools were installed on the runner by dev/bootstrap.sh into /data/tools, which every node
# mounts at the same path, so the venv shebangs and symlinks resolve inside the nodes too.
SMK_VENV=$(dirname "$(dirname "$(readlink -f /data/tools/bin/snakemake)")")
export PATH="$SMK_VENV/bin:/data/tools/bin:/data/tools/jdk/bin:$PATH"  # venv first: python3 with PyYAML
export JAVA_HOME=/data/tools/jdk
export NXF_OPTS="-Xms128m -Xmx768m"
export NXF_ANSI_LOG=false
