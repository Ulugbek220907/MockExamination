"""
How much AI marking each person gets. The allowances live here, in one place, so the passes stay priced for them.
docs/COSTS.md has the sums behind the numbers.

                                 Writing scripts                 Speaking tests
  a pass that covers the paper   30 in any 30 days, 3 a day      30 in any 30 days, 3 a day
  a free account                 1, once                         1, once
  an admin or an examiner        no personal limit

A Writing "script" is Task 1 and Task 2 marked together; a Speaking "test" is every answer listened to and rated.
A free account's one marking is for good: it does not come back the next month. Each number can be changed with the
environment variable named next to it below. On top of the personal allowances:

  - all free accounts together get AI_FREE_WRITING_PER_DAY scripts and AI_FREE_SPEAKING_PER_DAY tests a day, so a flood
    of new accounts cannot spend the AI budget. Counted in memory: a restart starts the count again, which is fine for
    a safety net;
  - one person spends at most a set amount on AI per paper in any 30 days, counted from what the AI service reported
    for each job (AI_COST_CAP_*): a net under the counts, for unusually long scripts or recordings;
  - one person has one Writing script with the AI examiner at a time (a second tab sending the same essay is refused);
  - the site-wide day caps stay (AI_DAILY_LIMIT and AI_PER_IP_PER_HOUR in server.py, SPEAKING_AI_DAILY_LIMIT).

Every refusal comes with a code, so the page can offer the pass where that helps:
  free_used    a free account has used its one marking (the page offers the pass)
  day_used     today's allowance is used
  month_used   the 30-day allowance is used
  cost_used    the 30-day spending net was reached
  busy         all free accounts together have used today's AI, or the person's previous script is still being marked
"""

import datetime
import logging
import os
import threading

from . import accounts
from .db import iso, now, parse_time

log = logging.getLogger("mockexam.ai_usage")


