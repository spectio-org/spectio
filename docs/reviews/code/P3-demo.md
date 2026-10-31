# Code review · P3-demo, the public read-only demo at `/demo/`

`review-code` on `autopilot/P3-demo`, base `4c4e3ba` (UI parity C on `main`, promotion #110), 2026-10-31. Thomas asked for the 0.0.1 screens on the real site, to click through without a clone ("pourquoi un artifact ? vrai site ?", then "oui ajoute cela", quoted in the step's brief). The step is not a P1 plan task. It changes:

- the demo build (`web/src/demo/`, new: `stub.ts`, `DemoBanner.tsx`, `demo.css`, `index.ts`; `web/vite.config.ts`, `web/package.json`, `main.tsx`, `routes.tsx`): `npm --prefix web run build:demo` writes `web/dist-demo`, the real screens with the API answered from a recording, a banner and hash routing;
- three screens, behind `import.meta.env.MODE === "demo"`: the Launch button's disabled reason (`LaunchPage.tsx`), Open raw as a `blob:` URL (`RunDetailPage.tsx`); and the sidebar's height in `shell/shell.css`, which subtracts `--sp-demo-banner-h` (`0px` when unset);
- the recording: `web/demo/fixtures.json` (new, committed, public: 41 answers, 773 205 bytes) from `tools/media/record_demo.py` (new), with `tools/media/test_record_demo.py` (new) and a section of `tools/media/README.md`;
- the normal build's guard: `web/scripts/check-dist.mjs` (new), run by `npm run build`;
- publishing: `.github/workflows/previews.yml` builds the demo into `site/demo` and checks `$URL/demo/`; one reviewed `cache-poisoning` exception in `.github/zizmor.yml`;
- tests: `web/src/demo/stub.test.ts` (13) and `web/src/demo/demo.test.tsx` (5), new.

The reviewers were `code-reviewer` and `security-reviewer`, independent and in parallel, then `code-simplifier`. Format: [`README.md`](../README.md). The behaviour is owned by the [dev-env §7.3 note of 2026-10-31](../../specs/dev-environment-and-testing.md#73-the-ui-in-mock-mode-from-the-first-ui-milestone), which the docs commit wrote.

| Round | Head | code-reviewer | security-reviewer |
|---|---|---|---|
| 1 | `f769837` (the step) | **approve** (5 minors) | **approve** (4 minors) |
| 2 | `06b1117` (CR-P3DEMO-02 and SEC-P3DEMO-02 fixed) | **changes** (1 major, 2 minors) | **approve** (3 minors) |
| 3 | `25aa0c9` (CR-P3DEMO-03 r2 fixed) | **approve** (3 minors, 1 simplify) | **approve** (2 minors) |
| simplify | `8244642` | one change: the sidebar's height offset in one rule (CR-P3DEMO-05 r3), `shell.css` +1, `demo.css` −3 | |

**Finding IDs restart in each round**, so this record writes the round after an ID. CR-P3DEMO-04 (r2), CR-P3DEMO-07 (r3), SEC-P3DEMO-05 (r2) and SEC-P3DEMO-03 (r3) are the same gap: no CI job runs `tools/media/test_record_demo.py`.

**Test-first.** The CR-P3DEMO-03 (r2) fix adds the test that pins it. `doc-writer` re-ran it against the banner before the fix, with the test of `HEAD`: on `06b1117`'s `DemoBanner.tsx` it fails (`expected '' to be '49px'`), and it passes at `HEAD` ([P3-M4 Evidence](../../progress/W5/P3-M4.md#public-demo-p3-demo_1)).

Gate at `8244642`, from the worktree, re-run by `doc-writer`:

```bash
uv run --locked pytest -q        # 510 passed, 1 failed (test_sigterm_stops_cleanly, run beside a browser check);
                                 # alone: 1 passed. No file under packages/ changed. FU-P3-19 holds that test.
uv run --locked ruff check .     # All checks passed! (tools/ is outside ruff's include)
uv run --locked mypy packages    # Success: no issues found in 81 source files
uv run --locked lint-imports     # Contracts: 4 kept, 0 broken.
python3 -m unittest tools/media/test_record_demo.py   # Ran 3 tests, OK
cd web && npx vitest run         # 17 files, 158 tests passed
cd web && npx tsc --noEmit       # exit 0
npm --prefix web run build       # ... dist: 6 files, none of the demo (8 needles)
npm --prefix web run build:demo  # web/dist-demo; Vite's 500 kB chunk warning (CR-P3DEMO-05 r1)
```

`ruff check tools/media/record_demo.py tools/media/test_record_demo.py` reports 4 errors (CR-P3DEMO-04 r3, open).

```text
CODE  step=P3-demo  review=approve b/M/m=0/1/10  security=approve b/M/m=0/0/9  rounds=3  simplify=changed -4/+1  tests=pass
```

The counts add up the three rounds of each reviewer. The one `simplify` finding is not counted.

## Findings

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3DEMO-01 (r1) | minor | `cp -R web/dist-demo site/demo` copies into `site/demo/dist-demo/` if `site/demo` already exists, as it would if the docs got `docs/demo.md` or `docs/demo/index.md`; the `curl $URL/demo/` check would still pass on the docs page. | **open**: follow-up FU-P3-28. The docs commit adds no such page (the nav links `/demo/` as an absolute path) and the [dev-env §7.3 note](../../specs/dev-environment-and-testing.md#73-the-ui-in-mock-mode-from-the-first-ui-milestone) forbids one |
| CR-P3DEMO-02 (r1) | minor | The sticky sidebar's height counted only the top bar, so its foot (status pill, account line) began about 31 px below the fold on every desktop page. | fixed in `06b1117`, then again in `25aa0c9` (CR-P3DEMO-03 r2): the sidebar subtracts the banner's measured height |
| CR-P3DEMO-03 (r1) | minor | Inspecting a pipeline that was not recorded answers `422` naming the recorded ones; the brief said an unknown path answers `404`. | recorded as decided in the dev-env §7.3 note *(assumed — standing rule)*: the `422` tells a visitor which pipelines work |
| CR-P3DEMO-04 (r1) | minor | `READ_ONLY` is the last check of `reason()`, so a visitor first meets "x is required" or invalid JSON and may fill the form before learning that launching is off. Only `nf-core-demo` (no schema) is tested. | **open**: FU-P3-28 |
| CR-P3DEMO-05 (r1) | minor | `build:demo` prints Vite's "Some chunks are larger than 500 kB" for the 830 kB demo chunk, mostly the fixtures string. | **open**: FU-P3-28 |
| SEC-P3DEMO-01 (r1) | minor | The hygiene gate runs the `fixtures.yaml` denylist over JSON encoded twice; quoting defeats the adjacency patterns (the account-root rule never fires on `"account":"root"`). The brief's allowlist (alice, login1, `/g/demo-lab`) is not enforced. | **open**: FU-P3-28 |
| SEC-P3DEMO-02 (r1) | minor | The public fixtures published the recording sandbox's kernel build, `System: Linux <release>`, in each Nextflow engine log. | fixed in `06b1117`: `neutral()` cuts the line to `System: Linux`, `problems()` refuses the recorder's `platform.release()`; the committed file rewritten; three tests |
| SEC-P3DEMO-03 (r1) | minor | The demo build runs the whole `web/` npm tree in the job bound to the `previews` environment; later steps hand `CLOUDFLARE_API_TOKEN` to `npx wrangler`, and earlier code can steer them through `GITHUB_PATH`, `GITHUB_ENV` or workspace files. | **open**: FU-P3-28 (a job without the environment, `site/demo` as an artifact); [inbox #92](../inbox.md#92-assumed-what-the-public-demo-leaves-open-before-it-is-published) |
| SEC-P3DEMO-04 (r1) | minor | Only the JS stub keeps requests in the page: the site has no `_headers` and no CSP, so `/demo/` runs without one on the docs origin. The Playwright origin check is not in the repo or CI. | **open**: FU-P3-28; inbox #92 |
| CR-P3DEMO-03 (r2) | major | The fix of CR-P3DEMO-02 cut the banner to one line with an ellipsis from about 768 to 1350 px and hid its second sentence below 768 px (`display:none`, out of the accessibility tree too). That sentence is the demo's only disclosure that times are moved and that `nf-core/demo` is a renamed copy, not an nf-core pipeline. | fixed in `25aa0c9`: the whole text wraps at every width; `DemoBanner` measures itself and sets `--sp-demo-banner-h` (CSSOM, a `ResizeObserver`); with a test |
| CR-P3DEMO-04 (r2) | minor | No CI job runs `tools/media/test_record_demo.py`; `uv run pytest` collects only `packages/`. | **open**: FU-P3-28 |
| CR-P3DEMO-05 (r2) | minor | `problems()` tests `platform.release() in text` with no guard for `''`, which Python returns when the release is unknown and which is in every string. | **open**: FU-P3-28 |
| SEC-P3DEMO-05 (r2) | minor | The same CI gap as CR-P3DEMO-04 (r2): a hand edit or a merge of `fixtures.json` could bring a leak back with no check failing. | **open**: FU-P3-28 |
| SEC-P3DEMO-06 (r2) | minor | The kernel guard knows only the recorder's machine; with `--base` on another host, that server's release and host name pass unless `sanitize.leaks` catches them. | **open**: FU-P3-28; written into `tools/media/README.md` by the docs commit |
| SEC-P3DEMO-07 (r2) | minor | Commit `f769837` still holds the kernel build four times; the branch is not on origin yet. | **open**: [inbox #92](../inbox.md#92-assumed-what-the-public-demo-leaves-open-before-it-is-published), option (b) assumed: the PR from a branch whose history does not hold `f769837` |
| CR-P3DEMO-04 (r3) | minor | `ruff` fails on the changed recorder and its test (E501 three times, RUF100 once); `pyproject.toml`'s ruff `include` leaves out `tools/`, so the gate does not see it. | **open**: FU-P3-28 |
| CR-P3DEMO-05 (r3) | simplify | `demo.css` copied `shell.css`'s `100vh - 86px` into a second sidebar rule. | fixed in `8244642` by `code-simplifier` |
| CR-P3DEMO-06 (r3) | minor | The new banner test undoes its stubs at the end of its body; a failing `expect` would leak the `getBoundingClientRect` spy and the `ResizeObserver` stub into the next tests. | **open**: FU-P3-28 |
| CR-P3DEMO-07 (r3) | minor | Same gap as CR-P3DEMO-04 (r2). | **open**: FU-P3-28 |
| SEC-P3DEMO-03 (r3) | minor | Same gap as SEC-P3DEMO-05 (r2), with the published URLs named. | **open**: FU-P3-28 |
| SEC-P3DEMO-04 (r3) | minor | The engine logs still describe the sandbox: the Ubuntu 24.04 JDK build, `CPUs: 4 - Mem: 13.4 GB`, and the locale. No credential, no internal host name: hardening only. | **open**: FU-P3-28 |
