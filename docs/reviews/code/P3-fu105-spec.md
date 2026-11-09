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

An independent round (`security-reviewer` and `ux-reviewer`, run by the coordinator) is still to come; until then this review is **not independent**.

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
- **Untrusted files.** The benchmark file and the plugin CSV are written by the user's jobs. *m1 (applied):* both are read once, size-capped, through the run files' confined reader, and parsed as numbers only (§3.7).
- **Denial of service on the across-runs routes.** *m2 (applied):* range, groups, scanned rows and page size are capped (§5.5).
- **Visibility.** *m3 (applied):* the across-runs routes list the caller's visible runs (§6); `user` only where multi-user.
- **Head argument.** `efficiency_report` is a boolean; the path is the run's own `.spectio/`, built by the head script, not taken from input.
- **Supply chain.** plotly pinned exactly, licence MIT, lazy chunk; the FU-P3-105g task runs `npm ls`, the licence check and the CSP listener.

### UX checklist (`ux-reviewer`)

- *m1 (applied):* every chart has a Chart | Table pair and a caption; plotly's hover is never the only way to read a value.
- *m2 (applied):* states: loading, empty, no measure, range too wide, truncated, error, chunk not loaded, a server before 0.0.2.
- *m3 (applied):* the phone layout has no plotly; filters in a sheet with Apply; 44 px targets as §4.11.
- Boards are not drawn yet (FU-P3-105f); no render was looked at.
