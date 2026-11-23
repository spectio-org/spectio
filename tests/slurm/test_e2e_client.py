"""The pure parts of e2e_client.py (P1 Tasks 22 and 23): the ticket line, the session cookie, the golden
counts, the run's states, the expect lines of a scenario and the jobs of a run, the cancel and restart checks
and the teardown; and its transport, against a stand-in HTTP server on a Unix socket and on TCP. No Spectio
server and no cluster: tests/slurm/e2e.sh runs the client itself. Runs in ci.yml (ci-ok) and in pipelines-slurm.yml."""
import ast
import http.server
import io
import json
import os
import socket
import socketserver
import sqlite3
import subprocess
import sys
import tempfile
import threading
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


class Local(unittest.TestCase):
    """Local mode (P2 §10.8, G7): the head runs in its own session (setsid), not in tmux, and there is no squeue."""

    def test_the_checks_of_each_mode(self):
        self.assertEqual(c.checks_of({"executor": "local"}), c.LOCAL_CHECKS)
        self.assertEqual(c.checks_of({"executor": "slurm"}), c.CHECKS)
        self.assertEqual(c.checks_of({}), c.CHECKS)  # the default executor is slurm
        self.assertNotIn("head in tmux, no sbatch", c.LOCAL_CHECKS)

    def test_the_committed_local_scenarios_name_every_local_check(self):
        for name in ("happy-local.yaml", "happy-local-snakemake.yaml"):
            lines = c.scenario_expect(os.path.join(HERE, "..", "scenarios", name))
            self.assertEqual(sorted(lines), sorted(c.LOCAL_CHECKS), name)

    def test_head_pid_as_the_head_script_writes_it(self):
        line = "4242 4242 987654 0f1e2d3c-4b5a-6978-8a9b-0c1d2e3f4a5b node-1\n"
        self.assertEqual(c.head_pid(line), (4242, 4242, "987654"))
        for bad in ("", "4242 4242 987654\n", "x 4242 987654 0f1e2d3c-4b5a-6978-8a9b-0c1d2e3f4a5b n\n"):
            self.assertIsNone(c.head_pid(bad), bad)

    def test_own_session(self):
        self.assertIsNone(c.own_session((4242, 4242, "98"), {"session": "4242.98", "alive": True}))
        self.assertIn("group 1", c.own_session((4242, 1, "98"), {"session": "4242.98", "alive": True}))
        self.assertIn("4242.98", c.own_session((4242, 4242, "98"), {"session": "4242.97", "alive": True}))
        self.assertIn("not alive", c.own_session((4242, 4242, "98"), {"session": "4242.98", "alive": False}))
        self.assertIn("no head.pid", c.own_session(None, {"session": "4242.98", "alive": True}))

    def test_a_head_is_left_while_its_process_lives(self):
        me = os.getpid()
        start = c.proc_start(me)
        self.assertIsNotNone(start)
        self.assertIn(str(me), c.head_left((me, me, start)))
        self.assertIsNone(c.head_left((me, me, start + "0")))  # another process that reused the PID
        self.assertIsNone(c.head_left(None))


class CancelChecks(unittest.TestCase):
    """P1 Task 23: once running with tasks running, `POST :cancel`; the run goes cancelling, then cancelled."""

    def test_ready_once_running_with_a_task_running(self):
        self.assertTrue(c.tasks_running({"state": "running", "task_counts": {"running": 2, "succeeded": 1}}))
        self.assertFalse(c.tasks_running({"state": "running", "task_counts": {"succeeded": 3}}))
        self.assertFalse(c.tasks_running({"state": "running", "task_counts": {}}))
        self.assertFalse(c.tasks_running({"state": "queued", "task_counts": {"running": 1}}))

    def test_queued_running_cancelling_cancelled(self):
        seen = ["queued", "running", "running", "cancelling", "cancelled"]
        self.assertIsNone(c.states_problem(seen, c.CANCELLED_PATH))
        self.assertIsNotNone(c.states_problem(seen))  # the default path ends succeeded

    def test_each_wrong_path(self):
        for seen in (["queued", "running", "cancelled"], ["queued", "running", "cancelling"],
                     ["queued", "running", "cancelling", "failed"], ["queued", "cancelling", "cancelled"],
                     ["queued", "running", "succeeded"], []):
            self.assertIsNotNone(c.states_problem(seen, c.CANCELLED_PATH), seen)

    def test_the_grace_is_the_tmux_launchers(self):
        """Read from the source with ast, so the check also runs where spectio is not installed (CR-P3T23-01)."""
        tree = ast.parse(open(os.path.join(HERE, "..", "..", "packages", "spectio", "src", "spectio", "runner",
                                           "tmux.py")).read())
        launcher = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "TmuxLauncher")
        cancel = next(n for n in launcher.body if isinstance(n, ast.FunctionDef) and n.name == "cancel")
        names = [a.arg for a in cancel.args.args]
        default = cancel.args.defaults[names.index("grace_s") - (len(names) - len(cancel.args.defaults))]
        self.assertEqual(ast.literal_eval(default), c.CANCEL_GRACE_S)

    def test_job_states_of_the_run(self):
        lines = ["12|nf-A|CANCELLED|/r/runs/run_1/work/ab", "13|nf-B|RUNNING|/r/runs/run_1/work/cd",
                 "14|nf-C|CANCELLED|/r/runs/run_10/work", "15|nf-D|COMPLETED|/r/runs/run_1"]
        self.assertEqual(c.job_states(lines, "/r/runs/run_1"), {"CANCELLED": 1, "RUNNING": 1, "COMPLETED": 1})
        self.assertEqual(c.job_states([], "/r/runs/run_1"), {})


