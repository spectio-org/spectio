"""The environments routes and the launch with an environment (FU-P3-86b to -86d; api §5.4;
dev-env §15.3 req. 18): the file through the server's pool, the six routes, their refusals and
their absence where the API is not served, the session, cross-site and `Origin` checks of
req. 2 and 7 per route, the launch body's `environment`, Resume's rules and the runner's
reading of the payload's snapshot (SEC-P3FU86A-R3-02)."""

import errno
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from spectio import envfile
from spectio import environments as envs
from spectio.config import Settings, SlurmOpts
from spectio.runner import loop
from spectio.runner.engines import EngineInfo
from spectio.runner.loop import LaunchPayload
from spectio.runner.rundir import read_run_manifest, run_paths
from spectio.runner.types import Stalled
from spectio_server.sink import StoreSink
from spectio_server.store.schema import runner_commands, runs
from spectio_server.store.writer import Writer

from .conftest import client_for
from .test_launch import RecordingLauncher
from .test_relaunch import end, resume

API = "/api/v1"
ENVS = f"{API}/environments"
MYLAB = {"name": "mylab", "label": "My lab", "executor": "local", "local": {"cpus": 4}}


def path() -> Path:
    return Path(os.environ["SPECTIO_CONFIG"]).parent / "environments.toml"


def hand_write(text: str, mode: int = 0o600) -> None:
    path().write_text(text)
    path().chmod(mode)


def create(client: TestClient, body: dict[str, Any] = MYLAB) -> Any:
    found = client.post(ENVS, json=body)
    assert found.status_code == 201, found.text
    return found


def problem(response: Any, status: int, slug: str, field: str | None = None) -> None:
    assert response.status_code == status, response.text
    body = response.json()
    assert body["type"] == f"/problems/{slug}", body
    if field is not None:
        assert field in [e["field"] for e in body["errors"]], body


def as_slurm(client: TestClient, settings: Settings, partition: str = "htc") -> Settings:
    """The server becomes one set up with SLURM (`[slurm] partition`), as behind its socket."""
    slurm = settings.model_copy(
        update={"executor": "slurm", "slurm": SlurmOpts(partition=partition)}
    )
    client.app.state.settings = slurm  # type: ignore[attr-defined]
    return slurm


def launch(client: TestClient, synthetic: Path, engine: str = "snakemake", **body: Any) -> Any:
    workflow = {"location": str(synthetic / engine), "engine": engine}
    return client.post(f"{API}/runs", json={"workflow": workflow, "params": {}, **body})


def launched(client: TestClient, synthetic: Path, **body: Any) -> str:
    found = launch(client, synthetic, **body)
    assert found.status_code == 201, found.text
    return str(found.json()["id"])


def column(writer: Writer, rid: str) -> Any:
    query = select(runs.c.environment).where(runs.c.id == rid)
    return writer.submit(lambda c: c.execute(query).scalar_one()).result()


def payload(writer: Writer, rid: str) -> LaunchPayload:
    query = select(runner_commands.c.payload).where(runner_commands.c.run_id == rid)
    return LaunchPayload.model_validate(
        writer.submit(lambda c: c.execute(query).scalar_one()).result()
    )


# --- The list and the file ------------------------------------------------------------------


def test_req18_routes_list_builtins(authed_client: TestClient, settings: Settings) -> None:
    found = authed_client.get(ENVS)
    assert found.status_code == 200, found.text
    body = found.json()
    assert body["default"] == "local"
    assert body["file"] == {"path": str(path()), "state": "missing", "detail": None}
    (local,) = body["items"]
    assert local["name"] == "local" and local["builtin"] and local["default"]
    assert (local["label"], local["local"], local["usable"]) == ("This machine", None, True)
    as_slurm(authed_client, settings)
    names = [(i["name"], i["default"]) for i in authed_client.get(ENVS).json()["items"]]
    assert names == [("slurm", True), ("local", False)]
    (_, local) = authed_client.get(ENVS).json()["items"]
    assert local["label"] == "Login node" and local["local"] == {"cpus": 2, "mem_mib": 8192}


