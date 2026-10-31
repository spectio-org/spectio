"""Stages, declared or detected (P1 Task 27; ui-spec §5.1.1, checking-scenarios §12.1, §12.3 and
§12.7, api §5 and §7).

Golden tests on `tests/pipelines/real/stages/`: the detectors against the spike's output, the four
example overlays against their fixtures, and the freeze, the stage states and the read routes on
the rnaseq preview events (`events/`), turned into spool events as `nf-spectio` writes them.
"""

import json
import logging
import os
import time
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from alembic import command as alembic_command
from sqlalchemy import inspect, select, text

from spectio.config import Settings
from spectio.runner.rundir import private_dir, write_file
from spectio.runner.types import SpoolBatch
from spectio_sdk.events import SpoolEvent
from spectio_sdk.stages import SpectioFile
from spectio_server.projector.ingest import ingest
from spectio_server.stages.assign import Overlap, StageDef, assign
from spectio_server.stages.detect_nf import detect_nextflow
from spectio_server.stages.detect_smk import detect_snakemake, read_rules_txt
from spectio_server.stages.freeze import StageSources, find_overlay, parse_spectio_yml
from spectio_server.store.db import open_db
from spectio_server.store.schema import run_processes, run_stages, runner_commands, tasks
from spectio_server.store.writer import Writer

from .conftest import add_run, client_for

STAGES = Path(__file__).resolve().parents[4] / "tests" / "pipelines" / "real" / "stages"
NEXTFLOW = {
    "rnaseq-3.27.0_star_salmon": ("nf-core/rnaseq", 67, 8),
    "rnaseq-3.27.0_hisat2": ("nf-core/rnaseq", 62, 8),
    "sarek-3.11.0": ("nf-core/sarek", 48, 8),
    "methylseq-4.2.0_bismark": ("nf-core/methylseq", 13, 4),
    "methylseq-4.2.0_bwameth": ("nf-core/methylseq", 15, 5),
}
MOSAICATCHER = "mosaicatcher-v2.5.1"
NEXTFLOW_KEY = "rnaseq-3.27.0_star_salmon"
HAPPY = ["MAKE_READS", "QC_STATS", "QC_REPORT", "SPLIT", "ALIGN", "MERGE", "COMPARE"]
HAPPY += ["FINAL_REPORT"]  # the synthetic pipeline of dev-env §10.1, in creation order
RNASEQ_RUN = "run_01K8T27STAGES0000000000000"
FIELDS = ("id", "name", "source", "description", "match")
T0 = datetime(2026, 10, 28, 7, 0, tzinfo=UTC)


def names(key: str) -> list[str]:
    return (STAGES / "processes" / f"{key}.txt").read_text().split()


def expected(key: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = json.loads(
        (STAGES / "expected" / f"{key}_detected.json").read_text()
    )
    return [{k: s.get(k) for k in FIELDS} for s in found]


def as_json(stages: list[StageDef]) -> list[dict[str, Any]]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "source": s.source,
            "description": s.description,
            "match": list(s.match),
        }
        for s in stages
    ]


def meta_of(key: str) -> dict[str, str]:
    """The `meta.yml` descriptions the spike read, keyed by subworkflow: the fixtures hold no
    source, so they are taken back from the golden output (one subworkflow per stage)."""
    return {
        s["name"].upper().replace(" ", "_"): s["description"]
        for s in expected(key)
        if s["description"] and "+" not in s["name"] and "," not in s["name"]
    }


# --- Nextflow detection ----------------------------------------------------------------------


@pytest.mark.parametrize("key", NEXTFLOW)
def test_detect_nf_golden(key: str) -> None:
    manifest, n_processes, n_stages = NEXTFLOW[key]
    found = detect_nextflow(names(key), manifest, meta_of(key))
    assert len(names(key)) == n_processes and len(found) == n_stages
    assert as_json(found) == expected(key)


@pytest.mark.parametrize("key", NEXTFLOW)
def test_detect_nf_without_manifest(key: str) -> None:
    """With no manifest name, the pipeline scope is the child holding more than half."""
    assert as_json(detect_nextflow(names(key), None, meta_of(key))) == expected(key)


def test_detect_nf_flat_none() -> None:
    assert detect_nextflow(HAPPY, None, {}) == []
    assert detect_nextflow([], "nf-core/rnaseq", {}) == []


@pytest.mark.parametrize("key", NEXTFLOW)
def test_detect_nf_report_kept(key: str) -> None:
    """MULTIQC is its own last stage, "Report", whatever the cap merged before it."""
    for cap in (8, 3):
        last = detect_nextflow(names(key), NEXTFLOW[key][0], {}, cap=cap)[-1]
        assert last.name == "Report"
        assert [m.rsplit(":", 1)[-1] for m in last.match] == ["MULTIQC"]


# --- Snakemake detection ---------------------------------------------------------------------


