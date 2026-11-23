# Fractal: evaluation for Spectio (2026-11-23)

Fact-checked 2026-11-23 by fact-checker, from the GLM digest `refract/res-fractal/fractal.md`. Every claim was re-read in the primary source: the GitHub repositories at a release tag (read through the GitHub API, no clone), PyPI, and the source of the Fractal website at a pinned commit. Where the docs and the code disagree, the code wins and the note says so.

**Pinned sources (all read 2026-11-23):**

| Short name | Source |
|---|---|
| `server@2.28.0` | https://github.com/fractal-analytics-platform/fractal-server/tree/2.28.0 (latest release, 2026-11-20) |
| `web@v1.30.1` | https://github.com/fractal-analytics-platform/fractal-web/tree/v1.30.1 (latest non-alpha, 2026-11-11) |
| `ftt@0.5.1` | https://github.com/fractal-analytics-platform/fractal-task-tools/tree/0.5.1 (latest, 2026-10-09) |
| `ftc@2.1.0` | https://github.com/fractal-analytics-platform/fractal-tasks-core/tree/2.1.0 (latest, 2026-07-13) |
| `data@v0.6.4` | https://github.com/fractal-analytics-platform/fractal-data/tree/v0.6.4 (latest, 2026-10-26) |
| `site@642bd16` | https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/tree/642bd16d6ba0654dd1b560ac4357d23854e885d9 (source of https://fractal-analytics-platform.github.io, main on 2026-11-23) |
| `ngio` | https://github.com/BioVisionCenter/ngio at v0.5.8, v0.5.14 and v1.1.5 |

Rendered docs pages cited by the digest are built from these files; a link to the rendered page is kept where it helps, with the source file as the evidence.

---

## 1. Task model

### 1.1 What a Fractal task is

- Fractal tasks are "modular and interoperable processing units that handle data in OME-Zarr containers"; each task "runs on a single OME-Zarr image or a collection of OME-Zarr images", and is given "the Zarr URL(s), that is, the path(s) to a given OME-Zarr image on disk or in the cloud". Source: `site@642bd16` [docs/tasks_spec.md](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/tasks_spec.md) (read 2026-11-23). On "in the cloud", see §3: the server accepts `s3://` since 2.20.0.
- "Fractal tasks are Linux command line executables"; for Python, "a Python function that knows how to process an OME-Zarr image and save the results back into that OME-Zarr image". Source: `site@642bd16` [docs/build_your_own_fractal_task.md:3](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/build_your_own_fractal_task.md).
- Signature: `python task.py --args-json /path/to/arguments.json --out-json /path/to/output/metadata.json`. Source: `ftt@0.5.1` [docs/usage/run_task.md](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/usage/run_task.md); the parser is in [src/fractal_task_tools/task_wrapper.py:63-72](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/src/fractal_task_tools/task_wrapper.py#L63-L72). Server side, `command_non_parallel` / `command_parallel` are run with `--args-json … --out-json …` appended: `server@2.28.0` [docs/internals/integrations/_task_execution.md](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/internals/integrations/_task_execution.md); the flags are built in `fractal_server/runner/executors/local/runner.py` and `slurm_common/base_slurm_runner.py` (code search, 2026-11-23).
- `run_fractal_task` turns a Python function into that CLI through an `if __name__ == "__main__"` block. Argument validation at run time is "typically" done by `@pydantic.validate_call`, not by the JSON Schema. Sources: `ftt@0.5.1` [run_task.md](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/usage/run_task.md), [manifest.md, "JSON Schemas"](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/usage/manifest.md).
- Logging: `FRACTAL_TASK_LOG_LEVEL` (DEBUG to CRITICAL), `FRACTAL_TASK_LOG_FORMAT`, `FRACTAL_TASK_SKIP_LOG_CONFIG`; default format `%(asctime)s; %(name)s; %(levelname)s; %(message)s` at INFO. Sources: `ftt@0.5.1` [run_task.md, "Log configuration"](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/usage/run_task.md) and [src/fractal_task_tools/logging_config.py](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/src/fractal_task_tools/logging_config.py).

### 1.2 The manifest (`__FRACTAL_MANIFEST__.json`)

- A task package "must contain a manifest (stored as a `__FRACTAL_MANIFEST__.json` file within the package)" that "describes the parameters, executables and metadata of the tasks". Sources: `site@642bd16` [tasks_spec.md, "Task list and manifest"](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/tasks_spec.md); `server@2.28.0` `ManifestV2` docstring in [fractal_server/app/schemas/v2/manifest.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/schemas/v2/manifest.py).
- The manifest is generated from a `task_list.py` module (`AUTHORS` and `DOCS_LINK` optional, `TASK_LIST`) with `fractal-manifest create --package <pkg>`, which writes `__FRACTAL_MANIFEST__.json` in the installed package root; `fractal-manifest check` "verifies that the on-disk manifest is up-to-date". Source: `ftt@0.5.1` [docs/usage/manifest.md, "Build and check manifest"](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/usage/manifest.md).
- **Two layers of field names (corrected, see FC-FR-01).** In `task_list.py`, the Python task models take `name`, `executable`, `meta`, `input_types`, `output_types`, `category`, `modality`, `tags`, `docs_info`, plus `executable_init` / `meta_init` for compound types. Source: `ftt@0.5.1` [src/fractal_task_tools/task_models.py:17-29, 48-57](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/src/fractal_task_tools/task_models.py#L17-L57). The **JSON manifest** stores them under other names, which is what a consumer parses:
  - manifest level: `manifest_version` (`Literal["2"]`), `task_list`, `has_args_schemas`, `args_schema_version`, `authors`;
  - per task: `name`, `type`, `executable_non_parallel`, `executable_parallel`, `meta_non_parallel`, `meta_parallel`, `args_schema_non_parallel`, `args_schema_parallel`, `input_types`, `output_types`, `docs_info`, `docs_link`, `category`, `modality`, `tags`. Executables are paths relative to the installed package root.
  - Source: `server@2.28.0` `TaskManifestV2` / `ManifestV2` in [fractal_server/app/schemas/v2/manifest.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/schemas/v2/manifest.py); confirmed on a real manifest, `ftc@2.1.0` [fractal_tasks_core/__FRACTAL_MANIFEST__.json](https://github.com/fractal-analytics-platform/fractal-tasks-core/blob/2.1.0/fractal_tasks_core/__FRACTAL_MANIFEST__.json) (`manifest_version "2"`, `args_schema_version "fractal_schema_v1"`, `authors "Fractal Core Team"`).
  - The server rejects a manifest where both executables are null, where `meta_*` or `args_schema_*` is set for a missing executable, where `has_args_schemas` is true but a schema is missing, or where task names repeat (same file, validators).
- `meta` example values `{"cpus_per_task": 1, "mem": 4000}` (verified in `ftt@0.5.1` manifest.md and in the `ftc@2.1.0` manifest).
- Metadata fields: `docs_info` (falls back to the task function docstring; may be `file:task_info/<x>.md`); `category`, one per task, standard values `Conversion`, `Image Processing`, `Segmentation`, `Registration`, `Measurement`; `modality`, one per task, none if the task works on all OME-Zarrs, standard values `HCS`, `lightsheet`, `EM`; `tags`, free strings for search; `authors`, set per package. `fractal-manifest` falls back to `pyproject.toml` for authors. Sources: `site@642bd16` [tasks_spec.md, "Manifest/task metadata"](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/tasks_spec.md); `ftt@0.5.1` [manifest.md](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/usage/manifest.md). Precision: `authors` is a manifest-level field (`ManifestV2.authors`), not a per-task field; the server copies it onto each `TaskV2` row ([models/v2/task.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/models/v2/task.py)).
- This metadata "is also used to make tasks searchable". Source: `site@642bd16` tasks_spec.md (as above).

### 1.3 Args JSON Schema

- One JSON Schema per task, or two (`args_schema_non_parallel`, `args_schema_parallel`) for a task with both units. Source: `ftt@0.5.1` [manifest.md, "JSON Schemas"](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/usage/manifest.md).
- The schemas are not used at task run time, "but they form the basis for constructing the fractal-web user interface that lets a user edit task arguments". Source: same section.
- `args_schema_version` is set at manifest level; current value `"fractal_schema_v1"` as of fractal-task-tools 0.5.0, with "relevant breaking changes" from `"pydantic_v2"`, supported until 0.4.\*. Sources: same section; [src/fractal_task_tools/_create_manifest.py:22](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/src/fractal_task_tools/_create_manifest.py#L22) (`ARGS_SCHEMA_VERSION = "fractal_schema_v1"`); [docs/changelog.md, 0.5.0](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/changelog.md).
- Restrictions checked by `validate_schema`, by code: E01 forbidden property names (`args`, `kwargs`, `v__args`, …), E02 `definitions` (use `$defs`), E03 mixed-type `enum`, E04 underdefined schemas (`typing.Any`), E05 booleans without default, E06 boolean-valued maps, E07 empty-string defaults, E08 boolean tuple items, E10–E12 nullable booleans and enums, E13–E15 `anyOf` shapes, E20–E22 `oneOf` needs a `discriminator` and `$ref` items. The list has gaps (no E09, no E16–E19), and the page says it "is currently evolving, and the ground truth is in the `_specs.py` module". Sources: `ftt@0.5.1` [manifest.md, "Restrictions on JSON Schemas"](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/usage/manifest.md); [src/fractal_task_tools/_specs.py:40](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/src/fractal_task_tools/_specs.py#L40). Valid examples: https://github.com/fractal-analytics-platform/example-fractal-task-arguments. Caveat (verified, same section): the restrictions apply to the schema, not to the Python signature; `dict[int, int]` loses its integer keys in the schema.
- **Added (verified 2026-11-23): real schemas contain the reserved keys.** In `ftc@2.1.0`, the "Threshold Segmentation" schema has `required: ["zarr_url", "channel"]` and a `zarr_url` string property; compute units of compound tasks list `zarr_url` and `init_args` as required. Its other properties use `$ref` into `$defs` (13 models), `anyOf [X, null]` with `default: null`, and `oneOf` with a `discriminator`. Source: [fractal_tasks_core/__FRACTAL_MANIFEST__.json](https://github.com/fractal-analytics-platform/fractal-tasks-core/blob/2.1.0/fractal_tasks_core/__FRACTAL_MANIFEST__.json). A form built from these schemas must hide the reserved keys and render nested objects and tagged unions.

### 1.4 Task types, `zarr_url` / `zarr_urls` / `zarr_dir`

Five task types, in code: `TaskType` = `compound`, `converter_compound`, `non_parallel`, `converter_non_parallel`, `parallel` (`server@2.28.0` [fractal_server/app/schemas/v2/task.py:22-31](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/schemas/v2/task.py#L22-L31)). They "differ in what required parameters they need, what kind of metadata they can produce, and how they run in Fractal server" (`ftt@0.5.1` [docs/usage/task_types.md](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/usage/task_types.md)).

| Type | Required args | Execution |
|---|---|---|
| Parallel | `zarr_url: str` | one image per unit, "meant to run in parallel across many OME-Zarr images" |
| Non-parallel | `zarr_urls: list[str]`, `zarr_dir: str` | "only runs as a single computational job" |
| Compound | init: `zarr_urls`, `zarr_dir`; compute: `zarr_url`, `init_args` | init runs like a non-parallel task and returns a parallelization list; compute units "run in parallel for each entry" |
| Non-parallel converter | `zarr_dir` | single job; creates new OME-Zarr images from raw data, so no `zarr_urls` |
| Compound converter | init: `zarr_dir`; compute: `zarr_url`, `init_args` | as compound, init "only requires a `zarr_dir`" |

(All rows: `ftt@0.5.1` [task_types.md](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/usage/task_types.md), read 2026-11-23.)

Key rules:
- `zarr_url`, `zarr_urls`, `zarr_dir`, `init_args` are reserved: "the server takes care to pass the correct value … and the user cannot set them directly" (task_types.md, "Parameters"). Enforced in code: `validate_wft_args` rejects workflow-task `args` containing any of the four keys, `server@2.28.0` [fractal_server/types/validators/_workflow_task_arguments_validators.py:1-9](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/types/validators/_workflow_task_arguments_validators.py#L1-L9).
- `zarr_url` "contains the full path to the zarr file to be processed"; `zarr_dir` "is the base directory into which new OME-Zarr files may be written". Same page. **The "filesystem paths only" sentence of that page is outdated: see FC-FR-02 and §3.**
- Task output: a JSON-serializable dict with `image_list_updates` (entries `zarr_url`, `origin`, `attributes`, `types`) and `image_list_removals`; validated with `extra="forbid"` by `TaskOutput` in `server@2.28.0` [fractal_server/runner/v2/task_interface.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/runner/v2/task_interface.py); the server also rejects duplicated `zarr_url`s across updates and removals (`check_zarr_urls_are_unique`, same file).
- Compound init returns `{"parallelization_list": [{"zarr_url": …, "init_args": {…}}, …]}` (`InitTaskOutput`, same file); the docs example with three acquisitions gives "three copies of the compute tasks" (task_types.md).

### 1.5 Packaging

- To be listed on the public Fractal tasks page, a package needs a manifest and must be on PyPI or a wheel in a GitHub release; `pixi` support for that page is "future work". Source: `site@642bd16` [tasks_spec.md, "How to get your task package on the Fractal tasks page"](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/tasks_spec.md). This is about the website listing only; the server collects pixi packages (below).
- The recommended starting point is the `fractal-tasks-template` repository and its developer's guide. Source: `site@642bd16` [build_your_own_fractal_task.md](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/build_your_own_fractal_task.md).
- fractal-tasks-core: `pip install fractal-tasks-core`; use the name `fractal-tasks-core` when collecting it on a server. Source: `ftc@2.1.0` [docs/install.md](https://github.com/fractal-analytics-platform/fractal-tasks-core/blob/2.1.0/docs/install.md). Its development environment "moved from `poetry` to `pixi`" in 2.0.0 ([CHANGELOG.md](https://github.com/fractal-analytics-platform/fractal-tasks-core/blob/2.1.0/CHANGELOG.md)). This is the developers' tooling, not how users get the package.
- **Server-side collection modes, by API route** (`server@2.28.0`, routes under `/api/v2/task`):
  - `POST /collect/pip/`: a PyPI package name with version, extras and pinned versions, or an uploaded wheel; one venv per package, Python version from the resource's `tasks_python_config`. Sources: [routes/api/v2/task_collection.py:154-155](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/routes/api/v2/task_collection.py#L154-L155); `TaskCollectPip` in [schemas/v2/task_collection.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/schemas/v2/task_collection.py); templates `1_create_venv.sh`, `2_pip_install.sh` under `fractal_server/tasks/v2/templates/`.
  - `POST /collect/pixi/`: an uploaded `.tar.gz` of a pixi project, with `pixi_version` and `use_pixi_lockfile` (`"true"` by default). Source: [routes/api/v2/task_collection_pixi.py:78-110](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/routes/api/v2/task_collection_pixi.py#L78-L110).
  - `POST /collect/apptainer/` (new in 2.28.0, **experimental**, SLURM-SSH resources only): builds a SIF from an uploaded pixi package and runs the tasks inside it. Sources: [routes/api/v2/task_collection_apptainer.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/routes/api/v2/task_collection_apptainer.py); [docs/changelog.md, 2.28.0](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/changelog.md); [docs/internals/integrations/tasks.md, "Apptainer"](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/internals/integrations/tasks.md) (needs `tasks_apptainer_config` on the resource and `APPTAINER_BINDPATH` through `extra_lines` for job and data folders). The SIF bootstraps from `ghcr.io/prefix-dev/pixi:<version>` and runs `pixi install --frozen` ([tasks/v2/templates/apptainer_template.def](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/tasks/v2/templates/apptainer_template.def)).
  - `POST /collect/custom/`: registers tasks from a manifest plus an existing `python_interpreter` and an optional `package_root`, with nothing installed. Source: `TaskCollectCustom` in [schemas/v2/task_collection.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/schemas/v2/task_collection.py); [routes/api/v2/task_collection_custom.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/routes/api/v2/task_collection_custom.py).
  - Lifecycle modules (`collect`, `collect_pixi`, `collect_apptainer` (SSH only), `deactivate`, `reactivate`, `delete`, `reset`) exist for local and SSH under `fractal_server/tasks/v2/{local,ssh}/` (tree at 2.28.0).
- fractal-web: pixi collection since 1.19.0, "Use pixi.lock file" option since 1.24.0. Source: `web@v1.30.1` [docs/changelog.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/docs/changelog.md).
- Pip collection: Python 3.9 and 3.10 deprecated in 2.27.0; 2.27.1 tells admins to remove them from `tasks_python_config`. Source: `server@2.28.0` [docs/changelog.md](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/changelog.md). The task-collection docs page says "This section is not in-place yet" ([tasks.md](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/internals/integrations/tasks.md)).
- Conda: there is no conda collection mode; a code search of fractal-server finds `conda` only in the install docs ("also available as a Conda package … but the PyPI version is the recommended one", [docs/install_and_deploy.md:32](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/install_and_deploy.md)) and in pixi test fixtures. Conda-forge dependencies reach tasks through pixi. Docker: only the demo stack (`site@642bd16` [run_fractal.md](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/run_fractal.md)) and the Apptainer base image; Docker is not a way to ship tasks.
- **Added:** fractal-tasks-core 2.1.0 now ships nine tasks; its only converter is "Import OME-Zarr". Microscope converters live in separate packages, for example `fractal-uzh-converters` 0.7.1 on PyPI ("A collection of fractal tasks to convert HCS Plates to OME-Zarr", https://pypi.org/project/fractal-uzh-converters/, read 2026-11-23). Source: `ftc@2.1.0` manifest (above).

---

## 2. Execution

### 2.1 fractal-server and its runners

- fractal-server is "the server component of the fractal analytics platform" (README at `server@2.28.0`) and "Fractal backend" (GitHub repository description, read 2026-11-23).
- A runner "executes a job (based on a certain workflow and dataset) on a computational resource". There are three implementations, for the local, SLURM/sudo and SLURM/SSH cases: `BaseRunner` (with `submit` and `multisubmit`) → `LocalRunner`; `BaseSlurmRunner` → `SlurmSudoRunner` and `SlurmSSHRunner`. Source: `server@2.28.0` [docs/internals/integrations/runners.md](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/internals/integrations/runners.md); `fractal_server/runner/executors/` tree.
- How they reach SLURM (code, `server@2.28.0`):
  - **sudo**: commands run as `sudo --set-home --non-interactive -u {user} {cmd}`, which needs sudoers rights for the server's account ([runner/executors/slurm_sudo/_subprocess_run_as_user.py:51](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/runner/executors/slurm_sudo/_subprocess_run_as_user.py#L51)).
  - **SSH**: Fabric (`FractalSSH`), with job folders moved as `.tar.gz` ([runner/executors/slurm_ssh/runner.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/runner/executors/slurm_ssh/runner.py)). The SSH host is the resource's `host`; user and key path come from the user's profile (`/job/squeue/` route, [routes/api/v2/job.py:284-292](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/routes/api/v2/job.py#L284-L292)).
  - **Submission and polling**: `sbatch --parsable <script>`; the job state is polled with `squeue` every `poll_interval` (the resource's `jobs_poll_interval`), and "If a job is not in `squeue` output, mark it as completed". Recoverable `squeue` errors are retried forever. Source: [runner/executors/slurm_common/base_slurm_runner.py:182-266, 436-440](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/runner/executors/slurm_common/base_slurm_runner.py#L182-L266); the finished-state set is in [_job_states.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/runner/executors/slurm_common/_job_states.py). This answers the digest's open item on polling. `sacct` is not used for state.
- Runner configuration is in the resource's `jobs_runner_config`:
  - local: `JobRunnerConfigLocal.parallel_tasks_per_job`, "Maximum number of tasks to be run in parallel within a local runner. If `None`, then all tasks may start at the same time" ([runner/config/_local.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/runner/config/_local.py));
  - SLURM: `JobRunnerConfigSLURM` with `default_slurm_config`, `gpu_slurm_config`, `batching_config` (`target_num_jobs`, `max_num_jobs`, `target_cpus_per_job`, `max_cpus_per_job`, `target_mem_per_job`, `max_mem_per_job`) and `user_local_exports`. `SlurmConfigSet` keys: `partition`, `cpus_per_task`, `mem`, `constraint`, `gres`, `exclude`, `nodelist`, `nodes`, `time`, `account`, `extra_lines`, `gpus`, `shebang_line`, `use_mem_per_cpu` ([runner/config/_slurm.py:21-139](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/runner/config/_slurm.py#L21-L139)).
- Per-task `meta` feeds SLURM: `cpus_per_task`, `mem` (converted by `slurm_mem_to_MB`), `needs_gpu` (switches to `gpu_slurm_config`), `account`, `extra_lines` and other SLURM keys, all read from the workflow task's `meta_non_parallel` / `meta_parallel` ([runner/executors/slurm_common/get_slurm_config.py:43-129](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/runner/executors/slurm_common/get_slurm_config.py#L43-L129)).
- **Backend selection (corrected, FC-FR-03).** The runner is chosen by fractal-server: the resource `type` (`slurm_sudo`, `slurm_ssh`, local) and the server setting `FRACTAL_RUNNER_BACKEND: Literal["local", "slurm_ssh", "slurm_sudo"] = "local"` ([config/_main.py:69-71](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/config/_main.py#L69-L71)). fractal-web has a mandatory variable of the same name that tells the UI which backend the server uses (jobs pages, squeue modal). Its code accepts `local`, `slurm_sudo` and `slurm_ssh` ([src/env.js:23-31](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/src/env.js#L23-L31)), while its docs still list `local`, `slurm`, `slurm_ssh` ([docs/environment-variables.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/docs/environment-variables.md)); the code wins.
- Deployment: "Fractal is meant to be deployed on-site in your institution to manage workflows on large cluster. It currently has support for different modes of running on slurm clusters. It is deployed on Linux servers and also runs on macOS or Windows (by using Windows Subsystem Linux)." Main deployments run the services "standalone, not via the docker example setup". Source: `site@642bd16` [docs/run_fractal.md](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/run_fractal.md).
- `FRACTAL_STOP_SLURM_JOBS_ON_SHUTDOWN` was added in 2.27.3 (default `"true"`, [config/_main.py:76](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/config/_main.py#L76)). 2.25.2 changed the SLURM-sudo runner: `_fetch_artifacts` now raises errors from its thread pool, and "Only ignore file-not-found errors when fetching remote job artifacts via `sudo -u`". Source: [docs/changelog.md](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/changelog.md).

### 2.2 Jobs: submission, execution, monitoring

- `execute_tasks` runs a list of workflow tasks on a dataset, given "filters based on image types or attributes, set by the user upon job submission". Source: `server@2.28.0` [_task_execution.md](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/internals/integrations/_task_execution.md).
- Per task, three phases (same page):
  - **Pre-task (corrected, FC-FR-04).** Converters get no input images. For the others, the server takes the current type filters, which start from the job's `type_filters` (`current_type_filters = copy(job_type_filters)`) and are updated after each task with its `output_types`. It patches them with the merge of the task's `input_types` and the workflow task's `type_filters`; the merge raises if the two disagree on a key. It then applies the job's attribute filters. Code: [runner/v2/runner.py:121, 147-152, 446-448](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/runner/v2/runner.py#L121); [images/tools.py:106-128](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/images/tools.py#L106-L128). Datasets hold no filters since 2.14.0 ("Drop attribute/type filters from dataset table. Add `type_filters` column to job table", changelog 2.14.0); `JobV2` has `attribute_filters` and `type_filters` ([models/v2/job.py:62-65](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/models/v2/job.py#L62-L65)). The result becomes `zarr_urls` (non-parallel, compound) or one `zarr_url` per unit (parallel).
  - **Execution**: `run_task_non_parallel` for NON_PARALLEL and CONVERTER_NON_PARALLEL, `run_task_parallel` for PARALLEL, `run_task_compound` for COMPOUND and CONVERTER_COMPOUND (same page).
  - **Post-task**: outputs are merged into one `TaskOutput`; `attributes`, `types` and `origin` are updated; removals are dropped; "The existing dataset image list is replaced with the new one, in the database" (same page).
- REST API (code, `server@2.28.0`; app prefixes in [main.py:48-51](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/main.py#L48-L51): `/api/v2`, `/admin/v2`, `/auth`):
  - `POST /api/v2/project/{project_id}/job/submit/?workflow_id=…&dataset_id=…` → 202, `JobRead` ([routes/api/v2/submit.py:51-62](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/routes/api/v2/submit.py#L51-L62)). The body (`JobCreate`) takes `first_task_index`, `last_task_index`, `slurm_account`, `worker_init`, `attribute_filters`, `type_filters` ([schemas/v2/job.py:44-53](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/schemas/v2/job.py#L44-L53)).
  - Read and stop: `GET /api/v2/job/`, `GET /api/v2/project/{project_id}/job/`, `GET /api/v2/project/{project_id}/job/{job_id}/`, `…/download/`, `GET /api/v2/project/{project_id}/workflow/{workflow_id}/job/`, `POST /api/v2/project/{project_id}/job/{job_id}/stop/` (202).
  - `GET /api/v2/job/squeue/?scope=all|user|accounts` returns raw `squeue` text and 422s on a local backend ([routes/api/v2/job.py:249-296](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/routes/api/v2/job.py#L249-L296)).
  - `GET /api/v2/project/{project_id}/latest-job/` ([routes/api/v2/latest_job.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/routes/api/v2/latest_job.py)).
  - Bodies and responses beyond these: the OpenAPI page of the rendered docs, https://fractal-analytics-platform.github.io/fractal-server/ (not re-read) **[to be validated]**.
- fractal-web polls job status every `PUBLIC_UPDATE_JOBS_INTERVAL` ms, default `3000` ([web@v1.30.1 docs/environment-variables.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/docs/environment-variables.md)). The help guide's Jobs page "lists workflow runs — those in progress and those already finished — and lets you inspect their status, logs and results", followed by TODO stubs ([help/docs/reference/jobs.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/help/docs/reference/jobs.md)). A Slurm-queue modal using `/job/squeue/` came in 1.29.5 ([docs/changelog.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/docs/changelog.md)).

### 2.3 Projects, workflows, datasets

- v2 models at `server@2.28.0` (`fractal_server/app/models/v2/`): `ProjectV2`, `DatasetV2`, `WorkflowV2`, `WorkflowTaskV2`, `WorkflowTemplate`, `TaskV2`, `TaskGroupV2`, `JobV2`, history (`HistoryRun`, `HistoryUnit`, `HistoryImageCache`), `Resource`, `Profile`, accounting.
- A dataset "is a collection of OME-Zarr images inside a project, together with their processing history"; "The dataset image list contains an overview of all the OME-Zarr images belonging to a given dataset". Source: `web@v1.30.1` [help/docs/reference/dataset.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/help/docs/reference/dataset.md). In code a dataset is `zarr_dir` plus `images` (JSONB) ([models/v2/dataset.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/models/v2/dataset.py)).
- Tasks reach Fractal "through task collection" ([help/docs/concepts/tasks.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/help/docs/concepts/tasks.md)). A workflow is "an ordered sequence of tasks that processes the images in a dataset — for example converting to OME-Zarr, segmenting objects, then measuring features" ([help/snippets/workflows.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/help/snippets/workflows.md)).
- Image list: each entry has a unique `zarr_url`, boolean `types` (a missing type counts as false; for example `is_3D`, `illumination_corrected`) and scalar `attributes` (plate, well, acquisition); "Fractal server uses the image list combined with filters … to provide the right image URLs to each task during execution". Source: `site@642bd16` [docs/image_list.md](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/image_list.md). Attribute filters are "defined upon submission of a job, and they do not change during the job execution" (same page). The same page says the "Continue Workflow" dialogue "is prepopulated with the attribute filters from the dataset", and also describes dataset type filters. Both predate 2.14.0, which removed filters from datasets (§2.2). Where the prefill comes from now is **[to be validated]**, see FC-FR-05.
- Workflow templates: introduced in fractal-server 2.20.0 ("Introduce `/api/v2/workflow-template/` API block", "`POST /project/{project_id}/workflow/import-from-template/`", [changelog 2.20.0](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/changelog.md)). A template can be private, shared with a user group, or shared with every user of the server (news post of 2026-03-31, [docs/news/2026-03-31-fractal-workflow-templates.md](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/news/2026-03-31-fractal-workflow-templates.md)). The public templates page is built from JSON (`templates_data_retrieval/raw/*.json` in `site@642bd16`).

### 2.4 fractal-web

- A Svelte app on SvelteKit (`@sveltejs/kit ^3.2.0`, `svelte ^5.57.3` in [package.json](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/package.json)); "The node server acts as a proxy to the fractal server" ([docs/index.md:17-19](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/docs/index.md)).
- `FRACTAL_SERVER_HOST` is required; sessions are cookie-based (`AUTH_COOKIE_*`), with optional OAuth2 (`PUBLIC_OAUTH_CLIENT_NAME`) ([docs/environment-variables.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/docs/environment-variables.md)). Compatibility table: fractal-web 1.30.1 and 1.30.0 go with fractal-server 2.27.0 ([docs/version-compatibility.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/docs/version-compatibility.md)); 1.30.0 notes: "you should also upgrade `fractal-server` to version 2.27.0 (or more recent)" ([docs/changelog.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/docs/changelog.md)). No row yet pairs a web version with server 2.28.0 **[to be validated]**.
- UI features, by changelog version ([docs/changelog.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/docs/changelog.md)):
  - JSON Schema form fixes in 1.29.6 (remove-property button) and 1.29.7 (renaming additional-property keys); larger form work in 1.24.0 (errors shown next to fields, unexpected properties, discriminators, tagged unions);
  - pixi collection in 1.19.0; args-schema and meta file upload for **single-task creation** in **0.7.1** (corrected, FC-FR-06);
  - project sharing in 1.22.0;
  - viewer links: vizarr in 1.4.1 ("Experimental feature"), Vol-E in 1.27.11, Feature Explorer in 1.19.3; `roi=1` on vizarr URLs in 1.29.8.
- The user guide says "This user guide is a work in progress" ([help/docs/index.md:3](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/help/docs/index.md)), and several of its pages are TODO stubs (Jobs page above).
- **Added:** there is also a command-line client, `fractal-client` (2.24.1 on PyPI, 2026-10-23, "Command-line client of the Fractal analytics platform", https://pypi.org/project/fractal-client/). The home page says workflows can be built and controlled "via the web client or the Fractal command line client" (`site@642bd16` [docs/index.md](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/index.md)).

---

## 3. OME-Zarr assumptions

- Fractal is a framework "to process bioimaging data at scale in the OME-Zarr format and prepare the images for interactive visualization"; "Fractal enables distributed workflows that convert TBs of image data into OME-Zarr files". Source: `site@642bd16` [docs/index.md](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/index.md); same sentence in the fractal-server README.
- HCS plates are the main layout in the examples: after a converter, "an OME-Zarr HCS plate with 2 wells that contain one image each"; with 3 wells × 3 acquisitions, "the image list includes 9 OME-Zarr images" (`site@642bd16` [image_list.md](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/image_list.md), "Examples"). The dataset page has "HCS Plate options" (`web@v1.30.1` [help/docs/reference/dataset.md:45-47](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/help/docs/reference/dataset.md)). In `ftc@2.1.0`, four of nine core tasks set `modality: "HCS"` (manifest). The `HCS`, `lightsheet` and `EM` modalities are as in §1.2.
- **NGFF version (resolved).** Neither the website nor the server docs name a required NGFF version (still true). The task code does: fractal-tasks-core 2.1.0 depends on `ngio>=0.5.8,<0.6.0` ([pyproject.toml:17](https://github.com/fractal-analytics-platform/fractal-tasks-core/blob/2.1.0/pyproject.toml#L17); `pixi.lock` pins ngio 0.5.12). ngio declares `NgffVersions = Literal["0.4", "0.5"]` with `DefaultNgffVersion = "0.4"` ([ngio v0.5.8 src/ngio/ome_zarr_meta/ngio_specs/_ngio_image.py:28-29](https://github.com/BioVisionCenter/ngio/blob/v0.5.8/src/ngio/ome_zarr_meta/ngio_specs/_ngio_image.py#L28-L29); same at v0.5.14). Its README at v0.5.14 says "ngio supports OME-Zarr v0.4/v0.5. Support for version 0.6 and higher is planned". So core tasks read NGFF 0.4 and 0.5, and new images default to 0.4 (Zarr v2). The "Unreleased" section of fractal-tasks-core main moves to `ngio>=1.1.0,<1.2` ([CHANGELOG.md on main](https://github.com/fractal-analytics-platform/fractal-tasks-core/blob/main/CHANGELOG.md), read 2026-11-23); ngio 1.1.5 still supports 0.4 and 0.5 with default 0.4, "backed by either Zarr v2 or v3 storage" ([README at v1.1.5](https://github.com/BioVisionCenter/ngio/blob/v1.1.5/README.md)). The public templates include a `zarr_v3_hipsc.json` workflow (`site@642bd16` `templates_data_retrieval/raw/`). fractal-server itself does not parse NGFF metadata: it handles `zarr_url` strings, and no code path reading `.zattrs` or `zarr.json` was found. **[to be validated]** Which NGFF version each third-party converter writes depends on that converter, so it is checked per package. The historical claim stands: fractal-tasks-core 1.1.0 changed the Plate model "to correspond better to 0.4.0 NGFF spec" ([CHANGELOG.md:278](https://github.com/fractal-analytics-platform/fractal-tasks-core/blob/2.1.0/CHANGELOG.md)).
- **Zarr locations (corrected, FC-FR-02).** The task-types page still says "The current version of Fractal server only supports filesystem paths … support for S3 URLs may be added in the future" ([task_types.md](https://github.com/fractal-analytics-platform/fractal-task-tools/blob/0.5.1/docs/usage/task_types.md)). The code says otherwise. Since fractal-server 2.20.0 ("Add support for S3 for data (#3127)", [changelog](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/changelog.md)), `ZarrUrlStr` and `ZarrDirStr` go through `normalize_url`, which accepts a path that starts with `/` or `s3://` and refuses anything else ([fractal_server/urls.py:6-17](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/urls.py#L6-L17); [types/__init__.py:90-113](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/types/__init__.py#L90-L113)). Whether core tasks and the viewers work on `s3://` data in practice is **[to be validated]**.
- Viewers: "pyramidal OME-Zarr files enable interactive visualization in different modern viewers like ViZarr, MoBIE and napari" (`site@642bd16` index.md). fractal-web links out to viewers via `PUBLIC_FRACTAL_VIZARR_VIEWER_URL`, `PUBLIC_FRACTAL_VOLE_VIEWER_URL`, `PUBLIC_FRACTAL_FEATURE_EXPLORER_URL`, with data through `PUBLIC_FRACTAL_DATA_URL` ([docs/environment-variables.md](https://github.com/fractal-analytics-platform/fractal-web/blob/v1.30.1/docs/environment-variables.md)). The dataset page offers "Open the image in OME-Zarr viewers" (help/docs/reference/dataset.md:40). Napari plugins "to handle Fractal-created OME-Zarrs" were announced on 2026-06-30 ([news post](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/news/2026-06-30-napari-plugins-for-ome-zarr.md); entry point `napari-ome-zarr-navigator`, built on ngio).
- fractal-data is the "Fractal data streaming service", an Express server with three endpoints ([README at v0.6.4](https://github.com/fractal-analytics-platform/fractal-data/blob/v0.6.4/README.md)):
  - `/files/{path-to-zarr}` "serves the content of Zarr files checking user authorization";
  - `/alive`;
  - optional `/vizarr` (static vizarr files from `VIZARR_STATIC_FILES_PATH`; example BioNGFF vizarr 1.2.1).
  
  Authorization: the service forwards the fractal-server cookie, or a bearer token from the fractal-web profile page, to fractal-server to fetch the user's allowed viewer paths (`AUTHORIZATION_SCHEME=fractal-server`, the only scheme). The cookie mode needs the services on one domain or its subdomains. "Prototype to explore serving/viewing zarr data" is the GitHub repository description, not README text (FC-FR-07).
- `GET /auth/current-user/allowed-viewer-paths/` (router prefix `/auth`, [main.py:51](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/main.py#L51)) "Returns a list of data paths that the user should have access to". These are the user's `project_dirs` plus the `zarr_dir` of every dataset in a project the user is verified on (owner or guest); `include_shared_projects=false` returns only `project_dirs`. Source: [app/routes/auth/viewer_paths.py](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/fractal_server/app/routes/auth/viewer_paths.py).

---

## 4. Licence, versions, maturity

### Licence

- "Unless otherwise stated in each individual module, all Fractal components are released according to a BSD 3-Clause License, and Copyright is with the BioVisionCenter at the University of Zurich", which "contracts eXact lab s.r.l. for software engineering and development support" (`site@642bd16` [docs/index.md](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/index.md), "Contributors and license"). GitHub reports `BSD-3-Clause` for fractal-server, fractal-web, fractal-task-tools, fractal-tasks-core, fractal-data and the website repository (GitHub API `license.spdx_id`, read 2026-11-23); fractal-tasks-core's `pyproject.toml` also says `BSD-3-Clause`.

### Versions and release dates (GitHub releases API and PyPI, read 2026-11-23)

- **fractal-server**: 2.28.0, 2026-11-20 (GitHub and PyPI). Before it: 2.28.0a0 (2026-11-18), 2.27.4 (2026-11-13), 2.27.3 (2026-11-10), 2.27.2 and 2.27.1 (2026-11-05), 2.26.0 (2026-10-26), 2.25.4 (2026-10-20), 2.25.3 (2026-10-13). 2.27.0 exists as a GitHub release (2026-11-05) but "is not available on PyPI, please use 2.27.1" ([changelog](https://github.com/fractal-analytics-platform/fractal-server/blob/2.28.0/docs/changelog.md)). Python:
  - 2.25.3 added Python 3.15; CI runs 3.12 and 3.15 on PRs and 3.12–3.15 on main;
  - 2.26.0 "drops support for Python 3.12";
  - PyPI `requires_python` for 2.28.0 is `>=3.13,<3.16`.
- **fractal-web**: v1.30.1, 2026-11-11, is the latest non-alpha. `GET /releases/latest` returns **v1.30.2-a0** (2026-11-20), and GitHub does *not* flag it as a pre-release (`prerelease: false`); it is an alpha by its tag name only (FC-FR-08). fractal-web is not published on PyPI or npm; it ships as GitHub release packages.
- **fractal-tasks-core**: 2.1.0, released 2026-07-13 (PyPI); earlier 2.0.2 (2026-06-23), 2.0.1 (2026-04-01), 2.0.0 (2026-03-25). Python `>=3.11,<3.15`. Main has an "Unreleased" section (ngio 1.1 migration).
- **fractal-task-tools**: 0.5.1, 2026-10-09 (PyPI); 0.5.0, 2026-04-22. Python `>=3.11,<3.16`. No GitHub releases, only tags.
- **fractal-data (corrected, FC-FR-09)**: GitHub releases exist, latest **v0.6.4 (2026-10-26)**, then v0.6.3 (2026-07-24), v0.6.2, v0.6.1, v0.6.0 (2026-03-18). The README install example still pins `FRACTAL_DATA_VERSION=0.1.3a0`, which is stale.
- **fractal-client**: 2.24.1, 2026-10-23 (PyPI).

### Maturity

- "Fractal is under active development", with "over 100 publicly available Fractal tasks"; a bioRxiv preprint (2026) is linked ([index.md](https://github.com/fractal-analytics-platform/fractal-analytics-platform.github.io/blob/642bd16d6ba0654dd1b560ac4357d23854e885d9/docs/index.md), "Status").
- Activity: 24,848 commits on fractal-server main and 3,222 on fractal-web main (GitHub API pagination, read 2026-11-23). fractal-server shipped eight releases between 2026-10-26 and 2026-11-20.
- The docs are uneven:
  - "This section is not in-place yet" (server task-collection page);
  - "The process of defining a single full specification for this interface is still ongoing" (`_task_execution.md`);
  - "This user guide is a work in progress" (web help), with TODO stubs;
  - stale pages: the task-types page on S3 (§3), the image-list page on dataset filters (§2.3), the fractal-web docs on `FRACTAL_RUNNER_BACKEND` values (§2.1), the fractal-data README version pin (§4).
- Production posture: "In our main deployments, we deploy the Fractal services standalone, not via the docker example setup" (run_fractal.md).

---

## 5. Touch points with Spectio

Spectio launches, monitors and steers Nextflow and Snakemake runs on SLURM from a login node, with a web UI, a launch form built from a schema (`nextflow_schema.json` / `config.schema.yaml`, ui-spec §4.6) and an OME-Zarr preview (Viv over key-by-key raw reads, api-and-data-model §5.3.1; HCS plates, S3 and labels are out of 0.0.1). Everything below about Spectio is *inferred* design reasoning from the facts above. It is not a decision.

### 5.1 What Spectio could do with Fractal tasks

**Launch and monitor a Fractal task as an engine step.**
- A Fractal task is a CLI with one JSON in and one JSON out (§1.1). A Nextflow process or a Snakemake rule can call it as `<python> <package_root>/<executable> --args-json a.json --out-json o.json`, with `<executable>` taken from `executable_parallel` or `executable_non_parallel` in the manifest (§1.2).
- No fractal-server is needed to run a task this way. That is *inferred*: the wrapper only parses the two flags (`task_wrapper.py:63-72`), and nothing in it calls a server.
- Spectio already monitors such runs through nf-spectio or Snakemake logging. Fractal-specific monitoring adds nothing at this level.

**Fan-out.** A parallel task becomes one process instance per image. A non-parallel task runs once, given `zarr_urls` and `zarr_dir`. A compound task runs its init, reads `parallelization_list` from the out-JSON, and fans out one compute call per entry with `zarr_url` and `init_args` (§1.4). In Nextflow this is a `splitJson`-style channel from the init output. In Snakemake it is a checkpoint.

**Resources.** Map manifest `meta_*` to engine resources:
- `cpus_per_task` → `cpus` / `threads`;
- `mem` → `memory` / `mem_mb` (fractal-server reads it as MB through `slurm_mem_to_MB`, §2.1);
- `needs_gpu` → a GPU profile.

Spectio's scheduler spec stays the owner of how SLURM resources are set (schedulers-and-monitoring).

**Import the args schema into Launch.** `__FRACTAL_MANIFEST__.json` sits in the installed package root (§1.2). Spectio could read `args_schema_parallel` / `args_schema_non_parallel` and render a form. What is needed:
- **Hide the reserved keys.** `zarr_url`, `zarr_urls`, `zarr_dir` and `init_args` appear as required properties in real schemas (§1.3). Spectio fills them, and refuses them in user input as fractal-server does (`validate_wft_args`).
- **Handle a different schema shape.** nf-schema puts top-level groups under `$defs` with `fa_icon`. Fractal schemas are flat at the top level, with nested objects through `$ref`, `anyOf [X, null]` with `default: null`, and `oneOf` with a `discriminator` (tagged unions). The Launch form needs nested-object and tagged-union widgets, or it falls back to a JSON editor for those fields.
- **Use the restrictions.** `fractal_schema_v1` forbids the hard cases (E01–E22), so a Fractal-aware renderer can rely on them: no `definitions`, every boolean has a default, `oneOf` always has a discriminator.
- **Validate only as a hint.** The schema is not the run-time contract: `@validate_call` is (§1.3). Server-side validation could run the task module's pydantic model, which is heavier, or keep schema validation as advisory.
- **Use the metadata for a task picker.** `category`, `modality`, `tags`, `docs_info` and `docs_link` (§1.2) could drive one.

**OME-Zarr preview of Fractal output.** Fractal output is OME-Zarr NGFF 0.4 by default (0.5 possible) from core tasks (§3), on filesystem paths in practice. Spectio's Viv viewer already reads it key by key from the run's results.
- Gaps against Fractal data: HCS plates (the main Fractal layout), labels and ROI/feature tables (ngio tables) are out of Spectio 0.0.1 (api-and-data-model §5.3.1 "Not in 0.0.1").
- Fractal's own answer: links to vizarr (BioNGFF fork) through fractal-data, plus Vol-E, the Feature Explorer and napari plugins (§3).
- For HCS, Spectio could link out to an existing vizarr or fractal-data deployment rather than render plates itself.

**Optional: drive a Fractal deployment** where one exists. Spectio could call `POST /api/v2/project/{id}/job/submit/` and follow `GET …/job/{job_id}/` and `/job/squeue/` (§2.2), as a "Fractal" environment next to SLURM. Fractal then keeps the image list, provenance and viewer authorization.

### 5.2 What Spectio must not re-implement

- **The image-list state machine.** The type and attribute filters, the `input_types` / `output_types` / workflow-task filter merge, the `TaskOutput` merge and image-list persistence are fractal-server logic (§2.2), and still under-specified ("still ongoing"). If Spectio runs Fractal tasks itself, it should pass explicit `zarr_urls` and treat `image_list_updates` as an output artifact, not rebuild a second image list with its own filter semantics. If users want the image list, they use Fractal.
- **Task collection and environments.** fractal-server already does pip venvs, pixi (lockfile), Apptainer SIF builds (experimental, SSH only) and "custom" registration of an existing interpreter (§1.5). Spectio should run tasks from an environment that already exists (a pixi or venv path, a container image the pipeline names), not add a Fractal package installer.
- **SLURM batching for Fractal jobs.** `batching_config` packs many parallel units into fewer SLURM jobs (§2.1). Within Spectio, Nextflow and Snakemake already own batching (executor queue sizes, `array` jobs, Snakemake groups); a second Fractal-style packer would fight them.
- **Viewer authorization and a zarr streaming service.** fractal-data plus `allowed-viewer-paths` is Fractal's model (§3). Spectio has its own confined raw-route model (api §5.3.1) and must not proxy fractal-data or trust a Fractal cookie without an explicit trust decision (authentication-and-access).
- **The JSON Schema form quirks** fractal-web has already fixed (1.24.0, 1.29.6, 1.29.7, §2.4): reuse the lessons, and do not chase every arbitrary JSON Schema. Accept `fractal_schema_v1` as the dialect for Fractal tasks.

### 5.3 Open questions

1. **Scope.** Does Spectio support Fractal tasks at all in a near version, and if so, as tasks wrapped in Nextflow or Snakemake modules, or as a third engine that submits to fractal-server? This needs a decision (inbox); nothing in the specs covers it today.
2. **Schema dialect in Launch.** Do the Launch form's widgets cover `$ref` objects, `anyOf`-null and discriminated `oneOf`, and how are reserved keys hidden? A spike could render the nine fractal-tasks-core 2.1.0 schemas with the Launch form generator (rendering only, no execution).
3. **Environment.** Where does the task's Python come from on the cluster: a pixi environment, a venv, or an Apptainer image built like fractal-server's (`pixi install --frozen` in `ghcr.io/prefix-dev/pixi`)? **[to be validated]** on the EMBL login node.
4. **Image-list outputs.** How are `image_list_updates` / `image_list_removals` shown in Run detail: as an evidence table, or as new OME-Zarr items for review? Without a server, nobody applies them.
5. **HCS and tables in the preview.** Fractal's main output is HCS plates with ngio tables (parquet, csv, anndata backends, ftc 2.1.0 changelog). Is plate and table viewing a later version, or a link-out to vizarr and the Feature Explorer?
6. **S3.** fractal-server accepts `s3://` zarr URLs (§3). Spectio's preview refuses remote reads in 0.0.1. Is S3-hosted Fractal output out of scope?
7. **Versions to pin.** fractal-task-tools 0.5.x (`fractal_schema_v1`) and NGFF 0.4/0.5 through ngio 0.5.x or 1.1.x; which fractal-server and fractal-web pairing applies if Spectio talks to a server (no compatibility row for 2.28.0 yet)?
8. **Identity, if Spectio drives fractal-server.** fractal-server's sudo runner impersonates users with `sudo -u` and its SSH runner uses per-user keys from profiles (§2.1). How does a Spectio user map to a Fractal user and profile? This needs the security-reviewer.

---

## Sources (all read 2026-11-23)

- `site@642bd16`: `docs/index.md`, `docs/tasks_spec.md`, `docs/build_your_own_fractal_task.md`, `docs/image_list.md`, `docs/run_fractal.md`, `docs/fractal_templates.md`, `docs/news/2026-03-31-fractal-workflow-templates.md`, `docs/news/2026-06-30-napari-plugins-for-ome-zarr.md`, `templates_data_retrieval/raw/`.
- `ftt@0.5.1`: `docs/usage/manifest.md`, `docs/usage/task_types.md`, `docs/usage/run_task.md`, `docs/changelog.md`, `src/fractal_task_tools/{task_models.py,_create_manifest.py,_specs.py,task_wrapper.py,logging_config.py}`.
- `ftc@2.1.0`: `docs/install.md`, `CHANGELOG.md`, `pyproject.toml`, `pixi.lock`, `fractal_tasks_core/__FRACTAL_MANIFEST__.json`; `CHANGELOG.md` on main.
- `server@2.28.0`:
  - docs: `README.md`, `docs/changelog.md`, `docs/install_and_deploy.md`, `docs/internals/integrations/{runners.md,tasks.md,_task_execution.md}`;
  - schemas: `app/schemas/v2/{manifest.py,task.py,task_collection.py,job.py}`;
  - models: `app/models/v2/{task.py,dataset.py,job.py,resource.py}`;
  - routes: `app/routes/api/v2/{submit.py,job.py,latest_job.py,task_collection*.py,__init__.py}`, `app/routes/auth/{router.py,viewer_paths.py}`;
  - other: `main.py`, `config/_main.py`, `runner/config/{_local.py,_slurm.py}`, `runner/executors/{slurm_common,slurm_sudo,slurm_ssh}/…`, `runner/v2/{runner.py,task_interface.py}`, `images/tools.py`, `types/__init__.py`, `types/validators/*`, `urls.py`, `tasks/v2/templates/apptainer_template.def`.
- `web@v1.30.1`: `docs/{index.md,environment-variables.md,version-compatibility.md,changelog.md}`, `help/docs/{index.md,concepts/tasks.md,reference/jobs.md,reference/dataset.md}`, `help/snippets/workflows.md`, `src/env.js`, `src/routes/v2/jobs/+page.server.js`, `package.json`.
- `data@v0.6.4`: `README.md`; GitHub repository description.
- ngio: `src/ngio/ome_zarr_meta/ngio_specs/_ngio_image.py` at v0.5.8, v0.5.14 and v1.1.5; `README.md` at v0.5.8, v0.5.14 and v1.1.5.
- GitHub API: releases, `/releases/latest`, licences, commit counts. PyPI JSON: fractal-server, fractal-tasks-core, fractal-task-tools, fractal-client, fractal-uzh-converters.

---

## Verification table

V = verified, C = corrected (wrong or partly true; finding below), U = unverifiable as stated, marked **[to be validated]**. "Resolved" means the digest had marked it [to be validated] and the primary source now settles it (counted as V).

| # | Claim (digest §) | Verdict | Source | Correction |
|---|---|---|---|---|
| 1 | Tasks are OME-Zarr processing units given Zarr URLs on disk or in the cloud (1.1) | V | tasks_spec.md | — |
| 2 | Tasks are Linux CLI executables; a Python function processing an OME-Zarr (1.1) | V | build_your_own_fractal_task.md:3 | — |
| 3 | `--args-json` / `--out-json` signature, client and server side (1.1) | V | run_task.md; task_wrapper.py:63-72; _task_execution.md | — |
| 4 | `run_fractal_task` wrapper; run-time validation via `@validate_call` (1.1) | V | run_task.md; manifest.md | "typically" |
| 5 | Task log env vars and default format (1.1) | V | run_task.md; logging_config.py | — |
| 6 | Package must contain `__FRACTAL_MANIFEST__.json` (1.2) | V | tasks_spec.md; schemas/v2/manifest.py | — |
| 7 | `task_list.py` + `fractal-manifest create/check` (1.2) | V | ftt manifest.md | — |
| 8 | Manifest fields `executable`/`executable_init`/`meta`/`meta_init` (1.2) | C | schemas/v2/manifest.py; task_models.py | FC-FR-01 |
| 9 | `docs_info`, `category`, `modality`, `tags` semantics and standard values (1.2) | V | tasks_spec.md | — |
| 10 | `authors`, with pyproject fallback (1.2) | V | tasks_spec.md; ftt manifest.md | manifest-level field |
| 11 | Metadata makes tasks searchable (1.2) | V | tasks_spec.md | — |
| 12 | One or two JSON Schemas per task (1.3) | V | ftt manifest.md | — |
| 13 | Schemas not used at run time; basis of fractal-web forms (1.3) | V | ftt manifest.md | — |
| 14 | `args_schema_version = "fractal_schema_v1"` since 0.5.0; `pydantic_v2` until 0.4.\* (1.3) | V | manifest.md; _create_manifest.py:22; changelog 0.5.0 | — |
| 15 | E01–E22 restrictions, "full list E01–E22" (1.3) | C | manifest.md; _specs.py | FC-FR-10 (minor) |
| 16 | Examples repo; `dict[int,int]` caveat (1.3) | V | manifest.md | — |
| 17 | Five task types (1.4) | V | schemas/v2/task.py:22-31 | — |
| 18 | Required args per type (table) (1.4) | V | task_types.md | — |
| 19 | Reserved keywords set by server, not by user (1.4) | V | task_types.md; _workflow_task_arguments_validators.py:1-9 | — |
| 20 | "Fractal server only supports filesystem paths" (1.4, 3, 5) | C | urls.py:6-17; changelog 2.20.0 | FC-FR-02 |
| 21 | `zarr_dir` meaning (1.4) | V | task_types.md | — |
| 22 | Output metadata keys and update-entry fields (1.4) | V | task_types.md; task_interface.py | — |
| 23 | Compound parallelization list (1.4) | V | task_types.md; task_interface.py | — |
| 24 | Tasks-page listing needs PyPI or wheel; pixi future (1.5) | V | tasks_spec.md | scope: website listing only |
| 25 | `fractal-tasks-template` recommended (1.5) | V | build_your_own_fractal_task.md | — |
| 26 | `pip install fractal-tasks-core`; collection name (1.5) | V | ftc docs/install.md | — |
| 27 | tasks-core moved poetry → pixi in 2.0.0 (1.5) | V | ftc CHANGELOG.md | dev tooling only |
| 28 | Collection modes pip, pixi, apptainer, custom (1.5) | V | routes/api/v2/task_collection*.py | — |
| 29 | 2.28.0 experimental Apptainer on SSH-SLURM (1.5) | V | changelog 2.28.0 | — |
| 30 | Apptainer doc: SIF from pixi, SSH only, `tasks_apptainer_config`, `APPTAINER_BINDPATH` (1.5) | V | docs/internals/integrations/tasks.md | — |
| 31 | fractal-web pixi 1.19.0, lockfile 1.24.0 (1.5) | V | web changelog | — |
| 32 | Pip collections; Python 3.9/3.10 deprecated 2.27.x; collection docs "not in-place yet" (1.5) | V | server changelog; tasks.md | 2.27.0 not on PyPI |
| 33 | Conda not documented; Docker demo only (1.5) | V (resolved) | code search; install_and_deploy.md:32 | no conda collection mode |
| 34 | fractal-server "server component" / "Fractal backend" (2.1) | V | README; repo description | — |
| 35 | Runner class hierarchy, three runners (2.1) | V | runners.md | — |
| 36 | `jobs_runner_config` local and SLURM fields (2.1) | V | runner/config/_local.py, _slurm.py | — |
| 37 | fractal-web selects backend via `FRACTAL_RUNNER_BACKEND` ∈ {local, slurm, slurm_ssh} (2.1) | C | web src/env.js:23-31; server config/_main.py:69-71 | FC-FR-03 |
| 38 | Deployment-model quote (2.1) | V | run_fractal.md | — |
| 39 | `FRACTAL_STOP_SLURM_JOBS_ON_SHUTDOWN` 2.27.3; sudo artifact fix 2.25.2 (2.1) | V | server changelog | — |
| 40 | SLURM polling mechanism unknown (2.1) | V (resolved) | base_slurm_runner.py:182-266 | `squeue`, not `sacct` |
| 41 | `execute_tasks` inputs (2.2) | V | _task_execution.md | — |
| 42 | Type-filter precedence "dataset < input_types < wftask" (2.2, 5.4) | C | runner.py:121-152; images/tools.py:106-128; changelog 2.14.0 | FC-FR-04 |
| 43 | Dispatch by type (2.2) | V | _task_execution.md | — |
| 44 | Post-task merge and image-list replacement (2.2) | V | _task_execution.md | — |
| 45 | API route names; OpenAPI (2.2) | V | routes/api/v2/*.py | paths added; bodies [to be validated] |
| 46 | `PUBLIC_UPDATE_JOBS_INTERVAL` default 3000 (2.2) | V | web environment-variables.md | — |
| 47 | Jobs help page is TODO stubs (2.2) | V | help/docs/reference/jobs.md | — |
| 48 | Squeue modal in 1.29.5 (2.2) | V | web changelog | — |
| 49 | v2 data-model list (2.3) | V | models/v2/ tree | — |
| 50 | Dataset definition and image list (2.3) | V | help/docs/reference/dataset.md | — |
| 51 | Task and workflow definitions (2.3) | V | help concepts/tasks.md; snippets/workflows.md | — |
| 52 | Image-list fields; attribute filters per job (2.3) | V | image_list.md | — |
| 53 | "Continue Workflow" prefilled with dataset attribute filters (2.3) | C | models/v2/dataset.py, job.py; changelog 2.14.0 | FC-FR-05 |
| 54 | Workflow templates details unknown (2.3) | V (resolved) | changelog 2.20.0; news 2026-03-31 | — |
| 55 | SvelteKit app; node server proxies to fractal-server (2.4) | V | web docs/index.md:17-19 | — |
| 56 | `FRACTAL_SERVER_HOST`, cookies, OAuth2; compatibility 1.30.x ↔ 2.27.0 (2.4) | V | environment-variables.md; version-compatibility.md | no row for 2.28.0 |
| 57 | Args-schema/meta upload in task-collection UI, 1.7.1 (2.4) | C | web changelog 0.7.1, 1.7.1 | FC-FR-06 |
| 58 | Other UI features (schema-form fixes, pixi, sharing, viewer links) (2.4) | V | web changelog | — |
| 59 | User guide "work in progress" (2.4) | V | help/docs/index.md:3 | — |
| 60 | OME-Zarr framework; TBs quote (3) | V | site index.md | — |
| 61 | HCS plate examples; dataset HCS options; modalities (3) | V | image_list.md; dataset.md:45-47 | — |
| 62 | NGFF: only 0.4.0 historical; current version unknown (3) | V (resolved) | ftc pyproject.toml:17; ngio _ngio_image.py:28-29 | 0.4 + 0.5, default 0.4 |
| 63 | Viewers: ViZarr, MoBIE, napari (3) | V | site index.md | — |
| 64 | fractal-web viewer env vars; dataset viewer options (3) | V | environment-variables.md; dataset.md:40 | — |
| 65 | fractal-data endpoints, auth, vizarr 1.2.1 (3) | V | data README v0.6.4 | plus `/alive` |
| 66 | fractal-data README says "Prototype…" (3, 4) | C | GitHub repo description; README v0.6.4 | FC-FR-07 (minor) |
| 67 | `allowed-viewer-paths` behaviour (3) | V | auth/viewer_paths.py | full path under `/auth` |
| 68 | BSD-3-Clause; BioVisionCenter; eXact lab (4) | V | site index.md; GitHub API | — |
| 69 | fractal-server 2.28.0 on 20 Nov (2026), cadence, Python support (4) | V | GitHub releases API; PyPI | year 2026 confirmed |
| 70 | fractal-web v1.30.1 stable; v1.30.2-a0 "pre-release" marked Latest (4) | C | GitHub releases API | FC-FR-08 (minor) |
| 71 | fractal-tasks-core 2.1.0, date unknown (4) | V (resolved) | PyPI | 2026-07-13 |
| 72 | fractal-task-tools 0.5.1, date unknown (4) | V (resolved) | PyPI | 2026-10-09 |
| 73 | fractal-data pins 0.1.3a0; no releases (4) | C | GitHub releases API | FC-FR-09 |
| 74 | "Under active development", over 100 tasks (4) | V | site index.md | — |
| 75 | Commit counts 24,848 / 3,222 (4) | V | GitHub API | — |
| 76 | Docs-unevenness quotes (4) | V | tasks.md; _task_execution.md; help index | — |
| 77 | Production posture quote (4) | V | run_fractal.md | — |
| 78 | Running a task needs no server (5.1) | U | task_wrapper.py (inference) | *inferred*; a spike settles it |
| 79 | `meta` maps directly to Nextflow/Snakemake resources (5.1) | U | get_slurm_config.py | *inferred*; units and key set differ |
| 80 | OpenAPI bodies at `./openapi/` (2.2, 5.4) | U | not re-read | [to be validated] |
| 81 | fractal-web 1.30.1 works with fractal-server 2.28.0 | U | no compatibility row | [to be validated] |
| 82 | Core tasks and viewers work on `s3://` data | U | server accepts `s3://`; task side not checked | [to be validated] |
| 83 | Origin of "Continue Workflow" attribute prefill today | U | — | [to be validated] (pairs with FC-FR-05) |

**Counts:** 83 rows. **Verified 67**; 6 of them were [to be validated] in the digest and are now settled by the source (33, 40, 54, 62, 71, 72), and 5 hold only with a narrower scope, given in the last column (10, 24, 27, 32, 45). **Corrected 10** (8, 15, 20, 37, 42, 53, 57, 66, 70, 73), of which 4 are major (8, 20, 37, 73). **Unverifiable 6** (78–83), each marked [to be validated] in the body.

---

## Corrections

Wrong or partly-true claims, dropped from (or rewritten in) the body above. Format: `docs/reviews/README.md`.

### FC-FR-01 · major · Manifest field names are those of `task_list.py`, not of the JSON manifest

- **Where:** digest §1.2, third bullet ("Task-model fields shown in the manifest example: `executable` / `executable_init` … `meta` / `meta_init`"); reused in digest §5.1.
- **Evidence:** the example in ftt `manifest.md` is Python `task_list.py` (`ConverterCompoundTask(executable_init=…, executable=…, meta_init=…, meta=…)`). The JSON manifest schema (`TaskManifestV2`, server@2.28.0 `app/schemas/v2/manifest.py`) has `executable_non_parallel`, `executable_parallel`, `meta_non_parallel`, `meta_parallel`, `args_schema_*`, `input_types`, `output_types`, `docs_link`, `type`, and at manifest level `manifest_version: "2"`, `has_args_schemas`, `args_schema_version`, `authors`. ftt `task_models.py:48-73` maps `executable_init` → `executable_non_parallel` and `executable` → `executable_parallel` for compound types. Confirmed on ftc@2.1.0's `__FRACTAL_MANIFEST__.json`. Read 2026-11-23.
- **Problem:** a Spectio importer written from the digest would look for keys that do not exist in any manifest.
- **Proposal:** parse the JSON keys above; treat `task_list.py` names as authoring-side only (done in §1.2).
- **Found by:** fact-checker
- **Status:** open

### FC-FR-02 · major · fractal-server accepts `s3://` zarr URLs since 2.20.0

- **Where:** digest §1.4 ("only supports filesystem paths"), §3 ("Zarr locations are filesystem paths today").
- **Evidence:** the sentence is on ftt@0.5.1 `task_types.md`, but the server code says otherwise. fractal-server changelog 2.20.0 "Runner: Add support for S3 for data (#3127)". `fractal_server/urls.py:6-17` `normalize_url`: "S3- aware URL normalization… URLs must begin with '/' or 's3://'". `ZarrUrlStr` / `ZarrDirStr` use it (`types/__init__.py:90-113`). Read 2026-11-23.
- **Problem:** the digest presents an outdated doc sentence as current behaviour; Spectio's scope question on remote Zarr (S3) would be answered wrongly.
- **Proposal:** state "the server accepts `/…` and `s3://…`; task-side and viewer support for S3 [to be validated]" (done in §3).
- **Found by:** fact-checker
- **Status:** open

### FC-FR-03 · major · `FRACTAL_RUNNER_BACKEND` values and role

- **Where:** digest §2.1 ("fractal-web selects the backend via `FRACTAL_RUNNER_BACKEND`, which is one of `local`, `slurm`, `slurm_ssh`").
- **Evidence:** web@v1.30.1 `src/env.js:28` `checkAllowedValues('FRACTAL_RUNNER_BACKEND', input, ['local', 'slurm_sudo', 'slurm_ssh'])`, so `slurm` is rejected; the docs page is stale. The backend is selected server-side: server@2.28.0 `config/_main.py:69` `FRACTAL_RUNNER_BACKEND: Literal["local", "slurm_ssh", "slurm_sudo"] = "local"` and the resource `type`. fractal-web only reads the value to adapt pages (`src/routes/v2/jobs/+page.server.js:4,31`). Read 2026-11-23.
- **Problem:** wrong value (`slurm`) and wrong owner of the choice.
- **Proposal:** values `local | slurm_sudo | slurm_ssh`; server selects, web mirrors (done in §2.1).
- **Found by:** fact-checker
- **Status:** open

### FC-FR-04 · minor · Type filters do not come from the dataset, and there is no precedence order

- **Where:** digest §2.2 pre-task bullet ("dataset < manifest `input_types` < per-workflow-task filters"), repeated in §5.4.
- **Evidence:** server@2.28.0 `runner/v2/runner.py:121` `current_type_filters = copy(job_type_filters)`, `:147-152` patch with `merge_type_filters(task_input_types=…, wftask_type_filters=…)`, `:446-448` update with `task.output_types`. `images/tools.py:106-128` raises "Cannot merge type filters" when task and workflow task disagree. changelog 2.14.0 "Drop attribute/type filters from dataset table. Add `type_filters` column to job table". Read 2026-11-23.
- **Problem:** the described override chain does not exist; conflicts are errors, and the base is the job, not the dataset.
- **Proposal:** use the code-level description (done in §2.2).
- **Found by:** fact-checker
- **Status:** open

### FC-FR-05 · minor · "Continue Workflow" prefilled "from the dataset" is a stale doc statement

- **Where:** digest §2.3 image-list bullet.
- **Evidence:** the quote is on site@642bd16 `image_list.md`, but `DatasetV2` at server@2.28.0 has no filter columns (`models/v2/dataset.py`: `zarr_dir`, `images` only); filters live on `JobV2` (`models/v2/job.py:62-65`) since 2.14.0. Read 2026-11-23.
- **Problem:** the claim describes a removed data model.
- **Proposal:** keep the quote as "documented", and mark where the prefill comes from today [to be validated] (done in §2.3).
- **Found by:** fact-checker
- **Status:** open

### FC-FR-06 · minor · Args-schema and meta upload: version 0.7.1, single-task creation

- **Where:** digest §2.4 ("task collection UI with args-schema/meta file uploads (1.7.1)").
- **Evidence:** web@v1.30.1 `docs/changelog.md`, 0.7.1: "Added the following fields on single task creation: args schema file upload (#364), meta file upload (#364)". 1.7.1 is about settings and making `FRACTAL_RUNNER_BACKEND` mandatory (#570). Read 2026-11-23.
- **Problem:** wrong version and wrong feature.
- **Proposal:** corrected in §2.4.
- **Found by:** fact-checker
- **Status:** open

### FC-FR-07 · minor · "Prototype to explore serving/viewing zarr data" is the repository description

- **Where:** digest §3 and §4 (attributed to the fractal-data README).
- **Evidence:** GitHub API `description` = "Prototype to explore serving/viewing zarr data"; README at v0.6.4 opens with "the **Fractal data** streaming service", and the project has six releases from v0.6.0 to v0.6.4. Read 2026-11-23.
- **Problem:** wrong attribution; it overstates immaturity relative to the released v0.6.x line.
- **Proposal:** cite the repository description as such (done in §3).
- **Found by:** fact-checker
- **Status:** open

### FC-FR-08 · minor · v1.30.2-a0 is not flagged as a pre-release

- **Where:** digest §4, fractal-web versions.
- **Evidence:** GitHub releases API: `v1.30.2-a0`, `published_at 2026-11-20T11:08:40Z`, `prerelease: false`; `GET /releases/latest` returns `v1.30.2-a0`. Read 2026-11-23.
- **Problem:** anyone automating "latest release" would get an alpha; the digest's wording hides that.
- **Proposal:** pin fractal-web by tag (`v1.30.1`), never by "latest" (done in §4).
- **Found by:** fact-checker
- **Status:** open

### FC-FR-09 · major · fractal-data has releases; latest is v0.6.4

- **Where:** digest §4 ("install example pins `FRACTAL_DATA_VERSION=0.1.3a0`; the repo's Releases section shows no releases").
- **Evidence:** GitHub releases API: v0.6.4 (2026-10-26), v0.6.3 (2026-07-24), v0.6.2 (2026-06-05), v0.6.1 (2026-05-20), v0.6.0 (2026-03-18). The `0.1.3a0` pin is a stale README example (README on main, line 66). Read 2026-11-23.
- **Problem:** wrong maturity and version information.
- **Proposal:** corrected in §4.
- **Found by:** fact-checker
- **Status:** open

### FC-FR-10 · minor · The E-code list is not contiguous and not final

- **Where:** digest §1.3 ("full list E01–E22 on the page").
- **Evidence:** ftt@0.5.1 `manifest.md` lists E01–E08, E10–E15, E20–E22 (no E09, E16–E19) and says the list "is currently evolving, and the ground truth is in the `_specs.py` module". Read 2026-11-23.
- **Problem:** small, but a renderer built against "E01–E22" may assume checks that do not exist.
- **Proposal:** cite `_specs.py` at the pinned tag as the contract (done in §1.3).
- **Found by:** fact-checker
- **Status:** open