def test_req18_routes_create_get_put_delete(authed_client: TestClient) -> None:
    made = create(authed_client)
    assert made.headers["location"] == f"{ENVS}/mylab"
    item = made.json()
    assert item["local"] == {"cpus": 4, "mem_mib": None} and not item["builtin"]
    assert made.headers["etag"] == item["etag"]
    got = authed_client.get(f"{ENVS}/mylab")
    assert got.status_code == 200 and got.headers["etag"] == item["etag"]
    assert [i["name"] for i in authed_client.get(ENVS).json()["items"]] == ["local", "mylab"]
    assert stat_mode(path()) == 0o600

    changed = {**MYLAB, "local": {"cpus": 8, "mem_mib": 1024}}
    problem(authed_client.put(f"{ENVS}/mylab", json=changed), 428, "if-match-required")
    star = {"If-Match": "*"}
    problem(
        authed_client.put(f"{ENVS}/mylab", json=changed, headers=star), 428, "if-match-required"
    )
    stale = {"If-Match": '"0000"'}
    problem(authed_client.put(f"{ENVS}/mylab", json=changed, headers=stale), 412, "etag-mismatch")
    put = authed_client.put(f"{ENVS}/mylab", json=changed, headers={"If-Match": item["etag"]})
    assert put.status_code == 200, put.text
    assert put.json()["local"] == {"cpus": 8, "mem_mib": 1024}
    assert put.headers["etag"] != item["etag"]
    renamed = {**changed, "name": "other"}
    tag = {"If-Match": put.headers["etag"]}
    problem(
        authed_client.put(f"{ENVS}/mylab", json=renamed, headers=tag),
        422,
        "validation-failed",
        "name",
    )

    problem(authed_client.delete(f"{ENVS}/mylab"), 428, "if-match-required")
    problem(authed_client.delete(f"{ENVS}/mylab", headers=star), 428, "if-match-required")
    problem(
        authed_client.delete(f"{ENVS}/mylab", headers={"If-Match": item["etag"]}),
        412,
        "etag-mismatch",
    )
    assert authed_client.delete(f"{ENVS}/mylab", headers=tag).status_code == 204
    problem(authed_client.get(f"{ENVS}/mylab"), 404, "not-found")
    problem(authed_client.delete(f"{ENVS}/mylab", headers=tag), 404, "not-found")


def stat_mode(p: Path) -> int:
    return p.stat().st_mode & 0o777


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({**MYLAB, "name": "local"}, "name"),
        ({**MYLAB, "name": "slurm"}, "name"),
        ({**MYLAB, "name": "new"}, "name"),
        ({**MYLAB, "name": "../spectio"}, "name"),
        ({**MYLAB, "name": "a" * 33}, "name"),
        ({"name": "x", "executor": "slurm"}, "executor"),  # a local server
        ({**MYLAB, "builtin": False}, "builtin"),
        ({**MYLAB, "default": True}, "default"),
        ({**MYLAB, "usable": True}, "usable"),
        ({**MYLAB, "local": {"cpus": True}}, "local.cpus"),
        ({**MYLAB, "local": {"cpus": "5"}}, "local.cpus"),
        ({**MYLAB, "local": {"cpus": 5.0}}, "local.cpus"),
        ({**MYLAB, "local": {"cpus": 0}}, "local.cpus"),
        ({**MYLAB, "local": {"cpus": 257}}, "local.cpus"),
        ({**MYLAB, "label": "a‮b"}, "label"),
        ({**MYLAB, "profiles": {"nextflow": "../x"}}, "profiles.nextflow"),
        ({**MYLAB, "slurm": {"partition": "htc"}}, "body"),  # slurm values on a local one
    ],
)
def test_req18_routes_refusals(authed_client: TestClient, body: dict[str, Any], field: str) -> None:
    problem(authed_client.post(ENVS, json=body), 422, "validation-failed", field)
    assert not path().exists()


