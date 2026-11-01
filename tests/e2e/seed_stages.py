"""Seed a run directory with the rnaseq preview events, for the stages check of the Playwright
smoke (P1 Task 27, Step 4): `spectio serve` adds it to the index at boot (Task 11), adopts its
ended head and replays its spool, and the run shows 8 detected stages above its processes.

    uv run python tests/e2e/seed_stages.py <runs_root>

The events are `tests/pipelines/real/stages/events/rnaseq-3.27.0_star_salmon_preview_events.jsonl`
(onFlowCreate, 67 onProcessCreate, onFlowBegin, onFlowComplete), written as the spool of launch 1
of run SEEDED; head.pid names a head that has ended (no such process) and head.exit says 0.
"""

import json
import socket
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from spectio.runner.rundir import (
    RunManifest,
    Workflow,
    make_run_dirs,
    private_dir,
    write_file,
    write_run_manifest,
)

SEEDED = "run_01K8T27SEEDED0000000000000"
EVENTS = (
    Path(__file__).resolve().parents[1]
    / "pipelines/real/stages/events/rnaseq-3.27.0_star_salmon_preview_events.jsonl"
)
T0 = datetime(2026, 10, 28, 7, 0, tzinfo=UTC)


def spool_lines() -> bytes:
    lines = []
    for n, line in enumerate(EVENTS.read_text().splitlines(), 1):
        body = json.loads(line)["body"]
        data = {k: v for k, v in body.items() if k not in ("hook", "instant", "seq")}
        event = {
            "v": 1,
            "id": f"evt_01K8T27SEEDED{n:012d}",
            "run": SEEDED,
            "launch": 1,
            "producer": "nf-spectio/0.0.1",
            "seq": n,
            "time": (T0 + timedelta(seconds=n)).isoformat().replace("+00:00", "Z"),
            "type": f"nextflow.{body['hook']}",
            "data": data,
        }
        lines.append(json.dumps(event) + "\n")
    return "".join(lines).encode()


def main(runs_root: Path) -> None:
    paths = make_run_dirs(runs_root, SEEDED)
    manifest = RunManifest(
        run_id=SEEDED,
        name="rnaseq-stages-seeded",
        workflow=Workflow(location="/pipelines/nf-core-rnaseq", engine="nextflow"),
        params={},
        profiles=["test"],
        created_at=T0,
    )
    write_run_manifest(paths.run_dir, manifest)
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    with private_dir(runs_root, SEEDED, "launch", ".spectio", "events") as fd:
        write_file(fd, "nf-spectio-1-0001.jsonl", spool_lines())
    with private_dir(runs_root, SEEDED, "launch", ".spectio") as fd:
        pid = 4194303  # above Linux's default pid_max: never a live process
        host = socket.gethostname()
        write_file(fd, "head.pid", f"{pid} {pid} 1 {boot} {host}\n".encode())
        write_file(fd, "head.exit", f"0 {int(T0.timestamp()) + 90}\n".encode())
    print(SEEDED)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
