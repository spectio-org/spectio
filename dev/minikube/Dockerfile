# syntax=docker/dockerfile:1
# The Spectio image of docs/specs/architecture-plugins-and-packaging.md §7.4, built from the wheels of the
# checkout (dev/minikube/up.sh builds them into .build/wheels). Two targets:
#
#   minimal   Python (uv-managed, so SQLite >= SQLITE_MIN_VERSION) + spectio, spectio-server, spectio-sdk
#   engines   minimal + Java 21 + Nextflow + Snakemake, so that runs on the `local` executor work in the pod
#
# Build context: dev/minikube/.build (wheels/, snakemake.lock.txt), staged by up.sh. The pins are build
# arguments, which up.sh reads from dev/versions.env; the defaults below are only for a manual build.
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c
FROM ${UV_IMAGE} AS uv

FROM debian:trixie-slim@sha256:8aa5a7bf5a1955bddbe7d74fcdd0b91ab30e74362a8b73af672b0481b35b44a0 AS minimal
ARG PYTHON_VERSION=3.13.14
ENV DEBIAN_FRONTEND=noninteractive \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PYTHONDONTWRITEBYTECODE=1
# procps: Nextflow's task wrapper calls `ps`; tini: PID 1 that reaps the engine heads' children
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates procps tini tmux git \
 && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /usr/local/bin/uv
RUN uv python install "${PYTHON_VERSION}" \
 && uv venv --python "${PYTHON_VERSION}" /opt/spectio
# The three wheels in one command: spectio's requirement on spectio-sdk and the [server] extra on
# spectio-server are met by these files, never by an index.
COPY wheels /tmp/wheels
RUN set -e; cd /tmp/wheels; \
    uv pip install --python /opt/spectio/bin/python \
      ./spectio_sdk-*.whl "spectio[server] @ $(ls /tmp/wheels/spectio-*.whl)" ./spectio_server-*.whl \
 && rm -rf /tmp/wheels \
 && ln -s /opt/spectio/bin/spectio /usr/local/bin/spectio \
 && /opt/spectio/bin/python -c "import sqlite3; print('sqlite', sqlite3.sqlite_version)"
RUN useradd --uid 10001 --create-home --home-dir /home/spectio --shell /bin/bash spectio \
 && mkdir -p /var/lib/spectio /var/lib/spectio-runs \
 && chown spectio:spectio /var/lib/spectio /var/lib/spectio-runs
USER 10001:10001
WORKDIR /home/spectio
ENV HOME=/home/spectio \
    SPECTIO_DATA_DIR=/var/lib/spectio/data \
    SPECTIO_DB_DIR=/var/lib/spectio/db \
    SPECTIO_RUNS_ROOT=/var/lib/spectio-runs \
    SPECTIO_CONFIG=/var/lib/spectio/data/spectio.toml
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["spectio", "serve", "--pane"]

FROM minimal AS engines
ARG NEXTFLOW_VERSION
ARG NEXTFLOW_SHA256
ARG SNAKEMAKE_VERSION
ARG SNAKEMAKE_EXECUTOR_SLURM_VERSION
ARG PYTHON_VERSION=3.13.14
ARG TARGETARCH
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-21-jre-headless curl \
 && rm -rf /var/lib/apt/lists/*
# Nextflow: the -dist launcher is the jar itself; checked against the sha256 of dev/versions.env
RUN curl -fsSL -o /usr/local/bin/nextflow \
      "https://github.com/nextflow-io/nextflow/releases/download/v${NEXTFLOW_VERSION}/nextflow-${NEXTFLOW_VERSION}-dist" \
 && echo "${NEXTFLOW_SHA256}  /usr/local/bin/nextflow" | sha256sum -c - \
 && chmod 0755 /usr/local/bin/nextflow
# Snakemake in its own environment. dev/snakemake.lock.txt is hash-locked for linux x86_64 only: on amd64 it
# is used as it is; on arm64 (a Mac under colima) the same top-level versions are resolved without hashes.
COPY snakemake.lock.txt /tmp/snakemake.lock.txt
RUN uv venv --python "${PYTHON_VERSION}" /opt/snakemake \
 && if [ "${TARGETARCH}" = amd64 ]; then \
      uv pip install --python /opt/snakemake/bin/python --require-hashes --no-deps -r /tmp/snakemake.lock.txt; \
    else \
      uv pip install --python /opt/snakemake/bin/python \
        "snakemake==${SNAKEMAKE_VERSION}" "snakemake-executor-plugin-slurm==${SNAKEMAKE_EXECUTOR_SLURM_VERSION}"; \
    fi \
 && ln -s /opt/snakemake/bin/snakemake /usr/local/bin/snakemake \
 && rm /tmp/snakemake.lock.txt
# `python3` for the pipelines' scripts: the uv-managed interpreter itself, not the Spectio environment
RUN ln -s "$(uv python find "${PYTHON_VERSION}")" /usr/local/bin/python3
USER 10001:10001
ENV NXF_ANSI_LOG=false
