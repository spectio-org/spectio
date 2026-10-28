# Spike: stage detection (2026-10-28, throwaway)

Question: can Spectio find the big stages of a run by itself, for nf-core pipelines (from their
subworkflows) and for a Snakemake pipeline (mosaicatcher), and how do they compare with stages a
lab declares in a `spectio.yml` overlay? Note: [`docs/research/spike-stage-detection-2026-10-28.md`](../../docs/research/spike-stage-detection-2026-10-28.md).

| Path | What |
|---|---|
| `nextflow/preview.sh` | Runs an nf-core pipeline with `-preview` (no task runs), the spike-T2 `nf-spectio` bridge loaded through `NXF_PLUGINS_DEFAULT`, and `-with-dag`; captures the bridge's events |
| `nextflow/capture_server.py` | Copy of the spike-T2 capture server (`spikes/engine-events/`, branch `spike/engine-events`) |
| `nextflow/toy/` | A toy pipeline with the nf-core shape (wrapper, pipeline workflow, nested subworkflows, a direct call, a `when: false` process), run for real |
| `nextflow/spectio-bridge.config` | The `-c` config that did **not** keep the pipeline's plugins (LOG.md §2) |
| `snakemake/snakemake_logger_plugin_spectio/` | Copy of the spike-T2 Snakemake logger plugin |
| `detector/detect_nf.py` | Nextflow detector: fully qualified process names → ordered stages |
| `detector/detect_smk.py` | Snakemake detector: `include:`d rule files → ordered stages |
| `detector/apply_overlay.py` | Applies a `spectio.yml` overlay to the same names; compares with the detected stages |
| `detector/run_all.sh` | Re-runs the Nextflow detector on every capture |
| `overlays/*.spectio.yml` | Example lab overlays: nf-core/rnaseq, sarek, methylseq, mosaicatcher |
| `out/` | Captures and detector outputs, paths replaced by `<src>`, `<run>`, `<scratch>` |
| `LOG.md` | Commands, timings, dead ends |

Pins: Nextflow 26.10.4, Snakemake 9.27.1 (`dev/versions.env`); nf-core/rnaseq 3.27.0
(`a1fcddd`), nf-core/sarek 3.11.0 (`6e9b164`), nf-core/methylseq 4.2.0 (`5aa5646`),
friendsofstrandseq/mosaicatcher-pipeline v2.5.1 (`2289f7c`, test data submodule `.tests` at `3ba5668`),
nextflow-io/nextflow v26.10.4 (`691b821`) for the source reading.

Reproduce (needs network for the nf-core plugins and the clones):

```bash
# clones under $SRC at the tags above; spike-T2 nf-spectio 0.0.1 installed in ~/.nextflow/plugins
nextflow/preview.sh $SRC/rnaseq /tmp/run/rnaseq out/rnaseq-3.27.0_star_salmon_preview_events.jsonl
detector/run_all.sh $SRC
python3 detector/detect_smk.py $SRC/mosaicatcher/workflow/Snakefile --defined out/mosaicatcher-v2.5.1_list-rules_default.txt
python3 detector/apply_overlay.py overlays/nf-core-rnaseq.spectio.yml out/rnaseq-3.27.0_star_salmon_preview_events.jsonl out/rnaseq-3.27.0_star_salmon_detected.json
```