def test_req18_routes_slurm_values_strict(authed_client: TestClient, settings: Settings) -> None:
    as_slurm(authed_client, settings)
    good = {"name": "mylab", "executor": "slurm", "slurm": {"partition": "htc", "time_min": 60}}
    for bad in ({"partition": "htc\n"}, {"account": "$HOME"}, {"time_min": 43201}):
        sent = {**good, "slurm": bad}
        problem(authed_client.post(ENVS, json=sent), 422, "validation-failed")
    assert create(authed_client, good).json()["slurm"]["partition"] == "htc"


def test_req18_routes_conflicts(authed_client: TestClient) -> None:
    create(authed_client)
    problem(authed_client.post(ENVS, json=MYLAB), 409, "environment-exists")
    tag = {"If-Match": '"x"'}
    for name in ("local", "slurm"):
        problem(
            authed_client.put(f"{ENVS}/{name}", json=MYLAB, headers=tag), 409, "environment-builtin"
        )
        problem(authed_client.delete(f"{ENVS}/{name}", headers=tag), 409, "environment-builtin")


def test_req18_routes_make_default(authed_client: TestClient) -> None:
    create(authed_client)
    assert authed_client.post(f"{ENVS}/mylab:make-default").status_code == 204
    body = authed_client.get(ENVS).json()
    assert body["default"] == "mylab"
    assert [i["default"] for i in body["items"]] == [False, True]
    assert envfile.read_file(path(), ["local"]).default == "mylab"
    problem(authed_client.post(f"{ENVS}/gone:make-default"), 404, "not-found")
    tag = {"If-Match": authed_client.get(f"{ENVS}/mylab").headers["etag"]}
    assert authed_client.delete(f"{ENVS}/mylab", headers=tag).status_code == 204
    assert authed_client.get(ENVS).json()["default"] == "local"  # the built-in's again
    assert envfile.read_file(path(), ["local"]).default is None
    assert authed_client.post(f"{ENVS}/local:make-default").status_code == 204
    assert envfile.read_file(path(), ["local"]).default == "local"


def test_req18_routes_hand_written_slurm_on_local_server(authed_client: TestClient) -> None:
    """A `slurm` entry on a server set up with --local is listed, not usable; the file is `ok`."""
    hand_write('[environments.hpc]\nexecutor = "slurm"\n')
    body = authed_client.get(ENVS).json()
    assert body["file"]["state"] == "ok"
    (hpc,) = [i for i in body["items"] if i["name"] == "hpc"]
    assert not hpc["usable"] and "spectio init --local" in hpc["unusable_reason"]
    problem(authed_client.post(f"{ENVS}/hpc:make-default"), 422, "validation-failed", "name")


@pytest.mark.parametrize(
    ("text", "mode", "state"),
    [
        ("a=" + "[" * 30000 + "]" * 30000, 0o600, "invalid"),
        ('default = "gone"\n', 0o600, "invalid"),
        ('[environments.x]\nexecutor = "local"\n', 0o620, "refused"),
    ],
)
def test_req18_routes_file_unusable(
    authed_client: TestClient, synthetic: Path, text: str, mode: int, state: str
) -> None:
    """Only the built-ins, with the state and its detail; never overwritten; launches with a
    built-in still work, one naming a file environment gets `422` on `environment`."""
    hand_write(text, mode)
    body = authed_client.get(ENVS).json()
    assert body["file"]["state"] == state and body["file"]["detail"]
    assert [i["name"] for i in body["items"]] == ["local"] and body["default"] == "local"
    problem(authed_client.post(ENVS, json=MYLAB), 409, "environments-file-unusable")
    problem(authed_client.post(f"{ENVS}/local:make-default"), 409, "environments-file-unusable")
    assert path().read_text() == text
    problem(
        launch(authed_client, synthetic, environment="x"), 422, "validation-failed", "environment"
    )
    assert launch(authed_client, synthetic).status_code == 201
    assert launch(authed_client, synthetic, environment="local").status_code == 201


