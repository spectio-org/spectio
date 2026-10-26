"""Tests for budget.py. Run: python3 -m unittest tools/autopilot/test_budget.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name("budget.py")
T0 = 1_800_000_000.0  # fixed clock
H = 3600.0


class Budget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / ".autopilot").mkdir()
        self.t = T0

    def tearDown(self):
        self.tmp.cleanup()

    def run_b(self, *args, stdin=None):
        env = {**os.environ, "SPECTIO_AUTOPILOT_ROOT": str(self.root), "SPECTIO_BUDGET_NOW": str(self.t)}
        r = subprocess.run([sys.executable, str(SCRIPT), *args], env=env, input=stdin, capture_output=True, text=True)
        return r.returncode, r.stdout.strip()

    def usage(self, week=None, five=None, week_reset=T0 + 3 * 24 * H, five_reset=T0 + 4 * H, cost=0.0):
        u = {"at": self.t, "session_id": "s1", "cost_usd": cost}
        if week is not None:
            u["seven_day"] = {"used_percentage": week, "resets_at": week_reset}
        if five is not None:
            u["five_hour"] = {"used_percentage": five, "resets_at": five_reset}
        (self.root / ".autopilot/usage.json").write_text(json.dumps(u))

    def check(self, kinds="review,review,spike"):
        code, out = self.run_b("check", "--kinds", kinds)
        return code, json.loads(out)

    def test_weekly_points_counts_from_start_and_stops(self):
        self.usage(week=40, five=10)
        self.run_b("start", "--weekly", "10")
        code, d = self.check()
        self.assertEqual((code, d["action"], d["fits"]), (0, "go", 3))
        self.t += 600; self.usage(week=47, five=30)
        code, d = self.check()
        self.assertEqual(d["consumed"], 7.0)
        self.assertEqual((code, d["action"], d["fits"]), (0, "go", 1))  # 3 left - margin 2 = 1 point: one review
        code, d = self.check("spike")
        self.assertEqual((code, d["action"]), (3, "stop"))  # a spike (1.5) does not fit

    def test_weekly_points_survive_a_weekly_reset(self):
        self.usage(week=95, five=10)
        self.run_b("start", "--weekly", "20")
        self.t += 600; self.usage(week=98, five=12)
        self.check()
        self.t += 600; self.usage(week=4, five=14, week_reset=T0 + 10 * 24 * H)  # new week
        code, d = self.check("review")
        self.assertEqual(d["consumed"], 7.0)  # 3 before + 4 after the reset
        self.assertEqual(d["action"], "go")

    def test_five_hour_window_full_means_wait_not_stop(self):
        self.usage(week=30, five=99)
        self.run_b("start", "--weekly", "30")
        code, d = self.check()
        self.assertEqual((code, d["action"]), (4, "wait"))
        self.assertAlmostEqual(d["wait_until"], T0 + 4 * H + 120)

    def test_until_exhausted_stops_at_window_reset(self):
        self.usage(week=30, five=60, five_reset=T0 + 4 * H)  # e.g. 11:00, window resets 15:00
        self.run_b("start", "--until-exhausted", "--window", "five_hour")
        code, d = self.check()
        self.assertEqual(d["action"], "go")
        self.t += 4 * H + 1; self.usage(week=40, five=2, five_reset=T0 + 9 * H)
        code, d = self.check()
        self.assertEqual((code, d["action"]), (3, "stop"))
        self.assertIn("deadline", d["reason"])

    def test_until_exhausted_stops_near_100(self):
        self.usage(five=60)
        self.run_b("start", "--until-exhausted", "--window", "five_hour", "--no-stop-at-reset")
        self.t += 600; self.usage(five=97)
        code, d = self.check("review")
        self.assertEqual(d["action"], "stop")

    def test_estimate_from_calibrated_cost_when_no_live_reading(self):
        self.usage(week=40)
        self.run_b("start", "--weekly", "10", "--pct-per-usd", "0.5")
        self.run_b("record-cost", "--usd", "8", "--kind", "tick")   # 8 USD x 0.5 = 4 points
        self.t += 2 * H  # usage.json now stale
        code, d = self.check("tick")
        self.assertEqual(d["source"], "estimated")
        self.assertEqual(d["consumed"], 4.0)

    def test_manual_baseline(self):
        self.run_b("start", "--weekly", "10", "--now", "50", "--pct-per-usd", "1")
        code, d = self.check("review")
        self.assertEqual(d["action"], "go")

    def test_no_reading_at_all_stops(self):
        self.run_b("start", "--weekly", "10")
        code, d = self.check()
        self.assertEqual(d["action"], "stop")
        self.assertIn("no usage reading", d["reason"])

    def test_limit_hit_from_stream(self):
        self.usage(week=50, five=50)
        self.run_b("start", "--until-exhausted", "--window", "seven_day")
        ev = [{"type": "system", "subtype": "api_retry", "error": "rate_limit", "attempt": 1, "max_retries": 10},
              {"type": "system", "subtype": "api_retry", "error": "rate_limit", "attempt": 10, "max_retries": 10},
              {"type": "result", "total_cost_usd": 1.25}]
        code, out = self.run_b("ingest-stream", stdin="\n".join(json.dumps(e) for e in ev) + "\n")
        self.assertEqual(len(out.splitlines()), 3)  # passed through
        code, d = self.check()
        self.assertEqual(d["action"], "stop")
        costs = (self.root / ".autopilot/costs.jsonl").read_text().splitlines()
        self.assertEqual(json.loads(costs[0])["usd"], 1.25)

    def test_no_budget_means_go(self):
        code, d = self.check()
        self.assertEqual((code, d["action"]), (0, "go"))


if __name__ == "__main__":
    unittest.main()
