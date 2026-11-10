---
icon: material/bookshelf
---
# Your pipeline catalog on Launch

!!! note "Built on the integration branch, not released yet"

    The catalog file, its routes and its pages (steps FU-P3-87a to FU-P3-87d, batch [P3-B14](../progress/W5/P3-M9.md#batch-p3-b14)) and the picker on Launch (FU-P3-87e, batch [P3-B13](../progress/W5/P3-M9.md#batch-p3-b13)) work today from a checkout, 2026-11-10. The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). The screens below come from servers seeded by `tools/media/b13_demo.py` and `tools/media/b14_demo.py`, not from a pipeline run.

The catalog is a short list of pipelines you use often, each under a name. Launch lets you pick one instead of typing its path again. The fields, the file and the routes are owned by [api §5.6](../specs/api-and-data-model.md#56-pipeline-catalog-001); the screens by [ui-spec §4.7.1](../specs/ui-spec.md#471-pipeline-catalog-in-001).

## What an entry holds

| Field | Meaning |
|---|---|
| name | lower case, starts with a letter, at most 32 characters |
| label | optional, shown instead of the name |
| engine | Nextflow or Snakemake |
| location | an absolute path, or a Git repository such as `nf-core/rnaseq` |
| revision | required for a repository, not allowed for a path |
| profile | optional, the profile selected at Launch |
| params file | optional, a JSON or YAML file inside the pipeline, such as `conf/test.yaml` |

The list is kept in `catalog.toml`, next to `spectio.toml` and `environments.toml`. It is yours: the server reads the file again on each request, so a hand edit shows the next time the list is read.

## The Catalog page

The page is `/catalog`, reached from Home ("Your catalog") and from **Manage catalog** on Launch. Its heading reads Launch › Catalog, and the sidebar marks Launch. It mirrors the [Environments](environments.md) page.

![The Catalog page: three cards, Liver QC (Snakemake), nf-core-rnaseq (Nextflow, at 3.27.0, profile test) and RNA-seq test (Nextflow, profile test, parameters from conf/test.yaml), each with Edit and Delete, and Add pipeline at the top right](../assets/shots/app-catalog_light.webp#only-light)
![The Catalog page: three cards, each with Edit and Delete, and Add pipeline at the top right](../assets/shots/app-catalog_dark.webp#only-dark)

*Three demo entries in a seeded `catalog.toml`. The line under the cards names the file, "Saved in /srv/demo-b14/data/catalog.toml".*

- **One card per entry:** its label (or its name), the engine, the name when there is a label, the location with `@revision` for a repository, and "profile test · parameters from conf/test.yaml" when set.
- **Add pipeline** opens an empty form. **Edit** and **Delete** are named per entry ("Edit rnaseq-test") for a screen reader. **Back to Launch** is above the heading.
- **Delete asks first:** "Delete rnaseq-test? It leaves your catalog and the picker at Launch. Runs launched from it keep their pipeline." A dialog on a desktop, a bottom sheet on a phone. A refusal that changed nothing (the entry changed in another tab, the file changed on disk, the file cannot be changed) adds "Reload reads it again; nothing was deleted." A network failure or a 5xx shows only its message, because the server may already have deleted the entry; **Reload** stays.
- **On a phone** the whole card is one link to the entry's page, and **More for this entry** under its form holds **Delete**.
- **When the file cannot be read,** the page says so under the heading and **Add pipeline** waits, with its reason ("Waits until the mistake in the file is fixed"). The wordings are in [When the catalog cannot be read](#when-the-catalog-cannot-be-read).

### The entry form

![The form of the entry rnaseq-test: Name (read only), Label, Engine Nextflow, Pipeline, Default profile, Params file, Save and Cancel](../assets/shots/app-catalog-entry_light.webp#only-light)
![The form of the entry rnaseq-test, dark](../assets/shots/app-catalog-entry_dark.webp#only-dark)

*The heading takes focus when the page opens, which is the purple frame around "RNA-seq test".*

- **Fields:** Name, Label (optional, at most 80 characters), Engine (Nextflow or Snakemake), Pipeline, **Revision** (shown only when Pipeline is a repository, and required then), Default profile, Params file. The table [What an entry holds](#what-an-entry-holds) has the rules.
- **A rule shows once you type in the field,** for example "Lowercase letters, digits and '-', up to 32, starting with a letter", "Required for a repository", "A .json, .yaml or .yml file". **Save** stays focusable and says why it waits ("Fix Pipeline first"). A `422` from the server lands on its field; "An entry named x exists" lands on Name.
- **The name cannot change** once saved: "delete the entry and add it again under a new name."
- **Saving checks how the fields are written, not that the pipeline exists:** Launch reads it. This is the line above Save.
- **A conflict** ("This entry changed in another tab.", "The file changed on disk since this page read it.") shows a banner with **Reload**, which discards your changes.
- After **Save** the list opens with "Saved rnaseq-test" read out and the focus on that card; after **Cancel** the focus returns to the button that opened the form.
- **A known wrong line:** the form's last line reads "Saving rewrites ~/.spectio/catalog.toml" whatever the data directory is. The list's "Saved in" line names the real file ([DW-P3B14-03](../reviews/code/P3-B14.md#findings)).

## On the API

The routes are `GET` and `POST /catalog` and `GET`, `PUT` and `DELETE /catalog/{name}`, with an `ETag` and `If-Match` as for environments; an entry is a shortcut, not a launch value. The workflow inspect route takes the entry's `params_file` and answers `values: null` with a fixed error ("not JSON", "not YAML") when the file does not parse, never a `500` ([api §5.6](../specs/api-and-data-model.md#56-pipeline-catalog-001)). Against the demo server of the screens above (`/api/v1`, signed in as `alice`):

```console
GET /catalog
200  items: [liver-qc, nf-core-rnaseq, rnaseq-test]   file: state "ok"
```

## Pick an entry

On Launch, the Pipeline section starts with **From your catalog**, a list whose first choice is None.

![Launch with the entry RNA-seq test chosen and loaded: the entry line, the Loaded card with In your catalog as rnaseq-test and Edit](../assets/shots/app-launch-catalog_light.webp#only-light)
![Launch with the entry RNA-seq test chosen and loaded: the entry line, the Loaded card with In your catalog as rnaseq-test and Edit](../assets/shots/app-launch-catalog_dark.webp#only-dark)

*The entry `rnaseq-test` chosen, then **Load**. The line under the list says "From the catalog: rnaseq-test · profile test · parameters from conf/test.yaml". The summary on the right names the entry beside the pipeline.*

- **Choosing an entry only fills the form**: the Pipeline field, the revision and the engine. Nothing is read until you press **Load**, so moving through the list with the arrow keys fetches nothing.
- **The engine is the entry's.** It counts as your choice, and the engine line says "Nextflow, from the catalog entry".
- **The profile** is selected for you when the pipeline has it, unless you already changed it.
- **The params file** fills the fields, which then read "changed". The page lists what it could not place: "3 values of conf/test.yaml fill the form and read changed" in the shot, or "2 values … have no field in this form, and are not sent" when some do not fit. A value that loads code or configuration is named under **Before Launch** as a warning. It does not stop the launch.
- **Editing Pipeline or Revision** puts the list back on None and forgets the entry's values. **None** keeps your fields and drops only the entry line. **Clear and start empty** empties the form.
- **A pipeline that is gone** (a path removed, a revision not found) fails at Load, with the error on the field and "From your catalog entry rnaseq-test: edit it in Manage catalog".

## Manage catalog and Save to catalog

**Manage catalog** opens the list in a dialog, so you never leave the form. On a phone it is a full-height sheet.

![Manage catalog open over Launch: Add pipeline, then one card each for Liver QC, nf-core-rnaseq and RNA-seq test, each with Edit and Delete](../assets/shots/app-launch-catalog-manage_light.webp#only-light)
![Manage catalog open over Launch: Add pipeline, then one card each for Liver QC, nf-core-rnaseq and RNA-seq test, each with Edit and Delete](../assets/shots/app-launch-catalog-manage_dark.webp#only-dark)

- **Add pipeline**, **Edit** and **Delete** act on `catalog.toml`. Edit replaces the list with the form, with **Back**.
- **Save to catalog** sits in the Loaded card once a pipeline has loaded. It opens the same form with the location, revision, engine and profile filled in, and a name made from the pipeline's. For a pipeline loaded from an entry the card says "In your catalog as rnaseq-test" and offers **Edit**, so nothing is saved twice.
- **Edits show at once.** The entry you loaded is read from the live list, so an edit or a delete in the dialog changes the card without a reload.
- **Delete** says "Runs launched from it keep their pipeline."

## When the catalog cannot be read

| State | What Launch says |
|---|---|
| loading | "Loading the catalog…" |
| read failed | "The catalog could not be read." with **Retry** |
| file refused | "Spectio does not read your catalog file: see Manage catalog" |
| file invalid | "Your catalog file has a mistake: see Manage catalog" |
| file unreachable | "Your catalog cannot be read right now", with **Retry** |
| no entry | "Your catalog is empty. Load a pipeline, then Save to catalog." |

In every state the free Pipeline field and **Try a test pipeline** still work. Save to catalog waits, with its reason, until the catalog can be read. A test pipeline whose location and revision are already in your catalog is left out of Try a test pipeline.

## Not built in 0.0.1

A Launch action on each entry, a link such as `/launch?catalog=`, browsing nf-core or the Snakemake catalogue, shared catalogs, and checking a path on save: [ui-spec §4.7.1, Later](../specs/ui-spec.md#471-pipeline-catalog-in-001).

## Not shown

- The phone view of the Catalog page and of its form (batch P3-B14), a file in the refused, invalid or unreachable state, the Delete dialog, and a saved entry: not captured. The tests cover them (`CatalogPage.test.tsx`, 17 tests).
- The phone view of the picker and of the dialog: the batch did not capture it. The tests cover the phone sheet ([`LaunchCatalog.test.tsx`](https://github.com/spectio-org/spectio/blob/HEAD/web/src/launch/LaunchCatalog.test.tsx)), and the focus return on Cancel and Escape has no test yet (CR-P3FU87E-04, open).
- The file states (refused, invalid, unreachable) on screen: the server was seeded with a good file.
