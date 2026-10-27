"""usage.py snapshots the current session only, never a newer transcript of another project.

python3 tools/dashboard/test_usage.py
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time, unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
USAGE = REPO / "tools/dashboard/usage.py"


def transcript(path, cwd, tokens):
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"cwd": cwd, "timestamp": "2026-10-27T10:00:00Z", "message": {"id": path.stem, "model": "m", "usage": {"output_tokens": tokens}}}
    path.write_text(json.dumps(rec) + "\n")


class TestUsage(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp())
        self.out = pathlib.Path(tempfile.mkdtemp())
        for d in (self.home, self.out):
            self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        projects = self.home / ".claude/projects"
        transcript(projects / "this-repo/aaaa.jsonl", str(REPO), 1)
        time.sleep(0.01)
        transcript(projects / "other-repo/bbbb.jsonl", "/somewhere/else", 2)  # newer, other project

    def run_usage(self, sid=None):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_SESSION_ID"}
        env["HOME"] = str(self.home)
        if sid:
            env["CLAUDE_CODE_SESSION_ID"] = sid
        return subprocess.run([sys.executable, str(USAGE), str(self.out)], cwd=REPO, env=env, capture_output=True, text=True)

    def snapshots(self):
        return sorted(p.name for p in self.out.iterdir())

    def test_session_id(self):
        self.assertEqual(self.run_usage("aaaa").returncode, 0)
        self.assertEqual(self.snapshots(), ["aaaa.json"])

    def test_cwd_when_no_session_id(self):
        r = self.run_usage()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.snapshots(), ["aaaa.json"])
        self.assertEqual(json.loads((self.out / "aaaa.json").read_text())["agents"][0]["tokens"]["output"], 1)

    def test_unknown_session_fails(self):
        self.assertNotEqual(self.run_usage("cccc").returncode, 0)
        self.assertEqual(self.snapshots(), [])

    def test_two_sessions_in_this_repo_fail(self):
        transcript(self.home / ".claude/projects/this-repo/dddd.jsonl", str(REPO), 3)
        self.assertNotEqual(self.run_usage().returncode, 0)
        self.assertEqual(self.snapshots(), [])


if __name__ == "__main__":
    unittest.main()
