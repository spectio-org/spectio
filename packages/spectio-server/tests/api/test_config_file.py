"""A launch's `default_resources` and `config_file` (FU-P3-110a, api §5.7; dev-env §15.3
req. 20): the strict checks of `POST /runs`, the path rule and the read, what the manifest and
`runs` keep, `GET /runs/{id}` and the launch template; what the runner gets, Resume's copy and
`GET /runs/{id}/config-file` (FU-P3-110b)."""

import hashlib
import os
import pwd
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from spectio.config import Settings, SlurmOpts
from spectio.environments import DefaultResources
from spectio.runner import loop
from spectio.runner.engines import EngineInfo
from spectio.runner.rundir import make_run_dirs, read_run_manifest, run_paths
from spectio.runner.types import ExtraFile
from spectio_server.api import extras
from spectio_server.files.pool import Stalled
from spectio_server.rebuild import rebuild_index
from spectio_server.sink import StoreSink
from spectio_server.store.schema import runner_commands, runs, workflows
from spectio_server.store.writer import Writer

from ..test_serve import make_run, run_id
from .test_launch import RecordingLauncher, fields, launch, table
from .test_relaunch import end, resume

API = "/api/v1"
NF_TEXT = "process.memory = '2 GB'\nincludeConfig 'other.config'\n"


@pytest.fixture
def home(authed_client: TestClient, settings: Settings) -> Path:
    """The test's home, as the password database would give it, made the app's home root."""
    found = settings.runs_root.parent
    authed_client.app.state.home = (str(found), os.path.realpath(found))  # type: ignore[attr-defined]
    return found


@pytest.fixture
def pipe(tmp_path: Path, synthetic: Path) -> Callable[[str], Path]:
    def copy(engine: str) -> Path:
        target = tmp_path / f"pipe-{engine}"
        if not target.exists():
            shutil.copytree(synthetic / engine, target)
        return target

    return copy


def write(path: Path, text: str | bytes = NF_TEXT, mode: int = 0o600) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode() if isinstance(text, str) else text)
    path.chmod(mode)
    return path


def fifo(path: Path) -> str:
    os.mkfifo(path)
    return path.name


def nf(client: TestClient, pipe: Callable[[str], Path], **body: Any) -> Any:
    return launch(client, str(pipe("nextflow")), "nextflow", **body)


def smk(client: TestClient, pipe: Callable[[str], Path], **body: Any) -> Any:
    return launch(client, str(pipe("snakemake")), "snakemake", **body)


def message(response: Any) -> str:
    return str(response.json()["errors"][0]["message"])


def column(writer: Writer, rid: str) -> Any:
    query = select(runs.c.default_resources, runs.c.config_file).where(runs.c.id == rid)
    return writer.submit(lambda c: c.execute(query).one()).result()


# --- default_resources -----------------------------------------------------------------------


def test_req20_resources_bounds_and_kept(
    authed_client: TestClient, pipe: Callable[[str], Path], settings: Settings, writer: Writer
) -> None:
    values = {"cpus": 256, "mem_mib": 4_194_304, "time_min": 43_200}
    found = nf(authed_client, pipe, default_resources=values)
    assert found.status_code == 201, found.text
    rid = found.json()["id"]
    manifest = read_run_manifest(run_paths(settings.runs_root, rid).run_dir)
    assert manifest.default_resources == values and manifest.config_file is None
    assert column(writer, rid) == ({**values, "state": "recorded"}, None)
    run = authed_client.get(f"{API}/runs/{rid}").json()
    assert run["default_resources"] == {**values, "state": "recorded"}
    assert run["config_file"] is None
    template = authed_client.get(f"{API}/runs/{rid}:launch-template").json()
    assert template["default_resources"] == values and template["config_file"] is None
    (command,) = table(writer, runner_commands)
    assert command.payload["default_resources"] == values


