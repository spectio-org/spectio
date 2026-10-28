"""Unit tests of dev/scenario.py without Docker: names, ports and paths per id, the scenario files, the id claim,
and the commands `down` runs (subprocess mocked).

    python3 -m unittest discover -s tests/scenarios -p 'test_*.py'
"""
import importlib.util
import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("scenario", REPO / "dev" / "scenario.py")
scenario = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scenario)


class Names(unittest.TestCase):
    def test_id_owns_names_ports_and_paths(self):
        n = scenario.names(3)
        self.assertEqual(n["name"], "spx-3")
        self.assertEqual(n["ports"], [20300, 20399])
        self.assertEqual(n["port"], {"spectio": 20300, "kube_api": 20301})
        self.assertEqual(n["data_dir"], str(REPO / ".scenarios" / "3"))

    def test_no_two_ids_share_a_name_port_or_path(self):
        all_ids = [scenario.names(i) for i in range(1, scenario.MAX_ID + 1)]
        ports = [p for n in all_ids for p in range(n["ports"][0], n["ports"][1] + 1)]
        self.assertEqual(len(ports), len(set(ports)))
        self.assertLessEqual(max(ports), 65535)
        self.assertEqual(len({n["name"] for n in all_ids}), len(all_ids))
        self.assertEqual(len({n["data_dir"] for n in all_ids}), len(all_ids))
        # sind names a realm's resources <realm>-<cluster>-*: spx-1 with cluster mini must not read as another
        # id's realm, which holds only when no profile name starts with a digit
        for _, profile, _ in scenario.SCHEDULERS.values():
            self.assertFalse(profile and profile[0].isdigit())

    def test_ids_out_of_range(self):
        for bad in (0, -1, scenario.MAX_ID + 1):
            with self.assertRaises(ValueError):
                scenario.names(bad)


class Yaml(unittest.TestCase):
    def test_subset(self):
        text = "# c\na: x  # trailing\nb: [p=1, q]\nc:\n  - one\n  - two words\nd: url#frag\n"
        self.assertEqual(scenario.parse_yaml(text),
                         {"a": "x", "b": ["p=1", "q"], "c": ["one", "two words"], "d": "url#frag"})

    def test_rejects_what_it_does_not_read(self):
        for text in ("a:\n    - deeper\n", "a: {x: 1}\n", "a: 'quoted'\n", "a: b: c\n", "A: x\n",
                     "a: x\na: y\n", "a: x\n  - stray\n", "a: |\n  block\n"):
            with self.assertRaises(ValueError, msg=text):
                scenario.parse_yaml(text)

    def test_check_fields_and_values(self):
        good = {"deployment": "bundle", "scheduler": "local", "engine": "e", "fixture": "f", "params": [],
                "gate": "none", "expect": []}
        self.assertEqual(scenario.check(dict(good), "x")["name"], "x")
        for broken in ({k: v for k, v in good.items() if k != "gate"}, dict(good, extra="1"),
                       dict(good, scheduler="slurm"), dict(good, deployment="helm")):
            with self.assertRaises(ValueError):
                scenario.check(broken, "x")

    def test_every_scenario_file_loads(self):
        files = sorted(scenario.SCENARIOS.glob("*.yaml"))
        self.assertTrue(files)
        for f in files:
            self.assertIn(scenario.load(f.stem)["scheduler"], scenario.SCHEDULERS)

    def test_bad_scenario_name(self):
        with self.assertRaises(ValueError):
            scenario.load("../etc/passwd")


