---
icon: material/memory
---
# Run resources and an extra config file

!!! note "Built on the integration branch, not released yet"

    Run resources and the extra config file work end to end from a checkout, 2026-11-11: the server (FU-P3-110a), the engines (FU-P3-110b), the boards (FU-P3-110c) and the screens (FU-P3-110d), batch [P3-B15](../progress/W5/P3-M9.md#batch-p3-b15). The first release is 0.0.1 ([development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version)). **Not run:** a real pipeline on either engine with these fields through the screens, and Nextflow 26.10 for the order of config files **[to be validated]**.

Launch can set, for one run, **default resources** (CPUs, memory and time per task) and **one extra config file**. The fields, the bounds and what each engine gets are owned by [api §5.7](../specs/api-and-data-model.md#57-run-resources-and-an-extra-config-file-001); the screens by [ui-spec §4.6](../specs/ui-spec.md#46-launch-and-relaunch).

## On Launch

Both are folding rows of **Where it runs**, under the environment. Both are optional.

![Launch from a catalog entry, with Resources open (2 CPUs, 3 GiB, 1 h per task) and Extra config file open with a path typed; the Summary beside it lists Resources and Extra config](../assets/shots/app-launch-resources_light.webp#only-light)
![Launch with Resources and Extra config file open, dark](../assets/shots/app-launch-resources_dark.webp#only-dark)

*A seeded server with one environment, Two cores (at most 2 CPUs and 4 GiB). Launch was not pressed.*

**Resources**

- **CPUs per task**, **Memory per task** (a number with MiB or GiB) and **Time per task** (hours and minutes). Each is optional, and each hint shows its bounds and the environment's cap: "1 to 256 · at most 2 (Two cores)".
- **A default, not an override.** A process (Nextflow) or a rule (Snakemake) that sets its own CPUs, memory or time keeps them. The row says so. On Nextflow the values replace a general `process` setting of the pipeline's own `nextflow.config` **[to be validated]** (api §5.7).
- **On a `local` environment with caps,** a value above the cap is refused before Launch: "At most 2 CPUs in Two cores".
- **On a SLURM environment,** an empty Memory or Time says what applies instead: "Empty: 32 GiB, from Long jobs, mylab". The run's value replaces the environment's, for this run only.
- **Snakemake takes no CPUs here:** it takes them from each rule's threads ("Snakemake takes CPUs from each rule's threads"). With a Snakemake workflow profile the profile owns the resources, so the row shows the profile line in place of the inputs.

**Extra config file**

- **One typed path,** absolute, in your home directory or in the pipeline's own directory. There is no picker: the browser cannot list the server's files.
- **Nextflow:** a `.config` file, passed with `-c` before Spectio's own. It runs as you, like the pipeline's `nextflow.config`. **Snakemake:** a `.yaml`, `.yml` or `.json` file of workflow config, merged key by key under the form's values; with a file, the form sends only the keys you set. It is not a profile and sets no resources.
- **Read once, kept with the run.** When you press Launch, the server reads the file (owner, mode and size, then a copy), hashes it, and keeps the copy in the run directory, mode 0600, as `extra.config` (`extra.yaml` or `extra.json` on Snakemake). A later edit of your file changes no run. At most 256 KiB, UTF-8.
- **Refused with the reason** on the input, in the server's words: a file writable by group or others, a symbolic link, no such file, over 256 KiB, a Snakemake file that is not a map or sets `__use_yte__`. A `503` ("The extra config file could not be read: …") keeps your values.
- **`includeConfig`** in a Nextflow file loads other files when the run starts; those are not kept, and Run detail warns.

## What the engines get

From the code of FU-P3-110b (`packages/spectio/src/spectio/runner/headscript.py`), checked against Nextflow 25.10.9 and Snakemake 9.27.1 by the step's order tests:

| | Nextflow | Snakemake |
|---|---|---|
| CPUs | `process.cpus = <n>` in `.spectio/spectio.config` | refused |
| Memory | `process.memory = '<n> MB'` | `mem_mb=<n>` in the one `--default-resources` list |
| Time | `process.time = '<n>m'` | `runtime=<n>` in the same list |
| The file | `-c .spectio/extra.config,.spectio/spectio.config`: yours first, Spectio's last, so its generic keys win | `--configfile .spectio/extra.yaml .spectio/params.json`: the later file wins, key by key |

The first line of `head.out` names them: "Spectio: run: cpus 8, memory 65536 MiB, time 720 min; config extra.config (sha256 238f89866940)".

## On Run detail

![A finished run's Facts: Default resources "8 CPUs · 64 GiB · 12 h per task, set at Launch · processes that set their own keep them", and Extra config file with its path, "kept as extra.config · 167 B · SHA-256 238f89866940…", the buttons View extra.config and Copy SHA-256](../assets/shots/app-run-resources_light.webp#only-light)
![A finished run's Facts with Default resources and Extra config file, dark](../assets/shots/app-run-resources_dark.webp#only-dark)

*A run record written by hand, with the file placed in its run directory: no engine ran it. Its Environment therefore reads "not recorded".*

- **Default resources** shows the values, what they replaced on a SLURM environment ("time: 48 h from mylab-long" for a key left out), and "processes that set their own keep them". A run with neither field has no such rows, nor has a run started from a terminal.
- **Extra config file** shows the original path, "kept as extra.config", the size and the start of the SHA-256. **Copy SHA-256** copies all of it and says so.
- **View extra.config** opens the kept copy as text. Only then does Spectio read it, so Run detail never fetches a possibly sensitive file on every visit.

![The sheet of View extra.config: the path and size, then the kept text with a withName block for ALIGN](../assets/shots/app-run-config-file_light.webp#only-light)
![The View extra.config sheet, dark](../assets/shots/app-run-config-file_dark.webp#only-dark)

- **"Changed since the launch"** shows in the sheet when the kept copy's hash differs from the recorded one, and "The kept copy of extra.config is not in the run directory any more." when it is gone. A `503` says "The run directory did not answer; try again." with **Retry**. Close and Escape return the focus to the button.
- **Resume and Copy to a new launch.** Resume's sheet says what it reuses ("Same resources as before.", "The same kept config file (extra.config) as before."); it copies the parent's kept bytes and refuses a copy whose hash changed. Copy to a new launch prefills both rows and lists the path as "Extra config file: loads code or configuration".

## On the API

Against the demo server of the shots (2026-11-11), with the session cookie and the loopback `Origin`; the demo's home directory is not the host's, so the file path is refused on purpose in the last line:

```console
GET /api/v1/runs/<tuned>   200  default_resources {"cpus": 8, "mem_mib": 65536, "time_min": 720, "state": "recorded"}
                                config_file {"path": ".../lab-tweaks.config", "kept_as": "extra.config", "sha256": "238f8986…", "size": 167, "includes": false, "state": "recorded"}
GET /api/v1/runs/<tuned>/config-file   200  text/plain; charset=utf-8, etag "238f898669406a62…", 167 bytes
POST /api/v1/runs {"default_resources": {"cpus": 4}}        422  default_resources.cpus: At most 2 CPUs in Two cores
POST /api/v1/runs {"default_resources": {"mem_mib": "4"}}   422  default_resources.mem_mib: Input should be a valid integer
POST /api/v1/runs {"config_file": "/tmp/x.config"}          422  config_file: Choose a file in your home directory or in the pipeline
```

## Not shown, and open

- **Not shown:** the 422 and 503 states on the input, the SLURM wording, the Snakemake rows, and the phone. `vitest` covers them (`LaunchResources.test.tsx`, `RunDetailExtras.test.tsx`, `ResumeDialog.test.tsx`); no shot does.
- **Not run:** the Playwright launch smoke with an extra file (api §5.7), and the new CSS in a browser other than the shots' Chromium.
- **Open findings:** the file's text stays in the page's state after the View sheet closes (SEC-P3FU110D-01); config file text appears in reprs and validation errors (SEC-P3FU110B-02). The CI step that runs the order fixtures is held back for Thomas (a PR that changes `.github/workflows/` waits for him). See [Follow-ups of batch P3-B15](../progress/W5/P3-M9.md#follow-ups-of-batch-p3-b15).

## Next

- [Environments](environments.md): the caps and defaults these values meet.
- [Your pipeline catalog](pipeline-catalog.md): the entry Launch loads.
- [Progress page of milestone M9](../progress/W5/P3-M9.md).
