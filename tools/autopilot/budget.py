#!/usr/bin/env python3
"""Budget governor for the Spectio autopilot (docs/playbooks/autopilot.md §6).

Two modes:
  points   use at most N percentage points of a plan window (default: the weekly window),
           counted from now, across a window reset.
  exhaust  keep going until the window is used up (100 % minus a margin), and by default stop
           when that window resets ("launch Wednesday 11:00, run until the quota resets at 15:00").

Readings, best first:
  live       .autopilot/usage.json, written by tools/autopilot/statusline.py (or by `ingest-stream`
             when the stream carries a rate-limit event), fresher than 15 minutes;
  estimated  last live reading + USD recorded since then x a calibrated percent-per-USD ratio;
  manual     the percentage typed by Thomas at `start --now` (read it from /usage).

Commands (state in .autopilot/budget.json, costs in .autopilot/costs.jsonl):
  start      --weekly 30 | --five-hour 40 | --until-exhausted [--window five_hour] [--no-stop-at-reset]
             [--deadline 15:00|ISO] [--now PCT] [--pct-per-usd R]
  check      [--kinds review,review,spike]   -> exit 0 go (prints how many fit), 4 wait, 3 stop
  record-cost --usd X [--kind K] [--step ID]
  limit-hit  [--reason rate_limit] [--window five_hour|seven_day]
  ingest-stream   tee a `claude -p --output-format stream-json` stream, recording costs and limits
  status     one line for the AUTOPILOT status
  off        remove the budget
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import statistics
import sys
import tempfile
import time

ROOT = pathlib.Path(os.environ.get("SPECTIO_AUTOPILOT_ROOT", pathlib.Path(__file__).resolve().parents[2]))
DIR = ROOT / ".autopilot"
BUDGET = DIR / "budget.json"
USAGE = DIR / "usage.json"
COSTS = DIR / "costs.jsonl"
LIMIT = DIR / "limit-hit.json"

FRESH_S = 15 * 60
# Prior cost of one step, in percentage points of the weekly window, before any calibration.
# Assumed values, replaced by medians from costs.jsonl as soon as there are three samples of a kind.
PRIOR_POINTS = {"review": 1.0, "spike": 1.5, "build": 2.0, "plan": 1.0, "apply": 1.0, "triage": 0.5, "tick": 2.0}
WINDOWS = ("five_hour", "seven_day")
EXIT_GO, EXIT_STOP, EXIT_WAIT = 0, 3, 4


# ---------- small helpers ----------

def now() -> float:
    return float(os.environ.get("SPECTIO_BUDGET_NOW", time.time()))


def load(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def costs() -> list[dict]:
    if not COSTS.exists():
        return []
    return [json.loads(line) for line in COSTS.read_text().splitlines() if line.strip()]


def parse_deadline(text: str | None) -> float | None:
    if not text:
        return None
    local = dt.datetime.fromtimestamp(now()).astimezone()
    try:
        hh, mm = (int(x) for x in text.split(":"))
        when = local.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if when.timestamp() <= now():
            when += dt.timedelta(days=1)
        return when.timestamp()
    except ValueError:
        when = dt.datetime.fromisoformat(text)
        if when.tzinfo is None:
            when = when.replace(tzinfo=local.tzinfo)
        return when.timestamp()


def hhmm(ts: float | None) -> str:
    return dt.datetime.fromtimestamp(ts).astimezone().strftime("%a %H:%M") if ts else "?"


# ---------- readings ----------

def live_reading(window: str) -> dict | None:
    """The window's latest live reading, or None when missing or stale."""
    usage = load(USAGE, {})
    w = usage.get(window)
    if not isinstance(w, dict) or "used_percentage" not in w:
        return None
    if now() - usage.get("at", 0) > FRESH_S:
        return None
    resets = w.get("resets_at")
    if resets and resets < now():  # the window has reset since the reading: it is ~0 now
        return {"pct": 0.0, "resets_at": None, "source": "live"}
    return {"pct": float(w["used_percentage"]), "resets_at": resets, "source": "live",
            "cost_usd": usage.get("cost_usd"), "session_id": usage.get("session_id")}


