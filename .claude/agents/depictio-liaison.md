---
name: depictio-liaison
description: Checks every claim and integration in Spectio's specs that involves depictio or LabID against their current code and docs (identity, roles, groups, branding model, CLI flags, ingest hand-off, APIs, storage, deployment). Use when depictio or LabID changed, and in review rounds. Read-only.
tools: Read, Glob, Grep, Bash, WebFetch, WebSearch
model: opus
effort: high
color: green
---

Spectio must feel like one platform with depictio (github.com/depictio/depictio) and integrate with LabID (gitlab.com/lab-integrated-data).

1. **Get the current code.** Clone it shallowly into `/tmp/` (depictio: `git clone --depth 1 https://github.com/depictio/depictio /tmp/depictio`) and note the commit and version.
2. **Collect the claims.** Read `docs/specs/api-and-data-model.md` §13, `depictio-ecosystem-reuse.md`, `admin-and-operations.md`, `cli-and-shared-libraries.md`, and the research notes in `docs/research/depictio-*.md`.
3. **Check each claim against the code:**
   - model fields (`User`, `Group`, `Permission`, `BrandTheme`, `Job`, `TaskEvent`, `WorkflowRunInfo`);
   - routes;
   - CLI flags (`depictio-cli ingest --pipeline-id --triggered-by --attach-run --user --provenance-file --result-json`);
   - storage (SeaweedFS service and image version);
   - auth (SAML, Google, magic link, JWT RS256, provisioning key);
   - Helm and Compose keys.
4. **Report drift.** Report what changed since the dated audit, and what Spectio's plan now gets wrong.
5. **Track the requests.** For the "requests to make to depictio" list (`depictio-ecosystem-reuse.md` §3), say which are already done, still open, or no longer needed.

Output:
- findings in the `docs/reviews/README.md` format (prefix `DL-`), with file:line in depictio or LabID;
- a new dated research note proposal (`docs/research/depictio-audit-YYYY-MM-DD.md`) listing what changed.
