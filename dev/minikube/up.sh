#!/usr/bin/env bash
# Spectio, as it is in this checkout, on a local minikube (dev/minikube/README.md). Development only.
#
#   bash dev/minikube/up.sh            start minikube, build the image from the wheels, deploy, wait for ready
#   bash dev/minikube/up.sh --rebuild  rebuild the wheels (web screens included) first, whatever their state
#   bash dev/minikube/up.sh down       delete the minikube profile (the data volumes go with it)
#
# Needs a running Docker (colima, Docker Desktop), minikube and kubectl; to build the wheels also uv, Node
# (npm) and, for the nf-spectio bridge in the spectio wheel, Java 21 and Nextflow (dev/versions.env pins).
# Nothing is installed: the wheels and the staged build context live in dev/minikube/.build (git-ignored).
# The wheels are rebuilt when .build/wheels.sha differs from the checkout's (HEAD plus uncommitted changes under
# packages/, web/, engine-bridges/, uv.lock).
# Environment: NEXTFLOW (path of the -dist Nextflow that compiles nf-spectio; default: nextflow on the PATH),
# MINIKUBE_PROFILE (spectio; `down` accepts only spectio or spectio-*, FORCE=1 overrides),
# MINIKUBE_CPUS (4), MINIKUBE_MEMORY (4096, MiB), TARGET (engines|minimal). Bash 3.2 (macOS) safe.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
build=$here/.build
profile=${MINIKUBE_PROFILE:-spectio}
target=${TARGET:-engines}
# shellcheck source=dev/versions.env
. "$repo/dev/versions.env"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die() { echo "up.sh: $*" >&2; exit 1; }

case "${1:-}" in
  down)
    case "$profile" in
      spectio | spectio-*) ;;
      *) [ "${FORCE:-}" = 1 ] || die "refusing to delete profile '$profile': only spectio or spectio-* (FORCE=1 overrides)" ;;
    esac
    echo "up.sh: deleting minikube profile '$profile': its node container, the volumes of the Spectio data and runs, and its kubectl context" >&2
    minikube delete -p "$profile"
    exit ;;
  "" | --rebuild) ;;
  *) sed -n '2,6p' "$0"; exit 2 ;;
esac

for cmd in docker minikube kubectl; do command -v "$cmd" >/dev/null || die "$cmd is not on PATH"; done
docker info >/dev/null 2>&1 || die "the Docker daemon is not running (colima start)"

# Two clusters on one Docker VM exhaust inotify instances (default 128): kube-proxy then dies with "too many open
# files" and the cluster never gets ready. Colima: `colima ssh -- sudo sysctl -w fs.inotify.max_user_instances=1024`.
inotify=$(docker run --rm "$BUSYBOX_IMAGE" cat /proc/sys/fs/inotify/max_user_instances 2>/dev/null || echo 0)
[ "$inotify" -ge 512 ] || echo "up.sh: warning: fs.inotify.max_user_instances is $inotify in the Docker VM; raise it to 1024 (see dev/minikube/README.md)" >&2

# 1. wheels: the web screens, then the three wheels (architecture-plugins-and-packaging.md §7.3)
state=$( (cd "$repo" && git rev-parse HEAD && git status --porcelain=v1 -- packages web engine-bridges uv.lock &&
  git diff HEAD -- packages web engine-bridges uv.lock) | shasum -a 256 | cut -c1-64)
if [ "${1:-}" = --rebuild ] || [ "$(cat "$build/wheels.sha" 2>/dev/null || true)" != "$state" ] ||
  ! ls "$build"/wheels/spectio_server-*.whl >/dev/null 2>&1; then
  for cmd in uv npm java; do command -v "$cmd" >/dev/null || die "$cmd is needed to build the wheels"; done
  command -v "${NEXTFLOW:-nextflow}" >/dev/null || die "nextflow is needed to build nf-spectio into the spectio wheel"
  log "web screens"
  npm --prefix "$repo/web" ci --ignore-scripts --no-audit --no-fund >/dev/null
  (cd "$repo/web" && ./node_modules/.bin/vite build --configLoader runner >/dev/null)
  log "wheels"
  rm -rf "$build/wheels" "$build/wheels.sha"
  mkdir -p "$build/wheels"
  for p in spectio-sdk spectio spectio-server; do
    uv build "$repo/packages/$p" --wheel --out-dir "$build/wheels" --quiet
  done
  # the hook that adds the bridges only warns when it cannot build them (`--quiet` hides it): a wheel without them
  # gives an image whose runs all fail ("_bridges/... is missing"), so check, and do not record the state
  listing=$(unzip -l "$build"/wheels/spectio-[0-9]*.whl)
  case "$listing" in
    *spectio/_bridges/nf-spectio-*) ;;
    *) rm -rf "$build/wheels"
       die "the spectio wheel carries no engine bridges: nf-spectio is compiled with the jar of the -dist Nextflow of dev/versions.env: put it on the PATH or set NEXTFLOW to its path (a conda launcher is not enough)" ;;
  esac
  echo "$state" >"$build/wheels.sha"
fi
# the hashed third-party dependencies of the wheels (the workspace itself is left out), and the Snakemake locks
(cd "$repo" && uv export --frozen --no-dev --no-emit-project --no-emit-workspace --no-header >"$build/requirements.txt")
cp "$repo/dev/snakemake.lock.txt" "$repo/dev/snakemake.lock.arm64.txt" "$build/"
ls "$build/wheels"/*.whl

# 2. minikube on the docker driver, in its own profile (and kubectl context) so that other clusters stay as they are
if ! minikube status -p "$profile" >/dev/null 2>&1; then
  log "minikube start (profile $profile, Kubernetes $MINIKUBE_KUBERNETES_VERSION)"
  minikube start -p "$profile" --driver=docker --cpus "${MINIKUBE_CPUS:-4}" --memory "${MINIKUBE_MEMORY:-4096}" \
    --kubernetes-version="$MINIKUBE_KUBERNETES_VERSION" --wait=all
fi

# 3. the image, built by the Docker daemon inside minikube: no registry, the manifests use imagePullPolicy: Never
log "image spectio:dev (target $target)"
eval "$(minikube -p "$profile" docker-env)"
docker build --target "$target" -t spectio:dev -f "$here/Dockerfile" \
  --build-arg "PYTHON_VERSION=$PYTHON_VERSION" \
  --build-arg "NEXTFLOW_VERSION=$NEXTFLOW_VERSION" --build-arg "NEXTFLOW_SHA256=$NEXTFLOW_SHA256" \
  --build-arg "SNAKEMAKE_VERSION=$SNAKEMAKE_VERSION" \
  --build-arg "SNAKEMAKE_EXECUTOR_SLURM_VERSION=$SNAKEMAKE_EXECUTOR_SLURM_VERSION" \
  "$build"

# 4. deploy and wait (a changed image under the same tag needs a restart)
log "deploy"
existed=0
kubectl --context "$profile" -n spectio get deployment/spectio >/dev/null 2>&1 && existed=1
kubectl --context "$profile" apply -f "$here/spectio.yaml"
[ "$existed" = 0 ] || kubectl --context "$profile" -n spectio rollout restart deployment/spectio >/dev/null
kubectl --context "$profile" -n spectio rollout status deployment/spectio --timeout=300s
log "ready: kubectl --context $profile -n spectio port-forward svc/spectio 8080:8080   (dev/minikube/README.md)"
