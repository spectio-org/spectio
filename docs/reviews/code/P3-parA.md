# Code review · P3 UI parity A, the shell, Home, the runs list and the run detail

`review-code` on `autopilot/P3-parA`, base `2785941`, 2026-10-31. The step fixes, within what the 0.0.1 API serves, findings UX-PAR-01 to 07, 11 to 27 and 29 of the [UI parity audit](../ui-parity-0.0.1.md). That audit compares the built screens with the 0.0.1 lite boards. Thomas asked for the step on 2026-10-31 (`.autopilot/journal.md`, 02:40 entry). It adds:

- `web/src/shell/`: `EngineMark.tsx` (the engine's mark, no nf-core mark: [inbox #91](../inbox.md#91-assumed-which-mark-a-pipeline-shows-no-nf-core-mark-yet-and-where-the-logos-come-from)), `FoldSection.tsx` (a folding section, remembered per screen), `PageHead.tsx` (the 48 px section tile), the active-run badge and active-on-child-pages links in `Sidebar.tsx` and `TabBar.tsx`, exact crumbs in `TopBar.tsx`, and the `--sp-state-*` tokens in `theme.ts`;
- `web/src/icons.tsx` (inline SVG paths, no new dependency) and the two logo PNGs in `web/src/assets/logos/`;
- `web/src/home/HomePage.tsx`: the subtitle words, linked count cards with a detail line, the marks, "Where your runs go";
- `web/src/runs/`: `RunsPage.tsx` (filters in the URL, the marks, the Tasks cell, the footer), `RunHeader.tsx` (new: the header, facts and task chips that every tab shares), `RunDetailPage.tsx` (Why it failed, stages and processes with bars, the Summary aside, the Tasks filters, the Logs tab, the Cancel dialog), `RunState.tsx` and `stateWord.ts` (tones, the engine's words, class words), `runs.css`;
- tests: `rail.test.tsx` and `FoldSection.test.tsx` (new), and new tests in `shell.test.tsx`, `HomePage.test.tsx`, `RunsPage.test.tsx`, `RunDetailPage.test.tsx` and `stateWord.test.ts`; `vite.config.ts` lets Vitest load `runs.css`;
- the live shots `app-home`, `app-runs`, `app-run-detail` and `app-run-detail-phone` retaken, the new shot `app-run-detail-failed` (`tools/media/shots.py`, `docs/assets/media.yaml`);
- inbox #91.

The reviewers were `code-reviewer` and `security-reviewer`, independent and in parallel. Format: [`README.md`](../README.md). The behaviour is owned by the ui-spec notes "UI parity A" of 2026-10-31 in [§4.2](../../specs/ui-spec.md#42-overview), [§4.3](../../specs/ui-spec.md#43-runs-table-and-rows) and [§4.4](../../specs/ui-spec.md#44-run-detail). The docs commit wrote them.

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `76466b0` (the step, with the shots and inbox #91) | **approve** (9 minors, 4 simplify) | **approve** (1 minor) |
| 2 | `ac5ae2c` (the `q` filter in the URL, All runs, the log tail, Download) | **approve** (2 minors) | **approve** (none) |
| simplify | `a55c74d`, `7a4811c` | `code-simplifier`: changed, −12 +8 | |

The coordinator relayed the reports in summary. **Finding IDs restart in each round**, so this record writes the round after an ID that repeats: CR-P3PARA-09 (r1) and (r2) are two different findings, and so are CR-P3PARA-10 (r1) and (r2).

**Test-first.** The worker reports that each round-1 fix in `ac5ae2c` came with a new test, and that each test was seen to fail before the fix. `doc-writer` checked this again. With `RunsPage.tsx`, `HomePage.tsx` and `RunDetailPage.tsx` put back to their `76466b0` versions, the five new or changed tests fail, and they pass on the code head ([P3-M4 Evidence](../../progress/W5/P3-M4.md#ui-parity-a-the-shell-home-the-runs-list-and-the-run-detail_1)).

Gate at `7a4811c`, from the worktree, re-run by `doc-writer`:

```bash
uv run --locked pytest -q             # 511 passed, 15 deselected
uv run --locked ruff check .          # All checks passed!
uv run --locked ruff format --check . # 82 files already formatted
uv run --locked mypy packages         # Success: no issues found in 81 source files
uv run --locked lint-imports          # Contracts: 4 kept, 0 broken.
uv lock --check                       # Resolved 55 packages
cd web && npx vitest run              # 12 files, 89 tests passed
cd web && npx tsc --noEmit            # no output, exit 0
cd web && npx vite build              # dist/index.html, two logo PNGs, one CSS and one JS asset
```

```text
CODE  step=P3-parA  review=approve b/M/m=0/0/11  security=approve b/M/m=0/0/1  rounds=2  simplify=changed -12/+8  tests=pass
```

The counts add up the two rounds per reviewer. The four `simplify` findings (CR-P3PARA-10 to -13, r1) are not counted.

## Findings

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3PARA-01 (r1) | minor | UX-PAR-12: only the state filter was kept in the URL, not the name filter `q`, and no owner was named for the rest. | fixed in `ac5ae2c`: `runsSearch` accepts a non-empty `q`. The 250 ms debounce and the state buttons both go through one `setSearch`, which merges into the current search, so a click during the wait keeps the other value. Test: open `/runs?state=failed&q=sar`, type, switch the filter, clear the box |
| CR-P3PARA-02 (r1) | minor | Home's "All runs" link went to `/runs?state=active`, so its label and its target disagreed. | fixed in `ac5ae2c`: it goes to `/runs`. The Home test checks `href="/runs"` |
| CR-P3PARA-03 (r1) | minor | The Pipeline fact in the header shows no mark. The lite board and UX-323 show the pipeline mark beside the name, and rule (a) of inbox #91 still allows the engine mark there. | **open**: follow-up FU-P3-25 |
| CR-P3PARA-04 (r1) | minor | The log tail read "Empty so far." on runs that had ended, and had no level tint, unlike the Logs tab. | fixed in `ac5ae2c`, in part. The tail reads "Empty." once the run has ended. Its lines get `data-tone` through the shared `LogLines`. **But no colour shows:** `runs.css` colours `span[data-tone]` only under `.sp-log`, and the tail is `.sp-code.sp-log-tail`. The test checks the attribute, not the colour. Found by `doc-writer` and `diagram-artist` while writing the docs. **Open**: follow-up FU-P3-25 |
| CR-P3PARA-05 (r1) | minor | `rail.test.tsx` passes only because of the order of the rules in the file: jsdom's `getComputedStyle` ignores specificity. The `.sp-ended` rail rows are not covered. | **open**: follow-up FU-P3-25 |
| CR-P3PARA-06 (r1) | minor | `theme.ts` adds the role tokens `code-text`, `code-failed` (`#F59A9A`), `code-review` (`#F5C779`) and `surface-mark` (`#FFFFFF`). None of the four is in `design/tokens/spectio-tokens.css`, so the app and the token source drift apart. | **open**: follow-up FU-P3-25 |
| CR-P3PARA-07 (r1) | minor | Some accessible names use Nextflow words on Snakemake runs: the chips list "Tasks by state", the table "Tasks" and the group "Show tasks". `words(engine)` exists for this. | **open**: follow-up FU-P3-25 |
| CR-P3PARA-08 (r1) | minor | Download clicked an anchor that was not on the page and revoked the object URL at once. Firefox and some Safari versions can drop such a download. | fixed in `ac5ae2c`: the anchor is appended to `document.body`, clicked and removed, and `URL.revokeObjectURL` runs in `setTimeout(…, 0)`. Test: the anchor is on the page at the click and gone afterwards, and the URL is revoked only after the click |
| CR-P3PARA-09 (r1) | minor | `tools/media/shots.py` reads `SPECTIO_DEMO_FAILED_RUN` for `app-run-detail-failed`, but `tools/media/README.md` does not document it. | fixed by the docs commit: the README names the variable and how to make the run |
| CR-P3PARA-10 (r1) | simplify | The `.sp-section h2` and `.sp-section > a` rules match nothing: `FoldSection` replaced every `sp-section`. | fixed in `a55c74d` by `code-simplifier` |
| CR-P3PARA-11 (r1) | simplify | The local `sum` helper was defined twice. | fixed in `7a4811c` by `code-simplifier`: one exported `sum` in `stateWord.ts` replaces three copies (the third was the private `n`) |
| CR-P3PARA-12 (r1) | simplify | `WhyItFailed` works out the failure class and message itself, which repeats `failureText(run)`. | left by `code-simplifier`: `WhyItFailed` needs three separate pieces, and a shared `{kind, message}` helper would remove about as many lines as it adds. Follow-up FU-P3-25 |
| CR-P3PARA-13 (r1) | simplify | The `TONES` map mixes state keys with English display words ("Done", "Stopped", "Not run", "Running"), so a change of wording would silently lose the colour. | left by `code-simplifier`: the fix changes the stage and process callers and the `tone("Done")` test in `rail.test.tsx`. Follow-up FU-P3-25 |
| SEC-P3PARA-01 (r1) | minor | "Open the head by hand" builds shell commands for the user to copy from server values, unquoted: `ssh ${head.node}`, `tmux attach -t ${head.session}`, `ps -o pid,etime,args --sid ${pid}`. Today the server sets them (the host name, and `head_native_id`, `store/runs.py:126`), and the card shows only for runs Spectio launched (`cli-observed` runs are excluded). A node name that starts with `-`, or a session name with shell metacharacters, from a future runner, config or imported record, would be an injection that the user pastes. | **open**: follow-up FU-P3-25, before the commands can come from anything but this server's own runner (P1 Task 10 at the latest, which adds tmux heads) |
| CR-P3PARA-09 (r2) | minor | Now that `q` is in the URL, the search box can show text that no longer filters the list. On `/runs?q=sar`, the sidebar or top-bar Runs link (`to="/runs"`) drops `q`, but `typed` was seeded once by `useState(q)` and stays "sar" over the full list. | **open**: follow-up FU-P3-25 |
| CR-P3PARA-10 (r2) | minor | The Download test replaces `URL.createObjectURL` and `URL.revokeObjectURL` with `Object.assign` and never restores them. Every later test in the file runs with the stubs. | **open**: follow-up FU-P3-25 |

## Fixes by round

| Commit | Findings |
|---|---|
| `ac5ae2c` fix(web): P3-parA post-approval review fixes (CR-P3PARA-01/02/04/08) | CR-P3PARA-01 (r1), CR-P3PARA-02 (r1), CR-P3PARA-04 (r1) (the tint in part), CR-P3PARA-08 (r1) |
| `a55c74d` refactor(P3-parA): simplify runs.css, drop the orphaned .sp-section selectors | CR-P3PARA-10 (r1) |
| `7a4811c` refactor(P3-parA): simplify the task-count sum, one helper instead of three | CR-P3PARA-11 (r1) |
| the docs commit | CR-P3PARA-09 (r1) |

`code-simplifier` ran the step's check command before and after its changes (pytest 511 passed, ruff, format, mypy, lint-imports, `uv lock --check`), and the web checks (vitest 89 of 89, `tsc --noEmit`, `vite build`). It got the same results each time.

## For the Progress page

The parity A section of P3-M4 is written: [P3-M4 · UI parity A](../../progress/W5/P3-M4.md#ui-parity-a-the-shell-home-the-runs-list-and-the-run-detail), with its [findings and open questions](../../progress/W5/P3-M4.md#findings-and-open-questions).
