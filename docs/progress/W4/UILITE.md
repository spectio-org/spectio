---
step: UILITE
wave: W4
status: running
pr: null
review: changes
review_score: 7/14
review_ref: "doc-reviewer 2026-10-28, changes 7/14 on 8bba74e; items 1-13 and 15 applied in the second commit, item 14 kept"
---
# UILITE · The 0.0.1 lite boards: review, stages and Thomas's design requests

!!! info "Running 2026-10-28 · branch `autopilot/ui-lite-review` · UX-292 to UX-304, then the re-check UX-305 to UX-314, all applied · Thomas: both stages and processes in 0.0.1, four screens with Home, logos, collapsible sections, the Spectio logo as the favicon only · doc review changes 7/14 on `8bba74e`, applied; re-review pending"

![UILITE figure, before and after. Before, at 1abd5dd: the lite run detail of a running nf-core/rnaseq run, header "stage 3 of 4", four stage cards named by hand (Preprocessing, Alignment & QC, Quantification, Reporting) that no endpoint served, since the API had /processes only, above a separate processes table with a Stage column of labels, 6 of 14 processes shown. After: header "3 of 8 stages done · 4 running · 524 / 803 tasks", the eight stages the stage-detection spike found for nf-core/rnaseq 3.27.0, in order, each with a Done, Running or Pending word and icon, a Detected badge, a bar and "n of m", the fourth, Bam markduplicates picard, open to its processes; notes: a process in no stage goes under "Not in a stage", with no stage the run detail shows the flat list, the state words map to run_stages.state (Pending not_started, Running running, Done completed, Failed failed, Not run skipped), processes are keyed by task.process and shown by their last segment, and /stages is empty until the detector task of step APPLY6](../../assets/diagrams/uilite_stages_light.png#only-light)
![UILITE figure, before and after. Before, at 1abd5dd: the lite run detail of a running nf-core/rnaseq run, header "stage 3 of 4", four stage cards named by hand (Preprocessing, Alignment & QC, Quantification, Reporting) that no endpoint served, since the API had /processes only, above a separate processes table with a Stage column of labels, 6 of 14 processes shown. After: header "3 of 8 stages done · 4 running · 524 / 803 tasks", the eight stages the stage-detection spike found for nf-core/rnaseq 3.27.0, in order, each with a Done, Running or Pending word and icon, a Detected badge, a bar and "n of m", the fourth, Bam markduplicates picard, open to its processes; notes: a process in no stage goes under "Not in a stage", with no stage the run detail shows the flat list, the state words map to run_stages.state (Pending not_started, Running running, Done completed, Failed failed, Not run skipped), processes are keyed by task.process and shown by their last segment, and /stages is empty until the detector task of step APPLY6](../../assets/diagrams/uilite_stages_dark.png#only-dark)

*Left: `LiteRunDetail` on `autopilot/integration` at `1abd5dd`. Right: this branch. Sources are named under the figure. The stages are the stage-detection spike's output for nf-core/rnaseq 3.27.0 (`tests/pipelines/real/stages/expected/` on branch `autopilot/apply-stages`); the counts are fixture data.*

This step is outside [`pipeline.yaml`](../../playbooks/pipeline.yaml): a `ux-reviewer` pass on the 0.0.1 lite boards, applied with Thomas's answers of 2026-10-28 ([review record](../../reviews/code/UI-LITE.md), [decision log](../../decisions/log.md#2026-10-28-001-has-four-screens-home-kept)).

## What changed

**Part 1, commit `8bba74e`: UX-292 to UX-304.** The boards of page **0.0.1 lite** got the four screens (Home kept), stages with their processes, runs started from a terminal, the head facts of P1 Task 20, live refresh over SSE, the missing states and the phone boards. P1 Task 18 gained the read endpoints the boards need. Details per finding: [review record](../../reviews/code/UI-LITE.md).

**Part 2, the second commit: the doc review, the re-check and Thomas's design requests.**

- **[ui-spec §4.4](../../specs/ui-spec.md#44-run-detail), a dated note, the one owner of the 0.0.1 stage presentation.** What the run detail shows, with or without stages; the header "n of m stages done · k running" (UX-306); one state-word rule from the task counts, with Pending including Submitted (UX-305); each word mapped to an api §7 `run_stages.state`, with Stopped → `failed` left to the stage-detection task; processes keyed by `task.process` **[to be validated]** and shown by their last segment (UX-307); `/stages` empty until step APPLY6.
- **[ui-spec §2](../../specs/ui-spec.md#2-main-navigation), a dated note.** The 0.0.1 top bar starts with the breadcrumbs; the Spectio logo is the favicon only.
- **[P1](../../plans/P1-walking-skeleton.md).**
    - Assumption 6 is one clause and a link to the §4.4 note. It names the spike and its branch, says `/stages` returns `{items: []}` until APPLY6, and that the same task reads the declared stages from `spectio.yml` or a lab overlay at launch.
    - Task 18:
        - `/stages` is a subset of `run_stages`: `{id, position, name, source, state, task_counts}`;
        - `/processes` items carry `stage_id`, and `process` is the fully qualified name;
        - `/version` gains `executor` (UX-311);
        - `GET /runs` gains `sort=-ended_at` (UX-312);
        - new tests `test_stages_ordered`, `test_stages_empty`, `test_stages_source` and `test_runs_sort_ended`;
        - "Snakemake declares none" is marked **[to be validated]**.
    - Task 20: the run-detail bullet is split in five; the smoke covers home at `/` and both the stage view and the flat list; `stateWord.ts` implements the §4.4 rule.
    - Task 24 and Done when: `spectio-open` opens home.
- **One clause and a link** to the §4.4 note in [mvp-0.0.1 §2](../../specs/mvp-0.0.1.md), [dev-env §15.1](../../specs/dev-environment-and-testing.md#151-capabilities-by-version), the [api §5 note](../../specs/api-and-data-model.md#5-endpoint-catalogue-api-v1) (which also names the `/stages` subset and `sort=-ended_at`; the catalogue gains the `ended_at` sort key), the [decision log](../../decisions/log.md#2026-10-28-001-has-four-screens-home-kept) and [`design/README.md`](https://github.com/weber8thomas/spectio/blob/main/design/README.md#001-lite-boards).
- **[mvp-0.0.1 §2](../../specs/mvp-0.0.1.md)** embeds the four lite screenshots.
- **[Decision log](../../decisions/log.md#2026-10-28-001-has-four-screens-home-kept).** Thomas's design request quoted; the Changed line extended.
- **[`next-phase.md`](../../playbooks/next-phase.md)**: a dated note on the P1 prompt's "three screens".
- **Boards.**
    - The engine and pipeline logos (Nextflow, Snakemake, nf-core).
    - A light icon on each section, each section collapsible, in the run detail, home and launch.
    - No logo in the top bar.
    - The examples rebuilt on the stage-detection spike's real output (`tests/pipelines/real/stages/expected/` on branch `autopilot/apply-stages`): nf-core/rnaseq 3.27.0 with STAR and Salmon, eight stages, 63 processes seen, 803 known tasks for 20 samples; mosaicatcher-pipeline v2.5.1, eight stages, 347 jobs for 96 cells. Stage names and membership verbatim; counts are fixture data, the same on every board.
    - The state rule, and fully qualified names as accessible names.
    - Phone wrapping, padding and a "Now" line.
    - Served facts only.
    - Lists newest first.
    - Log times that match the run.
    - Legend sections for the stage words and the stage sources.

## Why

Thomas, 2026-10-28, wants both the stages and the processes in 0.0.1 ("les 2 dans 0.0.1"), a home screen, and asked for the logos, light icons, collapsible sections and the logo as favicon only. The doc review of `8bba74e` found the stage presentation described in seven places, state words with no mapping to the API, a `/stages` shape that did not match api §7, and no Progress page. The re-check found state words that contradicted their counts, colliding short process names, and facts no endpoint serves.

## Evidence

- **Docs gate**, `python3 tools/docs/check.py` on this branch:

    ```text
    mermaid: 5 blocks checked
    diagrams: 28 scripts re-run, 56 SVGs compared
    media: 138 outputs in the manifest
    progress: 41 pages checked
    docs gate: 0 failure(s)
    ```

- **Strict build:** `uvx --with mkdocs-material mkdocs build --strict` exits 0. The anchors linked from the plan and the specs exist in the built pages: `44-run-detail` and `2-main-navigation` (ui-spec), `5-endpoint-catalogue-api-v1` (api), `2026-10-28-001-has-four-screens-home-kept` (decision log).
- **Frontmatter:** `python3 tools/claude/check_frontmatter.py` reports 0 problems.
- **Boards:** `LiteRunDetail`, `LiteRunDetailSnakemake`, `LiteRunTasks`, `LiteHome`, `LiteLaunch`, `LiteCancelDialog` (1440 × 1180) and `MLiteRunDetail`, `MLiteCancelSheet` (390 × 844) rendered with `node tools/canvas/render.js` and looked at; the run detail also at 1440 × 1700, to read its last stages and caption.
- **One set of numbers:** the stage rows, the header, the chips, the Tasks filters, home and the runs list all read 524 succeeded, 64 running, 215 pending, 7 retried, 803 known tasks; `grep -rn "524 / 824\|3 of 5 stages" design docs` prints only this line.
- **No stale wording:** `grep -rn "spike, pending" docs design` prints only this line.
- **Before:** `git show 1abd5dd:design/ui-canvas/LiteRunDetail.dc.html`. **After:** `git diff 1abd5dd -- docs design tools`.

## Figures and media

- `uilite_stages` (above), new: [`tools/diagrams/uilite_stages.py`](https://github.com/weber8thomas/spectio/blob/main/tools/diagrams/uilite_stages.py), entry `uilite-stages` in `docs/assets/media.yaml`. Rendered light and dark; both PNGs opened and checked for overlaps.
- Screenshots `lite-run-detail`, `lite-launch`, `lite-runs` and `lite-run-detail-phone`, regenerated with `python3 tools/media/shots.py run --shot <id> --theme light` (entry `ui-shots`); shown in [mvp-0.0.1 §2](../../specs/mvp-0.0.1.md).
- `tools/canvas/render.js` also looks for logos in `docs/assets/logos/`.

## Findings and open questions

- **Spike output used, not yet merged:** the boards follow the detector files on `autopilot/apply-stages` (2a245bf); if the stage-detection task changes a stage name or a merge, the boards follow it. **[to be validated]**: `task.process` as the process key in `/processes`; whether Snakemake declares a pipeline version.
- **Open:** Stopped → `failed` in the mapping, because api §7 has no cancelled stage state; to settle with the stage-detection task.
- **Doc review item 14** stays as it is, as the coordinator decided.
- **Coordination:** the spike's branch `autopilot/apply-stages` owns ui-spec §5.1 "Where stages come from", checking-scenarios §12, and the stages rows of dev-env §15.1 and mvp-0.0.1 §2; this branch edited only existing lines there.
