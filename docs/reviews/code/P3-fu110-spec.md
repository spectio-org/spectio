# Code review · P3-fu110-spec, run resources and an extra config file (design only)

Step `P3-fu110-spec` on `autopilot/P3-fu110-spec`, base `c061d4f8`, 2026-11-10. The step writes the design of FU-P3-110 ([decision log](../../decisions/log.md), [inbox #150](../inbox.md#150-assumed-run-resources-and-an-extra-config-file-fu-p3-110)). No product code changes. Format: [`README.md`](../README.md).

```text
CODE  step=P3-fu110-spec  review=approve b/M/m=0/1/6  security=approve b/M/m=0/1/5  rounds=2  simplify=skipped -0/+0  tests=skipped
```

Round 1 found `changes` from both reviewers; commit `71f2cf36` fixed the findings below; the fix check found none unresolved.

## Findings

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3FU110-SPEC-01 | major | Snakemake merges config files deeply, so a form map would overwrite the extra file's keys | fixed: [api §5.7](../../specs/api-and-data-model.md#57-run-resources-and-an-extra-config-file-001) sends only the leaf keys the user set; preview text; test case `ref.build` / `ref.release` |
| CR-P3FU110-SPEC-02 / SEC-P3FU110-SPEC-02 | minor | one ownership rule: file owned by the user, root and later directories by the user or root, none group- or other-writable; home from the password database | fixed: api §5.7, dev-env req. 20, decision log, inbox #150; tests added |
| CR-P3FU110-SPEC-03 | minor | a home that is a symbolic link was refused | fixed: home accepted as written and as its realpath; test added |
| CR-P3FU110-SPEC-04 | minor | Time bound, "per task" wording, `--default-resources` text | fixed: error "At most 720 hours (30 days)"; wording aligned |
| SEC-P3FU110-SPEC-01 | major | file bytes kept in `runner_commands.payload`, may hold credentials | fixed: payload text set to null at the sink's ack; Resume and the View route read the 0600 copy; test added |
| CR-P3FU110-SPEC-05 / -06 / -07, SEC-P3FU110-SPEC-03 to -06 | minor | credentials note, ETag comparison, 110a size, YTE edge cases, route principal, bidi display, slurm login-node selectors | not applied here; carried to FU-P3-110a to -110d |

Open point: freed SQLite pages and the WAL may keep old bytes after the null update (`PRAGMA secure_delete`); to be raised in FU-P3-110a.