class Store(unittest.TestCase):
    """Read-only queries of the server's database: attempts by state, and duplicate event IDs."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = os.path.join(tmp.name, "spectio.db")
        with sqlite3.connect(self.db) as conn:
            conn.executescript(
                "CREATE TABLE tasks (id TEXT, run_id TEXT, process_or_rule TEXT, state TEXT);"
                "CREATE TABLE attempts (id TEXT, task_id TEXT, n INTEGER, state TEXT);"
                "CREATE TABLE events (id TEXT, run_id TEXT, event_id TEXT);"
                "INSERT INTO tasks VALUES ('t1', 'run_1', 'ALIGN', 'running'), ('t2', 'run_1', 'QC', 'aborted'),"
                " ('t3', 'run_2', 'ALIGN', 'running');"
                "INSERT INTO attempts VALUES ('a1', 't1', 1, 'running'), ('a2', 't2', 1, 'aborted'),"
                " ('a3', 't2', 2, 'failed'), ('a4', 't3', 1, 'running');"
                "INSERT INTO events VALUES ('e1', 'run_1', 'x'), ('e2', 'run_1', 'y'), ('e3', 'run_1', 'x'),"
                " ('e4', 'run_2', 'y');")
        conn.close()

    def test_attempts_in_a_state(self):
        self.assertEqual(c.attempts_in(self.db, "run_1", ("running",)), ["ALIGN attempt 1: running"])
        self.assertEqual(c.attempts_in(self.db, "run_1", ("pending",)), [])

    def test_open_attempts_are_pending_submitted_or_running(self):
        self.assertEqual(c.OPEN_ATTEMPTS, ("pending", "submitted", "running"))
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO attempts VALUES ('a5', 't2', 3, 'submitted'), ('a6', 't2', 4, 'pending')")
        conn.close()
        self.assertEqual(c.attempts_in(self.db, "run_1", c.OPEN_ATTEMPTS),
                         ["ALIGN attempt 1: running", "QC attempt 3: submitted", "QC attempt 4: pending"])
        self.assertIn("no attempt left pending, submitted or running", c.CANCEL_CHECKS)

    def test_the_restart_checks_the_spool_too(self):
        self.assertIn("no spool drop", c.RESTART_CHECKS)

    def test_duplicate_event_ids(self):
        self.assertEqual(c.duplicate_events(self.db, "run_1"), ["x (2 times)"])
        self.assertEqual(c.duplicate_events(self.db, "run_2"), [])


class Restart(unittest.TestCase):
    """P1 Task 23: SIGKILL the server named by server.json, start it again, and the head is adopted."""

    LOG = ("-V\n"
           "new-session -d -P -F #{pane_id} #{pane_pid} -s spectio-server -c / /usr/bin/env -i a=b\n"
           "new-session -d -P -F #{pane_id} #{pane_pid} -s spectio-run_1 -c /r/run_1/launch /bin/bash h.sh\n"
           "has-session -t =spectio-run_1\n"
           "new-session -d -P -F #{pane_id} #{pane_pid} -s spectio-run_10 -c /r/run_10/launch /bin/bash h.sh\n"
           "list-panes -s -t =spectio-run_1 -F #{pane_id} #{pane_pid}\n")

    def test_new_sessions_of_the_run(self):
        self.assertEqual(c.new_sessions(self.LOG, "spectio-run_1"), 1)
        self.assertEqual(c.new_sessions(self.LOG + self.LOG, "spectio-run_1"), 2)
        self.assertEqual(c.new_sessions(self.LOG, "spectio-run_2"), 0)
        self.assertEqual(c.new_sessions("", "spectio-run_1"), 0)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data = tmp.name

    def state(self, **record):
        with open(os.path.join(self.data, "server.json"), "w") as f:
            json.dump({"host": socket.gethostname(), "port": 8123} | record, f)

    def fake_serve(self, *tail):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", *tail])
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        return proc

    def test_the_pid_of_a_spectio_serve_on_this_node(self):
        proc = self.fake_serve("-m", "spectio", "serve", "--pane")
        self.state(pid=proc.pid)
        self.assertEqual(c.server_pid(self.data), proc.pid)

    def test_not_the_pane_or_not_ours_is_refused(self):
        """SEC-P3T23-03: only `-m spectio serve --pane` (cli/serve.py `_runs_pane_serve`), of this uid."""
        for tail in (("spectio", "serve"), ("-m", "spectio", "serve"), ("-m", "spectio", "serve", "--detach")):
            proc = self.fake_serve(*tail)
            self.state(pid=proc.pid)
            with self.assertRaisesRegex(c.Failed, "not spectio serve --pane", msg=tail):
                c.server_pid(self.data)
        proc = self.fake_serve("-m", "spectio", "serve", "--pane")
        self.state(pid=proc.pid)
        with mock.patch.object(c.os, "getuid", return_value=os.getuid() + 1), \
                self.assertRaisesRegex(c.Failed, "uid"):
            c.server_pid(self.data)

    def test_kill_server_sigkills_it_through_a_pidfd(self):
        proc = self.fake_serve("-m", "spectio", "serve", "--pane")
        self.state(pid=proc.pid)
        with mock.patch.object(c.signal, "pidfd_send_signal", wraps=c.signal.pidfd_send_signal) as sent:
            self.assertEqual(c.kill_server(self.data), proc.pid)
        self.assertEqual(proc.wait(timeout=10), -9)
        self.assertEqual(sent.call_args.args[1], c.signal.SIGKILL)
        with self.assertRaises(c.Failed):  # gone now
            c.kill_server(self.data)

    def test_any_other_pid_is_refused(self):
        for record in ({"pid": os.getpid()}, {"pid": "1"}, {"pid": 1}, {"pid": None},
                       {"pid": os.getpid(), "host": "elsewhere"}):
            self.state(**record)
            with self.assertRaises(c.Failed, msg=record):
                c.server_pid(self.data)


class Teardown(unittest.TestCase):
    """FU-P3-68: after a failure, the heads' sessions and the jobs of the runs under the runs root go."""

    def test_sessions_and_jobs_under_the_runs_root(self):
        names = ["run_01M7PX2ZKY0WRFJFYGWH5WAQA0", "golden.tsv", "run_x", "run_01M7PX6QD89EB1SPPZSMGFAFZY"]
        lines = ["12|nf-A|/r/runs/run_01M7PX2ZKY0WRFJFYGWH5WAQA0/work/ab", "13|other|/r/runs2/x", "14|b|/r/runs/z"]
        self.assertEqual(c.teardown_plan(names, lines, "/r/runs"),
                         (["spectio-run_01M7PX2ZKY0WRFJFYGWH5WAQA0", "spectio-run_01M7PX6QD89EB1SPPZSMGFAFZY"],
                          ["12", "14"]))


