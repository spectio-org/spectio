"""Tests for the public demo's recorder (record_demo.py).

Run: python3 -m unittest tools/media/test_record_demo.py
"""

import json
import platform
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import record_demo  # noqa: E402

BANNER = "Oct-31 11:06:52.434 [main] DEBUG nextflow.cli.CmdRun - \n  Version: 26.10.4\n  System: Linux {}\n  Runtime: Groovy"


class Problems(unittest.TestCase):
    def test_the_recorder_kernel_release_is_refused(self):
        text = f"uname: {platform.release()}"
        self.assertTrue(any("kernel release" in p for p in record_demo.problems(text)))

    def test_the_nextflow_system_line_is_made_neutral(self):
        text = record_demo.neutral(BANNER.format("1.2.3-demo-v9"))
        self.assertIn("  System: Linux\n", text)
        self.assertNotIn("demo-v9", text)
        self.assertEqual(record_demo.problems(record_demo.neutral(BANNER.format(platform.release()))), [])

    def test_the_committed_recording_names_no_kernel(self):
        text = record_demo.OUT.read_text(encoding="utf-8")
        self.assertEqual(record_demo.problems(text), [])
        bodies = "".join(a["body"] for a in json.loads(text).values())
        self.assertIsNone(re.search(r"System: Linux \S", bodies))


if __name__ == "__main__":
    unittest.main()
