"""Tests for the "Choose the branch alias" step of .github/workflows/previews.yml.

Run: python3 -m unittest discover -s tools/previews -p 'test_*.py'
The step's own bash runs with the env GitHub would give it, so the tests follow the workflow as committed.
"""
import os
import pathlib
import subprocess
import tempfile
import unittest

import yaml

WORKFLOW = pathlib.Path(__file__).parents[2] / ".github" / "workflows" / "previews.yml"
STEP = next(s for s in yaml.safe_load(WORKFLOW.read_text())["jobs"]["preview"]["steps"] if s.get("id") == "alias")


def alias(event, action="", pr="", title="", inp="", ref="refs/heads/main"):
    """Return (alias or None, stdout) for one event."""
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp, "out")
        out.touch()
        env = {"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(out), "EVENT": event, "ACTION": action, "PR": pr,
               "TITLE": title, "INPUT": inp, "GITHUB_REF": ref, "GITHUB_REF_NAME": ref.split("/", 2)[-1], "HOME": tmp}
        # The step has no `shell:`, so GitHub runs it as `bash -e {0}` (no pipefail; seen in the run logs).
        r = subprocess.run(["bash", "-e", "-c", STEP["run"]], env=env, capture_output=True, text=True, cwd=tmp)
        got = out.read_text().strip().removeprefix("alias=") if r.returncode == 0 else None
        return got, r.stdout


class Alias(unittest.TestCase):
    def test_pr_tag_and_main(self):
        self.assertEqual(alias("pull_request", "synchronize", pr="13")[0], "pr-13")
        self.assertEqual(alias("push", ref="refs/tags/v0.3.0")[0], "v0-3-0")
        self.assertEqual(alias("push")[0], "main")

    def test_wave_from_the_title(self):
        self.assertEqual(alias("pull_request", "labeled", title="autopilot: APPLY2 applied (W2 complete)")[0], "wave-w2")
        self.assertEqual(alias("pull_request", "labeled", title="Promote W3, W3 again")[0], "wave-w3")

    def test_wave_needs_exactly_one_id(self):
        for title in ("W3 done, W4 next", "no wave here", "DW3 SW12x"):
            got, out = alias("pull_request", "labeled", title=title)
            self.assertIsNone(got, title)
            self.assertIn("::error::wave-approved needs exactly one wave id", out)

    def test_title_is_never_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark = pathlib.Path(tmp, "pwned")
            alias("pull_request", "labeled", title=f"W3 $(touch {mark}) `touch {mark}`")
            self.assertFalse(mark.exists())

    def test_manual_alias(self):
        self.assertEqual(alias("workflow_dispatch", inp="Demo-Gates")[0], "demo-gates")
        self.assertEqual(alias("workflow_dispatch", inp="mainline")[0], "mainline")
        for bad in ("main", "Production", "pr-12", "wave-w3", "Wave-W2", "v0-3-0", "-x", "", "a;b"):
            self.assertIsNone(alias("workflow_dispatch", inp=bad)[0], bad)


if __name__ == "__main__":
    unittest.main()
