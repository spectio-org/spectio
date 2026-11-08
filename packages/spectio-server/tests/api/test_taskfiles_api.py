"""`GET /tasks/{id}/attempts/{n}/files` and `…/files/{name}` (P1 Task 28; api §5 note of
2026-10-28, Job files; dev-env §15.3 req. 13), and the engine log of `GET /runs/{id}/logs`.

The attempts come from synthetic engine events ingested through the projector, as the runner
would, with paths under the run's directories (`make_run_dirs`).
"""

import errno
import os
import shutil
import threading
import time
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, update

from spectio.config import Settings
from spectio.runner.rundir import RunPaths, make_run_dirs
from spectio.runner.types import SpoolBatch
from spectio_sdk.events import SpoolEvent
from spectio_server.api import taskfiles as api_taskfiles
from spectio_server.files import taskfiles
from spectio_server.files.pool import FilePool
from spectio_server.ids import new_id
from spectio_server.projector.ingest import ingest
from spectio_server.stages import freeze
from spectio_server.stages.freeze import StageSources
from spectio_server.store.schema import attempts, events, run_stages, runs, tasks
from spectio_server.store.writer import Writer

from .conftest import add_run, client_for

RUN = "run_01K8T2F1XTVRES0000000000F8"
HASH = ("3f", "0123456789abcdef0123456789abcd")
API = "/api/v1"
MIB = 1048576


def event(n: int, type_: str, **data: Any) -> SpoolEvent:
    engine = type_.split(".")[0]
    return SpoolEvent.model_validate(
        {
            "v": 1,
            "id": f"evt_api{n}",
            "run": RUN,
            "launch": 1,
            "producer": "nf-spectio/0.0.1"
            if engine == "nextflow"
            else "snakemake-logger-spectio/1",
            "seq": n,
            "time": "2026-10-31T09:00:00Z",
            "type": type_,
            "data": data,
        }
    )


def push(writer: Writer, settings: Settings, launch_id: str, *events: SpoolEvent) -> None:
    sources = StageSources(None, settings.runs_root)
    batch = SpoolBatch(list(events), {}, Counter())
    writer.submit(lambda c: ingest(c, launch_id, batch, sources)).result()


class NfTask:
    def __init__(self, client: TestClient, writer: Writer, settings: Settings) -> None:
        self.client, self.writer, self.settings = client, writer, settings
        self.launch_id = add_run(writer, settings, RUN, "nf", "running")
        self.paths: RunPaths = make_run_dirs(settings.runs_root, RUN)
        self.dir = self.paths.work_dir.joinpath(*HASH)
        self.dir.mkdir(parents=True)
        (self.dir / ".command.err").write_text("err\n")
        (self.dir / ".command.out").write_text("out\n")
        self.task("onTaskStart")
        with writer.engine.connect() as conn:
            self.task_id = conn.execute(select(tasks.c.id)).scalar_one()

    def task(self, hook: str, n: int = 1, **trace: Any) -> None:
        workdir = str(self.dir)
        data: dict[str, Any] = {
            "process": "ALIGN",
            "tag": "S01",
            "attempt": 1,
            "workDir": workdir,
            "trace": {"native_id": "8812345", "workdir": workdir, **trace},
        }
        push(self.writer, self.settings, self.launch_id, event(n, f"nextflow.{hook}", **data))

    def url(self, name: str = "") -> str:
        base = f"{API}/tasks/{self.task_id}/attempts/1/files"
        return f"{base}/{name}" if name else base

    def get(self, name: str = "", **kwargs: Any) -> Any:
        return self.client.get(self.url(name), **kwargs)


@pytest.fixture
def nf_task(authed_client: TestClient, writer: Writer, settings: Settings) -> NfTask:
    return NfTask(authed_client, writer, settings)


