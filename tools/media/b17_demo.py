"""A demo server for the shots retaken after the design-system pass (UI-01 to UI-18): Environments and Launch.

Two seeded servers already exist; this script reuses them, so that no Nextflow or Snakemake is needed:

- `app-environments`, `app-environments-phone` and `app-environment-edit` run on the server of `b14_demo.py`
  (`two-cores`, the default, and `eight-cores`);
- `app-launch` and `app-launch-environment` run on the server of `b15_demo.py`, plus one finished run record of
  the synthetic pipeline (copied to `pipelines/synthetic/nextflow`, with `data` and `bin` beside it), so that
  Try a test pipeline lists it. The run record is seeded; nothing is executed.

    .venv/bin/python tools/media/b17_demo.py [--shot app-launch ...]

Same requirements as `b14_demo.py` (the checkout's `.venv`, `web/dist` built, `PLAYWRIGHT_BROWSERS_PATH`).
"""

import argparse
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import b14_demo
import b15_demo
from spectio.runner.rundir import RunManifest, Workflow, make_run_dirs
from spectio_server.store.db import open_db
from spectio_server.store.runs import insert_run
from spectio_server.store.writer import Writer

REPO = Path(__file__).resolve().parents[2]
ENVS = ("app-environments", "app-environments-phone", "app-environment-edit")
LAUNCH = ("app-launch", "app-launch-environment")
SHOTS = ENVS + LAUNCH


def shoot(names, env) -> None:
    for shot in names:  # the names come from the tuples above, not from argv
        subprocess.run([sys.executable, str(REPO / "tools/media/shots.py"), "run", "--shot", shot, "--theme", "both"],
                       check=True, env=env, cwd=REPO)


def seed_synthetic_run(root: Path) -> str:
    """Copy the synthetic Nextflow pipeline under `pipelines/synthetic/` and record one finished run of it."""
    dst = root / "pipelines" / "synthetic"
    for part in ("data", "bin"):
        shutil.copytree(b15_demo.SYNTH / part, dst / part, symlinks=True)
    shutil.copytree(b15_demo.SYNTH / "nextflow", dst / "nextflow", symlinks=True)
    run_id, now = "run_01K8T2F1XTVRB17RZ000000000", datetime.now(UTC) - timedelta(hours=1)
    make_run_dirs(root / "runs", run_id)
    location = str(dst / "nextflow")
    manifest = RunManifest(
        run_id=run_id, name="synthetic-test", params={}, profiles=[], created_at=now,
        workflow=Workflow.model_validate({"location": location, "engine": "nextflow"}),
    )
    engine, _ = open_db(root / "db")
    Writer(engine).submit(lambda c: insert_run(
        c, manifest, source="local", runs_root=root / "runs", now=now, state="succeeded", origin="ui",
        workflow_name="spectio/synthetic", workflow_version="1.0.0")).result()
    return location


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--shot", action="append", choices=SHOTS)
    wanted = set(ap.parse_args().shot or SHOTS)
    if wanted & set(ENVS):
        with b14_demo.running() as (env, _):
            shoot([s for s in ENVS if s in wanted], env)
    if wanted & set(LAUNCH):
        with b15_demo.running() as (env, _):
            env["SPECTIO_DEMO_PIPELINE"] = seed_synthetic_run(b15_demo.ROOT)
            shoot([s for s in LAUNCH if s in wanted], env)


if __name__ == "__main__":
    main()
