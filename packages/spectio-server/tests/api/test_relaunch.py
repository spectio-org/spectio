"""Resume, the copied command and Copy to a new launch (P1 Task 30; api §5 and §5.1, notes of
2026-10-28; dev-env §15.3 req. 7, 10 and 16).

The CSRF token of req. 7 waits for the session (P1 Tasks 12 to 16):
`test_req16_relaunch_origin_csrf` checks the Origin half, as the other write routes do until
then (inbox #86, rule 1).
"""

import os
import shlex
import shutil
import socket
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from spectio.config import EngineOpts, Settings
from spectio.runner.loop import LaunchPayload
from spectio.runner.rundir import make_run_dirs, read_run_manifest, run_paths
from spectio_server.api.relaunch import writable_by_others
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.rebuild import rebuild_index
from spectio_server.sink import StoreSink
from spectio_server.store.db import open_db
from spectio_server.store.schema import launches, runner_commands, runs
from spectio_server.store.writer import Writer

from .conftest import client_for

SESSION = "5f1c8a43-7f62-4a5e-9d4f-0a1b2c3d4e5f"
SLEEP = shutil.which("sleep") or "/bin/sleep"


def launch(client: TestClient, location: Path, engine: str = "nextflow", **body: Any) -> str:
    sent = {"workflow": {"location": str(location), "engine": engine}, **body}
    response = client.post("/api/v1/runs", json=sent)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def end(
    writer: Writer, settings: Settings, run_id: str, state: str = "failed", **values: Any
) -> None:
    """The run's head ran and ended: its directories exist, its launch has a session ID."""
    make_run_dirs(settings.runs_root, run_id)
    launch_values = {"engine_session_id": SESSION, **values.pop("launch", {})}

    def write(conn: Any) -> None:
        conn.execute(update(runs).where(runs.c.id == run_id).values(state=state, **values))
        conn.execute(update(launches).where(launches.c.run_id == run_id).values(**launch_values))

    writer.submit(write).result()


def resume(client: TestClient, run_id: str, **kwargs: Any) -> Any:
    return client.post(f"/api/v1/runs/{run_id}:relaunch", **{"json": {"mode": "resume"}, **kwargs})


def rows(writer: Writer, table: Any) -> list[Any]:
    return writer.submit(lambda c: list(c.execute(select(table)).all())).result()


def children(writer: Writer, parent: str) -> list[Any]:
    return [r for r in rows(writer, runs) if r.parent_run_id == parent]


