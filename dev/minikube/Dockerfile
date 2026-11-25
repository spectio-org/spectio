# syntax=docker/dockerfile:1
# A Spectio image for local development, modelled on the one of docs/specs/architecture-plugins-and-packaging.md
# §7.4 but built from the wheels of the checkout, not from a published wheel (dev only: tagged spectio:dev, never
# pushed). dev/minikube/up.sh builds the wheels into .build/wheels and stages the build context. Two targets:
#
#   minimal   Python (uv-managed, so SQLite >= SQLITE_MIN_VERSION) + spectio, spectio-server, spectio-sdk
#   engines   minimal + Java 21 + Nextflow + Snakemake, so that runs on the `local` executor work in the pod
#
# Build context: dev/minikube/.build (wheels/, requirements.txt, snakemake.lock*.txt). Every Python package is
# installed with --require-hashes: the third-party dependencies of the wheels from requirements.txt (a `uv export`
# of uv.lock, universal), Snakemake from the lock file of the image's architecture; the wheels themselves with
# --no-deps. uv, curl and the download of Nextflow stay in the build stage: the final image has none of them.
# The pins are build arguments, which up.sh reads from dev/versions.env; the defaults are only for a manual build.
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c
FROM ${UV_IMAGE} AS uv

FROM debian:trixie-slim@sha256:8aa5a7bf5a1955bddbe7d74fcdd0b91ab30e74362a8b73af672b0481b35b44a0 AS builder
ARG PYTHON_VERSION=3.13.14
ARG NEXTFLOW_VERSION
ARG NEXTFLOW_SHA256
ARG SNAKEMAKE_VERSION
ARG SNAKEMAKE_EXECUTOR_SLURM_VERSION
ARG TARGETARCH
ENV DEBIAN_FRONTEND=noninteractive \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /usr/local/bin/uv
RUN uv python install "${PYTHON_VERSION}" \
 && ln -s "$(uv python find "${PYTHON_VERSION}")" /opt/python/python3
# Spectio: the hashed third-party dependencies first, then the three wheels without dependencies
COPY requirements.txt /tmp/requirements.txt
COPY wheels /tmp/wheels
RUN uv venv --python "${PYTHON_VERSION}" /opt/spectio \
 && uv pip install --python /opt/spectio/bin/python --require-hashes --no-deps -r /tmp/requirements.txt \
 && uv pip install --python /opt/spectio/bin/python --no-deps /tmp/wheels/spectio_sdk-*.whl \
      /tmp/wheels/spectio-*.whl /tmp/wheels/spectio_server-*.whl
# Snakemake in its own environment, from the lock file of this architecture
COPY snakemake.lock.txt snakemake.lock.arm64.txt /tmp/
RUN case "${TARGETARCH}" in \
      amd64) lock=/tmp/snakemake.lock.txt ;; \
      arm64) lock=/tmp/snakemake.lock.arm64.txt ;; \
      *) echo "no Snakemake lock file for TARGETARCH='${TARGETARCH}' (needs BuildKit)" >&2; exit 1 ;; \
    esac \
 && uv venv --python "${PYTHON_VERSION}" /opt/snakemake \
 && uv pip install --python /opt/snakemake/bin/python --require-hashes --no-deps -r "$lock"
# Nextflow: the -dist launcher is the jar itself; checked against the sha256 of dev/versions.env
RUN mkdir /opt/nextflow \
 && curl -fsSL -o /opt/nextflow/nextflow \
      "https://github.com/nextflow-io/nextflow/releases/download/v${NEXTFLOW_VERSION}/nextflow-${NEXTFLOW_VERSION}-dist" \
 && echo "${NEXTFLOW_SHA256}  /opt/nextflow/nextflow" | sha256sum -c - \
 && chmod 0755 /opt/nextflow/nextflow

FROM debian:trixie-slim@sha256:8aa5a7bf5a1955bddbe7d74fcdd0b91ab30e74362a8b73af672b0481b35b44a0 AS minimal
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1
# procps: Nextflow's task wrapper calls `ps`; tini: PID 1 that reaps the engine heads' children (the Deployment
# runs it explicitly: a `command:` replaces the ENTRYPOINT); git: Nextflow and Snakemake fetch workflows with it
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates procps tini tmux git \
 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/python /opt/python
COPY --from=builder /opt/spectio /opt/spectio
RUN ln -s /opt/spectio/bin/spectio /usr/local/bin/spectio \
 && /opt/spectio/bin/python -c "import sqlite3; print('sqlite', sqlite3.sqlite_version)" \
 && useradd --uid 10001 --create-home --home-dir /home/spectio --shell /bin/bash spectio \
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
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-21-jre-headless \
 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/nextflow/nextflow /usr/local/bin/nextflow
COPY --from=builder /opt/snakemake /opt/snakemake
# `python3` for the pipelines' scripts: the uv-managed interpreter itself, not the Spectio environment
RUN ln -s /opt/snakemake/bin/snakemake /usr/local/bin/snakemake \
 && ln -s /opt/python/python3 /usr/local/bin/python3
USER 10001:10001
ENV NXF_ANSI_LOG=false
