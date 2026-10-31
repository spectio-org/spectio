"""Detected stages of a Nextflow run, from its fully qualified process names (ui-spec §5.1.1,
Nextflow rules 1 to 7; from the stage-detection spike's `detect_nf.py`).

The names are those of `onProcessCreate`, in creation order, all known before `onFlowBegin`.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from spectio_server.stages.assign import MAX_STAGES, StageDef

REPORT = "MULTIQC"


@dataclass
class _Group:
    sub: bool  # a subworkflow (else a run of direct process calls)
    parent: str
    heads: list[str]
    processes: list[str] = field(default_factory=list)

    @property
    def report(self) -> bool:
        if self.sub:
            return self.heads[0].startswith(REPORT)
        return len(self.heads) == 1 and REPORT in self.heads[0]


def humanise(scope: str) -> str:
    return " ".join(scope.lower().split("_")).capitalize()


def detect_nextflow(
    process_names: Sequence[str],
    manifest_name: str | None,
    meta: Mapping[str, str],
    cap: int = MAX_STAGES,
) -> list[StageDef]:
    """The detected stages, at most `cap`; none for a flat pipeline or fewer than 2 groups.
    `meta` maps a subworkflow's name (`PREPARE_GENOME`) to its `meta.yml` description."""
    split = [n.split(":") for n in process_names]
    if not split:
        return []
    # 1. Wrapper scopes: those every process shares, then the pipeline's own scope.
    depth = 0
    while len({s[depth] for s in split}) == 1 and all(len(s) > depth + 1 for s in split):
        depth += 1
    pipeline: str | None = None
    if manifest_name:
        pipeline = manifest_name.rsplit("/", 1)[-1].upper().replace("-", "_")
    if pipeline is None or not any(len(s) > depth + 1 and s[depth] == pipeline for s in split):
        # No manifest name, or one no scope bears (the workflow's name in Spectio, not the
        # pipeline's `manifest.name`): the scope that holds most processes.
        counts: dict[str, int] = {}
        for s in split:
            if len(s) > depth + 1:
                counts[s[depth]] = counts.get(s[depth], 0) + 1
        top = max(counts, key=lambda k: counts[k]) if counts else None
        pipeline = top if top is not None and counts[top] * 2 > len(split) else None

    # 2. Groups, in creation order.
    groups: list[_Group] = []
    for name, parts in zip(process_names, split, strict=True):
        if len(parts) > depth + 1 and parts[depth] == pipeline:
            parent, head, sub = parts[depth], parts[depth + 1], len(parts) > depth + 2
        else:
            parent, head, sub = ":".join(parts[:depth]), parts[depth], len(parts) > depth + 1
        last = groups[-1] if groups else None
        if sub:
            hit = next(
                (g for g in groups if g.sub and g.parent == parent and g.heads == [head]), None
            )
            if hit is None:
                hit = _Group(True, parent, [head])
                groups.append(hit)
            hit.processes.append(name)
        elif (
            last is not None
            and not last.sub
            and last.parent == parent
            and REPORT not in head
            and not any(REPORT in h for h in last.heads)
        ):
            last.heads.append(head)
            last.processes.append(name)
        else:
            groups.append(_Group(False, parent, [head], [name]))

    # 3. Aliases: neighbouring subworkflows that differ only in their last word.
    merged: list[_Group] = []
    for g in groups:
        p = merged[-1] if merged else None
        if (
            p is not None
            and p.sub
            and g.sub
            and p.parent == g.parent
            and p.heads[0].rsplit("_", 1)[0] == g.heads[0].rsplit("_", 1)[0]
        ):
            p.heads += g.heads
            p.processes += g.processes
        else:
            merged.append(g)
    groups = merged

    # 4. A lone direct process joins its neighbour in the same parent scope.
    i = 0
    while i < len(groups):
        g = groups[i]
        if not g.sub and len(g.processes) == 1 and not g.report:
            near = [
                j
                for j in (i - 1, i + 1)
                if 0 <= j < len(groups) and groups[j].parent == g.parent and not groups[j].report
            ]
            if near:
                t = groups[near[0]]
                t.processes = (
                    t.processes + g.processes if near[0] < i else g.processes + t.processes
                )
                del groups[i]
                continue
        i += 1

    # 5. Cap: merge the neighbouring pair with the fewest processes, never the Report.
    while len(groups) > cap:
        pairs = [
            k for k in range(len(groups) - 1) if not groups[k].report and not groups[k + 1].report
        ]
        if not pairs:
            break
        same = [k for k in pairs if groups[k].parent == groups[k + 1].parent]
        k = min(
            same or pairs, key=lambda k: len(groups[k].processes) + len(groups[k + 1].processes)
        )
        a, b = groups[k], groups.pop(k + 1)
        a.heads += b.heads
        a.processes += b.processes
        a.sub = True

    # 7. A flat pipeline, or fewer than 2 groups: no detected stages.
    if len(groups) < 2 or not any(g.sub for g in groups):
        return []

    # 6. Names and descriptions.
    stages = []
    for n, g in enumerate(groups, 1):
        if g.report:
            name = "Report"
        else:
            name = (" + " if g.sub else ", ").join(humanise(h) for h in g.heads)
        found = [meta[h] for h in g.heads if meta.get(h)]
        description = " / ".join(found) or None
        stages.append(StageDef(f"detected:{n}", name, "detected", description, tuple(g.processes)))
    return stages
