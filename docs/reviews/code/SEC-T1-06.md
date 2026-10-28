# Code review · SEC-T1-06, private workdir for the test runners

`review-code` on `claude/autopilot-promotion-t1-d6-hutw7a`, range `a2f87d3..c7ef6eb`, 2026-10-28, tick 11. Reviewers: `code-reviewer` and `security-reviewer`, independent, in parallel. Format: [`README.md`](../README.md).

The change fixes SEC-T1-06 from the [T1 code review](T1.md): before T3 runs the harness on a sind submitter node ([dev environment §4.1](../../specs/dev-environment-and-testing.md#41-slurm-with-sind)), `run_scenarios.py` must stop deleting and reusing the predictable shared directory `/tmp/spectio-scenarios`. Without `--workdir`, `run_scenarios.py` and `run_corpus.py` now create a fresh private directory with `tempfile.mkdtemp` (mode 0700) and print its path. An explicit `--workdir` is created with its missing parents under umask 077, resolved, and refused unless this user owns it, it is not a symlink, nobody else can write to it, and its resolved parents belong to this user or root (sticky if others can write, like `/tmp`); the resolved path is the one used. CI passes `$RUNNER_TEMP/…` and is unchanged.

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `9954aa0` | **approve** (0 blockers, 0 majors, 2 minors) | **approve** (0 blockers, 0 majors, 3 minors) |
| 2 | `f9a4d6e` | **approve** on the fix delta (0 blockers, 0 majors, 1 minor) | not re-run (round 1 had minors only) |
| 3 | `d31b2c9` | **approve** on `3355a10..d31b2c9` (0 blockers, 0 majors, 2 minors) | **approve** on `3355a10..d31b2c9` (0 blockers, 0 majors, 1 minor) |
| 4 | `881a65d` | not re-run (round 3 had minors only) | **approve** on `d31b2c9..881a65d` (0 blockers, 0 majors, 2 minors) |
| 5 | `c7ef6eb` | not re-run (round 4 had minors only) | **approve** on `881a65d..c7ef6eb` (0 blockers, 0 majors, 0 minors) |

```text
CODE  step=SEC-T1-06  review=approve b/M/m=0/0/5  security=approve b/M/m=0/0/6  rounds=5  simplify=nochange -0/+0  tests=pass
```

`code-simplifier` ran twice and changed nothing: on `f9a4d6e` (each helper was one line) and on `3355a10..c7ef6eb` (each line of `make_workdir` carries one approved check; the two copies stay identical). Round 5 tests, at `c7ef6eb`; the run and the refusal below were recorded at `f9a4d6e` and `e8ab2f4`, and `c7ef6eb` changes only docstrings and `--help`:

```bash
python3 -m unittest tests/pipelines/synthetic/test_golden.py tests/pipelines/real/test_run_corpus.py
```

```text
Ran 26 tests in 0.043s

OK
$ python3 tests/pipelines/synthetic/run_scenarios.py --engine snakemake --only happy
workdir: /tmp/spectio-scenarios-jhnhhktp
PASS  snakemake happy                             17.2s
$ ls -ld /tmp/spectio-scenarios-jhnhhktp
drwx------ 3 root root 4096 Oct 28 08:11 /tmp/spectio-scenarios-jhnhhktp
$ mkdir /tmp/sh && chmod 777 /tmp/sh   # a parent others can write to, not sticky
$ python3 tests/pipelines/synthetic/run_scenarios.py --workdir /tmp/sh/wd --engine snakemake --only happy
--workdir /tmp/sh/wd: must be a directory you own that others cannot write to (chmod go-w), not a symlink, under directories that only you or root can change
$ echo $?
1
```

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-S06-1 | minor | `run_corpus.py` had the same predictable default (`/tmp/spectio-corpus`, `rmtree` under it) | `f9a4d6e` (same `mkdtemp` default, unit test) |
| CR-S06-2 | minor | T1 Progress page, T1 review table and inbox #51 still called SEC-T1-06 open | `0d93d25`, squashed into integration as `7a2f1b0` |
| SEC-S06-1 | minor | An explicit `--workdir` in shared `/tmp` (another user's directory, or a symlink) is still trusted | `d31b2c9` (owner, symlink and group/other write checks, created with mode 0700, unit tests) |
| SEC-S06-2 | minor | The T1 step test told contributors to use `--workdir /tmp/t1` | `0d93d25`, squashed into integration as `7a2f1b0` (the T1 How-to-test command drops `--workdir`; dated evidence transcripts stay as recorded) |
| SEC-S06-3 | minor | The private workdirs are never removed and can fill a login node's quota | `f9a4d6e` (both docstrings say they are kept for debugging and how to remove them) |
| CR-S06-3 | minor | The cleanup command expanded to `/spectio-*` when `TMPDIR` is unset | `c9d53f9` (`${TMPDIR:-/tmp}`) |
| SEC-S06-4 | minor | Only the last component of an explicit `--workdir` was checked; a parent another user owns or can write to allowed a swap after the check | `881a65d` (resolved parents must belong to this user or root, sticky if others can write; unit tests for a shared and a sticky parent) |
| CR-S06-4 | minor | Same parent gap as SEC-S06-4 (proposed a docstring note instead of a check) | `881a65d` (the check from SEC-S06-4; the docstring states the rule) |
| CR-S06-5 | minor | With umask 002 a directory the user made is refused without a hint | `881a65d` (the refusal names `chmod go-w`) |
| SEC-S06-4a | minor | The resolved parents were checked but the path as given was used, so a symlink on the way could be swapped after the check | `e8ab2f4` (the resolved path is checked and returned; unit test with a linked parent) |
| SEC-S06-4b | minor | Missing parents followed the umask, so with umask 002 the script refused a path it had just created | `e8ab2f4` (parents created under umask 077; unit test under umask 002) |
