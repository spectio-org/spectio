"""Spike first-look: write synthetic nf-spectio spools that follow api §14.1.

No Nextflow and no bridge (P1 Task 6) exist yet, so the events are generated here. Each run is a
launch directory with `.spectio/events/nf-spectio-1-0001.jsonl` (0700 directories, 0600 file),
shaped like the T2 captures (tests/fixtures/engine-events/): a FASTQC -> TRIM -> ALIGN -> MULTIQC
pipeline. The trace records carry `script` and `env` on purpose, as the real hook does: the
allow-list must drop them.

    uv run python spikes/first-look/make_spool.py OUT_DIR           # three runs, live one partial
    uv run python spikes/first-look/make_spool.py OUT_DIR --follow  # then append the live one
"""

import argparse
import json
import os
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
PRODUCER = "nf-spectio/0.0.1"
SPOOL_FILE = "nf-spectio-1-0001.jsonl"
PROCESSES = ["FASTQC", "TRIM", "ALIGN", "MULTIQC"]


def ulid() -> str:
    value = (time.time_ns() // 1_000_000) << 80 | secrets.randbits(80)
    return "".join(CROCKFORD[(value >> s) & 31] for s in range(125, -1, -5))


class Run:
    """One synthetic run: its ID, name, launch directory and its event steps, in order."""

    def __init__(self, root: Path, name: str, workflow: str, samples: list[str],
                 retry: str | None = None, terminate: str | None = None,
                 start: datetime | None = None) -> None:
        self.id, self.name, self.workflow = f"run_{ulid()}", name, workflow
        self.launch_dir = root / self.id
        self.session = str(uuid.uuid4())
        self.clock = start or datetime.now(UTC)
        self.seq = 0
        self.task_n = 0
        self.steps = self._plan(samples, retry, terminate)

    # -- events -----------------------------------------------------------------------------

    def _event(self, hook: str, data: dict) -> dict:
        self.seq += 1
        self.clock += timedelta(seconds=4)
        return {
            "v": 1, "id": f"evt_{ulid()}", "run": self.id, "launch": 1, "producer": PRODUCER,
            "seq": self.seq, "time": self.clock.isoformat(timespec="milliseconds").replace(
                "+00:00", "Z"), "type": f"nextflow.{hook}",
            "data": {"runName": self.name, "sessionId": self.session, **data},
        }

    def _task(self, hook: str, process: str, tag: str | None, attempt: int,
              outcome: str | None = None, exit_code: int = 0, action: str | None = None) -> dict:
        self.task_n += 1
        name = f"{process} ({tag})" if tag else process
        data = {"taskId": str(self.task_n), "hash": secrets.token_hex(16), "name": name,
                "process": process, "tag": tag, "attempt": attempt, "cached": False,
                "workDir": f"<launch>/work/{secrets.token_hex(1)}/{secrets.token_hex(15)}"}
        if outcome:
            data |= {"status": outcome, "exitStatus": exit_code, "errorAction": action,
                     "trace": {"status": outcome, "exit": str(exit_code), "attempt": str(attempt),
                               "process": process, "tag": tag, "name": name,
                               "duration": str(secrets.randbelow(90_000) + 4_000),
                               "%cpu": f"{secrets.randbelow(1000) / 10}",
                               "peak_rss": str(secrets.randbelow(2**31)),
                               "native_id": str(4000 + self.task_n),
                               "script": "\n    fake_tool --secret-flag\n    ",
                               "env": "API_TOKEN=must-never-be-stored\n"}}
        return self._event(f"onTask{hook}", data)

    def _plan(self, samples: list[str], retry: str | None, terminate: str | None) -> list[list]:
        steps: list[list] = [[self._event("onFlowCreate", {"nextflow": "26.10.4",
                                                            "resume": False,
                                                            "workDir": "<launch>/work"})]]
        steps.append([self._event("onProcessCreate", {"process": p, "processId": i + 1})
                      for i, p in enumerate(PROCESSES)] + [self._event("onFlowBegin", {})])
        for process in PROCESSES:
            tags = [None] if process == "MULTIQC" else samples
            steps.append([self._task("Pending", process, t, 1) for t in tags])
            steps.append([self._task("Submit", process, t, 1) for t in tags])
            steps.append([self._task("Start", process, t, 1) for t in tags])
            for t in tags:
                key = f"{process}:{t}"
                if key == terminate:
                    steps.append([self._task("Complete", process, t, 1, "FAILED", 1, "TERMINATE"),
                                  self._event("onFlowError", {"process": process, "tag": t}),
                                  self._event("onFlowComplete", {
                                      "success": False, "exitStatus": 1,
                                      "errorMessage": f"Process `{process} ({t})` terminated "
                                                      "with an error exit status (1)"})])
                    return steps
                if key == retry:
                    steps.append([self._task("Complete", process, t, 1, "FAILED", 137, "RETRY")])
                    steps.append([self._task(h, process, t, 2)
                                  for h in ("Pending", "Submit", "Start")])
                    steps.append([self._task("Complete", process, t, 2, "COMPLETED")])
                else:
                    steps.append([self._task("Complete", process, t, 1, "COMPLETED")])
            steps.append([self._event("onProcessTerminate", {"process": process})])
        steps.append([self._event("onFlowComplete", {"success": True, "exitStatus": 0})])
        return steps

    # -- files ------------------------------------------------------------------------------

    def spool(self) -> Path:
        events_dir = self.launch_dir / ".spectio" / "events"
        events_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        for d in (self.launch_dir / ".spectio", events_dir):
            d.chmod(0o700)  # the reader refuses anything wider (dev-env §15.3 req. 12)
        return events_dir / SPOOL_FILE

    def write(self, steps: list[list]) -> None:
        """Append these steps, one JSON line per event, as a bridge would."""
        path = self.spool()
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            for step in steps:
                for event in step:
                    f.write(json.dumps(event, separators=(",", ":")) + "\n")


def build(root: Path) -> tuple[list[Run], Run, list[list]]:
    """Three runs under `root`: two finished, one live. Returns them and the live run's rest."""
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    earlier = datetime.now(UTC) - timedelta(hours=3)
    done = Run(root, "rnaseq-pilot", "demo/rnaseq-mini", ["S01", "S02", "S03", "S04"],
               retry="ALIGN:S03", start=earlier)
    failed = Run(root, "wgs-cohort-12", "demo/variant-mini", ["NA12878", "NA12891", "NA12892"],
                 terminate="TRIM:NA12891", start=earlier + timedelta(minutes=40))
    live = Run(root, "atac-limb-e11", "demo/rnaseq-mini", [f"E11_{i}" for i in range(1, 7)],
               retry="ALIGN:E11_4", start=datetime.now(UTC) - timedelta(minutes=10))
    for run in (done, failed):
        run.write(run.steps)
    cut = 6
    live.write(live.steps[:cut])
    return [done, failed, live], live, live.steps[cut:]


def follow(live: Run, rest: list[list], period: float) -> None:
    """Append the live run's remaining steps, one every `period` seconds."""
    for step in rest:
        time.sleep(period)
        live.write([step])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--follow", action="store_true", help="append the live run over time")
    parser.add_argument("--period", type=float, default=3.0)
    args = parser.parse_args()
    runs, live, rest = build(args.out)
    for run in runs:
        print(run.id, run.name, run.spool())
    if args.follow:
        follow(live, rest, args.period)
