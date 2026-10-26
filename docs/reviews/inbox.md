# Inbox — questions for Thomas

The autopilot adds entries here; answer inline with `Answer: <option>` (and a sentence if useful). Entries marked **assumed** already proceed with the recommended option; your answer overrides it on the next tick.

<!-- autopilot: append entries below this line -->

### #1 · Virgil font licence (blocks publishing the hand-drawn figures' font)

- **Context:** `tools/diagrams/FONT-LICENSE.md`. The file copied from depictio says "Copyright (c) Jason Smith … All rights reserved", while Excalidraw's page says OFL-1.1, and also MIT.
- **Options:**
  - (a) check `github.com/excalidraw/virgil` yourself and, if it is OFL, commit the font with `OFL.txt`;
  - (b) switch to Excalifont;
  - (c) keep the font local only (`SPECTIO_VIRGIL_TTF`), so CI renders SVG only and PNGs are rendered locally.
- **Recommendation:** (a), with (c) until then. **Assumed:** (c), so the font is not committed.
- **Answer (Thomas, 2026-10-26):** Virgil is set aside for now. Read as (c): the font stays local and is not committed, and figures are rendered locally. *Handled.*

### #2 · Install telemetry: opt-in (current) or opt-out like depictio?

- **Context:** `telemetry-and-analytics.md` §0.4.
- **Options:**
  - (a) opt-in with a prompt at `spectio init` and at the first admin sign-in (current);
  - (b) opt-out like depictio, with a notice and the payload preview.
- **Recommendation:** (a) for institutional installs. **Assumed:** (a).

### #3 · Let CI merge into `main`?

- **Context:** `documentation-system.md` §8, `autopilot.md` §8. PRs into `autopilot/integration` auto-merge after the checks and the doc review. Merging into `main` needs `AUTOMERGE_MAIN=true`, and branch protection set up with the `gh` commands in `autopilot.md` §8.
- **Options:**
  - (a) keep human merges into `main` for now;
  - (b) set the variable now.
- **Recommendation:** (a) until W1 has run once; then (b). **Assumed:** (a).

### #4 · Permissions, status line and hook for unattended runs

- **What to add:** the JSON in `autopilot.md` §4, which covers the permission rules, the budget status line and the `StopFailure` hook. Agents cannot add it themselves.
- **Answer with:** `done` when added.

### #5 · Clean git history before the repository is shared

- **Context.**
  - The remote has a single branch, `claude/foundations-2026-10-26`, which is also its default. Nobody else has cloned it.
  - Its history holds, in commit `b2687d8`, screenshots and a video that show the owner's name, initials, `/scratch/tw/…` and "EMBL SLURM".
  - It also holds a 3.3 MB GIF committed in `0e5b97a` and removed later.
  - The design boards themselves (`design/ui-canvas`, current tree) still show those names. Media are now rendered with fixture names.
- **Done (additive, nothing deleted).** A new branch `main` with one clean commit holding the current tree was pushed. The old history is kept as the local branch `archive/history-2026-10-26` and on the remote branch above.
- **Your part.** In GitHub settings, make `main` the default branch. Then delete the old branch (`git push origin --delete claude/foundations-2026-10-26`), or tell the autopilot to do it.
- **Optional.** Also replace the real names in the boards with fixtures before going public.

### #6 · Nextflow ingestion: keep the Tower protocol, or only Spectio's own plugin?

- **Context.** `docs/research/adoption-and-positioning-2026-10-26.md` §2 and `synthesis.md` §2. Accepting Nextflow's built-in Tower protocol gives zero-install monitoring, as nf-shard does, but the protocol is undocumented and positions Spectio closer to Seqera.
- **Options:**
  - (a) keep both, with the Tower route labelled unofficial and best effort;
  - (b) `nf-spectio` only.
- **Recommendation:** (a) for the alpha, revisited before the public beta. **Assumed:** (a).

### #7 · Licence and the date the repository goes public

- **Context.** JOSS needs more than six months of public history, and an OSI licence (adoption note §4).
- **Options:**
  - (a) MIT, public at the start of the private alpha (0.2);
  - (b) MIT, public at the beta.
- **Recommendation:** (a). **Assumed:** none. This needs your decision before the repository becomes public.

### #8 · Do not set branch protection yet (R8b blockers)

- **Context:** `docs/reviews/R8b-depictio-tooling.md`, findings DEP-T-001 and DEP-T-002.
  - The required checks listed in `autopilot.md` §8 include path-filtered workflows, so docs-only PRs would wait forever.
  - release-please with the default token can trigger neither the release builds nor the checks on its own PR.
- **Recommendation:** run the `gh` protection commands of `autopilot.md` §8 only after APPLY1 has added:
  - a single `ci-ok` check;
  - a GitHub App token for release-please and the other bot PRs.
- **Your part, meanwhile:** create a GitHub App for the repository (contents and pull requests: write), and store its ID and key as environment secrets.
- **Assumed:** protection is not set.

### #9 · GitHub organisation for packages and images (DEP-T-026)

- **Context:** the names `spectio`, `spectio-server`, `spectio-sdk`, `spectio-cli` and `@spectio/client` were free on PyPI and npm on 2026-10-26. Trusted publishers and GHCR packages are bound to the owner and the repository.
- **Options:**
  - (a) a `spectio` organisation;
  - (b) one organisation shared with depictio;
  - (c) stay under `weber8thomas` until 0.1.0.
- **Recommendation:** (a) or (b), decided before 0.1.0, with the names reserved then. **Assumed:** (c).
