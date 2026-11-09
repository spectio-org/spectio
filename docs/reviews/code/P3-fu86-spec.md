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
| R1 | `security-reviewer` and `ux-reviewer`, run by the coordinator | yes | pending | pending |

## R0, self-review (not independent)

### How it ran

The design worker had no Agent tool, so it could not start `security-reviewer` and `ux-reviewer` as independent agents. It went through each agent's checklist itself (`.claude/agents/security-reviewer.md`: STRIDE on the browser ↔ server boundary and the server ↔ engine boundary, injection into engine arguments and configuration, files in the shared home, the listener; `.claude/agents/ux-reviewer.md`: states, accessibility, phone, data the API can serve, boards), against the code read for the design. No board was drawn or rendered: the boards are FU-P3-86d. **This review is not independent.** R1 below is the independent round.

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
| UX-PRE-FU86-10 | minor | A fourth tab in the phone's tab bar may not fit at 360 px. | open: decided on MLiteEnvironments (FU-P3-86d) |
| UX-PRE-FU86-11 | minor | Save rewrites a hand-edited file and drops its comments. | yes: a line beside Save; whether that is acceptable is inbox #133 choice 1 |
| UX-PRE-FU86-12 | minor | An environment with no SLURM value has an empty summary. | yes: "SLURM's defaults for your account" |

Not taken: partitions and accounts offered from SLURM in a picker (Later, inbox #133 choice 10); a filter of the runs list by environment (Later).

## Round R1 (independent)

Pending: the coordinator runs `security-reviewer` and `ux-reviewer` on this design and relays their findings.

### `security-reviewer`

Pending.

### `ux-reviewer`

Pending.