def problem(response: Any, status: int, slug: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["type"] == f"/problems/{slug}"


def test_files_listed(nf_task: NfTask) -> None:
    body = nf_task.get().json()
    assert body["work_dir"] == str(nf_task.dir)
    states = {f["name"]: f["state"] for f in body["files"]}
    assert states[".command.err"] == "present"
    assert states[".exitcode"] == "not_yet"  # running: not written yet, no error


def test_nf_file_tail(nf_task: NfTask) -> None:
    data = bytes(range(32, 127)) * 1100  # ~100 KiB of printable text
    (nf_task.dir / ".command.err").write_bytes(data)
    found = nf_task.get(".command.err")
    assert found.status_code == 200
    assert found.content == data[-65536:]
    assert found.headers["content-type"] == "text/plain; charset=utf-8"
    assert found.headers["x-content-type-options"] == "nosniff"
    assert nf_task.get(".command.err", params={"tail": 10}).content == data[-10:]
    problem(nf_task.get(".command.err", params={"tail": MIB + 1}), 422, "validation-failed")


def test_cleaned_workdir_410(nf_task: NfTask) -> None:
    nf_task.task("onTaskComplete", 2, status="COMPLETED", exit="0")
    for child in nf_task.dir.iterdir():
        child.unlink()
    nf_task.dir.rmdir()
    problem(nf_task.get(".command.err"), 410, "log-cleaned")
    assert {f["state"] for f in nf_task.get().json()["files"]} == {"cleaned"}


def test_not_written_yet(nf_task: NfTask) -> None:
    found = nf_task.get(".exitcode")
    problem(found, 404, "log-not-found")
    assert "not written yet" in found.json()["detail"]


def test_binary_415(nf_task: NfTask) -> None:
    (nf_task.dir / ".command.out").write_bytes(b"BAM\x00" + b"x" * 100)
    problem(nf_task.get(".command.out"), 415, "binary-file")


def test_req13_deep_wrapper_served_hidden(nf_task: NfTask) -> None:
    """A `.command.run` nested 2000 deep is served, every line hidden: not a 500
    (SEC-P3T28-04)."""
    (nf_task.dir / ".command.run").write_text("X=" + "$(" * 2000 + ")" * 2000 + "\necho\n")
    found = nf_task.get(".command.run")
    assert found.status_code == 200, found.text
    assert found.text == "«hidden»\n«hidden»\n"


@pytest.mark.parametrize(
    ("code", "status", "slug"),
    [
        (errno.ENAMETOOLONG, 404, "log-not-found"),
        (errno.EIO, 503, "runner-offline"),
        (errno.ESTALE, 503, "runner-offline"),
    ],
)
def test_req13_os_errors_mapped(
    nf_task: NfTask, monkeypatch: pytest.MonkeyPatch, code: int, status: int, slug: str
) -> None:
    """Any other `OSError` of a read or a listing is a problem with a fixed text, never a 500
    or the path (SEC-P3T28-04)."""

    def failing(*args: Any, **kwargs: Any) -> Any:
        raise OSError(code, "secret detail", "/secret/path")

    monkeypatch.setattr(api_taskfiles, "read_task_file", failing)
    monkeypatch.setattr(api_taskfiles, "list_task_files", failing)
    for found in (nf_task.get(".command.err"), nf_task.get()):
        problem(found, status, slug)
        assert "secret" not in found.text


def test_req13_name_outside_allow_list_422(nf_task: NfTask) -> None:
    (nf_task.dir / ".command.env").write_text("SECRET=1\n")
    for name in (".command.env", "..%2Fx", "%2Fetc%2Fpasswd", "reads.fq", ".spectio/head.out"):
        problem(nf_task.get(name), 422, "file-not-allowed")


def test_req13_job_file_symlink_422(nf_task: NfTask) -> None:
    other = nf_task.paths.work_dir / "de" / "fedcba9876543210fedcba98765432"
    other.mkdir(parents=True)
    (other / ".command.env").write_text("SECRET=1\n")
    err = nf_task.dir / ".command.err"
    err.unlink()
    err.symlink_to(other / ".command.env")
    problem(nf_task.get(".command.err"), 422, "file-not-allowed")
    listed = {f["name"]: f for f in nf_task.get().json()["files"]}[".command.err"]
    assert listed["note"].startswith("Not served")


def test_req13_escape_sequences_removed(nf_task: NfTask) -> None:
    text = "\x1b[31mred\x1b[0m \x1b]8;;http://evil.example\x07link\x1b]8;;\x07 bell\x07 done\n"
    (nf_task.dir / ".command.err").write_text(text)
    assert nf_task.get(".command.err").text == "red link bell done\n"


def test_req13_headers(nf_task: NfTask) -> None:
    found = nf_task.get(".command.err", params={"download": "true"})
    assert found.headers["cache-control"] == "no-store"
    assert found.headers["referrer-policy"] == "no-referrer"
    assert found.headers["content-disposition"] == "attachment; filename*=UTF-8''.command.err"
    problem(nf_task.get(".command.err%07"), 422, "file-not-allowed")
    listing = nf_task.get()
    assert listing.headers["cache-control"] == "no-store"


def test_req13_range_capped(nf_task: NfTask) -> None:
    data = b"y" * (2 * MIB)
    (nf_task.dir / ".command.err").write_bytes(data)
    found = nf_task.get(".command.err", headers={"Range": f"bytes=0-{5 * MIB - 1}"})
    assert found.status_code == 206
    assert len(found.content) == MIB
    assert found.headers["content-range"] == f"bytes 0-{MIB - 1}/{2 * MIB}"
    problem(nf_task.get(".command.err", headers={"Range": "bytes=9-1"}), 422, "validation-failed")


def test_unknown_attempt_404(nf_task: NfTask) -> None:
    problem(nf_task.client.get(f"{API}/tasks/{nf_task.task_id}/attempts/9/files"), 404, "not-found")
    problem(nf_task.client.get(f"{API}/tasks/tsk_nope/attempts/1/files"), 404, "not-found")


CHILD = "run_01K8T2F1XTVRES0000000000F9"


def test_resumed_child_reads_the_lineage_dirs(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    """A Resume runs in its lineage root's directories (CR-P3T30-01): the child's task
    directory under the parent's work directory is kept, and its files are listed from there;
    a Snakemake child's engine log is read from the parent's launch directory."""
    add_run(writer, settings, RUN, "nf", "failed")
    parent = make_run_dirs(settings.runs_root, RUN)
    lineage: dict[str, Any] = {"parent_run_id": RUN, "lineage_id": RUN, "relaunch_mode": "resume"}
    launch_id = add_run(writer, settings, CHILD, "nf-resume", "running", **lineage)
    make_run_dirs(settings.runs_root, CHILD)
    task_dir = parent.work_dir.joinpath(*HASH)
    task_dir.mkdir(parents=True)
    (task_dir / ".command.err").write_text("err\n")
    workdir = str(task_dir)
    data = {"process": "ALIGN", "attempt": 1, "workDir": workdir, "trace": {"workdir": workdir}}
    started = event(1, "nextflow.onTaskStart", **data).model_copy(update={"run": CHILD})
    push(writer, settings, launch_id, started)
    with writer.engine.connect() as conn:
        task_id, kept = conn.execute(
            select(tasks.c.id, attempts.c.work_dir)
            .join(attempts, attempts.c.task_id == tasks.c.id)
            .where(tasks.c.run_id == CHILD)
        ).one()
    assert kept == workdir
    body = authed_client.get(f"{API}/tasks/{task_id}/attempts/1/files").json()
    assert body["work_dir"] == workdir
    assert {f["name"]: f["state"] for f in body["files"]}[".command.err"] == "present"

    smk = "run_01K8T2F1XTVRES0000000000FA"
    add_run(writer, settings, smk, "smk-resume", "running", engine="snakemake", **lineage)
    make_run_dirs(settings.runs_root, smk)
    (parent.launch_dir / ".snakemake" / "log").mkdir(parents=True)
    (parent.launch_dir / ".snakemake" / "log" / "a.snakemake.log").write_text("smk log\n")
    assert authed_client.get(f"{API}/runs/{smk}/logs").text == "smk log\n"


# --- Snakemake names: equal to a recorded path, byte for byte (SEC-156) ---------------------


@pytest.fixture
def smk_attempt(authed_client: TestClient, writer: Writer, settings: Settings) -> str:
    """A Snakemake attempt whose recorded paths are written directly: as a forged event would
    have left them before the projector's checks."""
    add_run(writer, settings, RUN, "smk", "running", engine="snakemake")
    launch = make_run_dirs(settings.runs_root, RUN).launch_dir
    (launch / "logs").mkdir()
    (launch / "logs" / "a.log").write_text("rule a\n")
    for name, text in (("head.out", "head\n"), ("manifest.json", "{}"), ("sacct.json", "{}")):
        (launch / ".spectio" / name).write_text(text)
    task_id = new_id("tsk")
    logs = [
        {"path": "logs/a.log", "kind": "rule_log"},
        {"path": ".spectio/head.out", "kind": "rule_log"},
        {"path": ".spectio/manifest.json", "kind": "rule_log"},
        {"path": ".spectio/sacct.json", "kind": "rule_log"},
    ]

    def write(conn: Any) -> None:
        now = conn.execute(select(runs.c.created_at)).scalar_one()
        conn.execute(
            insert(tasks).values(
                id=task_id, created_at=now, run_id=RUN, process_or_rule="a", state="running"
            )
        )
        conn.execute(
            insert(attempts).values(
                id=new_id("att"),
                created_at=now,
                task_id=task_id,
                n=1,
                launch_n=1,
                state="running",
                logs=logs,
            )
        )

    writer.submit(write).result()
    return task_id


def test_runs_root_missing_409(
    writer: Writer, settings: Settings, smk_attempt: str, tmp_path: Path
) -> None:
    """FU-P3-81: a runs root that is not there is not a cleaned launch directory."""
    missing = tmp_path / "scratch" / "runs"
    client = client_for(settings.model_copy(update={"runs_root": missing}), writer)
    base = f"{API}/tasks/{smk_attempt}/attempts/1/files"
    found = client.get(f"{base}/logs/a.log")
    problem(found, 409, "run-dir-unreachable")
    assert str(missing / RUN / "launch") in found.json()["detail"]
    problem(client.get(base), 409, "run-dir-unreachable")


def test_other_runs_root_409(
    writer: Writer, settings: Settings, smk_attempt: str, tmp_path: Path
) -> None:
    """FU-P3-81 r1: a run recorded under another runs root, served from one that exists, is
    not a cleaned launch directory: the listing and the read both answer 409."""
    other = tmp_path / "other-runs"
    other.mkdir(mode=0o700)
    client = client_for(settings.model_copy(update={"runs_root": other}), writer)
    base = f"{API}/tasks/{smk_attempt}/attempts/1/files"
    found = client.get(f"{base}/logs/a.log")
    problem(found, 409, "run-dir-unreachable")
    assert str(settings.runs_root) in found.json()["detail"]
    problem(client.get(base), 409, "run-dir-unreachable")


def test_terminal_run_is_not_under_a_runs_root(
    authed_client: TestClient, writer: Writer, settings: Settings, smk_attempt: str
) -> None:
    """FU-P3-81 r2 (CR-P3FU81-03): a run started in a terminal records its own project as its
    launch directory, not `<runs root>/<run>/launch`: its job files are never answered 409
    naming the project's grandparent as a runs root."""
    project = settings.runs_root.parent / "project"
    project.mkdir()
    shutil.rmtree(settings.runs_root / RUN)  # nothing under the runs root for this run
    observed = {"origin": "cli-observed", "launch_dir": str(project)}
    writer.submit(
        lambda c: c.execute(update(runs).where(runs.c.id == RUN).values(**observed))
    ).result()
    base = f"{API}/tasks/{smk_attempt}/attempts/1/files"
    listing = authed_client.get(base)
    assert listing.status_code == 200, listing.text
    assert {f["state"] for f in listing.json()["files"]} == {"cleaned"}
    found = authed_client.get(f"{base}/logs/a.log")
    problem(found, 410, "log-cleaned")
    assert found.json()["detail"].endswith(f"tried {settings.runs_root / RUN / 'launch'}")
    for answer in (listing, found):
        assert "runs root" not in answer.text
        assert str(project) not in answer.text


def test_nf_other_runs_root_409(nf_task: NfTask, tmp_path: Path) -> None:
    """FU-P3-81 r1: a Nextflow work directory recorded under another runs root is not a missing
    work directory (404) nor a cleaned one."""
    other = tmp_path / "other-runs"
    other.mkdir(mode=0o700)
    nf_task.client = client_for(
        nf_task.settings.model_copy(update={"runs_root": other}), nf_task.writer
    )
    problem(nf_task.get(".command.err"), 409, "run-dir-unreachable")
    problem(nf_task.get(), 409, "run-dir-unreachable")


def test_req13_smk_name_exact(authed_client: TestClient, smk_attempt: str) -> None:
    base = f"{API}/tasks/{smk_attempt}/attempts/1/files"
    assert authed_client.get(f"{base}/logs/a.log").text == "rule a\n"
    # ".%2F": a client folds a literal "./" away before it is sent
    for name in ("logs/a.lo", "logs/a.log ", "logs/b.log", "logs//a.log", ".%2Flogs/a.log"):
        problem(authed_client.get(f"{base}/{name}"), 422, "file-not-allowed")


def test_req13_spectio_dir(
    authed_client: TestClient, smk_attempt: str, writer: Writer, settings: Settings
) -> None:
    base = f"{API}/tasks/{smk_attempt}/attempts/1/files"
    assert authed_client.get(f"{base}/.spectio/head.out").text == "head\n"
    for name in (".spectio/manifest.json", ".spectio/sacct.json"):
        problem(authed_client.get(f"{base}/{name}"), 422, "file-not-allowed")
    launch = settings.runs_root / RUN / "launch" / ".spectio"
    (launch / "head.err").write_text("head err\n")
    logs = f"{API}/runs/{RUN}/logs"  # `.spectio/nextflow.log`: test_engine_log_from_the_run
    assert authed_client.get(logs, params={"source": "head-out"}).text == "head\n"
    assert authed_client.get(logs, params={"source": "head-err"}).text == "head err\n"


def test_engine_log_from_the_run(
    authed_client: TestClient, writer: Writer, settings: Settings
) -> None:
    """A run Spectio launched logs to `.spectio/nextflow.log` (NXF_LOG_FILE); one from a
    terminal keeps `.nextflow.log` in its launch directory (architecture §13.7)."""
    add_run(writer, settings, RUN, "nf", "running")
    launch = make_run_dirs(settings.runs_root, RUN).launch_dir
    (launch / ".nextflow.log").write_text("the terminal's log\n")
    (launch / ".spectio" / "nextflow.log").write_text("\x1b[1mthis run's log\x1b[0m\n")
    found = authed_client.get(f"{API}/runs/{RUN}/logs")
    assert found.text == "this run's log\n"
    assert found.headers["referrer-policy"] == "no-referrer"

    # A run from a terminal: its own launch directory, outside the runs root (P1 Task 25).
    terminal = settings.runs_root.parent / "project"
    terminal.mkdir()
    terminal.chmod(0o770)  # a project directory is often group-writable: not checked
    (terminal / ".nextflow.log").write_text("the project's log\n")
    observed = {"origin": "cli-observed", "launch_dir": str(terminal)}
    writer.submit(
        lambda c: c.execute(update(runs).where(runs.c.id == RUN).values(**observed))
    ).result()
    assert authed_client.get(f"{API}/runs/{RUN}/logs").text == "the project's log\n"


@pytest.mark.parametrize("how", ["symlink", "fifo", "foreign", "in_runs_root", "relative"])
def test_terminal_log_symlink_fifo_foreign_refused(
    authed_client: TestClient, writer: Writer, settings: Settings, how: str
) -> None:
    """Req. 12, "Server, reads": a terminal run's engine log is read only when it is a regular
    file of the user, opened with O_NOFOLLOW|O_NONBLOCK; otherwise "log not readable". Its
    launch directory must still pass the scan's check."""
    add_run(writer, settings, RUN, "nf", "running")
    terminal = settings.runs_root.parent / "project"
    terminal.mkdir()
    log = terminal / ".nextflow.log"
    secret = settings.runs_root.parent / "secret"
    secret.write_text("not the log\n")
    launch_dir = str(terminal)
    if how == "symlink":
        log.symlink_to(secret)
    elif how == "fifo":
        os.mkfifo(log)
    elif how == "foreign":
        if os.geteuid() != 0:
            pytest.skip("needs root to make another user's file")
        log.write_text("theirs\n")
        os.chown(log, 4242, 4242)
    elif how == "in_runs_root":
        launch_dir = str(make_run_dirs(settings.runs_root, RUN).launch_dir)
        (Path(launch_dir) / ".nextflow.log").write_text("a driven run's log\n")
    else:
        launch_dir = "project"
    observed = {"origin": "cli-observed", "launch_dir": launch_dir}
    writer.submit(
        lambda c: c.execute(update(runs).where(runs.c.id == RUN).values(**observed))
    ).result()
    found = authed_client.get(f"{API}/runs/{RUN}/logs")
    assert found.status_code == 404, found.text
    assert "log not readable" in found.json()["detail"]


# --- A stalled file system never stops the events (req. 13, SEC-157) --------------------------


@pytest.fixture
def slow_fs(monkeypatch: pytest.MonkeyPatch) -> Iterator[threading.Event]:
    """Every job-file read blocks until the event is set, or 30 s; the pool gives up after
    0.2 s."""
    release = threading.Event()
    real = taskfiles.read_task_file

    def stalled(*args: Any, **kwargs: Any) -> Any:
        release.wait(30)
        return real(*args, **kwargs)

    monkeypatch.setattr(api_taskfiles, "read_task_file", stalled)
    monkeypatch.setattr(api_taskfiles, "READ_TIMEOUT_S", 0.2)
    yield release
    release.set()


def test_req13_file_pool_separate(nf_task: NfTask, slow_fs: threading.Event) -> None:
    answers: list[Any] = []
    reader = threading.Thread(target=lambda: answers.append(nf_task.get(".command.err")))
    reader.start()
    time.sleep(0.05)  # the read is in the file pool, stalled
    began = time.monotonic()
    nf_task.task("onTaskComplete", 2, status="COMPLETED", exit="0")  # through the writer
    assert time.monotonic() - began < 0.5
    with nf_task.writer.engine.connect() as conn:
        assert conn.execute(select(attempts.c.state)).scalar_one() == "succeeded"
    reader.join(5)
    problem(answers[0], 503, "runner-offline")


def test_req13_freeze_reads_off_the_writer(
    writer: Writer, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The freeze's sources (overlays, spectio.yml, rules.txt, Snakemake files) are read in
    the file pool too: a stalled one gives no stages after the timeout (SEC-P3T27-03)."""
    launch_id = add_run(writer, settings, RUN, "nf", "running")
    release = threading.Event()

    def stalled(*args: Any, **kwargs: Any) -> Any:
        release.wait(30)
        raise AssertionError("not reached in time")

    monkeypatch.setattr(freeze, "_sources", stalled)
    monkeypatch.setattr(freeze, "FREEZE_TIMEOUT_S", 0.2)
    sources = StageSources(None, settings.runs_root, pool=FilePool())
    began = time.monotonic()
    batch = SpoolBatch([event(1, "nextflow.onFlowBegin")], {}, Counter())
    writer.submit(lambda c: ingest(c, launch_id, batch, sources)).result()
    assert time.monotonic() - began < 2
    release.set()
    with writer.engine.connect() as conn:
        assert conn.execute(select(runs.c.state)).scalar_one() == "running"
        assert conn.execute(select(run_stages.c.id)).all() == []  # no stages (CR-P3T28-05 r2)
        frozen = conn.execute(
            select(events.c.payload).where(events.c.type == freeze.FROZEN)
        ).scalar_one()
    assert frozen["note"] == (
        "The stage sources were not read in time (the file system did not answer)."
    )