@pytest.mark.parametrize("body", [None, {}])
def test_req20_resources_absent_or_empty_is_none(
    authed_client: TestClient, pipe: Callable[[str], Path], writer: Writer, body: Any
) -> None:
    extra = {} if body is None else {"default_resources": body}
    found = nf(authed_client, pipe, **extra)
    assert found.status_code == 201, found.text
    assert column(writer, found.json()["id"]) == (None, None)
    assert authed_client.get(f"{API}/runs/{found.json()['id']}").json()["default_resources"] is None


@pytest.mark.parametrize(
    ("values", "field"),
    [
        ({"cpus": 0}, "default_resources.cpus"),
        ({"cpus": 257}, "default_resources.cpus"),
        ({"mem_mib": 4_194_305}, "default_resources.mem_mib"),
        ({"time_min": 43_201}, "default_resources.time_min"),
        ({"cpus": True}, "default_resources.cpus"),
        ({"cpus": "4"}, "default_resources.cpus"),
        ({"mem_mib": 4.0}, "default_resources.mem_mib"),
        ({"gpus": 1}, "default_resources.gpus"),
    ],
)
def test_req20_resources_strict(
    authed_client: TestClient, pipe: Callable[[str], Path], values: Any, field: str
) -> None:
    assert fields(nf(authed_client, pipe, default_resources=values)) == [field]


def test_req20_resources_snakemake_cpus_and_profile(
    authed_client: TestClient, pipe: Callable[[str], Path]
) -> None:
    cpus = smk(authed_client, pipe, default_resources={"cpus": 2})
    assert fields(cpus) == ["default_resources.cpus"]
    assert message(cpus) == "Snakemake takes CPUs from each rule's threads"
    profile = smk(authed_client, pipe, profiles=["slurm"], default_resources={"mem_mib": 100})
    assert fields(profile) == ["default_resources"]
    assert message(profile) == "The profile slurm sets the resources"
    ok = smk(authed_client, pipe, default_resources={"mem_mib": 100, "time_min": 5})
    assert ok.status_code == 201, ok.text


def test_req20_resources_above_local_cap(
    authed_client: TestClient, pipe: Callable[[str], Path], settings: Settings
) -> None:
    """The built-in `local` of a SLURM server, "Login node", is capped at 2 CPUs and 8192 MiB."""
    slurm = settings.model_copy(update={"executor": "slurm", "slurm": SlurmOpts(partition="htc")})
    authed_client.app.state.settings = slurm  # type: ignore[attr-defined]
    cpus = nf(authed_client, pipe, environment="local", default_resources={"cpus": 3})
    assert fields(cpus) == ["default_resources.cpus"]
    assert message(cpus) == "At most 2 CPUs in Login node"
    mem = nf(authed_client, pipe, environment="local", default_resources={"mem_mib": 8193})
    assert fields(mem) == ["default_resources.mem_mib"]
    assert message(mem) == "At most 8192 MiB in Login node"
    ok = nf(authed_client, pipe, environment="local", default_resources={"cpus": 2})
    assert ok.status_code == 201, ok.text


# --- config_file: the route --------------------------------------------------------------------


def test_req20_config_file_kept(
    authed_client: TestClient,
    pipe: Callable[[str], Path],
    home: Path,
    settings: Settings,
    writer: Writer,
) -> None:
    path = write(home / "conf" / "extra.config")
    found = nf(authed_client, pipe, config_file=str(path))
    assert found.status_code == 201, found.text
    rid = found.json()["id"]
    kept = {
        "path": str(path),
        "kept_as": "extra.config",
        "sha256": hashlib.sha256(NF_TEXT.encode()).hexdigest(),
        "size": len(NF_TEXT.encode()),
        "includes": True,
    }
    manifest = read_run_manifest(run_paths(settings.runs_root, rid).run_dir)
    assert manifest.config_file == kept
    assert column(writer, rid) == (None, {**kept, "state": "recorded"})
    assert authed_client.get(f"{API}/runs/{rid}").json()["config_file"] == {
        **kept,
        "state": "recorded",
    }
    template = authed_client.get(f"{API}/runs/{rid}:launch-template").json()
    assert template["config_file"] == str(path)
    assert {"field": "config_file", "value": str(path), "writable_by_others": False} in template[
        "code_loading"
    ]
    (command,) = table(writer, runner_commands)
    assert command.payload["config_file"] == {
        "kept_as": "extra.config",
        "sha256": kept["sha256"],
        "size": kept["size"],
        "text": NF_TEXT,
    }


