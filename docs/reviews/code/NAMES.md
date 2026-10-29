# Code review · NAMES, the PyPI name-claim workflow and packages

Branch `autopilot/pypi-name-claim`, 2026-10-29. Two rounds. Round 1: `code-reviewer`, `security-reviewer` and `doc-reviewer` ran in parallel on `0ca035f` (range `925ddb0..0ca035f`); the coordinator accepted every finding, fixed in `ce2f660`, `1ad7e3e` and `44da735`. Round 2: the same three passes re-ran on `2433dc2`; all three approve, with minor findings that the final pass applies (below). No `code-simplifier` pass: the reviewer's simplify findings (CR-005, CR-006, CR-007) were applied by hand. The step's page is [Progress · NAMES](../../progress/W4/NAMES.md).

```text
CODE  step=NAMES  review=approve b/M/m=0/0/4  security=approve b/M/m=0/0/3  rounds=2  simplify=CR-005,CR-006,CR-007 by hand  tests=pass
```

| Pass | Round 1 (HEAD `0ca035f`) | Round 2 (HEAD `2433dc2`) |
|---|---|---|
| `code-reviewer` | changes, b/M/m = 0/1/4 (one simplify) | approve, b/M/m = 0/0/4 (two simplify): CR-006 to CR-009 |
| `security-reviewer` | changes, b/M/m = 0/1/5 | approve, b/M/m = 0/0/3: SEC-1b, SEC-7 and zizmor's pedantic "job has no `name:`"; plus a note on `settings` being `None` |
| `doc-reviewer` | changes, 10/14, six required changes | approve, 12/14, three changes |