def meter_usd() -> float:
    return sum(c.get("usd", 0.0) for c in costs())


def ratio(b: dict, window: str) -> float | None:
    samples = b.get("ratio_samples", {}).get(window, [])
    if len(samples) >= 2:
        return statistics.median(samples)
    return b.get("pct_per_usd", {}).get(window)


def reading(b: dict, window: str) -> dict | None:
    r = live_reading(window)
    if r:
        return r
    last = b.get("last", {}).get(window)
    if not last:
        return None
    if last.get("resets_at") and last["resets_at"] < now():
        return {"pct": 0.0, "resets_at": None, "source": "estimated"}
    k = ratio(b, window)
    if k is None:
        return {**last, "source": last.get("source", "manual") + "-stale"}
    est = last["pct"] + max(0.0, meter_usd() - last.get("meter_usd", 0.0)) * k
    return {"pct": min(100.0, est), "resets_at": last.get("resets_at"), "source": "estimated"}


def account(b: dict) -> None:
    """Fold the latest live readings into b['consumed'] and calibrate the ratio."""
    m = meter_usd()
    for window in WINDOWS:
        r = live_reading(window)
        if not r:
            continue
        last = b.setdefault("last", {}).get(window)
        if last:
            moved = bool(r.get("resets_at") and last.get("resets_at") and r["resets_at"] > last["resets_at"] + 60)
            cleared = r.get("resets_at") is None and bool(last.get("resets_at"))
            reset = moved or cleared
            delta = r["pct"] if reset else max(0.0, r["pct"] - last["pct"])
            if window == b["window"]:
                b["consumed"] = round(b.get("consumed", 0.0) + delta, 3)
            usd = m - last.get("meter_usd", 0.0)
            if not reset and usd > 0.05 and delta > 0:
                s = b.setdefault("ratio_samples", {}).setdefault(window, [])
                s.append(round(delta / usd, 4))
                del s[:-20]
        b["last"][window] = {"pct": r["pct"], "resets_at": r.get("resets_at"), "at": now(),
                             "meter_usd": m, "source": "live"}


# ---------- decisions ----------

def step_points(b: dict, kind: str) -> float:
    k = ratio(b, "seven_day") if b["window"] == "seven_day" else ratio(b, b["window"])
    usd = [c["usd"] for c in costs() if c.get("kind") == kind and c.get("usd")]
    if k is not None and len(usd) >= 3:
        return statistics.median(usd) * k
    return PRIOR_POINTS.get(kind, 2.0) * (1.0 if b["window"] == "seven_day" else 4.0)


def decide(b: dict, kinds: list[str]) -> dict:
    account(b)
    t = now()
    out = {"action": "go", "fits": len(kinds), "reason": "", "mode": b["mode"], "window": b["window"]}
    hit = load(LIMIT, None)
    if hit and hit.get("at", 0) >= b.get("started_at", 0):
        win = hit.get("window") or "five_hour"
        resets = hit.get("resets_at")
        if win == "five_hour" and b["window"] == "seven_day" and resets and (not b.get("deadline") or resets < b["deadline"]):
            return {**out, "action": "wait", "fits": 0, "reason": "five-hour limit hit", "wait_until": resets + 120}
        return {**out, "action": "stop", "fits": 0, "reason": f"plan limit hit ({hit.get('reason', 'rate_limit')})"}
    if b.get("deadline") and t >= b["deadline"]:
        return {**out, "action": "stop", "fits": 0, "reason": f"deadline {hhmm(b['deadline'])} reached"}

    r = reading(b, b["window"])
    out["source"] = r["source"] if r else "none"
    out["pct"] = round(r["pct"], 1) if r else None
    est = [step_points(b, k) for k in kinds]
    margin = max(b.get("margin_min", 2.0), max(est, default=0.0))
    out["margin"] = round(margin, 1)

    # The five-hour window can block a weekly budget: wait for its reset instead of stopping.
    if b["window"] == "seven_day":
        r5 = reading(b, "five_hour")
        if r5 and r5["pct"] >= 100 - max(5.0, margin * 4) and r5.get("resets_at"):
            return {**out, "action": "wait", "fits": 0, "reason": f"five-hour window at {r5['pct']:.0f}%",
                    "wait_until": r5["resets_at"] + 120}

    if r is None:
        return {**out, "action": "stop", "fits": 0,
                "reason": "no usage reading: install the status line tap or pass --now at start"}

    ceiling = 100.0 - margin
    if b["mode"] == "points":
        consumed = b.get("consumed", 0.0)
        if r["source"] != "live":
            last = b.get("last", {}).get(b["window"], {})
            consumed += max(0.0, r["pct"] - last.get("pct", r["pct"]))
        room = min(b["points"] - consumed, ceiling - r["pct"]) - margin
        out.update(consumed=round(consumed, 1), target=b["points"])
    else:
        room = ceiling - r["pct"]
    fits, used = 0, 0.0
    for e in est:
        if used + e > room:
            break
        used += e
        fits += 1
    out["fits"] = fits
    out["room"] = round(room, 1)
    if fits == 0:
        out.update(action="stop", reason="budget used" if b["mode"] == "points" else "window used up")
    return out


