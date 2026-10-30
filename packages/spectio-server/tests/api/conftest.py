"""Fixtures of the API tests (P1 Tasks 17 and 18).

`authed_client` is a plain TestClient for now: sign-in (P1 Tasks 12 to 16) is not built, and the
API is served in local mode only (inbox #86). Task 16 makes this fixture sign in, and the tests
that use it keep their name.
"""

import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from spectio.config import Settings
from spectio_server.app import create_app
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.store.db import open_db
from spectio_server.store.writer import Writer

SYNTHETIC = Path(__file__).resolve().parents[4] / "tests" / "pipelines" / "synthetic"
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


def client_for(settings: Settings, writer: Writer) -> TestClient:
    app = create_app(settings, writer)
    app.state.engine_versions = lambda: dict(ENGINE_VERSIONS)  # no login shell in the tests
    return TestClient(app)


@pytest.fixture
def authed_client(settings: Settings, writer: Writer) -> TestClient:
    return client_for(settings, writer)


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
