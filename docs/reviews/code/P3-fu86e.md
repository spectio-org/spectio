# Code review · FU-P3-86e: environments boards and the Environment row of Launch (first part)

`review-code` on `autopilot/P3-fu86e`, 2026-11-09, merge base `b2d49079`, head `c5c4634d` (three commits: `e871a16e` the boards, `d6a3e4ab` the round 1 fix, `c5c4634d` the round 2 fix). The step is the first part of FU-P3-86e of the build plan of [inbox #133](../inbox.md#133-assumed-environments-local-slurm-define-a-new-one-fu-p3-86): the boards the screens of FU-P3-86f and -86g are built from. The behaviour is owned by [ui-spec §4.8.1](../../specs/ui-spec.md#481-environments-in-001) and [api-and-data-model §5.4](../../specs/api-and-data-model.md#54-environments-001). Progress: [P3 · M9, FU-P3-86e](../../progress/W5/P3-M9.md#fu-p3-86e-the-environments-boards-and-the-environment-row-of-launch-first-part). Format: [`README.md`](../README.md).

Outside `docs/`: 6 design boards, +372 −14 over the merge base (`git diff --shortstat b2d49079..HEAD`), all under `design/ui-canvas/`. No product code, no test, no `tools/` file.

## What the step does

- **New boards.**
  - `LiteEnvironments`: the list with the two built-ins, `mylab-long` (the default) and `gpu-test`, the empty line, and the built-in `slurm` with a bad `spectio.toml` value ("Not usable: partition in spectio.toml is not a valid name: run spectio init").
  - `LiteEnvironmentEdit`: the new form for SLURM, with the "At least 1 minute" error and Save waiting with its reason.
  - `MLiteEnvironments`: the phone list, drawn at 360 and 320 px.
- **Changed boards.**
  - `LiteSidebar` and `MLiteTabbar` gain a fourth item, Environments, in the sky section colour; the tab label may wrap and is 10 px below 340 px.
  - `LiteLaunch` gains the Environment fieldset (radios, `local` selected on a SLURM server, New environment), drops the Executor row, rewrites the Tasks row ("run on login1 by Nextflow · at most 2 CPUs") and draws the invalid-file state (only the built-ins, New environment `aria-disabled` with its reason).
- **Deferred to FU-P3-86e2** (named in the board footnotes only): `LiteEnvironmentsStates`, `MLiteEnvironmentEdit`, `LiteLaunchNewEnvironment`, `MLiteLaunch`, `LiteLaunchSnakemake`, `LiteRunDetail` and `LiteStatesRun`.

## Review rounds

Finding IDs restart in each round, so a bare `CR-P3FU86E-03` is ambiguous: the table says the round. The reports were relayed in summary, so the texts below are summaries.

| Round | Head | code-reviewer | security-reviewer | Fix |
|---|---|---|---|---|
| 1 | `e871a16e` | **changes** (0 blockers, 2 majors, 5 minors, 1 simplify: CR-P3FU86E-01 to -08, -07 is the simplify) | **approve** (0 blockers, 0 majors, 2 minors: SEC-P3FU86E-01, -02) | `d6a3e4ab` (CR-01, -02) |
| 2 | `d6a3e4ab` | **approve** (0 blockers, 0 majors, 3 minors, 1 simplify: CR-P3FU86E-03 to -06) | **approve** (0 blockers, 0 majors, 3 minors: SEC-P3FU86E-01 to -03) | `c5c4634d` (CR-03) |
| 3 | `c5c4634d` | **approve** (no finding reported) | **approve** (no finding reported) | none |
| simplify | none | `code-simplifier` runs once per batch ([documentation-system §3.5](../../specs/documentation-system.md#35-docs-per-batch-of-p3-tasks-thomas-2026-11-04)) | | |

```text
CODE  step=P3-fu86e  review=approve b/M/m=0/0/0  security=approve b/M/m=0/0/0  rounds=3  simplify=skipped -0/+0  tests=pass
```

The counts are those of round 3, which reported nothing. Findings of rounds 1 and 2 that no commit closes stay open below.

**Test command and result.** There are no automated tests for boards. The worker did the test-first step with a scratch copy of `tools/canvas/render.js` that dumps Chrome's accessibility tree (a scratch script, not committed). Before the round 2 fix the long-jobs card link was named "Long jobs, mylab mylab-long SLURM Default partition long · ... Profiles: ...", and its description was the same summary again. After it, Chrome reads "Long jobs, mylab , SLURM , Default" and the description is the summary only. The extra spaces come from Chrome's handling of the hidden commas and are the same on the Launch radios; screen readers do not pronounce them (the worker's statement, not re-checked with a screen reader **[to be validated]**).

The worker's full gate at `c5c4634d`:

```text
pytest 1382 passed, 1 skipped · ruff check and ruff format --check OK · mypy OK
lint-imports 4 contracts kept · uv lock --check OK · vitest 435 passed · tsc --noEmit OK
tools/docs/check.py 0 failures
```

None of these runs reads a board: the step changed no code, so they show only that the gate was not broken. The evidence for the boards is their rendering, re-run by `doc-writer` at `c5c4634d`:

```text
$ node tools/canvas/render.js design/ui-canvas/LiteEnvironments.dc.html 1440 1180 <out>/LiteEnvironments.png
ok <out>/LiteEnvironments.png
$ node tools/canvas/render.js design/ui-canvas/LiteEnvironmentEdit.dc.html 1440 1180 <out>/LiteEnvironmentEdit.png
ok <out>/LiteEnvironmentEdit.png
$ node tools/canvas/render.js design/ui-canvas/LiteLaunch.dc.html 1440 1180 <out>/LiteLaunch.png
ok <out>/LiteLaunch.png
$ node tools/canvas/render.js design/ui-canvas/MLiteEnvironments.dc.html 360 900 <out>/MLiteEnvironments.png
ok <out>/MLiteEnvironments.png
```

`doc-writer` looked at `LiteEnvironments.png`: four cards (two built-ins, `mylab-long` marked Default, `gpu-test`), the foot "Saved in ~/.spectio/environments.toml", the empty-line card and the unusable `slurm` card with its reason. The other three renders were made, not read in full.

## Findings

| Id | Round | Severity | Finding | Status |
|---|---|---|---|---|
| CR-P3FU86E-01 | 1 | **major** | The unusable `gpu-test` entry (a file entry with partition "gpu test") is a state api §5.4 never returns: a value outside its rule makes the whole file `invalid`. Only two cases are unusable per entry: the built-in `slurm` with a bad `spectio.toml` value, and a hand-written `slurm` entry on a local server. | fixed in `d6a3e4ab`: `gpu-test` is a valid entry (partition `gpu`), offered at Launch; the unusable card is the built-in `slurm` case, under "On this board, also" |
| CR-P3FU86E-02 | 1 | **major** | The Launch radios' accessible names did not match ui-spec §4.8.1 (UX-PRE-FU86-R1-15, "<label or name>, <executor>"): the summary and the Default badge sat inside the name and were read again as the description. The invalid-file section copied the pattern. | fixed in `d6a3e4ab`: each radio is `aria-labelledby` a span holding the label, a hidden comma and the executor badge; the summary (and the Default badge) are the `aria-describedby` |
| CR-P3FU86E-03 | 1 | minor | The same summary is read twice on two controls: each phone card link (name is all its content, description the summary span) and the Executor radios of `LiteEnvironmentEdit` (hint inside the `<label>` and the `aria-describedby`). | **half fixed**: the phone card link in `c5c4634d` (round 2 CR-03, below). The Executor radios of `LiteEnvironmentEdit` still hold the hint inside the label and in `aria-describedby` (lines 64 and 65 of the board, read by `doc-writer`); round 3 did not report it. Open: FU-P3-86e2 |
| CR-P3FU86E-04 | 1 | minor | Two unit selects on `LiteEnvironmentEdit` have the same accessible name, "Memory unit" (Memory per job; Memory at most). | open: FU-P3-86e2. Not in the round 2 or 3 reports; both `aria-label="Memory unit"` are still in the board (`doc-writer` grep) |
| CR-P3FU86E-05 | 1 | minor | Input bounds differ from api §5.4: `mem_mib` is 1 to 4,194,304 but the memory inputs have `min="0"`; `cpus` is 1 to 256 but CPUs at most has no `max`. | open: FU-P3-86e2. Same as -04: `min="0"` is still in the board |
| CR-P3FU86E-06 | 1 | minor | The phone board links "New environment" and every card to the desktop form `LiteEnvironmentEdit.dc.html`, because `MLiteEnvironmentEdit` is deferred; nothing says so. | open: see round 2 CR-04, FU-P3-86e2 |
| CR-P3FU86E-07 | 1 | simplify | The form is named by a hidden `<h2 id="f-h" class="sr">` that repeats the h1 "New environment"; the board defines no `.sr` class. | open: still in the board (line 50); a simplify, for the batch `code-simplifier` or FU-P3-86e2 |
| CR-P3FU86E-08 | 1 | minor | The branch is behind `autopilot/integration`, so the literal range `autopilot/integration..HEAD` lists 9 files the step never touched, shown as deletions. | process, no fix in the step: see SEC-P3FU86E-02 (round 1) and -03 (round 2) |
| SEC-P3FU86E-01 | 1 | minor | The boards drew a state the spec rules out and that echoed raw bytes of the environments file: a hand-written file entry with a bad partition as one "Not usable" entry, whose reason and summary quote "gpu test". Per api §5.4 such an entry makes the whole file `invalid`, and the `invalid` detail never holds file bytes. | fixed in `d6a3e4ab` with CR-01 (the card now shows only the built-in case). The built code agrees: `environments.py` `view()` lists file entries only when the state is `ok`. See SEC-P3FU86E-01 of round 2 for what is left |
| SEC-P3FU86E-02 | 1 | minor | The branch is behind `autopilot/integration`; a merge that copies the branch tree, or a patch made from the two-dot range, would silently revert FU-P3-102a's reviewed code. The step's own commits touch only the six boards (merge base `b2d49079`). | process: merge or rebase, never copy the tree. See round 2 SEC-03 |
| CR-P3FU86E-03 | 2 | minor | A phone card link announces its summary twice: the accessible name is all of its content, summary included, and `aria-describedby` points at the same span. | fixed in `c5c4634d`: the link is `aria-labelledby="{{e.nid}} {{e.bid}}"` and keeps `aria-describedby="{{e.did}}"`; the label span ends with a hidden comma (class `menv-sr`, the rules of `env-sr` on Launch) and a hidden comma goes before every badge but the first (`sep` in the fixture's `env()`). **Departure:** the finding asked for one wrapper span; the monospace name sits between the label and the badges, so one wrapper would add the name to the link's name or change the layout. Two ids give the name the finding asked for |
| CR-P3FU86E-04 | 2 | minor | Every phone card links to `LiteEnvironmentEdit.dc.html`, the desktop form, including the built-ins and `mylab-long`; `MLiteEnvironmentEdit` is deferred, so the link has no correct target yet. | open: FU-P3-86e2 (draw `MLiteEnvironmentEdit`, then relink the phone card and New environment) |
| CR-P3FU86E-05 | 2 | minor | The deferred boards are named FU-P3-86e2 in the board text, but nothing in the diff records that follow-up. | closed in this task's docs: the [Progress section](../../progress/W5/P3-M9.md#fu-p3-86e-the-environments-boards-and-the-environment-row-of-launch-first-part), the ui-spec §4.8.1 Boards line and [inbox #137](../inbox.md#137-assumed-environments-boards-first-part-what-is-deferred-and-what-an-unusable-card-shows-fu-p3-86e) |
| CR-P3FU86E-06 | 2 | simplify | The `e.unusable` template branches cannot be reached, because no fixture entry sets `unusable`; the hand-drawn "also" card repeats the template's Not usable `<p>` word for word. | open: left to the batch `code-simplifier` |
| SEC-P3FU86E-01 | 2 | minor | The unusable built-in `slurm` card prints the rejected `spectio.toml` value ("partition gpu test"), which failed the closed character set. api §5.4 strips control and format characters from labels and the `invalid` detail, but says nothing on how the rejected `[slurm]` values of an unusable built-in are shown. A hand-edited `spectio.toml` could carry bidi or format characters, or a very long string, into the summary line. Low risk (single user, React escapes HTML): hardening. | decided in ui-spec §4.8.1 as an assumption ([inbox #137](../inbox.md#137-assumed-environments-boards-first-part-what-is-deferred-and-what-an-unusable-card-shows-fu-p3-86e), choice 2): an unusable built-in shows its `unusable_reason`, which names the field and never the value, and no value of `spectio.toml` in its summary. The board still prints "partition gpu test" in its summary line (line 81 of `LiteEnvironments`); open: FU-P3-86e2 |
| SEC-P3FU86E-02 | 2 | minor | The states moved to FU-P3-86e2 carry the security messaging of dev-env §15.3 req. 18 and api §5.4: the `refused` file state ("Spectio will not change it"), the Delete confirmation dialog, and the 412 and 409 Reload paths. Only board footnotes name FU-P3-86e2; nothing in `docs/plans`, the inbox or `pipeline.yaml` records it. | closed in this task's docs for the inbox and the Progress page ([inbox #137](../inbox.md#137-assumed-environments-boards-first-part-what-is-deferred-and-what-an-unusable-card-shows-fu-p3-86e), choice 1); `pipeline.yaml` is not edited by agents, so it is not recorded there |
| SEC-P3FU86E-03 | 2 | minor | Process only. The literal two-dot range `autopilot/integration..HEAD` lists 15 files; 9 of them (`results.py`, `workdir.py`, `files/results.py`, `test_imaging.py` with 339 lines, `openapi/0.0.1.json`, an api spec line, a review record, a progress page, the journal) show as reverted only because integration moved ahead to `cfa7d64d`, `00dcfeb1` and `245a70ca`. `git merge-tree` reports a clean merge. | process: integrate by merge |

## For the Progress page

- **Built:** three new boards and three changed ones; the Environment choice at Launch in two states (radios, invalid file); the phone tab bar with four tabs.
- **Open, minor:** CR-P3FU86E-03 (the form's Executor radios), -04 (unit names), -05 (bounds) of round 1, CR-P3FU86E-04 (phone links) and SEC-P3FU86E-01 (the printed value) of round 2 go to FU-P3-86e2, with the seven boards. The two simplify items (CR-07 of round 1, CR-06 of round 2) go to the batch `code-simplifier`.
- **Not done:** the seven boards above, so the screens of FU-P3-86f and -86g have no board yet for the file states, the dialogs, Snakemake with a profile, the run's Environment fact and the phone form. No screen reader was run.
