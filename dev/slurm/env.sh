# shellcheck shell=bash
# Sourced inside the sind nodes (submitter, and batch jobs through sbatch's default --export=ALL), from
# the data directory that dev/slurm/cluster.sh copies it to. The tools were installed on the host by
# dev/bootstrap.sh into <data>/tools, which every node mounts at the same path, so the venv shebangs and
# symlinks resolve inside the nodes too.
DATA=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SMK_VENV=$(dirname "$(dirname "$(readlink -f "$DATA/tools/bin/snakemake")")")
export PATH="$SMK_VENV/bin:$DATA/tools/bin:$DATA/tools/jdk/bin:$PATH"  # venv first: python3 with PyYAML
export JAVA_HOME=$DATA/tools/jdk
export NXF_OPTS="-Xms128m -Xmx768m"
export NXF_ANSI_LOG=false
