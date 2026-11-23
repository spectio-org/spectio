# Code review · FU-P3-87c, the catalog boards and the Launch picker

`code-reviewer` on `autopilot/P3-fu87c`, range `6cd4831..1d499236`, 2026-11-10. Design boards and one spec bullet; no product code, so no test run. `security-reviewer` skipped (no sensitive path). Format: [`README.md`](../README.md).

| Round | Result |
|---|---|
| 1 | approve (0 blockers, 0 majors, 5 minors) |
| 2 | fixes in `1d499236`: CR-01, CR-02, CR-04 resolved |

## Findings

| ID | Severity | Finding | Status |
|---|---|---|---|
| CR-P3FU87C-01 | minor | Save to catalog drawn in a row under the Loaded card, not inside it as in panel c1 | fixed in `1d499236` (LiteLaunch, MLiteLaunch) |
| CR-P3FU87C-02 | minor | ui-spec §4.7.1 Boards bullet contradicted the Save to catalog bullet | fixed in `1d499236` |
| CR-P3FU87C-03 | minor | Panel c1 treats nf-core hidden fields in two ways; the nf-core claim is **[to be validated]** | open |
| CR-P3FU87C-04 | minor | Designer note in the `aria-describedby` hint | fixed in `1d499236` |
| CR-P3FU87C-05 | minor | Small gaps against §4.7.1 (Manage catalog placement, "Clear and start empty" not drawn, "comments are not kept" line, 409 vs 412 delete) | open |

```text
CODE  step=P3-fu87c  review=approve b/M/m=0/0/2  security=skipped  rounds=2  simplify=skipped -0/+0  tests=n/a
```

## ux-reviewer (run by the orchestrator, 2026-11-10)

Verdict **approve**, b/M/m = 0/0/8. All the boards were rendered at 1440, 390, 360 and 320 px and looked at.

- **Fixed on this branch:**
  - UX-P3FU87C-02: the phone sheet now covers the whole screen, the tab bar included, and Escape closes it.
  - UX-P3FU87C-03: the foot on MLiteCatalog was #6E7287 on #F7F7FB, a contrast of 4.45:1; it is now #4D5065.
  - UX-P3FU87C-04: Save to catalog is a `<form novalidate>`, with Save as `type="submit"` and placed first.
  - UX-P3FU87C-05: the empty Catalog page no longer has a second Add pipeline link.
- **Carried to FU-P3-87d and FU-P3-87e:**
  - UX-P3FU87C-01: the Manage dialog rows have the same content as the page list, and each label is a focusable heading.
  - UX-P3FU87C-06: a `refused` catalog file reads "Spectio does not read your catalog file", and `unreachable` gets Retry. This needs one line in ui-spec §4.7.1.
  - UX-P3FU87C-07: these states are built and tested rather than drawn: Clear and start empty, a profile missing from the pipeline, the "writable by others" warning, a params file that cannot be read, Try leaving out entries already in the catalog, and Home's "Your catalog" link.
  - UX-P3FU87C-08: Manage catalog sits beside the picker on desktop and under it on the phone. The spec line will say so.