def refused(response: Any, status: int, reason: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["reason"] == reason, response.text


@pytest.fixture
def failed_run(
    authed_client: TestClient, writer: Writer, settings: Settings, synthetic: Path
) -> str:
    run_id = launch(authed_client, synthetic / "nextflow", profiles=["local"], params={"chunks": 2})
    end(writer, settings, run_id)
    return run_id


def head_pid(settings: Settings, run_id: str, line: str) -> None:
    path = run_paths(settings.runs_root, run_id).launch_dir / ".spectio" / "head.pid"
    path.write_text(line)
    path.chmod(0o600)


def boot_id() -> str:
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def my_head_line(host: str | None = None, boot: str | None = None) -> str:
    """head.pid naming this test process: a live head."""
    start = Path("/proc/self/stat").read_text().rsplit(") ", 1)[1].split()[19]
    host = host or socket.gethostname()
    return f"{os.getpid()} {os.getpgid(0)} {start} {boot or boot_id()} {host}\n"


# --- Resume ---------------------------------------------------------------------------------


def test_resume_failed_creates_child(
    authed_client: TestClient, writer: Writer, settings: Settings, failed_run: str
) -> None:
    response = resume(authed_client, failed_run)
    assert response.status_code == 201, response.text
    child = response.json()
    assert response.headers["location"] == f"/api/v1/runs/{child['id']}"
    assert (child["state"], child["parent_run_id"]) == ("queued", failed_run)
    assert (child["profiles"], child["params"]) == (["local"], {"chunks": 2})
    parent = authed_client.get(f"/api/v1/runs/{failed_run}").json()
    assert parent["state"] == "failed"  # the parent never changes state (api §5.1)
    assert parent["resumed_as"] == [{"id": child["id"], "name": child["name"], "state": "queued"}]
    assert parent["actions"]["resume"] == {"allowed": False, "reason": "resume_in_progress"}

    (row,) = children(writer, failed_run)
    parent_paths = run_paths(settings.runs_root, failed_run)
    assert (row.launch_dir, row.work_dir) == (
        str(parent_paths.launch_dir),
        str(parent_paths.work_dir),
    )
    assert (row.relaunch_mode, row.lineage_id) == ("resume", failed_run)
    # its own run directory, for its own .spectio/ (manifest, head files, spool)
    assert read_run_manifest(run_paths(settings.runs_root, child["id"]).run_dir).parent_run_id == (
        failed_run
    )
    leased = [
        c for c in StoreSink(writer, settings.runs_root).lease_commands() if c.kind == "launch"
    ]
    (command,) = [c for c in leased if c.launch.run_id == child["id"]]
    assert command.launch.launch_dir == run_paths(settings.runs_root, child["id"]).launch_dir
    payload = LaunchPayload.model_validate(command.payload)
    assert payload.resume_of is not None
    st = parent_paths.launch_dir.stat()
    assert payload.resume_of.model_dump() == {
        "run_id": failed_run,
        "parent_run_id": failed_run,
        "engine_session_id": SESSION,
        "device": st.st_dev,
        "inode": st.st_ino,
    }


def test_resume_without_launch_command_keeps_profiles(
    authed_client: TestClient, writer: Writer, settings: Settings, failed_run: str
) -> None:
    """A run rebuilt from its run directories has no `launch` command (CR-P3T30-04): its
    profiles come from its manifest, for the Resume and for Copy to a new launch."""
    writer.submit(
        lambda c: c.execute(delete(runner_commands).where(runner_commands.c.run_id == failed_run))
    ).result()
    template = authed_client.get(f"/api/v1/runs/{failed_run}:launch-template").json()
    assert template["profiles"] == ["local"]
    response = resume(authed_client, failed_run)
    assert response.status_code == 201, response.text
    child = response.json()["id"]
    (command,) = [
        c
        for c in StoreSink(writer, settings.runs_root).lease_commands()
        if c.kind == "launch" and c.launch.run_id == child
    ]
    assert LaunchPayload.model_validate(command.payload).profiles == ["local"]


def test_resume_of_a_resume_keeps_the_first_directories(
    authed_client: TestClient, writer: Writer, settings: Settings, failed_run: str
) -> None:
    first = resume(authed_client, failed_run).json()["id"]
    end(writer, settings, first, "failed")
    second = resume(authed_client, first)
    assert second.status_code == 201, second.text
    (row,) = children(writer, first)
    assert (row.lineage_id, row.launch_dir) == (
        failed_run,
        str(run_paths(settings.runs_root, failed_run).launch_dir),
    )


def test_resume_states(
    authed_client: TestClient, writer: Writer, settings: Settings, synthetic: Path
) -> None:
    for state, status, reason in (
        ("succeeded", 409, "not_failed_or_cancelled"),
        ("running", 409, "running"),
        ("queued", 409, "running"),
    ):
        run_id = launch(authed_client, synthetic / "nextflow")
        end(writer, settings, run_id, state)
        refused(resume(authed_client, run_id), status, reason)
        assert resume(authed_client, run_id).json()["type"] == "/problems/run-state-conflict"
        assert children(writer, run_id) == []
    observed = launch(authed_client, synthetic / "nextflow")
    end(writer, settings, observed, "failed", origin="cli-observed")
    response = resume(authed_client, observed)
    assert response.status_code == 422, response.text
    assert response.json()["type"] == "/problems/not-in-this-version"
    cancelled = launch(authed_client, synthetic / "nextflow")
    end(writer, settings, cancelled, "cancelled")
    assert resume(authed_client, cancelled).status_code == 201
    assert resume(authed_client, "run_01K8T2F1XTVRES000000000299").status_code == 404


def test_resume_actions_field(
    authed_client: TestClient, writer: Writer, settings: Settings, synthetic: Path
) -> None:
    expected = {
        "failed": {"allowed": True, "reason": None},
        "cancelled": {"allowed": True, "reason": None},
        "succeeded": {"allowed": False, "reason": "not_failed_or_cancelled"},
        "running": {"allowed": False, "reason": "running"},
    }
    for state, action in expected.items():
        run_id = launch(authed_client, synthetic / "nextflow")
        end(writer, settings, run_id, state)
        found = authed_client.get(f"/api/v1/runs/{run_id}").json()
        assert found["actions"] == {"resume": action}, state
        assert (found["parent_run_id"], found["resumed_as"]) == (None, [])
    observed = launch(authed_client, synthetic / "nextflow")
    end(writer, settings, observed, "failed", origin="cli-observed")
    found = authed_client.get(f"/api/v1/runs/{observed}").json()
    assert found["actions"]["resume"] == {"allowed": False, "reason": "cli_observed"}
    unverified = launch(authed_client, synthetic / "nextflow")
    end(writer, settings, unverified, "failed")
    head_pid(settings, unverified, my_head_line(host="elsewhere"))
    found = authed_client.get(f"/api/v1/runs/{unverified}").json()
    assert found["actions"]["resume"] == {"allowed": False, "reason": "head_unverified"}


@pytest.mark.parametrize(
    ("body", "slug"),
    [
        ({"mode": "rerun_from"}, "not-in-this-version"),
        ({"mode": "fresh"}, "not-in-this-version"),
        ({"mode": "resume", "params_patch": {"chunks": 3}}, "not-in-this-version"),
        ({"mode": "resume", "dry_run": True}, "not-in-this-version"),
        ({}, "validation-failed"),
        ({"mode": "again"}, "validation-failed"),
        ({"mode": "resume", "colour": 1}, "validation-failed"),
    ],
)
def test_resume_other_fields_422(
    authed_client: TestClient, writer: Writer, failed_run: str, body: dict[str, Any], slug: str
) -> None:
    response = resume(authed_client, failed_run, json=body)
    assert response.status_code == 422, response.text
    assert response.json()["type"] == f"/problems/{slug}"
    assert children(writer, failed_run) == []


def test_req16_relaunch_origin_csrf(
    authed_client: TestClient, writer: Writer, failed_run: str
) -> None:
    """Req. 7: no Origin, or another site's, is refused before the route. The CSRF token of
    req. 7 comes with the session: TODO(P1 Task 16) add the no-token case here."""
    url = f"/api/v1/runs/{failed_run}:relaunch"
    origin = authed_client.headers["origin"]
    del authed_client.headers["origin"]
    assert authed_client.post(url, json={"mode": "resume"}).status_code == 403
    foreign = {"Origin": "http://evil.example"}
    assert authed_client.post(url, json={"mode": "resume"}, headers=foreign).status_code == 403
    authed_client.headers["origin"] = origin
    assert children(writer, failed_run) == []


def test_req16_parent_head_unverified_409(
    authed_client: TestClient, writer: Writer, settings: Settings, failed_run: str
) -> None:
    for line, reason in (
        (my_head_line(host="node-b"), "head_unverified"),  # another node: cannot be checked
        (my_head_line(boot="00000000-0000-4000-8000-000000000000"), "head_unverified"),
        (my_head_line(), "running"),  # alive here
        ("not a pid line\n", "head_unverified"),
    ):
        head_pid(settings, failed_run, line)
        refused(resume(authed_client, failed_run), 409, reason)
    assert children(writer, failed_run) == []
    gone = f"999999999 999999999 1 {boot_id()} {socket.gethostname()}\n"  # no such process
    head_pid(settings, failed_run, gone)
    assert resume(authed_client, failed_run).status_code == 201


def test_req16_one_child_parallel(
    authed_client: TestClient, writer: Writer, failed_run: str
) -> None:
    """The one-child check and the insert are one BEGIN IMMEDIATE transaction."""
    barrier, found = threading.Barrier(2), []

    def post() -> None:
        barrier.wait()
        found.append(resume(authed_client, failed_run))

    threads = [threading.Thread(target=post) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(r.status_code for r in found) == [201, 409]
    refused(next(r for r in found if r.status_code == 409), 409, "resume_in_progress")
    assert len(children(writer, failed_run)) == 1


def test_req16_no_unlock_when_live(
    authed_client: TestClient, writer: Writer, settings: Settings, synthetic: Path
) -> None:
    """A Snakemake started by hand in the launch directory: a process of the user whose working
    directory is there. No child, so no `--unlock`."""
    run_id = launch(authed_client, synthetic / "snakemake", "snakemake")
    end(writer, settings, run_id)
    launch_dir = run_paths(settings.runs_root, run_id).launch_dir
    by_hand = subprocess.Popen([SLEEP, "30"], cwd=launch_dir / ".spectio")
    try:
        refused(resume(authed_client, run_id), 409, "running")
    finally:
        by_hand.kill()
        by_hand.wait()
    assert children(writer, run_id) == []
    assert resume(authed_client, run_id).status_code == 201


@pytest.mark.parametrize("planted", ["group-writable config", "foreign .nextflow", "symlink"])
def test_req16_planted_config(
    authed_client: TestClient, writer: Writer, settings: Settings, failed_run: str, planted: str
) -> None:
    launch_dir = run_paths(settings.runs_root, failed_run).launch_dir
    if planted == "group-writable config":
        (launch_dir / "nextflow.config").write_text("process.executor = 'local'\n")
        (launch_dir / "nextflow.config").chmod(0o664)
    elif planted == "symlink":
        (launch_dir / "nextflow.config").symlink_to("/etc/hostname")
    else:
        if os.geteuid() != 0:
            pytest.skip("chown to another uid needs root")
        (launch_dir / ".nextflow").mkdir(mode=0o700)
        os.chown(launch_dir / ".nextflow", 4321, 4321)
    refused(resume(authed_client, failed_run), 409, "launch_dir_refused")
    assert children(writer, failed_run) == []


def test_req16_session_id_uuid(
    authed_client: TestClient, writer: Writer, settings: Settings, failed_run: str
) -> None:
    end(writer, settings, failed_run, launch={"engine_session_id": "x; rm -rf ~"})
    refused(resume(authed_client, failed_run), 409, "session_id_refused")
    assert children(writer, failed_run) == []
    found = authed_client.get(f"/api/v1/runs/{failed_run}").json()
    assert found["actions"]["resume"] == {"allowed": False, "reason": "session_id_refused"}


@pytest.mark.parametrize("which", ["launch", "work"])
def test_resume_rechecks_dirs(
    authed_client: TestClient, writer: Writer, settings: Settings, failed_run: str, which: str
) -> None:
    """Req. 10 again on the parent's directories before the child's head starts there."""
    (run_paths(settings.runs_root, failed_run).run_dir / which).chmod(0o770)
    refused(resume(authed_client, failed_run), 409, "launch_dir_refused")
    assert children(writer, failed_run) == []


# --- Copy: the command and the launch template ----------------------------------------------


def test_command_quoted(
    authed_client: TestClient, writer: Writer, settings: Settings, synthetic: Path, tmp_path: Path
) -> None:
    location = tmp_path / "p" / "a b'$(x)"
    shutil.copytree(synthetic / "nextflow", location)
    value = "x\n$(rm -rf ~)"
    run_id = launch(authed_client, location, params={"fail_sample": value}, profiles=["local"])
    command = authed_client.get(f"/api/v1/runs/{run_id}").json()["command"]
    argv = command["argv"]
    assert argv[:3] == ["nextflow", "run", str(location)]  # one word, verbatim
    spectio = run_paths(settings.runs_root, run_id).launch_dir / ".spectio"
    assert argv[argv.index("-params-file") + 1] == str(spectio / "params.json")
    assert value not in command["text"] and "rm -rf" not in command["text"]
    assert command["text"] == shlex.join(argv) and shlex.split(command["text"]) == argv

    end(writer, settings, run_id)
    child = resume(authed_client, run_id).json()
    argv = child["command"]["argv"]
    assert argv[argv.index("-resume") + 1] == SESSION
    assert argv[argv.index("-work-dir") + 1] == str(run_paths(settings.runs_root, run_id).work_dir)

    observed = launch(authed_client, location)
    end(writer, settings, observed, origin="cli-observed")
    assert authed_client.get(f"/api/v1/runs/{observed}").json()["command"] is None


def test_launch_template(
    authed_client: TestClient, writer: Writer, settings: Settings, failed_run: str, synthetic: Path
) -> None:
    response = authed_client.get(f"/api/v1/runs/{failed_run}:launch-template")
    assert response.status_code == 200, response.text
    template = response.json()
    location = str(synthetic / "nextflow")
    assert template["workflow"] == {"location": location, "revision": None, "engine": "nextflow"}
    assert (template["profiles"], template["params"]) == (["local"], {"chunks": 2})
    assert template["non_default"] == ["chunks"]  # its default is 0
    # the template is a body POST /runs takes as it is
    body = {k: template[k] for k in ("workflow", "profiles", "params")}
    assert authed_client.post("/api/v1/runs", json=body).status_code == 201
    same = launch(authed_client, synthetic / "nextflow", params={"chunks": 0, "outdir": "results"})
    found = authed_client.get(f"/api/v1/runs/{same}:launch-template").json()
    assert found["non_default"] == []
    assert (
        authed_client.get("/api/v1/runs/run_01K8T2F1XTVRES000000000299:launch-template").status_code
        == 404
    )


def test_req16_code_loading_flagged(
    writer: Writer, settings: Settings, synthetic: Path, tmp_path: Path
) -> None:
    extra = {"nextflow": ["-c", str(tmp_path / "site.config")]}
    client = client_for(
        settings.model_copy(update={"engines": EngineOpts(extra_args=extra)}), writer
    )
    location = tmp_path / "pipelines" / "nf"
    shutil.copytree(synthetic / "nextflow", location)
    run_id = launch(client, location, params={"custom_config_base": str(tmp_path / "configs")})
    found = client.get(f"/api/v1/runs/{run_id}:launch-template").json()["code_loading"]
    assert found == [
        {"field": "workflow.location", "value": str(location), "writable_by_others": False},
        {
            "field": "params.custom_config_base",
            "value": str(tmp_path / "configs"),
            "writable_by_others": False,
        },
        {"field": "engine.-c", "value": str(tmp_path / "site.config"), "writable_by_others": False},
    ]
    location.chmod(0o775)
    found = client.get(f"/api/v1/runs/{run_id}:launch-template").json()["code_loading"]
    assert found[0] == {
        "field": "workflow.location",
        "value": str(location),
        "writable_by_others": True,
    }

    smk_extra = {"snakemake": ["--configfile", str(tmp_path / "extra.yaml")]}
    smk = client_for(
        settings.model_copy(update={"engines": EngineOpts(extra_args=smk_extra)}), writer
    )
    smk_id = launch(smk, synthetic / "snakemake", "snakemake")
    fields = [
        e["field"] for e in smk.get(f"/api/v1/runs/{smk_id}:launch-template").json()["code_loading"]
    ]
    assert fields == ["workflow.location", "engine.--configfile"]


@pytest.mark.parametrize(
    "case",
    [
        "other owner",
        "missing under sticky",
        "kept in sticky",
        "symlink",
        "symlink to shared",
        "link in shared",
        "my link in sticky",
        "other's link in sticky",
    ],
)
def test_req16_code_loading_flagged_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """Writable by others (SEC-P3T30-01, SEC-P3T30-02): a path or a directory above it owned
    by another user; a missing file whose nearest directory others can write, sticky or not; a
    symlink judged by its target, not by its own 0777 mode, and by the directory that holds it
    and its owner (one who can repoint it)."""
    mine = tmp_path / "mine"
    mine.mkdir(mode=0o700)
    (mine / "main.nf").write_text("")
    shared = tmp_path / "shared"
    shared.mkdir()
    shared.chmod(0o1777)
    (shared / "kept.config").write_text("")
    (shared / "kept.config").chmod(0o644)

    def owned_by_other(other: Path) -> None:
        real_lstat = os.lstat

        def lstat_as_other(path: Any, *args: Any, **kwargs: Any) -> os.stat_result:
            st = real_lstat(path, *args, **kwargs)
            if Path(path) != other:
                return st
            return os.stat_result((*st[:4], 4321, *st[5:10]))

        monkeypatch.setattr(os, "lstat", lstat_as_other)

    if case == "other owner":
        owned_by_other(mine)
        path, flagged = mine / "main.nf", True
    elif case == "missing under sticky":
        path, flagged = shared / "site.config", True
    elif case == "kept in sticky":
        path, flagged = shared / "kept.config", False
    elif case == "symlink":
        (tmp_path / "link").symlink_to(mine)
        path, flagged = tmp_path / "link" / "main.nf", False
    elif case == "symlink to shared":
        group = tmp_path / "group"
        group.mkdir()
        group.chmod(0o775)
        (group / "main.nf").write_text("")
        (mine / "link").symlink_to(group)
        path, flagged = mine / "link" / "main.nf", True
    elif case == "link in shared":  # /g/lab/pipelines/current -> ~/rnaseq
        open_dir = tmp_path / "open"
        open_dir.mkdir()
        open_dir.chmod(0o777)
        (open_dir / "current").symlink_to(mine)
        path, flagged = open_dir / "current" / "main.nf", True
    else:
        (shared / "current").symlink_to(mine)
        if case == "other's link in sticky":
            owned_by_other(shared / "current")
        path, flagged = shared / "current" / "main.nf", case != "my link in sticky"
    assert writable_by_others(str(path)) is flagged


def test_rebuild_keeps_the_lineage(
    authed_client: TestClient, writer: Writer, settings: Settings, failed_run: str, tmp_path: Path
) -> None:
    """The child's manifest names its parent: an index rebuilt from the run directories gives
    the child its parent, lineage and the parent's directories again (Assumption 21)."""
    child = resume(authed_client, failed_run).json()["id"]
    db_dir = tmp_path / "db2"
    db_dir.mkdir(mode=0o700)
    engine, _ = open_db(db_dir)
    fresh = Writer(engine)
    try:
        config = {"runs_root": str(settings.runs_root)}
        fresh.submit(lambda c: ensure_tenancy(c, "me", "local", config, "0.0.1")).result()
        assert rebuild_index(fresh, settings.runs_root).added == 2
        (row,) = [r for r in rows(fresh, runs) if r.id == child]
    finally:
        fresh.close()
        engine.dispose()
    parent = run_paths(settings.runs_root, failed_run)
    assert (row.parent_run_id, row.lineage_id, row.relaunch_mode) == (
        failed_run,
        failed_run,
        "resume",
    )
    assert (row.launch_dir, row.work_dir) == (str(parent.launch_dir), str(parent.work_dir))
