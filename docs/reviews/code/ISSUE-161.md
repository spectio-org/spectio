# Code review · issue #161, runs that target one module or one rule

The `review-code` passes on PR [#255](https://github.com/spectio-org/spectio/pull/255), branch `claude/module-run-161`, 2026-11-11. They are in two parts:
- the web redesign, with prefixes `SEC-161W-` and `CR-161R-`;
- the server, runner and bridges, with prefixes `SEC-161S-` and `CR-161S-`, reviewed against the merge base with `main`.

Owning specs: [api §5.10](../../specs/api-and-data-model.md#510-run-target-one-module-or-one-rule-002), [ui-spec §4.15](../../specs/ui-spec.md#415-runs-that-target-one-module-or-one-rule-002), [architecture §13.8](../../specs/architecture-plugins-and-packaging.md#138-runs-started-from-a-terminal), and [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 16 and 21. Progress page: [ISSUE-161](../../progress/W5/ISSUE-161.md). Format: [`README.md`](../README.md).

```text
CODE  step=ISSUE-161/web     review=approve b/M/m=0/0/4 (round 2; round 1 changes 0/1/9)  security=approve b/M/m=0/0/2 (round 2; round 1 changes 0/1/3)  rounds=2
CODE  step=ISSUE-161/server  review=changes b/M/m=0/3/17 (round 1)  security=block b/M/m=1/2/10 (round 1)  rounds=1, round 2 running
```

## Web redesign (`6a6244c..915f48e`, fixes to `d907d27`)

| Id | Severity | Finding | Status |
|---|---|---|---|
| SEC-161W-01 / CR-161R-01 | major | for a module, the Profile select was hidden but its value was still sent | fixed in `512f551`: the select is shown for a module too; tests in `LaunchTarget.test.tsx` |
| SEC-161W-02 / CR-161R-03 | minor | an unknown target kind or flag crashed the badge | fixed in `512f551`, own keys only in `137e217` (SEC-161W-R2-01); tests in `target.test.tsx` |
| SEC-161W-03 | minor | the checksum could be copied without being shown | fixed in `512f551`: shown and copied only when it is 64 hex characters, otherwise "checksum: not valid" |
| SEC-161W-04 | minor | a copy of a Snakemake file-target run opened as a Nextflow module | fixed in `512f551`; the test fails without the fix |
| CR-161R-02 | minor | ui-spec §4.15 did not match the module card's chips | fixed in `8340181` |
| CR-161R-04 | minor | the steps arrow was read aloud | fixed in `8340181` (`content: "→" / ""`) |
| CR-161R-05 | minor | no arrow keys between the rule radios | follow-up, recorded in ui-spec §4.15 |
| CR-161R-06 | minor | One step: a missing Snakefile pointed at the hidden engine buttons | fixed in `8340181`, tested in `d907d27` (CR-161R2-02) |
| CR-161R-07 | minor | a module copy's missing `config_file` and the shown profile were untested | tests added in `8340181` |
| CR-161R-08 to -10 | minor (simplify) | nine repeats of the module check, a stale JSDoc, the kind label not read from `SCOPES` | fixed in `8340181` |
| SEC-161W-R2-01 | minor | lookups read inherited keys (`toString`, `__proto__`) | fixed in `137e217`, tested |
| SEC-161W-R2-02 | minor | a copied profile that is not in the pipeline vanished from the select | fixed in `137e217`: "(not in this pipeline)" |
| CR-161R2-01 | minor | a file-target copy silently dropped its target | fixed in `d907d27`: the spec says so, and the test checks for "Choose a rule" |
| CR-161R2-02 | minor | the CR-161R-06 fix had no test | fixed in `d907d27` |
| CR-161R2-03 | minor | an upper-case checksum showed as "not valid" | fixed in `d907d27` (case-insensitive) |
| CR-161R2-04 | minor (simplify) | leftover brackets around `oneModule` | fixed in `d907d27` |

## Server, runner and bridges (`498e8c0..f18c218`, fixes `dafaabd`, `f0bfaad`, `2e855d9`)

| Id | Severity | Finding | Status |
|---|---|---|---|
| SEC-161S-01 | blocker | a local `meta.yml` was parsed with YAML aliases allowed (memory and CPU exhaustion), and deep nesting gave a 500 | fixed in `f0bfaad`: `workflows.load_yaml`, 422 on `workflow.location`; `module view` read as JSON; tests for aliases, nesting and trailing text |
| SEC-161S-02 | major | the launch template of a local module dropped its code-loading marks (req. 16) | fixed in `f0bfaad`: computed in the file pool; a 0777 module directory is flagged (tested) |
| SEC-161S-03 / CR-161S-03 | major | Resume and rebuild skipped the feature flag and the namespace allow-list; Resume kept the parent's local hash | fixed in `f0bfaad`: `require_flag`, `registry_module` and `name == location` again on Resume, a fresh read of a local module, a stricter rebuild; four tests |
| CR-161S-01 | major | nf-spectio decided registry or local from the name's shape and took the version from `-version` | fixed in `dafaabd`: `.module-info` decides, the version comes from `meta.yml`; no version means no checksum comparison. Checked under Groovy 3 only; the engine tests need Nextflow 26.04 or later |
| CR-161S-02 / SEC-161S-06 | major | `targets:inspect` read engine output with no bound | fixed in `f0bfaad`: `run_login(max_bytes=1 MiB)` kills the process group past the cap; at most two inspections at once, 503 otherwise; tested |
| SEC-161S-04 / CR-161S-14 | minor | short, attached and abbreviated stop flags passed the guard | fixed in `f0bfaad`; `--force` allowed again in `2e855d9`, because argparse takes an exact name first |
| SEC-161S-05 / CR-161S-06 | minor | module files were read by path (symlink race, FIFO hang, 500 on a permission error) | fixed in `f0bfaad`: `workflows._read` in the file pool, `workflows.local_dir` shared with `resolve`; a FIFO gives 422 (tested). Groovy `smallText` fixed in `dafaabd` |
| SEC-161S-07 | minor | targets reported by the bridges were not validated before they moved runs | fixed in `f0bfaad`: `projector.targets.fits`, counted as `target_refused`; eight cases |
| SEC-161S-08 | minor | the checksum comparison crossed projects | fixed in `f0bfaad`, tested with two projects |
| SEC-161S-09 | minor | Resume reused the parent's checksum; a reported version that differed from the pin was accepted | fixed in `f0bfaad`: the launch's target is kept and the mismatch is counted |
| SEC-161S-10 | minor | the runner and rebuild exempted any `source: registry` payload from the path rule | fixed in `f0bfaad`: `spectio_sdk.targets.from_registry(target, engine)` |
| SEC-161S-11 | minor | nf-spectio's `meta.yml` regex backtracked in cubic time | fixed in `dafaabd`: a line split |
| SEC-161S-12 | minor | control characters in a `meta.yml` name or version | fixed in `f0bfaad`: 422 (tested) |
| SEC-161S-13 | minor | the Snakemake inspect runs pipeline code before Launch, which §15.3 did not record | spec only: req. 21 added in `b22f3f3` |
| CR-161S-04, -07, -08, -09 | minor | unknown params allowed with no declared inputs; the launch template turned a file target into a rule; `target.name` ignored on a module; the `config_file` refusal came after the engine call | fixed in `f0bfaad`, with tests |
| CR-161S-05, -13, -18 | minor | a `moduleTarget` exception lost `onFlowCreate`; `path` was not cut; dead checks | fixed in `dafaabd` |
| CR-161S-10 | minor | `module view` JSON was parsed as YAML | fixed with SEC-161S-01 |
| CR-161S-11 | minor | the tests read their fixtures from `spikes/` | fixed in `f0bfaad`: `tests/fixtures/module-run/` |
| CR-161S-12 | minor | the spec named migration `0012`, and the docstring cited §5.9 | fixed in `b22f3f3` and `f0bfaad` |
| CR-161S-15 to -19 | minor (simplify) | an unused `label`, the `local_module` tuple, a repeated `module_source`, a split `if` | fixed in `f0bfaad`; `HASH` is kept and now used by `fits` |
| CR-161S-20 | minor (simplify) | `freeze` read stage sources for a target run | partly: skipped for a module only, because a rule target needs the Snakefile's rules to list the others as `not_needed` |

Seen by the worker and not changed here: PyYAML's parse time grows with the square of the flow nesting depth, for every caller of `load_yaml` (meta.yml reads are capped at 64 KiB); a resumed registry module run is named after `parent.workflow_name`; and `GET /runs/{id}` shows `nextflow run` as the command of a module run.