def test_req20_config_file_in_the_pipeline_under_tmp(
    authed_client: TestClient, tmp_path: Path, synthetic: Path, home: Path
) -> None:
    """A pipeline under `/tmp/<dir>` is a root; `/tmp` itself is not."""
    base = Path("/tmp") / f"spectio-{os.getpid()}-{tmp_path.name}"  # noqa: S108 - the case itself
    shutil.copytree(synthetic / "snakemake", base)
    try:
        base.chmod(0o700)
        write(base / "config" / "extra.yml", "ref:\n  build: GRCh38\n")
        ok = launch(authed_client, str(base), "snakemake", config_file=f"{base}/config/extra.yml")
        assert ok.status_code == 201, ok.text
        stray = write(Path(f"{base}.json"), "{}")
        try:
            refused = launch(authed_client, str(base), "snakemake", config_file=str(stray))
            assert fields(refused) == ["config_file"]
            assert message(refused) == "Choose a file in your home directory or in the pipeline"
        finally:
            stray.unlink()
    finally:
        shutil.rmtree(base)


def test_req20_config_file_home_link_both_prefixes(
    authed_client: TestClient, pipe: Callable[[str], Path], tmp_path: Path
) -> None:
    real = tmp_path / "nfs" / "u"
    real.mkdir(parents=True, mode=0o700)
    link = tmp_path / "u"
    link.symlink_to(real)
    authed_client.app.state.home = (str(link), str(real))  # type: ignore[attr-defined]
    write(real / "x.config")
    for prefix in (link, real):
        found = nf(authed_client, pipe, config_file=f"{prefix}/x.config")
        assert found.status_code == 201, found.text


def test_req20_config_file_home_link_with_trailing_slash(
    authed_client: TestClient, pipe: Callable[[str], Path], tmp_path: Path
) -> None:
    """A passwd home written with a trailing '/' that is a link (CR-P3FU110A-01)."""
    real = tmp_path / "nfs" / "u"
    real.mkdir(parents=True, mode=0o700)
    link = tmp_path / "u"
    link.symlink_to(real)
    authed_client.app.state.home = (f"{link}/", str(real))  # type: ignore[attr-defined]
    write(real / "x.config")
    found = nf(authed_client, pipe, config_file=f"{link}/x.config")
    assert found.status_code == 201, found.text


def test_req20_config_file_home_from_the_password_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    written = pwd.getpwuid(os.getuid()).pw_dir
    assert extras.home_roots() == (written, os.path.realpath(written))


@pytest.mark.parametrize(
    ("make", "why"),
    [
        (lambda h: write(h / "x.txt") and "x.txt", "a .config file"),
        (lambda h: "../x.config", "plain names"),
        (lambda h: "missing.config", "no such file"),
        (lambda h: write(h / "x.config", mode=0o620) and "x.config", "writable by group"),
        (lambda h: write(h / "x.config", mode=0o602) and "x.config", "writable by group"),
        (lambda h: write(h / "x.config", b"a" * (256 * 1024 + 1)) and "x.config", "256 KiB"),
        (lambda h: write(h / "x.config", b"\xff\xfe") and "x.config", "UTF-8"),
        (lambda h: write(h / "x.config", b"a\x00b") and "x.config", "NUL"),
        (lambda h: (h / "d.config").mkdir() or "d.config", "not a regular file"),
        (lambda h: fifo(h / "f.config"), "not a regular file"),
    ],
)
def test_req20_config_file_refused(
    authed_client: TestClient,
    pipe: Callable[[str], Path],
    home: Path,
    make: Callable[[Path], str],
    why: str,
) -> None:
    rel = make(home)
    found = nf(authed_client, pipe, config_file=f"{home}/{rel}")
    assert fields(found) == ["config_file"]
    assert why in message(found)


