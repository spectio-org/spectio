---
icon: material/server-network-outline
---
# Environments: how a run is sent to the compute

!!! note "Built on the integration branch, no screen yet, not released yet"

    The server side works today from a checkout (steps FU-P3-86a to FU-P3-86d, batch [P3-B10](../progress/W5/P3-M9.md#batch-p3-b10), 2026-11-09). The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). **There is no Environments page yet:** the boards are drawn ([ui-spec §4.8.1](../specs/ui-spec.md#481-environments-in-001)) and the screens come in FU-P3-86f and -86g. Everything below is done through the API and `spectio doctor`. **It ran on a local executor only** (`spectio init --local`): no SLURM environment was created or launched (see [Not shown](#not-shown)).

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

## Using them

All routes are under `/api/v1`, need a signed-in session, and write only with a same-origin request. These calls ran against a real `spectio serve` (local mode, Nextflow 26.10.4), signed in as `alice` on `demo-hpc-login1`. Long answers are shortened here to the fields that matter.

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
- **Any screen:** none is built. The boards are drawn: Environments and its states, the form, New environment from Launch, Launch in two columns, and the Environment fact on Run detail ([P3-B10 steps](../progress/W5/P3-M9.md#batch-p3-b10)).
- **`POST /runs:validate`:** 0.0.1 has no such route (it answers `404`); the field is read by `POST /runs`. See [DW-P3B10-01](../reviews/code/P3-B10.md#findings).
