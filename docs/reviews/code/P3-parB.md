# Code review · P3 UI parity B, the phone, the Launch form and the Head word

`review-code` on `autopilot/P3-parB`, base `4ce9112` (UI parity A merged as #105), 2026-10-31. The step fixes findings UX-PAR-08 to 10 and 30 to 34 of the [UI parity audit](../ui-parity-0.0.1.md), the UI items of follow-up FU-P3-25 (CR-P3PARA-03, 06, 07, 09 r2, 10 r2), and the Head fact that read "Alive" on runs that had ended. It adds:

- `web/src/shell/layout.tsx` (new): the phone's title row, where a page puts its `h1` and a 44 px back link; `TopBar.tsx`, `PageHead.tsx` and `AppShell.tsx` use it. 44 px targets on the phone in `shell.css`;
- the phone's cards: `RunCard` in `runs/RunsPage.tsx` (also used by Home), process, task and parameter cards in `runs/RunDetailPage.tsx`, the phone header in `runs/RunHeader.tsx`, two-by-two count cards and sideways segments in `runs/runs.css`;
- the Launch form: `launch/schemaFields.ts` (sections with description and icon, dotted keys for Snakemake maps, `buildParams`, `toYaml`), `launch/LaunchPage.tsx` (groups that fold, the preview, the Loaded card, "Where it runs", the pinned bar), `executorLabel()` in `runs/stateWord.ts`, `groupIcon()` in `icons.tsx`, and `status`, `sub` and `reveal` in `shell/FoldSection.tsx`;
- the Head word: a runner change (`2f6809b5`), reverted (`7993752a`), then "Ending" on the screen (`614b81f5`);
- tests: `phone.test.tsx` and `icons.test.ts` (new), and new tests in the Launch, schema, runs, state-word and fold-section files; `tests/e2e/skeleton.spec.ts` expects a list of processes on the phone;
- the live shots `app-home-phone`, `app-runs-phone` and `app-launch-snakemake` (new), five others retaken (`tools/media/shots.py`, `live.js`, `README.md`, `docs/assets/media.yaml`).

The reviewers were `code-reviewer` and `security-reviewer`, independent and in parallel. Format: [`README.md`](../README.md). The behaviour is owned by the ui-spec notes "UI parity B" of 2026-10-31 in [§4.3](../../specs/ui-spec.md#43-runs-table-and-rows), [§4.4](../../specs/ui-spec.md#44-run-detail), [§4.6](../../specs/ui-spec.md#46-launch-and-relaunch) and [§4.11](../../specs/ui-spec.md#411-phone-and-tablet). The docs commit wrote them.

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `35ed465` (the step, with its shots) | **approve** (5 minors, 1 simplify) | **changes** (1 major, 1 minor) |
| 2 | `8c86467` (SEC-P3PARB-01 fixed) | **approve** (5 minors, 1 simplify) | **approve** (1 minor; SEC-P3PARB-01 recorded as fixed) |
| 3 | `8c86467` (the fix round made no change) | **changes** (1 major, 5 minors, 2 simplify) | **approve** (2 minors) |
| 4, by hand | `8c86467..614b81f` (the revert and the round-3 fixes) | **changes** (1 major, already fixed in `dcec010`; 3 minors) | **approve** (none) |
| 5 | `dcec010`, `db620dc`, `b092b7c` (the fixes after round 4) | **approve** (1 minor, also a simplify: CR-P3PARB-R5-01) | not run |
| simplify | not run | its findings fixed by hand in `614b81f` and `e6de280`, except CR-P3PARB-08 | |

Rounds 1 to 3 ran in the `review-code` workflow. It stopped with "two fix rounds without approval" (round 3's major). The step's prompt lifted the two-round ceiling for this fix, so round 4 was run by hand on the range of the revert and the round-3 fixes. Round 5 was a `code-reviewer` pass on the three commits after round 4: `dcec010`, `db620dc` (the round-4 minors, +5 −3) and `b092b7c` (the phone header line, +9 −2). It approved, with one finding, fixed in `e6de280` (+3 −4, a variable removed), which has had no review of its own. `security-reviewer` did not run in round 5; its last verdict is round 4's approve.

**Finding IDs restart in each round**, so this record writes the round after an ID. CR-P3PARB-01 (r1), (r2) and (r3) are three findings about the same runner change; round 4's IDs carry `R4`.

**Test-first.** Each fix commit adds or changes the test that pins it; the round-4 `code-reviewer` judged, for each round-3 fix, that its test would fail without it. `doc-writer` checked the smoke's phone change: the base's spec fails on the phone against the new build, and the new one passes ([P3-M4 Evidence](../../progress/W5/P3-M4.md#ui-parity-b-the-phone-the-launch-form-and-the-head-word_1)).

Gate at `1eb483b`, from the worktree, re-run by `doc-writer`; vitest, `tsc` and the build re-run at `e6de280` with the same results (JS asset 429.06 kB, gzip 137.94 kB):

```bash
uv run --locked pytest -q   # 511 passed, 15 deselected (no product Python file changed)
cd web && npx vitest run    # 14 files, 114 tests passed
cd web && npx tsc --noEmit  # exit 0
cd web && npm run build     # dist/index.html, two logo PNGs, one CSS and one JS asset
# smoke, no engines, against serve-local.sh: 10 passed, 12 skipped (desktop and phone)
```

The round-4 `security-reviewer` ran `bash tools/ci/security.sh sast` on its range: 79 rules on 193 files, 0 findings.

```text
CODE  step=P3-parB  review=approve b/M/m=0/2/19  security=approve b/M/m=0/1/4  rounds=5  simplify=not-run -0/+0  tests=pass
```

The counts add up the five rounds of `code-reviewer` and the four of `security-reviewer`, from each report's own count line. The five `simplify` findings are not counted. `review=approve` is round 5's verdict. Round 4's was `changes` on `8c86467..614b81f`; its reviewer wrote that, with `dcec010` counted, no major remains and the verdict would be approve.

## Findings

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3PARB-01 (r1) | minor | With `2f6809b5`, a terminal run leaves `active_launches` as soon as the non-final report sets `exited_at`, so the runner stops reading its spool partway through the 60 s grace; the docstrings say the opposite. | superseded by CR-P3PARB-01 (r3); fixed by the revert `7993752a` |
| CR-P3PARB-02 (r1) | minor | UX-PAR-10 only in part: MLiteRuns groups the phone cards under a folding "ACTIVE · n", which was not built and had no owner. | **open**: follow-up FU-P3-26 |
| CR-P3PARB-03 (r1) | minor | The CR-P3PARA-10 check is a separate test that passes only after the Download test in the same file. | fixed in `614b81f`: the restore is checked inside the Download test (same as CR-P3PARB-03 r2, CR-P3PARB-05 r3) |
| CR-P3PARB-04 (r1) | minor | The CR-P3PARA-09 test hides a real 300 ms sleep, the pattern CR-P3T20-06 flagged. | **open**: follow-up FU-P3-26 |
| CR-P3PARB-05 (r1) | simplify | `.launch-loaded-status` is declared twice in `app.css`. | fixed in `614b81f` (one rule; same as CR-P3PARB-05 r2, CR-P3PARB-07 r3) |
| CR-P3PARB-06 (r1) | minor | Field hints in two places: Profile and Run name under the input, every schema parameter above it (Mantine's default); LiteLaunch puts them under. | **open**: follow-up FU-P3-26 |
| SEC-P3PARB-01 (r1) | major | Prototype pollution in the Launch form: schema keys from the pipeline (`__proto__`, `constructor.prototype`) became path segments, and `buildParams` wrote through `at[part] ??= {}` onto `Object.prototype`; inherited `toString` counted as filled. | fixed in `8c86467`: the three keys are skipped and named in a notice; null-prototype maps; values and parent defaults read as own properties; a test checks `({}).polluted` stays undefined |
| SEC-P3PARB-02 (r1) | minor | Dotted-key collisions: a top-level key `ref.release` and the nested `ref` → `release` get one form key, so both are sent and a 422 is ambiguous. | fixed in `614b81f` as SEC-P3PARB-03 (r3) |
| CR-P3PARB-01 (r2) | minor | A terminal Nextflow run stops having its spool read at the tick after its head exits; the end grace no longer covers it. | superseded by CR-P3PARB-01 (r3); fixed by the revert `7993752a` |
| CR-P3PARB-02 (r2) | minor | On the phone, the run header's duration line broke inside a value ("· 8" then "s · ended…"). | fixed in `614b81f` (each value `nowrap`), then `b092b7c`: `nowrap` alone let the line run past the card, so the header's line is a wrapping flex row. The new line can start with "·": FU-P3-26 |
| CR-P3PARB-03 (r2) | minor | The CR-P3PARA-10 check depends on test order, and its restore writes an own `undefined` where jsdom had none. | fixed in `614b81f` |
| CR-P3PARB-04 (r2) | minor | Partial nested maps for Snakemake (`{ref: {release: 114}}`) work only if Snakemake deep-merges a `--configfile` over the workflow's config, an unsourced fact about an external tool. | fixed in `614b81f`: a map with one value set is sent whole, its other keys at their defaults, so no merge rule is assumed; the merge stays **[to be validated]** |
| CR-P3PARB-05 (r2) | simplify | `.launch-loaded-status` declared twice. | fixed in `614b81f` |
| CR-P3PARB-06 (r2) | minor | `app-launch-snakemake` used a config with no nested map, so it showed none of UX-PAR-31's dotted sections. | fixed in `8c0f638`: the demo copy's `config/config.yaml` has a map `ref`, the shot opens it and sets `ref.release` |
| SEC-P3PARB-01 (r2) | recorded as fixed | Round 2 re-filed round 1's finding with severity "blocker" and status fixed, verified in `8c86467`; its report counts 0 blockers. | fixed in `8c86467` |
| SEC-P3PARB-02 (r2) | minor | `groupIcon` read `GROUP_ICONS[name]` through the prototype chain: `fas fa-constructor` returned `Object`, a function, where a path string was expected. | fixed in `614b81f` as SEC-P3PARB-02 (r3) |
| CR-P3PARB-01 (r3) | major | The Head "Alive" fix stopped the end-grace spool reads early for a run the engine had already ended: the non-final report set `launches.exited_at`, and the sink lists a launch only while its run is not terminal or `exited_at` is null. | fixed: `7993752a` reverts `2f6809b5` whole (`git diff 2f6809b5^ 7993752a -- packages` is empty); `614b81f` shows Head "Ending" for a terminal run whose head's end is not reported yet |
| CR-P3PARB-02 (r3) | minor | Dotted sections applied to every schema without `$defs`, Nextflow included, where a partial map in `-params-file` may replace the whole map. | fixed in `614b81f`: nesting for Snakemake only; a Nextflow map stays one JSON field |
| CR-P3PARB-03 (r3) | minor | `toYaml` left ".5" or "._1" unquoted, which PyYAML reads as floats, so the preview differed from the request. | fixed in `614b81f`: no leading dot in a plain scalar, with a test |
| CR-P3PARB-04 (r3) | minor | Each group's React key was `location:title`; two sections may share a title. | fixed in `614b81f`: keyed by position |
| CR-P3PARB-05 (r3) | minor | The CR-P3PARA-10 check passes when run alone, so it guards nothing. | fixed in `614b81f`: asserted inside the Download test |
| CR-P3PARB-06 (r3) | minor | `app-launch-snakemake` needs `SPECTIO_DEMO_SMK_PIPELINE` and a hand-written `config/config.yaml`, neither documented. | fixed in `8c0f638`: `tools/media/README.md` names the variable and gives the file |
| CR-P3PARB-07 (r3) | simplify | `.launch-loaded-status` in two blocks. | fixed in `614b81f` |
| CR-P3PARB-08 (r3) | simplify | The Engine row of "Where it runs" writes the head wording a second time; `RunsPage`'s `headsWhere` already decides it. | **open**: follow-up FU-P3-26 |
| SEC-P3PARB-02 (r3) | minor | `groupIcon` indexes a plain object with a schema-derived name (as in r2). | fixed in `614b81f`: `Object.hasOwn(GROUP_ICONS, name)`, with a test |
| SEC-P3PARB-03 (r3) | minor | A top-level key `a.b` and a nested `a` → `b` share one form key, one React key and one 422 target. | fixed in `614b81f`: the second is skipped and named in the "Not in the form" notice, with a test |
| CR-P3PARB-R4-01 | major | `buildParams` read `sent.get(field) ?? …`, so a JSON `null` typed in was treated as unset (inside a touched map, its default was sent), while "n values changed" still counted it. | fixed in `dcec010`: `set !== undefined`, with a nested-null test (the round-4 reviewer saw it) |
| CR-P3PARB-R4-02 | minor | A duplicate dotted key now goes to `skipped`, but the notice said "Spectio refuses these key names". | fixed in `db620dc`: "These keys are unsafe or repeat another key's dotted name" |
| CR-P3PARB-R4-03 | minor | The form's shape depends on the engine chosen: with no engine guessed it starts in the Nextflow shape, and values typed under one shape are hidden and unsent under the other. | **not fixed**: follow-up FU-P3-26. `db620dc` made the shape follow `engine ?? guess`, which round 5 found always equals `engine` (CR-P3PARB-R5-01); `e6de280` dropped it. The behaviour is written in a comment, `LaunchPage.tsx:128-129` at `e6de280` |
| CR-P3PARB-R4-04 | minor | The `fa-tostring` assertion in `icons.test.ts` tests nothing. | fixed in `db620dc`: dropped |
| CR-P3PARB-R5-01 | minor (simplify) | `db620dc`'s `formEngine = engine ?? guess` never changed behaviour: `engine` is null only before a load or when the guess is null, so it always equals `engine`. R4-03 was therefore not fixed. | fixed in `e6de280`: `formEngine` dropped, the form reads `engine`; R4-03 goes whole to FU-P3-26 |

## Fixes by commit

| Commit | Findings |
|---|---|
| `8c86467` fix(web): Launch treats pipeline schema keys as data (SEC-P3PARB-01) | SEC-P3PARB-01 (r1) |
| `7993752a` revert(runner): keep the end grace whole, the head's end reported after it (CR-P3PARB-01) | CR-P3PARB-01 (r1, r2, r3) |
| `614b81f` fix(web): P3-parB round 3 findings | CR-P3PARB-01 (r3) (Ending), -02 to -05 and -07 (r3), SEC-P3PARB-02 and -03 (r3), CR-P3PARB-04 (r2), -02 (r2), and the repeats CR-P3PARB-03 and -05 (r1, r2), SEC-P3PARB-02 (r1, r2) |
| `dcec010` fix(web): a JSON null typed in a nested field is sent as null | CR-P3PARB-R4-01 |
| `8c0f638` docs(media): P3-parB live shots retaken at db620dc | CR-P3PARB-06 (r2), CR-P3PARB-06 (r3) |
| `db620dc` fix(web): P3-parB round 4 minors | CR-P3PARB-R4-02, -04 (its change for -03 was dropped in `e6de280`) |
| `b092b7c` fix(web): the phone run header's line wraps between values, not past the card | the overflow left by CR-P3PARB-02 (r2)'s first fix, seen while retaking the shots |
| `e6de280` refactor(web): drop formEngine, which always equalled engine | CR-P3PARB-R5-01 |

## For the Progress page

The parity B section of P3-M4 is written: [P3-M4 · UI parity B](../../progress/W5/P3-M4.md#ui-parity-b-the-phone-the-launch-form-and-the-head-word), with its [findings and open questions](../../progress/W5/P3-M4.md#findings-and-open-questions) and follow-up FU-P3-26.