Tests after the final pass: the shell of all three jobs replayed locally for each project (and `bogus` refused); `smoke.py` for each project, including the logger's refusals; a one-rule Snakefile with `--logger spectio` on snakemake 9.27.1; the negative checks (a wrong wheel list, a symlinked log file, and three mutants of the logger's checks) each fail as expected. Details on the [Progress page](../../progress/W4/NAMES.md#evidence).

## Code review (CR-001 to CR-005)

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-001 | major | The logger's `docs/intro.md` is never read: the Snakemake catalogue reads `docs/intro.md` at the root of the `Repository` URL (snakemake-plugin-catalog `collect_plugins.py:636-665` at `d2c11a2`), and three docs said the placeholder has it | applied: the file is removed (`ce2f660`); the guide §3, dev-env §12, the FC-317 evidence and status say where the catalogue reads it; where it should live in this monorepo is open point 9 of the [verification](../verification-2026-10-29-names.md) and a line in inbox #66 |
| CR-002 | minor | The manual fallback ran `twine` on a `dist/` that `uv build` never wrote | applied: `uv build --out-dir dist/<name>`, then `twine check` and `twine upload` on `dist/<name>/*` (guide §2.5) |
| CR-003 | minor | `twine` unpinned in the build job | applied (`ce2f660`): `TWINE_VERSION=7.0.0` in `dev/versions.env`, read by the job |
| CR-004 | minor | The logger smoke test only imported the module | applied (`ce2f660`): `smoke.py` builds a `LogHandler` with settings, emits one record and parses the line as JSON |
| CR-005 | minor (simplify) | The default file name was written twice | applied (`ce2f660`): `file: str = field(default="spectio-events.jsonl", …)`; `Optional` dropped |

## Security review (SEC-1 to SEC-6)

These IDs are local to this record (the security reviewer's numbering for this step), not the spec-wide `SEC-1xx` series.

| Id | Severity | Finding | Status |
|---|---|---|---|
| SEC-1 | major | The required-reviewer gate is not independent of admins or of the agents | guide §2.2: admin bypass unticked on each `pypi-*` environment, no agent credential as reviewer or admin. **Open, Thomas:** the proposed `.claude/settings.json` deny rules for `gh workflow run`, `gh api …/pending_deployments`, `gh api …/dispatches` and `gh run rerun` are a permission change only Thomas may make; see SEC-1b below and [inbox #71](../inbox.md#71-deny-agent-sessions-the-commands-that-start-or-approve-a-publish) |
| SEC-2 | minor | A missing or misnamed environment publishes with no protection | applied: `publish` runs only when `github.ref == 'refs/heads/main'` (`ce2f660`); the guide §2.2 quotes GitHub ("will create an environment … not have any protection rules") and has Thomas create and check the three environments before the first run |
| SEC-3 | minor | The published package sources are not code-owned, and `main` is unprotected | applied: `/tools/release/ @weber8thomas` in `.github/CODEOWNERS` (`ce2f660`); branch protection on `main` with code-owner review is a prerequisite in the guide §2.2 (autopilot §8, inbox #8) |
| SEC-4 | minor | The smoke test ran third-party code in the job that produces the artifact | applied, then simplified in round 2 (CR-006): `build` runs only checkout, uv and the pinned `uv_build` backend, then uploads `dist/`. Every checker (twine, the `wheel-contents.txt` diff, the smoke test) runs in `smoke`, on a downloaded copy that feeds nothing to `publish`. The round 1 sha256 hand-off is gone: the isolation holds without it, since an artifact name cannot be uploaded twice in a run and the job token is `contents: read` |
| SEC-5 | minor | The logger followed symlinks and created its file with umask permissions | applied (`ce2f660`): `os.open(…, O_WRONLY|O_APPEND|O_CREAT|O_NOFOLLOW, 0o600)`; `smoke.py` checks that a symlinked path is refused and its target untouched; a real Snakemake run on a symlinked `--logger-spectio-file` stops with `OSError: [Errno 40]` and creates nothing |
| SEC-6 | minor | The manual fallback left an account-wide token where it can leak | applied: the guide §2.5 enters the token only at twine's password prompt, never on the command line or in a file, uploads all three in one sitting and revokes the token at once |

## Doc review (1 to 6)

| Id | Finding | Status |
|---|---|---|
| 1 | `Framework :: Snakemake` is not a trove classifier; warehouse `forklift/metadata.py:239-242` refuses the upload | applied (`ce2f660`), then met another way in round 2 (CR-007): the three packages carry no classifiers at all, so the inline checker and the `trove-classifiers` pin are gone |
| 2 | The fallback commands fail as written | applied with CR-002 |
| 3 | "The placeholder has both" is false for `docs/intro.md` | applied with CR-001 |
| 4 | A build-kind change needs a Progress page, a `CODE` line and this record | applied: this record, [Progress · NAMES](../../progress/W4/NAMES.md), the PR body's Checks |
| 5 | The GitHub facts in §2.2 were unsourced, and the path to `main` unstated | applied: three GitHub docs pages read 2026-10-29, quoted; the PR targets `autopilot/integration`, so the workflow reaches `main` through the promotion PR |
| 6 | "An approved claim holds the ID" is an inference | applied: worded as an inference from `plugin-registry.mdx:16` and `gradle-plugin.mdx:109-111` in the guide, dev-env §12 and the decision log; refusal of a second claimant is not stated |

## Round 2 (HEAD `2433dc2`)

| Id | From | Severity | Finding | Status |
|---|---|---|---|---|
| CR-006 | code | minor (simplify) | The sha256 hand-off guards against what a simpler job split already prevents | applied: `build` is checkout, setup-uv, `uv build --out-dir dist`, upload; `twine check --strict` and the wheel-contents `diff` moved to `smoke`; the sums output, both sum checks, both file counts and the header comment dropped. `security-reviewer` agreed (SEC-4 above) |
| CR-007 | code | minor (simplify) | The inline classifier checker repeats PyPI's own upload check | applied: classifiers dropped from the three `pyproject.toml` files; the checker and `TROVE_CLASSIFIERS_VERSION` removed (doc #1 above) |
| CR-008 | code | minor | The uv version is written in five places with nothing to catch drift | accepted as is: the workflow is a one-shot name claim; no new tooling. Each copy says `= UV_VERSION in dev/versions.env` |
| CR-009 | code | minor | The inbox #66 status and the figure stated the Nextflow outcome as fact | applied: the figure reads "approved: the ID should be held" and draws `build → smoke → publish`, both PNGs re-rendered and opened; inbox #66 says the claim should hold the ID, inferred (guide §1) |
| SEC-1b | security | minor | The gate also fails if an agent session holds a token of the reviewer's account | applied: guide §2.2 says no agent session holds a token of the reviewer's account with `actions:write` or the right to approve deployments. The deny rules for `gh workflow run`, `gh api …pending_deployments`, `gh api …/dispatches` and `gh run rerun` are **open, Thomas:** [inbox #71](../inbox.md#71-deny-agent-sessions-the-commands-that-start-or-approve-a-publish), linked from guide §4 and the PR body |
| SEC-7 | security | minor | `O_NOFOLLOW` does not stop a hard link, or a pre-existing file with loose permissions or another owner | applied: after `os.open`, `os.fstat`; the handler refuses unless the file is regular, owned by `os.getuid()` and has `st_nlink == 1`, then `os.fchmod(fd, 0o600)`. `smoke.py` covers a hard link (refused), another owner (refused; checked by patching `os.getuid` to return the real uid + 1, since a test cannot create a file owned by someone else without root) and a pre-existing 0666 file (tightened to 0600). Three mutants (no uid check, no link check, no `fchmod`) each make `smoke.py` fail |
| zizmor pedantic | security | minor (informational) | The three jobs have no `name:` | accepted as is: the job ids `build`, `smoke` and `publish` already name them; zizmor's default persona reports nothing |
| settings `None` | security | note | Can `settings` be `None`? | yes, from an API caller only: `LogHandlerBase` types it `Optional[LogHandlerSettingsBase]` (snakemake-interface-logger-plugins 2.1.0 `base.py:19`); the CLI always passes an instance (snakemake 9.27.1 `cli.py:2085-2088`, built from the dataclass defaults by snakemake-interface-common 1.23.0 `plugin_registry/plugin.py:223-231`). Handled: `self.settings or LogHandlerSettings()`; `smoke.py` builds `LogHandler(None, None)` and checks the default file is written |
| doc 1 | docs | change | The figure and the inbox #66 status line | applied with CR-009; the Progress page's alt text says what the figure shows |
| doc 2 | docs | change | The Progress page lacks the §3.2 headings | applied: "Figures and media" and "Findings and open questions" |
| doc 3 | docs | change | The review state and verdicts are not recorded | applied: Progress front matter `review: approve`, `review_score: 12/14`; the approve verdicts in the `CODE` line above, here and in the PR body's Checks |
