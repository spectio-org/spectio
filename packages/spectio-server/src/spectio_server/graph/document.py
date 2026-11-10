"""The GraphDocument (version 1) of api §5.10, built from plain inputs, with no I/O.

Node ids are the names the store keeps (`tasks.process_or_rule`), so a node joins
`/processes` and `/tasks?process=` with no mapping. Every text that comes from a pipeline (names,
conditions, file paths) is data: the screens render it as text only.
"""

import re
from typing import Any

VERSION = 1
MAX_NODES = 2000  # the bounds of the `onFlowBegin` DAG (graph contract), also for a metro map
MAX_EDGES = 20000
_PARAM = re.compile(r"\bparams\.([A-Za-z_]\w*)")
_COPY = re.compile(r"_\$\$_\d+$")  # BioFlow-Insight's call index: `FETCHNGS_$$_1`


def subworkflows(name: str) -> list[str]:
    """The group ids of a Nextflow qualified name, outermost first: `A:B:P` → `sub:A`, `sub:A:B`."""
    parts = name.split(":")[:-1]
    return ["sub:" + ":".join(parts[: n + 1]) for n in range(len(parts))]


def params_read(code: str | None) -> list[str]:
    """The `params.<name>` a node's code reads, each once, in order."""
    return list(dict.fromkeys(_PARAM.findall(code or "")))


