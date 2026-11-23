# Code review · release-publish, the real PyPI publisher (0.0.1-rc1)

Branch `autopilot/release-publish`, base `4124268d`. First draft and fix round: Refract GLM workers (`rel-publish`, `rel-fix`), reviewed and finished by the orchestrator. Reviewers: `code-reviewer` and `security-reviewer`, one round each on `0996d8c9`, 2026-11-23. Format: [`README.md`](../README.md).

```text
CODE  step=REL-publish  review=changes->fixed b/M/m=2/2/6  security=block->fixed-in-code b/M/m=1/3/3  rounds=1  simplify=skipped  tests=partial
```

`tests=partial`: `uv lock --check` (both projects), `bash -n`, shellcheck, yamllint, zizmor, and `tools/release/wheel_contents.sh` on freshly built `spectio-sdk` and logger wheels pass locally. `tests/packaging/test_wheel.sh` needs Node, Java and Nextflow and runs in CI (`ci.yml`). The workflow itself only runs on a release tag.

## Findings

| ID | Severity | Finding | State |
|---|---|---|---|
| SEC-REL-01 | blocker | The in-workflow "tag on main" check is no security control; the environments allow every ref, two environments and the tag ruleset do not exist, `main` requires no check | code: the guards now fail the run and say they are not the control. Settings: [inbox #157](../inbox.md) (Thomas) |
| SEC-REL-02 | major | The `workflow_dispatch` `tag` input is not tied to `github.ref` | fixed: no input; a re-run is `gh workflow run pypi-publish.yml --ref vX.Y.Z`; every job requires a `v*` tag ref |
| SEC-REL-03 | minor | The build is not pinned to the event's commit | fixed: checkout `github.sha`; the tag must point at it; `.release-please-manifest.json` must carry the tag's version |
| SEC-REL-04 | major | `spectio-sdk` and `spectio-server` are not held on PyPI | open, Thomas: inbox #157 item 1 |
| SEC-REL-05 | major | The publish docs describe the placeholder workflow | fixed: `claim-package-names.md` §2.2 and §2.4, dev-env §12 and §15.2 notes |
| SEC-REL-06 | minor | twine and packaging ran in the job that writes the sums | fixed: both moved to `smoke`; the build comment says what the sums prove |
| SEC-REL-07 | minor | `setup-nextflow` installs its own Java 17 and gets `github.token` | Java fixed (`java-version: "21"`, separate setup-java removed); the token stays, open |
| CR-REL-01 | blocker | The release PR would fail `ci-ok`: `uv.lock` and `test_wheel.sh` hard-code 0.0.1 | fixed: `tools/release/set-version.sh` rewrites versions, pins and both locks in its own PR before `Release-As`; release-please `extra-files` reverted to `[]`; `test_wheel.sh` reads the version |
| CR-REL-02 | blocker | Environments as documented refuse a tag ref; two environments and two publishers are missing | open, Thomas: inbox #157 |
| CR-REL-03 | major | An rc from PyPI pulls the `spectio` 0.0.0 placeholder | fixed: `spectio==` and `spectio-sdk==` pins, kept by `set-version.sh` |
| CR-REL-04 | major | Docs still describe the placeholder workflow | fixed, with SEC-REL-05 |
| CR-REL-05 | minor | `package-manager-cache` is no setup-node v4.4.0 input | fixed |
| CR-REL-06 | minor | The logger published before the core, with no contents check | fixed: last in the order, `snakemake_logger_plugin_spectio.wheel.txt` |
| CR-REL-07 | minor | No upgrade-from-previous-release job; the logger's `VERSION` constant does not follow the package | open, follow-up |
| CR-REL-08 | minor | Manual dispatch no longer checks its ref | fixed with SEC-REL-02 |
| CR-REL-09 | minor | The branch was behind integration | fixed: integration merged in |
| CR-REL-10 | minor (simplify) | Three download steps in smoke | fixed: one step, `pattern: dist-*` |

## Assumptions

- The version moves in its own PR (`set-version.sh`), so CI checks the locks and `test_wheel.sh` before release-please tags. release-please then writes only `CHANGELOG.md` and the manifest.
- The workflow changes `.github/workflows/`: Thomas merges this PR.
