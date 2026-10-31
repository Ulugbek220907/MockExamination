"""
Accounts: profiles, roles, the monthly plan, and which tests a user may open.

Roles: student (everyone), examiner (marks paid checks), admin (emails listed
in ADMIN_EMAILS). The plan is a list of subscription periods; a user has the
plan while now falls inside any period.

Free tests: every test whose `access` is "free" (by default the first test of
each module). Everything else needs the plan. Admins and examiners can open
every test.
"""

import concurrent.futures
import datetime
import logging
import os
import threading

from .db import iso, now, parse_time

log = logging.getLogger("mockexam.accounts")

ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
_plan_lock = threading.Lock()

# Called with a user id whenever that user's plan changes (the server forgets its cached plan).
PLAN_LISTENERS = []


def _plan_changed(user_id):
    for listener in PLAN_LISTENERS:
        listener(user_id)


def profile_role(profile):
    if profile and profile.get("email", "").lower() in ADMIN_EMAILS:
        return "admin"
    return (profile or {}).get("role") or "student"


_MISSING = object()


def upsert_profile(db, identity, existing=_MISSING):
    """
    Find or create the profile for a verified identity {id, email, name}. `existing` is the
    profile row found by email (or None) when the caller has already looked it up.
    """
    email = identity["email"].lower()
    rows = db.select("profiles", {"email": email}, limit=1) if existing is _MISSING else ([existing] if existing else [])
    stamp = iso(now())
    if rows:
        profile = dict(rows[0])
        if identity.get("name") and not profile.get("name"):
            profile["name"] = identity["name"][:80]
            db.update("profiles", {"id": profile["id"]}, {"last_login_at": stamp, "name": profile["name"]})
        else:
            # Nothing on a page shows the last sign-in, so it is written after the answer has gone.
            _later(lambda: db.update("profiles", {"id": profile["id"]}, {"last_login_at": stamp}, invalidate=False))
    else:
        created = db.insert("profiles", {
            "id": identity["id"], "email": email, "name": (identity.get("name") or "")[:80] or None,
            "role": "student", "last_login_at": stamp,
        }, ignore_conflict=True)
        profile = created or db.select("profiles", {"email": email}, limit=1)[0]
        if created:
            profile["created_now"] = True  # the first sign-in (for the signup event); not stored
    role = profile_role(profile)
    if role != profile.get("role"):
        db.update("profiles", {"id": profile["id"]}, {"role": role})
        profile["role"] = role
    return profile


_BACKGROUND = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="accounts")


def _later(job):
    """Run a write nobody waits for; a failure is logged, never shown."""
    def run():
        try:
            job()
        except Exception:
            log.exception("Background account write failed")
    _BACKGROUND.submit(run)


def get_profile(db, user_id):
    rows = db.select("profiles", {"id": user_id}, limit=1)
    if not rows:
        return None
    profile = rows[0]
    profile["role"] = profile_role(profile)
    return profile


def find_profile_by_email(db, email):
    rows = db.select("profiles", {"email": email.strip().lower()}, limit=1)
    return rows[0] if rows else None


# --------------------------------------------------------------------------
# Study goal: the band a student aims for and the day of their exam
# --------------------------------------------------------------------------

class GoalError(ValueError):
    status = 400


def clean_goal(body, today=None):
    """
    The goal fields present in `body`, ready to store: {"target_band": 7.0, "exam_date": "2026-12-05"}.
    An empty value clears a field. Raises GoalError with a message for the student.
    """
    out = {}
    if "targetBand" in body:
        raw = body.get("targetBand")
        if raw in (None, ""):
            out["target_band"] = None
        else:
            try:
                band = float(raw)
            except (TypeError, ValueError):
                raise GoalError("Choose a band between 4.0 and 9.0.")
            if not 4 <= band <= 9 or band * 2 != int(band * 2):
                raise GoalError("Choose a band between 4.0 and 9.0.")
            out["target_band"] = band
    if "examDate" in body:
        raw = str(body.get("examDate") or "").strip()
        if not raw:
            out["exam_date"] = None
        else:
            try:
                day = datetime.date.fromisoformat(raw[:10])
            except ValueError:
                raise GoalError("Enter the date of your exam.")
            today = today or now().date()
            if day < today or day > today + datetime.timedelta(days=730):
                raise GoalError("Enter an exam date between today and two years from now.")
            out["exam_date"] = day.isoformat()
    return out


def public_goal(profile):
    band = (profile or {}).get("target_band")
    day = (profile or {}).get("exam_date")
    return {"targetBand": float(band) if band is not None else None, "examDate": str(day)[:10] if day else None}


# --------------------------------------------------------------------------
# The monthly plan
# --------------------------------------------------------------------------

def plan_status(db, user_id, at=None):
    at = at or now()
    periods = db.select("subscription_periods", {"user_id": user_id}, order=[("ends_at", "desc")], limit=50)
    active = any(parse_time(p["starts_at"]) <= at < parse_time(p["ends_at"]) for p in periods)
    ends = max((parse_time(p["ends_at"]) for p in periods), default=None)
    return {
        "active": active,
        "endsAt": iso(ends) if active and ends and ends > at else None,
        "hadPlan": bool(periods),
        "hadPaidPlan": any(p["source"] == "payment" for p in periods),
    }


