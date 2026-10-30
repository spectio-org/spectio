"""Fixtures of the API tests (P1 Tasks 17 and 18).

`authed_client` is a TestClient on `http://127.0.0.1:<port>` with that Origin (dev-env §15.3 req. 4
and 7), with no session for now: sign-in (P1 Tasks 12 to 16) is not built, and the
API is served in local mode only (inbox #86). Task 16 makes this fixture sign in, and the tests
that use it keep their name. `client` is the same app on a machine that looks shared, so its
API is not mounted (TODO(P1 Task 16): a client with no session cookie, answered 401).
"""

import shutil
import subprocess
from collections.abc import Iterator
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, update

from spectio.config import Settings
from spectio.runner.rundir import RunManifest, Workflow
from spectio.runner.spool import read_spool
from spectio_server import app as app_mod
from spectio_server.app import create_app
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.projector.ingest import ingest
from spectio_server.store.db import open_db
from spectio_server.store.runs import insert_run
from spectio_server.store.schema import run_stages, runs, tasks
from spectio_server.store.writer import Writer

SYNTHETIC = Path(__file__).resolve().parents[4] / "tests" / "pipelines" / "synthetic"
FIXTURES = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "engine-events"
FLAKY_RUN = "run_01K8T2F1XTVRES000000000000"  # the run of every converted T2 fixture
ENGINE_VERSIONS = {"nextflow": "26.10.4", "snakemake": "9.27.1"}


@pytest.fixture
def writer(settings: Settings) -> Iterator[Writer]:
    assert settings.db_dir is not None
    engine, _ = open_db(settings.db_dir)
    writer = Writer(engine)
    config = {"runs_root": str(settings.runs_root)}
    writer.submit(lambda c: ensure_tenancy(c, "me", settings.executor, config, "0.0.1")).result()
    yield writer
    writer.close()
    engine.dispose()


def client_for(settings: Settings, writer: Writer, web_dir: Path | None = None) -> TestClient:
    """`web_dir` is the built screens (P1 Task 19); none by default, so `/` is the plain page."""
    app = create_app(settings, writer, web_dir=web_dir or Path("/nonexistent/web/dist"))
    app.state.engine_versions = lambda: dict(ENGINE_VERSIONS)  # no login shell in the tests
    origin = f"http://127.0.0.1:{settings.port}"  # what a browser on the loopback sends (req. 4, 7)
    return TestClient(app, base_url=origin, headers={"Origin": origin})


@pytest.fixture
def authed_client(settings: Settings, writer: Writer) -> TestClient:
    return client_for(settings, writer)


