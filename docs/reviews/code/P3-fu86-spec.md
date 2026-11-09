# Pre-review · FU-P3-86, environments (design only)

Step `P3-fu86-spec` on `autopilot/P3-fu86-spec`, base `3f9a7749`, 2026-11-09. The step writes the design of FU-P3-86 ([decision log](../../decisions/log.md#2026-11-09-environments-in-001-fu-p3-86-assumed), [inbox #133](../inbox.md#133-assumed-environments-local-slurm-define-a-new-one-fu-p3-86)); it changes no code, so `code-reviewer`, `code-simplifier` and the tests do not run.

There is no `CODE` line in this record: the step changes no code, so there is no code to review.

Reviewed sections:
- [api §5.4](../../specs/api-and-data-model.md#54-environments-001), new, and §4.1 (four problem slugs);
- [ui-spec §4.8.1](../../specs/ui-spec.md#481-environments-in-001), new;
- [dev-env §15.3](../../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 18, new, and §15.1, the Environments row.

## Rounds

| Round | Who | Independent | security | UX |
|---|---|---|---|---|
| R0 | the design worker, on the two agents' checklists | **no** | changes 0/3/9 | changes 0/1/11 |
| R1 | `security-reviewer` and `ux-reviewer`, run by the coordinator on the R0 design, in parallel | yes | **changes 0/2/10** | **changes 0/7/16** |

The R1 findings are all applied below, but UX-PRE-FU86-R1-21, deferred; the design in the specs is the one after R1.

## R0, self-review (not independent)

### How it ran

The design worker had no Agent tool, so it could not start `security-reviewer` and `ux-reviewer` as independent agents. It went through each agent's checklist itself (`.claude/agents/security-reviewer.md`: STRIDE on the browser ↔ server boundary and the server ↔ engine boundary, injection into engine arguments and configuration, files in the shared home, the listener; `.claude/agents/ux-reviewer.md`: states, accessibility, phone, data the API can serve, boards), against the code read for the design. No board was drawn or rendered: the boards are FU-P3-86e (FU-P3-86d before R1). **This review is not independent.** R1 below is the independent round.

Code read for the design: `spectio/config.py` (`Settings`, `SlurmOpts`, `check_config`, `write_config`), `spectio/cli/init.py`, `spectio/runner/loop.py` (the `LaunchSpec` built from `settings.executor`), `spectio/runner/headscript.py` (`engine_args`, `nextflow_config`, `_groovy`, `PROFILE`), `spectio/runner/rundir.py` (`RunManifest`), `spectio_server/app.py` (`no_api_reason`, `shared_host`), `serve.py`, `bootstrap.py` (`ensure_tenancy`), `store/schema.py` (`environments`, `runs.environment_id`), `api/runs_write.py`, `api/runs_read.py` (`GET /version`), `api/problems.py`, `static.py` (`ROUTES`), `web/src/launch/LaunchPage.tsx`, `web/src/runs/RunHeader.tsx`, `web/src/shell/Sidebar.tsx`, `TabBar.tsx`. Third-party sources read: Snakemake 9.27.1 `snakemake/resources.py:795-840` and `cli.py:557`, `:597`; `snakemake-executor-plugin-slurm` 2.8.0 `__init__.py`; the Nextflow configuration and executor-scope pages (2026-11-09).

### Security checklist (`security-reviewer`)

```text
SECURITY-REVIEW  verdict=changes  blockers=0  majors=3  minors=9
```

Every finding was applied to the design before the commit, except where the table says otherwise. The verdict is the verdict on the first draft.

| ID | Sev. | Finding | Applied |
|---|---|---|---|
| SEC-PRE-FU86-01 | major | Snakemake evaluates each `--default-resources` value as a Python expression after `os.path.expandvars`, keeping it as a string only on `NameError` or `SyntaxError` (9.27.1, `resources.py:801-825`; its namespace holds `shutil`). Today's `slurm_partition=<value>` is passed unquoted, from a `spectio.toml` field with no pattern; an environment written through the API would carry the same value. | yes: values passed as Python string literals (`slurm_partition='htc'`), the SLURM name pattern excludes quotes, backslashes and `$`, and `SlurmOpts` gains the pattern too (api §5.4, req. 18; FU-P3-86a, -86b) |
| SEC-PRE-FU86-02 | major | An environment that took free `clusterOptions`, extra engine arguments, a configuration file or environment variables would let whoever holds the session (or a page that rides it) set what every later launch submits, beyond the launch body's reviewed fields. | yes: typed fields only, each a name of a closed set or a bounded integer; free text never, named fields from an allow-list Later (req. 18, inbox #133 choice 3) |
| SEC-PRE-FU86-03 | major | Choosing an environment per run could be read as choosing the transport: if "local" opened TCP on a login node, the API would be reachable by every user of that node (one network namespace, [audit §2](../../research/2026-11-08-embl-login-node-audit.md#2-loopback-isolation)). | yes: the listener keys on the server's own kind and `shared_host()` only; a `slurm` environment exists only on a server set up with SLURM, already behind the socket (req. 18) |
| SEC-PRE-FU86-04 | minor | `environments.toml` in the shared home could be replaced by a symbolic link or made writable by others, steering launches. | yes: the `check_config` checks at every read, `O_NOFOLLOW`, `refused` state with only the built-ins listed |
| SEC-PRE-FU86-05 | minor | A server write over a file that was hand-edited, unsafe or invalid would hide tampering or lose the user's text. | yes: never overwritten when `refused` or `invalid`; a write checks the file's identity against its read (`409 environments-file-changed`) |
| SEC-PRE-FU86-06 | minor | The snapshot in a run's manifest is read back at rebuild and used by Resume; a run directory is untrusted input (req. 10). | yes: parsed with the routes' validators; "not readable" and Resume refused otherwise |
| SEC-PRE-FU86-07 | minor | A user-chosen name used in a path or a tmux session name would reopen req. 10 and 11. | yes: names appear in URLs, the file and the manifest only |
| SEC-PRE-FU86-08 | minor | Local tasks on a login node can take the user's whole cgroup slice on a machine others share. | yes: the built-in `local` of a SLURM server is capped at 2 CPUs and 8 GiB by default, and labelled; the cgroup stays the hard cap |
| SEC-PRE-FU86-09 | minor | Default profiles in an environment must not bypass the launch's `PROFILE` check. | yes: the same pattern; they only prefill the form, and the launch body is checked as today |
| SEC-PRE-FU86-10 | minor | The new write routes need the req. 7 checks and protection against two tabs overwriting each other. | yes: session, `Origin` and JSON checks; `If-Match` on `PUT` and `DELETE` |
| SEC-PRE-FU86-11 | minor | Labels are user text shown on several screens. | yes: no control or format characters, text nodes only |
| SEC-PRE-FU86-12 | minor | `process.clusterOptions = '--account=…'` replaces a pipeline's generic `clusterOptions`, and a selector's replaces the account: a correctness risk, not a boundary. | recorded, **[to be validated]** on nf-core/rnaseq; unchanged from today |

Checked and unchanged: everything runs as the server's Unix user; `account` is checked by `slurmctld` against the user's associations (`AccountingStorageEnforce = associations,limits,qos,safe`, [audit §1](../../research/2026-11-08-embl-login-node-audit.md#1-slurm)); the file holds no secret (0600 in a 0700 directory); no new subprocess (no `sinfo` or `sacctmgr` call in 0.0.1, inbox #133 choice 10).

### UX checklist (`ux-reviewer`)

```text
UX-REVIEW  verdict=changes  blockers=0  majors=1  minors=11
```

| ID | Sev. | Finding | Applied |
|---|---|---|---|
| UX-PRE-FU86-01 | major | No board shows the Environments list, the form, its states, the phone, or the Environment row at Launch; the board conventions need boards before screen code. | yes: FU-P3-86d lists them and comes before -86e and -86f (ui-spec §4.8.1, Boards) |
| UX-PRE-FU86-02 | minor | Going to the Environments page from Launch loses the form. | yes: New environment… opens the form in a dialog; the Manage link says the form is not kept |
| UX-PRE-FU86-03 | minor | A long list of radios is hard to scan. | yes: a native `<select>` over six environments |
| UX-PRE-FU86-04 | minor | With a Snakemake workflow profile the environment's SLURM defaults and caps are not passed, silently. | yes: one line in the form says so |
| UX-PRE-FU86-05 | minor | A time in minutes is easy to get wrong. | yes: hours and minutes fields, read back as "2 h 30 min" |
| UX-PRE-FU86-06 | minor | The run's facts show the server's executor, which becomes wrong once runs differ. | yes: the Environment fact and the Executor row from the run |
| UX-PRE-FU86-07 | minor | A disabled radio cannot be focused, so its reason is never heard. | yes: unusable environments are not offered and are named in a line under the group |
| UX-PRE-FU86-08 | minor | Delete needs a confirmation that says what happens to runs, with focus handling. | yes: a dialog, focus on Cancel, returned to the opener, "Runs that used it keep their settings" |
| UX-PRE-FU86-09 | minor | Two tabs editing the same environment. | yes: `412` "changed in another tab" with Reload |
| UX-PRE-FU86-10 | minor | A fourth tab in the phone's tab bar may not fit at 360 px. | open in R0; settled by R1-09 |
| UX-PRE-FU86-11 | minor | Save rewrites a hand-edited file and drops its comments. | yes: a line beside Save; whether that is acceptable is inbox #133 choice 1 |
| UX-PRE-FU86-12 | minor | An environment with no SLURM value has an empty summary. | yes: "SLURM's defaults for your account" |

Not taken: partitions and accounts offered from SLURM in a picker (Later, inbox #133 choice 10); a filter of the runs list by environment (Later).

## Round R1 (independent)

`security-reviewer` and `ux-reviewer` read the R0 design (commit `90cc6dee`) on 2026-11-09, independent and in parallel; the coordinator relayed their findings in summary, so the texts below are summaries. Every major and minor was applied to the owning spec in the commit after `90cc6dee`; where a finding offered two ways, the simpler one was taken, as each line says.

### `security-reviewer`

```text
SECURITY-REVIEW  verdict=changes  blockers=0  majors=2  minors=10
```

The reviewer's frame: whoever holds the session can already run code through `POST /runs`, so injection rules are defence in depth. The design now says so (api §5.4, req. 18).

| ID | Sev. | Finding (summary) | Applied, where |
|---|---|---|---|
| SEC-PRE-FU86-R1-01 | major | Per-run decisions read the per-name `environments` row or `settings.executor` (`failure.py:316`, `:823-894`, `resume.py:126`), and `ensure_tenancy` rewrites the oldest row. | applied: a `runs.environment` snapshot column read by every per-run decision; `ensure_tenancy` by name; the `local`-to-`slurm` rename test (api §5.4, "The database is not the source", §7 `runs`; req. 18; FU-P3-86a) |
| SEC-PRE-FU86-R1-02 | major | The login-node caps could be bypassed: `--cores` skipped when `extra_args` or a profile sets concurrency, `--jobs` aliases `--cores`, no memory counted without default resources, local rules on all cores under SLURM, Nextflow caps limit requests, not use. | applied, the simpler option: `--cores <cpus>` always last, a bare `--default-resources` then `--resources mem_mb`, `--local-cores 2` on every SLURM launch; the cap wording now says "the most the tasks may request; the cgroup is the only hard cap"; the order of `--cores` after `--jobs` **[to be validated]** (api §5.4, "Snakemake concurrency"; req. 18; FU-P3-86a, -86c) |
| SEC-PRE-FU86-R1-03 | minor | Resume must apply the launch rules again, and the runner must validate the payload's snapshot (`LaunchPayload` is lax, `loop.py:266`). | applied: the four Resume cases and the strict payload check (api §5.4, "Resume"; req. 18; FU-P3-86c) |
| SEC-PRE-FU86-R1-04 | minor | `check_config` follows symbolic links, `write_secret` opens the parent without `O_NOFOLLOW` or an owner check, no `O_NONBLOCK`, a per-process lock, and an identity tuple that misses same-size edits on NFS. | applied: directory `O_DIRECTORY\|O_NOFOLLOW` and `fstat`, `openat` with `O_NOFOLLOW\|O_NONBLOCK\|O_CLOEXEC`, the read cap + 1, `write_file` on the directory's descriptor, one process lock, identity with SHA-256; no lock file, the NFS window recorded as an accepted risk (the simpler option) (api §5.4, Reads and Writes; req. 18; FU-P3-86b) |
| SEC-PRE-FU86-R1-05 | minor | Deep nesting makes `tomllib` raise `RecursionError` (a 60,002-byte file on Python 3.13), a `500`. | applied: `RecursionError` and `ValueError` give `invalid`, with a short cleaned `detail`, never the file's bytes; a test (api §5.4; FU-P3-86b) |
| SEC-PRE-FU86-R1-06 | minor | The SLURM plugin runs `sbatch` with `shell=True` and does not quote `--mem`; Snakemake runs `expanduser` too; `$` in a pattern accepts a final newline; pydantic coerces types. | applied: `fullmatch` or `\Z`, strict types, a re-check in `headscript.py` at the point of use, the plugin's shell and `expanduser` named, tests for `"htc\n"`, `true`, `"5"`, `5.0`, 0 and 257 (api §5.4; req. 18; FU-P3-86a, -86c) |
| SEC-PRE-FU86-R1-07 | minor | The router must be in `create_app`'s conditional set, not the always-mounted one; cross-site tests on the `GET` and writes; `If-Match: *`. | applied (api §5.4, Routes and Tests; req. 18; FU-P3-86d) |
| SEC-PRE-FU86-R1-08 | minor | One path function (`data_dir` and `$SPECTIO_CONFIG` can differ), only the file and its temporary in that directory, render with `_toml_value` and parse back before rename; `../spectio` refused by the pattern. | applied (api §5.4, Where definitions live and Writes; FU-P3-86b) |
| SEC-PRE-FU86-R1-09 | minor | Reserve `new`; `:make-default` on an unknown or unusable name; a hand-written `default` naming nothing; deleting the default. | applied: `new` reserved; `404` and `422`; a dangling `default` makes the file `invalid` (the simpler of the two); Delete removes `default` in the same rename (api §5.4) |
| SEC-PRE-FU86-R1-10 | minor | Repudiation and visibility: a log line per write, the environment named in the run's facts, `head.out` and `spectio doctor`. | applied (api §5.4, Writes and "Where the environment is named"; FU-P3-86b, -86c) |
| SEC-PRE-FU86-R1-11 | minor | The read could hang on the file system: use the bounded file pool, cache by identity, and an "unreachable" state. | applied, built in 0.0.1: the pool with its timeout, the cache, a fifth state `unreachable`, a launch with a file environment `503 runner-offline` (api §5.4; req. 18; FU-P3-86b) |
| SEC-PRE-FU86-R1-12 | minor | Nextflow: scope the caps with `executor { $local { … } }`; a selector can pick another executor; `process_high` under 2 CPUs may fail. | applied, each **[to be validated]** as the reviewer marked (api §5.4, Nextflow; decision log) |

**Disagreements with R0.** SEC-PRE-FU86-08 said the caps were applied; R1-02 showed three bypasses. SEC-PRE-FU86-06 covered the manifest but not the per-run reads of the database and settings (R1-01). SEC-PRE-FU86-04 relied on `check_config`, which follows links (R1-04). SEC-PRE-FU86-01 and -02 overstated the threat, since a session can already launch code (R1-06, R1-10). SEC-PRE-FU86-03 was right but untested where the router is mounted (R1-07). SEC-PRE-FU86-10 missed `If-Match: *`, the cross-site checks and serialising the writes. R0 missed R1-05 and R1-11.

### `ux-reviewer`

```text
UX-REVIEW  verdict=changes  blockers=0  majors=7  minors=16
```

| ID | Sev. | Finding (summary) | Applied, where |
|---|---|---|---|
| UX-PRE-FU86-R1-01 | major | Launch's Profile is one choice, but an environment held a list. | applied, the simpler option: one default profile per engine; prefill only when the pipeline has it, with a line otherwise; Copy's profile wins (api §5.4 `profiles`; ui-spec §4.8.1 form and Launch; inbox #133 choice 3) |
| UX-PRE-FU86-R1-02 | major | "Where it runs" reads `server.executor` (`LaunchPage.tsx:335`, `:523-547`). | applied: no Executor row; every executor-dependent line follows the chosen environment; head and run directory stay the server's (ui-spec §4.8.1, "What follows the choice") |
| UX-PRE-FU86-R1-03 | major | No loading, error or `422` states for the environment row; no Launch reason; Copy's notice place. | applied (ui-spec §4.8.1, Launch States and Copy; §4.6 pointer) |
| UX-PRE-FU86-R1-04 | major | With a `refused` or `invalid` file only built-ins are listed, so "Not usable: mylab" cannot be served; the local-server SLURM entry was unsettled. | applied: Launch reads `file.state` and says so, New environment waits; a hand-written SLURM entry on a local server is `usable: false`, the file stays `ok` (api §5.4 `executor`; ui-spec §4.8.1) |
| UX-PRE-FU86-R1-05 | major | `GET /runs/{id}` could not carry the values or "not readable". | applied: `environment` with `slurm`, `local` and `state`; the fact with its summary; the Executor row from the run (api §5.4 Routes; ui-spec §4.8.1 Run detail) |
| UX-PRE-FU86-R1-06 | major | No focus rule after Delete and Make default. | applied (ui-spec §4.8.1, Delete and Make default) |
| UX-PRE-FU86-R1-07 | major | At Launch, a Snakemake profile silently replaces the environment's resources. | applied: the Tasks row says so, with the form's words (ui-spec §4.8.1) |
| UX-PRE-FU86-R1-08 | minor | One usable environment as a radio group. | applied: a text row; radios from two |
| UX-PRE-FU86-R1-09 | minor | The tab label at 360 and 320 px. | applied: full label, wrap rules, accessible name; the departure from §4.11 stated (ui-spec §4.8.1 Navigation) |
| UX-PRE-FU86-R1-10 | minor | One name "New environment", the empty line, the file's path. | applied |
| UX-PRE-FU86-R1-11 | minor | A section colour and icon. | applied: `--sp-section-environments` sky-600 / sky-400 and its background, the server icon |
| UX-PRE-FU86-R1-12 | minor | Errors inside the Delete dialog; the default's line. | applied |
| UX-PRE-FU86-R1-13 | minor | Make default errors. | applied: in the card, `role="alert"`, Reload |
| UX-PRE-FU86-R1-14 | minor | Time, memory, Reload and reserved-name rules; the local server's executor as text. | applied (ui-spec §4.8.1 form; api §5.4 `name`: `422`) |
| UX-PRE-FU86-R1-15 | minor | Radio names and descriptions; the select's summary. | applied |
| UX-PRE-FU86-R1-16 | minor | Built-in labels. | applied (api §5.4 Built-ins; ui-spec §4.8.1) |
| UX-PRE-FU86-R1-17 | minor | "SLURM account". | applied |
| UX-PRE-FU86-R1-18 | minor | Resume lines for `not_recorded` and `not_readable`. | applied (api §5.4 Resume; ui-spec §4.8.1) |
| UX-PRE-FU86-R1-19 | minor | The New environment dialog's errors, Reload, phone, unsaved values. | applied |
| UX-PRE-FU86-R1-20 | minor | Manage environments link and `?env=` add little. | applied, the simpler option: both dropped; Copy uses the launch template; moved to Later |
| UX-PRE-FU86-R1-21 | minor | A folded "What the engines get". | deferred to after 0.0.1, as recommended: ui-spec §4.8.1 Later and a line in [MVP 0.0.1](../../specs/mvp-0.0.1.md) |
| UX-PRE-FU86-R1-22 | minor | Phone cards and actions. | applied |
| UX-PRE-FU86-R1-23 | minor | Where `usable: false` comes from. | applied: the built-in `slurm` with a bad `spectio.toml` value, and the SLURM entry on a local server |

**Disagreements with R0.** UX-PRE-FU86-04 (the Snakemake profile line) was raised to a major at Launch (R1-07). UX-PRE-FU86-06 fixed the run's facts but not "Where it runs" or the values (R1-02, R1-05). UX-PRE-FU86-07 assumed unusable environments could be named, which a `refused` or `invalid` file prevents (R1-04). UX-PRE-FU86-08 had no focus rule after the delete (R1-06). UX-PRE-FU86-10 is now measured and settled (R1-09). UX-PRE-FU86-03 gave no accessible name rule (R1-15). R1 agreed with R0 on -01, -02, -05, -09, -11 and -12.

### What moved in the build plan

The per-run snapshot (`runs.environment`) and the `failure.py`, `resume.py` and `ensure_tenancy` changes come first, in FU-P3-86a; the file is -86b; the launch (mapping, caps, Resume, the launch template) is -86c; the routes are -86d. The UI tasks become -86e (boards), -86f (pages) and -86g (Launch and run detail): seven tasks instead of six ([inbox #133](../inbox.md#133-assumed-environments-local-slurm-define-a-new-one-fu-p3-86)).
