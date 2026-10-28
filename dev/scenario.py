#!/usr/bin/env python3
"""Isolated scenario environments (docs/specs/dev-environment-and-testing.md §5).

  python3 dev/scenario.py up <scenario> [--id N]   create the environment of tests/scenarios/<scenario>.yaml
                                                   and print it as JSON (N: 1-99, default the lowest free one)
  python3 dev/scenario.py down <id>                remove everything `up` created for that id
  python3 dev/scenario.py list                     the scenario files, and the environments that are up

Per id N, `up` creates: the data directory .scenarios/N/, the Docker network spx-N, and, after the scenario's
scheduler, the sind realm spx-N (dev/slurm/cluster.sh, tools bootstrapped into the data directory) or the kind
cluster spx-N on network spx-N with its API on port 20000+100*N+1 and its kubeconfig in the data directory
(dev/k8s/cluster.sh). The Compose project spx-N and its ports 20000+100*N+k are reserved and reported, not
started: there is no product to start yet. Stdlib only. sind and kind need Docker on cgroup v2 (not a
Claude Code cloud session): the proof runs in CI (.github/workflows/scenarios.yml).
"""
import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCENARIOS = REPO / "tests" / "scenarios"
STATE = REPO / ".scenarios"
# scheduler -> (layer, cluster.sh profile, MiB of free memory needed before `up`). The memory figures are
# estimates of what the running containers use, not their limits [to be validated: measured by scenarios.yml].
SCHEDULERS = {
    "local": (None, None, 256),
    "slurm-mini": ("slurm", "mini", 2048),
    "slurm-site": ("slurm", "site", 4096),
    "slurm-rest": ("slurm", "rest", 4608),
    "k8s-mini": ("k8s", "mini", 2048),
    "k8s-kueue": ("k8s", "kueue", 4096),
}
FIELDS = {"deployment", "scheduler", "engine", "fixture", "params", "gate", "expect"}
DEPLOYMENTS = {"bundle", "compose"}
MAX_ID = 99


def names(n):
    """Everything an id owns: one name for network, Compose project, realm and kind cluster; ports; paths."""
    if not 1 <= n <= MAX_ID:
        raise ValueError(f"scenario id must be 1-{MAX_ID}: {n}")
    base = 20000 + 100 * n
    return {
        "id": n,
        "name": f"spx-{n}",
        "data_dir": str(STATE / str(n)),
        "ports": [base, base + 99],
        "port": {"spectio": base, "kube_api": base + 1},
    }


def _scalar(text, where):
    if not text or text[0] in "{&*!|>'\"" or ": " in text:
        raise ValueError(f"{where}: unsupported YAML: {text!r}")
    return text


def parse_yaml(text, where="<yaml>"):
    """The YAML subset of tests/scenarios/*.yaml: `key: scalar`, `key: [a, b]`, `key:` then `  - item` lines,
    and `#` comments. Anything else is an error, so a file never means something other than it reads."""
    out, block = {}, None
    for i, raw in enumerate(text.splitlines(), 1):
        line, at = re.sub(r"(^|\s)#.*$", "", raw).rstrip(), f"{where}:{i}"
        if not line:
            continue
        if block and line.startswith("  - "):
            out[block].append(_scalar(line[4:].strip(), at))
            continue
        m = re.fullmatch(r"([a-z_]+):(?: (.*))?", line)
        if not m:
            raise ValueError(f"{at}: unsupported YAML: {raw!r}")
        key, value = m.group(1), (m.group(2) or "").strip()
        if key in out:
            raise ValueError(f"{at}: duplicate key {key}")
        block = None if value else key
        if not value:
            out[key] = []
        elif value.startswith("[") and value.endswith("]"):
            out[key] = [_scalar(v.strip(), at) for v in value[1:-1].split(",") if v.strip()]
        else:
            out[key] = _scalar(value, at)
    return out


