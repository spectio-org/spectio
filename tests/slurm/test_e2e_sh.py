"""tests/slurm/e2e.sh on slurm-mini, with a fake `sind` that records each command and runs nothing:
the Snakemake head must ask squeue for its jobs' states. slurm-mini has no accounting, so `sacct`
exits 1 ("Slurm accounting storage is disabled"); the SLURM plugin 2.8.0 picks sacct whenever it is
on PATH, and a failed status query yields no job, so the head waits for its jobs forever (PR #164,
CI job 134667343638)."""

import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
E2E = HERE / "e2e.sh"
BASH = shutil.which("bash")


class E2eMiniSnakemake(unittest.TestCase):
    def test_the_snakemake_head_queries_squeue(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        data, fakes, calls = tmp / "data", tmp / "bin", tmp / "calls"
        (data / "tools" / "bin").mkdir(parents=True)
        fakes.mkdir()
        for path, body in (
            (data / "tools" / "bin" / "spectio", "exit 0"),
            (fakes / "sind", f'printf "%s\\n" "$*" >>"{calls}"; exit 0'),
        ):
            path.write_text(f"#!/bin/sh\n{body}\n")
            path.chmod(stat.S_IRWXU)
        env = {
            **os.environ,
            "PATH": f"{fakes}:{os.environ['PATH']}",
            "CLUSTER": "mini",
            "SLURM_DATA": str(data),
        }
        out = subprocess.run(
            [BASH, str(E2E), "launch", "snakemake"], env=env, capture_output=True, text=True
        )
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        init = [line for line in calls.read_text().splitlines() if " spectio init " in line]
        self.assertEqual(len(init), 1, calls.read_text())
        self.assertIn(
            "SPECTIO_ENGINES_EXTRA_ARGS_SNAKEMAKE=--slurm-init-seconds-before-status-checks 5 "
            "--slurm-status-command squeue ",
            init[0],
        )


if __name__ == "__main__":
    unittest.main()