def test_req18_routes_unreachable(
    authed_client: TestClient, synthetic: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file system that does not answer within the pool's timeout: `unreachable`, `503` on
    writes and on a launch naming a file environment; a built-in launch still works."""

    def stalled(*args: Any, **kwargs: Any) -> Any:
        raise Stalled("the file system did not answer within 5 s")

    monkeypatch.setattr(envfile, "read_kind", stalled)
    monkeypatch.setattr(envfile, "update_kind", stalled)
    body = authed_client.get(ENVS).json()
    assert body["file"]["state"] == "unreachable" and body["default"] == "local"
    problem(authed_client.post(ENVS, json=MYLAB), 503, "runner-offline")
    problem(authed_client.get(f"{ENVS}/mylab"), 503, "runner-offline")
    problem(launch(authed_client, synthetic, environment="mylab"), 503, "runner-offline")
    assert launch(authed_client, synthetic).status_code == 201


def test_req18_routes_io_error_on_read(
    authed_client: TestClient, synthetic: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An I/O error reading the file (ESTALE on NFS): `unreachable`, only the built-ins listed,
    `503` on writes and on a launch naming a file environment; a built-in launch still works
    (CR-P3FU86BCD-01)."""
    create(authed_client)
    read = os.read

    def stale(fd: int, n: int) -> bytes:
        if os.readlink(f"/proc/self/fd/{fd}") == str(path()):
            raise OSError(errno.ESTALE, os.strerror(errno.ESTALE))
        return read(fd, n)

    monkeypatch.setattr(os, "read", stale)  # the module envfile reads with
    hand_write(path().read_text().replace("cpus = 4", "cpus = 6"))  # a new identity: read again
    body = authed_client.get(ENVS).json()
    assert body["file"]["state"] == "unreachable" and body["file"]["detail"]
    assert [i["name"] for i in body["items"]] == ["local"] and body["default"] == "local"
    problem(authed_client.post(ENVS, json={**MYLAB, "name": "other"}), 503, "runner-offline")
    problem(launch(authed_client, synthetic, environment="mylab"), 503, "runner-offline")
    assert launch(authed_client, synthetic).status_code == 201


def test_req18_routes_io_error_on_write(
    authed_client: TestClient, synthetic: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A full home (ENOSPC) when the file is written: `503`, nothing written (CR-P3FU86BCD-01)."""

    def full(*args: Any, **kwargs: Any) -> None:
        raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))

    monkeypatch.setattr(envfile, "write_file", full)
    problem(authed_client.post(ENVS, json=MYLAB), 503, "runner-offline")
    assert not path().exists()
    assert authed_client.get(ENVS).json()["file"]["state"] == "missing"
    assert launch(authed_client, synthetic).status_code == 201


def test_req18_routes_file_changed(
    authed_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hand edit between the write's read and its rename: `409`, the edit kept."""
    create(authed_client)
    render = envfile.render

    def edited(*args: Any) -> bytes:
        hand_write(path().read_text().replace("cpus = 4", "cpus = 5"))
        return render(*args)

    monkeypatch.setattr(envfile, "render", edited)
    problem(authed_client.post(f"{ENVS}/local:make-default"), 409, "environments-file-changed")
    assert "cpus = 5" in path().read_text() and "default" not in path().read_text()


def test_req18_routes_hand_edit_picked_up(authed_client: TestClient) -> None:
    create(authed_client)
    assert authed_client.get(f"{ENVS}/mylab").json()["local"]["cpus"] == 4
    hand_write(path().read_text().replace("cpus = 4", "cpus = 6"))
    assert authed_client.get(f"{ENVS}/mylab").json()["local"]["cpus"] == 6


def test_req18_routes_absent_on_tcp_slurm(settings: Settings, writer: Writer) -> None:
    """SEC-PRE-FU86-R1-07: on a SLURM server's TCP port (`no_api_reason`) none of the six routes
    is mounted; they answer the API's 404 with its reason."""
    slurm = settings.model_copy(update={"executor": "slurm", "slurm": SlurmOpts(partition="htc")})
    client = client_for(slurm, writer)
    assert client.app.state.no_api is not None  # type: ignore[attr-defined]
    tag = {"If-Match": '"x"'}
    for response in (
        client.get(ENVS),
        client.get(f"{ENVS}/slurm"),
        client.post(ENVS, json=MYLAB),
        client.put(f"{ENVS}/mylab", json=MYLAB, headers=tag),
        client.delete(f"{ENVS}/mylab", headers=tag),
        client.post(f"{ENVS}/slurm:make-default"),
    ):
        problem(response, 404, "not-found")
        assert "Unix socket" in response.json()["detail"]
    assert not path().exists()


def calls(client: TestClient, tag: str) -> list[tuple[str, str, dict[str, Any]]]:
    put = {"json": {**MYLAB, "label": "New"}, "headers": {"If-Match": tag}}
    return [
        ("GET", ENVS, {}),
        ("GET", f"{ENVS}/mylab", {}),
        ("POST", ENVS, {"json": {**MYLAB, "name": "other"}}),
        ("PUT", f"{ENVS}/mylab", put),
        ("DELETE", f"{ENVS}/mylab", {"headers": {"If-Match": tag}}),
        ("POST", f"{ENVS}/mylab:make-default", {}),
    ]


def test_req18_routes_session_cross_site_origin(authed_client: TestClient) -> None:
    """Req. 2 and 7 per route: no session is `401`; another site (`Sec-Fetch-Site`, `Referer`,
    `Origin`) is `403`, a `GET` too; a write without an `Origin` is `403`. Nothing is written."""
    create(authed_client)
    before = path().read_bytes()
    tag = authed_client.get(f"{ENVS}/mylab").headers["etag"]
    cookies = dict(authed_client.cookies)
    authed_client.cookies.clear()
    for method, url, kw in calls(authed_client, tag):
        assert authed_client.request(method, url, **kw).status_code == 401, (method, url)
    authed_client.cookies.update(cookies)
    for foreign in (
        {"Sec-Fetch-Site": "cross-site"},
        {"Sec-Fetch-Site": "same-site"},
        {"Referer": "http://evil.example/page"},
        {"Origin": "http://evil.example"},
    ):
        for method, url, kw in calls(authed_client, tag):
            headers = {**kw.get("headers", {}), **foreign}
            found = authed_client.request(method, url, **{**kw, "headers": headers})
            problem(found, 403, "cross-site")
    origin = authed_client.headers.pop("origin")
    for method, url, kw in calls(authed_client, tag)[2:]:
        assert authed_client.request(method, url, **kw).status_code == 403, (method, url)
    authed_client.headers["origin"] = origin
    assert path().read_bytes() == before


def test_req18_routes_write_logged(
    authed_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-PRE-FU86-R1-10: one log line per write, with its route, name and values."""
    with caplog.at_level("INFO", logger="spectio_server.api.environments"):
        create(authed_client)
    (record,) = [r for r in caplog.records if r.name == "spectio_server.api.environments"]
    message = record.getMessage()
    assert message.startswith("environments POST /environments mylab: ")
    assert "'mylab': None" in message and "'cpus': 4" in message


# --- Launch with an environment (FU-P3-86c) --------------------------------------------------


def test_req18_snapshot_launch_with_environment(
    authed_client: TestClient,
    synthetic: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The values as resolved at launch go into the manifest, the row and the payload; an edit
    after the launch changes none of them, and the runner launches from the payload."""
    create(authed_client)
    rid = launched(authed_client, synthetic, environment="mylab")
    want = {
        "name": "mylab",
        "label": "My lab",
        "executor": "local",
        "slurm": None,
        "local": {"cpus": 4, "mem_mib": None},
    }
    assert column(writer, rid) == {**want, "state": "recorded"}
    assert read_run_manifest(run_paths(settings.runs_root, rid).run_dir).environment == want
    assert payload(writer, rid).environment == envs.Snapshot.model_validate(want)
    tag = {"If-Match": authed_client.get(f"{ENVS}/mylab").headers["etag"]}
    authed_client.put(f"{ENVS}/mylab", json={**MYLAB, "local": {"cpus": 64}}, headers=tag)
    assert column(writer, rid)["local"]["cpus"] == 4
    assert authed_client.get(f"{API}/runs/{rid}").json()["environment"]["local"]["cpus"] == 4

    monkeypatch.setattr(loop, "check_engine", lambda engine, cmd: EngineInfo(engine, "9.27.1"))
    launcher = RecordingLauncher()
    loop.RunnerLoop(StoreSink(writer, settings.runs_root), launcher, settings).tick()
    (spec,) = launcher.specs
    assert (spec.environment, spec.slurm) == ("mylab", None)
    assert spec.local == envs.LocalValues(cpus=4)


def test_req18_snapshot_launch_default(
    authed_client: TestClient, synthetic: Path, writer: Writer
) -> None:
    create(authed_client)
    assert column(writer, launched(authed_client, synthetic))["name"] == "local"
    authed_client.post(f"{ENVS}/mylab:make-default")
    assert column(writer, launched(authed_client, synthetic))["name"] == "mylab"


@pytest.mark.parametrize("name", ["gone", "slurm", "hpc", "../x", "Mylab"])
def test_req18_snapshot_launch_refused(
    authed_client: TestClient, synthetic: Path, settings: Settings, name: str
) -> None:
    """Unknown, `slurm` on a local server, a SLURM one there (not usable), not a name."""
    hand_write('[environments.hpc]\nexecutor = "slurm"\n')
    found = launch(authed_client, synthetic, environment=name)
    problem(found, 422, "validation-failed", "environment")
    if name == "slurm":
        assert "spectio init --local" in found.json()["errors"][0]["message"]
    assert list(settings.runs_root.iterdir()) == []


def test_req18_snapshot_runner_reads_the_payload_not_settings(
    authed_client: TestClient,
    synthetic: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-P3FU86A-R3-02: the runner builds the SLURM values from the payload's snapshot; a
    `[slurm]` changed after the launch changes nothing. A payload whose snapshot fails the
    strict model is a launch error, never a launch."""
    slurm = as_slurm(authed_client, settings)
    rid = launched(authed_client, synthetic)
    bad = launched(authed_client, synthetic)
    query = select(runner_commands.c.id, runner_commands.c.payload).where(
        runner_commands.c.run_id == bad
    )
    cid, sent = writer.submit(lambda c: c.execute(query).one()).result()
    broken = {**sent, "environment": {**sent["environment"], "slurm": {"partition": "htc\n"}}}
    writer.submit(
        lambda c: c.execute(
            update(runner_commands).where(runner_commands.c.id == cid).values(payload=broken)
        )
    ).result()
    later = slurm.model_copy(update={"slurm": SlurmOpts(partition="gpu", account="other")})
    monkeypatch.setattr(loop, "check_engine", lambda engine, cmd: EngineInfo(engine, "9.27.1"))
    launcher = RecordingLauncher()
    loop.RunnerLoop(StoreSink(writer, settings.runs_root), launcher, later).tick()
    (spec,) = launcher.specs
    assert spec.run_id == rid and spec.environment == "slurm"
    assert spec.slurm == envs.SlurmValues(partition="htc")
    failed = writer.submit(
        lambda c: c.execute(select(runs.c.state, runs.c.failure).where(runs.c.id == bad)).one()
    ).result()
    assert failed.failure["class"] == "launch_error"


def test_req18_snapshot_runner_checks_the_server_kind(
    authed_client: TestClient,
    synthetic: Path,
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-P3FU86BCD-02: a payload asking for SLURM on a server with no SLURM is a launch
    error, never a launch, even past the routes."""
    rid = launched(authed_client, synthetic)
    query = select(runner_commands.c.id, runner_commands.c.payload).where(
        runner_commands.c.run_id == rid
    )
    cid, sent = writer.submit(lambda c: c.execute(query).one()).result()
    forged = {**sent, "environment": {"name": "forged", "executor": "slurm"}}
    writer.submit(
        lambda c: c.execute(
            update(runner_commands).where(runner_commands.c.id == cid).values(payload=forged)
        )
    ).result()
    monkeypatch.setattr(loop, "check_engine", lambda engine, cmd: EngineInfo(engine, "9.27.1"))
    launcher = RecordingLauncher()
    loop.RunnerLoop(StoreSink(writer, settings.runs_root), launcher, settings).tick()
    assert launcher.specs == []
    failed = writer.submit(
        lambda c: c.execute(select(runs.c.failure).where(runs.c.id == rid)).one()
    ).result()
    assert failed.failure["class"] == "launch_error"


# --- Resume's rules (api §5.4, Resume; SEC-PRE-FU86-R1-03) -----------------------------------


def failed(
    client: TestClient, writer: Writer, settings: Settings, synthetic: Path, **body: Any
) -> str:
    rid = launched(client, synthetic, **body)
    end(writer, settings, rid)
    return rid


def child_payload(response: Any, writer: Writer) -> LaunchPayload:
    assert response.status_code == 201, response.text
    return payload(writer, response.json()["id"])


def test_req18_snapshot_resume_recorded(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    """A recorded snapshot still allowed: unchanged, whatever the file says now."""
    create(authed_client)
    rid = failed(authed_client, writer, settings, synthetic, environment="mylab")
    tag = {"If-Match": authed_client.get(f"{ENVS}/mylab").headers["etag"]}
    authed_client.delete(f"{ENVS}/mylab", headers=tag)
    found = child_payload(resume(authed_client, rid), writer)
    assert found.environment is not None and found.environment.local == envs.LocalValues(cpus=4)
    assert found.resume_of is not None
    child = resume(authed_client, rid)  # the first child is queued: refused
    assert child.status_code == 409


def test_req18_snapshot_resume_slurm_on_local_server(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    as_slurm(authed_client, settings)
    rid = failed(authed_client, writer, settings, synthetic)
    authed_client.app.state.settings = settings  # type: ignore[attr-defined]
    found = resume(authed_client, rid)
    problem(found, 422, "validation-failed", "environment")
    assert "this server has no SLURM" in found.json()["errors"][0]["message"]


def test_req18_snapshot_resume_local_gets_caps_on_slurm(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    rid = failed(authed_client, writer, settings, synthetic)  # the local-mode built-in: no caps
    as_slurm(authed_client, settings)
    found = child_payload(resume(authed_client, rid), writer)
    assert found.environment is not None and found.environment.name == "local"
    assert found.environment.local == envs.LocalValues(cpus=2, mem_mib=8192)


def set_column(writer: Writer, rid: str, value: dict[str, Any]) -> None:
    query = update(runs).where(runs.c.id == rid).values(environment=value)
    writer.submit(lambda c: c.execute(query)).result()


def test_req18_snapshot_resume_not_recorded_and_not_readable(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    old = failed(authed_client, writer, settings, synthetic)
    bad = failed(authed_client, writer, settings, synthetic)
    for rid, value in ((old, envs.run_column(None)), (bad, envs.run_column({"name": "x'"}))):
        set_column(writer, rid, value)
    slurm = as_slurm(authed_client, settings)
    found = child_payload(resume(authed_client, old), writer)
    builtin = envs.snapshot(envs.server_builtin(slurm).environment)
    assert found.environment == envs.Snapshot.model_validate(builtin)
    problem(resume(authed_client, bad), 422, "validation-failed", "environment")


def test_req18_snapshot_launch_template_environment(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    """Copy to a new launch preselects the run's environment by name, or the default with a
    notice when it is gone."""
    create(authed_client)
    rid = failed(authed_client, writer, settings, synthetic, environment="mylab")
    template = authed_client.get(f"{API}/runs/{rid}:launch-template").json()
    assert (template["environment"], template["environment_notice"]) == ("mylab", None)
    tag = {"If-Match": authed_client.get(f"{ENVS}/mylab").headers["etag"]}
    authed_client.delete(f"{ENVS}/mylab", headers=tag)
    template = authed_client.get(f"{API}/runs/{rid}:launch-template").json()
    assert template["environment"] == "local"
    assert "mylab" in template["environment_notice"]


def test_req18_snapshot_launch_template_file_unusable(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    """CR-P3FU86BCD-03: a file that cannot be used now does not say the environment is gone."""
    create(authed_client)
    rid = failed(authed_client, writer, settings, synthetic, environment="mylab")
    path().chmod(0o620)  # others may write it: refused
    template = authed_client.get(f"{API}/runs/{rid}:launch-template").json()
    assert template["environment"] == "local"
    assert template["environment_notice"] == (
        "The environment mylab of this run cannot be read: the environments file is refused;"
        " local is chosen."
    )
