---
name: verify-claims
description: Extract every external factual claim (and every "[to be validated]" marker) from one or more Spectio specs and verify them with the fact-checker agent, writing a verification table. Use before a spec is marked stable or when a dependency released a new version.
argument-hint: "<spec file(s)>"
disable-model-invocation: true
---

1. **Extract the claims.** For each file in `$ARGUMENTS`, list every sentence that states a fact about something outside Spectio (a tool, flag, API, version, default, licence, standard), plus every `[to be validated]`. Give each claim an ID: `<file-stem>-<n>`.
2. **Dispatch.** Split the claims into batches of about 15. Dispatch one `fact-checker` agent per batch, in parallel. Each gets its claims, their locations and the target versions.
3. **Collect.** Write `docs/reviews/verification-<date>.md` with:
   - a table: claim, location, verdict, source, correction;
   - the totals.
4. **Propose fixes.** For every claim marked wrong or partly true, propose the exact replacement sentence. Do not edit the spec unless Thomas says so. Then `/apply-findings` handles it.
