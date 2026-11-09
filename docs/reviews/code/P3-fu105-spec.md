# Pre-review · FU-P3-105, performance per run and across runs (design only)

Step `P3-fu105-spec` on `autopilot/P3-fu105-spec`, base `9b9c3c81`, 2026-11-09. The step writes the design of FU-P3-105 ([decision log](../../decisions/log.md#2026-11-09-performance-per-run-and-across-runs-fu-p3-105), [inbox #139](../inbox.md#139-assumed-performance-per-run-and-across-runs-fu-p3-105)); it changes no code, so `code-reviewer`, `code-simplifier` and the tests do not run.

There is no `CODE` line in this record: the step changes no code, so there is no code to review.

Reviewed sections:
- [schedulers §3.7](../../specs/schedulers-and-monitoring.md#37-performance-measures-per-attempt), new;
- [api §5.5](../../specs/api-and-data-model.md#55-performance-002), new, with one note in §5.4 and one in §7;
- [ui-spec §4.12](../../specs/ui-spec.md#412-performance-002), new.

## Rounds

| Round | Who | Independent | security | UX |
|---|---|---|---|---|
| R0 | the design worker, on the two agents' checklists | **no** | changes 0/0/3 (applied) | changes 0/0/3 (applied) |
| R1 | `security-reviewer` and `ux-reviewer`, run by the coordinator, and the SLURM polling audit (`constraints-hunter`) | yes | changes 0/7/7 | changes 0/9/8 |

R1 is the independent round; its findings and their outcome are [below](#r1-independent).

## R0, self-review (not independent)

### How it ran

The design worker had no Agent tool. It went through `.claude/agents/security-reviewer.md` and `.claude/agents/ux-reviewer.md` itself. Code read: `engine-bridges/nf-spectio/src/spectio/SpectioPlugin.groovy` (`TRACE_KEYS`, `enableMetrics`), `spectio_server/failure.py` (`trace_resources`, `smk_resources`, the `sacct` cache), `spectio_server/efficiency.py`, `spectio/runner/sacct.py` (`FORMAT`), `spectio_server/static.py` (`CSP`), `migrations/versions/` (last: `0011_run_environment`). Web pages read on 2026-11-09: the Nextflow trace reference and reports page, `ReportSummary.groovy` and `ReportTemplate.js` on `master`, the Snakemake SLURM plugin catalogue page, its CHANGELOG and `efficiency_report.py` at v2.8.0, the plotly.js dist README (3.7.0). GitHub's API was not reachable from the session (`403`); raw files and pages were.

### plotly.js under the page's CSP (audit, 2026-11-09)

`npm pack plotly.js-cartesian-dist-min@4.2.0`, `@4.1.2` and `plotly.js-basic-dist-min@4.2.0`, unpacked in a scratch folder and searched as text:

| Bundle | Minified | gzip | `eval(` | `new Function` | `Function(` constructor | `blob:` | `createObjectURL` | licence |
|---|---|---|---|---|---|---|---|---|
| cartesian 4.2.0 | 1,514,949 B | 502,361 B | 0 | 0 | 1 (`Function("binder", …)`) | 0 | 4 | MIT |
| cartesian 4.1.2 | 1,507,990 B | 500,307 B | 0 | 0 | 1 (same) | 0 | present | MIT |
| basic 4.2.0 (no box) | 1,202,920 B | 399,410 B | 0 | 0 | 1 (same) | 0 | 4 | MIT |

- The one constructor sits in the `function-bind` shim: `module.exports = Function.prototype.bind || <shim>`, so it runs only where `bind` is missing.
- `createObjectURL` is used by image export (`toImage`) and download only; the design turns the mode bar off and offers CSV instead.
- `createElement("style")` and `insertRule`: allowed by `style-src 'unsafe-inline'`.
- `data:image` strings are CSS of map controls not used by these traces; `img-src 'self'` would block them, without effect on box, scatter or bar **[to be validated]** in the browser test.
- The basic bundle has no `box` trace ([dist README](https://app.unpkg.com/plotly.js@3.7.0/files/dist/README.md)), hence cartesian.

### Security checklist (`security-reviewer`)

- **SLURM load.** No route calls `sacct`; one more field in the existing batched call; the plugin report only when Spectio's accounting is off, one call per run, by the plugin. Fine.
- **Untrusted files.** The benchmark file and the plugin CSV are written by the user's jobs. *m1:* the benchmark file is read once, size-capped, through the run files' confined reader, and parsed as numbers only. *Corrected in R1 (SEC-PRE-FU105-R1-05):* this line said the plugin CSV was read the same way, but §3.7 did not say so; since R1 the CSV is not read at all.
- **Denial of service on the across-runs routes.** *m2 (applied):* range, groups, scanned rows and page size are capped (§5.5).
- **Visibility.** *m3 (applied):* the across-runs routes list the caller's visible runs (§6); `user` only where multi-user.
- **Head argument** (moot since R1: no plugin option). `efficiency_report` is a boolean; the path is the run's own `.spectio/`, built by the head script, not taken from input.
- **Supply chain.** plotly pinned exactly, licence MIT, lazy chunk; the FU-P3-105g task runs `npm ls`, the licence check and the CSP listener.

### UX checklist (`ux-reviewer`)

- *m1 (applied):* every chart has a Chart | Table pair and a caption; plotly's hover is never the only way to read a value.
- *m2 (applied):* states: loading, empty, no measure, range too wide, truncated, error, chunk not loaded, a server before 0.0.2.
- *m3 (applied):* the phone layout has no plotly; filters in a sheet with Apply; 44 px targets as §4.11.
- Boards are not drawn yet (FU-P3-105f); no render was looked at.

## R1, independent

Run 2026-11-09 on `df6603de`: `security-reviewer` (changes, 0/7/7) and `ux-reviewer` (changes, 0/9/8), each with a fresh context, and the SLURM polling audit of `constraints-hunter` the same day, whose §5 policy is binding here (Thomas, 2026-11-09: do not overload SLURM, no extra polling). The audit's other findings (CON-SLURM-POLL-01 to -12: the live per-job `sacct` queue, back-off, `-S` on every call, one owner for the SLURM query budget) are for its own step, not this one.

**SLURM-budget decision, applied to §3.7.** SLURM values come from one end-of-run `sacct` sweep per run through the existing `SacctLimiter` (job ID list, `--user`, `-S`/`-E` window), with one follow-up for missing IDs; the plugin's `--slurm-efficiency-report` is not used (the `efficiency_report` environment field, the head options, the CSV read and inbox #139 choice 4's plugin branch are removed) and is refused in `extra_args`; the across-runs routes read only the database; with `[slurm] accounting = false` the SLURM values are absent.

| ID | Sev. | Outcome |
|---|---|---|
| SEC-PRE-FU105-R1-01 tenancy | major | applied: `project_id` on the row, updated on a run move; rows deleted with the run; four `project_id` indexes; every query filters `visible_projects`; `test_perf_tenancy_*` (api §5.5) |
| SEC-PRE-FU105-R1-02 principals | major | applied: who may read, per route (api §5.5) |
| SEC-PRE-FU105-R1-03 DoS | major | applied: time budget off the event loop, per-principal and per-server limit with `429`, count check, `metrics` at most 4, streamed statistics, cache of ended runs, input caps, `range-too-wide` in §4.1; the 5 s budget is **[to be validated]** in FU-P3-105e |
| SEC-PRE-FU105-R1-04 plotly pseudo-HTML | major | applied: one escape helper, Spectio's `hovertemplate`, text cells, the Playwright test (ui-spec §4.12); partition check (schedulers §3.7) |
| SEC-PRE-FU105-R1-05 CSV read unconfined | major | resolved by decision: the CSV is not read; R0 line corrected |
| SEC-PRE-FU105-R1-06 `efficiency_report` re-enables `sacct` | major | resolved by decision: field and plugin options removed |
| SEC-PRE-FU105-R1-07 migration reads `sacct.json` at boot | major | applied: the migration fills from the database only; `sacct.json` in a background task (api §5.5); the three tests go to FU-P3-105a |
| SEC-PRE-FU105-R1-08 ingest validation | minor | applied (schedulers §3.7, Ingest checks) |
| SEC-PRE-FU105-R1-09 allowlists | minor | applied (api §5.5, Input checks) |
| SEC-PRE-FU105-R1-10 CSV export | minor | applied: formula prefix; stop rule reworded to "any change to a CSP directive" (inbox #139); whether AG Grid's CSV download uses a `blob:` URL is deferred to FU-P3-105g **[to be validated]** |
| SEC-PRE-FU105-R1-11 plotly config and citation | minor | applied: frozen config, exact pin with integrity, `npm ci --ignore-scripts` (ui-spec §4.12); citation now the 4.1.2 tarball audit (inbox #139) |
| SEC-PRE-FU105-R1-12 head-script arguments | minor | resolved by decision: no plugin option; `--slurm-efficiency-report*` refused in `extra_args` (api §5.4 note) |
| SEC-PRE-FU105-R1-13 what is not stored | minor | applied (api §5.5) |
| SEC-PRE-FU105-R1-14 benchmark read off the writer | minor | applied (schedulers §3.7); its test goes to FU-P3-105b |
| UX-PRE-FU105-R1-01 no More sheet | major | applied: More key and sheet, Environments moves in (ui-spec §4.12 Phone); shell code in FU-P3-105i |
| UX-PRE-FU105-R1-02 duplicates By process | major | applied: the tab replaces By process; Order moves; median headline; waste lines above |
| UX-PRE-FU105-R1-03 no metric control on the page | major | applied: controls in the URL, top 20 with no pipeline, 30 boxes then Show all, no request line |
| UX-PRE-FU105-R1-04 API gaps | major | applied: `tag`, `totals`, `jobs.total`, `processes_truncated`, page max 200, facet `{id, name}` (api §5.5) |
| UX-PRE-FU105-R1-05 missing states | major | applied; the accounting-off text says `benchmark:` only, after the SLURM-budget decision; the terminal run in schedulers §3.7 |
| UX-PRE-FU105-R1-06 visibility and refresh | major | applied: tab by task counts, 30 s refresh while visible, Updated and Refresh |
| UX-PRE-FU105-R1-07 URL state | major | applied: `range=` presets, UTC custom, `tz=`, `hour`, process cap 20, every control in the URL |
| UX-PRE-FU105-R1-08 worst job hover-only | major | applied: `min_task`/`max_task`, links, Show jobs sorted, point click opens the drawer |
| UX-PRE-FU105-R1-09 boards | major | applied as the list (ui-spec §4.12 Boards); drawing deferred to FU-P3-105f |
| UX-PRE-FU105-R1-10 units and words | minor | applied |
| UX-PRE-FU105-R1-11 metric sub-choices | minor | applied |
| UX-PRE-FU105-R1-12 colour not the only signal | minor | applied |
| UX-PRE-FU105-R1-13 phone | minor | applied; 44 px at 320 checked on the boards, FU-P3-105f |
| UX-PRE-FU105-R1-14 Count radio and low mark | minor | applied |
| UX-PRE-FU105-R1-15 Show jobs and CPU waste wording | minor | applied: `&sort=`; the CPU line added to schedulers §3.6 |
| UX-PRE-FU105-R1-16 table and box interaction | minor | applied |
| UX-PRE-FU105-R1-17 icon, token, capability | minor | applied: `chart-column`, `--sp-section-performance`, detection by `GET /version`, dev-env §15.1 row |

Deferred, with their build task: the board drawing (FU-P3-105f), AG Grid's CSV `blob:` check (FU-P3-105g), the time budget's value (FU-P3-105e); the tests named above go to the task that builds their part.
