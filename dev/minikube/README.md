# Spectio on minikube

The Spectio of this checkout (wheels built from `packages/`, web screens included) in a local minikube cluster:
the `minimal` profile of `docs/specs/architecture-plugins-and-packaging.md` §7.4, one service with SQLite on a
volume. It is a development and demonstration setup, not the Kubernetes deployment of §7.5.

## Prerequisites

- A running Docker daemon (colima, Docker Desktop, Linux Docker), `minikube` (docker driver) and `kubectl`.
- To build the wheels (done once; `up.sh --rebuild` repeats it): `uv`, `npm`, Java 21 and Nextflow (the `spectio`
  wheel carries nf-spectio, which is compiled against Nextflow; pins in `dev/versions.env`).
- About 5 GiB of free memory in the Docker VM (minikube gets 4 GiB by default: `MINIKUBE_MEMORY`, `MINIKUBE_CPUS`).
- Colima, or any Docker VM that also hosts another cluster (kind): raise the inotify limit, or kube-proxy dies with
  "too many open files" and the cluster never gets ready (it is 128 by default):
  `colima ssh -- sudo sysctl -w fs.inotify.max_user_instances=1024`. `up.sh` warns when it is below 512.

## Up

```bash
bash dev/minikube/up.sh
```

It starts minikube in its own profile `spectio` (kubectl context `spectio`), builds the wheels into
`dev/minikube/.build/` (git-ignored), builds the image `spectio:dev` with the Docker daemon inside minikube
(`Dockerfile`, target `engines`: Java 21, Nextflow and Snakemake at the pins of `dev/versions.env`; `TARGET=minimal`
leaves the engines out), applies `spectio.yaml` and waits until the Deployment is ready. A first run downloads
the minikube base image (1.7 GB) and takes several minutes; a repeat takes about one.

What it creates, in the namespace `spectio`: PVC `spectio-data` (data directory and SQLite database), PVC
`spectio-runs` (the runs root), Deployment `spectio` (one replica, strategy `Recreate`, user 10001, no service
account token, all capabilities dropped; an init container only chowns the volumes) and Service `spectio`.
The first start runs `spectio init --local` in the pod; the configuration is kept on the volume.

## Open the UI

The server listens on `127.0.0.1` of the pod only (dev-env §15.3 request 1: there is no `--host`), so the way in
is `kubectl port-forward`, whose connection is made inside the pod:

```bash
kubectl --context spectio -n spectio port-forward svc/spectio 8080:8080
```

Every URL answers `401` until you have a session, `/` included. Ask the server for a single-use link (valid 15
minutes) and open it in the browser; the pod log never contains one, because the container runs `serve --pane`:

```bash
kubectl --context spectio -n spectio exec deploy/spectio -c spectio -- spectio login --print-link
```

The link names `http://127.0.0.1:<port>`: use the forwarded port `8080` as the command prints it.

## Check it

```bash
bash dev/minikube/smoke.sh                # both engines
bash dev/minikube/smoke.sh nextflow       # or snakemake
```

It port-forwards and requests `/` and `/api/v1/me` (expect 401: the server answers and wants a session), then runs
`tests/slurm/e2e_client.py` inside the pod, as `tests/local/e2e.sh` does on a laptop. The client signs in with a
link it asks `spectio login --print-link --json` for (never printed), launches the synthetic pipeline `happy` with
`POST /api/v1/runs` on the `local` environment, polls until the run ends and compares its tasks to the golden
file. The output ends with `RESULT minikube-<engine> pass|fail`.

## Logs and state

```bash
kubectl --context spectio -n spectio logs deploy/spectio
kubectl --context spectio -n spectio exec deploy/spectio -c spectio -- spectio doctor
```

Runs live under `/var/lib/spectio-runs/<run id>/` in the pod (PVC `spectio-runs`).

## Teardown

```bash
bash dev/minikube/up.sh down      # minikube delete -p spectio: the cluster, its volumes and the image
```

`kubectl --context spectio delete namespace spectio` removes only Spectio and its data.

## Known limits

- **Runs execute inside the server pod** (`executor = local`). The Kubernetes runner of
  `docs/specs/schedulers-and-monitoring.md` §4 is not built: no run creates a Job or a Pod, and there is no
  Kueue here. For that, see the kind profiles of `dev/k8s/cluster.sh`, which test the engines' own Kubernetes
  executors, not Spectio.
- **Nothing outside the pod can reach the server except through `kubectl port-forward`**: it binds `127.0.0.1`.
  No Ingress, no `NodePort`, no TLS.
- One replica, SQLite, one volume. Deleting the Deployment's pod is safe (the volumes stay); deleting the PVCs or
  the minikube profile deletes users, runs and results.
- The image is built for the architecture of the Docker VM (arm64 on Apple silicon). Snakemake's lock file
  `dev/snakemake.lock.txt` is hash-locked for linux x86_64 only, so on arm64 the same pinned versions are resolved
  without hashes (`Dockerfile`, target `engines`). The Debian packages (Java, `procps`, `tmux`) are not pinned.
- The image is not an official one: §7.4 builds it from the *published* wheel; this one is built from the
  checkout, tagged `spectio:dev`, and never pushed.
