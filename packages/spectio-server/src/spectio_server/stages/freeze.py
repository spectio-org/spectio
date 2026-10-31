"""The projector's side of stages: freeze them once, assign tasks, keep their state (P1 Task 27;
api §7 `run_stages`, ui-spec §5.1.1, checking-scenarios §12.7 note of 2026-10-28).

The stages freeze at the run's first `onFlowBegin` (Nextflow) or `workflow_started` (Snakemake),
before any task, and later launches keep them; the freeze is logged as a `spectio.stages.frozen`
event, so it happens once. Where they come from, first that applies: a lab overlay in
`~/.spectio/overlays/` that matches the run (one only: two matching files apply none, and the
run detail says so), the workflow's own `spectio.yml`, then detection. A declared file whose
globs overlap on this run's names is refused, and detection is used.

Every process or rule seen before the freeze takes the stage whose `match` matches it; one first
seen after it has none (`tasks.stage_id` null). The files read are the server user's: overlays
and their directory must be its own and not writable by others (`read_small`), at most
`MAX_SPEC_BYTES` and parsed with `yaml.safe_load`; the pipeline's files go through
`detect_smk.read_confined` (dev-env §15.3 req. 12).
"""

import logging
import os
import stat
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from sqlalchemy import Row, func, insert, select, update

from spectio.runner.rundir import private_dir, read_small
from spectio_sdk.stages import SpectioFile, applies
from spectio_server.ids import new_id
from spectio_server.stages.assign import Overlap, StageDef, assign
from spectio_server.stages.detect_nf import detect_nextflow
from spectio_server.stages.detect_smk import (
    Unsafe,
    detect_snakemake,
    read_confined,
    read_rules_txt,
    rule_files,
)
from spectio_server.stages.state import stage_state
from spectio_server.store.schema import (
    events,
    run_processes,
    run_stages,
    runs,
    tasks,
    workflow_versions,
    workflows,
)

if TYPE_CHECKING:
    from spectio_server.projector.runs import Projection

log = logging.getLogger(__name__)

FROZEN = "spectio.stages.frozen"
SPEC_SUFFIX = ".spectio.yml"
MAX_SPEC_BYTES = 65536  # an overlay, a `spectio.yml` or a `meta.yml`
MAX_OVERLAYS = 100  # files read from the overlays directory, in name order
MAX_SCOPES = 200  # subworkflows whose `meta.yml` is looked for
DONE = ("succeeded", "cached", "stored")
IN_CHUNK = 500


@dataclass(frozen=True)
class StageSources:
    """Where the server reads stage sources: the overlays directory (`~/.spectio/overlays`) and
    the runs root, under which a launch's `.spectio/rules.txt` is."""

    overlays: Path | None
    runs_root: Path | None


def parse_spectio_yml(data: bytes) -> SpectioFile:
    """A `spectio.yml` of 0.0.1: `workflow` and `stages` only. Raises ValueError."""
    if len(data) > MAX_SPEC_BYTES:
        raise ValueError(f"larger than {MAX_SPEC_BYTES} bytes")
    try:
        value = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise ValueError(f"not YAML: {str(exc)[:200]}") from None
    if not isinstance(value, dict):
        raise ValueError("not a mapping")
    extra = sorted(str(k)[:40] for k in value if k not in ("workflow", "stages"))
    if extra:
        raise ValueError(f"keys not read in 0.0.1: {', '.join(extra[:5])}")
    return SpectioFile.model_validate(value)  # a ValidationError is a ValueError


