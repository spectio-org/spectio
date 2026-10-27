# Code review · dashboard tooling and the autopilot skill

`review-code` on `autopilot/dashboard-review`, range `b24511a..cddb67b` (commits `3217ee4`, `2550a27`, `f7f14d1`, `cddb67b`, which reached the integration branch with no review), fixed from base `0e33427`, 2026-10-27, tick 8. Reviewers: `code-reviewer` and `security-reviewer`, independent, in parallel. Thomas allowed a third fix round (session message, 2026-10-27). Format: [`README.md`](../README.md).

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `cddb67b` | changes (0 blockers, 3 majors, 9 minors) | changes (0 blockers, 4 majors, 5 minors) |
| 2 | `a47b81c` | changes (0 blockers, 2 majors, 5 minors) | changes (0 blockers, 2 majors, 6 minors) |
| 3 | `b065ef2` | changes (0 blockers, 1 major, 6 minors) | approve (0 blockers, 0 majors, 4 minors) |
| 4 | `263ca9a` | **approve** (0 blockers, 0 majors, 4 minors) | **approve** (0 blockers, 0 majors, 2 minors) |

The round-4 minors were fixed in `c940bcf`. No separate `code-simplifier` pass: no reviewer found code to simplify after round 1, and its three simplify items (CR-010 to CR-012) were applied in the fix rounds. Test command, passing at `c940bcf`:

```bash
OUT=$(mktemp -d); python3 tools/dashboard/gen.py . "$OUT/data.json" && python3 tools/dashboard/build.py "$OUT" \
  && node tools/dashboard/check_xss.js "$OUT" && python3 tools/dashboard/test_usage.py
```

```text
CODE-REVIEW  verdict=approve  blockers=0  majors=0  minors=4  simplify=1
SECURITY-REVIEW  verdict=approve  blockers=0  majors=0  minors=2
```

## Findings

All applied. One line each; the reviewers' full evidence is in the session of 2026-10-27, tick 8.

| ID | Severity | Finding | Applied in |
|---|---|---|---|
| SEC-1 | major | Repository Markdown rendered with `innerHTML` unsanitised, in a page that can write answers | `35ae6f4` (DOMPurify, link scheme filter, mermaid `strict`, `check_xss.js`) |
| SEC-2 / CR-001 | major | Dashboard answers never applied, and an unaudited command channel into the autopilot | `35ae6f4`, `a47b81c` (copied into `inbox.md` as data, skill §0.3) |
| SEC-3 | major | Owner-only write claimed but not configured | `35ae6f4` (`db` rule `write: owner` at publish) |
| SEC-4 | major | CDN scripts without SRI; mermaid 10.9.1 vulnerable ([CVE-2025-54881](https://osv.dev/vulnerability/CVE-2025-54881)) | `35ae6f4` (SRI on marked 12.0.2, DOMPurify 3.4.17, mermaid 10.9.8) |
| CR-002 | major | Hand-kept values in `gen.py` and the template | `35ae6f4` |
| CR-003 | major | Readiness logic copied from `ready.py` and already different | `35ae6f4` (`gen.py` calls `ready.py --only`) |
| SEC-5…9, CR-004…012 | minor | Path containment, single-pass substitution, usage scope, fonts, data exposure note, naming, dedup, relative paths, git errors, playbook, MVP duplication, simplifications | `35ae6f4`, `a47b81c` |
| SEC-10 | major | Sanitised Markdown could make the owner's browser write answers through `data-ans-*` | `b065ef2` (`ALLOW_DATA_ATTR: false`, forbidden form tags, owner and page-built form required) |
| SEC-11 / CR-101 | major | `usage.py` took the newest transcript of every project | `b065ef2` (session id or repository cwd, `test_usage.py`) |
| CR-102 | major | Inbox batch hard-coded in the template | `b065ef2` |
| SEC-12…17, CR-103…107 | minor | Remote media, page restyling, comments, pre-rule answers, refusal retry, check coverage, snapshot summaries, anchors, open marker, capabilities, temp dirs | `b065ef2` |
| CR-201 / SEC-18 | major | Remote media still fetched (`srcset`, `audio`, `background`, SVG `image`, mermaid labels) | `00df86e` |
| SEC-19…21, CR-202…207 | minor | Overlay classes, mermaid answer controls, first-publish record, usage failure, cleanup, withdraw wording, wait, guard comment | `00df86e`, `263ca9a` |
| SEC-22, SEC-23, CR-208…211 | minor | SVG `url()` attributes, mermaid `themeCSS`, clipped borders and focus rings, CSP pass wording, `id@at` pairs, style exemption | `c940bcf` |

## Still open

- Whether the claude.ai host applies the page's meta CSP **[to be validated]**; the sanitiser is the tested defence.
- No CI job runs `check_xss.js` yet (`.github/` was outside the fix's files); the autopilot runs it before every publish (skill §5).
- The pre-rule `answers` documents could not be deleted from this session (the permission classifier refused); they are recorded as `id@at` at the first rule-bearing publish and ignored unless Thomas confirms them.
