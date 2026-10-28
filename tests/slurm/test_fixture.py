"""fixture.py must refuse a document that holds a credential, and write nothing (security review SEC-T3-03)."""
import json, os, subprocess, sys, tempfile, unittest

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixture.py")
# A made-up JWT: header {"alg":"HS256","typ":"JWT"}, a dummy payload and signature.
FAKE_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdW4iOiJzcHgifQ.c2lnbmF0dXJlLW5vdC1yZWFs"


def run(doc: dict, *args: str) -> tuple[int, bool]:
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "f.json")
        p = subprocess.run([sys.executable, FIXTURE, out, *args], input=json.dumps(doc), text=True, capture_output=True)
        return p.returncode, os.path.exists(out)


class FixtureGuard(unittest.TestCase):
    def test_jwt_refused(self):
        self.assertEqual(run({"jobs": [{"job_id": 1, "comment": FAKE_JWT}]}), (1, False))

    def test_munge_credential_refused(self):
        self.assertEqual(run({"note": "MUNGE:AwQFAAB5c2VjcmV0LW5vdC1yZWFsLWNyZWQ="}), (1, False))

    def test_no_job_kept_refused(self):
        self.assertEqual(run({"jobs": [{"job_id": 1}]}, "--jobs", "2"), (1, False))

    def test_clean_document_written(self):
        self.assertEqual(run({"jobs": [{"job_id": 1}, {"job_id": 2}]}, "--jobs", "2"), (0, True))


if __name__ == "__main__":
    unittest.main()