class TempState(unittest.TestCase):
    """scenario.STATE points at a temporary directory for the test."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(scenario, "STATE", Path(self.tmp.name) / ".scenarios")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)


class Claim(TempState):
    def test_parallel_claims_get_distinct_ids(self):
        got, lock = [], threading.Lock()

        def take():
            n = scenario.claim(None)
            with lock:
                got.append(n)
        threads = [threading.Thread(target=take) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(got), list(range(1, 9)))

    def test_same_id_twice_is_refused(self):
        self.assertEqual(scenario.claim(3), 3)
        with self.assertRaises(SystemExit):
            scenario.claim(3)

    def test_id_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            scenario.claim(0)
        with mock.patch.object(scenario, "available_mib", return_value=1 << 20), self.assertRaises(SystemExit):
            scenario.main(["up", "happy-local", "--id", "0"])
        self.assertFalse((scenario.STATE / "0").exists())


class Down(TempState):
    def test_down_never_searches_the_data_directory(self):
        data = scenario.names(5)["data_dir"]
        Path(data, "tools", "bin").mkdir(parents=True)
        calls = []

        def fake_run(cmd, env=None, **kw):
            calls.append((cmd, env))
            return subprocess.CompletedProcess(cmd, 0, stdout="spx-5 x\n")
        which_paths = []
        with mock.patch.object(scenario.subprocess, "run", side_effect=fake_run), \
                mock.patch.object(scenario.shutil, "which",
                                  side_effect=lambda cmd, path=None: which_paths.append(path) or f"/usr/bin/{cmd}"), \
                mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            scenario.down(5)
        self.assertTrue(calls)
        for cmd, env in calls:
            self.assertNotIn(data, (env or {}).get("PATH", ""), cmd)
        for path in which_paths:
            self.assertNotIn(data, path or "")
        self.assertFalse(Path(data).exists())

    def test_down_keeps_the_data_directory_when_a_step_fails(self):
        data = scenario.names(6)["data_dir"]
        Path(data).mkdir(parents=True)
        with mock.patch.object(scenario.subprocess, "run",
                               side_effect=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, stdout="spx-6\n")), \
                mock.patch.object(scenario.shutil, "which", return_value="/usr/bin/x"), mock.patch("sys.stdout"), \
                mock.patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                scenario.down(6)
        self.assertTrue(Path(data).exists())

    def test_down_keeps_the_data_directory_when_the_cluster_tool_is_missing(self):
        data = scenario.names(7)["data_dir"]
        Path(data).mkdir(parents=True)
        Path(data, "scenario.json").write_text(json.dumps({"scenario": {"scheduler": "slurm-mini"}}))
        with mock.patch.object(scenario.subprocess, "run",
                               side_effect=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="")), \
                mock.patch.object(scenario.shutil, "which", return_value=None), \
                mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                scenario.down(7)
        self.assertTrue(Path(data).exists())

    def test_down_survives_a_corrupt_scenario_json(self):
        data = scenario.names(8)["data_dir"]
        Path(data).mkdir(parents=True)
        Path(data, "scenario.json").write_text("{not json")
        with mock.patch.object(scenario.subprocess, "run",
                               side_effect=lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="")), \
                mock.patch.object(scenario.shutil, "which", return_value="/usr/bin/x"), \
                mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            scenario.down(8)
        self.assertFalse(Path(data).exists())

    def test_down_keeps_the_network_when_a_step_fails(self):
        cmds = []

        def fake_run(cmd, **kw):
            cmds.append(cmd)
            return subprocess.CompletedProcess(cmd, 1 if cmd[:2] == ["sind", "--realm"] else 0, stdout="spx-9\n")
        Path(scenario.names(9)["data_dir"]).mkdir(parents=True)
        with mock.patch.object(scenario.subprocess, "run", side_effect=fake_run), \
                mock.patch.object(scenario.shutil, "which", return_value="/usr/bin/x"), \
                mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                scenario.down(9)
        self.assertNotIn(["docker", "network", "rm", "spx-9"], cmds)


class Up(TempState):
    def test_failed_up_takes_down_what_it_created(self):
        with mock.patch.object(scenario, "available_mib", return_value=1 << 20), \
                mock.patch.object(scenario, "_reserve", return_value={}), \
                mock.patch.object(scenario, "_up", side_effect=RuntimeError("boom")), \
                mock.patch.object(scenario, "down") as down, mock.patch("sys.stderr"):
            with self.assertRaises(RuntimeError):
                scenario.up("happy-local", 4)
        down.assert_called_once_with(4)

    def test_up_that_cannot_own_the_network_deletes_nothing_by_name(self):
        # another checkout holds spx-4: `docker network create` fails, and only the claim is released (CR-8)
        fail = subprocess.CalledProcessError(1, ["docker", "network", "create"])
        with mock.patch.object(scenario, "available_mib", return_value=1 << 20), \
                mock.patch.object(scenario, "port_free", return_value=True), \
                mock.patch.object(scenario.subprocess, "run", side_effect=fail) as run, \
                mock.patch.object(scenario, "down") as down, mock.patch("sys.stderr"):
            with self.assertRaises(subprocess.CalledProcessError):
                scenario.up("happy-local", 4)
        down.assert_not_called()
        self.assertEqual(run.call_count, 1)
        self.assertFalse(Path(scenario.names(4)["data_dir"]).exists())


if __name__ == "__main__":
    unittest.main()
