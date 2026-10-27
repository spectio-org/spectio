# Dashboard

The Spectio dashboard is one self-contained HTML page. It is published as a claude.ai artifact and shows:
- the pipeline steps;
- the inbox decisions and their answers;
- the review findings;
- the MVP scope;
- every Markdown file and figure;
- the token usage.

Build it from the repository root, into a folder outside the repository (the page is about 12 MB):

```bash
OUT=$(mktemp -d)
python3 tools/dashboard/gen.py . "$OUT/data.json"   # steps, inbox, rounds, git; docs.json and imgs.json
python3 tools/dashboard/build.py "$OUT"             # writes $OUT/spectio-board.html
```

Then publish `$OUT/spectio-board.html` with the Artifact tool, passing `url` = https://claude.ai/artifact/VrNreQfsQvF6GBK3LUGW9C, so the link stays the same. The autopilot does this at the end of every tick (`.claude/skills/autopilot/SKILL.md` §5).

| File | Role |
|---|---|
| `gen.py` | Reads `pipeline.yaml`, `.autopilot/state.json`, `docs/reviews/inbox.md` (each entry's state is the italic marker that ends its last answer), the review rounds and git. |
| `build.py` | Fills `template.html` with that data, `extras.json` and the usage snapshots. |
| `extras.json` | The only hand-written content: the review round names and the MVP summary. Everything else is read from the repository. |
| `usage.py` | Counts the tokens and agents in one session's transcripts. |

**Usage across sessions.** Each cloud session runs in its own container, and its transcripts are gone when the container is reclaimed. So before a session ends, it snapshots its own numbers and commits them:

```bash
python3 tools/dashboard/usage.py ~/.claude/projects/<project-slug> .autopilot/usage/<session-id>.json
```

`build.py` merges every file in `.autopilot/usage/`. Rows are deduplicated by agent and workflow ID, so running the snapshot again in the same session only replaces its own file. These are token counts. The weekly-window percentage is a separate figure that only `/usage` shows, so the page does not show it.