def _int_env(name, default):
    try:
        return max(0, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


def _money_env(name, default):
    try:
        return max(0.0, float(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


MODULES = ("writing", "speaking")

# {module: {"pass": (per 30 days, per day), "free": (ever, None)}}.
def _limits():
    return {
        "writing": {
            "pass": (_int_env("WRITING_AI_PER_MONTH", 30), _int_env("WRITING_AI_PER_DAY", 3)),
            "free": (_int_env("WRITING_AI_FREE_TOTAL", 1), None),
        },
        "speaking": {
            "pass": (_int_env("SPEAKING_AI_PER_MONTH", 30), _int_env("SPEAKING_AI_PER_DAY", 3)),
            "free": (_int_env("SPEAKING_AI_FREE_TOTAL", 1), None),
        },
    }


def _cost_caps():
    """US dollars of AI per person, per paper, in any 30 days."""
    return {
        "writing": {"pass": _money_env("AI_COST_CAP_WRITING_USD", 2.0), "free": _money_env("AI_FREE_COST_CAP_WRITING_USD", 0.3)},
        "speaking": {"pass": _money_env("AI_COST_CAP_SPEAKING_USD", 3.0), "free": _money_env("AI_FREE_COST_CAP_SPEAKING_USD", 0.5)},
    }


def free_per_day():
    return {"writing": _int_env("AI_FREE_WRITING_PER_DAY", 40), "speaking": _int_env("AI_FREE_SPEAKING_PER_DAY", 15)}


def caps():
    """What the pages say: {"pass": {"writing": 30, "speaking": 12}, "free": {...}} (a month = any 30 days)."""
    lim = _limits()
    return {tier: {m: lim[m][tier][0] for m in MODULES} for tier in ("pass", "free")}


def allowances():
    """Every allowance for the pages: {"pass": {"writing": {"month": 30, "day": 3}, ...}, "free": {"writing": {"total": 1}, ...}}."""
    lim = _limits()
    return {"pass": {m: {"month": lim[m]["pass"][0], "day": lim[m]["pass"][1]} for m in MODULES},
            "free": {m: {"total": lim[m]["free"][0]} for m in MODULES}}


class Refused(Exception):
    def __init__(self, message, code, status=429):
        super().__init__(message)
        self.code = code
        self.status = status


def tier_of(profile, plan, module):
    """"staff" (no personal limit), "pass" (a pass that covers the paper) or "free"."""
    if accounts.profile_role(profile) in ("admin", "examiner"):
        return "staff"
    return "pass" if accounts.has_module(plan, module) else "free"


# --------------------------------------------------------------------------
# What a person has used (from the saved submissions)
# --------------------------------------------------------------------------

def job_cost(module, row):
    """US dollars the AI service reported for one saved job, or 0 when it is not known."""
    blob = row.get("assessment") if module == "writing" else row.get("ai_review")
    usage = (blob or {}).get("usage") if isinstance(blob, dict) else None
    try:
        return max(0.0, float((usage or {}).get("cost") or 0))
    except (TypeError, ValueError):
        return 0.0


def _jobs(db, module, user_id, since, limit):
    """This person's AI jobs for the paper since `since`, newest first."""
    if module == "writing":
        rows = db.select("writing_submissions", {"user_id": user_id, "created_at": ("gte", iso(since))},
                         order=[("created_at", "desc")], limit=limit)
        # A script the AI examiner marked (one whose tasks were all blank, copied or too short was never sent).
        return [r for r in rows if r.get("assessment") and
                ((r["assessment"].get("usage") or {}).get("calls", 1) if isinstance(r["assessment"], dict) else 1)]
    return db.select("speaking_submissions", {"user_id": user_id, "mode": "ai", "created_at": ("gte", iso(since))},
                     order=[("created_at", "desc")], limit=limit)


def jobs_ever(db, module, user_id, limit):
    """How many AI jobs for the paper this person has ever had (counted up to `limit`)."""
    if module == "writing":
        rows = db.select("writing_submissions", {"user_id": user_id}, order=[("created_at", "desc")], limit=max(limit, 1) * 5 + 20)
        return min(limit, len([r for r in rows if r.get("assessment") and
                               ((r["assessment"].get("usage") or {}).get("calls", 1) if isinstance(r["assessment"], dict) else 1)]))
    return len(db.select("speaking_submissions", {"user_id": user_id, "mode": "ai"}, limit=limit))


def usage(db, module, user_id, at=None):
    """{"month": jobs in 30 days, "day": jobs in 24 hours, "cost": dollars in 30 days}."""
    at = at or now()
    month_cap, _ = _limits()[module]["pass"]
    jobs = _jobs(db, module, user_id, at - datetime.timedelta(days=30), max(month_cap, 30) * 3 + 50)
    day_start = at - datetime.timedelta(days=1)
    day = sum(1 for r in jobs if (parse_time(r.get("created_at")) or at) >= day_start)
    return {"month": len(jobs), "day": day, "cost": round(sum(job_cost(module, r) for r in jobs), 4)}


# --------------------------------------------------------------------------
# All free accounts together, today (in memory)
# --------------------------------------------------------------------------

class FreeBudget:
    def __init__(self):
        self.lock = threading.Lock()
        self.day = None
        self.used = {m: 0 for m in MODULES}

    def _roll(self):
        today = now().date()
        if today != self.day:
            self.day, self.used = today, {m: 0 for m in MODULES}

    def take(self, module):
        with self.lock:
            self._roll()
            if self.used[module] >= free_per_day()[module]:
                return False
            self.used[module] += 1
            return True

    def give_back(self, module):
        with self.lock:
            self._roll()
            self.used[module] = max(0, self.used[module] - 1)

    def snapshot(self):
        with self.lock:
            self._roll()
            return dict(self.used)


FREE_BUDGET = FreeBudget()


# --------------------------------------------------------------------------
# One Writing script at a time per person (in memory)
# --------------------------------------------------------------------------

class InFlight:
    def __init__(self):
        self.lock = threading.Lock()
        self.busy = set()

    def take(self, key):
        with self.lock:
            if key in self.busy:
                return False
            self.busy.add(key)
            return True

    def release(self, key):
        with self.lock:
            self.busy.discard(key)


IN_FLIGHT = InFlight()


# --------------------------------------------------------------------------
# The check
# --------------------------------------------------------------------------

WHAT = {"writing": ("Writing script", "Writing scripts", "marked"), "speaking": ("Speaking test", "Speaking tests", "rated")}
WITHOUT = {"writing": "Your script is analysed without a band.", "speaking": "This test is recorded without a band."}


def _plural(n, one, many):
    return f"{n} {one if n == 1 else many}"


def check(db, profile, plan, module, at=None):
    """
    Raise Refused when this person may not have another AI job for the paper now; else return the tier
    ("staff", "pass" or "free"). A free job also takes one place from today's free budget: call release(module, tier)
    if the job does not run after all.
    """
    tier = tier_of(profile, plan, module)
    if tier == "staff":
        return tier
    month_cap, day_cap = _limits()[module][tier]
    one, many, done = WHAT[module]
    if tier == "free":
        # One marking for good: whatever this account has had before (on a pass too) counts.
        pass_month = _limits()[module]["pass"][0]
        if jobs_ever(db, module, profile["id"], month_cap + 1) >= month_cap:
            raise Refused(f"Your free account includes {_plural(month_cap, one, many)} {done} by the AI examiner, and "
                          f"you have used {'it' if month_cap == 1 else 'them'}. {WITHOUT[module]} "
                          f"A {module.capitalize()} pass includes {pass_month} a month.", "free_used")
        used = usage(db, module, profile["id"], at)
    else:
        used = usage(db, module, profile["id"], at)
        if used["month"] >= month_cap:
            raise Refused(f"You have had {_plural(month_cap, one, many)} {done} by the AI examiner in the last 30 days, "
                          f"which is what a pass includes. {WITHOUT[module]} Your allowance comes back day by day.",
                          "month_used")
        if used["day"] >= day_cap:
            raise Refused(f"You have had {_plural(day_cap, one, many)} {done} by the AI examiner today. "
                          f"{WITHOUT[module]} The AI examiner is free again tomorrow.", "day_used")
    if used["cost"] >= _cost_caps()[module][tier]:
        log.warning("AI spending net reached: user %s, %s, $%.2f in 30 days", profile["id"], module, used["cost"])
        raise Refused(f"You have used this month's AI marking for {module.capitalize()}. {WITHOUT[module]} "
                      "Your allowance comes back day by day.", "cost_used")
    if tier == "free" and not FREE_BUDGET.take(module):
        log.warning("Free AI budget for %s used up today", module)
        raise Refused("The AI examiner has marked as much as it can for free accounts today. "
                      f"{WITHOUT[module]} Please try again tomorrow.", "busy")
    return tier


def release(module, tier):
    """Give back today's free place when a checked job did not run."""
    if tier == "free":
        FREE_BUDGET.give_back(module)


def summary(db, days=30, at=None):
    """For the admin page: what the AI examiner cost in the last `days`, per paper, with the people who used it most."""
    at = at or now()
    since = iso(at - datetime.timedelta(days=days))
    out, people = {}, {}
    for module, table, where in (("writing", "writing_submissions", {}), ("speaking", "speaking_submissions", {"mode": "ai"})):
        rows = db.select(table, {**where, "created_at": ("gte", since)}, order=[("created_at", "desc")], limit=3000)
        jobs = [r for r in rows if (r.get("assessment") if module == "writing" else r.get("ai_review"))]
        costs = [job_cost(module, r) for r in jobs]
        known = [c for c in costs if c > 0]
        free = sum(1 for r in jobs if ((r.get("assessment") or r.get("ai_review") or {}).get("usage") or {}).get("tier") == "free")
        out[module] = {"jobs": len(jobs), "withCost": len(known), "cost": round(sum(known), 4),
                       "average": round(sum(known) / len(known), 4) if known else None, "free": free}
        for r, c in zip(jobs, costs):
            uid = r.get("user_id")
            if uid:
                p = people.setdefault(uid, {"userId": uid, "writing": 0, "speaking": 0, "cost": 0.0})
                p[module] += 1
                p["cost"] = round(p["cost"] + c, 4)
    top = sorted(people.values(), key=lambda p: (-p["cost"], -(p["writing"] + p["speaking"])))[:15]
    # Recordings kept now (finished tests' recordings are deleted after SPEAKING_KEEP_DAYS): the free database plan
    # holds 1 GB of files, so this is the number that says when to move to a paid plan.
    try:
        recs = db.select("recordings", {"created_at": ("gte", since)}, limit=50000)
        stored_mb = round(sum(int(r.get("size") or 0) for r in recs) / (1024 * 1024), 1)
    except Exception:  # noqa: BLE001 - the page still shows the rest
        stored_mb = None
    return {"days": days, "modules": out, "top": top, "freeToday": FREE_BUDGET.snapshot(), "freePerDay": free_per_day(),
            "allowances": allowances(), "recordingsMB": stored_mb}