def grant_plan_period(db, user_id, days, source, order_id=None, note=None):
    """
    Add `days` of plan to a user, starting when their current plan ends (or now).
    Idempotent per order: a second call for the same order_id changes nothing.
    """
    with _plan_lock:
        if order_id is not None:
            existing = db.select("subscription_periods", {"order_id": order_id}, limit=1)
            if existing:
                return existing[0]
        current = now()
        periods = db.select("subscription_periods", {"user_id": user_id}, order=[("ends_at", "desc")], limit=1)
        start = max(current, parse_time(periods[0]["ends_at"])) if periods else current
        end = start + datetime.timedelta(days=days)
        row = {"user_id": user_id, "starts_at": iso(start), "ends_at": iso(end), "source": source, "note": note}
        if order_id is not None:
            row["order_id"] = order_id
            period = db.insert("subscription_periods", row, ignore_conflict="order_id") or \
                db.select("subscription_periods", {"order_id": order_id}, limit=1)[0]
        else:
            period = db.insert("subscription_periods", row)
    _plan_changed(user_id)
    return period


def revoke_plan_period(db, order_id):
    """
    Remove the plan time bought by a refunded order. Time queued after it (a month bought
    while this one was running) moves up to fill the unused part, so no paid day is lost
    and there is no gap without the plan. Safe to repeat.
    """
    with _plan_lock:
        rows = db.select("subscription_periods", {"order_id": order_id}, limit=1)
        if not rows:
            return None
        gone = rows[0]
        db.delete("subscription_periods", {"order_id": order_id})
        start, end = parse_time(gone["starts_at"]), parse_time(gone["ends_at"])
        unused = end - max(start, now())
        if unused.total_seconds() > 0:
            for p in db.select("subscription_periods", {"user_id": gone["user_id"]}, order=[("starts_at", "asc")], limit=50):
                if parse_time(p["starts_at"]) >= end:  # queued after the refunded period
                    db.update("subscription_periods", {"id": p["id"]}, {
                        "starts_at": iso(parse_time(p["starts_at"]) - unused),
                        "ends_at": iso(parse_time(p["ends_at"]) - unused),
                    })
    _plan_changed(gone["user_id"])
    return gone


def pass_counts(db, at=None):
    """Students with the pass now, and how many of them lose it within 7 days (no later month bought)."""
    at = at or now()
    rows = db.select("subscription_periods", {"ends_at": ("gt", iso(at))}, limit=10000)
    active, last_end = set(), {}
    for p in rows:
        ends = parse_time(p["ends_at"])
        if parse_time(p["starts_at"]) <= at:
            active.add(p["user_id"])
        last_end[p["user_id"]] = max(ends, last_end.get(p["user_id"], ends))
    week = at + datetime.timedelta(days=7)
    return {"active": len(active), "endingIn7Days": sum(1 for u in active if last_end[u] <= week)}


REMIND_DAYS = 3


def send_plan_reminders(db, send, at=None):
    """
    Tell each student once when their pass ends within REMIND_DAYS days and no
    later month is already bought. `send(db, user_id, ends_at)` sends the message.
    Returns how many were sent. Safe to run as often as you like.
    """
    at = at or now()
    soon = at + datetime.timedelta(days=REMIND_DAYS)
    rows = db.select("subscription_periods", {"ends_at": ("gt", iso(at)), "reminded_at": None},
                     order=[("ends_at", "asc")], limit=200)
    sent = 0
    for p in rows:
        ends = parse_time(p["ends_at"])
        if ends > soon:
            break  # the rest end later
        if parse_time(p["starts_at"]) > at:
            continue  # a month queued after the current one: its turn comes later
        db.update("subscription_periods", {"id": p["id"]}, {"reminded_at": iso(at)})
        later = db.select("subscription_periods", {"user_id": p["user_id"], "ends_at": ("gt", p["ends_at"])}, limit=1)
        if later:
            continue  # already renewed
        send(db, p["user_id"], p["ends_at"])
        sent += 1
    return sent


# --------------------------------------------------------------------------
# Access to tests
# --------------------------------------------------------------------------

# The first tests of every module are free; the others need the pass. While nothing is for sale
# (COMMERCE_ENABLED is off, the launch setting) a test that needs the pass is "soon": shown blurred as
# "Coming soon…", refused to everyone except admins and examiners, who can still preview it.
FREE_TESTS_PER_MODULE = 5


def commerce_enabled():
    """True once the site sells the pass and examiner checks. Read each time so a restart is not needed in tests."""
    return os.environ.get("COMMERCE_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


def declared_access(test):
    """What the test file says: "free" or "premium" (a test may also say "soon" outright)."""
    return test.get("access") or ("free" if test.get("sortOrder", 1) <= FREE_TESTS_PER_MODULE else "premium")


def test_access(test):
    """free, premium (needs the pass) or soon (not open yet). The pass tests are "soon" while commerce is off."""
    access = declared_access(test)
    return "soon" if access == "premium" and not commerce_enabled() else access


def can_open_test(test, profile, plan):
    access = test_access(test)
    if access == "free":
        return True
    if not profile:
        return False
    if profile_role(profile) in ("admin", "examiner"):
        return True
    return access == "premium" and bool(plan and plan.get("active"))