def mosaicatcher_tree(root: Path) -> Path:
    """The pipeline's rule files rebuilt from the fixture (in include order, with their rules and
    checkpoints): the main Snakefile includes each file, in that order."""
    found = json.loads((STAGES / "rules" / f"{MOSAICATCHER}_rule-files.json").read_text())
    workflow = root / "mosaicatcher-pipeline" / "workflow"
    main = workflow / "Snakefile"
    lines: list[str] = []
    for entry in found["files"]:
        body = [
            f"{'checkpoint' if r in entry['checkpoints'] else 'rule'} {r}:\n    shell: 'true'\n"
            for r in entry["rules"]
        ]
        if entry["file"] == "Snakefile":
            lines += body
            continue
        path = workflow / entry["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(body))
        lines.insert(0, f'include: "{entry["file"]}"\n')
    main.parent.mkdir(parents=True, exist_ok=True)
    includes = [line for line in lines if line.startswith("include")][::-1]
    main.write_text("".join(includes + [line for line in lines if not line.startswith("include")]))
    return main


def list_rules() -> set[str]:
    return set((STAGES / "rules" / f"{MOSAICATCHER}_list-rules.txt").read_text().split())


def test_detect_smk_golden(tmp_path: Path) -> None:
    found = detect_snakemake(mosaicatcher_tree(tmp_path), list_rules())
    assert len(list_rules()) == 101 and len(found) == 8
    assert as_json(found) == expected(MOSAICATCHER)


def test_detect_smk_source_only(tmp_path: Path) -> None:
    found = detect_snakemake(mosaicatcher_tree(tmp_path), None)
    assert len(found) == 8
    assert len({r for s in found for r in s.match}) == sum(len(s.match) for s in found) == 204
    assert found[-1].name == "Final targets" and list(found[-1].match) == ["all"]


def test_detect_smk_one_rule_file_none(tmp_path: Path) -> None:
    main = tmp_path / "w" / "Snakefile"
    (tmp_path / "w" / "rules").mkdir(parents=True)
    (tmp_path / "w" / "rules" / "a.smk").write_text("rule a:\n    shell: 'true'\n")
    main.write_text('include: "rules/a.smk"\nrule all:\n    input: []\n')
    assert detect_snakemake(main, None) == []
    synthetic = Path(__file__).resolve().parents[4] / "tests" / "pipelines" / "synthetic"
    assert detect_snakemake(synthetic / "snakemake" / "workflow" / "Snakefile", None) == []


def test_rules_txt_docstrings_stripped() -> None:
    data = b"count_reads (Count reads per bin)\nall\n\n  mosaic_count  \nnot a rule\n"
    assert read_rules_txt(data) == ["count_reads", "all", "mosaic_count"]


def unsafe_trees(tmp_path: Path) -> Iterator[tuple[str, Path]]:
    for case in ("symlink", "many", "fifo", "large", "outside"):
        main = tmp_path / case / "workflow" / "Snakefile"
        rules = main.parent / "rules"
        rules.mkdir(parents=True)
        includes = ['include: "rules/a.smk"\n', 'include: "rules/b.smk"\n']
        (rules / "a.smk").write_text("rule a:\n    shell: 'true'\n")
        outside = tmp_path / f"{case}-elsewhere.smk"
        outside.write_text("rule b:\n    shell: 'true'\n")
        if case == "symlink":
            (rules / "b.smk").symlink_to(outside)
        elif case == "many":
            for i in range(200):
                (rules / f"r{i}.smk").write_text(f"rule r{i}:\n    shell: 'true'\n")
                includes.append(f'include: "rules/r{i}.smk"\n')
        elif case == "fifo":
            os.mkfifo(rules / "b.smk")
        elif case == "large":
            (rules / "b.smk").write_text("rule b:\n    shell: 'true'\n" + "#" * 1048576)
        else:  # an include that climbs out of the main Snakefile's directory
            includes[1] = f'include: "../../{outside.name}"\n'
        main.write_text("".join(includes) + "rule all:\n    input: []\n")
        yield case, main


def test_detect_smk_unsafe_path(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """dev-env §15.3 req. 12: regular files only, no symlink or include leaving the main
    Snakefile's directory, at most 200 files of 1 MiB; a path that fails gives no stages."""
    for case, main in unsafe_trees(tmp_path):
        caplog.clear()
        with caplog.at_level(logging.WARNING):
            assert detect_snakemake(main, None) == [], case
        assert "no detected stages" in caplog.text, case
    good = tmp_path / "symlink" / "workflow" / "rules" / "b.smk"
    good.unlink()
    good.write_text("rule b:\n    shell: 'true'\n")
    assert [s.name for s in detect_snakemake(good.parents[1] / "Snakefile", None)] == [
        "A",
        "B",
        "Final targets",
    ]


# --- Overlays and assignment -----------------------------------------------------------------

OVERLAYS = {
    "nf-core-rnaseq": ["rnaseq-3.27.0_star_salmon", "rnaseq-3.27.0_hisat2"],
    "nf-core-sarek": ["sarek-3.11.0"],
    "nf-core-methylseq": ["methylseq-4.2.0_bismark", "methylseq-4.2.0_bwameth"],
    "mosaicatcher": [MOSAICATCHER],
}


def overlay(name: str) -> SpectioFile:
    return parse_spectio_yml((STAGES / "overlays" / f"{name}.spectio.yml").read_bytes())


def declared(found: SpectioFile) -> list[StageDef]:
    return [StageDef(s.id, s.name, "declared", s.description, tuple(s.match)) for s in found.stages]


@pytest.mark.parametrize("name", OVERLAYS)
def test_overlay_assign_golden(name: str) -> None:
    stages = declared(overlay(name))
    for key in OVERLAYS[name]:
        found = sorted(list_rules()) if key == MOSAICATCHER else names(key)
        assigned = {n: assign(stages, n) for n in found}
        assert None not in assigned.values(), key
        assert {s.id for s in stages} >= set(assigned.values())


def test_overlay_overlap_refused() -> None:
    stages = declared(overlay("nf-core-rnaseq"))
    stages.append(StageDef("qc2", "QC again", "declared", None, ("*:FASTQC",)))
    with pytest.raises(Overlap) as caught:
        for n in names("rnaseq-3.27.0_star_salmon"):
            assign(stages, n)
    assert caught.value.ids == ("reads", "qc2")
    assert "reads" in str(caught.value) and "qc2" in str(caught.value)


def write_overlay(where: Path, file: str, workflow: str) -> None:
    text = (STAGES / "overlays" / "nf-core-rnaseq.spectio.yml").read_text()
    (where / file).write_text(text.replace(text.splitlines()[3], workflow))
    (where / file).chmod(0o600)


def test_overlay_matching(tmp_path: Path) -> None:
    """checking-scenarios §12.7 note: engine and name match; the version range is checked on
    Nextflow; two matching files apply none, and say so."""
    home = tmp_path / "overlays"
    home.mkdir(mode=0o700)
    write_overlay(
        home,
        "a.spectio.yml",
        'workflow: {name: nf-core/rnaseq, engine: nextflow, version: ">=3.27.0 <4"}',
    )
    found, note = find_overlay(home, "nextflow", "nf-core/rnaseq", "3.27.0")
    assert found is not None and found.stages[0].id == "reference" and note is None
    assert find_overlay(home, "snakemake", "nf-core/rnaseq", None) == (None, None)
    assert find_overlay(home, "nextflow", "nf-core/sarek", "3.27.0") == (None, None)
    assert find_overlay(home, "nextflow", "nf-core/rnaseq", "4.0.0") == (None, None)
    assert find_overlay(home, "nextflow", "nf-core/rnaseq", "3.26.1") == (None, None)
    assert find_overlay(home, "nextflow", "nf-core/rnaseq", None)[0] is not None  # unknown: kept
    # Snakemake: the last part of the name is the pipeline directory's name; no version check.
    write_overlay(
        home,
        "m.spectio.yml",
        "workflow: {name: friendsofstrandseq/mosaicatcher-pipeline, engine: snakemake,"
        ' version: "9"}',
    )
    assert find_overlay(home, "snakemake", "mosaicatcher-pipeline", "1.0")[0] is not None
    write_overlay(home, "b.spectio.yml", "workflow: {name: nf-core/rnaseq, engine: nextflow}")
    found, note = find_overlay(home, "nextflow", "nf-core/rnaseq", "3.27.0")
    assert found is None
    assert note is not None and "a.spectio.yml" in note and "b.spectio.yml" in note
    # Refused files are skipped: other keys than workflow and stages, a symlink, too large.
    for bad in ("b", "m"):
        (home / f"{bad}.spectio.yml").unlink()
    (home / "g.spectio.yml").write_text(
        "workflow: {name: x, engine: nextflow}\nstages: []\ngates: {}\n"
    )
    (home / "l.spectio.yml").symlink_to(home / "a.spectio.yml")
    (home / "z.spectio.yml").write_text("#" * 70000)
    assert find_overlay(home, "nextflow", "nf-core/rnaseq", "3.27.0")[0] is not None
    assert find_overlay(tmp_path / "none", "nextflow", "nf-core/rnaseq", "3.27.0") == (None, None)
    with pytest.raises(ValueError, match="gates"):
        parse_spectio_yml(
            b"workflow: {name: x, engine: nextflow}\n"
            b"stages: [{id: a, name: A, match: ['*']}]\ngates: {}\n"
        )
    with pytest.raises(ValueError):
        parse_spectio_yml(b"!!python/object/apply:os.system ['true']\n")  # safe_load only


# --- Freeze, assignment of tasks and stage states (projector) --------------------------------


def nf_event(seq: int, body: dict[str, Any], run_id: str = RNASEQ_RUN) -> SpoolEvent:
    data = {k: v for k, v in body.items() if k not in ("hook", "instant", "seq")}
    return SpoolEvent.model_validate(
        {
            "v": 1,
            "id": f"evt_t27_{seq}",
            "run": run_id,
            "launch": 1,
            "producer": "nf-spectio/0.0.1",
            "seq": seq,
            "time": (T0 + timedelta(seconds=seq)).isoformat(),
            "type": f"nextflow.{body['hook']}",
            "data": data,
        }
    )


def rnaseq_bodies() -> list[dict[str, Any]]:
    path = STAGES / "events" / "rnaseq-3.27.0_star_salmon_preview_events.jsonl"
    return [json.loads(line)["body"] for line in path.read_text().splitlines()]


def task(hook: str, process: str, tag: str, **extra: Any) -> dict[str, Any]:
    return {"hook": hook, "process": process, "tag": tag, "name": f"{process} ({tag})", **extra}


def done(process: str, tag: str, status: str = "COMPLETED", **extra: Any) -> dict[str, Any]:
    return task("onTaskComplete", process, tag, trace={"status": status}, **extra)


class Replayed:
    def __init__(self, writer: Writer, launch_id: str, sources: StageSources) -> None:
        self.writer, self.launch_id, self.sources, self.seq = writer, launch_id, sources, 0

    def send(self, *bodies: dict[str, Any]) -> None:
        found = []
        for body in bodies:
            self.seq += 1
            found.append(nf_event(self.seq, body))
        batch = SpoolBatch(found, {}, Counter())
        run = partial(ingest, launch_id=self.launch_id, batch=batch, sources=self.sources)
        self.writer.submit(run).result()

    def stages(self) -> list[Any]:
        query = select(run_stages).where(run_stages.c.run_id == RNASEQ_RUN)
        return self.writer.submit(
            lambda c: list(c.execute(query.order_by(run_stages.c.position)).all())
        ).result()

    def stage_of(self) -> dict[str, str | None]:
        query = select(tasks.c.process_or_rule, tasks.c.stage_id).where(
            tasks.c.run_id == RNASEQ_RUN
        )
        return dict(self.writer.submit(lambda c: c.execute(query).all()).result())


@pytest.fixture
def overlays(settings: Settings) -> Path:
    home = settings.data_dir / "overlays"
    home.mkdir(mode=0o700)
    return home


@pytest.fixture
def replayed(settings: Settings, writer: Writer, overlays: Path) -> Replayed:
    """The rnaseq run of the preview events, launched from the UI; nothing sent yet but
    `onFlowCreate` and the 67 `onProcessCreate` (all before `onFlowBegin`)."""
    launch_id = add_run(writer, settings, RNASEQ_RUN, "rnaseq-staged")
    found = Replayed(writer, launch_id, StageSources(overlays, settings.runs_root))
    bodies = rnaseq_bodies()
    found.send(*[b for b in bodies if b["hook"] in ("onFlowCreate", "onProcessCreate")])
    return found


def flow_begin(r: Replayed) -> None:
    r.send({"hook": "onFlowBegin"})


def test_declared_beats_detected(
    replayed: Replayed, overlays: Path, writer: Writer, settings: Settings
) -> None:
    flow_begin(replayed)
    assert [(s.stage_id, s.source) for s in replayed.stages()][:2] == [
        ("detected:1", "detected"),
        ("detected:2", "detected"),
    ]
    # The same pipeline with a lab overlay for it (name from the launch, `lab/nextflow`).
    write_overlay(
        overlays, "rnaseq.spectio.yml", "workflow: {name: lab/nextflow, engine: nextflow}"
    )
    other = "run_01K8T27STAGES0000000000001"
    launch_id = add_run(writer, settings, other, "rnaseq-declared")
    r = Replayed(writer, launch_id, replayed.sources)
    bodies = [b for b in rnaseq_bodies() if b["hook"] in ("onProcessCreate", "onFlowBegin")]
    found = [nf_event(i, b, other) for i, b in enumerate(bodies, 1)]
    run = partial(
        ingest, launch_id=launch_id, batch=SpoolBatch(found, {}, Counter()), sources=r.sources
    )
    writer.submit(run).result()
    rows = writer.submit(
        lambda c: c.execute(
            select(run_stages).where(run_stages.c.run_id == other).order_by(run_stages.c.position)
        ).all()
    ).result()
    assert [(s.stage_id, s.name, s.source) for s in rows] == [
        ("reference", "Reference preparation", "declared"),
        ("reads", "Read QC and trimming", "declared"),
        ("align", "Alignment", "declared"),
        ("quant", "Quantification", "declared"),
        ("qc", "Alignment QC and coverage", "declared"),
        ("report", "Report", "declared"),
    ]


def test_overlay_overlap_falls_back(replayed: Replayed, overlays: Path) -> None:
    """An overlay whose globs overlap on this run is not applied: detected stages instead."""
    text = (STAGES / "overlays" / "nf-core-rnaseq.spectio.yml").read_text()
    text = text.replace(
        'workflow: {name: nf-core/rnaseq, engine: nextflow, version: ">=3.27.0 <4"}',
        "workflow: {name: lab/nextflow, engine: nextflow}",
    )
    (overlays / "rnaseq.spectio.yml").write_text(
        text + "  - {id: qc2, name: QC again, match: ['*:FASTQC']}\n"
    )
    flow_begin(replayed)
    assert {s.source for s in replayed.stages()} == {"detected"}


def test_stages_frozen_at_flow_begin(replayed: Replayed) -> None:
    flow_begin(replayed)
    late = "NFCORE_RNASEQ:RNASEQ:FASTQ_ALIGN_HISAT2:HISAT2_ALIGN"
    replayed.send(
        {"hook": "onProcessCreate", "process": late},
        task("onTaskPending", late, "S1"),
        {"hook": "onFlowBegin"},  # a second one never refreezes
    )
    rows = replayed.stages()
    assert [s.stage_id for s in rows] == [f"detected:{n}" for n in range(1, 9)]
    assert [s.name for s in rows][-1] == "Report"
    assert {s.state for s in rows} == {"not_started"}
    assert replayed.stage_of() == {late: None}


def test_stage_states(replayed: Replayed) -> None:
    """ui-spec §5.1.1 Order and state: running from the first task, completed when every
    process has ended, skipped when it ended with no task, failed when the run fails on one of
    its tasks; a stage still running when the run fails ends failed too (shown as Stopped)."""
    flow_begin(replayed)
    stages = {s.stage_id: s for s in replayed.stages()}
    first, second, third = (names_of(replayed, f"detected:{n}") for n in (1, 2, 3))
    replayed.send(task("onTaskStart", first[0], "S1"))
    assert state(replayed) == {"detected:1": "running"}
    replayed.send(
        done(first[0], "S1"),
        *[{"hook": "onProcessTerminate", "process": p} for p in first],
        *[{"hook": "onProcessTerminate", "process": p} for p in second],  # `when:` false
        task("onTaskStart", third[0], "S1"),
        task("onTaskStart", third[1], "S1"),
    )
    assert state(replayed) == {
        "detected:1": "completed",
        "detected:2": "skipped",
        "detected:3": "running",
    }
    rows = {s.stage_id: s for s in replayed.stages()}
    assert rows["detected:1"].task_counts == {"succeeded": 1}
    assert rows["detected:1"].started_at is not None and rows["detected:1"].ended_at is not None
    assert stages["detected:1"].started_at is None
    replayed.send(
        done(third[0], "S1", "FAILED", errorAction="TERMINATE", exitStatus=1),
        {"hook": "onFlowComplete", "success": False},
    )
    found = state(replayed)
    assert found["detected:3"] == "failed" and found["detected:1"] == "completed"
    assert found["detected:2"] == "skipped" and found["detected:8"] == "skipped"
    assert replayed.stage_of()[third[1]] == "detected:3"


def names_of(r: Replayed, stage_id: str) -> list[str]:
    query = (
        select(run_processes.c.name)
        .where(run_processes.c.run_id == RNASEQ_RUN, run_processes.c.stage_id == stage_id)
        .order_by(run_processes.c.position)
    )
    return list(r.writer.submit(lambda c: c.execute(query).scalars().all()).result())


def state(r: Replayed) -> dict[str, str]:
    return {s.stage_id: s.state for s in r.stages() if s.state != "not_started"}


def test_stages_route(replayed: Replayed, settings: Settings, writer: Writer) -> None:
    """Task 18's GET /stages filled from `run_stages`; `stage_id` on every `/processes` item,
    in creation order, a process with no task included; `summary.stage_mode`."""
    client = client_for(settings, writer)
    runs = "/api/v1/runs"
    assert client.get(f"{runs}/{RNASEQ_RUN}").json()["summary"]["stage_mode"] == "quarters"
    flow_begin(replayed)
    items = client.get(f"{runs}/{RNASEQ_RUN}/stages").json()["items"]
    assert [s["position"] for s in items] == list(range(1, 9))
    assert set(items[0]) == {"id", "position", "name", "source", "state", "task_counts"}
    assert items[0]["name"] == "Prepare genome references + Prepare genome indices"
    processes = client.get(f"{runs}/{RNASEQ_RUN}/processes").json()["items"]
    assert [p["process"] for p in processes] == names("rnaseq-3.27.0_star_salmon")
    assert processes[0] == {
        "process": "NFCORE_RNASEQ:PREPARE_GENOME_REFERENCES:GUNZIP_GTF",
        "stage_id": "detected:1",
        "counts": {},
        "retries": 0,
    }
    assert {p["stage_id"] for p in processes} == {s["id"] for s in items}
    run = client.get(f"{runs}/{RNASEQ_RUN}").json()
    assert run["summary"]["stage_mode"] == "detected" and run["stages_note"] is None
    listed = client.get(runs).json()["items"]
    assert [r["summary"]["stage_mode"] for r in listed if r["id"] == RNASEQ_RUN] == ["detected"]


def test_stages_note_when_two_overlays_match(
    replayed: Replayed, overlays: Path, settings: Settings, writer: Writer
) -> None:
    for file in ("a.spectio.yml", "b.spectio.yml"):
        write_overlay(overlays, file, "workflow: {name: lab/nextflow, engine: nextflow}")
    flow_begin(replayed)
    run = client_for(settings, writer).get(f"/api/v1/runs/{RNASEQ_RUN}").json()
    assert run["summary"]["stage_mode"] == "detected"
    assert "a.spectio.yml" in run["stages_note"] and "b.spectio.yml" in run["stages_note"]


DEEP = b"[" * 60000  # a RecursionError in `yaml.safe_load`, under MAX_SPEC_BYTES


@pytest.mark.parametrize("engine", ["nextflow", "snakemake"])
def test_freeze_survives_deep_yaml(
    settings: Settings, writer: Writer, overlays: Path, tmp_path: Path, engine: str
) -> None:
    """A deeply nested overlay, `spectio.yml` or `meta.yml` gives no declared stages, never a
    failed ingest: the start event is projected and the freeze is recorded (CR-P3T27-02,
    SEC-P3T27-01)."""
    with pytest.raises(ValueError, match="nested too deep"):
        parse_spectio_yml(DEEP)
    run_id = f"run_01K8T27DEEP{engine[0].upper()}00000000000000"
    launch_id = add_run(writer, settings, run_id, "deep", "running", engine=engine)
    pipeline = tmp_path / "pipeline"
    (pipeline / "subworkflows" / "nf-core" / "nfcore_rnaseq").mkdir(parents=True)
    (pipeline / "subworkflows" / "nf-core" / "nfcore_rnaseq" / "meta.yml").write_bytes(DEEP)
    (pipeline / "spectio.yml").write_bytes(DEEP)
    (pipeline / "Snakefile").write_text("rule a:\n    shell: 'true'\n")
    (overlays / "deep.spectio.yml").write_bytes(DEEP)
    writer.submit(
        lambda c: c.execute(text("UPDATE workflows SET location = :l"), {"l": str(pipeline)})
    ).result()
    if engine == "nextflow":
        procs = [{"hook": "onProcessCreate", "process": n} for n in names(NEXTFLOW_KEY)]
        found = [nf_event(i, b, run_id) for i, b in enumerate([*procs, {"hook": "onFlowBegin"}], 1)]
        start = "spectio.engine.nextflow.onFlowBegin"
    else:
        found = [smk_event(1, run_id, "workflow_started", {"snakemake_version": "9.27.1"})]
        start = "spectio.engine.snakemake.workflow_started"
    run = partial(
        ingest,
        launch_id=launch_id,
        batch=SpoolBatch(found, {}, Counter()),
        sources=StageSources(overlays, settings.runs_root),
    )
    writer.submit(run).result()
    logged, started = writer.submit(
        lambda c: (
            set(
                c.execute(
                    text("SELECT type FROM events WHERE run_id = :r"), {"r": run_id}
                ).scalars()
            ),
            c.execute(text("SELECT started_at FROM runs WHERE id = :r"), {"r": run_id}).scalar(),
        )
    ).result()
    assert start in logged and "spectio.stages.frozen" in logged
    assert started is not None
    rows = writer.submit(
        lambda c: c.execute(select(run_stages).where(run_stages.c.run_id == run_id)).all()
    ).result()
    assert {r.source for r in rows} <= {"detected"}


def alias_bomb(levels: int = 10) -> bytes:
    """Nine-fold aliases, `levels` deep: a few hundred bytes that stand for 9**levels items
    (SEC-P3T27-02)."""
    lines = ["workflow:", "  l0: &l0 [x, x, x, x, x, x, x, x, x]"]
    for n in range(1, levels):
        lines.append(f"  l{n}: &l{n} [{', '.join([f'*l{n - 1}'] * 9)}]")
    lines.append(f"stages: *l{levels - 1}")
    return ("\n".join(lines) + "\n").encode()


@pytest.mark.parametrize("engine", ["nextflow", "snakemake"])
def test_freeze_refuses_yaml_aliases(
    settings: Settings, writer: Writer, overlays: Path, tmp_path: Path, engine: str
) -> None:
    """An alias bomb in an overlay or a `spectio.yml` is refused at once: no anchors are read,
    and the freeze is still recorded (SEC-P3T27-02)."""
    bomb = alias_bomb()
    assert len(bomb) < 1024
    began = time.monotonic()
    with pytest.raises(ValueError, match="alias"):
        parse_spectio_yml(bomb)
    assert time.monotonic() - began < 1
    run_id = f"run_01K8T27BMB{engine[0].upper()}{'0' * 15}"
    launch_id = add_run(writer, settings, run_id, "bomb", "running", engine=engine)
    pipeline = tmp_path / "pipeline"
    pipeline.mkdir()
    (pipeline / "spectio.yml").write_bytes(bomb)
    (pipeline / "Snakefile").write_text("rule a:\n    shell: 'true'\n")
    (overlays / "bomb.spectio.yml").write_bytes(bomb)
    (overlays / "bomb.spectio.yml").chmod(0o600)
    writer.submit(
        lambda c: c.execute(text("UPDATE workflows SET location = :l"), {"l": str(pipeline)})
    ).result()
    if engine == "nextflow":
        found = [nf_event(1, {"hook": "onFlowBegin"}, run_id)]
    else:
        found = [smk_event(1, run_id, "workflow_started", {"snakemake_version": "9.27.1"})]
    run = partial(
        ingest,
        launch_id=launch_id,
        batch=SpoolBatch(found, {}, Counter()),
        sources=StageSources(overlays, settings.runs_root),
    )
    began = time.monotonic()
    writer.submit(run).result()
    assert time.monotonic() - began < 1
    logged = writer.submit(
        lambda c: set(
            c.execute(text("SELECT type FROM events WHERE run_id = :r"), {"r": run_id}).scalars()
        )
    ).result()
    assert "spectio.stages.frozen" in logged


def test_validation_error_logged_without_input(caplog: pytest.LogCaptureFixture) -> None:
    """A file that fails validation is logged by field and message, never by its content
    (SEC-P3T27-02): `str()` of a ValidationError formats the input."""
    secret = "x" * 50 + "INPUT-NOT-LOGGED"
    with pytest.raises(ValueError) as caught:
        parse_spectio_yml(f"stages: [{{id: a, name: A, match: 3, other: {secret}}}]".encode())
    assert "INPUT-NOT-LOGGED" not in str(caught.value)


@pytest.mark.parametrize(
    "data",
    [
        b"stages:\n  - id: a\n    name: [MARKER-NOT-LOGGED\n",  # a syntax error on that line
        b"workflow: {name: x}\nMARKER-NOT-LOGGED\nx: : y\n",
        b"MARKER-NOT-LOGGED-\n-\n-: 1\nstages: []\n",
    ],
)
def test_yaml_error_logged_without_content(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, data: bytes
) -> None:
    """A malformed or refused file is reported by line, column and problem, never by its text:
    PyYAML's error quotes the offending line (SEC-P3T27-03)."""
    with pytest.raises(ValueError) as caught:
        parse_spectio_yml(data)
    said = str(caught.value)
    assert "MARKER" not in said and "\n" not in said
    where = tmp_path / "overlays"
    where.mkdir(mode=0o700)
    (where / "bad.spectio.yml").write_bytes(data)
    with caplog.at_level(logging.WARNING):
        assert find_overlay(where, "nextflow", "x", None) == (None, None)
    assert "not applied" in caplog.text and "MARKER" not in caplog.text


def test_extra_key_reported_on_one_line() -> None:
    """An extra key is named by its repr(), at most 40 characters: no newline reaches the log."""
    with pytest.raises(ValueError) as caught:
        parse_spectio_yml(b'stages: []\n"gates\\n\\x1b' + b"y" * 60 + b'": 1\n')
    said = str(caught.value)
    assert "gates" in said and "y" * 40 not in said
    assert all(c.isprintable() for c in said)


# --- Snakemake freeze ------------------------------------------------------------------------


def smk_event(seq: int, run_id: str, type_: str, data: dict[str, Any]) -> SpoolEvent:
    return SpoolEvent.model_validate(
        {
            "v": 1,
            "id": f"evt_smk_{seq}",
            "run": run_id,
            "launch": 1,
            "producer": "snakemake-logger-spectio/0.0.1",
            "seq": seq,
            "time": (T0 + timedelta(seconds=seq)).isoformat(),
            "type": f"snakemake.{type_}",
            "data": data,
        }
    )


@pytest.mark.parametrize("rules_txt", [True, False])
def test_snakemake_freeze(
    settings: Settings, writer: Writer, overlays: Path, tmp_path: Path, rules_txt: bool
) -> None:
    """At `workflow_started`, the rule files of the run's pipeline, and `.spectio/rules.txt`
    from `snakemake --list-rules` when the head wrote it; a job of a rule takes its stage, and a
    stage is completed once `run_info`'s planned jobs of its rules have all ended."""
    run_id = "run_01K8T27SNAKE00000000000000"
    launch_id = add_run(writer, settings, run_id, "mosaic", "running", engine="snakemake")
    main = mosaicatcher_tree(tmp_path)
    pipeline = main.parents[1]
    writer.submit(
        lambda c: c.execute(text("UPDATE workflows SET location = :l"), {"l": str(pipeline)})
    ).result()
    if rules_txt:
        listed = (STAGES / "rules" / f"{MOSAICATCHER}_list-rules.txt").read_bytes()
        with private_dir(settings.runs_root, run_id, "launch", ".spectio", create=True) as fd:
            write_file(
                fd, "rules.txt", listed.replace(b"mosaic_count\n", b"mosaic_count (Count)\n")
            )
    events = [
        smk_event(
            1,
            run_id,
            "workflow_started",
            {"snakefile_main": str(main), "snakemake_version": "9.27.1"},
        ),
        smk_event(2, run_id, "run_info", {"stats": {"save_config": 1, "total": 1}}),
        smk_event(3, run_id, "job_info", {"jobid": 1, "rule_name": "save_config"}),
    ]
    sources = StageSources(overlays, settings.runs_root)
    run = partial(
        ingest, launch_id=launch_id, batch=SpoolBatch(events, {}, Counter()), sources=sources
    )
    writer.submit(run).result()
    rows = writer.submit(
        lambda c: c.execute(
            select(run_stages).where(run_stages.c.run_id == run_id).order_by(run_stages.c.position)
        ).all()
    ).result()
    assert len(rows) == 8 and rows[-1].name == "Final targets"
    stage = {r.stage_id: r.name for r in rows}
    sid = writer.submit(
        lambda c: c.execute(select(tasks.c.stage_id).where(tasks.c.run_id == run_id)).scalar_one()
    ).result()
    assert "Setup" in stage[sid]
    if rules_txt:  # as the golden file
        assert sid == "detected:2" and stage[sid] == "Setup + Utils"
    assert [(r.stage_id, r.state) for r in rows if r.state != "not_started"] == [(sid, "running")]
    events = [smk_event(4, run_id, "job_finished", {"job_id": 1})]
    run = partial(
        ingest, launch_id=launch_id, batch=SpoolBatch(events, {}, Counter()), sources=sources
    )
    writer.submit(run).result()
    rows = writer.submit(
        lambda c: c.execute(
            select(run_stages).where(run_stages.c.run_id == run_id).order_by(run_stages.c.position)
        ).all()
    ).result()
    assert [(r.stage_id, r.state) for r in rows if r.state != "not_started"] == [(sid, "completed")]
    if not rules_txt:  # the source only: the ashleys rules are in a stage too
        assert "Ashleys" in " ".join(r.name for r in rows)


def test_snakemake_main_outside_pipeline(
    settings: Settings, writer: Writer, overlays: Path, tmp_path: Path
) -> None:
    """`snakefile_main` is untrusted (a run from a terminal): outside the run's pipeline
    directory, no detected stages."""
    run_id = "run_01K8T27SNAKE00000000000001"
    launch_id = add_run(writer, settings, run_id, "mosaic", "running", engine="snakemake")
    main = mosaicatcher_tree(tmp_path)  # the run's location stays /pipelines/snakemake
    events = [smk_event(1, run_id, "workflow_started", {"snakefile_main": str(main)})]
    run = partial(
        ingest,
        launch_id=launch_id,
        batch=SpoolBatch(events, {}, Counter()),
        sources=StageSources(overlays, settings.runs_root),
    )
    writer.submit(run).result()
    rows = writer.submit(
        lambda c: c.execute(select(run_stages).where(run_stages.c.run_id == run_id)).all()
    ).result()
    assert rows == []


@pytest.mark.parametrize(
    ("with_overlay", "rebuilt"), [(False, False), (True, False), (False, True)]
)
def test_snakemake_freeze_git_workflow(
    settings: Settings,
    writer: Writer,
    overlays: Path,
    tmp_path: Path,
    with_overlay: bool,
    rebuilt: bool,
) -> None:
    """A workflow imported from Git: its location is the URL, so the pipeline directory is the
    fetched copy the launch ran in (the launch command's `location`); the overlay key is the
    repository's name, not the revision's (CR-P3T27-03). A run of a rebuilt index has no launch
    command: the copy is the one `api.workflows.fetch` wrote for its URL and revision
    (CR-P3T27-04)."""
    run_id = f"run_01K8T27G1T{int(with_overlay)}{int(rebuilt)}{'0' * 14}"
    launch_id = add_run(writer, settings, run_id, "mosaic", "running", engine="snakemake")
    built = mosaicatcher_tree(tmp_path / "built").parents[1]
    fetched = tmp_path / "pipelines" / "github.com" / "lab" / "mosaicatcher-pipeline" / "v2.5.1"
    fetched.parent.mkdir(parents=True)
    built.rename(fetched)
    url = "https://github.com/lab/mosaicatcher-pipeline"

    def as_git(c: Any) -> None:
        c.execute(text("UPDATE workflows SET source = 'git', location = :l"), {"l": url})
        c.execute(text("UPDATE workflow_versions SET revision = 'v2.5.1'"))
        if rebuilt:
            return
        c.execute(
            runner_commands.insert().values(
                id=f"cmd_{run_id}",
                created_at=T0,
                run_id=run_id,
                launch_id=launch_id,
                kind="launch",
                payload={"location": str(fetched), "profiles": [], "params": {}},
                state="pending",
            )
        )

    writer.submit(as_git).result()
    if with_overlay:
        write_overlay(
            overlays,
            "m.spectio.yml",
            "workflow: {name: lab/mosaicatcher-pipeline, engine: snakemake}",
        )
    main = fetched / "workflow" / "Snakefile"
    events = [smk_event(1, run_id, "workflow_started", {"snakefile_main": str(main)})]
    run = partial(
        ingest,
        launch_id=launch_id,
        batch=SpoolBatch(events, {}, Counter()),
        sources=StageSources(overlays, settings.runs_root, tmp_path),
    )
    writer.submit(run).result()
    rows = writer.submit(
        lambda c: c.execute(select(run_stages).where(run_stages.c.run_id == run_id)).all()
    ).result()
    if with_overlay:
        assert rows and {r.source for r in rows} == {"declared"}
    else:
        assert len(rows) == 8 and {r.source for r in rows} == {"detected"}


# --- An older database -----------------------------------------------------------------------


def test_old_database_opens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A database at revision 0004 (before Task 27) is migrated at open, and its runs' processes
    are still listed from their tasks."""
    db_dir = tmp_path / "db"
    db_dir.mkdir(mode=0o700)
    real = alembic_command.upgrade
    with monkeypatch.context() as patch:
        patch.setattr(alembic_command, "upgrade", lambda config, _rev: real(config, "0004"))
        engine, _ = open_db(db_dir)
    with engine.begin() as conn:
        assert "run_processes" not in inspect(conn).get_table_names()
    engine.dispose()
    engine, new = open_db(db_dir)
    with engine.begin() as conn:
        assert "run_processes" in inspect(conn).get_table_names()
    assert new is False
    engine.dispose()