def find_overlay(
    overlays: Path, engine: str, name: str | None, version: str | None
) -> tuple[SpectioFile | None, str | None]:
    """The one lab overlay that matches the run, and a note for the run detail when more than
    one does (then none applies). A refused file is skipped with a warning."""
    try:
        fd = os.open(overlays, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        log.warning("overlays directory %s not read: %s", overlays, exc)
        return None, None
    hits: list[tuple[str, SpectioFile]] = []
    try:
        st = os.fstat(fd)
        if st.st_uid != os.geteuid() or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            log.warning("overlays directory %s: not yours, or writable by others", overlays)
            return None, None
        files = sorted(n for n in os.listdir(fd) if n.endswith(SPEC_SUFFIX))[:MAX_OVERLAYS]
        for file in files:
            try:
                data = read_small(fd, file, cap=MAX_SPEC_BYTES)
                if data is None:
                    continue
                found = parse_spectio_yml(data)
            except (OSError, ValueError) as exc:
                log.warning("overlay %s not applied: %s", file, str(exc)[:300])
                continue
            if applies(found, engine, name, version):
                hits.append((file, found))
    finally:
        os.close(fd)
    if len(hits) > 1:
        both = ", ".join(file for file, _ in hits)
        return None, f"{len(hits)} lab overlays match this run ({both}): none was applied."
    return (hits[0][1], None) if hits else (None, None)


# --- Rows of the projection ------------------------------------------------------------------


@dataclass(frozen=True)
class _Run:
    engine: str | None
    source: str
    location: str
    name: str | None
    version: str | None

    @property
    def root(self) -> Path | None:
        """The pipeline directory, for a local workflow."""
        if self.source != "local" or not self.location.startswith("/"):
            return None
        return Path(os.path.realpath(self.location))


def _run(p: "Projection") -> _Run:
    row = p.conn.execute(
        select(
            workflows.c.engine,
            workflows.c.source,
            workflows.c.location,
            workflows.c.name,
            workflow_versions.c.version,
        )
        .join(workflow_versions, workflow_versions.c.workflow_id == workflows.c.id)
        .join(runs, runs.c.workflow_version_id == workflow_versions.c.id)
        .where(runs.c.id == p.run_id)
    ).one()
    return _Run(row.engine, row.source, row.location, row.name, row.version)


def frozen(p: "Projection") -> bool:
    found = p.conn.execute(
        select(events.c.id).where(events.c.run_id == p.run_id, events.c.type == FROZEN).limit(1)
    ).first()
    return found is not None


def _names(p: "Projection") -> list[str]:
    return list(
        p.conn.execute(
            select(run_processes.c.name)
            .where(run_processes.c.run_id == p.run_id)
            .order_by(run_processes.c.position)
        ).scalars()
    )


def process_ended(p: "Projection", name: str) -> None:
    """`onProcessTerminate`: the process has no task left."""
    p.process(name)
    p.conn.execute(
        update(run_processes)
        .where(run_processes.c.run_id == p.run_id, run_processes.c.name == name)
        .values(ended=True)
    )


def plan_jobs(p: "Projection", stats: dict[str, int]) -> None:
    """Snakemake's `run_info`: the jobs it plans per rule (it plans again past a checkpoint)."""
    for rule, n in stats.items():
        if rule != "total":
            p.conn.execute(
                update(run_processes)
                .where(run_processes.c.run_id == p.run_id, run_processes.c.name == rule)
                .values(jobs_planned=n)
            )


def freeze(p: "Projection", snakefile_main: str | None = None) -> None:
    """Freeze the run's stages, once (api §7 `run_stages`)."""
    if frozen(p):
        return
    run = _run(p)
    if run.engine == "snakemake":
        universe, detected = _snakemake(p, run, snakefile_main)
        key = None if run.root is None else run.root.name  # the pipeline directory's name
    else:
        universe = _names(p)
        detected = detect_nextflow(universe, run.name, _meta(run, universe))
        key = run.name
    stages, source, note = _declared(p, run, key, universe)
    if not stages:
        stages, source = detected, None
    for n, stage in enumerate(stages, 1):
        p.conn.execute(
            insert(run_stages).values(
                id=new_id("stg"),
                created_at=p.now,
                run_id=p.run_id,
                stage_id=stage.id,
                position=n,
                name=stage.name,
                source=stage.source,
                state="not_started",
                task_counts={},
            )
        )
    by_stage: dict[str, list[str]] = {}
    for name in universe:
        p.process(name)
        if (stage_id := assign(stages, name)) is not None:
            by_stage.setdefault(stage_id, []).append(name)
    for stage_id, found in by_stage.items():
        for i in range(0, len(found), IN_CHUNK):
            p.conn.execute(
                update(run_processes)
                .where(
                    run_processes.c.run_id == p.run_id,
                    run_processes.c.name.in_(found[i : i + IN_CHUNK]),
                )
                .values(stage_id=stage_id)
            )
    of_task = (
        select(run_processes.c.stage_id)
        .where(
            run_processes.c.run_id == tasks.c.run_id,
            run_processes.c.name == tasks.c.process_or_rule,
        )
        .scalar_subquery()
    )
    p.conn.execute(update(tasks).where(tasks.c.run_id == p.run_id).values(stage_id=of_task))
    mode = stages[0].source if stages else "none"
    p.log(FROZEN, {"mode": mode, "source": source, "note": note}, source="projector")


def _declared(
    p: "Projection", run: _Run, key: str | None, universe: list[str]
) -> tuple[list[StageDef], str | None, str | None]:
    """The declared stages that apply, the file they come from, and a note for the run detail."""
    found, note, file = None, None, None
    if p.sources is not None and p.sources.overlays is not None and run.engine:
        found, note = find_overlay(p.sources.overlays, run.engine, key, run.version)
        file = "a lab overlay"
    if found is None and note is None:
        found, file = _own_file(run), "spectio.yml"
    if found is None:
        return [], None, note
    stages = [
        StageDef(s.id, s.name, "declared", s.description, tuple(s.match)) for s in found.stages
    ]
    try:
        for name in universe:
            assign(stages, name)
    except Overlap as exc:
        log.warning("run %s: %s refused: %s", p.run_id, file, exc)
        return [], None, f"The stages of {file} were not applied: {exc}."
    return stages, file, None


def _own_file(run: _Run) -> SpectioFile | None:
    """The workflow's own `spectio.yml`, at the root of its directory."""
    root = run.root
    if root is None:
        return None
    try:
        text = read_confined(root, root / "spectio.yml", MAX_SPEC_BYTES)
        found = None if text is None else parse_spectio_yml(text.encode())
    except (OSError, ValueError) as exc:
        log.warning("%s/spectio.yml not applied: %s", root, str(exc)[:300])
        return None
    if found is not None and found.workflow is not None and found.workflow.engine != run.engine:
        return None
    return found


def _meta(run: _Run, names: list[str]) -> dict[str, str]:
    """The `description` of each subworkflow's `meta.yml` (nf-core layout), when present."""
    root = run.root
    if root is None:
        return {}
    scopes = list(dict.fromkeys(s for n in names for s in n.split(":")[:-1]))[:MAX_SCOPES]
    found: dict[str, str] = {}
    for scope in scopes:
        for kind in ("nf-core", "local"):
            path = root / "subworkflows" / kind / scope.lower() / "meta.yml"
            try:
                text = read_confined(root, path, MAX_SPEC_BYTES)
                value = None if text is None else yaml.safe_load(text)
            except (Unsafe, OSError, yaml.YAMLError):
                continue
            if isinstance(value, dict) and isinstance(value.get("description"), str):
                found[scope] = " ".join(value["description"].split())[:2000]
                break
    return found


def _snakemake(
    p: "Projection", run: _Run, snakefile_main: str | None
) -> tuple[list[str], list[StageDef]]:
    """The run's rules (from `rules.txt` when the head wrote it, else from the rule files) and
    the detected stages."""
    defined = _rules_txt(p)
    main = _main_snakefile(run, snakefile_main)
    if main is None:
        return defined or [], []
    detected = detect_snakemake(main, defined)
    universe = [r for s in detected for r in s.match]
    if defined is not None:
        universe += defined
    else:
        try:
            universe += [r for f in rule_files(main) for r in f.rules]
        except Unsafe:
            pass
    return list(dict.fromkeys(universe)), detected


def _main_snakefile(run: _Run, snakefile_main: str | None) -> Path | None:
    """The main Snakefile: the one `workflow_started` names, else the one the head script
    passes; never one outside the run's pipeline directory."""
    root = run.root
    if root is None:
        return None
    if snakefile_main:
        main = Path(snakefile_main)
    else:
        main = root / "workflow" / "Snakefile"
        if not main.is_file():
            main = root / "Snakefile"
    if not main.is_absolute() or not Path(os.path.realpath(main)).is_relative_to(root):
        log.warning("%s is not in the pipeline directory %s: no detected stages", main, root)
        return None
    return main


def _rules_txt(p: "Projection") -> list[str] | None:
    """`.spectio/rules.txt`, written by the head from `snakemake --list-rules` (P1 Task 9)."""
    if p.sources is None or p.sources.runs_root is None:
        return None
    try:
        with private_dir(p.sources.runs_root, p.run_id, "launch", ".spectio") as fd:
            data = read_small(fd, "rules.txt")
    except FileNotFoundError:
        return None  # no launch directory: a run from a terminal, or a rebuilt one
    except (OSError, ValueError) as exc:
        log.warning("run %s: rules.txt not read: %s", p.run_id, exc)
        return None
    return None if data is None else read_rules_txt(data)


# --- State, at the end of each transaction ---------------------------------------------------


def refresh(p: "Projection") -> None:
    """Each stage's task counts and state, from its tasks and processes (ui-spec §5.1.1)."""
    rows = p.conn.execute(select(run_stages).where(run_stages.c.run_id == p.run_id)).all()
    if not rows:
        return
    mine = tasks.c.run_id == p.run_id
    counts: dict[str, dict[str, int]] = {}
    for stage_id, state, n in p.conn.execute(
        select(tasks.c.stage_id, tasks.c.state, func.count())
        .where(mine, tasks.c.stage_id.is_not(None))
        .group_by(tasks.c.stage_id, tasks.c.state)
    ):
        counts.setdefault(stage_id, {})[state] = n
    procs = p.conn.execute(
        select(run_processes).where(
            run_processes.c.run_id == p.run_id, run_processes.c.stage_id.is_not(None)
        )
    ).all()
    ended = _ended(p, procs, counts)
    failed_here = _failed_stage(p)
    at = p.event_time or p.now
    for row in rows:
        c = counts.get(row.stage_id, {})
        state = stage_state(c, ended.get(row.stage_id, False), p.state, failed_here == row.stage_id)
        values: dict[str, Any] = {}
        if state != row.state:
            values["state"] = state
        if c != (row.task_counts or {}):
            values["task_counts"] = c
        if row.started_at is None and state in ("running", "completed", "failed"):
            values["started_at"] = at
        if row.ended_at is None and state in ("completed", "failed", "skipped"):
            values["ended_at"] = at
        elif row.ended_at is not None and state in ("not_started", "running"):
            values["ended_at"] = None  # more jobs past a checkpoint
        if values:
            p.conn.execute(update(run_stages).where(run_stages.c.id == row.id).values(**values))


def _ended(
    p: "Projection", procs: Iterable[Row[Any]], counts: dict[str, dict[str, int]]
) -> dict[str, bool]:
    """Whether each stage has ended: every Nextflow process terminated; for Snakemake, which
    has no such event, every rule has as many jobs done as `run_info` planned."""
    by_stage: dict[str, list[Row[Any]]] = {}
    for proc in procs:
        by_stage.setdefault(proc.stage_id, []).append(proc)
    if _run(p).engine != "snakemake":
        return {s: all(x.ended for x in found) for s, found in by_stage.items()}
    done: dict[str, int] = dict(
        p.conn.execute(
            select(tasks.c.process_or_rule, func.count())
            .where(tasks.c.run_id == p.run_id, tasks.c.state.in_(DONE))
            .group_by(tasks.c.process_or_rule)
        ).all()
    )
    return {
        s: sum(counts.get(s, {}).values()) > 0
        and all(done.get(x.name, 0) >= (x.jobs_planned or 0) for x in found)
        for s, found in by_stage.items()
    }


def _failed_stage(p: "Projection") -> str | None:
    """The stage of the task the run failed on, if it failed on one."""
    if p.state != "failed":
        return None
    failure = p.conn.execute(select(runs.c.failure).where(runs.c.id == p.run_id)).scalar()
    task_id = (failure or {}).get("task_id")
    if not isinstance(task_id, str):
        return None
    found = p.conn.execute(select(tasks.c.stage_id).where(tasks.c.id == task_id)).scalar()
    return found if isinstance(found, str) else None
