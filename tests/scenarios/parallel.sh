#!/usr/bin/env bash
# The isolation proof of docs/specs/dev-environment-and-testing.md §5: three scenarios up at the same time with
# dev/scenario.py, two on slurm-mini (the same sind cluster name, "mini", in realms spx-1 and spx-2) and one on
# k8s-mini (kind cluster spx-3), plus a local one (spx-4). Each cluster runs a job that writes into its own data
# directory; then `down` in parallel, and nothing may be left: containers, networks and volumes are compared with
# the state before `up`, and no sind realm or kind cluster named spx-* may remain.
# Needs Docker on cgroup v2 (not a Claude Code cloud session), dev/bootstrap.sh's tools and Java (for slurm).
#
#   bash tests/scenarios/parallel.sh
set -euo pipefail
# shellcheck source=dev/lib.sh
. "$(dirname "$0")/../../dev/lib.sh"
cd "$SPECTIO_REPO"
out=$(mktemp -d)
declare -A SCENARIO=([1]=happy-slurm-mini [2]=happy-slurm-mini [3]=happy-k8s-mini [4]=happy-local)
die() { echo "::error::$*"; exit 1; }
docker_state() { # every container, network and volume, by name
  { docker ps -a --format 'container {{.Names}}'; docker network ls --format 'network {{.Name}}'
    docker volume ls --format 'volume {{.Name}}'; } | sort
}
docker_state >"$out/before"

echo "===== up, in parallel"
for id in "${!SCENARIO[@]}"; do
  python3 dev/scenario.py up "${SCENARIO[$id]}" --id "$id" >"$out/$id.json" 2>"$out/$id.log" &
  echo "$!" >"$out/$id.pid"
done
t=$SECONDS failed=0
for id in "${!SCENARIO[@]}"; do
  wait "$(cat "$out/$id.pid")" || { echo "::error::up ${SCENARIO[$id]} --id $id failed"; failed=1; }
done
echo "TIMING up (parallel) $((SECONDS - t)) s"
for id in "${!SCENARIO[@]}"; do
  echo "::group::up $id log"; cat "$out/$id.log"; echo "::endgroup::"
done
[ "$failed" = 0 ] || die "an up failed"

echo "===== no collision"
jq -s 'map({id, name, data_dir, ports, urls, credentials, sind, kind})' "$out"/[0-9].json | tee "$out/all.json"
jq -e 'length == 4 and ([.[].name] | unique | length) == 4 and ([.[].data_dir] | unique | length) == 4
       and ([.[].ports[0]] | unique | length) == 4' "$out/all.json" >/dev/null || die "two scenarios share a name"
docker network ls --format '{{.Name}}' | grep '^spx-' | sort | tee "$out/networks"
for n in spx-1 spx-2 spx-3 spx-4; do grep -qx "$n" "$out/networks" || die "no network $n"; done
sind get realms | tee "$out/realms"
for id in 1 2; do
  grep -q "^spx-$id " "$out/realms" || die "no sind realm spx-$id"
  sind --realm "spx-$id" get clusters | grep -qw mini || die "realm spx-$id has no cluster mini"
done
[ "$(kind get clusters)" = spx-3 ] || die "kind clusters: $(kind get clusters | tr '\n' ' ')"
# Each sind cluster runs a job as spx that writes its realm into its own data directory, and only there.
for id in 1 2; do
  data=$SPECTIO_REPO/.scenarios/$id
  # shellcheck disable=SC2016  # expanded by the inner bash
  sind --realm "spx-$id" exec mini -u spx -- bash -c 'cd "$0" && sbatch --wait -o hello.out --wrap "echo $1 \$(hostname)"' \
    "$data" "spx-$id"
  grep -q "^spx-$id " "$data/hello.out" || die "spx-$id: hello.out says $(cat "$data/hello.out" 2>&1)"
  echo "spx-$id: $(cat "$data/hello.out")"
done
# The kind cluster answers on its port in its range, with its own kubeconfig, on its own network.
kc=$SPECTIO_REPO/.scenarios/3/kubeconfig
[ "$(KUBECONFIG=$kc kubectl config view -o jsonpath='{.clusters[0].cluster.server}')" = https://127.0.0.1:20301 ] ||
  die "spx-3: API server not on 20301"
KUBECONFIG=$kc kubectl wait --for=condition=Ready node --all --timeout=120s
[ "$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' spx-3-control-plane)" = "spx-3 " ] ||
  die "spx-3-control-plane is not on network spx-3 alone"
echo "--- memory per scenario (docker stats, MiB)"
docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' | sort | tee "$out/stats"
python3 dev/scenario.py list

echo "===== down, in parallel"
for id in "${!SCENARIO[@]}"; do python3 dev/scenario.py down "$id" & echo "$!" >"$out/$id.pid"; done
for id in "${!SCENARIO[@]}"; do wait "$(cat "$out/$id.pid")" || die "down $id failed"; done

echo "===== nothing left"
docker_state >"$out/after"
diff "$out/before" "$out/after" || die "down left Docker objects behind (diff above: > is new)"
! sind get realms | grep '^spx-' || die "a sind realm spx-* is left"
! kind get clusters 2>/dev/null | grep '^spx-' || die "a kind cluster spx-* is left"
for id in "${!SCENARIO[@]}"; do [ ! -e ".scenarios/$id" ] || die ".scenarios/$id is left"; done
echo "RESULT parallel: 4 scenarios up in parallel (2 sind realms with cluster mini, 1 kind, 1 local), no collision, nothing left after down"
