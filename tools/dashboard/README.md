# Dashboard

The Spectio dashboard is one self-contained HTML page. It is published as a claude.ai artifact and shows:
- the pipeline steps;
- the inbox decisions and their answers;
- the review findings;
- the MVP page (`docs/specs/mvp-0.0.1.md`, rendered as committed);
- every Markdown file and figure;
- the token usage.

Build it from the repository root, into a folder outside the repository (the page is about 12 MB):

```bash
OUT=$(mktemp -d)
python3 tools/dashboard/gen.py . "$OUT/data.json"   # steps, inbox, rounds, git; docs.json and imgs.json
python3 tools/dashboard/build.py "$OUT"             # writes $OUT/spectio-board.html
node tools/dashboard/check_xss.js "$OUT"            # hostile Markdown must not run (Playwright); before every publish
```

`check_xss.js` needs Playwright and its Chromium. It finds them on `NODE_PATH`, or where `dev/bootstrap.sh` installs them (`$SPECTIO_HOME/npm/node_modules`, `dev/lib.sh`); otherwise run `dev/bootstrap.sh`, or set `NODE_PATH` to a `node_modules` that has `playwright`. Behind a proxy, it passes `HTTPS_PROXY` to Chromium.

Then publish `$OUT/spectio-board.html` with the Artifact tool, passing `url` = https://claude.ai/artifact/VrNreQfsQvF6GBK3LUGW9C, so the link stays the same, and these capabilities:

```json
{"db": {"rules": [{"path": "answers", "read": "view", "write": "owner"}]}}
```

Sources: claude.ai Artifact runtime contract 0.2.91, `db.d.ts` and `user.d.ts`, read 2026-10-27 in the artifact-capabilities skill.
- **The `db` rule.** `db` holds the answers typed on the page. By default, Contributors (`interact`) and up may write shared documents. A rule sets a per-path minimum (`view` < `interact` < `admin` < `owner`), so this one lets every viewer read the answers and only the owner (Thomas) write them.
- **No `user` capability.** The page shows the answer form to the owner only, with `user.isOwner()`, which needs no declaration and never rejects.
- **Across republishes.** The database survives them ("surviving reloads, republishes, and sessions"), and rules are "fixed at publish". The autopilot restates the rule on every publish (`.claude/skills/autopilot/SKILL.md` §5). The artifact-capabilities skill says that a publish which omits `capabilities` keeps the stored declaration; this page does not rely on that.

**First publish with the owner-only rule:** not yet published with the rule. Answers dated before that time are ignored (SKILL §0, step 3), because any Contributor could write them.

