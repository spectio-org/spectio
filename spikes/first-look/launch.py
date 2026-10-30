"""Spike first-look, part 2: register runs, start a real `nextflow run`, receive the plugin's POSTs.

Stands in for what P1 does elsewhere (launch API Task 17, head launcher, bridge Task 6), reduced
to what a local demo needs:

- `register` writes the project, run and launch rows the launch API would write;
- `start` runs `nextflow run spikes/first-look/nf/main.nf -plugins nf-spectio@0.0.1` in the run's
  launch directory, with SPECTIO_ENDPOINT set to a per-launch URL on this server;
- `receive` takes one plugin POST (spike T2 format) and appends it as one spool line of
  api §14.1 to `<launch dir>/.spectio/events/nf-spectio-1-0001.jsonl`, with the mapping of
  tests/fixtures/engine-events/convert_t2.py (imported, not copied);
- `watch` reports the head's start and end through the real `apply_head_report`.

Throwaway: no auth, no quotas, nothing of P1 Tasks 11-16.
"""

import importlib.util
import json
import os
import secrets
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import insert

from spectio.runner.spool import read_spool
from spectio.runner.types import Failure, HeadReport
from spectio_server.ids import new_id
from spectio_server.projector.ingest import apply_head_report, ingest, load_cursor
from spectio_server.store.schema import (environments, launches, projects, runs,
                                         workflow_versions, workflows)
from spectio_server.store.writer import Writer

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MAIN_NF = HERE / "nf" / "main.nf"
PLUGIN = "nf-spectio@0.0.1"
SPOOL_FILE = "nf-spectio-1-0001.jsonl"
MAX_POST_BYTES = 1 << 20

_spec = importlib.util.spec_from_file_location(
    "convert_t2", REPO / "tests" / "fixtures" / "engine-events" / "convert_t2.py")
convert_t2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(convert_t2)


@dataclass
class Launch:
    run_id: str
    launch_id: str
    launch_dir: Path
    token: str = ""  # the secret path part of this launch's event URL; empty for synthetic runs
    proc: subprocess.Popen | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


