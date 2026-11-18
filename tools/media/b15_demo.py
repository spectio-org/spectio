"""A demo server for the shots of batch P3-B15: search, the notifications panel, the runs table actions, and run
resources with an extra config file.

Like `b13_demo.py` and `b14_demo.py`, this seeds the store of a throwaway `spectio` server and serves the built
screens (`web/dist`: run `npx vite build` in `web/` first) on a loopback port, then runs `shots.py` against it.
No Nextflow or Snakemake is needed. It seeds:

- `catalog.toml` with three entries and a copy of the synthetic Nextflow pipeline with `conf/test.yaml`, for the
  search results (FU-P3-89) and the catalog picker on Launch (FU-P3-110d);
- `environments.toml` with `two-cores` (2 CPUs, 4 GiB, the default), whose caps the resource hints quote;
- eight run records (succeeded, running, failed, cancelled), for the notifications panel (FU-P3-113), the search
  and the runs table: select, delete, pin and sort (FU-P3-115b);
- one finished run, `rnaseq-tuned`, that was launched with default resources (8 CPUs, 64 GiB, 12 h per task) and an
  extra config file, kept as `launch/.spectio/extra.config` with its SHA-256, for Run detail (FU-P3-110d).

    .venv/bin/python tools/media/b15_demo.py [--shot app-search ...]

Run it from the repository root with the checkout's `.venv` (it imports `spectio_server`) and a Playwright that finds
Chromium (`PLAYWRIGHT_BROWSERS_PATH`). The paths are under `/srv/demo-b15`, and the sidebar names `demo-hpc-login1`
and `alice`, so that no host detail shows on a page (`fixtures.yaml`, `forbidden`).
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import tiff_demo
import uvicorn
from sqlalchemy import update

from spectio.config import Settings, write_config
from spectio.runner.rundir import RunManifest, Workflow, make_run_dirs
from spectio_server.api import me
from spectio_server.app import create_app
from spectio_server.auth.middleware import cookie_name
from spectio_server.bootstrap import ensure_tenancy
from spectio_server.store.db import open_db
from spectio_server.store.runs import insert_run
from spectio_server.store.schema import runs
from spectio_server.store.writer import Writer

REPO = Path(__file__).resolve().parents[2]
ROOT = Path("/srv/demo-b15")
SYNTH = REPO / "tests/pipelines/synthetic"
TUNED = "run_01K8T2F1XTVRB15RZ000000000"
SHOTS = (
    "app-search",
    "app-notifications",
    "app-runs-actions",
    "app-runs-delete",
    "app-launch-resources",
    "app-run-resources",
    "app-run-config-file",
)
CATALOG = """\
[pipelines.rnaseq-test]
label = "RNA-seq test"
engine = "nextflow"
location = "{pipeline}"
profile = "test"
params_file = "conf/test.yaml"

[pipelines.nf-core-rnaseq]
engine = "nextflow"
location = "nf-core/rnaseq"
revision = "3.27.0"
profile = "test"

[pipelines.liver-qc]
label = "Liver QC"
engine = "snakemake"
location = "/srv/demo-b15/pipelines/liver-qc"
"""
ENVIRONMENTS = """\
default = "two-cores"

[environments.two-cores]
label = "Two cores"
executor = "local"

