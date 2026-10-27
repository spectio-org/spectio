# Reviews

Each review round writes one file here, `<round-id>.md` (e.g. `R1-consistency.md`), produced by the `/review-round` skill. Findings are applied to the specs only after triage, by `/apply-findings`.

## Finding format

```markdown
### SR-012 · major · Gate decisions: two definitions of "exclude"

- **Where:** api-and-data-model.md §5 (gate decision body) vs checking-scenarios.md §5 (decision types)
- **Evidence:** "…" (api §5) / "…" (checking §5)
- **Problem:** an implementer cannot tell whether excluding an item also edits the samplesheet.
- **Proposal:** define `exclude` once in checking-scenarios.md §5; api §5 links to it and lists the fields.
- **Found by:** spec-reviewer, constraints-hunter
- **Status:** open | accepted | rejected (reason) | applied (commit / section)
```

**Severity:**
- **Blocker:** implementation cannot start, or would build the wrong thing.
- **Major:** a real problem that will cost rework.
- **Minor:** worth fixing, low risk.

**ID prefixes:**
- `SR`: spec reviewer;
- `FC`: fact checker;
- `CH`: constraints hunter;
- `SEC`: security;
- `UX`: UX reviewer;
- `DL`: depictio liaison;
- `TA`: test architect;
- `IE`: infra engineer;
- `DEP-T`: depictio liaison, tooling and ecosystem re-audit (R8b);
- `CR`: code reviewer, one file per build step in `code/<step-id>.md` (`review-code` skill).
