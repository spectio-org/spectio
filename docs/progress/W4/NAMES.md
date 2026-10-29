---
step: NAMES
wave: W4
status: running
pr: null
review: approve
review_score: 12/14
review_ref: "doc-reviewer 2026-10-29: changes 10/14 on 0ca035f, then approve 12/14 on 2433dc2 with three changes (applied in the final pass); code-reviewer and security-reviewer approve on 2433dc2; security-reviewer approve on 46888e0 with three minors, applied (docs/reviews/code/NAMES.md)"
---
# NAMES · Prepare the four package-name claims

!!! info "Running 2026-10-29 · branch `autopilot/pypi-name-claim` · Thomas: \"Pour PyPI, prépare-moi déjà ce qu'il faudrait faire dans un fichier ou sur le CI\" · nothing published, no token made, no workflow run · round 1 on `0ca035f`: code, security and doc changes, all applied · round 2 on `2433dc2`: code approve, security approve, doc approve 12/14, the remaining changes applied · round 3 on `46888e0`: security approve, three minors applied · open for Thomas: inbox #71 (agent deny rules), the placeholder version, the registry provider string, where the logger's catalogue page lives"

![NAMES figure: on the Nextflow registry, Thomas logs in through Seqera and claims nf-spectio with a provider; the claim waits in PENDING REVIEW until an admin approves it, and the approved claim should then hold the ID with no release, an inference from the docs. On PyPI, a pending publisher with owner spectio-org, repository spectio, workflow pypi-publish.yml and environment pypi-<project> holds nothing yet; Run workflow on main runs build, then smoke, then publish; only publish has id-token, and the token exchange creates the project before the 0.0.0 upload](../../assets/diagrams/name-claim_light.png#only-light)
![NAMES figure: on the Nextflow registry, Thomas logs in through Seqera and claims nf-spectio with a provider; the claim waits in PENDING REVIEW until an admin approves it, and the approved claim should then hold the ID with no release, an inference from the docs. On PyPI, a pending publisher with owner spectio-org, repository spectio, workflow pypi-publish.yml and environment pypi-<project> holds nothing yet; Run workflow on main runs build, then smoke, then publish; only publish has id-token, and the token exchange creates the project before the 0.0.0 upload](../../assets/diagrams/name-claim_dark.png#only-dark)

## What changed

- **`.github/workflows/pypi-publish.yml`, new:** started by hand, one project per run (`spectio`, `spectio-open`, `snakemake-logger-plugin-spectio`), three jobs:
    - `build`: only uv (checked against `UV_SHA256`) and the pinned `uv_build` backend run: `uv build`, the sha256 sums recorded as a job output, then `dist/` uploaded;
    - `smoke`: on a downloaded copy: `twine check --strict`, the wheel's file list against `wheel-contents.txt`, the wheel installed in a fresh venv and `tools/release/pypi-placeholders/smoke.py` run;
    - `publish`: needs both, only from `main`, in environment `pypi-<project>`, the only job with `id-token: write`; checks the downloaded files against the build job's sums and count, then uploads them with `pypa/gh-action-pypi-publish` v1.14.3 and `skip-existing`.
- **`tools/release/pypi-placeholders/`, new:** three working `0.0.0` packages (`uv_build==0.11.32`, MIT, `Repository` URL, no classifiers). `spectio` and `spectio-open` install a command with `--version`. `snakemake-logger-plugin-spectio` is a Snakemake logger that appends one JSON line per log event to `--logger-spectio-file` (default `spectio-events.jsonl`). It opens the file with `O_NOFOLLOW|O_NONBLOCK`, then refuses it unless `fstat` shows a regular file of the current user with one link, and sets it to 0600.
- **`dev/versions.env`:** `TWINE_VERSION=7.0.0`.
- **`.github/CODEOWNERS`:** `/tools/release/` is code-owned.
- **Guide, new:** [Claim the package names](../../developer/claim-package-names.md): the registry claim, `main` protection and the GitHub environments, the pending publishers, the run, the manual fallback, open points.
- **Spec:** [dev-env §12](../../specs/dev-environment-and-testing.md#12-versioning-and-releases) Publishing: FC-314 to FC-317.
- **Records:** the [name-claim verification](../../reviews/verification-2026-10-29-names.md), the [review record](../../reviews/code/NAMES.md), a [decision-log entry](../../decisions/log.md#2026-10-29-how-the-four-package-names-are-held), a status line on [inbox #66](../../reviews/inbox.md#66-claim-the-four-package-names-and-confirm-how-the-bridges-are-released) and a new [inbox #71](../../reviews/inbox.md#71-deny-agent-sessions-the-commands-that-start-or-approve-a-publish).

## Why

Thomas, 2026-10-29: "Comment faire pour réserver ces 4 noms de paquets? … Pour PyPI, prépare-moi déjà ce qu'il faudrait faire dans un fichier ou sur le CI. Puis je préparerai ceci moi-même sur le site." The fact-check found that a PyPI pending publisher holds nothing until it is used, so the preparation is a workflow Thomas runs right after adding each publisher, plus packages that do something real (PEP 541).

## How to test it

From the repository root, for one project (`smoke.py` needs the wheel installed):

```bash
uv build --out-dir /tmp/d tools/release/pypi-placeholders/snakemake-logger-plugin-spectio
uv venv /tmp/v && uv pip install --python /tmp/v/bin/python /tmp/d/*.whl
/tmp/v/bin/python tools/release/pypi-placeholders/smoke.py snakemake-logger-plugin-spectio
```

## Evidence

- **Jobs replayed locally** (every `run:` block of the three jobs, in order): all steps exit 0 for the three projects, with `twine check` PASSED on each wheel and sdist and `smoke: <project> ok`; `publish`'s check passes on the build job's sums; `bogus` stops at `::error::Unknown project: bogus`. An extra line in `wheel-contents.txt` fails the smoke job's `diff`. A byte appended to the wheel after the sums fails `publish`'s `sha256sum --check` (`FAILED`, `1 computed checksum did NOT match`); an extra wheel added to `dist/` fails its count.
- **Smoke, logger** (`smoke.py`): one event written as valid JSON; refused: a symlinked path (target untouched), a FIFO (`ENXIO`, no hang), a second hard link, a file of another user; tightened: an existing 0666 file of ours ends at 0600; no settings object: the default `spectio-events.jsonl` in the working directory. The other-user case patches `os.getuid` to return another uid, since the test runs without root.
- **The checks are live:** each of four mutants of the installed module fails `smoke.py`, with the assertion that names it. The mutants drop the uid check, drop the link-count check, replace `fchmod` with `pass`, or drop `O_NONBLOCK` (the FIFO open then blocks until the 5 s guard fires: "opening a FIFO log file blocked").
- **Settings can be None?** Through the CLI, no: snakemake 9.27.1 builds one settings object per `--logger` (`snakemake/cli.py:2085-2088`), and `get_settings` returns an instance filled from the dataclass defaults when no flag is given (snakemake-interface-common 1.23.0 `plugin_registry/plugin.py:223-231`). The interface types the argument `Optional[LogHandlerSettingsBase]` (snakemake-interface-logger-plugins 2.1.0 `base.py:19`), so an API caller may pass None; the handler then uses `LogHandlerSettings()`.
- **Real Snakemake runs** (snakemake 9.27.1, a one-rule Snakefile):
    - `--logger spectio --logger-spectio-file events.jsonl` exits 0 and writes 14 valid JSON lines (`workflow_started`, `run_info`, `job_started`, `job_info`, `job_finished`, `progress`, `resources_info`), mode `600`;
    - `--logger spectio` with no flag writes 14 lines to `spectio-events.jsonl`;
    - with `events.jsonl` a symlink to a missing file, the run stops with `OSError: [Errno 40] Too many levels of symbolic links`, and the target is not created.
    - an existing 0666 `loose.jsonl` exits 0 and ends at mode `600`; a second hard link to the log file stops the run with `PermissionError: refusing …: not a regular file of ours with one link`;
    - a FIFO at `fifo.jsonl` stops the run in under a second with `OSError: [Errno 6] No such device or address`.
- **setup-uv checksum:** `UV_SHA256` in `dev/versions.env` equals the `uv-x86_64-unknown-linux-gnu.tar.gz.sha256` the uv 0.11.32 release publishes; setup-uv v6.8.0 declares `checksum` (`action.yml:21-23`) and its built-in list stops at 0.8.20.
- **Linters:** actionlint (the repo's pinned binary, with shellcheck): clean. zizmor 1.31.1 `--offline --min-severity low`: no findings. The online audits need a token and run in CI.
- **Docs:** `python3 tools/docs/check.py --base origin/autopilot/integration` and `mkdocs build --strict`: see the PR's Checks.

**Review** ([record](../../reviews/code/NAMES.md)):

- Round 1, on `0ca035f`: `code-reviewer` changes (0/1/4), `security-reviewer` changes (0/1/5), `doc-reviewer` changes 10/14; all applied.
- Round 2, on `2433dc2`: all three approve (doc 12/14); the minors applied, CR-008 accepted.
- Round 3, on `46888e0`: `security-reviewer` approve (0/0/3): SEC-4b, SEC-7b, SEC-8, all applied.
- No `code-simplifier` pass: the simplify findings CR-005 to CR-007 were applied by hand.

```text
CODE  step=NAMES  review=approve b/M/m=0/0/4  security=approve b/M/m=0/0/3  rounds=3  simplify=CR-005,CR-006,CR-007 by hand  tests=pass
```

## Figures and media

- `name-claim` (light and dark), drawn by `tools/diagrams/name_claim.py`. It shows the two ways a name is held: the registry claim, and the PyPI pending publisher followed by the build, smoke and publish jobs. Both PNGs were looked at after each render.
- No screenshots or casts: nothing in this step has a screen.

## Findings and open questions

- FC-314 to FC-317 ([verification](../../reviews/verification-2026-10-29-names.md)): applied to dev-env §12.
- CR-001 to CR-009, SEC-1 to SEC-8 (with SEC-1b, SEC-4b, SEC-7b) and the doc reviews ([review record](../../reviews/code/NAMES.md)): applied, except SEC-1's permission part, now [inbox #71](../../reviews/inbox.md#71-deny-agent-sessions-the-commands-that-start-or-approve-a-publish).
- Open for Thomas: inbox #71; the placeholder version (`0.0.0` proposed); the registry provider string; where the logger's catalogue page lives (verification, open point 9).
