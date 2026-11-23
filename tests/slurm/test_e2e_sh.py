"""tests/slurm/e2e.sh on slurm-mini, with a fake `sind` that records each command and runs
nothing (it prints a tmux path for `command -v tmux`, and exits 1 for a command that contains
$FAIL_ON):

- the Snakemake launch needs no `--slurm-status-command` from the environment: slurm-mini has
  no accounting (sacct exits 1), so Spectio passes `squeue` itself (FU-P3-106b), and the env
  keeps only the delay before the executor's first status check (PR #164, CI job 134667343638);
- `cancel <engine>` and `restart` (P1 Task 23) run their client with a larger scale, and the
  tmux shim that logs each tmux call;
- every case prints its RESULT line and tears down, even when a step before the client fails
  (FU-P3-68)."""

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


class E2eMini(unittest.TestCase):
    def setUp(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        self.data, fakes, self.calls = tmp / "data", tmp / "bin", tmp / "calls"
        (self.data / "tools" / "bin").mkdir(parents=True)
        fakes.mkdir()
        sind = (
            f'printf "%s\\n" "$*" >>"{self.calls}"\n'
            'case "$*" in *"command -v tmux"*) echo "${FAKE_TMUX:-/usr/bin/tmux}" ;; esac\n'
            'case "$*" in *"${FAIL_ON:-no such command}"*) exit 1 ;; esac\n'
            "exit 0"
        )
        for path, body in (
            (self.data / "tools" / "bin" / "spectio", "exit 0"),
            (fakes / "sind", sind),
        ):
            path.write_text(f"#!/bin/sh\n{body}\n")
            path.chmod(stat.S_IRWXU)
        self.env = {
            **os.environ,
            "PATH": f"{fakes}:{os.environ['PATH']}",
            "CLUSTER": "mini",
            "SLURM_DATA": str(self.data),
        }

    def run_e2e(self, *args, **env):
        return subprocess.run(
            [BASH, str(E2E), *args], env=self.env | env, capture_output=True, text=True
        )

    def lines(self, word):
        return [line for line in self.calls.read_text().splitlines() if word in line]

    def test_the_snakemake_init_keeps_only_the_status_check_delay(self):
        out = self.run_e2e("launch", "snakemake")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        init = self.lines(" spectio init ")
        self.assertEqual(len(init), 1, self.calls.read_text())
        self.assertIn(
            "SPECTIO_ENGINES_EXTRA_ARGS_SNAKEMAKE=--slurm-init-seconds-before-status-checks 5 ",
            init[0],
        )
        self.assertNotIn("--slurm-status-command", init[0])  # Spectio passes squeue itself
        self.assertIn("RESULT e2e-launch-snakemake pass", out.stdout)

    def test_cancel_runs_a_larger_happy(self):
        for engine in ("nextflow", "snakemake"):
            with self.subTest(engine):
                self.calls.unlink(missing_ok=True)
                out = self.run_e2e("cancel", engine)
                self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
                client = self.lines(f"e2e_client.py cancel {engine} ")
                self.assertEqual(len(client), 1, self.calls.read_text())
                self.assertIn('"scale": 4', client[0])
                self.assertIn(f"/e2e/cancel-{engine}/", client[0])
                self.assertIn(f"RESULT e2e-cancel-{engine} pass", out.stdout)

    def test_restart_logs_tmux_through_its_shim(self):
        out = self.run_e2e("restart")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        e = self.data / "e2e" / "restart"
        client = self.lines("e2e_client.py restart ")
        self.assertEqual(len(client), 1, self.calls.read_text())
        self.assertIn(f"--tmux-log {e}/tmux.log", client[0])
        self.assertIn(f"--golden {e}/golden.tsv", client[0])
        # every command of the case has the shim first on PATH, so the server's tmux calls too
        serve = self.lines(" spectio serve --detach")
        self.assertEqual(len(serve), 1)
        self.assertIn(f"E2E_BIN={e}/tmux-bin ", serve[0])
        shim = (e / "tmux-bin" / "tmux").read_text()
        self.assertIn(f'>>"{e}/tmux.log"', shim)
        self.assertIn('exec /usr/bin/tmux "$@"', shim)
        self.assertIn("RESULT e2e-restart pass", out.stdout)

    def test_the_shim_log_is_private(self):
        """SEC-P3T23-05: the log of the tmux calls is written 0600, whatever the caller's umask."""
        out = self.run_e2e("restart", FAKE_TMUX="/bin/true")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        e = self.data / "e2e" / "restart"
        shim = e / "tmux-bin" / "tmux"
        done = subprocess.run(["/bin/sh", "-c", f'umask 022; exec "{shim}" new-session -s x'])
        self.assertEqual(done.returncode, 0)
        log = e / "tmux.log"
        self.assertEqual(log.read_text(), "new-session -s x\n")
        self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)

    def test_a_failed_step_still_prints_result_and_tears_down(self):
        for case, name in (
            (("launch", "nextflow"), "launch-nextflow"),
            (("cancel", "snakemake"), "cancel-snakemake"),
            (("restart",), "restart"),
        ):
            with self.subTest(case):
                self.calls.unlink(missing_ok=True)
                out = self.run_e2e(*case, FAIL_ON=" spectio init ")
                self.assertEqual(out.returncode, 1, out.stdout + out.stderr)
                self.assertIn(f"RESULT e2e-{name} fail", out.stdout)
                self.assertEqual(
                    self.lines("e2e_client.py launch")
                    + self.lines("e2e_client.py cancel")
                    + self.lines("e2e_client.py restart"),
                    [],
                )
                self.assertEqual(
                    len(self.lines("e2e_client.py teardown ")), 1, self.calls.read_text()
                )
                self.assertEqual(len(self.lines("tmux kill-session -t =spectio-server")), 1)

    def test_a_failed_client_prints_fail(self):
        out = self.run_e2e("cancel", "nextflow", FAIL_ON="e2e_client.py cancel")
        self.assertEqual(out.returncode, 1, out.stdout + out.stderr)
        self.assertIn("RESULT e2e-cancel-nextflow fail", out.stdout)
        self.assertEqual(len(self.lines("e2e_client.py teardown ")), 1)

    def test_an_unknown_case_is_refused(self):
        for args in (("cancel", "cwl"), ("restart", "snakemake"), ("launch",), ()):
            with self.subTest(args):
                self.assertEqual(self.run_e2e(*args).returncode, 2)


if __name__ == "__main__":
    unittest.main()
