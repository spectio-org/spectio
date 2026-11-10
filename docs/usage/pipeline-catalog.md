---
icon: material/bookshelf
---
# Your pipeline catalog on Launch

!!! note "Built on the integration branch, not released yet"

    The catalog file, its routes and its pages (steps FU-P3-87a to FU-P3-87d) and the picker on Launch (FU-P3-87e, batch [P3-B13](../progress/W5/P3-M9.md#batch-p3-b13)) work today from a checkout, 2026-11-10. The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). The screens below come from a server seeded by `tools/media/b13_demo.py`, not from a pipeline run.

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

- The phone view of the picker and of the dialog: the batch did not capture it. The tests cover the phone sheet ([`LaunchCatalog.test.tsx`](https://github.com/spectio-org/spectio/blob/HEAD/web/src/launch/LaunchCatalog.test.tsx)), and the focus return on Cancel and Escape has no test yet (CR-P3FU87E-04, open).
- The file states (refused, invalid, unreachable) on screen: the server was seeded with a good file.
