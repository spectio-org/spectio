---
step: APPLY8
wave: W4
status: running
pr: null
review: approve
review_score: 11/14
review_ref: "doc-reviewer 2026-10-29, approve 11/14 on a150447; required changes applied with the spec-reviewer's SR-421 to SR-428 in the third commit; re-review pending"
---
# APPLY8 · `nf-spectio` enabled with `NXF_PLUGINS_DEFAULT`

!!! info "Running 2026-10-29 · branch `autopilot/apply-inbox-69` · Thomas decided inbox #69: the bridge is added by an environment variable set per run, never by `-plugins` or a config file · fact-check FC-318 to FC-321 · spec review SR-421 to SR-428"

![Three ways to add nf-spectio to a pipeline that pins nf-schema@2.7.2. 1: nextflow run with -plugins nf-spectio replaces the pipeline's list; nf-schema falls to the newest release, so the run fails on 26.10.4 and drifts on 25.10.9. 2: a plugins block in ~/.nextflow/config is replaced by the pipeline's list; only nf-schema@2.7.2 loads, no bridge, no warning. 3: NXF_PLUGINS_DEFAULT=nf-spectio before nextflow run adds the bridge; nf-schema@2.7.2, nf-spectio and, with -with-tower, nf-tower all load. Below: the variable is set per run, by the head script for launched runs, as a one-shot prefix for terminal runs, or as a Seqera Platform Head job variable; the runner's copy in $NXF_HOME/plugins starts with no registry, online or offline; the undocumented merge is checked weekly by nextflow-edge.yml](../../assets/diagrams/nextflow-attach_light.png#only-light)
![Three ways to add nf-spectio to a pipeline that pins nf-schema@2.7.2. 1: nextflow run with -plugins nf-spectio replaces the pipeline's list; nf-schema falls to the newest release, so the run fails on 26.10.4 and drifts on 25.10.9. 2: a plugins block in ~/.nextflow/config is replaced by the pipeline's list; only nf-schema@2.7.2 loads, no bridge, no warning. 3: NXF_PLUGINS_DEFAULT=nf-spectio before nextflow run adds the bridge; nf-schema@2.7.2, nf-spectio and, with -with-tower, nf-tower all load. Below: the variable is set per run, by the head script for launched runs, as a one-shot prefix for terminal runs, or as a Seqera Platform Head job variable; the runner's copy in $NXF_HOME/plugins starts with no registry, online or offline; the undocumented merge is checked weekly by nextflow-edge.yml](../../assets/diagrams/nextflow-attach_dark.png#only-dark)

*Before: `autopilot/integration` at `925ddb0`, where the specs launched Nextflow with `-plugins nf-spectio@<ver>` and told terminal users to add a `plugins` block to `~/.nextflow/config` (inbox #69 open).*

This step is outside [`pipeline.yaml`](../../playbooks/pipeline.yaml). Thomas, 2026-10-29, asked for "la solution la plus simple pour la communauté Nextflow de manière générale, sans que cela affecte leur système, si possible, et sans que cela les empêche d'utiliser Seqera Platform" (the simplest solution for the Nextflow community, without affecting their setup if possible, and without stopping them from using Seqera Platform). After the [attach verification](../../reviews/verification-2026-10-29-nextflow-attach.md), he answered: "Ok pour ta recommandation pour la question 2".

## What changed

Each item: before, then after, then where it now lives.

- **The #69 decision.** Before: `-plugins nf-spectio@<ver>` for launched runs, `-plugins` or `~/.nextflow/config` for terminal runs. After: `NXF_PLUGINS_DEFAULT=nf-spectio@<ver>` set per run, never `-plugins` or a `plugins` block. [Architecture §13.8](../../specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal) (Enabling it), §7.3 (0.0.1 prerequisites); [inbox #69](../../reviews/inbox.md#69-nf-spectio-is-enabled-in-a-way-that-breaks-nf-core-runs-or-drops-the-bridge); [decision log](../../decisions/log.md#2026-10-29-nf-spectio-is-enabled-with-nxf_plugins_default-set-per-run).
- **FC-318** (the list drops less than #69 said). Before: the head script would append `nf-amazon`, `nf-google` or `nf-azure` for object-store work directories. After: only `nf-k8s`, on 25.10.x with `k8s`; `nf-tower`, `nf-wave` and `nf-cloudcache` are kept, so Seqera Platform is unaffected. Architecture §13.8; [P1](../../plans/P1-walking-skeleton.md) Task 9.
- **FC-319** (the code's merge contradicts the Nextflow docs). Before: "an undocumented interface". After: a named Risk item; [dev-env §11](../../specs/dev-environment-and-testing.md) `nextflow-edge.yml` asserts each week that a declared plugin and the default one both resolve; an upstream issue drafted in the verification, not filed.
- **FC-320** (a config profile cannot enable the bridge). Before: ui-spec §6 offered a `spectio` config profile, cli §2 had `engine nextflow config --install`. After: [ui-spec §6](../../specs/ui-spec.md) names the one-shot prefix; [cli §2](../../specs/cli-and-shared-libraries.md) has `engine nextflow env [--install|--uninstall]`.
- **FC-321** (weblog dates). Before: "deprecated in 26.10". After: deprecated in 25.04, removed in 26.10, not used by Spectio. [Synthesis §2 and §10](../../specs/synthesis.md).
- **No registry for 0.0.1.** Before: the first release waited for the registry name. After: a pinned copy in `$NXF_PLUGINS_DIR` starts with no registry contact; architecture §13.8 (Published), [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts).

### Spec review (SR-421 to SR-428)

- **SR-421.** [Schedulers §4](../../specs/schedulers-and-monitoring.md): on 25.10 the head script adds `nf-k8s@<version>` to `NXF_PLUGINS_DEFAULT` instead of a `plugins { id 'nf-k8s@…' }` block; the offline pre-install sentence stays.
- **SR-422.** Architecture §13.8 (The plugin copy) and cli §2: `spectio init` and `spectio engine nextflow env` unpack the wheel's jar into `$NXF_PLUGINS_DIR/nf-spectio-<ver>/`, idempotent, before printing or installing the line; dev-env §15.3 names `spectio init` for the guide; P1 Task 9 `test_init_unpacks_nf_spectio`. What a run does when the directory is missing is **[to be validated]**.
- **SR-423.** The profile export is opt-in: `spectio login` prints the one-shot line and offers the export, default no; `engine nextflow env --install` writes one marked block to `~/.bashrc` (bash) or `~/.zshrc` (zsh), `--uninstall` removes it. ui-spec §6 links §13.8 instead of restating it.
- **SR-424.** Dev-env §15.3 (Runs started from a terminal): the note is now "Revised 2026-10-29", and the registry and PyPI are needed only once the guide installs the published bridges.
- **SR-425.** The 0.0.1 cluster figure `mvp001_cluster`: the head's tmux pane shows `NXF_PLUGINS_DEFAULT=nf-spectio@<ver>` then `nextflow run ...`; re-rendered, both PNGs opened.
- **SR-426.** The `spectio doctor` check is defined once, in §13.8: warn on `false`, a list without `nf-spectio`, another version, a `plugins` block naming `nf-spectio` in `$NXF_HOME/config`, or `k8s` on 25.10.x; fail when the plugin directory is missing. Architecture §7.3 Operator commands lists it; P1 Task 8's test matches.
- **SR-427.** §13.8: never a `plugins` block in any config file, including Spectio's own `-c .spectio/spectio.config`; P1 `test_head_script_nextflow_args` asserts that file has none.
- **SR-428.** The decision-log entry has a **Reverses:** line: the `-plugins` part of inbox #35 (architecture §7.3) and the Enabling-it mechanism of the 2026-10-28 terminal-runs entry.
- **The three open questions** (opt-in export, Spectio deposits the jar, doctor fails loudly) are recorded in inbox #69 as *assumed from the decision — pending Thomas*.

## Why

Most nf-core pipelines pin their own plugins, and Nextflow keeps one plugin list per run. Every route that names the bridge in Nextflow's configuration either replaces the pipeline's pins or is silently replaced by them. The environment variable is the only route that adds the bridge, it touches nothing on the user's system beyond one run, and Seqera Platform's `nf-tower` is still added after it.

## Evidence

- **Sources:** Nextflow `v26.10.4` (`691b821`) and `v25.10.9` (`64d39b0`), read and run on 2026-10-29 on a toy pipeline pinning `nf-schema@2.7.2`; every claim carries file:line in the [verification record](../../reviews/verification-2026-10-29-nextflow-attach.md).
- **Docs gate:** `python3 tools/docs/check.py --base origin/autopilot/integration` reports 0 failures.
- **Strict build:** `uvx --with mkdocs-material mkdocs build --strict` exits 0; the decision-log anchor `2026-10-29-nf-spectio-is-enabled-with-nxf_plugins_default-set-per-run` exists in the built site.
- **Mermaid:** no diagram added or changed.
- **Before:** `git show 925ddb0:docs/specs/architecture-plugins-and-packaging.md` (§13.8 Enabling it). **After:** `git diff 925ddb0 -- docs/specs docs/plans docs/decisions docs/reviews/inbox.md tools/diagrams`.

## Figures and media

- `nextflow-attach` (above), new: `tools/diagrams/nextflow_attach.py`, entry `nextflow-attach` in `docs/assets/media.yaml`; light and dark PNGs opened.
- `mvp001_cluster`, changed (SR-425): the head's tmux pane, re-rendered with `python3 tools/diagrams/mvp001_cluster.py`; light and dark PNGs opened.
- The figures of the historical step pages T2 and APPLY5 still show `-plugins`, as records of those steps.

## Findings and open questions

- **Assumed from the decision** (inbox #69): the opt-in export and its profile rule; Spectio deposits the jar; doctor fails when the directory is missing.
- **[to be validated]:**
    - how a real Seqera Platform launch treats the variable;
    - `awsbatch` with a list;
    - what a run does when the variable names a version with no local copy and no registry release;
    - whether an upstream Nextflow issue already exists;
    - `NXF_PLUGINS_DEFAULT` on the EMBL cluster's Nextflow;
    - whether Platform cloud compute environments need the registry release.
