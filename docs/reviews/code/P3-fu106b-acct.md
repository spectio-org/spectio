# Code review · FU-P3-106b (accounting part), Snakemake SLURM status command from the site's accounting

`review-code` on `autopilot/P3-fu106b-acct`, base `4124268d`, 2026-11-23. Two commits: the step `bdf0e51e` and the fix `09c9917b`. The server reads `AccountingStorageType` from `scontrol show config` once per process and passes `--slurm-status-command squeue` (off) or `sacct` (on) to Snakemake SLURM launches. Behaviour is owned by [schedulers-and-monitoring §3.8](../../specs/schedulers-and-monitoring.md#38-slurm-query-budget); decision in [inbox #156](../inbox.md#156-assumed-a-slurm-site-without-accounting-and-a-run-whose-jobs-left-the-queue-task-22-2026-11-18). Reviewers: `code-reviewer` and `security-reviewer`, in parallel. Format: [`README.md`](../README.md).

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `bdf0e51e` | **changes** (1 blocker, 2 minors, 1 simplify) | **approve** (3 minors) |
| 2 | `09c9917b` | fix check: CR-01 and CR-03 resolved | not re-run |

```text
CODE  step=P3-fu106b-acct  review=changes->fixed b/M/m=1/0/2  security=approve b/M/m=0/0/3  rounds=2  simplify=skipped -0/+0  tests=pass
```

Counts are round 1. The `simplify` finding is not counted.

## Findings

| ID | Severity | Finding | Status |
|---|---|---|---|
| CR-P3FU106B-ACCT-01 | blocker | `AccountingStorageType = (null)` was read as unknown, not off, so no flag was passed and the Snakemake e2e could hang | fixed in `09c9917b`: empty or `(null)` counts as off. Man page quoted: "Unset by default, which indicates that accounting records are not maintained" ([slurm.conf](https://slurm.schedmd.com/slurm.conf.html#OPT_AccountingStorageType), checked 2026-11-23) |
| CR-P3FU106B-ACCT-02 | minor | no test covers `loop.py` setting `slurm_accounting` | open |
| CR-P3FU106B-ACCT-03 | minor | the doctor's unknown line named the wrong cause | fixed in `09c9917b`: "unknown (the reason is logged as a warning)" |
| CR-P3FU106B-ACCT-04 | minor, simplify | the user-flag check is written in the code and again in the test | open |
| SEC-P3FU106B-ACCT-01 | minor | an unknown result is cached for the process life, so one transient failure keeps the plugin default (`sacct`) | open |
| SEC-P3FU106B-ACCT-02 | minor | `functools.cache` takes no lock; two first launches may each run `scontrol` | open |
| SEC-P3FU106B-ACCT-03 | minor | `check_tool` refusals say `sacct at <path>/scontrol` | open, diagnostics only |

## Assumptions

- `(null)` is how `scontrol` prints an unset key: source is the [EMBL audit](../../research/2026-11-08-embl-login-node-audit.md), lines 36 to 40.
- slurm-mini's real `AccountingStorageType` line was not captured (Docker stopped). `dev/slurm/cluster.sh up` now prints it, so the CI log shows it. **[to be validated]** in the spec until then.
- The doctor's warning reaches stderr through Python's last-resort handler. Not run to confirm. **[to be validated]**
- The `pipelines-slurm` e2e (launch Snakemake) was not run here. It must pass in CI before merge.
