# Spike D2: what a Claude Code cloud session can run (2026-10-26)

**Question.** In a Claude Code cloud session, which of these work, and with what limits?
- `docker run` and `docker compose`;
- sind: create a cluster with 1 controller and 1 worker, then `sbatch --wait`;
- kind: create a cluster, then run a Job;
- Nextflow 26.10: install it and run a hello pipeline;
- Snakemake 9 with the SLURM executor plugin against sind;
- Playwright with the pre-installed Chromium;
- mermaid-cli.

The spike also records memory, disk, timings and every network domain the proxy blocked. It ends with the exact Custom allowlist and a budget for the setup script.

**Time box:** 60 minutes. About 27 minutes were used, from 21:10Z to 21:37Z. An item was stopped after two failed attempts.

**Answer in one line.** Docker, Compose, Nextflow, Snakemake (local), Playwright and mermaid-cli work. sind and kind do not, because the VM boots with a hybrid cgroup v1 layout that a session cannot change. SLURM and Kubernetes scenarios therefore run in CI and on a developer machine, not in cloud sessions.

## Setup

| Fact | Value | Evidence |
|---|---|---|
| VM | Firecracker microVM (`rdinit=/process_api -- --firecracker-init` on the kernel command line), Ubuntu 24.04.5, kernel 6.18.44, user `root` | `fixtures/vm-kernel-cmdline-6.18.44.txt` |
| CPU and memory | 4 vCPU, 16 091 MiB, no swap. No memory pressure during the spike: PSI `total=0` | LOG §0 and §10 |
| Disk | `/` reports a 252 G device, with 11 G used and 29 G available at the start, so about 40 G in practice. 22 G were left at the end. The [docs](https://code.claude.com/docs/en/cloud-environments.md#resource-limits) say "30 GB of disk". | LOG §0 and §10 |
| cgroups | Hybrid layout. Each v1 controller is mounted under `/sys/fs/cgroup/<ctrl>`, and cgroup2 is mounted at `/sys/fs/cgroup/unified` with only `hugetlb`. The sandbox uses the v1 memory hierarchy for itself (`process_api/…` and `sbx-telemetry` cgroups). | LOG §3, "inspect the cgroup layout" |
| Pre-installed | Docker 29.9.2 with Compose v5.6.1 and buildx (the daemon is **not running** at start, and there is no systemd), Java 21.0.12, Node 22.22.0, Python 3.13, uv 0.11.32, Go 1.24.7, and Playwright 1.63.0 with Chromium 153 under `/opt/pw-browsers` | LOG §0, §1, §8 |
| Network | Every outbound HTTPS connection goes through the agent proxy (`HTTPS_PROXY`, CA `/root/.ccr/ca-bundle.crt`). This session's environment reached every host probed, including some outside the Trusted list (`example.com`, `quay.io`, `nf-co.re`), so it is not on Trusted. Whether it is on Full or on a broad Custom list cannot be read from inside the session **[to be validated]**. | `fixtures/domains-proxy-2026-10-26.tsv`, `fixtures/agentproxy-status-2026-10-26.json` |
| Installs | All user-level, under `spikes/cloud-env/.tools/` (git-ignored, 1.9 G at the end). The exception is puppeteer's first run, which wrote 676 MB to `~/.cache/puppeteer`. | LOG §10 |

## Result

| Item | Works | Limits | Time (cold) |
|---|---|---|---|
| `docker run` | **yes** | **Starting the daemon.** It must be started by hand (`dockerd &` as root). A daemon is a process, so it is not kept in the environment snapshot ([docs](https://code.claude.com/docs/en/cloud-environments.md#environment-caching)). Every session has to start it.<br>**Container network.** Containers on a bridge network are intercepted transparently by the proxy. TLS inside them fails unless they trust the proxy CA (mount `/root/.ccr/ca-bundle.crt`). The alternative is `--network host` with `HTTPS_PROXY`.<br>**Docker Hub.** After about 6 anonymous pulls it answered **429 Too Many Requests**, and it was still 429 on retry. `dockerd --registry-mirror=https://mirror.gcr.io` fixed it.<br>**cgroups.** Docker runs on cgroup v1. | daemon 1 s; `hello-world` 1.7 s |
| `docker compose` | **yes** | Same limits as `docker run`. Health checks, `depends_on: service_healthy` and a port published to the host (`curl 127.0.0.1:20080` → 200) all work. | 19.4 s (nginx, postgres, alpine) |
| sind (1 controller + 1 worker, `sbatch --wait`) | **no** | **Install.** `go install github.com/GSI-HPC/sind/cmd/sind@v0.13.0` works. `GOTOOLCHAIN=auto` fetches Go ≥ 1.26 from `proxy.golang.org`.<br>**Attempt 1.** `sind doctor` and `sind create cluster` refuse to start: "Docker runs containers on cgroup v1 (sind requires cgroupv2)".<br>**Attempt 2.** dockerd ran in a private mount namespace, with cgroup2 mounted at `/sys/fs/cgroup` with `nsdelegate`. sind's checks then passed, but container creation failed: "NanoCPUs can not be set … the cgroup is not mounted". The cpu, memory and pids controllers stay bound to the v1 hierarchies that the sandbox itself uses, so v2 only has `hugetlb`.<br>**Fix.** Only a VM booted with the unified hierarchy would allow it (`systemd.unified_cgroup_hierarchy=1` or `cgroup_no_v1=all`), and a session cannot change that. | install 39 s; no cluster |
| kind (cluster + Job) | **no** | **Install.** kind v0.33.0 (`go install`) and kubectl v1.37.1 (dl.k8s.io, sha256 checked) install fine.<br>**Attempt 1.** With the default node image `kindest/node:v1.37.0`, kubeadm failed and the API server never answered (88 s).<br>**Attempt 2.** With `kindest/node:v1.34.0` and `--retain`, kubelet started, warning "cgroup v1 support is in maintenance mode". Then every static pod failed with `CreatePodSandboxError`, so the API server never came up (250 s). The exact runc message was cut off before the node was deleted **[to be validated]**. The cause is very likely the same cgroup v1 layout **[to be validated]**. | install 21 s; create fails |
| Nextflow 26.10 install + hello | **yes** | **Install.** 26.10.0 (build 14055), from the pinned asset `github.com/nextflow-io/nextflow/releases/download/v26.10.0/nextflow-26.10.0-dist` (49 MB). The redirect goes to `release-assets.githubusercontent.com`.<br>**Runs.** A local 4-task pipeline (`spikes/cloud-env/nf-hello/main.nf`) ran in 4.6 s; with `-with-docker ubuntu:24.04` it took 5.1 s.<br>**Not tested.** `nextflow run <GitHub repo>`: the session's auto-mode permission classifier refused it ("Code from External"). The `get.nextflow.io` installer was not tested either. **[to be validated]** | install 3 s; run 5 s |
| Snakemake 9 + SLURM executor plugin against sind | **partly** | **Install.** Snakemake 9.27.1 with `snakemake-executor-plugin-slurm` 2.8.0, through `uv tool install` (PyPI).<br>**Works.** A local run (2.3 s) and `--executor slurm -n`.<br>**Fails.** A real `--executor slurm` run: "No such file or directory: 'sacct'". There is no sind cluster to submit to (row above). | install 8 s |
| Playwright + Chromium | **yes** | Pre-installed: `require('playwright')` resolves to `/opt/node-tools`, with `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`. Nothing was reinstalled. An HTTPS page loads through the proxy (`launch({proxy:{server: HTTPS_PROXY}})`). The repository's board renderer (`tools/canvas/render.js`) produced a correct `RunDetail` PNG, which was checked by looking at it. The pinned version is the pre-installed **1.63.0**: another pin would need a browser download. | launch 1.5 s; board 3.9 s |
| mermaid-cli | **yes, with two settings** | mermaid-cli 11.17.0, run with `npx -y @mermaid-js/mermaid-cli@11` as in `CLAUDE.md`.<br>**As root.** The command as written fails: "Running as root without --no-sandbox is not supported". It needs `-p puppeteer-config.json` containing `{"args":["--no-sandbox"]}`.<br>**Browser download.** By default, puppeteer's postinstall downloads its own Chrome (676 MB). With `PUPPETEER_SKIP_DOWNLOAD=1` and `PUPPETEER_EXECUTABLE_PATH=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome`, the pre-installed Chromium is reused and the cold run takes 21 s. | 21–29 s cold, 8 s warm |

## Network

**Blocked by the domain allowlist: none.** 43 URLs were probed (`spikes/cloud-env/probe-domains.sh`). Every relevant hop was traced (`redirect-hosts.sh`). `recentRelayFailures` in the proxy status stayed empty all session. This only says that nothing was blocked at this session's level, which is broader than Trusted. A Custom list must be checked again (follow-up 3).

**Refused for other reasons.**

| What | Answer | Cause | Consequence |
|---|---|---|---|
| `api.github.com/repos/<repo>/…`, `github.com/<repo>/releases/latest` (sind, nextflow-io) | 403 "GitHub access to this repository is not enabled for this session" | The GitHub proxy's repository scope. It serves only the repositories attached to the session, and applies whatever the access level is ([docs](https://code.claude.com/docs/en/cloud-environments.md#github-proxy)). `archive/` and `codeload` URLs get the same 403. | Bootstrap must use **explicit tags**: `releases/download/<tag>/<asset>` passes for any public repository (302, then `release-assets.githubusercontent.com`). It must never resolve "latest" through GitHub. |
| `registry-1.docker.io` manifests | 429 Too Many Requests | Docker Hub's anonymous rate limit on the shared egress | `--registry-mirror=https://mirror.gcr.io` for dockerd. With the mirror set, every later Docker Hub pull worked (`kindest/node`, `bash`, `ubuntu`). Whether the mirror served them or Docker Hub had recovered was not checked. |
| `go install …@latest` combined with a GitHub binary download; `nextflow run hello` | refused before running | The session's auto-mode permission classifier, not the network | A pinned `go install …@v0.13.0`, checked by sum.golang.org, was allowed. Remote pipelines need an explicit permission rule (follow-up 5). |

**Hosts the toolchain uses, and whether the Trusted list ([docs](https://code.claude.com/docs/en/cloud-environments.md#default-allowed-domains)) covers them.**

| Host | Used for | In Trusted |
|---|---|---|
| `release-assets.githubusercontent.com`, `github.com` (pinned tags only) | Nextflow dist, sind or kind binaries | yes |
| `proxy.golang.org`, `sum.golang.org` | `go install` of sind and kind, and the Go 1.26 toolchain | yes |
| `dl.k8s.io` | kubectl | yes |
| `pypi.org`, `files.pythonhosted.org` | Snakemake and its plugins | yes |
| `registry.npmjs.org` | mermaid-cli, puppeteer | yes |
| `registry-1.docker.io`, `auth.docker.io`, `production.cloudfront.docker.com` | Docker Hub (rate-limited) | yes |
| `mirror.gcr.io` | Docker Hub mirror | yes (`*.gcr.io`) |
| `ghcr.io` | sind-node image | yes |
| `pkg-containers.githubusercontent.com` | **blobs behind ghcr.io** | **no** |
| `quay.io` | biocontainers (nf-core) | **no** |
| `cdn01.quay.io` (`cdn0N`) | **blobs behind quay.io** | **no** |
| `community.wave.seqera.io`, `cerbero.seqera.io` (token), `community-cr-prod.seqera.io` (blobs) | Seqera containers (nf-core) | **no** |
| `registry.k8s.io` → `us-east5-docker.pkg.dev` (the region varies) | Kueue and other Kubernetes images | **no** |
| `get.nextflow.io`, `www.nextflow.io`, `registry.nextflow.io` | Nextflow installer, plugin registry | **no** |
| `nf-co.re` | nf-core tooling and docs | **no** |
| `conda.anaconda.org`, `repo.anaconda.com` | conda / bioconda | yes |
| `prefix.dev` | pixi | **no** |
| `storage.googleapis.com` | puppeteer's own Chrome (avoided, see above) | yes |
| `cdn.playwright.dev`, `playwright.download.prss.microsoft.com` | only for a Playwright other than 1.63.0 | **no**, and not needed |

### Recommended Custom allowlist

Network access set to **Custom**, with **"Also include default list of common package managers"** checked. The **Allowed domains** field gets these lines:

```text
get.nextflow.io
www.nextflow.io
registry.nextflow.io
nf-co.re
quay.io
*.quay.io
community.wave.seqera.io
cerbero.seqera.io
community-cr-prod.seqera.io
pkg-containers.githubusercontent.com
registry.k8s.io
*.pkg.dev
prefix.dev
*.prefix.dev
```

- `ghcr.io`, `conda.anaconda.org` and the `*.gcr.io` mirror are already in the default list, so they are dropped from the spec's draft list.
- GitHub traffic does not go through this allowlist ([docs](https://code.claude.com/docs/en/cloud-environments.md#allow-specific-domains)), so no GitHub host is needed in it.
- Not checked yet **[to be validated]**:
  - where Nextflow plugin downloads redirect to, from `registry.nextflow.io`;
  - whether `*.prefix.dev` is the right pattern for pixi's channel host;
  - whether `*.pkg.dev` covers every region that `registry.k8s.io` may redirect to.

## Setup-script budget

What the setup script would do, with the cold timings measured here:

| Step | Measured | Keep in the cloud setup? |
|---|---|---|
| start dockerd with `--registry-mirror=https://mirror.gcr.io` | 1 s | yes. It is needed for the pulls, then started again by a SessionStart hook, because processes are not kept in the snapshot |
| Nextflow 26.10 dist (pinned tag) | 3 s | yes. 25.10.x would be another ~3 s **[to be validated]** |
| Snakemake 9 + SLURM, Kubernetes and Kueue plugins (`uv tool install`) | 8–12 s with the SLURM plugin only | yes |
| mermaid-cli with `PUPPETEER_SKIP_DOWNLOAD=1` | 21 s | yes |
| pre-pull the Compose images (nginx, postgres, alpine) | 19 s | yes, and later Spectio's own images |
| Go toolchain + sind + kind + kubectl | 60 s | **no**: neither runs here |
| pre-pull `kindest/node` (22 s) and `sind-node` (1.35 GB) | ~45 s | **no** |

- **Budget:** about **60 s** measured for what is kept, and at most **150 s** as a target. That is half of the roughly five-minute limit beyond which the environment is not cached ([docs](https://code.claude.com/docs/en/cloud-environments.md#script-requirements)), with room for slower registries.
- **Parallel downloads:** run them with `&` and `wait`.
- **Not measured:** the script itself was not run as a real setup script. Whether the snapshot keeps `/var/lib/docker` is stated in the docs but **[to be validated]** here.

## Evidence

All paths are on branch `spike/cloud-env`.
- `spikes/cloud-env/LOG.md`: every command, with its output, exit code and wall time.
- `spikes/cloud-env/fixtures/`:
  - `docker-29.9.2-info.txt`;
  - `sind-0.13.0-doctor-cgroupv1.txt`;
  - `vm-kernel-cmdline-6.18.44.txt` (the kernel command line and the cgroup mounts);
  - `domains-proxy-2026-10-26.tsv` (43 probes);
  - `redirect-hosts-2026-10-26.txt`;
  - `agentproxy-status-2026-10-26.json`;
  - `nextflow-26.10.0-local-hello-trace.tsv`;
  - `snakemake-9.27.1-slurm-2.8.0-no-cluster.log`;
  - `playwright-1.63.0-chromium-153.0-smoke.png`;
  - `mermaid-cli-11.17.0-flow.svg`.
- `spikes/cloud-env/`: the scripts and inputs:
  - `probe-domains.sh` and `redirect-hosts.sh`;
  - `pw-smoke.js`;
  - `compose/compose.yaml`;
  - `nf-hello/main.nf`;
  - `smk-hello/Snakefile`;
  - `mmd/flow.mmd` and `mmd/puppeteer-config.json`.

## What it changes in `docs/specs/dev-environment-and-testing.md`

These are proposals for the apply step. The spec is not edited here.

- **§0, decision 2.** Keep "no real HPC needed". Add that sind and kind run in CI and on a developer machine, **not in cloud sessions** (hybrid cgroup v1). Cloud sessions run engine, Compose and UI work only.
- **§0, decision 4, and §2 "Setup script".**
  - Setup script: `bash dev/bootstrap.sh --ci`, without the cluster tools.
  - A SessionStart hook starts `dockerd --registry-mirror=https://mirror.gcr.io` when it is not running.
  - Replace "about 5 minutes" with the measured budget above.
- **§1, toolchain table.**
  - **Nextflow:** resolve its **[to be validated]**. The pinned `releases/download/v<ver>/nextflow-<ver>-dist` asset works through the proxy, and `releases/latest` does not.
  - **sind:** resolve its **[to be validated]**. Install with `go install github.com/GSI-HPC/sind/cmd/sind@v<pin>`, which needs Go ≥ 1.26, or with the release asset at an explicit tag. sind needs cgroup v2 with `nsdelegate`.
  - **kind:** `go install sigs.k8s.io/kind@v<pin>`.
  - **Playwright:** pin 1.63.0 in the cloud, to match `/opt/pw-browsers`.
  - **mermaid-cli:** needs `--no-sandbox` as root, and `PUPPETEER_SKIP_DOWNLOAD` / `PUPPETEER_EXECUTABLE_PATH`.
- **§1 "Checks".**
  - `dev/doctor.sh` starts dockerd when it is missing.
  - It reports sind and kind as **skipped**, with the reason from `sind doctor` (cgroup v1), instead of failing. Otherwise it can never be green in a cloud session.
- **§2, table row "Cloud sessions".** Add the facts measured here:
  - Firecracker VM, 4 vCPU, 16 GiB, no swap, about 40 G of disk;
  - hybrid cgroup v1;
  - Docker installed but not running;
  - the Docker Hub 429;
  - the GitHub repository scope;
  - the auto-mode classifier, which refuses remote code.
- **§2 "Cloud environment settings", Network.** Replace the draft list with the recommended Custom allowlist above, and note that GitHub hosts are governed separately.
- **§4.2, last paragraph.** Answer it: kind does **not** run in a cloud session, so Kubernetes scenarios run in CI and on the user's machine. **§4.1** needs the same sentence for sind.
- **§5.** The scenario matrix with `slurm-*` and `k8s-*` profiles cannot run in cloud sessions. Only the `local` scheduler with the bundle or Compose deployments can.
- **§7.2.** The Codespaces dev container relies on Docker-in-Docker for sind and kind, so it needs cgroup v2 there too **[to be validated]**.
- **§9.** D2 is answered. D3's "run them green in a cloud session" applies to the non-cluster layers only.

## Follow-ups

1. **Platform request.**
   - Ask whether Anthropic-hosted cloud VMs can boot with the unified cgroup v2 hierarchy.
   - That would unlock sind and kind in cloud sessions.
   - Until then, this is a platform limitation and should not be worked around.
2. **CI check (D3).** Run `sind create cluster` with `sbatch --wait`, and `kind create cluster` with a Job, on a GitHub Actions `ubuntu-24.04` runner, which has cgroup v2 **[to be validated]**. CI is now the main place for the tier with real clusters.
3. **Recheck the allowlist.** Set this environment to Custom with the list above, then run `spikes/cloud-env/probe-domains.sh` and a real `nextflow run nf-core/demo -profile test,docker` again.
4. **Setup script and cache.** Run `dev/bootstrap.sh --ci` as a real setup script. Time it, and confirm that the snapshot keeps the pulled images and that `dockerd` comes back through the hook.
5. **Inbox question for Thomas.** Should the project's permission settings allow running remote pipelines (`nextflow run <repo>`) and pinned `go install` in auto mode? The classifier refused `go install …@latest` combined with a GitHub binary download, and `nextflow run hello`. It allowed a pinned `go install`.
6. **kind diagnosis (optional).** Keep the full `CreatePodSandbox` error to confirm the cgroup v1 cause. This is only useful if the platform answer to follow-up 1 is "no".
7. **`CLAUDE.md` mermaid command.** In cloud sessions, as root, it needs `-p` with `--no-sandbox`. The rule and command belong to `documentation-system.md`, so update them there.
8. **Docs site.** Link this note from `mkdocs.yml` (Research) and from `docs/map.md` (Spikes) when the findings are applied. This spike only writes under `spikes/cloud-env/` and this note.