def load(name):
    """tests/scenarios/<name>.yaml, checked: exactly the §5 fields, a known scheduler and deployment."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise ValueError(f"bad scenario name: {name!r}")
    path = SCENARIOS / f"{name}.yaml"
    if not path.is_file():
        raise ValueError(f"no scenario {name}: tests/scenarios/{name}.yaml does not exist")
    s = parse_yaml(path.read_text(), str(path.relative_to(REPO)))
    return check(s, name)


def check(s, name):
    if set(s) != FIELDS:
        raise ValueError(f"{name}: fields must be {sorted(FIELDS)}; missing {sorted(FIELDS - set(s))}, "
                         f"unknown {sorted(set(s) - FIELDS)}")
    if s["scheduler"] not in SCHEDULERS:
        raise ValueError(f"{name}: unknown scheduler {s['scheduler']!r}; one of {sorted(SCHEDULERS)}")
    if s["deployment"] not in DEPLOYMENTS:
        raise ValueError(f"{name}: unknown deployment {s['deployment']!r}; one of {sorted(DEPLOYMENTS)}")
    return dict(s, name=name)


def available_mib():
    with open("/proc/meminfo") as f:
        return next(int(line.split()[1]) // 1024 for line in f if line.startswith("MemAvailable:"))


def port_free(port):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def run(cmd, env=None, check=True):
    """A command whose output goes to stderr, so that stdout stays the JSON."""
    print("+ " + " ".join(cmd), file=sys.stderr, flush=True)
    return subprocess.run(cmd, env=env, stdout=sys.stderr, check=check).returncode


def claim(n):
    """Create .scenarios/<n>/ (atomic: two parallel `up` never get the same id); n=None takes the lowest free."""
    STATE.mkdir(exist_ok=True)
    for i in [n] if n else range(1, MAX_ID + 1):
        try:
            os.mkdir(STATE / str(names(i)["id"]))
            return i
        except FileExistsError:
            continue
    raise SystemExit(f"scenario id {n} is in use (.scenarios/{n}/ exists)" if n else "no free scenario id")


def layer_env(env_ids, layer):
    """The environment cluster.sh needs to put this id's cluster in this id's names and paths."""
    data, name = env_ids["data_dir"], env_ids["name"]
    env = dict(os.environ)
    if layer == "slurm":  # dev/slurm/cluster.sh header: the tools live in the data directory every node mounts
        env.update(SLURM_DATA=data, SIND_REALM=name, SPECTIO_HOME=f"{data}/tools", SPECTIO_BIN=f"{data}/tools/bin",
                   UV_PYTHON_INSTALL_DIR=f"{data}/tools/python", PATH=f"{data}/tools/bin:{env['PATH']}")
    elif layer == "k8s":
        env.update(CLUSTER=name, KUBECONFIG=f"{data}/kubeconfig", KIND_EXPERIMENTAL_DOCKER_NETWORK=name,
                   KIND_API_PORT=str(env_ids["port"]["kube_api"]))
    return env


def up(scenario, n):
    s = load(scenario)
    layer, profile, need = SCHEDULERS[s["scheduler"]]
    free = available_mib()
    if free < need:
        raise SystemExit(f"{s['scheduler']} needs about {need} MiB free, {free} MiB available: `down` another scenario")
    n = claim(n)
    ids = names(n)
    taken = [p for p in range(ids["ports"][0], ids["ports"][1] + 1) if not port_free(p)]
    if taken:
        shutil.rmtree(ids["data_dir"])
        raise SystemExit(f"ports {taken} of id {n} are in use: pick another --id")
    env = layer_env(ids, layer)
    state = dict(ids, scenario=s, compose={"project": ids["name"], "started": False},
                 network=ids["name"], urls={}, credentials={})
    (Path(ids["data_dir"]) / "scenario.json").write_text(json.dumps(state, indent=2) + "\n")
    run(["docker", "network", "create", "--label", f"spectio.scenario={n}", ids["name"]])
    if layer == "slurm":
        run(["bash", str(REPO / "dev/bootstrap.sh")], env)
        run(["bash", str(REPO / "dev/slurm/cluster.sh"), "up", profile], env)
        state["sind"] = {"realm": ids["name"], "cluster": profile,
                         "exec": f"sind --realm {ids['name']} exec {profile} -u spx -- <command>"}
    elif layer == "k8s":
        run(["bash", str(REPO / "dev/k8s/cluster.sh"), "up", profile], env)
        state["kind"] = {"cluster": ids["name"], "context": f"kind-{ids['name']}"}
        state["urls"]["kube_api"] = f"https://127.0.0.1:{ids['port']['kube_api']}"
        state["credentials"]["kubeconfig"] = env["KUBECONFIG"]
    (Path(ids["data_dir"]) / "scenario.json").write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state, indent=2))


def down(n):
    """Idempotent, and needs no state: it removes whatever exists under the id's names."""
    ids = names(n)
    env = layer_env(ids, "slurm")  # PATH with the data directory's tools, where sind may be the only copy
    env["KUBECONFIG"] = f"{ids['data_dir']}/kubeconfig"
    failed = 0
    if shutil.which("sind", path=env["PATH"]) and ids["name"] in _first_column(["sind", "get", "realms"], env):
        failed |= run(["sind", "--realm", ids["name"], "delete", "realm"], env, check=False)
    if shutil.which("kind", path=env["PATH"]) and ids["name"] in _first_column(["kind", "get", "clusters"], env):
        failed |= run(["kind", "delete", "cluster", "--name", ids["name"]], env, check=False)
    if ids["name"] in _first_column(["docker", "network", "ls", "--format", "{{.Name}}"], env):
        failed |= run(["docker", "network", "rm", ids["name"]], check=False)
    if Path(ids["data_dir"]).exists():
        shutil.rmtree(ids["data_dir"])
    if failed:
        raise SystemExit(f"down {n}: a step failed, see above")
    print(json.dumps({"id": n, "down": True}))


def _first_column(cmd, env):
    out = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True).stdout
    return {line.split()[0] for line in out.splitlines() if line.strip()}


def list_():
    up_ = [json.loads(p.read_text()) for p in sorted(STATE.glob("[0-9]*/scenario.json"))] if STATE.exists() else []
    print(json.dumps({"scenarios": sorted(p.stem for p in SCENARIOS.glob("*.yaml")),
                      "up": [{k: e[k] for k in ("id", "name", "data_dir", "ports", "urls")} | {
                          "scenario": e["scenario"]["name"]} for e in up_]}, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("up")
    u.add_argument("scenario")
    u.add_argument("--id", type=int)
    sub.add_parser("down").add_argument("id", type=int)
    sub.add_parser("list")
    a = p.parse_args(argv)
    try:
        if a.cmd == "up":
            up(a.scenario, a.id)
        elif a.cmd == "down":
            down(a.id)
        else:
            list_()
    except ValueError as e:
        raise SystemExit(str(e))
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"{a.cmd} failed ({e}); `dev/scenario.py down <id>` removes what was created")


if __name__ == "__main__":
    main()
