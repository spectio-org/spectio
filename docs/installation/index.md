---
icon: material/download
---
# Installation

!!! info "0.0.1 is built and not released yet"
    The first version, `0.0.1`, is finished on the development branch and waits for its release checks ([roadmap](../roadmap/index.md)). Nothing is published for it yet: the names on PyPI (`spectio`, `snakemake-logger-plugin-spectio`) and in the Nextflow plugin registry (`nf-spectio`) only hold empty `0.0.0` placeholders. Do not install those.

## What 0.0.1 is made of

0.0.1 is installed as Python packages, on a laptop, a machine of your own or a SLURM login node. There is no Docker Compose file and no Helm chart yet.

| Package | What it holds |
|---|---|
| `spectio` | the `spectio` command (`init`, `doctor`, `serve`, `login`, `open`), the runner, and both engine bridges |
| `spectio-server` | the API, the store and the screens. It depends on `spectio`. There is no `spectio[server]` extra: the server is its own package |
| `spectio-sdk` | the event schemas shared by the two above |
| `snakemake-logger-plugin-spectio` | the Snakemake bridge, for runs you start by hand ([details](../usage/runs-from-a-terminal.md)) |
| `nf-spectio` | the Nextflow bridge. `spectio init` unpacks it from the `spectio` wheel |

You also need Python 3.11 or later, [uv](https://docs.astral.sh/uv/), tmux 2.1 or later on the machine that runs the server, and Nextflow or Snakemake for the engine you use. Source: `requires-python` in `packages/*/pyproject.toml`; the tmux floor is the check of `spectio serve --detach`.

0.0.1 targets the EMBL cluster first. Other sites are not checked.

## Try it from a checkout

Until the release, the way to run Spectio is from a checkout of the [repository](https://github.com/spectio-org/spectio). This is the path the project's own end-to-end tests use; it is **[to be validated]** as an install route for someone who is not a developer.

1. Build the screens once. They need Node:

    ```console
    $ git clone https://github.com/spectio-org/spectio && cd spectio
    $ npm --prefix web ci --ignore-scripts
    $ npm --prefix web run build
    ```

2. Install the packages and set Spectio up on one machine, with no scheduler:

    ```console
    $ uv sync --locked
    $ mkdir -p ~/spectio-runs
    $ uv run spectio init --local
    $ uv run spectio doctor
    ```

    `spectio doctor` prints one `ok`, `warn` or `fail` line per check: SQLite, the data and runs directories, the engines, tmux, `sbatch`. A missing engine is a `fail` until you install it.

3. Start the server. It prints a single-use link; open it in a browser on the same machine ([Signing in](../usage/sign-in.md)):

    ```console
    $ uv run spectio serve
    ```

On a SLURM login node, run `spectio init` without `--local` and give it your partition and account (`--partition`, `--account`). The server then listens on a Unix socket and you reach it through an SSH tunnel ([Opening from your laptop](../usage/open-from-your-laptop.md)). That path was not run on a real cluster yet.

The script `tests/e2e/serve-local.sh` of the repository does steps 2 and 3 in a throwaway directory, for a quick look.

## Which SQLite

Spectio refuses an SQLite older than 3.51.3: older ones lack a fix of the write-ahead log (WAL) reset. The Python that uv installs brings its own SQLite. If Spectio stops with `SQLite … lacks the WAL-reset fix`, the message names the Python it came from; then:

1. upgrade uv: `uv self update`, or run the [installer](https://docs.astral.sh/uv/getting-started/installation/) again (`uv self update` works only for a uv the installer put there **[to be validated]**);
2. `uv python install 3.13`; if the refusal comes back, name the patch, `uv python install 3.13.14`, the one that worked on an EMBL login node on 2026-11-08 (whether plain `3.13` fetches a newer patch is **[to be validated]**);
3. install Spectio again with that Python, for example `uv sync --python 3.13`.

On that login node, uv 0.9.29 only offered Pythons with SQLite 3.50.4, which Spectio refuses; uv 0.13.7 with Python 3.13.14 (SQLite 3.53.1) worked. Use uv 0.13.7 or later. `spectio doctor` shows the uv on your path and warns when it is older.

## Put the runs on a file system with room

Each run's launch and work directories go under the runs directory, `~/spectio-runs` by default. On the EMBL login node that is `/home`, a shared file system that was 97% full on 2026-11-08. `spectio doctor` prints a `runs_disk` line with the free space and warns when the file system is 90% used or has less than 10 GiB free; a launch then logs the same warning and still starts.

To move it, set `SPECTIO_RUNS_ROOT`, `runs_root` in `~/.spectio/spectio.toml`, or `spectio init --runs-root`. Point it at a larger scratch or group file system that the compute nodes also see. A directory you choose must exist already, be yours, and not be writable by others.

## Later

Docker Compose, a Helm chart for Kubernetes, remote runners and signed images are planned for later versions ([roadmap](../roadmap/index.md)).