def test_req20_config_file_links_refused(
    authed_client: TestClient, pipe: Callable[[str], Path], home: Path, tmp_path: Path
) -> None:
    target = write(tmp_path / "elsewhere" / "x.config")
    (home / "x.config").symlink_to(target)
    (home / "d").symlink_to(target.parent)
    for rel in ("x.config", "d/x.config"):
        found = nf(authed_client, pipe, config_file=f"{home}/{rel}")
        assert fields(found) == ["config_file"]
        assert "symbolic link" in message(found)


def test_req20_config_file_group_writable_root_and_directory(
    authed_client: TestClient, pipe: Callable[[str], Path], home: Path
) -> None:
    write(home / "d" / "x.config")
    (home / "d").chmod(0o770)
    found = nf(authed_client, pipe, config_file=f"{home}/d/x.config")
    assert fields(found) == ["config_file"] and "writable by group" in message(found)
    (home / "d").chmod(0o700)
    home.chmod(0o770)
    try:
        found = nf(authed_client, pipe, config_file=f"{home}/d/x.config")
        assert fields(found) == ["config_file"] and "writable by group" in message(found)
    finally:
        home.chmod(0o700)
    pipeline = pipe("nextflow")
    write(pipeline / "conf" / "extra.config")
    pipeline.chmod(0o775)
    found = nf(authed_client, pipe, config_file=f"{pipeline}/conf/extra.config")
    assert fields(found) == ["config_file"] and "writable by group" in message(found)


def test_req20_config_file_owner(tmp_path: Path) -> None:
    """The file is the user's only, root's included; a directory may be root's."""
    write(tmp_path / "d" / "x.config")
    (tmp_path / "d").chmod(0o700)
    uid = os.stat(tmp_path).st_uid
    assert extras.read_config_file(str(tmp_path), ("d", "x.config"), "nextflow", uid)["size"]
    with pytest.raises(ValueError, match="not owned by this user"):
        extras.read_config_file(str(tmp_path), ("d", "x.config"), "nextflow", 12345)


@pytest.mark.parametrize(
    ("name", "text", "why"),
    [
        ("x.yaml", "- a\n- b\n", "not a map"),
        ("x.yaml", "a: &x 1\nb: *x\n", "alias"),
        ("x.yaml", "__use_yte__: true\na: 1\n", "__use_yte__"),
        ("x.json", '{"__use_yte__": false}', "__use_yte__"),
        ("x.json", "{", "not JSON"),
        ("x.yaml", "a: [", "not YAML"),
    ],
)
def test_req20_config_file_snakemake_data_only(
    authed_client: TestClient,
    pipe: Callable[[str], Path],
    home: Path,
    name: str,
    text: str,
    why: str,
) -> None:
    write(home / name, text)
    found = smk(authed_client, pipe, config_file=f"{home}/{name}")
    assert fields(found) == ["config_file"]
    assert why in message(found)


def test_req20_config_file_snakemake_kept(
    authed_client: TestClient, pipe: Callable[[str], Path], home: Path, writer: Writer
) -> None:
    write(home / "x.yml", "ref:\n  build: GRCh38\nnote: includeConfig\n")
    found = smk(authed_client, pipe, config_file=f"{home}/x.yml")
    assert found.status_code == 201, found.text
    _, kept = column(writer, found.json()["id"])
    assert (kept["kept_as"], kept["includes"]) == ("extra.yaml", False)


def test_req20_config_file_pool_timeout(
    authed_client: TestClient, pipe: Callable[[str], Path], home: Path
) -> None:
    write(home / "x.config")

    class Stuck:
        def run(self, fn: Any, timeout_s: float, on_done: Any = None) -> Any:
            raise Stalled("the file system did not answer within 5 s")

    authed_client.app.state.files = Stuck()  # type: ignore[attr-defined]
    found = nf(authed_client, pipe, config_file=f"{home}/x.config")
    assert found.status_code == 503, found.text
    assert found.json()["type"] == "/problems/runner-offline"


def test_req20_config_file_refusal_never_quotes_the_bytes(
    authed_client: TestClient, pipe: Callable[[str], Path], home: Path
) -> None:
    write(home / "x.yaml", "SECRET: [\n")
    found = smk(authed_client, pipe, config_file=f"{home}/x.yaml")
    assert fields(found) == ["config_file"] and "SECRET" not in found.text