| File | Role |
|---|---|
| `gen.py` | Reads `pipeline.yaml`, `.autopilot/state.json`, `docs/reviews/inbox.md` (each entry's state is the italic marker that ends its last answer), the review rounds and git. Whether a step is ready comes from `tools/autopilot/ready.py`, which owns the rule. |
| `build.py` | Fills `template.html` with that data and the usage snapshots. |
| `extras.json` | The only hand-written content: the titles of the steps that `docs/playbooks/next-phase.md` has no `### <id> · <title>` heading for (W0, triage, apply, GO). Everything else is read from the repository: round names from each review file's first heading, the MVP view from its page. |
| `usage.py` | Counts the tokens and agents of the current session from its transcripts; `test_usage.py` tests that it picks that session only. |
| `check_xss.js` | Builds the page with a hostile Markdown file and checks in Chromium: no payload runs; the Markdown cannot write an answer, even for the owner; and no script, handler, form control, style, id, stray comment, unsafe link or remote media is left. |

**Answers typed on the page.** On an open, assumed or partial inbox entry, the owner can accept the recommendation or type an answer; it is stored in the `answers` collection, one document per entry. The page applies nothing. The next autopilot tick copies each answer into `docs/reviews/inbox.md` as an `Answer` line, as data for that entry's question only, and the entry stays open until Thomas confirms it in a session or a commit (`.claude/skills/autopilot/SKILL.md` §0, step 3). Whether ArtifactData shows who wrote a document is not documented, so the tick relies on the owner-only write rule above.

**Libraries.** Loaded from cdnjs, pinned, with Subresource Integrity (`integrity="sha384-…"`, computed from the downloaded file with `curl -sL URL | openssl dgst -sha384 -binary | openssl base64 -A`, and matching the SHA-512 that the cdnjs API publishes, 2026-10-27):

| Library | Version | sha384 |
|---|---|---|
| marked | 12.0.2 | `/TQbtLCAerC3jgaim+N78RZSDYV7ryeoBCVqTuzRrFec2akfBkHS7ACQ3PQhvMVi` |
| DOMPurify | 3.4.17 | `P0JNneQf81HOl9VwNXK76cQ9VMD6Nfsnepxb0cCOg8+UzEdzgPHAPV4wVQrvYQSx` |
| mermaid | 10.9.8 | `N3QqR/7q+xm3BGX+CBbNI8AUmRRqcsDzToy+0z1NLDI0QmTKW8zvwLvqulJgk3dP` |

- Every marked output is sanitised with DOMPurify before it reaches the page. The sanitiser drops `data-*` attributes, ids, inline styles, `style` elements, forms and form controls, and every comment except the `<!--cls:…-->` image markers. The page's answer controls work only for the owner, and only inside the form the page built for that entry.
- Links keep only `http`, `https`, `mailto`, relative and `#` targets. Images and videos that are not embedded are never fetched: a remote image becomes a link to it. mermaid runs with `securityLevel: "strict"`.
- mermaid 10.9.1 had CVE-2025-54881 ([OSV](https://osv.dev/vulnerability/CVE-2025-54881)). 10.9.8 is the newest 10.x on cdnjs, and OSV lists no advisory for it (query of 2026-10-27). The 11.x line needs 11.16.1 for the advisories of 2026-08-06 (for example [GHSA-6x64-9x62-f2gx](https://osv.dev/vulnerability/GHSA-6x64-9x62-f2gx)), and cdnjs stops at 11.15.0.
- To bump a library, recompute its hash, then run `check_xss.js`: a wrong hash stops the script from loading, and the check fails.

**Data exposure.** The page embeds:
- every git-tracked Markdown file except `.claude/skills/` and `spikes/`, and the git-tracked images and videos they reference (no symlinks, nothing outside the repository);
- the pipeline state, the inbox, the review counts, the branch, the head commit and the last 15 commit subjects on `main`;
- the token usage (agent types, task labels cut to 80 characters, no prompts or workflow summaries).

That is most of a private repository. Keep the artifact private, as it is created, and never share it. If it was shared by mistake, unshare it on claude.ai **[to be validated: where the sharing settings are]**, or delete it (Artifact tool `action: "delete"`, which stops the link for everyone), then publish a new one and update the link above.

**Usage across sessions.** Each cloud session runs in its own container, and its transcripts are gone when the container is reclaimed. So before a session ends, it snapshots its own numbers and commits them:

```bash
python3 tools/dashboard/usage.py .autopilot/usage
```

The current session's transcript under `~/.claude/projects/` is the one named after `$CLAUDE_CODE_SESSION_ID`. In a Claude Code cloud container that variable equals the transcript's file name (seen 2026-10-27; **[to be validated]** elsewhere). Without the variable, it is the one transcript whose records carry the repository root as `cwd`. The script exits with an error when neither finds exactly one. The file is named after the transcript, so running the snapshot again in the same session replaces its own file. `build.py` merges every file in `.autopilot/usage/`. Rows are deduplicated by agent and workflow ID; on a duplicate, the row with more calls, then the later end, wins. These are token counts. The weekly-window percentage is a separate figure that only `/usage` shows, so the page does not show it.
