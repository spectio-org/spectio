"""Tests for versions_page.py. Run: python3 -m unittest discover -s tools/previews -p 'test_*.py'

The deployment objects follow the shape the live Cloudflare Pages deployments API returned on 2026-10-27
(key names printed by fetch() in the previews.yml log of PR #13); ids, hashes and dates are made up.
"""
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import versions_page as vp  # noqa: E402

SCRIPT = pathlib.Path(__file__).with_name("versions_page.py")


def dep(branch, sha, status="success", env="preview", n=1):
    return {
        "id": f"id-{n}", "short_id": f"{n:08x}", "project_name": "spectio", "environment": env,
        "url": f"https://{n:08x}.spectio.pages.dev", "created_on": f"2026-10-27T10:{n % 60:02d}:00.000000Z",
        "aliases": None, "is_skipped": False,
        "latest_stage": {"name": "deploy", "status": status, "started_on": None, "ended_on": None},
        "deployment_trigger": {"type": "ad_hoc", "metadata": {
            "branch": branch, "commit_hash": sha, "commit_message": "subject line\nbody", "commit_dirty": False}},
    }


class Rows(unittest.TestCase):
    def test_kinds_and_fields(self):
        items = vp.rows([dep("pr-13", "950e1de41c98", n=1), dep("wave-w3", "aaaaaaa1", n=2),
                         dep("v0-3-0", "bbbbbbb2", n=3), dep("main", "ccccccc3", env="production", n=4)])
        self.assertEqual([i["kind"] for i in items], ["pr", "wave", "release", "main"])
        self.assertEqual(items[0]["sha"], "950e1de")
        self.assertEqual(items[0]["message"], "subject line")
        self.assertEqual(items[0]["created"], "2026-10-27 10:01")
        self.assertEqual(items[0]["url"], "https://00000001.spectio.pages.dev")

    def test_unsuccessful_deployments_are_left_out(self):
        items = vp.rows([dep("pr-1", "a" * 7, status="failure", n=1), dep("pr-1", "b" * 7, status="active", n=2),
                         dep("pr-1", "c" * 7, n=3)])
        self.assertEqual([i["sha"] for i in items], ["ccccccc"])

    def test_production_without_branch_is_main(self):
        d = dep("main", "d" * 7, env="production")
        d["deployment_trigger"]["metadata"]["branch"] = None
        self.assertEqual(vp.rows([d])[0]["alias"], "main")


class Fetch(unittest.TestCase):
    def pages(self, *batches, info=True):
        total = len(batches)
        bodies = [json.dumps({"result": b, **({"result_info": {"page": i + 1, "per_page": 25, "count": len(b),
                                                              "total_count": sum(map(len, batches)), "total_pages": total}}
                                              if info else {})})
                  for i, b in enumerate(batches)]
        calls = []

        def urlopen(req, timeout):
            calls.append(req.full_url)
            return io.BytesIO(bodies[len(calls) - 1].encode())
        return calls, urlopen

    def run_fetch(self, *batches, info=True):
        calls, fake = self.pages(*batches, info=info)
        env = {"CLOUDFLARE_API_TOKEN": "t", "CLOUDFLARE_ACCOUNT_ID": "a"}
        with mock.patch.dict(os.environ, env), mock.patch.object(vp.urllib.request, "urlopen", fake), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            got = vp.fetch("spectio")
        return got, calls, out.getvalue()

    def test_follows_total_pages(self):
        got, calls, out = self.run_fetch([dep("pr-1", "a" * 7, n=i) for i in range(25)], [dep("main", "b" * 7)])
        self.assertEqual((len(got), len(calls)), (26, 2))
        self.assertIn("page=2&per_page=25", calls[1])
        self.assertIn("metadata keys=['branch', 'commit_dirty', 'commit_hash', 'commit_message']", out)

    def test_full_last_page_stops(self):
        got, calls, _ = self.run_fetch([dep("pr-1", "a" * 7, n=i) for i in range(25)])
        self.assertEqual((len(got), len(calls)), (25, 1))

    def test_without_result_info_a_short_page_stops(self):
        got, calls, _ = self.run_fetch([dep("pr-1", "a" * 7, n=i) for i in range(25)], [dep("main", "b" * 7)] * 3,
                                       info=False)
        self.assertEqual((len(got), len(calls)), (28, 2))


class Page(unittest.TestCase):
    def test_from_json_renders_every_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = pathlib.Path(tmp, "d.json"), pathlib.Path(tmp, "versions", "index.html")
            src.write_text(json.dumps({"result": [dep("pr-13", "950e1de", n=1), dep("wave-w3", "aaaaaaa", n=2),
                                                  dep("main", "bbbbbbb", n=3), dep("x<y>", "ccccccc", n=4)]}))
            r = subprocess.run([sys.executable, str(SCRIPT), "--project", "spectio", "--out", str(out),
                                "--from-json", str(src), "--current-alias", "pr-13", "--current-sha", "950e1de41c98"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            html = out.read_text()
        for title in ("Validated waves", "main", "Pull requests", "Other"):
            self.assertIn(f"<h2>{title} ", html)
        self.assertIn("This build: <code>pr-13</code> at <code>950e1de</code>", html)
        self.assertIn("x&lt;y&gt;", html)  # branch names are escaped
        self.assertNotIn("x<y>", html)


if __name__ == "__main__":
    unittest.main()
