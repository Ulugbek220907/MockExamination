"""
Accounts: profiles, roles, the monthly plan, and which tests a user may open.

Roles: student (everyone), examiner (marks paid checks), admin (emails listed
in ADMIN_EMAILS). The plan is a list of subscription periods; a user has the
plan while now falls inside any period.

Free tests: every test whose `access` is "free" (by default the first test of
each module). Everything else needs the plan. Admins and examiners can open
every test.
"""

import datetime
import os
import threading

from .db import iso, now, parse_time

ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
_plan_lock = threading.Lock()


def profile_role(profile):
    if profile and profile.get("email", "").lower() in ADMIN_EMAILS:
        return "admin"
    return (profile or {}).get("role") or "student"


def upsert_profile(db, identity):
    """Find or create the profile for a verified identity {id, email, name}."""
    email = identity["email"].lower()
    rows = db.select("profiles", {"email": email}, limit=1)
    stamp = iso(now())
    if rows:
        profile = rows[0]
        values = {"last_login_at": stamp}
        if identity.get("name") and not profile.get("name"):
            values["name"] = identity["name"][:80]
        updated = db.update("profiles", {"id": profile["id"]}, values)
        profile = updated[0] if updated else profile
    else:
        profile = db.insert("profiles", {
            "id": identity["id"], "email": email, "name": (identity.get("name") or "")[:80] or None,
            "role": "student", "last_login_at": stamp,
        }, ignore_conflict=True) or db.select("profiles", {"email": email}, limit=1)[0]
    role = profile_role(profile)
    if role != profile.get("role"):
        db.update("profiles", {"id": profile["id"]}, {"role": role})
        profile["role"] = role
    return profile


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
# The monthly plan
# --------------------------------------------------------------------------

def plan_status(db, user_id, at=None):
    at = at or now()
    periods = db.select("subscription_periods", {"user_id": user_id}, order=[("ends_at", "desc")], limit=50)
    active = any(parse_time(p["starts_at"]) <= at < parse_time(p["ends_at"]) for p in periods)
    ends = max((parse_time(p["ends_at"]) for p in periods), default=None)
    return {
        "active": active,
        "endsAt": iso(ends) if ends and ends > at else None,
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
            return db.insert("subscription_periods", row, ignore_conflict="order_id") or \
                db.select("subscription_periods", {"order_id": order_id}, limit=1)[0]
        return db.insert("subscription_periods", row)


def revoke_plan_period(db, order_id):
    """Remove the plan time bought by a refunded order."""
    return db.delete("subscription_periods", {"order_id": order_id})


# --------------------------------------------------------------------------
# Access to tests
# --------------------------------------------------------------------------

def test_access(test):
    return test.get("access") or ("free" if test.get("sortOrder", 1) <= 1 else "premium")


def can_open_test(test, profile, plan):
    if test_access(test) == "free":
        return True
    if not profile:
        return False
    if profile_role(profile) in ("admin", "examiner"):
        return True
    return bool(plan and plan.get("active"))