@pytest.fixture
def client(settings: Settings, writer: Writer, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """The app on a machine that looks shared: no `/api/v1` route is mounted (inbox #86)."""
    with monkeypatch.context() as patch:  # create_app decides once: the others stay lone
        patch.setattr(app_mod, "shared_host", lambda: "a process of uid 1001 runs here")
        return client_for(settings, writer)


def add_run(
    writer: Writer,
    settings: Settings,
    run_id: str,
    name: str,
    state: str = "queued",
    *,
    engine: str = "nextflow",
    created_at: datetime | None = None,
    **values: Any,
) -> str:
    """A run and its launch 1, as `POST /runs` writes them, then `values` set on the run.
    Returns the launch's ID."""
    manifest = RunManifest(
        run_id=run_id,
        name=name,
        workflow=Workflow.model_validate({"location": f"/pipelines/{engine}", "engine": engine}),
        params={"reads": 4},
        profiles=[],
        created_at=created_at or datetime.now(UTC),
    )

    def write(conn: Any) -> str:
        launch_id = insert_run(
            conn,
            manifest,
            source="local",
            runs_root=settings.runs_root,
            now=manifest.created_at,
            state=state,
            origin="ui",
            workflow_name=f"lab/{engine}",
            workflow_version="1.2.0" if engine == "nextflow" else None,
        )
        if values:
            conn.execute(update(runs).where(runs.c.id == run_id).values(**values))
        return launch_id

    return writer.submit(write).result()


def replay(writer: Writer, tmp_path: Path, launch_id: str, fixture: str, run_id: str) -> None:
    """A T2 fixture read through the real spool reader and ingested, batch by batch."""
    launch_dir = tmp_path / "spool-launch"
    (launch_dir / ".spectio" / "events").mkdir(mode=0o700, parents=True)
    (launch_dir / ".spectio").chmod(0o700)
    target = launch_dir / ".spectio" / "events" / "nf-spectio-1-0001.jsonl"
    shutil.copyfile(FIXTURES / fixture, target)
    target.chmod(0o600)
    cursor: dict[str, int] = {}
    while (batch := read_spool(launch_dir, run_id, 1, cursor, max_lines=100)).events:
        writer.submit(partial(ingest, launch_id=launch_id, batch=batch)).result()
        cursor = batch.cursor


@pytest.fixture
def replayed_flaky(settings: Settings, writer: Writer, tmp_path: Path) -> str:
    """The T2 `flaky` run of Nextflow 26.10.4, launched from the UI and replayed: no head report,
    so its head is unknown."""
    launch_id = add_run(writer, settings, FLAKY_RUN, "rnaseq-flaky")
    replay(writer, tmp_path, launch_id, "nextflow-26.10.4_plugin_flaky.spool.jsonl", FLAKY_RUN)
    return FLAKY_RUN


SEEDED_RUN = "run_01K8T2F1XTVRES000000000001"


@pytest.fixture
def seeded_stages(settings: Settings, writer: Writer) -> str:
    """A run with two stages and three processes, written directly (P1 Task 27 fills them)."""
    add_run(writer, settings, SEEDED_RUN, "rnaseq-staged", "running")
    now = datetime.now(UTC)

    def write(conn: Any) -> None:
        for stage_id, position, name, source, state in (
            ("align", 2, "Align", "declared", "not_started"),
            ("detected:1", 1, "Quality control", "detected", "running"),
        ):
            conn.execute(
                insert(run_stages).values(
                    id=f"stg_{position}",
                    created_at=now,
                    run_id=SEEDED_RUN,
                    stage_id=stage_id,
                    position=position,
                    name=name,
                    source=source,
                    state=state,
                    task_counts={"running": 1} if state == "running" else {},
                )
            )
        processes: tuple[tuple[str, str | None], ...] = (
            ("NFCORE_RNASEQ:RNASEQ:FASTQC", "detected:1"),
            ("NFCORE_RNASEQ:RNASEQ:ALIGN:STAR", "align"),
            ("NFCORE_RNASEQ:RNASEQ:MULTIQC", None),
        )
        for i, (process, stage) in enumerate(processes):
            conn.execute(
                insert(tasks).values(
                    id=f"tsk_0{i}",
                    created_at=now,
                    run_id=SEEDED_RUN,
                    process_or_rule=process,
                    tag="S1",
                    state="running" if i == 0 else "not_scheduled",
                    stage_id=stage,
                )
            )

    writer.submit(write).result()
    return SEEDED_RUN


@pytest.fixture
def synthetic() -> Path:
    return SYNTHETIC


def git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.org", *args],  # noqa: S607
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A local repository `<tmp>/repos/lab/hello` with a Nextflow pipeline, tagged v1.0."""
    repo = tmp_path / "repos" / "lab" / "hello"
    repo.mkdir(parents=True)
    (repo / "main.nf").write_text("workflow { println 'hello' }\n")
    (repo / "nextflow.config").write_text(
        "manifest {\n    name = 'lab/hello'\n    version = '1.0'\n}\n"
        "profiles {\n    local { executor.name = 'local' }\n}\n"
    )
    git("init", "-q", "-b", "main", cwd=repo)
    git("add", ".", cwd=repo)
    git("commit", "-q", "-m", "first", cwd=repo)
    git("tag", "v1.0", cwd=repo)
    return repo


@pytest.fixture(autouse=True)
def lone_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """The API tests run as on one person's machine, whatever the test host is (SEC-P3T17-06)."""
    monkeypatch.setattr(app_mod, "shared_host", lambda: None)
