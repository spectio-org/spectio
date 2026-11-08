"""The pure parts of e2e_client.py (P1 Task 22): the ticket line, the session cookie, the golden
counts, the run's states, the expect lines of a scenario and the jobs of a run. No server and no
cluster: tests/slurm/e2e.sh runs the client itself. Runs in ci.yml (ci-ok) and in pipelines-slurm.yml."""
import os
import sys
import unittest
from email.message import Message
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import e2e_client as c  # noqa: E402

GOLDEN = """# nextflow 26.10.4 · happy
# run 1: exit 0
run\tprocess\tstatus\texit\tattempt\ttag\tcount
1\tALIGN\tCOMPLETED\t0\t1\t*\t24
1\tMERGE\tCOMPLETED\t0\t1\t*\t1
"""


class Ticket(unittest.TestCase):
    def test_the_sentinel_line(self):
        out = "some profile noise\nspectio-ticket-v1 {\"ticket\": \"" + "a" * 43 + "\"}\n"
        self.assertEqual(c.parse_ticket(out), "a" * 43)

    def test_no_line_or_a_bad_ticket(self):
        for out in ("", "spectio-ticket-v1 {}\n", "spectio-ticket-v1 {\"ticket\": \"short\"}\n",
                    "x spectio-ticket-v1 {\"ticket\": \"" + "a" * 43 + "\"}\n"):
            with self.assertRaises(c.Failed, msg=out):
                c.parse_ticket(out)


class Cookie(unittest.TestCase):
    def headers(self, *values):
        m = Message()
        for v in values:
            m["Set-Cookie"] = v
        return m

    def test_the_cookie_of_the_port(self):
        h = self.headers("other=1; Path=/", "spectio_session_8123=s3cr3t; HttpOnly; SameSite=Strict; Path=/")
        self.assertEqual(c.session_cookie(h, 8123), "spectio_session_8123=s3cr3t")

    def test_another_port_is_not_ours(self):
        with self.assertRaises(c.Failed):
            c.session_cookie(self.headers("spectio_session_8124=s3cr3t; Path=/"), 8123)


class Golden(unittest.TestCase):
    def test_counts_per_process_in_task_states(self):
        self.assertEqual(c.golden_counts(GOLDEN), {"ALIGN": {"succeeded": 24}, "MERGE": {"succeeded": 1}})

    def test_the_last_run_only(self):
        text = GOLDEN + "2\tALIGN\tCACHED\t0\t1\t*\t24\n2\tMERGE\tCOMPLETED\t0\t1\t*\t1\n"
        self.assertEqual(c.golden_counts(text), {"ALIGN": {"cached": 24}, "MERGE": {"succeeded": 1}})

    def test_an_unknown_status_is_refused(self):
        with self.assertRaises(c.Failed):
            c.golden_counts(GOLDEN.replace("1\tMERGE\tCOMPLETED", "1\tMERGE\tWEIRD"))

    def test_the_api_counts_upper_cased(self):
        items = [{"process": "align", "counts": {"succeeded": 24}}, {"process": "MERGE", "counts": {"succeeded": 1}}]
        self.assertEqual(c.process_counts(items), c.golden_counts(GOLDEN))

    def test_a_difference_is_named(self):
        diff = c.count_diff({"ALIGN": {"succeeded": 24}}, {"ALIGN": {"succeeded": 23}, "QC": {"failed": 1}})
        self.assertEqual(diff, ["ALIGN: want {'succeeded': 24}, got {'succeeded': 23}",
                                "QC: want {}, got {'failed': 1}"])
        self.assertEqual(c.count_diff({"A": {"succeeded": 1}}, {"A": {"succeeded": 1}}), [])


class States(unittest.TestCase):
    def test_queued_running_succeeded(self):
        self.assertIsNone(c.states_problem(["queued", "running", "succeeded"]))

    def test_each_state_missing_or_wrong(self):
        for seen in (["running", "succeeded"], ["queued", "succeeded"], ["queued", "running", "failed"],
                     ["queued", "running", "cancelling", "succeeded"], []):
            self.assertIsNotNone(c.states_problem(seen), seen)

    def test_changes_only(self):
        self.assertEqual(c.changes(["queued", "queued", "running", "running", "succeeded"]),
                         ["queued", "running", "succeeded"])


class Expect(unittest.TestCase):
    def test_every_line_is_a_check(self):
        checks = {"run succeeded": None, "counts equal the golden": "ALIGN: want 24"}
        self.assertEqual(c.expect_problems(["run succeeded", "counts equal the golden"], checks),
                         ["counts equal the golden: ALIGN: want 24"])

    def test_an_unknown_line_fails(self):
        self.assertEqual(c.expect_problems(["run is fast"], {"run succeeded": None}),
                         ["run is fast: no such check in e2e_client.py"])

    def test_the_committed_scenario_names_known_checks(self):
        lines = c.scenario_expect(os.path.join(HERE, "..", "scenarios", "happy-slurm-mini.yaml"))
        self.assertTrue(lines)
        self.assertEqual(set(lines) - set(c.CHECKS), set())


class Jobs(unittest.TestCase):
    def test_jobs_of_the_run_by_work_dir(self):
        lines = ["12|nf-ALIGN_(S01)|/r/runs/run_1/work/ab/cd", "13|other|/r/runs/run_10/work", "14|x|/r/runs/run_1",
                 ""]
        self.assertEqual(c.run_jobs(lines, "/r/runs/run_1"), ["12|nf-ALIGN_(S01)|/r/runs/run_1/work/ab/cd",
                                                               "14|x|/r/runs/run_1"])

    def test_head_jobs_by_name(self):
        self.assertEqual(c.head_jobs(["12|nf-ALIGN|/w", "13|spectio-head-run_1|/w"]), ["13|spectio-head-run_1|/w"])


class Squeue(unittest.TestCase):
    """A squeue that exits non-zero (slurmctld unreachable, a bad flag) is a failure, never an empty queue."""

    def test_a_non_zero_exit_raises_with_its_stderr(self):
        with self.assertRaisesRegex(c.Failed, "exited 3: slurmctld down"):
            c.lines_of(sys.executable, "-c", "import sys; sys.stderr.write('slurmctld down'); sys.exit(3)")

    def test_a_zero_exit_gives_the_lines(self):
        self.assertEqual(c.lines_of(sys.executable, "-c", "print('a'); print('b')"), ["a", "b"])

    def test_a_failed_squeue_is_left_over_not_nothing(self):
        with mock.patch.object(c, "squeue", side_effect=c.Failed("squeue exited 1: no controller")), \
                mock.patch.object(c, "tmux_has", return_value=False):
            self.assertEqual(c.left_over("/r/runs/run_1", "spectio-run_1"),
                             "squeue failed: squeue exited 1: no controller")

    def test_nothing_left(self):
        with mock.patch.object(c, "squeue", return_value=["13|other|/r/runs/run_10/work"]), \
                mock.patch.object(c, "tmux_has", return_value=False):
            self.assertIsNone(c.left_over("/r/runs/run_1", "spectio-run_1"))

    def test_a_job_or_the_session_left(self):
        with mock.patch.object(c, "squeue", return_value=["12|x|/r/runs/run_1/work"]), \
                mock.patch.object(c, "tmux_has", return_value=True):
            self.assertEqual(c.left_over("/r/runs/run_1", "spectio-run_1"),
                             "jobs in squeue: ['12|x|/r/runs/run_1/work']; tmux session spectio-run_1: True")


if __name__ == "__main__":
    unittest.main()
