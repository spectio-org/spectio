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

from spectio_server.graph import document
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
MAX_WALK_ENTRIES = 20000  # directories and files visited, all told (SEC-160-03)
MAX_WALK_DEPTH = 8
_SKIPPED_DIRS = {"work", "results", "conda", "envs", "node_modules"}  # outputs and environments
# `[ \t]` rather than `\s`: `^\s*` crosses newlines and goes quadratic on blank text (SEC-SRC-01)
_PROCESS = re.compile(r"^[ \t]*process[ \t]+([A-Za-z_]\w*)[ \t]*\{", re.MULTILINE)


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
    visited = 0
    for dirpath, dirnames, filenames in os.walk(real_root):
        visited += 1 + len(dirnames) + len(filenames)
        if visited > MAX_WALK_ENTRIES:
            break
        depth = len(Path(dirpath).relative_to(real_root).parts)
        dirnames[:] = (
            []
            if depth >= MAX_WALK_DEPTH
            else sorted(d for d in dirnames if not d.startswith(".") and d not in _SKIPPED_DIRS)
        )
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


def nextflow_graph(
    root: Path, manifest_name: str | None, metro: dict[str, Any] | None
) -> dict[str, Any]:
    """`metro`: BioFlow-Insight's map (`bioflow.metro_map`), run by the caller outside the file
    pool, whose reads time out sooner than the tool."""
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
    found = _nf_processes(root)
    stages = detect_nextflow([name for name, _ in found], manifest_name, {})
    nodes = [
        {"id": name, "stage_id": _stage_of(stages, name), "source": {"file": file, "line": None}}
        for name, file in found
    ]
    return document.build(
        engine="nextflow",
        producer="stages-only",
        complete=False,
        nodes=nodes,
        edges=[],
        stages=_stages(stages),
    )


MAX_CODE_LINES = 300
_NAME = re.compile(r"[A-Za-z_]\w*")


def _smk_block(lines: list[str], start: int) -> list[str]:
    """A rule: its line, then every indented, blank or comment line after it."""
    end = start + 1
    while end < len(lines) and (not lines[end].strip() or lines[end][:1].isspace()):
        end += 1
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def _nf_block(lines: list[str], start: int) -> list[str]:
    """A process: from its `process X {` line to the brace that closes it (strings and comments
    are not parsed: a brace in one can end it early or late, and MAX_CODE_LINES bounds it)."""
    depth = 0
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth <= 0 and i > start:
            return lines[start : i + 1]
    return lines[start:]


def definition(root: Path, engine: str, entry: str | None, name: str) -> dict[str, Any] | None:
    """Where the code defines the process or rule `name` (its last `:` part, for a Nextflow
    qualified name), and its code: `{file, line, code, truncated}`, or None when it is not
    found (an alias of an `include`, a rule made in Python). Only files under `root` are read,
    each with `read_confined`'s checks."""
    short = name.rsplit(":", 1)[-1]
    if not _NAME.fullmatch(short):
        return None
    real_root = Path(os.path.realpath(root))
    if engine == "snakemake":
        if entry is None:
            return None
        try:
            files = [(f.path, f.rules) for f in rule_files(root / entry)]
        except Unsafe as exc:
            log.warning("%s: no rules read: %s", root, exc)
            return None
        pattern = re.compile(rf"^(?:rule|checkpoint)[ \t]+{re.escape(short)}[ \t]*:", re.MULTILINE)
        candidates = [path for path, rules in files if short in rules]
        block = _smk_block
    else:
        candidates = [real_root / file for proc, file in _nf_processes(root) if proc == short]
        pattern = re.compile(rf"^[ \t]*process[ \t]+{re.escape(short)}[ \t]*\{{", re.MULTILINE)
        block = _nf_block
    for path in candidates:
        try:
            text = read_confined(real_root, path, MAX_FILE_BYTES)
        except Unsafe:
            continue
        m = pattern.search(text or "")
        if not m or text is None:
            continue
        lines = text.splitlines()
        start = text.count("\n", 0, m.start())
        code = block(lines, start)
        rel = os.path.relpath(path, real_root)  # the path read, no second realpath (SEC-SRC-03)
        joined = "\n".join(code[:MAX_CODE_LINES])
        return {
            "file": rel,
            "line": start + 1,
            "code": joined[: document.MAX_CODE_CHARS],
            "truncated": len(code) > MAX_CODE_LINES or len(joined) > document.MAX_CODE_CHARS,
        }
    return None
