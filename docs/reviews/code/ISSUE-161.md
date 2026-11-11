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

### Round 2 (`e11c029`, fixes `1863ee4`)

code-reviewer approved with 9 minors; security-reviewer asked for changes (1 major, 4 minors), so a third round runs on `e11c029..1863ee4`.

| Id | Severity | Finding | Status |
|---|---|---|---|
| SEC-161S2-01 | major | deep flow nesting in a local `meta.yml` made `load_yaml` take minutes (PyYAML's parse time grows with the square of the depth) while it held a file-pool thread | fixed in `1863ee4`: a linear bracket count refuses past 64 before PyYAML parses; `meta.yml` read up to 64 KiB; 60 000 `[` refused in under 1 s (tested) |
| SEC-161S2-02 / CR-161S2-01 | minor | grouped short stop flags (`-pU merge`, `-nRx`) passed the rule-target guard | fixed in `1863ee4`: a single-dash cluster with `U`, `O` or `R` is refused; four cases added. A Snakemake profile that sets `until:` is not checked: recorded in api §5.10 |
| SEC-161S2-03 | minor | `POST /runs` of a registry module ran `module view` outside the two-slot bound | fixed in `1863ee4`: `targets.bounded` wraps every engine call; tested with both slots held (503, no engine call) |
| SEC-161S2-04 | minor | `local_dir` stat the location outside the file pool | fixed in `1863ee4`: inside the pooled read, for Launch and Resume |
| SEC-161S2-05 | minor | a non-UTF-8 `meta.yml` gave a 422 that quoted the decoder's bytes | fixed in `1863ee4`: "main.nf or meta.yml is not UTF-8 text" (tested) |
| CR-161S2-02 | minor | a reported registry target with no checksum was accepted | fixed in `1863ee4`: required; `nohash` case added |
| CR-161S2-03 | minor | comparing the version could drop the checksum of every launched registry run whose `meta.yml` names the version otherwise **[to be validated]** | fixed in `1863ee4`: compared by name and source; the pin is kept, the hash added (tested) |
| CR-161S2-04 | minor | nf-spectio sent a local module's path as found | fixed in `1863ee4`: absolute and normalised |
| CR-161S2-05 | minor | `target_refused` missing from the api §14.1 drop table | fixed in `1863ee4` |
| CR-161S2-06 | minor | cap tests allowed one extra chunk and any non-zero code | fixed in `1863ee4`: `rc == 125`, output within the cap |
| CR-161S2-07 | minor (simplify) | two tests of the options a rule target keeps | merged in `1863ee4` |
| CR-161S2-08 | minor (simplify) | `run_login` keeps two read paths | not changed: the uncapped path serves every other login call |
| CR-161S2-09 | minor (simplify) | `launch_template` repeated the pool's 503 and a `None` check | fixed in `1863ee4`: `pooled` |

### Round 3 (`1863ee4`, fixes `85a60d7`, `07402d8`)

code-reviewer approved with 5 minors; security-reviewer asked for changes (1 major, 3 minors): the bracket count of round 2 could be fooled. A fourth round runs on `1863ee4..07402d8`.

| Id | Severity | Finding | Status |
|---|---|---|---|
| SEC-161S3-01 | major | quoted closers (`[']',` × 10 900) hid the flow depth from the bracket count: 7 s for a 64 KiB `meta.yml`, 27 s for a 256 KiB params file, each holding a file-pool thread and the GIL | fixed in `07402d8`: `workflows._Loader` refuses in PyYAML's scanner once `flow_level` reaches 64, and refuses aliases while composing, in one pass; both quote shapes refused in under 1 s (tested), and a 256 KiB params file too |
| SEC-161S3-02 | minor | a head that reported another version had its checksum stored as the pin's, so `checksum_changed` could fire for nothing | fixed in `07402d8`: the pin is kept, no checksum, counted `target_version_differs` (api §14.1). This supersedes the CR-161S2-03 fix: the difference is counted, neither accepted nor dropped silently |
| SEC-161S3-03 | minor | Snakemake `targets:inspect` checked the directory in the request thread, and its Git fetch lost the route's bound | fixed in `07402d8`: a local directory in the file pool, a Git fetch under the inspection slots |
| SEC-161S3-04 | minor (before #161) | `workflows:inspect` quoted PyYAML's message, the file's failing line, in its 422 | fixed in `07402d8`: "not YAML" or "not UTF-8 text"; the test fails without the fix |
| CR-161S3-01 | minor | the guard also refuses a short cluster whose attached value holds `U`, `O` or `R` (`-d/scratch/RUN1`), which the spec did not say | spec in `85a60d7`: refused whole, the safe direction |
| CR-161S3-02 | minor | the round-2 bound made a deep params file "not YAML" instead of "nested too deep" | fixed in `85a60d7` (`RecursionError`); `test_catalog` now expects "too deep" for `conf/nested.yaml`, as for its JSON twin |
| CR-161S3-03 | minor | the spec named the 503 for `targets:inspect` only | fixed in `85a60d7`: also `POST /runs` of a registry module |
| CR-161S3-04 | minor | req. 21 caps `main.nf` at 64 KiB; the code capped `meta.yml` only | fixed in `85a60d7` |
| CR-161S3-05 | minor (simplify) | `launch_template` repeated the module check | fixed in `85a60d7`: narrowed once |

### Round 4 (`1863ee4..07402d8`, fixes `c00f7a8`)

code-reviewer approved with 5 minors; security-reviewer asked for changes (1 major, 3 minors).

| Id | Severity | Finding | Status |
|---|---|---|---|
| SEC-161S4-01 | major | YAML 1.1 sexagesimal integers (`1:59:59…`) convert in quadratic time: 1.9 s at 256 KiB, 29.9 s for a 1 MiB `config.yaml` through `inspect_dir` | fixed in `c00f7a8`: `_Loader` refuses a number over 128 characters before converting, `SafeLoader` unchanged (tested) |
| SEC-161S4-02 | minor | a 600-byte sexagesimal float raised `OverflowError`, a 500 | fixed in `c00f7a8` by the 128-character cap; the `OverflowError` branch is defence in depth (CR-161S5-02) |
| SEC-161S4-03 | minor | a Git fetch held an engine slot for up to about 900 s | fixed in `c00f7a8`: its own `FETCHES` slots (tested) |
| SEC-161S4-04 | minor (before #161) | inspect parsed up to 1 MiB of YAML in the request thread, about 5 s | fixed in `c00f7a8`: 256 KiB; amended in round 5 (CR-161S5-01) |
| CR-161S4-01 | minor | the Snakemake slot path had no test | fixed in `c00f7a8`; the test was vacuous in part (CR-161S5-03) |
| CR-161S4-02 | minor | the `main.nf` cap had no test | fixed in `c00f7a8` |
| CR-161S4-03 | minor | §5.10 Checksum paragraph did not name `target_version_differs` | fixed in `c00f7a8` |
| CR-161S4-04 | minor (simplify) | `MAX_META_YML` also capped `main.nf` | renamed `MAX_MODULE_FILE` in `c00f7a8` |
| CR-161S4-05 | minor | the `_Loader` docstring claimed every caller says "nested too deep" | reworded in `c00f7a8` |

### Round 5 (`07402d8..c00f7a8`, fixes `1766e6c`)

Both asked for changes: code-reviewer 1 major, 3 minors; security-reviewer 2 majors, 4 minors. Since a security major was open, a sixth round runs on `c00f7a8..1766e6c`.

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-161S5-01 / SEC-161S5-06 | major | the 256 KiB cap refused a Snakemake pipeline whose `config.yaml` is larger, with no test, and api §5.4 and §5.6 still said 1 MiB | fixed in `1766e6c`: a larger `config.yaml` infers no form (`schema_source: none`) and the pipeline launches; a `config.schema.yaml` that large is still refused (tested); specs updated |
| SEC-161S5-01 | major | an explicit tag that SafeConstructor cannot build (`!!bool foo`, `!!int ''`, `!!timestamp foo`) raised `KeyError`, `IndexError` or `AttributeError`, a 500 | fixed in `1766e6c`: `load_yaml` turns them into a refusal (tested per shape) |
| SEC-161S5-02 | major | a lone surrogate (`"\ud800"`) passed parsing and failed when the response was encoded, a 500, through YAML, `nextflow_schema.json` or a `meta.yml` name | fixed in `1766e6c`: `_jsonable` refuses it; `nextflow_schema.json` and `module view` output go through it (tested) |
| SEC-161S5-03 | minor | `inspect_dir` showed constructor messages, which quote the value (`invalid literal for int()… 'TOKEN-abc123'`) | fixed in `1766e6c`: only `Unreadable` (the server's own words), `RecursionError` and JSON positions are shown (tested) |
| SEC-161S5-04 | minor | 63-deep flow bursts cost 3.5 to 4 s at 256 KiB | fixed in `1766e6c`: 131,072 tokens a file, about 1.8 s (tested under 4 s) |
| SEC-161S5-05 | minor | integer keys that collide in Python's hash make a mapping quadratic, 0.84 s at 256 KiB | accepted residual, recorded in req. 21 and the `_Loader` docstring |
| CR-161S5-02 | minor | the `OverflowError` branch is unreachable and its test wording said otherwise | `1766e6c`: kept as defence in depth with the tag errors; the test docstring says what it proves |
| CR-161S5-03 | minor | the fetch-slot test's launch assertion proved nothing | fixed in `1766e6c`: the fake fetch asserts both inspection slots are free |
| CR-161S5-04 | minor (simplify) | `_small_yaml` duplicated `_read`'s cap | fixed in `1766e6c`: `_read(…, cap=)` |
| (no id) | note | other routes still fetch Git without a slot; req. 21 now says the fetch slots bound `targets:inspect` only | spec in `1766e6c` |

### Round 6 (`c00f7a8..1766e6c`, fixes `de66920`, `0fa93d8`)

Both asked for changes: code-reviewer 1 major, 5 minors; security-reviewer 2 majors, 1 minor. A seventh round runs on the fixes, since a security major was open.

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-161S6-01 / SEC-161S6-01 | major | a `config.yaml` over 1 MiB was still refused: `_read` capped it at 1 MiB before the 256 KiB test | fixed in `de66920`: `TooLarge` (a subclass of `Unreadable`) from `_read` at 256 KiB gives `schema_source: none`; the size is checked before decoding, so a large non-UTF-8 config gives `none` too (tested at 290 KiB, 1.2 MiB and 300 KiB of non-UTF-8 bytes, each with a launch giving `201`, since CR-161S7-02) |
| SEC-161S6-02 | major (before #161) | a schema or config nested 250 to 990 levels passed parsing and failed when the response was encoded, a 500 | fixed in `0fa93d8`: `_object` refuses past 64 levels (tested for `nextflow_schema.json`, `config.schema.yaml` and `config.yaml`; each fails without the fix) |
| CR-161S6-02 | minor | the token budget could refuse a dense `config.yaml` under 256 KiB | fixed in `de66920`: the budget raises `TooLarge`, so the config gives `none` (tested) |
| CR-161S6-03 | minor | the catch-all said "not YAML" for JSON | fixed in `de66920`: "not JSON or YAML this server reads" |
| CR-161S6-04 | minor | the surrogate path of `module view` had no test | fixed in `de66920`: the same view gives `200`, with a lone surrogate `502` |
| CR-161S6-05 | minor | the large-config test never launched | fixed in `de66920`: `POST /runs` gives `201` |
| CR-161S6-06 | minor (simplify) | `_module_files` repeated `_read`'s cap | fixed in `de66920`: `_read(…, cap=MAX_MODULE_FILE)` |
| SEC-161S6-03 | minor (before #161, outside the range) | the ingest YAML readers of `stages/freeze.py` take no bound, and a bad tag's traceback reaches the log | not changed here: req. 21 now says it covers the request paths and names this as open; left as follow-up **FU-161-01**, named in the PR body: move `_Loader` to a shared module and use it in `freeze.py`, catch its refusals there, and log the exception type only |

### Round 7 (`1766e6c..0fa93d8`, fixes in the next commit)

Both approved: code-reviewer with 3 minors, all fixed below; security-reviewer with none (0/0/0): `TooLarge` hides no refusal it should not, and no path on the range answers 500 or quotes a pipeline file (about 25 probes).

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-161S7-01 | minor | the depth refusal also refused a `config.yaml` nested 65 to 250 levels, so its pipeline no longer launched | fixed: the depth bound raises `TooLarge`, so such a config infers no form and launches; a schema that deep is still a `422` (tested) |
| CR-161S7-02 | minor | the record claimed launches at 290 KiB and 1.2 MiB and a non-UTF-8 case that the test did not have | fixed: each config case launches (`201`), and 300 KiB of non-UTF-8 bytes is a case |
| CR-161S7-03 | minor | the `freeze.py` follow-up had no id | FU-161-01, in req. 21, this record and the PR body |

### Fix review (`2332f2d..d00353d`)

security-reviewer approved with one minor; code-reviewer: see below.

| Id | Severity | Finding | Status |
|---|---|---|---|
| SEC-161S8-01 | minor | the specs said any `config.yaml` past 64 levels infers no form; past about 250 block levels PyYAML's composer raises `RecursionError`, and past 64 flow brackets the scanner refuses, both a `422` that quotes nothing | spec reworded to the window (65 to about 250 block levels); the code fails closed |

Seen by the worker and not changed here: a resumed registry module run is named after `parent.workflow_name`; and `GET /runs/{id}` shows `nextflow run` as the command of a module run.
