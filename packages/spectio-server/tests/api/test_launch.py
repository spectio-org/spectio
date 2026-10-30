"""`GET /workflows:inspect` and `POST /runs` (P1 Task 17, Assumption 2; G5 of P2 §10.6)."""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import select

from spectio.config import Settings
from spectio.runner import loop
from spectio.runner.engines import EngineInfo
from spectio.runner.loop import LaunchPayload
from spectio.runner.rundir import read_run_manifest, run_paths
from spectio.runner.types import HeadReport, LaunchSpec
from spectio_server import app as app_mod
from spectio_server.api import workflows as wf
from spectio_server.serve import start_text
from spectio_server.sink import StoreSink
from spectio_server.store.schema import (
    launches,
    run_inputs,
    runner_commands,
    runs,
    workflow_versions,
    workflows,
)
from spectio_server.store.writer import Writer

from .conftest import ENGINE_VERSIONS, client_for, git

DATA = Path(__file__).resolve().parents[1] / "data"
INSPECT = "/api/v1/workflows:inspect"
RUNS = "/api/v1/runs"
PROTOCOL_FLAGS = [
    "-c",
    "protocol.allow=never",
    "-c",
    "protocol.https.allow=always",
    "-c",
    "protocol.ssh.allow=always",
]


def fields(response: Any) -> list[str]:
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["type"] == "/problems/validation-failed"
    assert response.headers["content-type"].startswith("application/problem+json")
    return [e["field"] for e in body["errors"]]


def launch(client: TestClient, location: str, engine: str, **body: Any) -> Any:
    workflow = {"location": location, "engine": engine}
    if "revision" in body:
        workflow["revision"] = body.pop("revision")
    return client.post(RUNS, json={"workflow": workflow, "params": {}, **body})


def table(writer: Writer, t: Any) -> list[Any]:
    return writer.submit(lambda c: list(c.execute(select(t)).all())).result()


def pipeline(tmp_path: Path, *files: str, schema: str | None = None, to: str = "") -> Path:
    """A pipeline directory with these entry files and, optionally, a schema file at `to`."""
    root = tmp_path / "pipeline"
    for name in files:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("\n")
    root.mkdir(exist_ok=True)
    if schema is not None:
        (root / to).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(DATA / schema, root / to)
    return root


