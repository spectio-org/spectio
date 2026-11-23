# Bilayers: evaluation for Spectio (2026-11-23)

*Checked 2026-11-23 by the fact-checker agent. Code read at these commits:*

| Short | Repository | Commit (date) |
|---|---|---|
| **B** | [bilayer-containers/bilayers](https://github.com/bilayer-containers/bilayers/tree/ad5939637904fe6a9b67cd5a1ec124e952d273aa) | `ad59396` (2026-11-04) |
| **S** | [bilayers-schema](https://github.com/bilayer-containers/bilayers-schema/tree/8bd685779a81affa0494cc48eb30b5f9296ba8f0) | `8bd6857` (2026-08-17) |
| **A** | [bilayers-algorithms](https://github.com/bilayer-containers/bilayers-algorithms/tree/3d8c60cdbca97f352a9ebf726e15ead8775aa9ca) | `3d8c60c` (2026-11-19) |
| **T** | [bilayers-targets](https://github.com/bilayer-containers/bilayers-targets/tree/ee4a9782200841eca48c0e90daf29830a31bd5a0) | `ee4a978` (2026-08-21) |
| **NF** | [nf-core/modules](https://github.com/nf-core/modules/tree/9804fc814f848fd7100b2203e35ff6d5321d031f) | `9804fc8` (2026-11-23) |
| **SW** | [snakemake/snakemake-wrappers](https://github.com/snakemake/snakemake-wrappers/tree/93934d79422e7af7668844faeb6a0baf3ce97cf3) | `93934d7` (2026-11-20) |

Below, `B:README.md:12` means file:line at the commit above. Where the docs and the code disagree, this note follows the code and says so.

## 1. The spec

**Who.** A Broad Institute project led by Beth Cimini, maintained by Rajavi Shah, Nodar Gogoberidze and Beth Cimini (`B:pyproject.toml:9-18`, `B:LICENSE:3`, `B:CITATION.cff`).

**Code layout.** Since the "Phase 4" split (Aug 2026) the project spans four repos: **S** holds the LinkML schema, **A** the tool configs and Dockerfiles, **T** the interface generators, and **B** the CLI and CI (`B:pyproject.toml:21-26`; PRs [T#1](https://github.com/bilayer-containers/bilayers-targets/pull/1), [B#177](https://github.com/bilayer-containers/bilayers/pull/177), read 2026-11-23).

**File format.** One `config.yaml` per tool, validated against a **LinkML** schema (`S:src/bilayers_schema/schema.yaml:1-13`; `bilayers_cli validate` calls `linkml.validator.validate`, `B:src/bilayers/cli.py:88-103`).

**Top level** (`SpecContainer`, `S:schema.yaml:19-29`): `inputs`, `outputs`, `parameters` (all required), `display_only`, `exec_function` (required), `docker_image` (required), `algorithm_folder_name` (required), and `citations` (required).
- `exec_function`: `name` (always `generate_cli_command`), the base `cli_command` (e.g. `python -m cellpose --verbose`), and `hidden_args` (`cli_tag`, `value`, `append_value`, `cli_order`). Hidden args are appended but never shown (`S:schema.yaml:169-209`; `B:docs/custom_algorithm/understanding_config.md:129-195`).
- `docker_image`: `org`, `name`, `tag` and `platform` are all required. That is **one image and one platform**, with no digest (`S:schema.yaml:177-184, 249-268`).
- `inputs` / `outputs` (`S:schema.yaml:31-101`) have the fields `name`, `type`, `label`, `description`, `cli_tag`, `cli_order`, `default`, `optional`, `format`, `unique_string`, `folder_name`, `file_count`, `section_id` and `mode`.
    - `format` is a list of free strings, not an enum (`:347-350`).
    - `folder_name` is a **container-side path** (e.g. `/bilayers/input_images`).
    - `unique_string` holds glob-like markers that identify a tool's files (`:355-359`).
    - When `type: image`, the fields `subtype` (grayscale / color / binary / label), `depth`, `timepoints`, `tiled` and `pyramidal` become required (`:57-78`).
- `parameters` (`S:schema.yaml:103-166`) have the fields `name`, `type`, `label`, `description`, `default` (**required**, `:295-298`), `cli_tag` (required), `cli_order`, `optional`, `section_id`, and `mode` (`beginner | advanced`, `:399-403`). Some fields apply only to some types:
    - `options` (label/value pairs) for `radio` and `dropdown`;
    - `multiselect` for `dropdown` (the docs say it accepts only `False`, `understanding_config.md:714-718`);
    - `append_value` for `checkbox` (emit `--tag True/False`, or emit the bare flag only when true);
    - `output_dir_set` for an output-folder textbox.
- `display_only`: read-only fields shown in the UI and never passed on the command line (`understanding_config.md:853-857`).
- Type enum (`S:schema.yaml:383-398`):
    - parameter types: `integer, float, boolean, checkbox, dropdown, radio, textbox`;
    - input/output types: `image, measurement, array, file, executable`.

**Not in the schema at `8bd6857`.** All of these are absent from the whole file:
- numeric `min`/`max`, a regex pattern, units;
- CPU, memory or GPU requirements;
- a schema version;
- a secret type.

Open PRs would add some of them:
- [S#11](https://github.com/bilayer-containers/bilayers-schema/pull/11) (open, updated 2026-11-10) adds `structure` and a required `schema_version` (`bilayers-0.1.0`).
- [S#10](https://github.com/bilayer-containers/bilayers-schema/pull/10) (open) adds `secret`.
- Optional run requirements (GPU, CUDA) are only discussed, in [B#197](https://github.com/bilayer-containers/bilayers/issues/197) (read 2026-11-23).

Already, `A:src/bilayers_algorithms/cellsam_inference/config.yaml:90` uses `type: secret`, and [B#204](https://github.com/bilayer-containers/bilayers/pull/204) (merged 2026-11-04) keeps secrets out of the CLI sequence. The code is therefore ahead of the schema on `main`.

**Breaking 1.0.0 schema changes are in progress** ([S#8](https://github.com/bilayer-containers/bilayers-schema/issues/8), open, read 2026-11-23). They include:
- a new `algorithm:` block (id, licence, tags);
- `structure`, `path_kind` and `path_role` on inputs and outputs;
- `schema_version`.

**CLI mapping** (`B:docs/custom_algorithm/understanding_config.md:163-183`):
- Flags are appended to `cli_command` as `tag value`, or as `tag=value` when `cli_tag` ends in `=`.
- Ordering: a positive `cli_order` gives a fixed position; 0 or absent means unordered, after the ordered ones; a negative value goes last.
- `cli_tag: ""` gives a positional value; `"None"` means no flag at all.
- Library code: `generate_cli_command` builds the command from **defaults only** (`item.get("default")`, `B:src/bilayers/cli_generator.py:54`) and joins it with spaces (`:92`). User values are applied only inside the generated interfaces.

**Generated interfaces.** The targets registry lists `gradio`, `jupyter`, `streamlit` and `cellprofiler_plugin` (`T:src/bilayers_targets/registry.py:5-10`; extras in `B:pyproject.toml:28-43`). This is more than the docs and bilayers.org say: they list only Gradio and Jupyter (`B:docs/custom_algorithm/supported_interfaces.md:9-12`; [bilayers.org](https://bilayers.org), read 2026-11-23). A **Hail Batch** target exists only as a draft PR labelled "vibe-coded" ([T#15](https://github.com/bilayer-containers/bilayers-targets/pull/15), opened 2026-11-10). There is **no Nextflow, Snakemake, CWL, WDL or Galaxy target** in `registry.py`.

**Build and publish.** `nox` runs the steps in order: `build_algorithm`, then `build_interface` (`B:noxfile.py:200-340`).
1. `build_algorithm` pulls `org/name:tag` for the given `--platform`. If the pull fails, it builds the tool's Dockerfile (`:207-295`).
2. `build_interface` builds `Gradio.Dockerfile` or `Jupyter.Dockerfile` `FROM $BASE_IMAGE`. These add pip packages and `app.py` or a notebook, and `EXPOSE 7878` (`T:interfaces/gradio/Gradio.Dockerfile`, `T:interfaces/jupyter/Jupyter.Dockerfile`).
3. The result is tagged `bilayer/<algorithm>:<version>-<interface>` (`B:noxfile.py:307-339`).

The CI workflow runs **only on manual `workflow_dispatch`**: its push and PR triggers are commented out "until caching system is implemented" (`B:.github/workflows/docker-build.yml:3-12, 87`).

## 2. How a Bilayers tool runs

**Documented path.** Pull the interface image and run it, with Docker Desktop or `docker run -it --rm bilayer/<repo>:<tag>`. Jupyter needs `-v /data:/bilayers/input_images` (`B:docs/tool_user/steps_to_run.md:13-69`). The documented CLI command publishes no port; how users reach the UI then is **[to be validated]** (see the share link below).

**Gradio app** (`T:interfaces/gradio/gradio_template.py.j2`):
- copies the uploaded files into `folder_name`;
- builds one command string (`:171`) and runs it with `subprocess.run(..., shell=True)` (`:253`);
- zips the outputs;
- launches on `0.0.0.0:7878` with `share=True` (`:522`).

Gradio documents `share=True` as creating "a publicly shareable link", tunnelled through the FRP server at gradio.live ([Gradio Blocks docs](https://www.gradio.app/docs/gradio/blocks), read 2026-11-23).

**CellProfiler plugin target.** This is the closest pattern to a batch step (`T:plugins/cellprofiler_plugin/cellprofiler_plugin_template.py.j2:504-684`). It runs Docker or Podman only, with `[runtime, "run", "--rm", -v host:folder_name …, image, *cli_command tokens, tag, value …]` as an argument list, not a shell string.

**Apptainer / Singularity.** Neither the code nor the docs mention them. A maintainer wrote on 2026-11 that they "don't regularly use Singularity", but "don't see any reason why most of not all would not work" ([A#9](https://github.com/bilayer-containers/bilayers-algorithms/issues/9), read 2026-11-23). **[to be validated]** by a spike.

**HPC / SLURM.** The only mention is aspirational: "can also be deployed to an HPC or to the cloud" (`B:README.md:12`; bilayers.org). The code has no SLURM, scheduler, resource or GPU-request support.

**OME-Zarr.** Not supported at `main`.
- No config lists `ome-zarr` or `zarr`: input formats across the 7 configs are tiff, ometiff, png, jpg, bmp, npy, h5 and similar (`A:src/bilayers_algorithms/*/config.yaml`).
- The schema has no `zarr` value. It only has `tiled` and `pyramidal` booleans for images (`S:schema.yaml:375-380`).
- Two open proposals would add it: `format: [ome-zarr]` with `structure: [plate]` ([B#197](https://github.com/bilayer-containers/bilayers/issues/197), [S#8](https://github.com/bilayer-containers/bilayers-schema/issues/8)), and the `structure` slot of S#11.

**Published images.** [Docker Hub `bilayer`](https://hub.docker.com/u/bilayer) has 6 repositories (API, read 2026-11-23):
- `classical_segmentation` 1.0.0 (base, gradio, jupyter): **arm64 only**, updated 2024-11-06. This disagrees with its config, which says `linux/x86_64`.
- `cellpose` 1.0.0 and 1.0.1-gradio: amd64, 2024-11-05.
- `instanseg` 1.0.2 (`_pixi_gradio`, `_pixi_jupyter`) and `instanseg-cuda`: amd64, 2024-11.
- `gaussian_smoothing` 1.0.0: amd64, 2025-09-16.
- `stardist` 7.0.0: **arm64 only**, 2025-12-02. The config points instead to `rajavishah/stardist:8.0.0`, `linux/arm64/v8` (`A:…/stardist_inference/config.yaml`).

There are no Streamlit tags, and no image for `cellsam` (config `bilayer/cellsam:1.0.0`). Pull counts range from 185 to 617.

## 3. Licence, versions, maturity

**Licence.**
- `B:LICENSE` is a "BSD-style" licence: Broad copyright, the three BSD-3 conditions, and a Broad-specific disclaimer and remedy clause (`:1-40`). That is why GitHub reports `NOASSERTION`.
- `pyproject.toml` and `CITATION.cff` say `BSD-3-Clause`.
- S, A and T are `BSD-3-Clause` (GitHub API, read 2026-11-23).

**Versions.**
- The package is `0.1.0` (`B:pyproject.toml:7`; `bilayers_cli 0.1.0`, `B:cli.py:36`).
- One GitHub release, `v1.0.0rc1`, was published 2025-11-19 at `eadf9c8` with **empty notes** (API, read 2026-11-23).
- The Zenodo DOI is [10.5281/zenodo.17652333](https://doi.org/10.5281/zenodo.17652333) (`B:README.md:1`).
- Not on PyPI as far as checked: dependencies are `git+https` URLs (`B:pyproject.toml:21-26`). **[to be validated]** on pypi.org.

**Activity** (GitHub API, read 2026-11-23).
- Last commits: B 2026-11-04, A 2026-11-19, S 2026-08-17 (with open PRs updated 2026-11-10), T 2026-08-21.
- B has 21 stars, 7 forks and 36 open issues and PRs, and contributors rajavishah (227 commits), gnodar01 (53), bethac07 (30) and helia77 (2).
- Several tool PRs are open: ASHLAR, Elastix, MorphEm, CellSAM.

**Maturity signals.** Pre-1.0, with a breaking schema revision under way (S#8). Maintainers say the docs are outdated (A#9). Image builds are manual, and images are stale and single-architecture.

**The arXiv paper is not about Bilayers.** [arXiv:2306.01915](https://arxiv.org/abs/2306.01915) is "CellProfiler plugins – an easy image analysis platform integration for containers and Python tools" (Weisbart … Cimini; v2 2023-08-15). It never mentions Bilayers. It is context for the CellProfiler-plugin target only.

**Stated non-goals.** Bilayers is "not trying to recreate nextflow, or snakemake, or cwl/wdl"; it is "the master lego brick catalog, not individual kits" (`B:README.md:25`). The README also says the spec "will also aid sysadmins design and validate workflows … in tools such as Nextflow or Snakemake" (`:12`).

## 4. Touch points with Spectio

Spectio context:
- the Launch form is built from `nextflow_schema.json` or `config.schema.yaml` (api-and-data-model §5, `workflows:inspect`);
- single-module and single-rule runs are planned for 0.0.2 behind `single_target` (api-and-data-model §5.10);
- Spectio is engine-transparent and does not run containers itself (decision log line 78).

**4.1 Importing a Bilayers spec into the Launch form (proposal).** A `bilayers` schema source could map the spec onto the form as follows.

| Bilayers spec | Launch form |
|---|---|
| `integer` / `float` | number fields |
| `checkbox` / `boolean` | toggle (keep `append_value`) |
| `radio` / `dropdown` | enum with labels |
| `textbox` | text field |
| `mode: advanced` | the collapsed section |
| `section_id` | groups |
| `display_only` | read-only rows |
| `hidden_args` | not shown |
| `inputs` | path pickers |

Gaps the form must handle:
- There are no bounds or patterns, so validation is weaker than with nf-schema.
- `default` is always required, so "unset" is encoded by Bilayers' own `set_*` checkbox trick in the Gradio template (`:323-338`).
- `folder_name` is a path *inside* the container, so the form needs a host path that the step binds onto it.
- A `secret` must never be written to `params.json`.

**4.2 Running a Bilayers tool from Spectio.**
- Spectio should not exec containers itself. The fitting path is to wrap the **base algorithm image** (not the `-gradio`/`-jupyter` image) as a local Nextflow module (`main.nf` + `meta.yml`) or a Snakemake rule. A §5.10 target run then launches, follows and relaunches it with other parameters.
- The command is `cli_command` plus the ordered flags (§1), with binds `host_dir:folder_name`. Use an argument list, as the CellProfiler target does, not `shell=True`.
- On SLURM this would be the engine's Apptainer support pulling `docker://…`: **[to be validated]** by a spike.
- arm64-only images (classical_segmentation, stardist) will not run on x86_64 nodes.
- **Never launch interface images on compute nodes.** They start a server and, with `share=True`, open a public gradio.live tunnel.

**4.3 What Spectio must not re-implement:**
- the spec and its validator (use `bilayers-schema` / `bilayers_cli validate`);
- the interface generators;
- the image build and publish pipeline;
- the tool catalogue.

A "Bilayers → nf-core-style module or Snakemake rule" generator fits Bilayers' own plugin registry (`T:registry.py`). It belongs as an upstream target, like the Hail Batch draft, not inside Spectio (**proposal**).

**4.4 OME-Zarr preview.** Bilayers cannot yet declare OME-Zarr outputs. `outputs[].unique_string` and `format` could help Spectio find a step's output images for preview, once B#197 lands **[to be validated]**.

## 5. nf-core modules and Snakemake wrappers compared

| | Bilayers `config.yaml` | nf-core module `meta.yml` | Snakemake wrapper `meta.yaml` |
|---|---|---|---|
| Validation | LinkML (`S:schema.yaml`) | JSON Schema draft 2020-12; required `name, description, keywords, authors, output, tools` (`NF:modules/meta-schema.json`) | none: no schema file in the repo tree at `93934d7` |
| Inputs / outputs | typed (image, file, array…), formats, image flags | channel elements typed `map`/`file`/`eval`, with `pattern` and ontologies (`NF:modules/nf-core/fastqc/meta.yml:21-65`) | free-text lists (`SW:bio/fastqc/meta.yaml`) |
| Tool parameters | **typed**, with defaults, options, UI hints and CLI mapping | **untyped**: `extra_args` holds descriptions only, and arguments pass as the `task.ext.args` string (`NF:…/fastqc/main.nf:25`) | **untyped**: `params` is free text, and `extra` is a raw string (`SW:bio/fastqc/wrapper.py:15`) |
| Software | one Docker image + platform | Docker and Singularity (`oras://`) per architecture, plus conda lock files (`meta.yml:88-111`) | conda `environment.yaml` + pin file |
| Execution | interface generators; no engine target | a `process` in `main.nf`, launched alone in Spectio 0.0.2 (§5.10) | `wrapper.py` through the `wrapper:` directive (`SW:bio/fastqc/test/Snakefile`) |

**Scope of "custom tools as modules"** (recommendation for Thomas, not verified fact). The request is a Python or R script, plus its container, plus a parameter spec, launched on the cluster, followed, and relaunched with other parameters. It splits cleanly:
- **Description and packaging** (spec, container, build, catalogue) belong to a partner standard. Bilayers fits bioimage tools; nf-core module tooling fits Nextflow.
- **Launch, follow and relaunch** belong to Spectio. §5.10 already covers them, if the tool is wrapped as a local module or rule.

Spectio's own addition would be a parameter form for such targets. Today `targets:inspect` returns a module's inputs only, not typed tool parameters (api §5.10). Bilayers is the only one of the three formats with typed tool parameters to read them from.

## 6. Open questions and spikes

1. Spike: do `bilayer/cellpose:1.0.0` and `gaussian_smoothing:1.0.0` run under Apptainer on slurm-mini, with `/bilayers/*` binds and a non-root user?
2. Spike: hand-write one local Nextflow module around `bilayer/gaussian_smoothing:1.0.0`, and launch it as a §5.10 target.
3. Ask the maintainers whether they would accept a `nextflow_module` or `snakemake_rule` target in `bilayers-targets`, and whether `schema_version` (S#11) lands before 1.0.0.
4. After S#8 lands, re-check the field names: `default` optional? `path_kind`? `algorithm:` block?
5. How should Spectio surface the single-platform `docker_image.platform` against the cluster's architecture?

## 7. Claim checks (fact-checker format, 2026-11-23)

| # | Claim | Location | Verdict | Source | Correction |
|---|---|---|---|---|---|
| 1 | Bilayers is a container spec from the Cimini lab, Broad | brief | verified | `B:LICENSE:3`, `B:README.md` | none |
| 2 | arXiv 2306.01915 gives Bilayers context | brief | wrong | arxiv.org/abs/2306.01915 | the paper covers CellProfiler plugins; cite Zenodo 10.5281/zenodo.17652333 |
| 3 | "currently supports Gradio and Jupyter" | `B:README.md:12`, bilayers.org | partly true | `T:registry.py:5-10` | code also has Streamlit and CellProfiler plugin; images exist only for Gradio and Jupyter |
| 4 | containers "can also be deployed to an HPC" | `B:README.md:12` | unverifiable | A#9 | no HPC or Apptainer support or tests; settle by spike 1 |
| 5 | configs live in `bilayers/src/bilayers/algorithms/` | `B:docs/custom_algorithm/understanding_config.md:10` | wrong | **A** repo; A#9 | they live in `bilayers-algorithms/src/bilayers_algorithms/<name>/` |
| 6 | outputs make the spec usable by Snakemake, Nextflow, WDL | same file `:23-24` | partly true | `T:registry.py` | intent only: no such target exists |
| 7 | images built by the Bilayers CI/CD | README, bilayers.org | partly true | `docker-build.yml:3-12` | the build is manual dispatch only |
| 8 | Bilayers handles OME-Zarr | (question) | wrong at `main` | `S:schema.yaml`, A configs | only proposed (B#197, S#8, S#11) |
| 9 | licence is BSD-3-Clause | `B:pyproject.toml:19` | partly true | `B:LICENSE` | BSD-3 conditions with a Broad disclaimer and remedy; S, A and T are plain BSD-3 |

### FC-B01 · major · The arXiv reference is not a Bilayers source
- **Where:** research brief (Bilayers note), source list.
- **Evidence:** arXiv:2306.01915 is titled "CellProfiler plugins – an easy image analysis platform integration for containers and Python tools" and does not mention Bilayers.
- **Problem:** a spec citing it for Bilayers would mis-attribute claims.
- **Proposal:** cite the repo at a commit and Zenodo 10.5281/zenodo.17652333. Keep 2306.01915 only for the CellProfiler-plugin target.
- **Found by:** fact-checker
- **Status:** open

### FC-B02 · major · "HPC-deployable" is aspirational, and some images are arm64 only
- **Where:** `B:README.md:12`, bilayers.org.
- **Evidence:** no Apptainer, SLURM or resource code. A maintainer says Singularity is not regularly used (A#9). `classical_segmentation` and `stardist` are arm64 only on Docker Hub.
- **Problem:** Spectio cannot assume a Bilayers image runs on x86_64 SLURM nodes.
- **Proposal:** any Spectio spec text on Bilayers says "OCI images, Apptainer **[to be validated]**". Run spike 1. The import checks `docker_image.platform` against the cluster.
- **Found by:** fact-checker
- **Status:** open

### FC-B03 · major · Interface images are interactive servers with a public share link
- **Where:** `T:gradio_template.py.j2:253, 522`.
- **Evidence:** `subprocess.run(cli_command, shell=True)` on a space-joined string; `app.launch(..., share=True)`.
- **Problem:** launching a `-gradio` image as a task would hang a SLURM slot and open a gradio.live tunnel. Copying its command building would bring shell injection into Spectio.
- **Proposal:** Spectio runs only base algorithm images, with an argument list, as `cellprofiler_plugin_template.py.j2:647-684` does.
- **Found by:** fact-checker
- **Status:** open

### FC-B04 · minor · The interface list and config paths in the docs are out of date
- **Where:** `B:docs/custom_algorithm/supported_interfaces.md:9-12`, `understanding_config.md:10`.
- **Evidence:** see claims 3 and 5 of the table.
- **Problem:** a reader following the docs looks in the wrong place and misses two interfaces.
- **Proposal:** when Spectio cites Bilayers, cite the code repos at a commit, not the docs site.
- **Found by:** fact-checker
- **Status:** open

### FC-B05 · minor · OME-Zarr and typed bounds are absent at `main`
- **Where:** `S:schema.yaml` (whole file).
- **Evidence:** no zarr format and no min/max anywhere. Proposals exist only in B#197, S#8 and S#11.
- **Problem:** a Bilayers-based form gives weaker validation than nf-schema, and cannot drive the OME-Zarr preview.
- **Proposal:** mark both **[to be validated]** in any spec text, and re-check after schema 1.0.0.
- **Found by:** fact-checker
- **Status:** open

**Sources read (33):**
- **B:** README, LICENSE, pyproject, CITATION, myst.yml, `cli.py`, `cli_generator.py`, `noxfile.py`, `docker-build.yml`, and 3 docs pages.
- **S:** `schema.yaml`.
- **A:** the 7 configs and 1 Dockerfile.
- **T:** `registry.py`, the Gradio template, 2 Dockerfiles, the CellProfiler template.
- **GitHub:** issues S#8, B#197, B#167 and A#9; PRs T#15 and S#11; the repos, branches, PR, release and contributor APIs.
- **Docker Hub:** the tag API for 6 repositories.
- **Web:** bilayers.org, arXiv, Gradio docs.
- **NF:** meta-schema, fastqc `meta.yml` and `main.nf`.
- **SW:** fastqc `meta.yaml`, `environment.yaml`, `wrapper.py` and the test Snakefile.
- **Spectio:** api-and-data-model §5.10.
