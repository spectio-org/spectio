# Spike first-look: run Spectio's merged code against a real local Nextflow

A brief for an agent or a human. It starts a local demo server, then runs a dummy Nextflow pipeline
(4 processes, a few samples, a few seconds each), and you watch the run appear and move in a
browser. You can launch the pipeline from the page ("New run") or from the shell (`--cli`).
It is a throwaway spike on branch `spike/first-look`, not product code. Findings are in
`docs/research/2026-10-30-first-look-spike.md`.

## Prerequisites

| Need | Why | Check |
|---|---|---|
| Linux or macOS, bash | the script | `bash --version` |
| Java 17 or newer (21 is the project pin) | Nextflow 26.10 runs on the JVM | `java -version` |
| uv | installs the workspace (`spectio`, `spectio-server`, `spectio-sdk`) | `uv --version` |
| curl and network access to github.com | first start only: downloads the Nextflow 26.10.4 `-dist` launcher (49 MB), checked against `dev/versions.env` | `curl -sI https://github.com` |
| port 8765 free on 127.0.0.1 | the demo page and the plugin's event endpoint share it | `--port N` to change |
| Node and Playwright (optional) | only for the screenshot script `launch-ui.js` | `node -e "require('playwright')"` |

No Docker, conda or container: the dummy pipeline uses the local executor and `sleep`/`echo`/`cat`.

## Commands

From the repository root, on branch `spike/first-look`:

```bash
# 1. Start the demo (installs Nextflow and the plugin on first run), then open the URL it prints.
spikes/first-look/run-local.sh                 # http://127.0.0.1:8765/ ; Ctrl-C stops it
#    In the page: "New run" -> samples 3 -> Launch run. Tick "Fail a task" for a failed run.

# 2. Or launch from the shell: same demo, plus one run started here (its Nextflow output shows here).
spikes/first-look/run-local.sh --cli --samples 3
spikes/first-look/run-local.sh --cli --samples 2 --fail

# Options: --port N, --synthetic (also show part 1's three synthetic runs), NF_VERSION=25.10.9.

# 3. Optional: drive the form with Playwright and take screenshots (with the demo running).
node spikes/first-look/launch-ui.js 8765 spikes/first-look/shots
```

## What you should see

1. The script prints `==> Nextflow version 26.10.4 build 14435`, `==> uv sync`, then
   `==> demo on http://127.0.0.1:8765/`.
2. The page shows **Runs** with a **New run** form (pipeline `first-look/dummy 0.1.0`, run name,
   samples 1–12, "Fail a task"). Submitting opens the run's page.
3. The run is `Queued`, then `Running` within 2–3 seconds; the page reloads every 3 s. You see
   the processes (FASTQC, TRIM, ALIGN, MULTIQC) fill in, the tasks and attempts, the last 12
   events and the last lines of `nextflow.out`. Expect running attempts to show
   `exit 2147483647 (none yet)`: that is a finding about the projector, not a demo bug.
4. With 3 samples it ends `Succeeded` in about 15 s: 10 / 10 tasks, head state `succeeded · 0`.
5. With "Fail a task": `ALIGN` of the last sample fails, is retried once, fails again; the run
   ends `Failed` with failure `tool_error · ALIGN (S0N) attempt 2`, MULTIQC `aborted`.
6. With `--cli`, the shell prints the run page URL and the launch directory, then Nextflow's own
   output; the run shows origin `cli-observed` and no head pid (nothing watches the process).

Reference screenshots: `spikes/first-look/shots/launch-form.png`, `live-run.png`, `run-done.png`,
`run-failed.png`, `runs-local.png`.

## Stop and clean up

- Ctrl-C in the terminal stops the demo; it also stops the Nextflow runs it started. With `--cli`,
  Ctrl-C stops Nextflow if it is still running, then the demo.
- Everything lives under `$SPECTIO_FIRST_LOOK_HOME` (default `~/.cache/spectio-first-look`):
  `nextflow-26.10.4`, `nxf-home/` (with `plugins/nf-spectio-0.0.1/`) and `data/<timestamp>/`
  (one per start: the SQLite store in `db/`, one launch directory per run in `runs/`).
  `~/.nextflow` is not touched. Clean up with `rm -rf ~/.cache/spectio-first-look`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Java 11 found, Nextflow 26.10.4 needs 17+` | install Java 17+ (Temurin 21) and put it first on `PATH`, or set `JAVA_HOME` |
| `port 8765 is in use` | another demo is running (`pkill -f first-look/demo.py`) or pass `--port 8766` |
| download fails or `checksum mismatch` | no route to github.com, or a proxy rewrote the file; download `nextflow-26.10.4-dist` by hand into `~/.cache/spectio-first-look/nextflow-26.10.4` (chmod +x), or try `NF_VERSION=25.10.9` |
| run stays `Queued`, then `Failed · engine_fault` | Nextflow exited before sending any event: read the "Head output" card or `data/<ts>/runs/<run>/nextflow.out` |
| `ERROR ~ Plugin with id nf-spectio not found in any repository` (in "Head output") | the plugin was not built into `$NXF_HOME/plugins`: `rm -rf ~/.cache/spectio-first-look/nxf-home/plugins/nf-spectio-0.0.1` and start again; the build output is shown by `spikes/first-look/nf-spectio/build.sh <nextflow> <nxf-home>/plugins` |
| run never moves, `nextflow.out` shows `nf-spectio: post failed` | the plugin cannot reach `http://127.0.0.1:<port>/spectio/events/…`: check that the demo is up, and that a JVM proxy setting (`-Dhttp.proxyHost` in `JAVA_TOOL_OPTIONS`, say) lists `127.0.0.1` in `http.nonProxyHosts` |
| `403 cross-origin launch refused` | the form was posted from another origin (or a tool without an `Origin` header); open the page at `http://127.0.0.1:<port>/` or `http://localhost:<port>/` |
| `Picked up JAVA_TOOL_OPTIONS` in the output | harmless: your environment sets Java options |

## What is real and what is not

Real, unchanged:

- **Nextflow 26.10.4**, a real `nextflow run` with the local executor;
- **the prototype plugin `nf-spectio` 0.0.1 from spike T2** (branch `spike/engine-events`,
  copied to `spikes/first-look/nf-spectio/`), loaded with `-plugins nf-spectio@0.0.1`;
- the event mapping of `tests/fixtures/engine-events/convert_t2.py` (imported), the spool format
  of api §14.1, and the spool directories at mode 0700;
- `spectio.runner.spool.read_spool`, the envelope and allow-lists of `spectio_sdk.events`;
- the projector (`ingest`, `load_cursor`, `apply_head_report`, the Nextflow mapping) and the
  store (`open_db`, Alembic migrations, `Writer`, SQLite).

Not real (stand-ins written for this spike):

- **the server**: a stdlib `http.server` on 127.0.0.1 (`demo.py`), not `spectio serve`; none of
  the authentication, tokens, cookies, host allow-list or security of P1 Tasks 11–16. It checks
  `Host` and `Origin` on the form and uses an unguessable per-launch event URL, nothing more;
- **the launch API** (Task 17): `launch.py` inserts the project, run and launch rows itself;
- **the head launcher**: a plain `subprocess.Popen` with `apply_head_report` on start and exit;
  no head script, no tmux, no SLURM, no Kubernetes;
- **the event bridge**: the prototype plugin POSTs to the demo, which writes the spool lines;
  the Task 6 `nf-spectio` (which writes the spool itself) does not exist yet;
- **the UI**: two server-rendered pages loosely after the Lite boards, no product frontend, no
  logs, parameters, stages, cancel or resume.
