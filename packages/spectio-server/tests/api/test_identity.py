"""A pipeline's identity beyond the Nextflow manifest (#400): the name of a Git location from
the URL's path, the version from a `VERSION` file or the revision's tag, and `version_source`
saying which one gave it."""

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from spectio_server.api import workflows as wf
from spectio_server.store.schema import workflow_versions, workflows
from spectio_server.store.writer import Writer

from .conftest import git

INSPECT = "/api/v1/workflows:inspect"
RUNS = "/api/v1/runs"


class FakeGit:
    """Records each git argv; a clone leaves a Snakemake pipeline behind."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> Any:
        assert isinstance(argv, list)
        self.calls.append(argv)
        if "clone" in argv:
            target = Path(argv[-1])
            target.mkdir(parents=True)
            (target / "Snakefile").write_text("\n")
        return subprocess.CompletedProcess(argv, 0, "", "")


@pytest.fixture
def fake_git(monkeypatch: pytest.MonkeyPatch) -> FakeGit:
    fake = FakeGit()
    monkeypatch.setattr(wf, "run_git", fake)
    return fake


@pytest.fixture
def make_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[..., Path]:
    """A local repository `<tmp>/repos/example-org/pipeline` with a Snakemake pipeline and the
    given files, committed and tagged: identity comes from the URL, a `VERSION` file or the tag
    (#400). Git is read as a `file://` URL, as a test alone allows."""

    monkeypatch.setattr(wf, "GIT_SCHEMES", ("https", "ssh", "file"))

    def make(files: dict[str, str], tag: str = "v2.1") -> Path:
        repo = tmp_path / "repos" / "example-org" / "pipeline"
        repo.mkdir(parents=True)
        (repo / "Snakefile").write_text("\n")
        for name, text in files.items():
            (repo / name).write_text(text)
        git("init", "-q", "-b", "main", cwd=repo)
        git("add", ".", cwd=repo)
        git("commit", "-q", "-m", "first", cwd=repo)
        git("tag", tag, cwd=repo)
        return repo

    return make


def inspect(authed_client: TestClient, location: str, revision: str) -> Any:
    body = authed_client.get(INSPECT, params={"location": location, "revision": revision})
    assert body.status_code == 200, body.text
    return body.json()


def launch(client: TestClient, location: str, engine: str, **body: Any) -> Any:
    workflow = {"location": location, "engine": engine}
    if "revision" in body:
        workflow["revision"] = body.pop("revision")
    return client.post(RUNS, json={"workflow": workflow, "params": {}, **body})


def table(writer: Writer, t: Any) -> list[Any]:
    return writer.submit(lambda c: list(c.execute(select(t)).all())).result()


# --- Name ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("location", "name"),
    [
        ("https://gitlab.com/example-org/pipeline.git", "example-org/pipeline"),
        ("ssh://git@gitlab.com/example-org/pipeline.git", "example-org/pipeline"),
        ("https://github.com/example-org/pipeline", "example-org/pipeline"),
        ("example-org/pipeline", "example-org/pipeline"),  # the short name (GitHub)
        ("https://gitlab.com/example-org/group/pipeline", "group/pipeline"),  # the last two parts
        ("https://example.com/pipeline", "pipeline"),  # one path part: the repository's name
    ],
)
def test_git_name_comes_from_the_url_path(
    authed_client: TestClient, fake_git: FakeGit, location: str, name: str
) -> None:
    assert inspect(authed_client, location, "v1")["name"] == name


