"""Unit tests for the golden fixtures of the synthetic scenarios (no engine needed).

  python3 -m unittest tests/pipelines/synthetic/test_golden.py

A fresh run is compared with the fixtures by `run_scenarios.py --golden check`.
"""
import sys, unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_scenarios as rs  # noqa: E402

TRACE = """task_id\thash\tnative_id\tprocess\ttag\tname\tstatus\texit\tattempt\tsubmit
1\tab/cdef12\t101\tALIGN\tS01.chunk0000\tALIGN (S01.chunk0000)\tCOMPLETED\t0\t1\t2026-10-27 10:00:00.000
2\tab/cdef13\t102\tALIGN\tS02.chunk0000\tALIGN (S02.chunk0000)\tCOMPLETED\t0\t1\t2026-10-27 10:00:01.000
3\tab/cdef14\t103\tQC_STATS\tS05\tQC_STATS (S05)\tFAILED\t137\t1\t2026-10-27 10:00:02.000
4\tab/cdef15\t104\tQC_STATS\tS05\tQC_STATS (S05)\tCOMPLETED\t0\t2\t2026-10-27 10:00:03.000
5\tab/cdef16\t105\tQC_STATS\tS06\tQC_STATS (S06)\tCACHED\t0\t1\t2026-10-27 10:00:04.000
"""

SMK_LOG = """[Tue Oct 27 21:43:47 2026]
localrule qc_stats:
    input: results/work/reads/S05.reads.txt
    jobid: 10
    wildcards: sample=S05
    resources: tmpdir=/tmp, attempt=1, mem_mb=512
Shell command: true
[Tue Oct 27 21:43:47 2026]
localrule qc_stats:
    jobid: 11
    wildcards: sample=S06
    resources: tmpdir=/tmp, attempt=1, mem_mb=512
Command 'set -euo pipefail; synth.py fail oom 1 2' returned non-zero exit status 137.
[Tue Oct 27 21:43:48 2026]
Error in rule qc_stats:
    message: None
    jobid: 10
Trying to restart job 10.
[Tue Oct 27 21:43:48 2026]
Finished jobid: 11 (Rule: qc_stats)
[Tue Oct 27 21:43:48 2026]
localrule qc_stats:
    jobid: 10
    wildcards: sample=S05
    resources: tmpdir=/tmp, attempt=2, mem_mb=1024
[Tue Oct 27 21:43:49 2026]
Finished jobid: 10 (Rule: qc_stats)
"""


class NormaliseTest(unittest.TestCase):
    def test_nextflow_trace_rows(self):
        rows = rs.nf_rows(TRACE)
        self.assertIn(("QC_STATS", "S05", "FAILED", "137", "1"), rows)
        self.assertEqual(len(rows), 5)

    def test_snakemake_log_rows(self):
        rows = sorted(rs.smk_rows(SMK_LOG))
        self.assertEqual(rows, [("QC_STATS", "sample=S05", "COMPLETED", "0", "2"),
                                ("QC_STATS", "sample=S05", "FAILED", "137", "1"),
                                ("QC_STATS", "sample=S06", "COMPLETED", "0", "1")])

    def test_first_attempt_successes_are_counted_and_the_rest_listed(self):
        text = rs.golden_text("nextflow", "0.0", "x", [(0, rs.nf_rows(TRACE))], None)
        lines = text.splitlines()
        self.assertEqual(lines[0], "# nextflow 0.0 · x")
        self.assertEqual(lines[1], "# run 1: exit 0")
        self.assertIn("1\tALIGN\tCOMPLETED\t0\t1\t*\t2", lines)
        self.assertIn("1\tQC_STATS\tFAILED\t137\t1\tS05\t1", lines)
        self.assertIn("1\tQC_STATS\tCOMPLETED\t0\t2\tS05\t1", lines)
        self.assertIn("1\tQC_STATS\tCACHED\t0\t1\t*\t1", lines)

    def test_target_filter_keeps_only_the_injected_task(self):
        text = rs.golden_text("nextflow", "0.0", "x", [(1, rs.nf_rows(TRACE))], ("QC_STATS", "S05"))
        rows = [l for l in text.splitlines() if not l.startswith("#")][1:]
        self.assertEqual(rows, ["1\tQC_STATS\tCOMPLETED\t0\t2\tS05\t1", "1\tQC_STATS\tFAILED\t137\t1\tS05\t1"])


class FixturesTest(unittest.TestCase):
    """The recorded fixtures parse and cover every PR scenario that runs on their engine."""

    def test_fixtures_cover_every_pr_scenario(self):
        scenarios = yaml.safe_load(open(HERE / "scenarios.yaml"))["scenarios"]
        dirs = sorted(p for p in (HERE / "golden").iterdir() if p.is_dir())
        self.assertTrue(dirs, "no golden fixtures recorded")
        for d in dirs:
            engine, version = d.name.split("-", 1)
            self.assertIn(engine, ("nextflow", "snakemake"))
            want = {s["id"] for s in scenarios if not s.get("nightly") and engine in s.get("engines", [engine])}
            have = {p.name.removesuffix(".tsv") for p in d.glob("*.tsv")}
            self.assertEqual(want - have, set(), f"{d.name}: missing fixtures")
            self.assertEqual(have - want, set(), f"{d.name}: fixtures without a scenario")
            for p in d.glob("*.tsv"):
                lines = p.read_text().splitlines()
                self.assertEqual(lines[0], f"# {engine} {version} · {p.stem}", p)
                header = [l for l in lines if not l.startswith("#")][0]
                self.assertEqual(header, "\t".join(rs.GOLDEN_COLUMNS), p)
                for l in lines[lines.index(header) + 1:]:
                    self.assertEqual(len(l.split("\t")), len(rs.GOLDEN_COLUMNS), f"{p}: {l}")


if __name__ == "__main__":
    unittest.main()
