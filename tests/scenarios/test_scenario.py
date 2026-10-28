"""Unit tests of the pure parts of dev/scenario.py: names, ports and paths per id, and the scenario files.

    python3 -m unittest discover -s tests/scenarios -p 'test_*.py'
"""
import importlib.util
import unittest
from pathlib import Path

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
        for layer, profile, _ in scenario.SCHEDULERS.values():
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


if __name__ == "__main__":
    unittest.main()
