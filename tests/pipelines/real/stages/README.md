# Stage fixtures: example pipelines for declared and detected stages

Golden inputs and outputs for the stage detection of [ui-spec §5.1.1](../../../../docs/specs/ui-spec.md) and P1 Task 27. They come from the [stage-detection spike](../../../../docs/research/spike-stage-detection-2026-10-28.md) (branch `spike/stage-detection`, `spikes/stage-detection/out/` and `overlays/`), captured on 2026-10-28 with Nextflow 26.10.4 (`-preview`) and Snakemake 9.27.1. `packages/spectio-server/tests/api/test_stages.py` reads them (Task 27).

| Path | What | Pipeline and pin |
|---|---|---|
| `processes/rnaseq-3.27.0_star_salmon.txt` | fully qualified process names in `onProcessCreate` order, one per line (67) | nf-core/rnaseq 3.27.0 `a1fcddd`, `-profile test` |
| `processes/rnaseq-3.27.0_hisat2.txt` | the same, `--aligner hisat2` (62) | nf-core/rnaseq 3.27.0 `a1fcddd` |
| `processes/sarek-3.11.0.txt` | the same (48) | nf-core/sarek 3.11.0 `6e9b164`, `-profile test` |
| `processes/methylseq-4.2.0_bismark.txt`, `_bwameth.txt` | the same (13 and 15) | nf-core/methylseq 4.2.0 `5aa5646`, `--aligner bismark` / `bwameth` |
| `events/rnaseq-3.27.0_star_salmon_preview_events.jsonl` | the events the spike-T2 `nf-spectio` sent for that preview, as received by the capture server (70 records: `onFlowCreate`, 67 `onProcessCreate`, `onFlowBegin`, `onFlowComplete`; paths replaced by `<src>`, `<run>`), for the freeze and replay tests of Task 27; the other process lists are turned into events by the test | nf-core/rnaseq 3.27.0 `a1fcddd` |
| `rules/mosaicatcher-v2.5.1_list-rules.txt` | `snakemake --list-rules` with the default configuration (101 rules), names only: Snakemake prints `name (docstring)`, stripped here | friendsofstrandseq/mosaicatcher-pipeline v2.5.1 `2289f7c` |
| `rules/mosaicatcher-v2.5.1_rule-files.json` | its rule files in include order, with their rules and checkpoints (27 files), so the grouping can be tested without the source | the same |
| `expected/*_detected.json` | the spike detectors' output, capped at 8: `id`, `name`, `source`, `match` (the names), and per engine `description` and `attached_processes`, or `files` and `checkpoints` | as above; mosaicatcher with `--defined` from `list-rules` |
| `overlays/*.spectio.yml` | four example lab overlays, `stages[]` only, display only, in the [checking-scenarios §12.1](../../../../docs/specs/checking-scenarios.md) shape | nf-core/rnaseq, sarek, methylseq; mosaicatcher-pipeline |

The expected files are the spike's output, not a specification: Task 27 may change a stage name or a merge, and then updates the file in the same commit with the reason. The overlays match every name of their fixture, with no overlap (spike `out/overlays_vs_detected.txt`).

Changed by Task 27 (2026-10-31): in both rnaseq files, the description of "Bam qc rnaseq" was `"|"`, the YAML block marker of `description: |` that the spike's line parser kept; the server reads `meta.yml` with `yaml.safe_load`, and the fixtures hold no source to read the text from, so it is now `null`.