# --- What the run keeps, rebuilt -----------------------------------------------------------------


def test_req20_rebuild_reads_both_fields(settings: Settings, writer: Writer) -> None:
    """Read with the routes' validators (req. 10): a bad one is `not_readable` for that field
    only, a manifest without them reads as none."""
    good_res = {"cpus": None, "mem_mib": 100, "time_min": 5}
    good_cfg = {
        "path": "/home/u/x.config",
        "kept_as": "extra.config",
        "sha256": "0" * 64,
        "size": 3,
        "includes": False,
    }
    make_run(settings.runs_root, run_id(1), default_resources=good_res, config_file=good_cfg)
    make_run(settings.runs_root, run_id(2))
    bad_cfg = {**good_cfg, "path": "/home/u/x\u202e.config"}
    make_run(settings.runs_root, run_id(3), default_resources={"cpus": "4"}, config_file=bad_cfg)
    assert rebuild_index(writer, settings.runs_root).added == 3
    assert column(writer, run_id(1)) == (
        {**good_res, "state": "recorded"},
        {**good_cfg, "state": "recorded"},
    )
    assert column(writer, run_id(2)) == (None, None)
    res, cfg = column(writer, run_id(3))
    assert res == {"cpus": None, "mem_mib": None, "time_min": None, "state": "not_readable"}
    assert cfg["state"] == "not_readable" and cfg["path"] is None


# --- FU-P3-110b: the runner, Resume and the kept file -----------------------------------------


def launched_with_file(
    client: TestClient, pipe: Callable[[str], Path], home: Path, **body: Any
) -> str:
    path = write(home / "conf" / "extra.config")
    found = nf(client, pipe, config_file=str(path), **body)
    assert found.status_code == 201, found.text
    return str(found.json()["id"])


def kept_path(settings: Settings, rid: str) -> Path:
    return run_paths(settings.runs_root, rid).launch_dir / ".spectio" / "extra.config"


def keep(settings: Settings, rid: str, text: str = NF_TEXT) -> Path:
    """What the runner leaves: the snapshot in the run's `.spectio/`, 0600."""
    make_run_dirs(settings.runs_root, rid)
    return write(kept_path(settings, rid), text)