# ---------- commands ----------

def cmd_start(a) -> int:
    window = "five_hour" if (a.five_hour is not None or (a.until_exhausted and a.window == "five_hour")) else "seven_day"
    if a.until_exhausted:
        b = {"mode": "exhaust", "window": a.window or "five_hour"}
        window = b["window"]
    else:
        pts = a.weekly if a.weekly is not None else a.five_hour
        if pts is None:
            print("give --weekly N, --five-hour N or --until-exhausted", file=sys.stderr)
            return 2
        b = {"mode": "points", "window": window, "points": float(pts)}
    b.update(started_at=now(), consumed=0.0, margin_min=a.margin, last={}, ratio_samples={},
             pct_per_usd={w: a.pct_per_usd for w in WINDOWS} if a.pct_per_usd else {})
    old = load(BUDGET, {})
    if old.get("ratio_samples"):  # keep calibration across budgets
        b["ratio_samples"] = old["ratio_samples"]
    if a.now is not None:
        b["last"][window] = {"pct": a.now, "resets_at": None, "at": now(), "meter_usd": meter_usd(), "source": "manual"}
    account(b)
    deadline = parse_deadline(a.deadline)
    if b["mode"] == "exhaust" and a.stop_at_reset:
        resets = (b["last"].get(window) or {}).get("resets_at")
        deadline = min(x for x in (deadline, resets) if x) if (deadline or resets) else None
    b["deadline"] = deadline
    LIMIT.unlink(missing_ok=True)
    save(BUDGET, b)
    print(status_line(b))
    return 0


def cmd_check(a) -> int:
    b = load(BUDGET, None)
    if not b:
        print(json.dumps({"action": "go", "fits": len(a.kinds), "reason": "no budget set"}))
        return EXIT_GO
    d = decide(b, a.kinds)
    save(BUDGET, b)
    if d.get("wait_until"):
        d["wait_until_local"] = hhmm(d["wait_until"])
    print(json.dumps(d))
    return {"go": EXIT_GO, "wait": EXIT_WAIT, "stop": EXIT_STOP}[d["action"]]


def cmd_record(a) -> int:
    DIR.mkdir(exist_ok=True)
    with COSTS.open("a") as fh:
        fh.write(json.dumps({"at": now(), "usd": a.usd, "kind": a.kind, "step": a.step}) + "\n")
    return 0


def cmd_limit(a) -> int:
    save(LIMIT, {"at": now(), "reason": a.reason, "window": a.window, "resets_at": a.resets_at})
    return 0


