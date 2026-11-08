"""dev/slurm/native.sh must refuse before any apt, daemon start or file write: when not root, and when a
slurm.conf or slurmdbd.conf it did not write (no marker line) is there, so it never clobbers a site's
config (FU-P3-66). Fakes only: every command the script could run is a recorder on PATH, `id -u` is faked,
and the config directory is a temporary one (NATIVE_SLURM_ETC). Nothing is installed or started."""
import os, shutil, stat, subprocess, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "..", "..", "dev", "slurm", "native.sh")
BASH = shutil.which("bash")
MARK = "# Written by dev/slurm/native.sh"
# External commands native.sh calls; each fake records its name and fails, so that a guard that lets the
# script through stops it at its first command (any other command is not found).
COMMANDS = (
    "apt-get dpkg-query install mungekey munged runuser mysqld_safe mysql mysqladmin slurmdbd slurmctld "
    "slurmd sacctmgr sinfo scontrol pgrep pkill hostname nproc setsid nohup chown mkdir rm sed head tr base64"
).split()


class NativeGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.bin = os.path.join(self.tmp, "bin")
        self.etc = os.path.join(self.tmp, "etc")
        self.calls = os.path.join(self.tmp, "calls")
        self.proc = os.path.join(self.tmp, "proc")
        os.mkdir(self.bin)
        os.mkdir(self.etc)
        os.mkdir(self.proc)
        for name in COMMANDS:
            self._fake(name, f'echo "{name}" >>"{self.calls}"; exit 97')

    def _fake(self, name, body):
        path = os.path.join(self.bin, name)
        with open(path, "w") as fh:
            fh.write(f"#!/bin/sh\n{body}\n")
        os.chmod(path, stat.S_IRWXU)

    def run_native(self, uid, *args, **extra_env):
        self._fake("id", f'[ "$1" = -u ] && echo {uid} || exit 97')
        # Only the fakes on PATH: no real tool can be reached, an unfaked one is "not found".
        env = {"PATH": self.bin, "NATIVE_SLURM_ETC": self.etc, "NATIVE_SLURM_PROC": self.proc, **extra_env}
        p = subprocess.run([BASH, NATIVE, *args], env=env, capture_output=True, text=True, timeout=30)
        return p.returncode, p.stderr

    def recorded(self):
        if not os.path.exists(self.calls):
            return []
        with open(self.calls) as fh:
            return fh.read().split()

    def etc_files(self):
        return {n: open(os.path.join(self.etc, n)).read() for n in sorted(os.listdir(self.etc))}

    def test_not_root_refused(self):
        for cmd in ("up", "down"):
            with self.subTest(cmd):
                code, err = self.run_native(1000, cmd)
                self.assertNotEqual(code, 0)
                self.assertIn("as root", err)
                self.assertEqual(self.recorded(), [])
                self.assertEqual(self.etc_files(), {})

    def test_foreign_config_refused(self):
        for name in ("slurm.conf", "slurmdbd.conf"):
            with self.subTest(name):
                site = {name: "ClusterName=site\n"}
                with open(os.path.join(self.etc, name), "w") as fh:
                    fh.write(site[name])
                for cmd in ("up", "down"):
                    code, err = self.run_native(0, cmd)
                    self.assertNotEqual(code, 0)
                    self.assertIn("not written by", err)
                    self.assertEqual(self.recorded(), [])
                    self.assertEqual(self.etc_files(), site)
                os.remove(os.path.join(self.etc, name))

    def test_inherited_site_slurm_conf_refused(self):
        for cmd in ("up", "down"):
            with self.subTest(cmd):
                code, err = self.run_native(0, cmd, SLURM_CONF="/opt/site/slurm.conf")
                self.assertNotEqual(code, 0)
                self.assertIn("SLURM_CONF", err)
                self.assertEqual(self.recorded(), [])
                self.assertEqual(self.etc_files(), {})

    def test_down_without_own_config_refused(self):
        code, err = self.run_native(0, "down")
        self.assertNotEqual(code, 0)
        self.assertIn("nothing of native.sh to stop", err)
        self.assertEqual(self.recorded(), [])
        self.assertEqual(self.etc_files(), {})

    def test_up_refused_when_slurm_daemon_runs(self):
        for daemon in ("slurmctld", "slurmd", "slurmdbd"):
            with self.subTest(daemon):
                pid = os.path.join(self.proc, "4242")
                os.makedirs(pid, exist_ok=True)
                with open(os.path.join(pid, "comm"), "w") as fh:
                    fh.write(f"{daemon}\n")
                code, err = self.run_native(0, "up")
                self.assertNotEqual(code, 0)
                self.assertIn(f"{daemon} is already running", err)
                self.assertEqual(self.recorded(), [])
                self.assertEqual(self.etc_files(), {})

    def test_up_with_unrelated_processes_passes_the_guards(self):
        pid = os.path.join(self.proc, "1")
        os.mkdir(pid)
        with open(os.path.join(pid, "comm"), "w") as fh:
            fh.write("bash\n")
        self.run_native(0, "up")
        self.assertEqual(self.recorded()[0], "dpkg-query")

    def test_marker_config_passes_the_guards(self):
        # Its own config: the guards let it through, and the first command it runs is the package check.
        own = {"slurm.conf": f"{MARK}: a dev-only one-node Slurm.\nClusterName=local\n"}
        with open(os.path.join(self.etc, "slurm.conf"), "w") as fh:
            fh.write(own["slurm.conf"])
        code, _ = self.run_native(0, "up")
        self.assertNotEqual(code, 0)
        self.assertEqual(self.recorded()[0], "dpkg-query")
        self.assertEqual(self.etc_files(), own)

    def test_plain_etc_path_only(self):
        self.etc = "relative/etc"
        code, err = self.run_native(0, "up")
        self.assertNotEqual(code, 0)
        self.assertIn("plain absolute path", err)
        self.assertEqual(self.recorded(), [])

    def test_usage(self):
        code, _ = self.run_native(0, "start")
        self.assertEqual(code, 2)
        self.assertEqual(self.recorded(), [])

    @unittest.skipIf(shutil.which("shellcheck") is None, "no shellcheck on PATH")
    def test_shellcheck_clean(self):
        subprocess.run(["shellcheck", NATIVE], check=True)


if __name__ == "__main__":
    unittest.main()
