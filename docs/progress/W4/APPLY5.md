---
step: APPLY5
wave: W4
status: done
pr: null
review: approve
review_score: 11/14
review_ref: "doc-reviewer 2026-10-28, approve 11/14 on c66a29b, required changes applied; security review: docs/reviews/code/APPLY5.md"
---
# APPLY5 · Runs started from a terminal in 0.0.1

!!! success "Done 2026-10-28 · branch `autopilot/apply-observed-runs` · Thomas: 0.0.1 also monitors runs started from a terminal · bridges published in the engines' catalogues · mechanism assumed (pointer file) · the names wait for Thomas (inbox #66) · security review: 9 findings, all applied as §15.3 req. 12 · doc review approve 11/14, changes applied"

![APPLY5 figure, before and after, in three rows. Terminal runs: before, a run typed by hand is not in the runs list, deferred with no version set; after, nextflow run with -plugins nf-spectio@0.0.1, or once in ~/.nextflow/config, or Snakemake with --logger spectio, shows in the runs list with a terminal mark, monitor only, no Cancel. Discovery: before, the server reads only the run directories it created under the runs root; after, the bridge writes a pointer file ~/.spectio/observed/run_ULID.json, 0600, only if ~/.spectio exists, naming the launch directory and its .spectio/events spool; the server scans the pointers when observed/ changes and at rebuild, under the checks of requirement 12. The bridges: before, copies bundled in the spectio wheel, for UI launches only; after, the wheel for the UI, plus nf-spectio in the Nextflow registry and snakemake-logger-plugin-spectio on PyPI, listed by the Snakemake plugin catalogue; Thomas claims the names, the bridges are released as dev-env §12 says, Claude builds and dry-runs only](../../assets/diagrams/apply5_observed_light.png#only-light)
![APPLY5 figure, before and after, in three rows. Terminal runs: before, a run typed by hand is not in the runs list, deferred with no version set; after, nextflow run with -plugins nf-spectio@0.0.1, or once in ~/.nextflow/config, or Snakemake with --logger spectio, shows in the runs list with a terminal mark, monitor only, no Cancel. Discovery: before, the server reads only the run directories it created under the runs root; after, the bridge writes a pointer file ~/.spectio/observed/run_ULID.json, 0600, only if ~/.spectio exists, naming the launch directory and its .spectio/events spool; the server scans the pointers when observed/ changes and at rebuild, under the checks of requirement 12. The bridges: before, copies bundled in the spectio wheel, for UI launches only; after, the wheel for the UI, plus nf-spectio in the Nextflow registry and snakemake-logger-plugin-spectio on PyPI, listed by the Snakemake plugin catalogue; Thomas claims the names, the bridges are released as dev-env §12 says, Claude builds and dry-runs only](../../assets/diagrams/apply5_observed_dark.png#only-dark)

*Left: the specs and the plan on `autopilot/integration` at `9d0fa54`. Right: this branch. Sources are named under the figure.*

This step is outside [`pipeline.yaml`](../../playbooks/pipeline.yaml): Thomas decided on 2026-10-28 that 0.0.1 must also follow the runs that people start by hand, "otherwise few people will use it" ([decision log](../../decisions/log.md#2026-10-28-001-also-monitors-runs-started-from-a-terminal-bridges-published-in-the-engines-catalogues)).

## What changed

**Part 1, the first commit `c66a29b`.**

- **[dev-env §15.1](../../specs/dev-environment-and-testing.md#151-capabilities-by-version).** A new intro bullet. The terminal row moves from "no" to "yes, monitor only", with no Cancel *(assumed, inbox #65)*. Adopted runs, a `spectio run --` wrapper and the ingest token stay later.
- **[dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts).**
    - A short "Runs started from a terminal" bullet links to the owner. It marks EMBL egress to the registry and PyPI **[to be validated]**.
    - Req. 10 gains one sentence: the same checks apply to pointer files and to the `.spectio/` directory each one names.
    - "A person can take the head over" no longer says terminal runs come later.
- **[Architecture §13.8](../../specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal), new.** It covers:
    - how to enable the bridge for each engine;
    - the pointer file `~/.spectio/observed/<run ID>.json`, written only when `SPECTIO_RUN_ID` is unset and `~/.spectio/` exists;
    - discovery under req. 10, with origin `cli-observed`;
    - the run's end, through the existing head-alive check, never a signal;
    - the behaviour without Spectio, or with the server down;
    - monitor only;
    - a link to the §12 version window;
    - publishing.

    Architecture §2 and the §13 intro gain a line each.
- **[api §5.1](../../specs/api-and-data-model.md) and [ui-spec §6](../../specs/ui-spec.md).** Dated notes:
    - `:cancel` on a `cli-observed` run returns `422 not-in-this-version`;
    - 0.0.1 shows only the Observed level, with no adopt banner.
- **[`mvp-0.0.1.md`](../../specs/mvp-0.0.1.md).** A §2 feature row, whose Boards cell says the screen is not drawn for 0.0.1. The existing Boards cells are untouched while PR #48 is open. The item is removed from §3 Deferred.
- **[P1](../../plans/P1-walking-skeleton.md).**
    - The Goal is updated, with a new milestone M6 and Assumption 22.
    - Task 25 adds the pointer file in both bridges and the server's scan and display, with named tests for:
        - every untrusted-input case;
        - "no `~/.spectio` → run unaffected";
        - "driven run writes no pointer";
        - the rebuild;
        - "no Cancel".
    - Task 26 adds the release packages of both bridges, dry-run only.
    - Out of scope and Done when are updated, and a dated note says the P1 figure predates Tasks 25 and 26.
- **[Inbox](../../reviews/inbox.md).** Three new items, #65 to #67, and a note on #11.
- **[Decision log](../../decisions/log.md#2026-10-28-001-also-monitors-runs-started-from-a-terminal-bridges-published-in-the-engines-catalogues).** A new entry.

**Part 2, the reviews of `c66a29b`.**

- **Security review**, block: 1 blocker, 4 majors, 4 minors ([record](../../reviews/code/APPLY5.md)), all applied. [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) gains trust boundary (iv), other users who can write a launch directory, and a new req. 12, one line per control. The req. 10 sentence of Part 1 moved there. P1 Tasks 25 and 26 name a test for each.
- **Doc review**, approve 11/14. Required changes:
    1. Release mechanics have one owner, [dev-env §12](../../specs/dev-environment-and-testing.md#12-versioning-and-releases) (Publishing). The registry steps moved there, which clears its "[to be validated: registry release steps]". §13.8 keeps one line and a link. Inbox #66 now cites the §12 default (inbox #9 (c)) and asks Thomas to claim the four names; the log matches it.
    2. A terminal head on another login node is never marked lost (SEC-144).
    3. Two terminal runs in one launch directory get their own spool files (SEC-143).
    4. The bridge creates `observed/` 0700; a loose `observed/` is skipped with a warning and never blocks the start (SEC-146).
    5. §15.3 Where data lives lists `observed/` in the data directory, and the rebuild reads the pointers. The pointers stay at `~/.spectio/observed/` whatever the data directory *(assumed)*.
    6. The "before" caption names `autopilot/integration`.
- **Optional changes:** all applied.
    - The ui-spec §6 note says 0.0.1 uses Observed although the directory is readable.
    - §13.8 notes the `-C` exception and the `--logger` replacement risk **[to be validated]**.
    - The wrapper is "later (open)" everywhere.
    - Task 25 depends on Tasks 9 and 18, and `test_scan_finds_pointer` is renamed.
    - §13.8 gains a Logs line: engine logs, no `head.out`.
    - The branch is linked, and "at the GO gate" is dropped.

## Why

Most users at EMBL already run Nextflow and Snakemake by hand in tmux on a login node. A Spectio that sees only the runs it launched would be left unused (Thomas). The spool and the run directory already work without a network path or a credential, so the smallest addition is a way for the server to learn that a run exists. That way is a pointer file in the shared home. The pointer and the directory it names come from outside the server, so they get the checks that run directories already have (req. 10), and nothing sends a signal to a head that Spectio did not start.

## Evidence

- **Docs gate**, `python3 tools/docs/check.py` on this branch:

    ```text
    mermaid: 5 blocks checked
    diagrams: 27 scripts re-run, 54 SVGs compared
    media: 130 outputs in the manifest
    progress: 40 pages checked
    docs gate: 0 failure(s)
    ```

- **Mermaid:** no diagram changed in this step.
- **Strict build:** `uvx --with mkdocs-material mkdocs build --strict` exits 0. The new anchors exist in the built pages: `2026-10-28-001-also-monitors-runs-started-from-a-terminal-bridges-published-in-the-engines-catalogues` and `138-runs-started-from-a-terminal`.
- **Branch:** [`autopilot/apply-observed-runs`](https://github.com/weber8thomas/spectio/tree/autopilot/apply-observed-runs).
- **Before:** `git show 9d0fa54:docs/specs/mvp-0.0.1.md` (§3 lists "runs started from a terminal"). **After:** `git diff 9d0fa54 -- docs/specs docs/plans docs/decisions docs/reviews/inbox.md`.
- **External facts**, each read on 2026-10-28:
    - the Nextflow `plugins` block and the `-plugins` option, which ignores the plugins declared in config files ([using plugins](https://docs.seqera.io/nextflow/plugins/using-plugins));
    - `$NXF_HOME/config`, read first and with the lowest priority ([configuration](https://docs.seqera.io/nextflow/config));
    - release with the Gradle plugin, the registry claim, `npr.apiKey` and `make release` ([Gradle plugin guide](https://docs.seqera.io/nextflow/guides/gradle-plugin));
    - registry-only downloads from Nextflow 25.10 ([migrating plugins](https://docs.seqera.io/nextflow/guides/migrate-plugin));
    - the Snakemake plugin catalogue, built from PyPI ([catalogue](https://snakemake.github.io/snakemake-plugin-catalog/));
    - the four names unclaimed: `https://pypi.org/pypi/<name>/json` returns 404 for `snakemake-logger-plugin-spectio`, `spectio` and `spectio-open`, and `https://registry.nextflow.io/api/v1/plugins/nf-spectio` returns 404 (the same route returns `nf-hello`).

## Figures and media

- `apply5_observed` (above), new: [`tools/diagrams/apply5_observed.py`](https://github.com/weber8thomas/spectio/blob/main/tools/diagrams/apply5_observed.py), entry `apply5-observed` in `docs/assets/media.yaml`. Rendered light and dark; both PNGs were opened and checked for overlaps.
- The P1 figure `p1_skeleton` is not redrawn; a dated note under it says it predates Tasks 25 and 26.
- No screenshot or cast: nothing in this step runs.

## Findings and open questions

- **Inbox #65** *(assumed (a))*: no Cancel for terminal runs.
- **Inbox #66** *(not assumed)*: Thomas claims the four names and confirms the §12 release path. It blocks only the merge of the terminal-runs guide; Task 26 stops at the dry run.
- **Inbox #67** *(assumed (a))*: engine setup documented, not automated.
- **[to be validated]**:
    - whether the EMBL login nodes reach `registry.nextflow.io` and PyPI;
    - whether Nextflow 25.04, the floor of architecture §13.4, finds a plugin published only to the registry.
- **Merge note:** the new `mvp-0.0.1.md` §2 row sits next to rows that PR #48 changes. Expect a one-line conflict there.
- **Review findings:** SEC-141 to SEC-149, all applied ([record](../../reviews/code/APPLY5.md)); the doc review's required and optional changes, all applied (Part 2).
- **Still [to be validated]:** Java `SecureDirectoryStream` on the JDKs of architecture §13.4; inherited NFSv4 ACLs on EMBL storage (inbox #64 note); whether an explicit `--logger spectio` replaces a profile's loggers.