class FakeGit:
    """Records each git argv; a clone or a checkout leaves a Nextflow pipeline behind."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> Any:
        assert isinstance(argv, list)
        self.calls.append(argv)
        if "clone" in argv:
            target = Path(argv[-1])
            target.mkdir(parents=True)
            (target / "main.nf").write_text("\n")
        return subprocess.CompletedProcess(argv, 0, "", "")


@pytest.fixture
def fake_git(monkeypatch: pytest.MonkeyPatch) -> FakeGit:
    fake = FakeGit()
    monkeypatch.setattr(wf, "run_git", fake)
    return fake


# --- Inspect ---------------------------------------------------------------------------------


def test_inspect_detects_engines(authed_client: TestClient, synthetic: Path) -> None:
    nf = authed_client.get(INSPECT, params={"location": str(synthetic / "nextflow")})
    assert nf.status_code == 200, nf.text
    body = nf.json()
    assert body["engine"] == "nextflow"
    assert body["engine_files"] == ["main.nf"]
    assert body["schema_source"] == "none" and body["schema"] is None
    assert (body["name"], body["version"]) == ("spectio/synthetic-scenarios", "0.1.0")
    assert {"local", "slurm", "test"} <= set(body["profiles"])
    assert body["engine_version"] == ENGINE_VERSIONS["nextflow"]
    assert body["engine_versions"] == ENGINE_VERSIONS  # UX-G2-04: the other engine's too
    assert (body["location"], body["revision"]) == (str(synthetic / "nextflow"), None)

    smk = authed_client.get(INSPECT, params={"location": str(synthetic / "snakemake")}).json()
    assert smk["engine"] == "snakemake"
    assert smk["engine_files"] == ["workflow/Snakefile"]
    assert smk["profiles"] == ["local", "slurm"]
    assert smk["version"] is None  # Snakemake declares none [to be validated]
    assert smk["engine_version"] == ENGINE_VERSIONS["snakemake"]


@pytest.mark.parametrize(
    ("schema", "to", "source", "group"),
    [
        ("nf_schema_defs.json", "nextflow_schema.json", "nextflow_schema.json", "$defs"),
        ("nf_schema_definitions.json", "nextflow_schema.json", "nextflow_schema.json", None),
        ("smk_config.schema.yaml", "config.schema.yaml", "config.schema.yaml", None),
        (
            "smk_config.schema.yaml",
            "workflow/schemas/config.schema.yaml",
            "config.schema.yaml",
            None,
        ),
    ],
)
def test_inspect_reads_schemas(
    authed_client: TestClient,
    tmp_path: Path,
    schema: str,
    to: str,
    source: str,
    group: str | None,
) -> None:
    root = pipeline(tmp_path, "main.nf", schema=schema, to=to)
    body = authed_client.get(INSPECT, params={"location": str(root)}).json()
    assert body["schema_source"] == source
    raw = (DATA / schema).read_text()
    assert body["schema"] == (json.loads(raw) if schema.endswith(".json") else yaml.safe_load(raw))
    groups = body["schema"].get("$defs") or body["schema"].get("definitions")
    if schema.startswith("nf_"):  # $defs (2020-12) and definitions (draft 7): two groups each
        assert [g["title"] for g in groups.values()] == ["Input/output", "Options"]
    else:
        assert body["schema"]["properties"]["chunks"]["type"] == "integer"


def test_inspect_infers_types_from_config(authed_client: TestClient, tmp_path: Path) -> None:
    root = pipeline(tmp_path, "Snakefile", schema="smk_config.yaml", to="config/config.yaml")
    body = authed_client.get(INSPECT, params={"location": str(root)}).json()
    assert body["schema_source"] == "inferred"
    props = body["schema"]["properties"]
    assert {k: v.get("type") for k, v in props.items()} == {
        "outdir": "string",
        "chunks": "integer",
        "scale": "number",
        "dry": "boolean",
        "samples": "array",
        "resources": "object",
        "nothing": None,
    }
    assert props["chunks"]["default"] == 0


@pytest.mark.parametrize(
    "location",
    ["./relative/dir", "pipeline", "/nonexistent/spectio/pipeline", "/etc/hostname", ""],
)
def test_inspect_refuses_relative_or_missing(authed_client: TestClient, location: str) -> None:
    assert fields(authed_client.get(INSPECT, params={"location": location})) == ["location"]


def test_inspect_needs_a_location(authed_client: TestClient) -> None:
    assert fields(authed_client.get(INSPECT)) == ["location"]


def test_inspect_ambiguous_engine_no_guess(authed_client: TestClient, tmp_path: Path) -> None:
    both = pipeline(tmp_path, "main.nf", "workflow/Snakefile")
    body = authed_client.get(INSPECT, params={"location": str(both)}).json()
    assert body["engine"] is None and body["engine_version"] is None
    assert body["engine_files"] == ["main.nf", "workflow/Snakefile"]  # "both found"
    neither = tmp_path / "empty"
    neither.mkdir()
    body = authed_client.get(INSPECT, params={"location": str(neither)}).json()
    assert body["engine"] is None and body["engine_files"] == []  # "neither found"
    assert body["engine_versions"] == ENGINE_VERSIONS


# --- Launch ----------------------------------------------------------------------------------


def test_launch_creates_run_and_command(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    location = str(synthetic / "nextflow")
    response = launch(authed_client, location, "nextflow", profiles=["local"], params={"chunks": 2})
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["state"] == "queued"
    assert response.headers["location"] == f"/api/v1/runs/{run['id']}"
    assert run["name"] == f"spectio/synthetic-scenarios-{run['id'][-6:]}"
    assert run["workflow"] == {
        "location": location,
        "revision": None,
        "engine": "nextflow",
        "name": "spectio/synthetic-scenarios",
        "version": "0.1.0",
    }
    assert (run["profiles"], run["params"]) == (["local"], {"chunks": 2})

    (row,) = table(writer, runs)
    assert (row.id, row.state, row.origin) == (run["id"], "queued", "ui")
    paths = run_paths(settings.runs_root, run["id"])
    assert (row.launch_dir, row.work_dir) == (str(paths.launch_dir), str(paths.work_dir))
    manifest = read_run_manifest(paths.run_dir)  # written before the rows (Assumption 21)
    assert (manifest.name, manifest.workflow.location) == (run["name"], location)
    assert (manifest.params, manifest.profiles) == ({"chunks": 2}, ["local"])
    (inputs,) = table(writer, run_inputs)
    assert (inputs.kind, inputs.content) == ("params", {"chunks": 2})
    (workflow,) = table(writer, workflows)
    assert (workflow.source, workflow.location, workflow.engine) == ("local", location, "nextflow")
    assert len(table(writer, workflow_versions)) == 1
    (launch_row,) = table(writer, launches)
    (command,) = table(writer, runner_commands)
    assert (command.kind, command.state, command.launch_id) == ("launch", "pending", launch_row.id)

    (leased,) = StoreSink(writer, settings.runs_root).lease_commands()  # what the runner gets
    assert leased.launch.engine == "nextflow"
    assert LaunchPayload.model_validate(leased.payload) == LaunchPayload(
        location=location, profiles=["local"], params={"chunks": 2}
    )


def test_launch_validates_params(
    authed_client: TestClient, tmp_path: Path, settings: Settings, writer: Writer
) -> None:
    root = pipeline(tmp_path, "main.nf", schema="nf_schema_defs.json", to="nextflow_schema.json")
    bad = {"outdir": "results", "chunks": "x"}
    response = launch(authed_client, str(root), "nextflow", params=bad)
    assert fields(response)[0] == "params.chunks"
    assert fields(launch(authed_client, str(root), "nextflow")) == ["params.outdir"]  # required
    assert table(writer, runs) == [] and list(settings.runs_root.iterdir()) == []
    ok = launch(authed_client, str(root), "nextflow", params={"outdir": "out", "chunks": 3})
    assert ok.status_code == 201, ok.text


def test_launch_draft7_schema(authed_client: TestClient, tmp_path: Path) -> None:
    root = pipeline(
        tmp_path, "main.nf", schema="nf_schema_definitions.json", to="nextflow_schema.json"
    )
    bad = {"outdir": "results", "fail_mode": "maybe"}
    assert fields(launch(authed_client, str(root), "nextflow", params=bad)) == ["params.fail_mode"]


def test_launch_engine_file_missing_422(authed_client: TestClient, synthetic: Path) -> None:
    response = launch(authed_client, str(synthetic / "nextflow"), "snakemake")
    assert fields(response) == ["workflow.engine"]


def test_launch_snakemake_accepted(
    authed_client: TestClient, synthetic: Path, writer: Writer
) -> None:
    """Accepted here; the runner fails it `launch_error` until the logger (P1 Task 7)."""
    location = str(synthetic / "snakemake")
    response = launch(authed_client, location, "snakemake", profiles=["local"])
    assert response.status_code == 201, response.text
    two = launch(authed_client, location, "snakemake", profiles=["local", "slurm"])
    assert fields(two) == ["profiles"]  # a Snakemake launch takes one profile
    (workflow,) = table(writer, workflows)
    assert workflow.engine == "snakemake"


def test_launch_one_engine_per_location(authed_client: TestClient, tmp_path: Path) -> None:
    both = str(pipeline(tmp_path, "main.nf", "Snakefile"))
    assert launch(authed_client, both, "nextflow").status_code == 201
    assert fields(launch(authed_client, both, "snakemake")) == ["workflow.engine"]


@pytest.mark.parametrize(
    "body",
    [
        {"profiles": ["a,b"]},
        {"profiles": ["-x"]},
        {"name": "x\ny"},
        {"name": ""},
        {"surprise": 1},
    ],
)
def test_launch_refuses_bad_fields(
    authed_client: TestClient, synthetic: Path, body: dict[str, Any]
) -> None:
    response = launch(authed_client, str(synthetic / "nextflow"), "nextflow", **body)
    (field,) = fields(response)
    assert field.split(".")[0] == next(iter(body))


def test_launch_refuses_unknown_engine(authed_client: TestClient, synthetic: Path) -> None:
    assert fields(launch(authed_client, str(synthetic / "nextflow"), "cwl")) == ["workflow.engine"]


@pytest.mark.parametrize("location", ["/srv/a\x00b", "/srv/a\nb", "/srv/\x1b[2Ja", "/srv/a\x7f"])
def test_location_control_characters_refused(
    authed_client: TestClient, fake_git: FakeGit, location: str
) -> None:
    """SEC-P3T09-R5-05: NUL and control characters never reach the runner."""
    assert fields(launch(authed_client, location, "nextflow")) == ["workflow.location"]
    assert fields(authed_client.get(INSPECT, params={"location": location})) == ["location"]
    assert fake_git.calls == []


# --- Git (G5) --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "file:///srv/git/pipeline.git",
        "ext::sh -c touch% /tmp/pwned",
        "git://github.com/nf-core/rnaseq",
        "./pipelines/rnaseq",
        "../rnaseq.git",
        "https://user:token@github.com/nf-core/rnaseq",
        "git@github.com:nf-core/rnaseq.git",
        "https://github.com/nf-core/../../etc",
    ],
)
def test_git_url_refused_schemes(authed_client: TestClient, fake_git: FakeGit, url: str) -> None:
    assert fields(launch(authed_client, url, "nextflow", revision="v1")) == ["workflow.location"]
    response = authed_client.get(INSPECT, params={"location": url, "revision": "v1"})
    assert fields(response) == ["location"]  # UX-G2-14: Load reaches inspect first
    assert fake_git.calls == []


def test_git_clone_argv(authed_client: TestClient, fake_git: FakeGit, settings: Settings) -> None:
    url = "https://gitlab.example.org/lab/sub/pipeline.git"
    response = authed_client.get(INSPECT, params={"location": url, "revision": "v2.1"})
    assert response.status_code == 200, response.text
    (argv,) = fake_git.calls
    target = settings.data_dir / "pipelines" / "gitlab.example.org" / "lab" / "sub" / "pipeline"
    assert argv[0] == "git" and argv[1:7] == PROTOCOL_FLAGS
    assert argv[7:] == ["clone", "--depth", "1", "--branch", "v2.1", "--", url, argv[-1]]
    assert Path(argv[-1]).parent == target  # a temporary name, renamed to the revision
    assert (target / "v2.1" / "main.nf").is_file()


def test_git_commit_is_fetched(authed_client: TestClient, fake_git: FakeGit) -> None:
    sha = "0123456789abcdef0123456789abcdef01234567"
    url = "https://github.com/lab/pipeline"

    def fetch(argv: list[str]) -> Any:
        fake_git.calls.append(argv)
        if "init" in argv:
            Path(argv[-1]).mkdir()
        if "checkout" in argv:
            (Path(argv[argv.index("-C") + 1]) / "main.nf").write_text("\n")
        return subprocess.CompletedProcess(argv, 0, "", "")

    wf.run_git = fetch  # restored by the fixture's monkeypatch
    response = authed_client.get(INSPECT, params={"location": url, "revision": sha})
    assert response.status_code == 200, response.text
    verbs = [
        next(a for a in argv[7:] if a in ("init", "fetch", "checkout")) for argv in fake_git.calls
    ]
    assert verbs == ["init", "fetch", "checkout"]
    assert fake_git.calls[1][-3:] == ["--", url, sha]
    assert all(argv[1:7] == PROTOCOL_FLAGS for argv in fake_git.calls)


@pytest.mark.parametrize("revision", ["--upload-pack=touch /tmp/x", "-b", "a..b", "v1\n", None])
def test_git_revision_not_an_option(
    authed_client: TestClient, fake_git: FakeGit, revision: str | None
) -> None:
    url = "https://github.com/nf-core/rnaseq"
    body = {} if revision is None else {"revision": revision}
    assert fields(launch(authed_client, url, "nextflow", **body)) == ["workflow.revision"]
    params = {"location": url, **body}
    assert fields(authed_client.get(INSPECT, params=params)) == ["revision"]
    assert fake_git.calls == []


def test_git_short_name(authed_client: TestClient, fake_git: FakeGit, writer: Writer) -> None:
    body = authed_client.get(INSPECT, params={"location": "nf-core/rnaseq", "revision": "3.14.0"})
    assert body.status_code == 200, body.text
    assert body.json()["location"] == "https://github.com/nf-core/rnaseq"
    assert fake_git.calls[0][-2] == "https://github.com/nf-core/rnaseq"
    response = launch(authed_client, "nf-core/rnaseq", "nextflow", revision="3.14.0")
    assert response.status_code == 201, response.text
    assert len(fake_git.calls) == 1  # fetched once per revision
    (workflow,) = table(writer, workflows)
    assert (workflow.source, workflow.location) == ("git", "https://github.com/nf-core/rnaseq")
    (version,) = table(writer, workflow_versions)
    assert version.revision == "3.14.0"


def test_git_location_fetched_once(
    authed_client: TestClient,
    git_repo: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wf, "GIT_SCHEMES", ("https", "ssh", "file"))  # this test alone
    calls: list[list[str]] = []
    real = wf.run_git

    def recorded(argv: list[str]) -> Any:
        assert isinstance(argv, list)  # an argument list, never a shell string
        calls.append(argv)
        return real(argv)

    monkeypatch.setattr(wf, "run_git", recorded)
    url = git_repo.as_uri()
    inspected = authed_client.get(INSPECT, params={"location": url, "revision": "v1.0"})
    assert inspected.status_code == 200, inspected.text
    assert (inspected.json()["engine"], inspected.json()["version"]) == ("nextflow", "1.0")
    response = launch(authed_client, url, "nextflow", revision="v1.0")
    assert response.status_code == 201, response.text
    assert len(calls) == 1 and "clone" in calls[0]
    assert "protocol.file.allow=always" in calls[0]
    clone = settings.data_dir / "pipelines" / "local" / Path(*git_repo.parts[1:]) / "v1.0"
    assert (clone / "main.nf").is_file()
    (command,) = table(writer, runner_commands)
    assert command.payload["location"] == str(clone)  # the runner launches the clone
    run_id = response.json()["id"]
    manifest = read_run_manifest(run_paths(settings.runs_root, run_id).run_dir)
    assert (manifest.workflow.location, manifest.workflow.revision) == (url, "v1.0")


def test_git_fetch_failure_names_the_field(
    authed_client: TestClient, git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wf, "GIT_SCHEMES", ("https", "ssh", "file"))
    url = git_repo.as_uri()
    response = authed_client.get(INSPECT, params={"location": url, "revision": "v9.9"})
    assert fields(response) == ["revision"]  # no such tag or branch
    gone = (git_repo.parent / "gone").as_uri()
    assert fields(authed_client.get(INSPECT, params={"location": gone, "revision": "v1"})) == [
        "location"
    ]


# --- Local-only mode (inbox #86) ------------------------------------------------------------


def test_api_absent_off_local(settings: Settings, writer: Writer, synthetic: Path) -> None:
    slurm = settings.model_copy(update={"executor": "slurm"})
    client = client_for(slurm, writer)
    response = client.get(INSPECT, params={"location": str(synthetic / "nextflow")})
    assert response.status_code == 404
    assert "Tasks 12" in response.json()["detail"]
    assert launch(client, str(synthetic / "nextflow"), "nextflow").status_code == 404
    assert table(writer, runs) == []


def test_api_absent_on_shared_host(
    settings: Settings, writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_mod, "shared_host", lambda: "sinfo on PATH")
    assert settings.executor == "local"
    client = client_for(settings, writer)
    response = client.get(INSPECT, params={"location": "/srv/pipeline"})
    assert response.status_code == 404
    assert "sinfo on PATH" in response.json()["detail"]
    assert "Tasks 12 to 16" in response.json()["detail"]
    text = start_text(settings, "login1", "alice", client.app.state.no_api)  # type: ignore[attr-defined]
    assert "sinfo on PATH" in text and "Tasks 12 to 16" in text


class RecordingLauncher:
    """Starts nothing: records the spec the runner would hand to a launcher."""

    def __init__(self) -> None:
        self.specs: list[LaunchSpec] = []

    def submit(self, spec: LaunchSpec) -> str:
        self.specs.append(spec)
        return "1.1"

    def poll(self, ids: list[str]) -> dict[str, HeadReport]:
        return {i: HeadReport("running", i, None, None, False, None) for i in ids}

    def cancel(self, native_id: str, grace_s: int = 60) -> None: ...

    def adopt(self, launch: Any) -> HeadReport:
        raise AssertionError("nothing to adopt")

    def forget(self, ids: Any) -> None: ...


def test_launch_reaches_the_runner(
    authed_client: TestClient,
    synthetic: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The `launch` command the endpoint writes is one the runner loop starts (P1 Task 9)."""
    monkeypatch.setattr(loop, "check_engine", lambda engine, cmd: EngineInfo("nextflow", "26.10.4"))
    location = synthetic / "nextflow"
    response = launch(authed_client, str(location), "nextflow", profiles=["local"])
    assert response.status_code == 201, response.text
    launcher = RecordingLauncher()
    loop.RunnerLoop(StoreSink(writer, settings.runs_root), launcher, settings).tick()
    (spec,) = launcher.specs
    assert (spec.run_id, spec.location, spec.profiles) == (
        response.json()["id"],
        location,
        ["local"],
    )
    (row,) = table(writer, runs)
    assert row.state == "running"  # the head report of the started head