class Main(unittest.TestCase):
    """A hung squeue or tmux (TimeoutExpired) or an OSError ends the client with a FAIL line, not a traceback
    (CR-P3T22-08 (r3)); a teardown with no config left tears nothing down and passes."""

    def test_a_timeout_or_os_error_is_a_fail_line(self):
        for exc in (subprocess.TimeoutExpired(["squeue"], 60), ProcessLookupError(3, "No such process")):
            with self.subTest(exc), mock.patch.object(c, "cancel", side_effect=exc), \
                    mock.patch("sys.stdout", new_callable=io.StringIO) as out:
                self.assertEqual(c.main(["cancel", "nextflow", "--config", "x", "--location", "y"]), 1)
                self.assertTrue(out.getvalue().startswith("FAIL "), out.getvalue())

    def test_teardown_without_a_config(self):
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(c.main(["teardown", "--config", "/nonexistent/spectio.toml"]), 0)
        self.assertIn("teardown: nothing to tear down", out.getvalue())


class Echo(http.server.BaseHTTPRequestHandler):
    """Answers each request with what it received; `/missing` answers 404 with a JSON problem."""

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        code = 404 if self.path == "/missing" else 200
        doc = json.dumps({"path": self.path, "method": self.command, "host": self.headers["Host"],
                          "origin": self.headers["Origin"], "cookie": self.headers["Cookie"],
                          "type": self.headers["Content-Type"], "body": body.decode()}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Set-Cookie", "spectio_session_8123=s3cr3t; HttpOnly; Path=/")
        self.send_header("Content-Length", str(len(doc)))
        self.end_headers()
        self.wfile.write(doc)

    def log_message(self, *args):  # quiet, and a Unix peer has no address to log
        pass


class UnixEcho(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class TcpEcho(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


class Transport(unittest.TestCase):
    """FU-P3-72: on SLURM and shared hosts the server listens only on `spectio.sock` in its database directory.
    The client finds it in server.json and speaks HTTP over it, with the Host and Origin of the tunnel's end."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data, self.db = os.path.join(tmp.name, "data"), os.path.join(tmp.name, "db")
        os.mkdir(self.data, 0o700)
        os.mkdir(self.db, 0o700)
        self.sock = os.path.join(self.db, "spectio.sock")

    def state(self, **record):
        with open(os.path.join(self.data, "server.json"), "w") as f:
            json.dump({"host": "n1", "port": 8123, "socket": self.sock, "pid": 1, "db_dir": self.db} | record, f)

    def serve(self, server):
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

    def test_the_socket_of_server_json(self):
        self.state()
        self.assertEqual(c.server_address(self.data, self.db), (8123, self.sock))

    def test_a_tcp_server_has_no_socket(self):
        self.state(socket=None)
        self.assertEqual(c.server_address(self.data, self.db), (8123, None))

    def test_a_socket_elsewhere_or_a_bad_record_is_refused(self):
        for record in ({"socket": "/srv/other/spectio.sock"}, {"socket": self.db + "/other.sock"},
                       {"socket": 7}, {"port": 80}, {"port": "8123"}):
            self.state(**record)
            with self.assertRaises(c.Failed, msg=record):
                c.server_address(self.data, self.db)

    def test_on_slurm_a_server_without_a_socket_is_refused(self):
        """SEC-P3T23-01: on SLURM the server listens only on its socket, never TCP: no fallback."""
        self.state(socket=None)
        with self.assertRaisesRegex(c.Failed, "no socket"):
            c.server_address(self.data, self.db, socket_only=True)
        self.state()
        self.assertEqual(c.server_address(self.data, self.db, socket_only=True), (8123, self.sock))
        self.assertTrue(c.socket_only({"executor": "slurm"}))
        self.assertTrue(c.socket_only({}))
        self.assertFalse(c.socket_only({"executor": "local"}))

    def test_a_listener_on_the_port_fails_socket_only(self):
        listener = socket.socket()
        self.addCleanup(listener.close)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        self.assertIn(f"127.0.0.1:{port}", c.tcp_listener(port))
        listener.close()
        self.assertIsNone(c.tcp_listener(port))
        self.assertIsNone(c.tcp_listener(None))  # server.json names no port
        for checks in (c.CHECKS, c.CANCEL_CHECKS, c.RESTART_CHECKS):
            self.assertIn("socket only, no TCP port", checks)
        self.assertNotIn("socket only, no TCP port", c.LOCAL_CHECKS)

    def test_the_same_socket_after_the_restart(self):
        self.assertIsNone(c.same_socket(self.sock, self.sock))
        self.assertIn("moved", c.same_socket(self.sock, self.db + "/x/spectio.sock"))
        self.assertIn("no socket", c.same_socket(None, None))  # None == None is not the same socket

    def test_no_server_json(self):
        with self.assertRaisesRegex(c.Failed, "server.json"):
            c.server_address(self.data, self.db)

    def check_exchange(self, api):
        api.cookie = "spectio_session_8123=s3cr3t"
        doc, headers = api.expect(200, "POST", "/api/v1/runs", {"a": 1})
        self.assertEqual(doc, {"path": "/api/v1/runs", "method": "POST", "host": "127.0.0.1:8123",
                               "origin": "http://127.0.0.1:8123", "cookie": "spectio_session_8123=s3cr3t",
                               "type": "application/json", "body": '{"a": 1}'})
        self.assertEqual(c.session_cookie(headers, 8123), "spectio_session_8123=s3cr3t")
        code, doc, _ = api.call("POST", "/missing", {})
        self.assertEqual((code, doc["path"]), (404, "/missing"))
        with self.assertRaisesRegex(c.Failed, "HTTP 404, not 200"):
            api.expect(200, "POST", "/missing", {})

    def test_http_over_the_unix_socket(self):
        self.serve(UnixEcho(self.sock, Echo))
        # A proxy in the environment is never used: the request goes to the socket.
        with mock.patch.dict(os.environ, {"http_proxy": "http://192.0.2.1:9", "HTTP_PROXY": "http://192.0.2.1:9"}):
            self.check_exchange(c.Api(8123, self.sock))

    def test_http_over_tcp_without_a_socket(self):
        server = TcpEcho(("127.0.0.1", 0), Echo)
        self.serve(server)
        api = c.Api(8123, None)
        api.address = ("127.0.0.1", server.server_address[1])  # the stand-in's port; Host stays 127.0.0.1:8123
        self.check_exchange(api)

    def test_nothing_on_the_socket_is_a_failure(self):
        with self.assertRaisesRegex(c.Failed, "spectio.sock"):
            c.Api(8123, self.sock).call("GET", "/api/v1/runs")


if __name__ == "__main__":
    unittest.main()
