"""A demo server for the shots of batch P3-B16: the notifications panel after UI-05b, on a phone too, and the
warning that Launch shows for an unsafe extra config file (FU-P3-121).

It reuses the seeded server of `b15_demo.py` (the same catalog, environments and eight run records, which end
today, yesterday and two days ago, so the panel shows three day groups), adds one extra config file that is
writable by group (mode 664) in the catalog pipeline's own directory (the demo home is not the host's, so a path
under it is refused for its place, not for its mode), and runs `shots.py` against it.

    .venv/bin/python tools/media/b16_demo.py [--shot app-notifications ...]

Run it from the repository root with the checkout's `.venv`, after `npx vite build` in `web/`, and a Playwright that
finds Chromium (`PLAYWRIGHT_BROWSERS_PATH`). The paths are under `/srv/demo-b15`, as in `b15_demo.py`.
"""

import argparse
import subprocess
import sys
from pathlib import Path

import b15_demo

REPO = Path(__file__).resolve().parents[2]
SHOTS = ("app-notifications", "app-notifications-phone", "app-launch-config-warning")
SHARED = "shared-tweaks.config"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--shot", action="append", choices=SHOTS)
    wanted = set(ap.parse_args().shot or SHOTS)
    with b15_demo.running() as (env, _):
        shared = b15_demo.ROOT / "pipelines" / "synthetic-rnaseq" / SHARED
        shared.write_text("process.cpus = 2\n")
        shared.chmod(0o664)  # writable by group: Launch refuses it, and says so before the click
        env["SPECTIO_DEMO_SHARED"] = str(shared)
        for shot in (s for s in SHOTS if s in wanted):  # the names come from SHOTS, not from argv
            subprocess.run([sys.executable, str(REPO / "tools/media/shots.py"), "run", "--shot", shot, "--theme", "both"],
                           check=True, env=env, cwd=REPO)


if __name__ == "__main__":
    main()
