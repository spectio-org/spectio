---
icon: material/server-network-outline
---
# Environments: how a run is sent to the compute

!!! note "Built on the integration branch, not released yet"

    The server side (steps FU-P3-86a to FU-P3-86d, batch [P3-B10](../progress/W5/P3-M9.md#batch-p3-b10)) the screens (FU-P3-86f to FU-P3-86h, batch [P3-B11](../progress/W5/P3-M9.md#batch-p3-b11)) and the kind icons, the table view and Duplicate to edit (FU-P3-111, batch [P3-B14](../progress/W5/P3-M9.md#batch-p3-b14)) work today from a checkout, 2026-11-09. The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). **Everything here ran on a local executor only** (`spectio init --local`): no SLURM environment was created or launched, so the SLURM form is not shown (see [Not shown](#not-shown)).

An **environment** is a named set of launch defaults for one executor: where the engine sends its tasks, and how much it may ask for. It never changes where Spectio's own head runs. The fields, the rules and the routes are owned by [api §5.4](../specs/api-and-data-model.md#54-environments-001); the behaviour of the screens by [ui-spec §4.8.1](../specs/ui-spec.md#481-environments-in-001).

## Two built-ins and your own

| Name | When it is listed | What it is |
|---|---|---|
| `local` | on every server | the tasks run on the machine that runs the head. On a SLURM server it is capped at 2 CPUs and 8192 MiB; in local mode it has no caps |
| `slurm` | on a server set up with SLURM only | `partition` and `account` from `spectio.toml`'s `[slurm]` |
| yours | when `environments.toml` defines it | `executor` `local` (with `cpus`, `mem_mib`) or `slurm` (with `partition`, `account`, `time_min`, `mem_mib`) |

- The built-ins cannot be changed or deleted: that is `409 environment-builtin`. To start from one, copy its values into a new name.
- The **default** is the built-in of the server's own kind until you make another one the default.
- Names are lower case, start with a letter, at most 32 characters. `local`, `slurm` and `new` are reserved.

## Where they are kept

Your definitions are in `environments.toml`, next to `spectio.toml`, not in the database. The database is an index that a purge can rebuild; a definition kept only there would be lost. `spectio doctor` prints the file's path, its state and the default:

```console
$ spectio doctor | grep environments
ok environments /srv/demo-b10/data/environments.toml: missing, default local
```

The file is read without following a link, and only if it is yours and nobody else can write it. It has one of five states:

| State | Meaning | What still works |
|---|---|---|
| `missing` | no file: normal | the built-ins |
| `ok` | read and valid | everything |
| `refused` | not a regular file of yours, or others can write it, or it cannot be opened (permission, a link) | the built-ins; nothing is written |
| `invalid` | does not parse, breaks a rule, or is over 64 KiB or 32 environments | the built-ins; nothing is written |
| `unreachable` | the file system did not answer, or an I/O error | a launch with a built-in; a launch naming a file environment and every write get `503` |

In every state but `ok`, only the built-ins are listed. A file that is `refused` or `invalid` is never overwritten: fix it by hand, then reload.

## On screen

The pages are in the sidebar under **Environments**, and the form of a new one opens from **Launch**. The screens below are the real app, from a local server run as `alice` on `login1` with two environments in the file.

### The Environments page

[![The Environments page: the built-in and two environments, one the default](../assets/shots/app-environments_light.webp#only-light)](../assets/shots/app-environments_light.webp)
[![The Environments page, dark](../assets/shots/app-environments_dark.webp#only-dark)](../assets/shots/app-environments_dark.webp)

- One card per environment: an icon for its kind, its label, its name, its executor, and what it caps ("this machine · at most 2 CPUs and 4 GiB"). Chips say **Local** or **SLURM**, **Default** and **Built-in**. The icon (`terminal` for Local, `server` for SLURM) only decorates: the chip says the kind.
- The built-in has **Duplicate to edit** and **Make default**, no Edit and no Delete. Yours have **Edit**, **Duplicate** and **Delete**, and **Make default** unless it is the default already.
- **Make default** changed the line under the title from "the default is two-cores" to "the default is local" at once (it was clicked on the built-in's card).
- **Delete** asks first: "Delete eight-cores? Runs that used it keep their settings." After the confirmation the environment was gone from the file, and `GET /runs/<id>` of a run that used it still gave `"name": "eight-cores"`, `"state": "recorded"`.
- The path of `environments.toml` is shown under the cards.
- When the file is `refused`, `invalid` or `unreachable`, the actions that write wait and each says why ("Waits until the mistake in the file is fixed"). This was read from the code and its tests, **not** reproduced in a browser.

On a phone a card is one link to the environment's page, which carries the actions (Duplicate and Delete last):

[![The Environments page on a phone](../assets/shots/app-environments-phone_light.webp#only-light)](../assets/shots/app-environments-phone_light.webp)
[![The Environments page on a phone, dark](../assets/shots/app-environments-phone_dark.webp#only-dark)](../assets/shots/app-environments-phone_dark.webp)

### Cards or a table

*Step FU-P3-111, batch [P3-B14](../progress/W5/P3-M9.md#batch-p3-b14). Owner: [ui-spec §4.8.1](../specs/ui-spec.md#481-environments-in-001).*

A switch under the title, **Show environments as** Cards or Table, changes the list's view. The view is kept in the address (`/environments?view=table`; cards when absent), so Reload and a copied link keep it, and Save or Cancel on a form returns to the view the list last showed.

[![Environments as a table: This machine (built-in), Eight cores and Two cores (the default), each with its kind icon and chip, its settings, its state and its actions](../assets/shots/app-environments-table_light.webp#only-light)](../assets/shots/app-environments-table_light.webp)
[![Environments as a table, dark](../assets/shots/app-environments-table_dark.webp#only-dark)](../assets/shots/app-environments-table_dark.webp)

- **One real `<table>`** with the columns Environment, Kind, Settings, State and Actions. The default row has the coloured rail the card has.
- **Actions are named per row** ("Edit eight-cores", "Delete eight-cores", "Make default eight-cores"), so a screen reader hears which row each belongs to.
- **Duplicate to edit** on the built-in opens `/environments/new?from=local` with the built-in's values filled in and a free name, here `local-copy`. The built-in's label is not copied. **Duplicate** on your own environment does the same and copies its label. Nothing is written until you press Save. The new-environment page without `?from=` reads no list.

[![The form opened by Duplicate to edit on the built-in local environment: the name local-copy, an empty label, the executor fixed to Local, and the local caps and default profiles](../assets/shots/app-environment-duplicate_light.webp#only-light)](../assets/shots/app-environment-duplicate_light.webp)
[![The form opened by Duplicate to edit, dark](../assets/shots/app-environment-duplicate_dark.webp#only-dark)](../assets/shots/app-environment-duplicate_dark.webp)

*The built-in `local` has no limit, so the CPU and memory fields are empty. The page title reads "New environment": a duplicate is a new one.*

- **Not drawn as the boards draw it** (open minors): the board's switch buttons carry icons and the app's do not; a table row has no "Not usable: <reason>" in its State column; the phone table view and "Duplicate to edit" exist on the board only as footnotes ([P3-fu111](../reviews/code/P3-fu111.md)).

### The form

[![The form of two-cores on a local server](../assets/shots/app-environment-edit_light.webp#only-light)](../assets/shots/app-environment-edit_light.webp)
[![The form of two-cores, dark](../assets/shots/app-environment-edit_dark.webp#only-dark)](../assets/shots/app-environment-edit_dark.webp)

- The name, an optional label, the executor and its fields, and a default profile for each engine. On this server the executor is fixed: "This server was set up with spectio init --local: it has no SLURM".
- The local caps are CPUs and memory with a MiB or GiB unit.
- A value the server refuses (a `422`) shows under its field. One for a field the form does not show goes to an alert banner. Both are from the tests; with the name `Bad Name` typed, the browser run showed Save not enabled.

### On Launch and on Run detail

[![Launch with Where it runs and the aside](../assets/shots/app-launch-environment_light.webp#only-light)](../assets/shots/app-launch-environment_light.webp)
[![Launch with Where it runs and the aside, dark](../assets/shots/app-launch-environment_dark.webp#only-dark)](../assets/shots/app-launch-environment_dark.webp)

- **Where it runs** has the **Environment** row. With one usable environment it is a text line; two to six are radio cards, as above; more are a select. The default is chosen until you pick another. **New environment** opens the form in a dialog (a bottom sheet on a phone) and **Save and choose it** keeps your launch form.
- **Summary**, top right: pipeline and profile, engine and its version, environment, engine head, tasks, run directory. In the browser run, choosing the new `one-core` changed the Environment line from "This machine · Local" to "One core · Local" and the Tasks line to "run on login1 by Nextflow · at most 1 CPUs" (the "1 CPUs" is a plural slip, [DW-P3B11-02](../reviews/code/P3-B11.md#findings)).
- **Before Launch** lists every reason Launch waits, each a link to its field. A link opens the folded section that holds the field and moves focus there. Here, with `scale` set to 0: "Fix scale: Must be at least 1." With nothing wrong it reads "Nothing is missing." Both Launch buttons are described by this list.
- The params preview is folded at first.

On Run detail, **Facts** names the environment the run ran with, from the copy stored at launch (see [A run keeps what it ran with](#a-run-keeps-what-it-ran-with)):

[![A run's Facts with its Environment](../assets/shots/app-run-environment_light.webp#only-light)](../assets/shots/app-run-environment_light.webp)
[![A run's Facts with its Environment, dark](../assets/shots/app-run-environment_dark.webp#only-dark)](../assets/shots/app-run-environment_dark.webp)

A run launched from the screen with `one-core` chosen was `succeeded`, its `GET /runs/<id>` gave `"environment": {"name": "one-core", ..., "local": {"cpus": 1, "mem_mib": null}, "state": "recorded"}`, and the first line of its `head.out` was `Spectio: environment one-core (local: cpus 1)`.

## Using them (the API)

The screens call these routes. All of them are under `/api/v1`, need a signed-in session, and write only with a same-origin request. These calls ran against a real `spectio serve` (local mode, Nextflow 26.10.4), signed in as `alice` on `login1`. Long answers are shortened here to the fields that matter.

**List.** With no file, the built-in only:

```console
GET /environments
200  items: [local ("This machine", default, usable)]  default: "local"
     file: {"path": "/srv/demo-b10/data/environments.toml", "state": "missing", "detail": null}
```

**Create.** The answer is `201` with a `Location` and an `ETag`; the file is written by Spectio and has the values you sent:

```console
POST /environments   {"name": "two-cores", "label": "Two cores", "executor": "local", "local": {"cpus": 2, "mem_mib": 4096}}
201  Location: /api/v1/environments/two-cores   ETag: "a66f74b327e91ed28bf03b2bebb33202"

$ cat /srv/demo-b10/data/environments.toml
# Written by Spectio: a write keeps no comment.

[environments.two-cores]
label = "Two cores"
executor = "local"

[environments.two-cores.local]
cpus = 2
mem_mib = 4096
```

A write keeps no comment: if you edit the file by hand, put nothing in it you want to keep next to an environment you also edit through the API.

**What is refused,** each with a `422` or `409` that names the field:

| Request | Answer |
|---|---|
| `{"name": "slurm", …}` | `422`, `name: slurm is a built-in name` |
| `{"name": "hpc", "executor": "slurm", …}` on a local server | `422`, `executor: This server was set up with spectio init --local: it has no SLURM` |
| `"local": {"cpus": 0}` | `422`, `local.cpus: Input should be greater than or equal to 1` |
| a name that exists | `409 environment-exists` |
| `PUT` or `DELETE` of `local` | `409 environment-builtin`, "local is built in: it cannot be changed; duplicate it into a new name." |

**Change one.** `PUT` and `DELETE` need `If-Match` with the `ETag` you read, because two tabs may edit. Without it the answer is `428 if-match-required` (and `*` is refused); with an old tag it is `412 etag-mismatch`, "The environment changed since it was read: read it again."

**Make it the default.** `POST /environments/two-cores:make-default` answers `204`, and the list then says `default: "two-cores"`.

## Launching with one

Add `environment` (a name) to the launch body of `POST /runs`. Without it the default is used. This run was launched on the synthetic Nextflow pipeline with `"profiles": ["test", "local"]`:

```console
POST /runs   {"workflow": {...}, "profiles": ["test", "local"], "params": {}, "environment": "two-cores"}
201  {"id": "run_01M700BNEANSHBVBK6CE2EB480", "state": "queued"}
... succeeded {'succeeded': 65}

$ head -1 runs/run_01M700BNEANSHBVBK6CE2EB480/launch/.spectio/head.out
Spectio: environment two-cores (local: cpus 2, memory 4096 MiB)

$ cat runs/run_01M700BNEANSHBVBK6CE2EB480/launch/.spectio/spectio.config
// Written by Spectio for this launch.
process.executor = 'local'
executor {
  $local {
    cpus = 2
    memory = '4096 MB'
  }
}
```

- The first line of the head's output names the environment. The config is the only place its values reach Nextflow; for Snakemake they become arguments (the table is in [api §5.4](../specs/api-and-data-model.md#54-environments-001), and was checked on Nextflow only).
- **Cpus and memory are caps,** not what the tasks use.
- **A pipeline's own settings still win** for a process that sets its own time or memory (Nextflow's configuration order, per api §5.4).
- **A launch that cannot work is a `422` on `environment`,** and no run is created:

| `environment` | Server state | Answer |
|---|---|---|
| `"ghost"` | any | `422`, `environment: there is no environment ghost` |
| `"slurm"` | set up with `--local` | `422`, `environment: This server was set up with spectio init --local: it has no SLURM` |
| `"two-cores"` | file `invalid` | `422`, `environment: the environments file is invalid: …` |
| none, or `"local"` | file `invalid` | `201`: a built-in still launches |

## A run keeps what it ran with

The run stores a copy of the environment as it was at launch. This was checked: after `PUT /environments/two-cores` changed `cpus` from 2 to 8, `GET /runs/<id>` still gave:

```console
"environment": {"name": "two-cores", "label": "Two cores", "executor": "local", "slurm": null,
                "local": {"cpus": 2, "mem_mib": 4096}, "state": "recorded"}
```

So editing or deleting an environment changes no run. Everything that depends on how a run was sent (the failure summary, the `sacct` call, Resume's copied command) reads this copy. A run from before this feature has `state: "not_recorded"` and is read as the built-in of the server's kind; a run whose copy cannot be read has `state: "not_readable"` and is never asked of `sacct`. A run started from a terminal has `environment: null`.

## When the file is not usable

Both states below were made by editing the file by hand while the server ran. The server read the new state at the next request.

```console
GET /environments   (the file now holds: default = "ghost")
200  items: [local]  default: "local"
     file: {"state": "invalid", "detail": "default ghost names no environment"}

POST /environments   {"name": "other", "executor": "local"}
409  /problems/environments-file-unusable: The environments file is invalid: default ghost names no environment

$ spectio doctor | grep environments
warn environments /srv/demo-b10/data/environments.toml: invalid (default ghost names no environment), default local
```

```console
GET /environments   (the file now has mode 666)
200  file: {"state": "refused", "detail": "environments.toml must be a file of yours that others cannot write (owner uid 0, mode 666)"}

$ spectio doctor | grep environments
warn environments /srv/demo-b10/data/environments.toml: refused (environments.toml must be a file of yours that others cannot write (owner uid 0, mode 666)), default local
```

The `detail` of an `invalid` file never holds bytes of the file: a parser message is cut at its first quote and keeps only its place (`not TOML: Cannot overwrite a value (at line 3, column 22)`). Putting the file back (mode 600) made the next list `ok` again, with `two-cores` as the default.

## Not shown

- **A SLURM environment:** no create, no launch, no `sacct`. The `slurm` fields, the Snakemake arguments and `--local-cores 2` are covered by tests (`test_headscript.py`, `test_environment_snapshot.py`), not run on a cluster.
- **An `unreachable` file:** it needs a file system that stops answering. The tests make it with a patched `os.open` (`ESTALE`) and a stalled pool.
- **Snakemake with an environment:** not launched here, only tested.
- **The SLURM form and a SLURM environment on screen:** the server was local, so the executor is fixed to Local and no partition or account field was seen.
- **A file that is `refused`, `invalid` or `unreachable` on screen:** the page's banners and waiting buttons are covered by Vitest (`EnvironmentsPage.test.tsx`), not run in a browser against a bad file.
- **Firefox, WebKit and a screen reader:** screens were taken with Chromium only.
- **Launch and Run detail on a phone:** only the Environments list was taken on a phone.
- **`POST /runs:validate`:** 0.0.1 has no such route (it answers `404`); the field is read by `POST /runs`. See [DW-P3B10-01](../reviews/code/P3-B10.md#findings).