# --- Untrusted pipeline files (SEC-P3T17-03, SEC-P3T17-04) -----------------------------------


_N = (wf.MAX_FILE - 40) // 2


@pytest.mark.parametrize(
    "tail",
    [
        "'" + "\\'" * _N,
        '"' + '\\"' * _N + "\\",  # a lone final backslash defeated the `\\Z` alternative
        "profiles {\n" + "a" * (2 * _N) + "\n}",  # a long word rescanned from each character
    ],
    ids=["single-quotes", "trailing-backslash", "profiles-word"],
)
def test_inspect_unterminated_strings_linear(
    authed_client: TestClient, tmp_path: Path, tail: str
) -> None:
    """A 1 MiB nextflow.config built to make the tokenizer or the profiles scan quadratic."""
    root = pipeline(tmp_path, "main.nf")
    text = "manifest { name = 'x' }\n" + tail
    assert len(text) <= wf.MAX_FILE
    (root / "nextflow.config").write_text(text)
    started = time.monotonic()
    response = authed_client.get(INSPECT, params={"location": str(root)})
    assert time.monotonic() - started < 1, "the tokenizer is not linear"
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "x"


@pytest.mark.parametrize("ref", ["file", "http://127.0.0.1:1/x"])
def test_launch_schema_remote_ref_not_fetched(
    authed_client: TestClient, tmp_path: Path, ref: str
) -> None:
    """A `$ref` in the pipeline's schema is never retrieved: no local file, no request."""
    secret = tmp_path / "secret.json"
    secret.write_text(json.dumps({"enum": ["TOP-SECRET-VALUE"]}))
    target = secret.as_uri() if ref == "file" else ref
    root = pipeline(tmp_path, "main.nf")
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"x": {"$ref": target}},
    }
    (root / "nextflow_schema.json").write_text(json.dumps(schema))
    started = time.monotonic()
    response = launch(authed_client, str(root), "nextflow", params={"x": "a"})
    assert time.monotonic() - started < 5
    assert fields(response) == ["params"]
    assert "TOP-SECRET-VALUE" not in response.text