def cmd_ingest(a) -> int:
    """Pass a stream-json stream through, recording cost and limit signals.

    Recognised events (https://code.claude.com/docs/en/headless.md):
      {"type":"system","subtype":"api_retry","error":"rate_limit",...}  -> limit-hit
      {"type":"result","total_cost_usd":X,...}                         -> record-cost
      {"type":"rate_limit_event",...}  shape [to be validated]          -> usage.json, when it has a percentage
    """
    for line in sys.stdin:
        sys.stdout.write(line)
        sys.stdout.flush()
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        typ = ev.get("type")
        if typ == "result" and ev.get("total_cost_usd") is not None:
            cmd_record(argparse.Namespace(usd=float(ev["total_cost_usd"]), kind=a.kind, step=a.step))
        elif typ == "system" and ev.get("subtype") == "api_retry" and ev.get("error") == "rate_limit":
            # A server throttle also retries; only count it when retries are exhausted or a reset is given.
            if ev.get("attempt", 0) >= ev.get("max_retries", 99) or ev.get("resets_at"):
                cmd_limit(argparse.Namespace(reason="rate_limit", window=ev.get("window"), resets_at=ev.get("resets_at")))
        elif typ == "rate_limit_event":
            info = ev.get("rate_limit_info") or ev
            pct = info.get("utilization", info.get("used_percentage"))
            win = {"five_hour": "five_hour", "seven_day": "seven_day"}.get(info.get("rateLimitType") or info.get("window"))
            if pct is not None and win:
                pct = float(pct) * (100 if float(pct) <= 1 else 1)
                usage = load(USAGE, {})
                usage.update({"at": now(), win: {"used_percentage": pct, "resets_at": info.get("resetsAt") or info.get("resets_at")}})
                save(USAGE, usage)
            if info.get("status") == "rejected":
                cmd_limit(argparse.Namespace(reason="rate_limit", window=win, resets_at=info.get("resetsAt")))
    return 0


def status_line(b: dict | None) -> str:
    if not b:
        return "budget=none"
    r = reading(b, b["window"])
    src = r["source"] if r else "none"
    pct = f"{r['pct']:.0f}%" if r else "?"
    dl = f"  until {hhmm(b['deadline'])}" if b.get("deadline") else ""
    win = "7d" if b["window"] == "seven_day" else "5h"
    if b["mode"] == "points":
        return f"budget={b.get('consumed', 0):.1f}/{b['points']:.0f}pt {win} ({src}, window {pct}){dl}"
    return f"budget=until-exhausted {win} ({src}, window {pct}){dl}"


def cmd_status(a) -> int:
    b = load(BUDGET, None)
    if b:
        account(b)
        save(BUDGET, b)
    print(status_line(b))
    return 0


def cmd_off(a) -> int:
    BUDGET.unlink(missing_ok=True)
    print("budget=none")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--weekly", type=float, help="points of the weekly window to use")
    s.add_argument("--five-hour", type=float, help="points of the five-hour window to use")
    s.add_argument("--until-exhausted", action="store_true")
    s.add_argument("--window", choices=WINDOWS, default=None, help="window to exhaust (default five_hour)")
    s.add_argument("--no-stop-at-reset", dest="stop_at_reset", action="store_false")
    s.add_argument("--deadline")
    s.add_argument("--now", type=float, help="current used %% of the window, read from /usage")
    s.add_argument("--pct-per-usd", type=float, help="prior ratio before calibration")
    s.add_argument("--margin", type=float, default=2.0)
    s.set_defaults(fn=cmd_start)
    c = sub.add_parser("check")
    c.add_argument("--kinds", type=lambda x: [k for k in x.split(",") if k], default=["tick"])
    c.set_defaults(fn=cmd_check)
    r = sub.add_parser("record-cost")
    r.add_argument("--usd", type=float, required=True)
    r.add_argument("--kind", default="tick")
    r.add_argument("--step")
    r.set_defaults(fn=cmd_record)
    lh = sub.add_parser("limit-hit")
    lh.add_argument("--reason", default="rate_limit")
    lh.add_argument("--window", choices=WINDOWS)
    lh.add_argument("--resets-at", type=float)
    lh.set_defaults(fn=cmd_limit)
    i = sub.add_parser("ingest-stream")
    i.add_argument("--kind", default="tick")
    i.add_argument("--step")
    i.set_defaults(fn=cmd_ingest)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("off").set_defaults(fn=cmd_off)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