[environments.two-cores.local]
cpus = 2
mem_mib = 4096
"""
CONFIG = """\
// lab-tweaks.config: the lab's settings for the nf-core pipelines
process {
    withName: 'ALIGN' {
        errorStrategy = 'retry'
        maxRetries    = 2
    }
}
"""
# (name, pipeline, engine, state, minutes ago)
RUNS = [
    ("rnaseq-treatA-ctrl", "demo-lab/rnaseq", "nextflow", "succeeded", 35),
    ("rnaseq-treatB-ctrl", "demo-lab/rnaseq", "nextflow", "running", 12),
    ("liver-qc-batch-7", "demo-lab/liver-qc", "snakemake", "succeeded", 190),
    ("rnaseq-treatC-ctrl", "demo-lab/rnaseq", "nextflow", "failed", 340),
    ("liver-qc-batch-6", "demo-lab/liver-qc", "snakemake", "succeeded", 1500),
    ("rnaseq-pilot", "demo-lab/rnaseq", "nextflow", "cancelled", 2900),
    ("rnaseq-tuned", "demo-lab/rnaseq", "nextflow", "succeeded", 60),
]
# Notifications, N unread: the runs that succeeded, failed or were cancelled
UNREAD = sum(1 for r in RUNS if r[3] in ("succeeded", "failed", "cancelled"))


@contextmanager
def running():
    """A seeded server on a loopback port; yields (the environment for `shots.py`, the port)."""
    tiff_demo.demo_identity()
    me.pwd = SimpleNamespace(getpwuid=lambda uid: SimpleNamespace(pw_name="alice"))
    shutil.rmtree(ROOT, ignore_errors=True)
    data_dir, db_dir, runs_root, home = ROOT / "data", ROOT / "db", ROOT / "runs", ROOT / "users" / "alice"
    for p in (data_dir, db_dir, runs_root, home):  # not `/home/…`: a path under it is a forbidden term (`fixtures.yaml`)
        p.mkdir(parents=True, mode=0o700)
    os.environ["HOME"] = str(home)
    os.environ["SPECTIO_CONFIG"] = str(data_dir / "spectio.toml")
    pipeline = ROOT / "pipelines" / "synthetic-rnaseq"
    for part in ("data", "bin"):  # main.nf reads ../data, and bin/synth.py links to ../../bin
        shutil.copytree(SYNTH / part, ROOT / "pipelines" / part, symlinks=True)
    shutil.copytree(SYNTH / "nextflow", pipeline, symlinks=True)
    (pipeline / "conf" / "test.yaml").write_text("chunks: 2\nscale: 1\nseed: 7\n")
    port = tiff_demo.free_port()
    settings = Settings(data_dir=data_dir, db_dir=db_dir, runs_root=runs_root, port=port, executor="local")
    write_config(settings)
    for name, text in (("catalog.toml", CATALOG.format(pipeline=pipeline)), ("environments.toml", ENVIRONMENTS)):
        (data_dir / name).write_text(text)
        (data_dir / name).chmod(0o600)
    engine, _ = open_db(db_dir)
    writer = Writer(engine)
    writer.submit(lambda c: ensure_tenancy(c, "me", settings.executor, {"runs_root": str(runs_root)}, "0.0.1")).result()
    now = datetime.now(UTC)
    for i, (name, flow, eng, state, ago) in enumerate(RUNS):
        run_id = TUNED if name == "rnaseq-tuned" else f"run_01K8T2F1XTVRB15R{i:010d}"
        paths = make_run_dirs(runs_root, run_id)
        created = now - timedelta(minutes=ago)
        extras = {}
        if run_id == TUNED:
            kept = paths.launch_dir / ".spectio" / "extra.config"
            kept.write_text(CONFIG)
            kept.chmod(0o600)
            extras = {
                "default_resources": {"cpus": 8, "mem_mib": 65536, "time_min": 720},
                "config_file": {
                    "path": f"{home}/lab-tweaks.config",
                    "kept_as": "extra.config",
                    "sha256": hashlib.sha256(CONFIG.encode()).hexdigest(),
                    "size": len(CONFIG.encode()),
                    "includes": False,
                },
            }
        manifest = RunManifest(
            run_id=run_id, name=name, params={}, profiles=[], created_at=created,
            workflow=Workflow.model_validate({"location": f"/pipelines/{flow.split('/')[1]}", "engine": eng}),
            **extras,
        )

        def seed(conn, manifest=manifest, state=state, flow=flow, created=created, i=i):
            insert_run(conn, manifest, source="local", runs_root=runs_root, now=created, state=state,
                       origin="ui", workflow_name=flow, workflow_version="1.0.0")
            took = timedelta(minutes=9 + 7 * i)  # so that Started and Duration have values
            ended = {"ended_at": created + took} if state != "running" else {}
            conn.execute(update(runs).where(runs.c.id == manifest.run_id).values(started_at=created, **ended))

        writer.submit(seed).result()
    writer.submit(lambda c: c.execute(update(runs).where(runs.c.name == "liver-qc-batch-7").values(pinned=True))).result()
    app = create_app(settings, writer, web_dir=REPO / "web" / "dist")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, lifespan="off", log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        threading.Event().wait(0.05)
    env = {
        **os.environ,
        "SPECTIO_URL": f"http://127.0.0.1:{port}",
        "SPECTIO_DEMO_TUNED": TUNED,
        "SPECTIO_DEMO_UNREAD": str(UNREAD),
        "SPECTIO_DEMO_HOME": str(home),
        "SPECTIO_SESSION_COOKIE": f"{cookie_name(f'127.0.0.1:{port}')}={app.state.sessions.create()}",
    }
    try:
        yield env, port
    finally:
        server.should_exit = True
        writer.close()
        engine.dispose()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--shot", action="append", choices=SHOTS)
    wanted = set(ap.parse_args().shot or SHOTS)
    with running() as (env, _):
        for shot in (s for s in SHOTS if s in wanted):  # the names come from SHOTS, not from argv
            subprocess.run([sys.executable, str(REPO / "tools/media/shots.py"), "run", "--shot", shot, "--theme", "both"],
                           check=True, env=env, cwd=REPO)


if __name__ == "__main__":
    main()