def test_inspect_symlink_out_of_tree_not_read(
    authed_client: TestClient,
    tmp_path: Path,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Git clone whose schema and config files are symlinks out of the tree: none of them is
    read, so none of the target's bytes reaches the response (SEC-P3T17-05)."""
    monkeypatch.setattr(wf, "GIT_SCHEMES", ("https", "ssh", "file"))
    secrets_dir = tmp_path / "elsewhere"
    secrets_dir.mkdir()
    token = secrets_dir / "hosts.json"
    token.write_text(json.dumps({"oauth_token": "gho_SECRET"}))
    (secrets_dir / "config.yaml").write_text("oauth_token: gho_SECRET\n")
    (secrets_dir / "nextflow.config").write_text("manifest { name = 'gho_SECRET' }\n")
    repo = tmp_path / "repos" / "lab" / "links"
    clone = settings.data_dir / "pipelines" / "local" / Path(*repo.parts[1:]) / "v1"

    def rel(target: Path, link: str) -> str:  # relative to where the link sits in the clone
        return os.path.relpath(target, (clone / link).parent)

    links = {
        "nextflow.config": rel(secrets_dir / "nextflow.config", "nextflow.config"),
        "nextflow_schema.json": str(token),  # absolute
        "config.schema.yaml": rel(token, "config.schema.yaml"),
        "workflow/schemas/config.schema.yaml": str(token),
        "config/config.yaml": rel(secrets_dir / "config.yaml", "config/config.yaml"),
    }
    repo.mkdir(parents=True)
    (repo / "main.nf").write_text("\n")
    for name, target in links.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).symlink_to(target)
    git("init", "-q", "-b", "main", cwd=repo)
    git("add", ".", cwd=repo)
    git("commit", "-q", "-m", "links", cwd=repo)
    git("tag", "v1", cwd=repo)

    response = authed_client.get(INSPECT, params={"location": repo.as_uri(), "revision": "v1"})
    assert (clone / "config" / "config.yaml").read_text().startswith("oauth_token")  # it escapes
    assert "gho_SECRET" not in response.text
    assert response.status_code in (200, 422), response.text
    if response.status_code == 200:
        assert response.json()["schema_source"] == "none"


