"""The catalog file (FU-P3-87a; api §5.6, Where entries live; dev-env §15.3 req. 18):
`catalog.toml` next to `environments.toml`, one strict `[pipelines.<name>]` table per entry,
read and written by the code of the environments file (`spectio.envfile`), whose shared tests
run for both files (`test_envfile.py`)."""

import os
from pathlib import Path

import pytest

from spectio import catalog, envfile

GOOD = """[pipelines.rnaseq]
label = "RNA-seq"
engine = "nextflow"
location = "nf-core/rnaseq"
revision = "3.14.0"
profile = "singularity"
params_file = "assets/params.yaml"

[pipelines.mine]
engine = "snakemake"
location = "/srv/pipelines/mine"
"""
GIT = "[pipelines.x]\nengine = 'nextflow'\nlocation = 'nf-core/x'\n"


@pytest.fixture
def path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    monkeypatch.setenv("SPECTIO_CONFIG", str(data / "spectio.toml"))
    return catalog.catalog_path()


def read(path: Path, text: str) -> envfile.File[catalog.Entry]:
    path.write_text(text)
    path.chmod(0o600)
    return envfile.read_kind(catalog.KIND, path, ())


def test_req18_catalog_file_path_is_next_to_environments_toml(path: Path) -> None:
    assert path == envfile.environments_path().parent / "catalog.toml"


def test_req18_catalog_file_ok(path: Path) -> None:
    found = read(path, GOOD)
    assert found.state == "ok" and found.identity is not None
    mine, rnaseq = found.entries
    assert (mine.name, mine.engine, mine.revision) == ("mine", "snakemake", None)
    assert mine.profile is None and rnaseq.profile == "singularity"
    assert rnaseq.location == "nf-core/rnaseq" and rnaseq.params_file == "assets/params.yaml"


@pytest.mark.parametrize(
    "text",
    [
        GIT,  # a Git location without a revision
        "[pipelines.x]\nengine = 'nextflow'\nlocation = '/srv/x'\nrevision = 'v1'\n",
        "[pipelines.x]\nlocation = '/srv/x'\n",  # no engine
        "[pipelines.x]\nengine = 'cwl'\nlocation = '/srv/x'\n",
        "[pipelines.x]\nengine = 'nextflow'\nlocation = '/srv/x'\nqos = 1\n",
        "[pipelines.x]\nengine = 'nextflow'\nlocation = '/srv/x'\nprofile = 'a,b'\n",
        "[pipelines.x]\nengine = 'nextflow'\nlocation = '/srv/x'\nlabel = 'a‮b'\n",
        "[pipelines.new]\nengine = 'nextflow'\nlocation = '/srv/x'\n",  # the screen route
        "[pipelines.X]\nengine = 'nextflow'\nlocation = '/srv/x'\n",
        "default = 'x'\n",  # no default in this file
        "".join(f"[pipelines.p{i}]\nengine = 'nextflow'\nlocation = '/x'\n" for i in range(101)),
        *(
            f"[pipelines.x]\nengine = 'nextflow'\nlocation = '/srv/x'\nparams_file = '{p}'\n"
            for p in ("../p.json", "/p.json", "/".join("a" * 9) + ".json", "p.txt", "a//p.yml")
        ),
    ],
)
def test_req18_catalog_file_invalid(path: Path, text: str) -> None:
    found = read(path, text)
    assert found.state == "invalid" and found.entries == ()
    assert found.detail and len(found.detail) <= 200


@pytest.mark.parametrize(
    ("location", "revision"),
    [
        ("/srv/x\x1bSECRET", None),
        ("SECRET" + "x" * 4096, "v1"),
        ("http://example.org/SECRET", "v1"),
        ("file:///srv/SECRET", "v1"),
        ("https://user:SECRET@example.org/x", "v1"),
        ("https://SECRET@example.org/x", "v1"),
        ("https://example.org:SECRET/x", "v1"),  # urlsplit's message quotes the port
        ("https://example.org/../SECRET", "v1"),
        ("https://example.org/a b SECRET", "v1"),
        ("nf-core/x", "-SECRET"),
        ("nf-core/x", "SECRET/../x"),
        ("nf-core/x", "SECRET‮"),
        ("nf-core/x", "SECRET/"),
    ],
)
def test_req18_catalog_file_bad_value_invalid(
    path: Path, location: str, revision: str | None
) -> None:
    """A refused location or revision written by hand makes the file `invalid`, never an
    exception, and the detail never quotes it (SEC-PRE-FU87-02)."""
    rev = "" if revision is None else f"revision = {revision!r}\n".replace("'", '"')
    escaped = location.replace("\\", "\\\\").replace("\x1b", "\\u001b")
    found = read(path, f'[pipelines.x]\nengine = "nextflow"\nlocation = "{escaped}"\n{rev}')
    assert found.state == "invalid" and found.detail
    assert "SECRET" not in found.detail and found.detail.startswith("pipelines.x")


def test_req18_catalog_file_write_round_trip(path: Path) -> None:
    entries = list(read(path, GOOD).entries)
    written = envfile.update_kind(catalog.KIND, path, (), lambda current: (None, entries[:1]))
    assert written.state == "ok" and written.entries == tuple(entries[:1])
    assert envfile.read_kind(catalog.KIND, path, ()).entries == tuple(entries[:1])
    assert [p.name for p in path.parent.iterdir()] == ["catalog.toml"]
    assert os.stat(path).st_mode & 0o777 == 0o600
