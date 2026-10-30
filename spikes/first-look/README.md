# Spike first-look

Throwaway demo of the code merged so far (spool reader, store, projector), shown on a local page.
Not product code.

- **Part 2 (real Nextflow):** `spikes/first-look/run-local.sh` installs Nextflow 26.10.4 and the
  spike T2 plugin, starts the demo on http://127.0.0.1:8765/, and lets you launch a dummy
  pipeline from the page ("New run") or from the shell (`--cli`). Brief for an agent or a human,
  with prerequisites, expected output, cleanup and troubleshooting: [AGENT.md](AGENT.md).
- **Part 1 (synthetic spools):** `uv run python spikes/first-look/demo.py --synthetic`.

| File | Role |
|---|---|
| `run-local.sh` | one entry point: Nextflow, plugin, `uv sync`, demo; `--cli` launches from the shell |
| `demo.py` | the store, the poller (read_spool + ingest every second) and the pages |
| `launch.py` | run registration, `nextflow run` as a subprocess, the plugin event receiver |
| `nf/main.nf` | the dummy pipeline: FASTQC, TRIM, ALIGN per sample, MULTIQC; `--fail` |
| `nf-spectio/` | the prototype plugin of spike T2, copied from `spike/engine-events` |
| `make_spool.py` | part 1's synthetic spools |
| `launch-ui.js`, `shoot.js` | Playwright: launch from the form and screenshot; screenshot only |

Findings, what is faked and all commands: `docs/research/2026-10-30-first-look-spike.md`.
