# depictio and LabID re-audit (2026-10-26)

Sources: depictio `main` 0d1aa0a (2026-10-23; = tag v1.19.2 `e40ca79` + CHANGELOG commit);
labid-server 52d3952 (2026-10-23), labid-lib cd14636 (2026-10-26), labid-cli 5af9e16
(2026-09-23). Shallow clones, read only. Findings: [R8](../reviews/R8-depictio.md) DL-101..DL-115.

## 1. What changed upstream since the 2026-10-25 audits
- depictio: nothing. `origin/HEAD` is still 0d1aa0a. Cite `v1.19.2 (e40ca79)` for code and
  0d1aa0a for the tree (DEP-T-031).
- LabID: labid-server is public and was read for the first time; labid-lib moved to cd14636
  (no new tag since v26.09.2).

## 2. What the earlier notes got wrong or left out
- plotly-upset / plotly-complexheatmap are on PyPI (0.1.0, 2026-10-05).
- Embeds already post `{source:"depictio-embed", type:"filter"|"ready"}` (EmbedApp.tsx:12-104).
  The API and nginx send `frame-ancestors 'self'` (security_headers.py:121;
  nginx.conf.template:231,234), but nginx's `location /dashboard/` re-declares `add_header`
  (l.94-98), so its HTML probably carries no framing header [to be validated]. Either way a
  cross-origin frame has no session (localStorage, partitioned storage) [to be validated].
- A standalone recipe runner exists as a maintainer command: `depictio dev recipe run`
  (dev.py:17-21); it skips `dc_ref` recipes (186/339) with exit 0 (recipe.py:64-74).
  61 MultiQC outputs have no recipe.
- `--pipeline-id` needs an exact shipped template (run.py:1384-1400); 41 templates, 32 pipelines.
- Run tag = directory basename (scan.py:798-825); `--attach-run` recipe collections read the
  first run only (run.py:2928-2939); `--result-json` has no run ID (run.py:157-177).
- `--provenance-file` = flat key/value, 500 chars, project-level, "User provided"
  (templates.py:1003,1149-1162).
- `--user` requires the instance provisioning key (run.py:3102-3124); CLIConfig requires S3
  write credentials (cli.py:84-87; deltatables.py:1083-1088).
- JWT claims: name, token_lifetime, token_type, sub, exp; no iss/aud/email; revocation via
  TokenBeanie lookup (core_functions.py:416-465). `/auth/me` returns `User` (password field,
  inference).
- `/groups/list` = summaries; detail via `/groups/{id}`.
- Server-side refresh ingestion exists: `POST /projects/ingestion/trigger/{id}`, off by default.
- Per-user filter state: `PUT /dashboards/filter_state/{dashboard_id}`.
- LabID: `/api/v2/`, OpenAPI `/api/schema/`, simplejwt Bearer (14 d) + DRF Token + `?jwt=`/`?key=`,
  SSO OIDC or SAML, superuser impersonation, WorkflowRun API.
- megatest.yaml: 35 of 38 version templates.

## 3. Requests to depictio: status on 2026-10-26
The status table is kept in [`depictio-ecosystem-reuse.md`](../specs/depictio-ecosystem-reuse.md) §3.
