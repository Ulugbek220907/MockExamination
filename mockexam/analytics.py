"""
First-party funnel analytics and in-app feedback. No third-party scripts, no cookies of
their own, and nothing personal: events carry the browser's anonymous client id (the one
the history list already uses) and, when signed in, the user id. Feedback may include an
email address if the student chooses to give one.

The funnel:  visit → signup → free_test_started → test_finished → paid

Browsers report `visit`, `free_test_started` and `cta_click` (POST /api/events). The server
records `signup` (first sign-in), `test_finished` (every submitted test) and `paid` (an
order fulfilled), so those cannot be faked from a browser.

Repeats are dropped with a `dedupe_key` (unique, NULL when repeats are wanted): one visit
per browser per day, one signup per user, one paid per order, one free_test_started per
browser, test and day.
"""

import datetime
import logging
import re

from .db import iso, now

log = logging.getLogger("mockexam.analytics")

CLIENT_EVENTS = {"visit", "free_test_started", "cta_click"}
SERVER_EVENTS = {"signup", "test_finished", "paid"}
FUNNEL = ("visit", "signup", "free_test_started", "test_finished", "paid")
MODULES = {"reading", "listening", "writing", "speaking"}

# Days follow Tashkent time (UTC+5, no daylight saving), so "once a day" matches the students' day.
TASHKENT = datetime.timezone(datetime.timedelta(hours=5))
DETAIL_RE = re.compile(r"^[a-z0-9_]{1,40}$")
TEST_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class AnalyticsError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def today():
    return now().astimezone(TASHKENT).date().isoformat()


def _dedupe_key(name, client_id, user_id, test_id, order_id):
    if name == "visit" and client_id:
        return f"visit:{client_id}:{today()}"
    if name == "signup" and user_id:
        return f"signup:{user_id}"
    if name == "paid" and order_id:
        return f"paid:{order_id}"
    if name == "free_test_started" and client_id and test_id:
        return f"free:{client_id}:{test_id}:{today()}"
    return None


def record(db, name, client_id=None, user_id=None, module=None, test_id=None, detail=None, order_id=None):
    """Store one event. Never raises: analytics must not break the request it rides on."""
    try:
        row = {
            "name": name, "client_id": client_id, "user_id": user_id,
            "module": module if module in MODULES else None,
            "test_id": test_id if test_id and TEST_ID_RE.match(str(test_id)) else None,
            "detail": detail if detail and DETAIL_RE.match(str(detail)) else None,
            "day": today(),
        }
        key = _dedupe_key(name, client_id, user_id, row["test_id"], order_id)
        if key:
            row["dedupe_key"] = key
            return db.insert("product_events", row, ignore_conflict="dedupe_key")
        return db.insert("product_events", row)
    except Exception:  # noqa: BLE001 – a lost event is better than a failed page
        log.warning("Could not record the %s event", name, exc_info=True)
        return None


def client_event(body):
    """Check an event a browser sent (POST /api/events). Returns the fields for record()."""
    if not isinstance(body, dict):
        raise AnalyticsError("Expected a JSON object.")
    name = body.get("name")
    if name not in CLIENT_EVENTS:
        raise AnalyticsError("Unknown event.")
    module = body.get("module")
    if module is not None and module not in MODULES:
        raise AnalyticsError("Unknown module.")
    test_id = body.get("testId")
    if test_id is not None and not (isinstance(test_id, str) and TEST_ID_RE.match(test_id)):
        raise AnalyticsError("Bad test id.")
    detail = body.get("detail")
    if detail is not None and not (isinstance(detail, str) and DETAIL_RE.match(detail)):
        raise AnalyticsError("Bad detail.")
    if name == "free_test_started" and not test_id:
        raise AnalyticsError("A started test needs its test id.")
    if name == "cta_click" and not detail:
        raise AnalyticsError("A click needs to say what was clicked.")
    return {"name": name, "module": module, "test_id": test_id, "detail": detail}


def funnel(db, days):
    """Event counts for the last `days` days, in funnel order (deduplicated as described above)."""
    since = iso(now() - datetime.timedelta(days=days))
    return {name: db.count("product_events", {"name": name, "created_at": ("gte", since)}) for name in FUNNEL}


# --------------------------------------------------------------------------
# Feedback
# --------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,24}$")
PAGE_RE = re.compile(r"^#/[\w\-/?=&.]{0,78}$")


def clean_feedback(body):
    """The fields of a feedback message, checked. Raises AnalyticsError with a message for the student."""
    if not isinstance(body, dict):
        raise AnalyticsError("Expected a JSON object.")
    message = str(body.get("message") or "").strip()
    if not message:
        raise AnalyticsError("Please write a message.")
    if len(message) > 2000:
        raise AnalyticsError("Please keep the message under 2000 characters.")
    rating = body.get("rating")
    if rating in ("", None):
        rating = None
    elif not (isinstance(rating, int) and not isinstance(rating, bool) and 1 <= rating <= 5):
        raise AnalyticsError("The rating must be from 1 to 5.")
    email = str(body.get("email") or "").strip().lower() or None
    if email and not EMAIL_RE.match(email):
        raise AnalyticsError("Please check the email address, or leave it empty.")
    page = str(body.get("page") or "").strip() or None
    if page and not PAGE_RE.match(page):
        page = None
    return {"message": message, "rating": rating, "email": email, "page": page}


def public_feedback(row):
    return {"id": row["id"], "message": row["message"], "rating": row.get("rating"), "email": row.get("email"),
            "page": row.get("page"), "signedIn": bool(row.get("user_id")), "createdAt": row.get("created_at")}
