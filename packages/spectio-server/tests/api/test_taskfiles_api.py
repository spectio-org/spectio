"""`GET /tasks/{id}/attempts/{n}/files` and `…/files/{name}` (P1 Task 28; api §5 note of
2026-10-28, Job files; dev-env §15.3 req. 13), and the engine log of `GET /runs/{id}/logs`.

The attempts come from synthetic engine events ingested through the projector, as the runner
would, with paths under the run's directories (`make_run_dirs`).
"""

import threading
import time
from collections import Counter
from collections.abc import Iterator
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
from spectio_server.ids import new_id
from spectio_server.projector.ingest import ingest
from spectio_server.stages import freeze
from spectio_server.stages.freeze import StageSources
from spectio_server.store.schema import attempts, runs, tasks
from spectio_server.store.writer import Writer

from .conftest import add_run

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
    (launch / "nextflow.log").write_text("nf log\n")
    logs = f"{API}/runs/{RUN}/logs"
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
    writer.submit(
        lambda c: c.execute(update(runs).where(runs.c.id == RUN).values(origin="cli-observed"))
    ).result()
    assert authed_client.get(f"{API}/runs/{RUN}/logs").text == "the terminal's log\n"


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
    sources = StageSources(None, settings.runs_root, pool=api_taskfiles.FilePool())
    began = time.monotonic()
    batch = SpoolBatch([event(1, "nextflow.onFlowBegin")], {}, Counter())
    writer.submit(lambda c: ingest(c, launch_id, batch, sources)).result()
    assert time.monotonic() - began < 2
    release.set()
    with writer.engine.connect() as conn:
        assert conn.execute(select(runs.c.state)).scalar_one() == "running"