def test_req20_runner_gets_the_values_and_the_bytes_then_cleared(
    authed_client: TestClient,
    pipe: Callable[[str], Path],
    home: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rid = launched_with_file(authed_client, pipe, home, default_resources={"mem_mib": 100})
    monkeypatch.setattr(loop, "check_engine", lambda engine, cmd: EngineInfo(engine, "26.10.4"))
    launcher = RecordingLauncher()
    loop.RunnerLoop(StoreSink(writer, settings.runs_root), launcher, settings).tick()
    (spec,) = launcher.specs
    assert spec.run_id == rid and spec.default_resources == DefaultResources(mem_mib=100)
    sha = hashlib.sha256(NF_TEXT.encode()).hexdigest()
    assert spec.config_file == ExtraFile("extra.config", sha, NF_TEXT)
    # once the command is answered, no row holds the bytes (SEC-P3FU110-SPEC-01)
    (command,) = table(writer, runner_commands)
    assert command.state == "done" and command.payload["config_file"]["text"] is None
    assert command.payload["config_file"]["sha256"] == sha
    # the copied command names the kept file, read from the payload without its bytes
    argv = authed_client.get(f"{API}/runs/{rid}").json()["command"]["argv"]
    own = run_paths(settings.runs_root, rid).launch_dir / ".spectio"
    assert argv[argv.index("-c") + 1] == f"{own}/extra.config,{own}/spectio.config"


def test_req20_unrunnable_launch_fails_without_the_bytes(
    authed_client: TestClient,
    pipe: Callable[[str], Path],
    home: Path,
    settings: Settings,
    writer: Writer,
) -> None:
    """A launch command the runner cannot run ends `failed` at lease time, never answered by
    `ack`: its row keeps no bytes either (SEC-P3FU110-SPEC-01, CR-P3FU110B-02)."""
    launched_with_file(authed_client, pipe, home)
    writer.submit(lambda c: c.execute(update(workflows).values(engine="cwl"))).result()
    assert StoreSink(writer, settings.runs_root).lease_commands() == []
    (command,) = table(writer, runner_commands)
    assert command.state == "failed" and command.payload["config_file"]["text"] is None
    assert command.payload["config_file"]["sha256"] == hashlib.sha256(NF_TEXT.encode()).hexdigest()


def test_req20_resume_copies_the_kept_file(
    authed_client: TestClient,
    pipe: Callable[[str], Path],
    home: Path,
    settings: Settings,
    writer: Writer,
) -> None:
    rid = launched_with_file(authed_client, pipe, home, default_resources={"time_min": 5})
    end(writer, settings, rid)
    keep(settings, rid)
    (home / "conf" / "extra.config").write_text("process.cpus = 64\n")  # changes no run
    found = resume(authed_client, rid)
    assert found.status_code == 201, found.text
    child = found.json()["id"]
    commands = {c.run_id: c.payload for c in table(writer, runner_commands)}
    assert commands[child]["config_file"]["text"] == NF_TEXT
    assert commands[child]["default_resources"] == {"cpus": None, "mem_mib": None, "time_min": 5}
    manifest = read_run_manifest(run_paths(settings.runs_root, child).run_dir)
    assert (
        manifest.config_file
        == read_run_manifest(run_paths(settings.runs_root, rid).run_dir).config_file
    )
    assert manifest.default_resources == {"cpus": None, "mem_mib": None, "time_min": 5}


@pytest.mark.parametrize("change", ["edited", "missing", "link"])
def test_req20_resume_refuses_a_changed_copy(
    authed_client: TestClient,
    pipe: Callable[[str], Path],
    home: Path,
    settings: Settings,
    writer: Writer,
    change: str,
) -> None:
    rid = launched_with_file(authed_client, pipe, home)
    end(writer, settings, rid)
    if change == "edited":
        keep(settings, rid, "process.cpus = 64\n")
    elif change == "link":
        kept_path(settings, rid).symlink_to(home / "conf" / "extra.config")
    found = resume(authed_client, rid)
    assert fields(found) == ["config_file"]
    assert "use Copy to a new launch" in message(found)


def test_req20_get_config_file(
    authed_client: TestClient,
    pipe: Callable[[str], Path],
    home: Path,
    settings: Settings,
    writer: Writer,
) -> None:
    rid = launched_with_file(authed_client, pipe, home)
    assert authed_client.get(f"{API}/runs/{rid}/config-file").status_code == 404  # not kept yet
    path = keep(settings, rid)
    found = authed_client.get(f"{API}/runs/{rid}/config-file")
    assert found.status_code == 200, found.text
    assert found.text == NF_TEXT
    assert found.headers["content-type"] == "text/plain; charset=utf-8"
    assert found.headers["etag"] == f'"{hashlib.sha256(NF_TEXT.encode()).hexdigest()}"'
    assert found.headers["content-security-policy"] == "sandbox; default-src 'none'"
    assert found.headers["cross-origin-resource-policy"] == "same-origin"
    assert found.headers["x-content-type-options"] == "nosniff"
    path.write_text("edited by hand\n")
    changed = authed_client.get(f"{API}/runs/{rid}/config-file")
    edited = hashlib.sha256(b"edited by hand\n").hexdigest()
    assert changed.headers["etag"] == f'"{edited}"'
    path.unlink()
    path.symlink_to(home / "conf" / "extra.config")
    assert authed_client.get(f"{API}/runs/{rid}/config-file").status_code == 404
    write(path.with_name("big"), "x" * (extras.MAX_CONFIG_FILE + 1)).replace(path)
    assert authed_client.get(f"{API}/runs/{rid}/config-file").status_code == 404
    shutil.rmtree(path.parent)
    write(path.parent)  # `.spectio` replaced by a file: ENOTDIR, a 404 (CR-P3FU110B-05)
    assert authed_client.get(f"{API}/runs/{rid}/config-file").status_code == 404
    other = nf(authed_client, pipe).json()["id"]
    assert authed_client.get(f"{API}/runs/{other}/config-file").status_code == 404
    assert authed_client.get(f"{API}/runs/run_nope/config-file").status_code == 404


# --- Inspect's `config_file`: the same checks before Launch (FU-P3-121) -------------------------


def inspect(client: TestClient, location: Path, **params: str) -> Any:
    return client.get(f"{API}/workflows:inspect", params={"location": str(location), **params})


def test_inspect_config_file_says_what_launch_would_refuse(
    authed_client: TestClient, pipe: Callable[[str], Path], home: Path
) -> None:
    """A group-writable file (login1 retest h): inspect reports Launch's refusal in its words,
    and a file Launch accepts with `error: null`; never the file's bytes."""
    path = write(home / "x.config", "SECRET = 1\n", 0o664)
    found = inspect(authed_client, pipe("nextflow"), config_file=str(path), engine="nextflow")
    assert found.status_code == 200, found.text
    assert found.json()["config_file"] == {
        "path": str(path),
        "error": "the file is writable by group or others",
    }
    path.chmod(0o600)
    found = inspect(authed_client, pipe("nextflow"), config_file=str(path), engine="nextflow")
    assert found.json()["config_file"] == {"path": str(path), "error": None}
    assert "SECRET" not in found.text


@pytest.mark.parametrize(
    ("engine", "name", "text", "why"),
    [
        ("nextflow", "x.yaml", "a: 1\n", "a .config file"),
        ("snakemake", "x.yaml", "__use_yte__: true\n", "__use_yte__"),
        ("snakemake", "x.json", "{", "not JSON"),
    ],
)
def test_inspect_config_file_follows_the_engine(
    authed_client: TestClient,
    pipe: Callable[[str], Path],
    home: Path,
    engine: str,
    name: str,
    text: str,
    why: str,
) -> None:
    path = write(home / name, text)
    found = inspect(authed_client, pipe(engine), config_file=str(path), engine=engine)
    assert why in found.json()["config_file"]["error"]


def test_inspect_config_file_outside_the_roots_and_absent(
    authed_client: TestClient, pipe: Callable[[str], Path], home: Path, tmp_path: Path
) -> None:
    path = write(tmp_path / "x.config")
    found = inspect(authed_client, pipe("nextflow"), config_file=str(path), engine="nextflow")
    assert "home directory or in the pipeline" in found.json()["config_file"]["error"]
    assert inspect(authed_client, pipe("nextflow")).json()["config_file"] is None


def test_inspect_config_file_engine_from_the_pipeline(
    authed_client: TestClient, pipe: Callable[[str], Path], home: Path
) -> None:
    """Without `engine`, the pipeline's own (main.nf here); an unknown engine is a 422."""
    path = write(home / "x.config")
    found = inspect(authed_client, pipe("nextflow"), config_file=str(path))
    assert found.json()["config_file"] == {"path": str(path), "error": None}
    bad = inspect(authed_client, pipe("nextflow"), config_file=str(path), engine="cwl")
    assert bad.status_code == 422


def test_inspect_config_file_browser_checks_before_any_read(
    settings: Settings,
    writer: Writer,
    authed_client: TestClient,
    pipe: Callable[[str], Path],
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Session, Host and cross-site checks as on every route: the file is never read."""
    from .conftest import client_for

    reads: list[Any] = []
    monkeypatch.setattr(extras, "read_config_file", lambda *a: reads.append(a))
    path = write(home / "x.config")
    params = {"location": str(pipe("nextflow")), "config_file": str(path), "engine": "nextflow"}
    url = f"{API}/workflows:inspect"
    assert client_for(settings, writer, signed_in=False).get(url, params=params).status_code == 401
    for headers, status in (
        ({"Host": "evil.example"}, 400),
        ({"Sec-Fetch-Site": "cross-site"}, 403),
    ):
        assert authed_client.get(url, params=params, headers=headers).status_code == status
    assert reads == []