class Registry:
    """The launches the poller reads, by run and by event token."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_run: dict[str, Launch] = {}

    def add(self, launch: Launch) -> None:
        with self._lock:
            self._by_run[launch.run_id] = launch

    def all(self) -> list[Launch]:
        with self._lock:
            return list(self._by_run.values())

    def by_run(self, run_id: str) -> Launch | None:
        with self._lock:
            return self._by_run.get(run_id)

    def by_token(self, token: str) -> Launch | None:
        with self._lock:
            return next((x for x in self._by_run.values()
                         if x.token and secrets.compare_digest(x.token, token)), None)


# -- rows ----------------------------------------------------------------------------------


def base_rows(writer: Writer) -> None:
    """The project, environment and dummy workflow every run here belongs to."""
    now = datetime.now(UTC)

    def fn(conn):
        conn.execute(insert(projects).values(id="prj_demo", owning_group_id="grp_demo",
                                             created_at=now, name="demo"))
        conn.execute(insert(environments).values(id="env_local", kind="local", created_at=now))
        conn.execute(insert(workflows).values(id="wfl_dummy", project_id="prj_demo",
                                              source="local", location=str(MAIN_NF),
                                              name="first-look/dummy", engine="nextflow",
                                              created_at=now))
        conn.execute(insert(workflow_versions).values(id="wfv_dummy", workflow_id="wfl_dummy",
                                                      revision="0.1.0", created_at=now))

    writer.submit(fn).result()


def register(writer: Writer, runs_root: Path, name: str, origin: str) -> Launch:
    """What the launch API (P1 Task 17) would write: a queued run, launch 1, its directory."""
    run_id, launch_id = new_id("run"), new_id("lch")
    launch_dir = runs_root / run_id
    for d in (launch_dir, launch_dir / ".spectio", launch_dir / ".spectio" / "events"):
        d.mkdir(mode=0o700)  # the reader refuses anything wider (dev-env §15.3 req. 12)
    now = datetime.now(UTC)

    def fn(conn):
        conn.execute(insert(runs).values(
            id=run_id, project_id="prj_demo", workflow_version_id="wfv_dummy",
            environment_id="env_local", name=name, state="queued", origin=origin,
            launch_dir=str(launch_dir), created_at=now))
        conn.execute(insert(launches).values(id=launch_id, run_id=run_id, n=1,
                                             launch_dir=str(launch_dir), created_at=now))

    writer.submit(fn).result()
    return Launch(run_id, launch_id, launch_dir, token=secrets.token_urlsafe(24))


def nextflow_args(nextflow: str, samples: int, fail: bool) -> list[str]:
    args = [nextflow, "run", str(MAIN_NF), "-plugins", PLUGIN, "--samples", str(samples)]
    return args + ["--fail"] if fail else args


# -- head ----------------------------------------------------------------------------------


def start(writer: Writer, launch: Launch, nextflow: str, endpoint: str, samples: int,
          fail: bool) -> None:
    """Start the head: `nextflow run` in the launch directory, output to nextflow.out."""
    env = {**os.environ, "SPECTIO_ENDPOINT": endpoint, "NXF_ANSI_LOG": "false"}
    out = os.open(launch.launch_dir / "nextflow.out", os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                  0o600)
    try:
        launch.proc = subprocess.Popen(nextflow_args(nextflow, samples, fail),
                                       cwd=launch.launch_dir, env=env, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=subprocess.STDOUT,
                                       start_new_session=True)
    except OSError as e:
        report(writer, launch, HeadReport("exited", None, None, None, True,
                                          Failure("launch_error", f"cannot start nextflow: {e}")))
        return
    finally:
        os.close(out)
    report(writer, launch, HeadReport("running", str(launch.proc.pid), None, None, False, None))
    threading.Thread(target=watch, args=(writer, launch), daemon=True).start()


def watch(writer: Writer, launch: Launch) -> None:
    """Wait for the head; read the spool one last time, then report its end."""
    rc = launch.proc.wait()
    msg = f"nextflow exited {rc} with no terminal engine event (see nextflow.out)"
    # The failure only applies when no onFlowComplete ended the run (apply_head_report).
    report(writer, launch, HeadReport("exited", str(launch.proc.pid), None, rc, True,
                                      Failure("engine_fault", msg)))


def ingest_once(conn, launch: Launch) -> int:
    batch = read_spool(launch.launch_dir, launch.run_id, 1, load_cursor(conn, launch.launch_id))
    ingest(conn, launch.launch_id, batch)
    return len(batch.events)


def report(writer: Writer, launch: Launch, head: HeadReport) -> None:
    def fn(conn):
        ingest_once(conn, launch)  # events first: the engine's own end wins (api §8.2)
        apply_head_report(conn, launch.launch_id, head)

    writer.submit(fn).result()


def tail(launch: Launch, lines: int = 12) -> str:
    """The last lines of the head's output, for the run page."""
    try:
        text = (launch.launch_dir / "nextflow.out").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join([x for x in text.splitlines() if "JAVA_TOOL_OPTIONS" not in x][-lines:])


# -- receiver ------------------------------------------------------------------------------


def receive(launch: Launch, raw: bytes) -> None:
    """Append one plugin POST to the launch's spool as one api §14.1 line. Raises ValueError."""
    body = json.loads(raw)
    if not isinstance(body, dict) or not {"hook", "seq", "instant"} <= body.keys():
        raise ValueError("not an nf-spectio event")
    try:
        event = convert_t2.convert_line("nextflow", launch.token, json.dumps({"body": body}))
    except (TypeError, OverflowError, OSError) as e:  # e.g. an `instant` that is no number
        raise ValueError("not an nf-spectio event") from e
    event["run"] = launch.run_id
    line = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    with launch.lock:
        fd = os.open(launch.launch_dir / ".spectio" / "events" / SPOOL_FILE,
                     os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            os.write(fd, line)  # one write per line: the reader never sees half a line
        finally:
            os.close(fd)