def test_inspect_symlinked_directory_not_followed(
    authed_client: TestClient, tmp_path: Path
) -> None:
    """A `config` or `profiles` directory or an entry file that is a symlink out of the tree
    is not followed (SEC-P3T17-05, SEC-P3T17-08)."""
    outside = tmp_path / "outside"
    (outside / "secretproj").mkdir(parents=True)
    (outside / "secretproj" / "config.yaml").write_text("\n")
    (outside / "config.yaml").write_text("oauth_token: gho_SECRET\n")
    (outside / "main.nf").write_text("\n")
    root = pipeline(tmp_path, "Snakefile")
    (root / "config").symlink_to(outside)
    (root / "profiles").symlink_to(outside)
    (root / "main.nf").symlink_to(outside / "main.nf")
    response = authed_client.get(INSPECT, params={"location": str(root)})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_source"] == "none"
    assert "gho_SECRET" not in response.text
    assert body["engine_files"] == ["Snakefile"] and body["profiles"] == []
    refused = launch(authed_client, str(root), "nextflow")
    assert refused.status_code == 422 and fields(refused) == ["workflow.engine"]


def test_inspect_symlinked_profile_not_listed(authed_client: TestClient, tmp_path: Path) -> None:
    """A profile directory or its config.yaml that is a symlink is not a profile."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "config.yaml").write_text("\n")
    root = pipeline(tmp_path, "Snakefile", "profiles/local/config.yaml")
    (root / "profiles" / "linked").symlink_to(outside)
    (root / "profiles" / "file").mkdir()
    (root / "profiles" / "file" / "config.yaml").symlink_to(outside / "config.yaml")
    response = authed_client.get(INSPECT, params={"location": str(root)})
    assert response.status_code == 200, response.text
    assert response.json()["profiles"] == ["local"]