def test_local_directory_keeps_its_name_and_version(
    authed_client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "pipeline"
    root.mkdir()
    (root / "Snakefile").write_text("\n")
    (root / "VERSION").write_text("1.2.3\n")  # a VERSION is read at a repository's root only
    found = authed_client.get(INSPECT, params={"location": str(root)}).json()
    assert (found["name"], found["version"], found["version_source"]) == ("pipeline", None, None)


# --- Version ---------------------------------------------------------------------------------


def test_version_comes_from_the_revision_tag(
    authed_client: TestClient, make_repo: Callable[..., Path]
) -> None:
    repo = make_repo({})
    found = inspect(authed_client, repo.as_uri(), "v2.1")
    assert (found["name"], found["version"], found["version_source"]) == (
        "example-org/pipeline",
        "2.1",
        "tag",
    )


def test_version_tag_without_the_v(
    authed_client: TestClient, make_repo: Callable[..., Path]
) -> None:
    repo = make_repo({}, tag="release")
    found = inspect(authed_client, repo.as_uri(), "release")
    assert (found["version"], found["version_source"]) == ("release", "tag")


def test_version_annotated_tag(authed_client: TestClient, make_repo: Callable[..., Path]) -> None:
    repo = make_repo({})
    git("tag", "-a", "v3.0", "-m", "x", cwd=repo)
    found = inspect(authed_client, repo.as_uri(), "v3.0")
    assert (found["version"], found["version_source"]) == ("3.0", "tag")


def test_version_branch_is_not_a_tag(
    authed_client: TestClient, make_repo: Callable[..., Path]
) -> None:
    repo = make_repo({})
    found = inspect(authed_client, repo.as_uri(), "main")
    assert (found["version"], found["version_source"]) == (None, None)


def test_version_comes_from_the_file(
    authed_client: TestClient, make_repo: Callable[..., Path]
) -> None:
    repo = make_repo({"VERSION": "2.1.0\n"})
    found = inspect(authed_client, repo.as_uri(), "v2.1")
    assert (found["version"], found["version_source"]) == ("2.1.0", "file")


def test_version_file_first_line_stripped(
    authed_client: TestClient, make_repo: Callable[..., Path]
) -> None:
    repo = make_repo({"VERSION": "  1.2.3  \nsecond line\n"})
    found = inspect(authed_client, repo.as_uri(), "v2.1")
    assert (found["version"], found["version_source"]) == ("1.2.3", "file")


@pytest.mark.parametrize(
    "text",
    ["9" * 65, "1.0 beta\n", "\n"],  # too long  # not of [0-9A-Za-z._+-]  # an empty first line
)
def test_version_file_that_is_not_a_version_falls_to_the_tag(
    authed_client: TestClient, make_repo: Callable[..., Path], text: str
) -> None:
    repo = make_repo({"VERSION": text})
    found = inspect(authed_client, repo.as_uri(), "v2.1")
    assert (found["version"], found["version_source"]) == ("2.1", "tag")


def test_version_file_symlink_is_not_read(
    authed_client: TestClient, make_repo: Callable[..., Path]
) -> None:
    """A symlinked `VERSION` counts as absent, as every file inspect reads (dev-env §15.3
    req. 13): the tag names the version."""
    repo = make_repo({"VERSION": "9.9.9\n"}, tag="keep")
    (repo / "VERSION").unlink()
    (repo / "elsewhere").write_text("9.9.9\n")
    (repo / "VERSION").symlink_to("elsewhere")
    git("add", ".", cwd=repo)
    git("commit", "-q", "-m", "symlink", cwd=repo)
    git("tag", "v2.1", cwd=repo)
    found = inspect(authed_client, repo.as_uri(), "v2.1")
    assert (found["version"], found["version_source"]) == ("2.1", "tag")


def test_manifest_wins_over_file_and_tag(
    authed_client: TestClient, make_repo: Callable[..., Path]
) -> None:
    repo = make_repo(
        {
            "nextflow.config": "manifest {\n    name = 'example-org/pipeline'\n"
            "    version = '9.9.9'\n}\n",
            "VERSION": "1.0\n",
        }
    )
    found = inspect(authed_client, repo.as_uri(), "v2.1")
    assert (found["name"], found["version"], found["version_source"]) == (
        "example-org/pipeline",
        "9.9.9",
        "manifest",
    )


# --- The run keeps it ------------------------------------------------------------------------


def test_launch_stores_a_git_pipeline_identity(
    authed_client: TestClient, make_repo: Callable[..., Path], writer: Writer
) -> None:
    repo = make_repo({"VERSION": "2.1.0\n"})
    response = launch(authed_client, repo.as_uri(), "snakemake", revision="v2.1")
    assert response.status_code == 201, response.text
    run = response.json()
    assert (run["workflow"]["name"], run["workflow"]["version"]) == (
        "example-org/pipeline",
        "2.1.0",
    )
    (row,) = table(writer, workflows)
    assert (row.name, row.source, row.location) == ("example-org/pipeline", "git", repo.as_uri())
    (version,) = table(writer, workflow_versions)
    assert (version.version, version.version_source) == ("2.1.0", "file")


def test_launch_stores_the_manifest_source(
    authed_client: TestClient, tmp_path: Path, writer: Writer
) -> None:
    root = tmp_path / "nf"
    root.mkdir()
    (root / "main.nf").write_text("\n")
    (root / "nextflow.config").write_text("manifest { version = '0.1.0' }\n")
    response = launch(authed_client, str(root), "nextflow")
    assert response.status_code == 201, response.text
    (version,) = table(writer, workflow_versions)
    assert (version.version, version.version_source) == ("0.1.0", "manifest")


def test_launch_stores_no_source_without_a_version(
    authed_client: TestClient, tmp_path: Path, writer: Writer
) -> None:
    plain = tmp_path / "smk"
    plain.mkdir()
    (plain / "Snakefile").write_text("\n")
    response = launch(authed_client, str(plain), "snakemake")
    assert response.status_code == 201, response.text
    (version,) = table(writer, workflow_versions)
    assert (version.version, version.version_source) == (None, None)
