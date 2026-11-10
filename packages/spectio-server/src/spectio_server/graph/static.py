"""The graph of a pipeline before any run, for the Launch form (`GET /workflows:graph`).

The server never runs pipeline code to draw it: Snakemake's `--rulegraph` evaluates the
Snakefile (Python), so the Snakemake graph is the rules of the rule files (`detect_smk`), one
group per file, with no edges until a run sends its rule graph. Nextflow's comes from
BioFlow-Insight when it is installed (`bioflow`, static analysis), else from the `process`
definitions of the `.nf` files, with no edges. Files are read with `read_confined`'s checks.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any

from spectio_server.graph import bioflow, document
from spectio_server.stages.assign import Overlap, StageDef, assign
from spectio_server.stages.detect_nf import detect_nextflow
from spectio_server.stages.detect_smk import (
    MAX_FILE_BYTES,
    Unsafe,
    detect_snakemake,
    read_confined,
    rule_files,
)

log = logging.getLogger(__name__)

MAX_NF_FILES = 500
_PROCESS = re.compile(r"^\s*process\s+([A-Za-z_]\w*)\s*\{", re.MULTILINE)


def _stage_of(stages: list[StageDef], name: str) -> str | None:
    try:
        return assign(stages, name)
    except Overlap:
        return None


def _stages(stages: list[StageDef]) -> list[dict[str, Any]]:
    return [{"id": s.id, "name": s.name} for s in stages]


def snakemake_graph(root: Path, entry: str) -> dict[str, Any]:
    main = root / entry
    try:
        files = rule_files(main)
    except Unsafe as exc:
        log.warning("%s: no rules read: %s", main, exc)
        files = []
    stages = detect_snakemake(main, None)
    real_root = Path(os.path.realpath(root))
    by_file: dict[str, str] = {}
    nodes: list[dict[str, Any]] = []
    for f in files:
        rel = (
            str(f.path.relative_to(real_root)) if f.path.is_relative_to(real_root) else f.path.name
        )
        for rule in dict.fromkeys(f.rules):
            if rule in by_file:
                continue
            by_file[rule] = rel
            nodes.append(
                {
                    "id": rule,
                    "kind": "checkpoint" if rule in f.checkpoints else "rule",
                    "stage_id": _stage_of(stages, rule),
                    "source": {"file": rel, "line": None},
                }
            )
    return document.build(
        engine="snakemake",
        producer="stages-only",
        complete=False,
        nodes=nodes,
        edges=[],
        stages=_stages(stages),
        file_groups=by_file,
    )


def _nf_processes(root: Path) -> list[tuple[str, str]]:
    """(process name, file) of every `process X {` in the pipeline's `.nf` files, bounded."""
    real_root = Path(os.path.realpath(root))
    found: dict[str, str] = {}
    seen = 0
    for dirpath, dirnames, filenames in os.walk(real_root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d != "work")
        for name in sorted(filenames):
            if not name.endswith(".nf"):
                continue
            seen += 1
            if seen > MAX_NF_FILES:
                return list(found.items())
            path = Path(dirpath) / name
            try:
                text = read_confined(real_root, path, MAX_FILE_BYTES)
            except Unsafe:
                continue
            for m in _PROCESS.finditer(text or ""):
                found.setdefault(m.group(1), str(path.relative_to(real_root)))
    return list(found.items())


def nextflow_graph(root: Path, manifest_name: str | None) -> dict[str, Any]:
    metro = bioflow.metro_map(root / "main.nf")
    if metro is not None:
        mapped = document.from_metro(metro)
        names = list(mapped["nodes"])
        stages = detect_nextflow(names, manifest_name, {})
        nodes = [
            {
                "id": name,
                "stage_id": _stage_of(stages, name),
                **{k: v for k, v in info.items() if v is not None},
            }
            for name, info in mapped["nodes"].items()
        ]
        return document.build(
            engine="nextflow",
            producer="bioflow-insight",
            complete=False,  # static edges: an estimate, cycles included (spike #160)
            estimate=True,
            nodes=nodes,
            edges=mapped["edges"],
            stages=_stages(stages),
            conditions=mapped["groups"],
            edge_conditions=mapped["edge_conditions"],
        )
    nodes = [
        {"id": name, "source": {"file": file, "line": None}} for name, file in _nf_processes(root)
    ]
    return document.build(
        engine="nextflow", producer="stages-only", complete=False, nodes=nodes, edges=[], stages=[]
    )
