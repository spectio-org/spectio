---
icon: material/download
---
# Installation

!!! info "Nothing to install yet"
    Spectio is in its design phase. The first release, `0.0.1`, will be a basic version, installed as the Python package. See [what ships in which version](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version) and the [roadmap](../roadmap/index.md).

There will be three ways to run Spectio, from the smallest to the largest. All of them run the same code.

<div class="grid cards" markdown>

-   :material-language-python:{ .lg } **Python package**

    ---

    `pip install spectio` on a laptop or a login node. It has the CLI and the runner; add the server with `spectio[server]`. Data stays in SQLite. On an HPC login node, the server needs a node-local, non-purged data directory ([details](../specs/architecture-plugins-and-packaging.md#73-python-bundle)).

-   :material-docker:{ .lg } **Docker Compose**

    ---

    For a lab server: the server, a Postgres database and object storage, with optional profiles for Depictio and a test identity provider.

-   :simple-kubernetes:{ .lg } **Kubernetes**

    ---

    For an institute: a Helm chart, with runners in the cluster or on the HPC login nodes.

</div>

**With uv, use uv 0.13.7 or later.** Spectio refuses an SQLite without the WAL-reset fix ([api §7](../specs/api-and-data-model.md#7-database-schema)), and the Python a uv installs brings its own SQLite. On an EMBL login node, uv 0.9.29 only offered Pythons with SQLite 3.50.4, which Spectio refuses; uv 0.13.7 with Python 3.13.14 (SQLite 3.53.1) works ([login-node audit](../research/2026-11-08-embl-login-node-audit.md#8-spectio-serve) §8). If Spectio stops with `SQLite … lacks the WAL-reset fix`, the message names the Python it came from; then:

1. upgrade uv: `uv self update`, or the [installer](https://docs.astral.sh/uv/getting-started/installation/) again (`uv self update` works only for a uv the installer put there **[to be validated]**);
2. `uv python install 3.13`; if you already have a 3.13 and the refusal comes back, name the patch, `uv python install 3.13.14`, the one that worked in the audit (whether the plain `3.13` fetches a newer patch is **[to be validated]**);
3. reinstall Spectio with that Python, for example `uv tool install --reinstall --python 3.13 'spectio[server]'`, or recreate its virtual environment with `--python 3.13` (these uv flags are **[to be validated]** against [uv's documentation](https://docs.astral.sh/uv/)).

`spectio doctor` shows the uv on your path and warns when it is older than 0.13.7.

**Put the runs directory on a file system with room.** Each run's launch and work directories go under the runs directory, `~/spectio-runs` by default. On an EMBL login node that is `/home`, an NFS file system that was 97% full on 2026-11-08 ([login-node audit](../research/2026-11-08-embl-login-node-audit.md#6-shared-home) §6). `spectio doctor` prints a `runs_disk` line with the free space there, and warns when that file system is 90% used or has less than 10 GiB free; a launch then logs the same warning in the server's output, and still starts. To move it, point `SPECTIO_RUNS_ROOT`, `runs_root` in `~/.spectio/spectio.toml`, or `spectio init --runs-root` at a larger scratch or group file system that the compute nodes also see. A directory you choose must exist already, be yours, and not be writable by others.

**The runner on your cluster** is a small program on the login node or in the cluster. It only makes outgoing HTTPS calls to the server, so no port needs to be opened on the HPC side.

**Checking what you install.** Every published image and chart will carry a signature, an SBOM and a provenance attestation that `gh attestation verify` checks; see [versioning and releases](../specs/dev-environment-and-testing.md#12-versioning-and-releases). *(decided — Thomas, 2026-10-27, inbox #26)*

Design details: [packaging](../specs/architecture-plugins-and-packaging.md#7-packaging-and-the-three-deployments) and [schedulers](../specs/schedulers-and-monitoring.md#6-running-the-runner-on-hpc).
