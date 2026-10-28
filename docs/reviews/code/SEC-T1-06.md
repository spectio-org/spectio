# Code review · SEC-T1-06, private workdir for the test runners

`review-code` on `claude/autopilot-promotion-t1-d6-hutw7a`, range `a2f87d3..c9d53f9`, 2026-10-28, tick 11. Reviewers: `code-reviewer` and `security-reviewer`, independent, in parallel. Format: [`README.md`](../README.md).

The change fixes SEC-T1-06 from the [T1 code review](T1.md): before T3 runs the harness on a sind submitter node ([dev environment §4.1](../../specs/dev-environment-and-testing.md#41-slurm-with-sind)), `run_scenarios.py` must stop deleting and reusing the predictable shared directory `/tmp/spectio-scenarios`. Without `--workdir`, `run_scenarios.py` and `run_corpus.py` now create a fresh private directory with `tempfile.mkdtemp` (mode 0700) and print its path. An explicit `--workdir` is used as given; CI passes `$RUNNER_TEMP/…` and is unchanged.

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `9954aa0` | **approve** (0 blockers, 0 majors, 2 minors) | **approve** (0 blockers, 0 majors, 3 minors) |
| 2 | `f9a4d6e` | **approve** on the fix delta (0 blockers, 0 majors, 1 minor) | not re-run (round 1 had minors only) |

`code-simplifier` ran on `f9a4d6e` and changed nothing: each helper is one line and the unit tests call it. Test command:

```bash
python3 -m unittest tests/pipelines/synthetic/test_golden.py tests/pipelines/real/test_run_corpus.py
```

```text
Ran 16 tests in 0.041s

OK
$ python3 tests/pipelines/synthetic/run_scenarios.py --engine snakemake --only happy
workdir: /tmp/spectio-scenarios-jhnhhktp
PASS  snakemake happy                             17.2s
$ ls -ld /tmp/spectio-scenarios-jhnhhktp
drwx------ 3 root root 4096 Oct 28 08:11 /tmp/spectio-scenarios-jhnhhktp
```

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-S06-1 | minor | `run_corpus.py` had the same predictable default (`/tmp/spectio-corpus`, `rmtree` under it) | `f9a4d6e` (same `mkdtemp` default, unit test) |
| CR-S06-2 | minor | T1 Progress page, T1 review table and inbox #51 still called SEC-T1-06 open | docs commit of this change |
| SEC-S06-1 | minor | An explicit `--workdir` in shared `/tmp` (another user's directory, or a symlink) is still trusted | open: follow-up before the harness runs on a shared node with an explicit `--workdir`; check owner, symlink and group/other write bits, create levels with mode 0700 |
| SEC-S06-2 | minor | The T1 step test told contributors to use `--workdir /tmp/t1` | docs commit of this change (the T1 How-to-test command drops `--workdir`; dated evidence transcripts stay as recorded) |
| SEC-S06-3 | minor | The private workdirs are never removed and can fill a login node's quota | `f9a4d6e` (both docstrings say they are kept for debugging and how to remove them) |
| CR-S06-3 | minor | The cleanup command expanded to `/spectio-*` when `TMPDIR` is unset | `c9d53f9` (`${TMPDIR:-/tmp}`) |