def rulegraph_edges(graphs: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """The links of every rule graph of the run (`sourcerule` → `targetrule`), each once."""
    found: dict[tuple[str, str], None] = {}
    for graph in graphs:
        links = graph.get("links")
        for link in links if isinstance(links, list) else []:
            if not isinstance(link, dict):
                continue
            source, target = link.get("sourcerule"), link.get("targetrule")
            if isinstance(source, str) and isinstance(target, str) and source != target:
                found[(source, target)] = None
    return list(found)[:MAX_EDGES]


def nf_dag(payload: Any) -> tuple[list[str], list[tuple[str, str]]] | None:
    """The processes and edges of `onFlowBegin`'s `dag`, or None when absent or truncated."""
    dag = payload.get("dag") if isinstance(payload, dict) else None
    if not isinstance(dag, dict) or dag.get("truncated"):
        return None
    processes = [p for p in dag.get("processes") or [] if isinstance(p, str)][:MAX_NODES]
    known = set(processes)
    edges: dict[tuple[str, str], None] = {}
    for edge in dag.get("edges") or []:
        if isinstance(edge, list | tuple) and len(edge) == 2:
            a, b = edge
            if a in known and b in known and a != b:
                edges[(a, b)] = None
    return processes, list(edges)[:MAX_EDGES]


def _metro_name(node_id: str) -> str:
    """`A_$$_1.B_$$_1.PROC` → `A:B:PROC`; `.ALIGN` → `ALIGN`."""
    return ":".join(_COPY.sub("", p) for p in node_id.split(".") if p)


def from_metro(metro: dict[str, Any]) -> dict[str, Any]:
    """BioFlow-Insight's `metro_map.json` as {nodes: {qualified name: info}, edges, groups}."""
    nodes: dict[str, dict[str, Any]] = {}
    ids: dict[str, str] = {}
    for node in (metro.get("nodes") or [])[:MAX_NODES]:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            continue
        name = _metro_name(node["id"])
        ids[node["id"]] = name
        ref = node.get("file_ref")
        source = ref.strip("()") if isinstance(ref, str) and ref.strip("()") else None
        position = node.get("position")
        layout = None
        if isinstance(position, dict):
            try:
                layout = {"x": float(position["x"]), "y": float(position["y"])}
            except (KeyError, TypeError, ValueError):
                layout = None
        condition = node.get("condition")
        nodes[name] = {
            "source": {"file": source, "line": None} if source else None,
            "condition": condition if isinstance(condition, str) else None,
            "params": params_read(node.get("code") if isinstance(node.get("code"), str) else None),
            "layout": layout,
        }
    # Static edges, not a DAG: a channel reassigned after `.mix()` links the mixed processes
    # both ways (nf-core/fetchngs, spike #160); each edge keeps its `condition`.
    edges: dict[tuple[str, str], str | None] = {}
    for edge in metro.get("edges") or []:
        if isinstance(edge, dict) and edge.get("A") in ids and edge.get("B") in ids:
            a, b = ids[edge["A"]], ids[edge["B"]]
            condition = edge.get("condition")
            if a != b:
                edges[(a, b)] = condition if isinstance(condition, str) else None
    groups: dict[str, str | None] = {}
    subs = metro.get("subworkflows")
    for key, sub in (subs if isinstance(subs, dict) else {}).items():
        if isinstance(key, str):
            condition = sub.get("condition") if isinstance(sub, dict) else None
            groups["sub:" + _metro_name(key)] = condition if isinstance(condition, str) else None
    kept = list(edges)[:MAX_EDGES]
    return {
        "nodes": nodes,
        "edges": kept,
        "edge_conditions": {e: edges[e] for e in kept if edges[e]},
        "groups": groups,
    }


def build(
    *,
    engine: str,
    producer: str,
    complete: bool,
    nodes: list[dict[str, Any]],
    edges: list[tuple[str, str]],
    stages: list[dict[str, Any]],
    file_groups: dict[str, str] | None = None,
    conditions: dict[str, str | None] | None = None,
    edge_conditions: dict[tuple[str, str], str] | None = None,
    estimate: bool = False,
) -> dict[str, Any]:
    """The document. Each of `nodes` has at least `id`; `stage_id`, `kind`, `source`,
    `condition`, `params` and the overlay keys are kept as given. Nextflow subworkflow groups
    come from the qualified names (their `conditions` from a metro map); `file_groups` maps a
    Snakemake rule to its rule file, a group when the rules come from more than one file.
    `estimate`: the edges come from a static analysis, and may hold cycles or miss runtime
    links. Edges are never assumed to form a DAG."""
    stage_ids = {s["id"] for s in stages}
    groups: list[dict[str, Any]] = [
        {"id": f"stage:{s['id']}", "kind": "stage", "name": s.get("name") or s["id"]}
        | {"parent": None, "condition": None}
        for s in stages
    ]
    subs: dict[str, None] = {}
    out_nodes = []
    by_file = file_groups if file_groups and len(set(file_groups.values())) > 1 else {}
    for node in nodes[:MAX_NODES]:
        name = node["id"]
        sub_ids = subworkflows(name) if engine == "nextflow" else []
        if name in by_file:
            sub_ids = ["file:" + by_file[name]]
        subs.update(dict.fromkeys(sub_ids))
        stage_id = node.get("stage_id")
        out_nodes.append(
            {"source": None, "condition": None, "params": []}
            | node
            | {
                "name": name.rsplit(":", 1)[-1],
                "kind": node.get("kind") or ("rule" if engine == "snakemake" else "process"),
                "stage_id": stage_id if stage_id in stage_ids else None,
                "subworkflow": sub_ids[-1] if sub_ids else None,
            }
        )
    for gid in subs:
        if gid.startswith("file:"):
            file_path = gid[5:]
            groups.append(
                {"id": gid, "kind": "subworkflow", "name": file_path.rsplit("/", 1)[-1]}
                | {"parent": None, "condition": None}
            )
            continue
        path = gid[4:].split(":")
        parent = "sub:" + ":".join(path[:-1]) if len(path) > 1 else None
        groups.append(
            {
                "id": gid,
                "kind": "subworkflow",
                "name": path[-1],
                "parent": parent,
                "condition": (conditions or {}).get(gid),
            }
        )
    ids = {n["id"] for n in out_nodes}
    return {
        "version": VERSION,
        "engine": engine,
        "producer": producer,
        "complete": complete,
        "estimate": estimate,
        "groups": groups,
        "nodes": out_nodes,
        "edges": [
            {"source": a, "target": b, "condition": (edge_conditions or {}).get((a, b))}
            for a, b in edges
            if a in ids and b in ids
        ],
    }
