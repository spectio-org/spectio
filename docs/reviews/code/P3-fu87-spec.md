# Pre-review · FU-P3-87, minimal pipeline catalog (design only)

Step `P3-fu87-spec` on `autopilot/P3-fu87-spec`, base `a8bba4a7`, 2026-11-10. The step writes the design of FU-P3-87 ([decision log](../../decisions/log.md#2026-11-10-minimal-pipeline-catalog-in-001-fu-p3-87-assumed), [inbox #147](../inbox.md#147-assumed-minimal-pipeline-catalog-in-001-fu-p3-87)); it changes no code, so `code-reviewer`, `code-simplifier` and the tests do not run.

There is no `CODE` line in this record: the step changes no code, so there is no code to review.

Reviewed sections:
- [api §5.6](../../specs/api-and-data-model.md#56-pipeline-catalog-001), new, and §4.1 (three problem slugs);
- [ui-spec §4.7.1](../../specs/ui-spec.md#471-pipeline-catalog-in-001), new, and the pointer in §4.6.

## Rounds

| Round | Who | Independent | security | UX |
|---|---|---|---|---|
| R0 | the design worker, while writing the design (commit `de685218`) | **no** | not scored | not scored |
| R1 | `security-reviewer` and `ux-reviewer`, run by the coordinator on `de685218`, in parallel | yes | **changes 0/2/5** | **changes 0/4/8** |

Every R1 finding is applied below; none is rejected. The design in the specs is the one after R1.

## Round R1 (independent)

```text
SECURITY-REVIEW  verdict=changes  blockers=0  majors=2  minors=5
UX-REVIEW        verdict=changes  blockers=0  majors=4  minors=8
```

### Security (`security-reviewer`)

| ID | Sev. | Finding | Applied |
|---|---|---|---|
| SEC-PRE-FU87-01 | major | The params file is an import (api §5, req. 16): the form drops hidden fields (`schemaFields.ts:105`, nf-core `custom_config_base`) and `_check_params` skips inferred or missing schemas (`runs_write.py:104`), so "the file can only hold what the form can send" was false. | yes: api §5.6 "The params file is an import" (`values` with every key, `code_loading` from `relaunch.code_loading`, the file itself flagged for a local pipeline); ui-spec §4.7.1 lists every unplaced value and warns on each code-loading one before Launch; tests `test_req18_catalog_params_hidden_key_listed`, `_code_loading_flagged`; inbox #147 choice 3 |
| SEC-PRE-FU87-02 | major | An entry model in `spectio.envfile` reusing the checks of `spectio_server.api.workflows` makes the core import the server, and those raise `Invalid` (a plain `Exception`, `problems.py:22`), which pydantic does not catch: a bad value in `catalog.toml` would give a `500` and crash `spectio doctor`. | yes: api §5.6 "One set of checks, in the core package" (`spectio.locations` raising `ValueError`, `spectio.catalog`, the server wraps in `Invalid`, `detail` never quotes the value); test `test_req18_catalog_file_bad_value_invalid`; inbox #147 choice 11 and FU-P3-87a |
| SEC-PRE-FU87-03 | minor | Every params-file read failure must give `values: null`, never `422` or `500`; its own `try`, not `inspect_dir`'s (`:415-416`); the error cleaned and capped; depth refused over 32; missing told apart from linked. | yes: api §5.6 inspect "Every failure…" and the read-failure tests (depth 33, FIFO, not UTF-8, 10,000 nested `[`) |
| SEC-PRE-FU87-04 | minor | A bad `params_file` must be refused before `resolve`, so no `git` fetch runs. | yes: api §5.6 "Checked before anything is fetched", and the test that `run_git` is not called |
| SEC-PRE-FU87-05 | minor | Say that `If-Match: *` is refused with `428`; a `PUT` body `name` other than the path gets `422` on `name`. | yes: api §5.6 routes table and tests |
| SEC-PRE-FU87-06 | minor | The cache is filled once per revision (`fetch`, `workflows.py:214`), so a branch is never updated. | yes: api §5.6 "What exists" and the Revision hint of ui-spec §4.7.1; recording the fetched commit is Later |
| SEC-PRE-FU87-07 | minor | Cap the params file below inspect's 1 MiB `MAX_FILE`, or parse it once. | yes: 256 KiB and parsed once (api §5.6) |

### UX (`ux-reviewer`)

| ID | Sev. | Finding | Applied |
|---|---|---|---|
| UX-PRE-FU87-01 | major | Manage catalog left Launch and discarded the form (refused in §4.8.1, UX-PRE-FU86-R1-20), with nothing leading back. | yes: Manage catalog is a dialog on Launch; `/catalog` is headed "Launch › Catalog" with Back to Launch, Launch marked in the sidebar, and Home's "Your catalog" link (ui-spec §4.7.1; inbox #147 choice 7). The `sessionStorage` alternative is not taken: the dialog leaves nothing to restore |
| UX-PRE-FU87-02 | major | Arrow keys on a closed `<select>` fire `change` per option in some browsers **[to be validated]**, each an inspect or a fetch. | yes: choosing only fills the form, Load starts the inspect (ui-spec §4.7.1; inbox #147 choice 5) |
| UX-PRE-FU87-03 | major | The params prefill was silent on keys with no field, reserved keys, Nextflow maps, Snakemake dotted keys and wrong types. | yes: the polite listing line with Copy's words, the wrong type as the field's error (ui-spec §4.7.1, merged with SEC-PRE-FU87-01) |
| UX-PRE-FU87-04 | major | Missing states: an entry whose pipeline is gone; the page's loading, list error, `refused`, `unreachable`, `404`, `412` and delete dialog; Save to catalog while the catalog loads or after its read failed. | yes: ui-spec §4.7.1 "An entry whose pipeline is gone", "States of the list and the form", Save to catalog's reasons; board LiteCatalogStates added to FU-P3-87c |
| UX-PRE-FU87-05 | minor | None should clear only the entry line; another entry replaces the form with "Clear and start empty". | yes: ui-spec §4.7.1 "Changing the choice" |
| UX-PRE-FU87-06 | minor | The entry's profile stays when the Environment changes; one line when both profiles are missing; Copy to a new launch and the picker. | yes: ui-spec §4.7.1 "The profile prefill"; inbox #147 choice 6 |
| UX-PRE-FU87-07 | minor | Save to catalog's name: slug, 32 characters, `-2` on a clash; "In your catalog as …" with Edit for a pipeline loaded from an entry. | yes: ui-spec §4.7.1 Save to catalog |
| UX-PRE-FU87-08 | minor | Short option text on the phone, the location as a line under the select; Manage catalog at 44 px. | yes: ui-spec §4.7.1 "The picker" |
| UX-PRE-FU87-09 | minor | Phone Catalog cards as links to the entry's page (UX-PRE-FU86-R1-22). | yes: ui-spec §4.7.1 the list, phone |
| UX-PRE-FU87-10 | minor | Leave out Try buttons already in the catalog; a fixed-height picker skeleton. | yes: ui-spec §4.7.1 "Try a test pipeline" and "States" |
| UX-PRE-FU87-11 | minor | The entry and empty lines as `role="status"`; Before Launch names the entry. | yes: ui-spec §4.7.1 "The entry line" and "With no entry" |
| UX-PRE-FU87-12 | minor | The entry's engine wins over the guess as a user choice (§4.6, UX-G2-07), with "Nextflow, from the catalog entry". | yes: ui-spec §4.7.1 "Choosing an entry" |

## Open

- **[to be validated]**: `change` per option on a closed `<select>` (UX-PRE-FU87-02), moot for the design since choosing no longer fetches; whether the EMBL login nodes reach GitHub (ui-spec §4.7).
