# Code review · NAMES, the PyPI name-claim workflow and packages

Branch `autopilot/pypi-name-claim`, range `925ddb0..0ca035f` (first round), 2026-10-29. `code-reviewer`, `security-reviewer` and `doc-reviewer` ran in parallel on `0ca035f`; the coordinator accepted every finding. The code fixes are in `ce2f660`; the docs fixes are in the commit after it. No `code-simplifier` pass: CR-005, the reviewer's simplify finding, was applied by hand. The step's page is [Progress · NAMES](../../progress/W4/NAMES.md).

```text
CODE  step=NAMES  review=changes b/M/m=0/1/4  security=changes b/M/m=0/1/5  rounds=1  simplify=CR-005 by hand  tests=pass
```

| Pass | Round 1 (HEAD `0ca035f`) |
|---|---|
| `code-reviewer` | changes, b/M/m = 0/1/4 (one simplify) |
| `security-reviewer` | changes, b/M/m = 0/1/5 |
| `doc-reviewer` | changes, 10/14, six required changes; re-review pending |

Tests after the fixes: the shell of all three jobs replayed locally for each project (and `bogus` refused); `smoke.py` for each project; a one-rule Snakefile with `--logger spectio` on snakemake 9.27.1; the negative checks (an invalid classifier, a wrong wheel list, a changed file under its recorded sum, a symlinked log file) each fail as expected. Details on the [Progress page](../../progress/W4/NAMES.md#evidence).

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
| SEC-1 | major | The required-reviewer gate is not independent of admins or of the agents | guide §2.2: admin bypass unticked on each `pypi-*` environment, no agent credential as reviewer or admin. **Open, Thomas:** the proposed `.claude/settings.json` deny rules for `gh workflow run`, `gh api …/pending_deployments`, `gh api …/dispatches` and `gh run rerun` are a permission change only Thomas may make (guide §4) |
| SEC-2 | minor | A missing or misnamed environment publishes with no protection | applied: `publish` runs only when `github.ref == 'refs/heads/main'` (`ce2f660`); the guide §2.2 quotes GitHub ("will create an environment … not have any protection rules") and has Thomas create and check the three environments before the first run |
| SEC-3 | minor | The published package sources are not code-owned, and `main` is unprotected | applied: `/tools/release/ @weber8thomas` in `.github/CODEOWNERS` (`ce2f660`); branch protection on `main` with code-owner review is a prerequisite in the guide §2.2 (autopilot §8, inbox #8) |
| SEC-4 | minor | The smoke test ran third-party code in the job that produces the artifact | applied (`ce2f660`): `build` records the sums and uploads `dist/` before installing any checker; `smoke` and `publish` check the sums (from the output of the build step itself) and the file count; twine, trove-classifiers, setup-uv's uv and the `uv_build` backend are pinned; the wheel's file list is compared with `wheel-contents.txt` |
| SEC-5 | minor | The logger followed symlinks and created its file with umask permissions | applied (`ce2f660`): `os.open(…, O_WRONLY|O_APPEND|O_CREAT|O_NOFOLLOW, 0o600)`; `smoke.py` checks that a symlinked path is refused and its target untouched; a real Snakemake run on a symlinked `--logger-spectio-file` stops with `OSError: [Errno 40]` and creates nothing |
| SEC-6 | minor | The manual fallback left an account-wide token where it can leak | applied: the guide §2.5 enters the token only at twine's password prompt, never on the command line or in a file, uploads all three in one sitting and revokes the token at once |

## Doc review (1 to 6)

| Id | Finding | Status |
|---|---|---|
| 1 | `Framework :: Snakemake` is not a trove classifier; warehouse `forklift/metadata.py:239-242` refuses the upload | applied (`ce2f660`): removed; the build job checks every classifier against `trove-classifiers==2026.9.21.13` |
| 2 | The fallback commands fail as written | applied with CR-002 |
| 3 | "The placeholder has both" is false for `docs/intro.md` | applied with CR-001 |
| 4 | A build-kind change needs a Progress page, a `CODE` line and this record | applied: this record, [Progress · NAMES](../../progress/W4/NAMES.md), the PR body's Checks |
| 5 | The GitHub facts in §2.2 were unsourced, and the path to `main` unstated | applied: three GitHub docs pages read 2026-10-29, quoted; the PR targets `autopilot/integration`, so the workflow reaches `main` through the promotion PR |
| 6 | "An approved claim holds the ID" is an inference | applied: worded as an inference from `plugin-registry.mdx:16` and `gradle-plugin.mdx:109-111` in the guide, dev-env §12 and the decision log; refusal of a second claimant is not stated |
