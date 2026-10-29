"""fixture.py must refuse a document that holds a credential, and write nothing (security review SEC-T3-03,
SEC-T3-07); no committed SLURM or engine event fixture may hold one. Runs in ci.yml (ci-ok) and in pipelines-slurm.yml."""
import glob, json, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixture.py")
sys.path.insert(0, HERE)
from fixture import SECRET  # noqa: E402
# A made-up JWT: header {"alg":"HS256","typ":"JWT"}, a dummy payload and signature.
FAKE_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdW4iOiJzcHgifQ.c2lnbmF0dXJlLW5vdC1yZWFs"


def run(doc: dict, *args: str) -> tuple[int, bool]:
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "f.json")
        p = subprocess.run([sys.executable, FIXTURE, out, *args], input=json.dumps(doc), text=True, capture_output=True)
        return p.returncode, os.path.exists(out)


class FixtureGuard(unittest.TestCase):
    def test_each_secret_pattern_refused(self):
        # One sample for each alternative of fixture.SECRET.
        samples = {
            "jwt": FAKE_JWT,
            "env": "SLURM_JWT=x",
            "header": "X-SLURM-USER-TOKEN: x",
            "key": "-----BEGIN OPENSSH PRIVATE KEY-----",
            "munge": "MUNGE:AwQFAAB5c2VjcmV0LW5vdC1yZWFsLWNyZWQ=",
        }
        self.assertEqual(len(samples), SECRET.pattern.count("|") + 1, "a SECRET alternative has no sample")
        for name, sample in samples.items():
            with self.subTest(name):
                self.assertTrue(SECRET.search(sample))
                self.assertEqual(run({"jobs": [{"job_id": 1, "comment": sample}]}), (1, False))

    def test_committed_fixtures_clean(self):
        files = glob.glob(os.path.join(HERE, "..", "fixtures", "slurm", "**", "*.json"), recursive=True)
        self.assertTrue(files, "no committed SLURM fixture found")
        # The engine event spools and the spike T2 captures they are converted from (SEC-P3T1-03).
        events = glob.glob(os.path.join(HERE, "..", "fixtures", "engine-events", "*.jsonl"))
        events += glob.glob(os.path.join(HERE, "..", "..", "spikes", "engine-events", "fixtures", "*.jsonl"))
        self.assertEqual(len(events), 24, "engine event fixtures missing")
        files += events
        for f in files:
            with self.subTest(os.path.relpath(f, HERE)), open(f) as fh:
                m = SECRET.search(fh.read())
                self.assertIsNone(m and m.span(), "credential-like text")  # never the match itself

    def test_no_job_kept_refused(self):
        self.assertEqual(run({"jobs": [{"job_id": 1}]}, "--jobs", "2"), (1, False))

    def test_clean_document_written(self):
        self.assertEqual(run({"jobs": [{"job_id": 1}, {"job_id": 2}]}, "--jobs", "2"), (0, True))


if __name__ == "__main__":
    unittest.main()
