---
name: write-docs
description: Write and verify the documentation for one Spectio pipeline step or PR — Progress page, owning-spec changes, figures, media, PR body — then run the docs gate and an independent doc-reviewer pass. Use at the end of every autopilot step (the autopilot skill calls it), before opening any PR, and when Thomas asks to "document" a change.
argument-hint: "<step-id or 'pr'> [wave]"
---

# Write and verify docs: $ARGUMENTS

The rules are in `docs/specs/documentation-system.md`. This skill is the procedure.

1. **Evidence first.** Collect the step's diff (`git diff --stat` and the diff against the integration branch), the worker's commands and outputs, test reports and the exit-check output. Docs are written from these, never from the step prompt alone.
2. **Write** — dispatch `doc-writer` with the evidence, the step id, wave and kind. It creates `docs/progress/<wave>/<step>.md` from `progress-template.md` in this folder, updates the owning spec when behaviour was decided, and lists the figures and media the step kind needs (§3.1).
3. **Figures and media** — every step gets at least one sketch, whatever its kind (§3.4): for a review round, the scope walked with its blockers and majors pinned by finding ID; for triage, bars to scale from the real counts; for apply, before and after. It goes first on the Progress page, under the `!!!` line. In parallel, dispatch `diagram-artist` for each figure and `media-capture` for each screenshot, cast or combined capture that `doc-writer` listed. They return light/dark pairs and media paths; `doc-writer` embeds them.
4. **Gate** — run `python3 tools/docs/check.py`. Fix every failure (rebuild figures with their scripts, list media in `docs/assets/media.yaml`, complete front matter). Never weaken a check.
5. **Independent review** — dispatch `doc-reviewer` with only the changed pages, the evidence and the spec; not your reasoning. Record its verdict as `review:` in the Progress page front matter.
   - `changes`: send the required changes to `doc-writer`, then repeat 4–5. At most two revisions; after that set the step `blocked` and write an inbox entry.
   - `block`: stop, fix the cause (wrong claim, leaked data) before anything else.
6. **PR body** — for a PR, `doc-writer` generates the body from the Progress page (§7.2); check it with `python3 tools/docs/check.py --only pr-body --pr-title "<title>" --pr-body <file> --changed <file>`.
7. **Report** — print `DOCS  step=<id>  pages=<n>  figures=<n>  media=<n>  gate=pass|fail  review=<verdict> <score>/14`.
