"""
Examiner marketplace: examiner profiles, paid checks, marking and reviews.

A student who has submitted a Writing (or Speaking) test chooses an examiner
and pays for a check. When the payment arrives a check is created in that
examiner's queue. The examiner marks it on the four public criteria and writes
feedback; the student then sees the result and may rate the examiner once.
"""

from . import writing
from .db import iso, now

WRITING_CRITERIA = ("task", "coherence_cohesion", "lexical_resource", "grammar")
SPEAKING_CRITERIA = ("fluency_coherence", "lexical_resource", "grammar", "pronunciation")
SPEAKING_LABELS = {
    "fluency_coherence": "Fluency and Coherence",
    "lexical_resource": "Lexical Resource",
    "grammar": "Grammatical Range and Accuracy",
    "pronunciation": "Pronunciation",
}
MAX_TEXT = 4000


class CheckError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# --------------------------------------------------------------------------
# Examiners
# --------------------------------------------------------------------------

def _stats(db):
    """Ratings, completed checks and queue length per examiner."""
    stats = {}
    for c in db.select("checks", {"status": ("in", ["waiting", "in_progress", "completed"])}, limit=10000):
        s = stats.setdefault(c["examiner_id"], {"ratings": [], "done": 0, "queue": 0})
        if c["status"] == "completed":
            s["done"] += 1
            if c.get("rating"):
                s["ratings"].append(c["rating"])
        else:
            s["queue"] += 1
    return stats


def public_examiner(row, stats=None):
    s = (stats or {}).get(row["user_id"], {"ratings": [], "done": 0, "queue": 0})
    ratings = s["ratings"]
    return {
        "id": row["user_id"],
        "name": row["display_name"],
        "headline": row.get("headline") or "",
        "bio": row.get("bio") or "",
        "doesWriting": bool(row.get("does_writing")),
        "doesSpeaking": bool(row.get("does_speaking")),
        "accepting": bool(row.get("accepting")),
        "approved": bool(row.get("approved")),
        "rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "reviews": len(ratings),
        "checksDone": s["done"],
        "queue": s["queue"],
    }


def list_examiners(db, kind=None, include_hidden=False):
    rows = db.select("examiners", {} if include_hidden else {"approved": True}, limit=500)
    stats = _stats(db)
    out = []
    for row in rows:
        if kind == "writing" and not row.get("does_writing"):
            continue
        if kind == "speaking" and not row.get("does_speaking"):
            continue
        if not include_hidden and not row.get("accepting"):
            continue
        out.append(public_examiner(row, stats))
    # Best rated first, then the most experienced.
    out.sort(key=lambda e: (-(e["rating"] or 0), -e["checksDone"], e["name"].lower()))
    return out


def get_examiner(db, user_id):
    rows = db.select("examiners", {"user_id": user_id}, limit=1)
    return rows[0] if rows else None


def examiner_reviews(db, examiner_id, limit=20):
    rows = db.select("checks", {"examiner_id": examiner_id, "status": "completed"},
                     order=[("completed_at", "desc")], limit=200)
    return [{"rating": r["rating"], "review": r.get("review") or "", "date": r.get("reviewed_at")}
            for r in rows if r.get("rating")][:limit]


def save_examiner(db, user_id, fields, admin=False):
    """Create or update an examiner profile. Only admins can approve."""
    allowed = {"display_name", "headline", "bio", "does_writing", "does_speaking", "accepting"}
    if admin:
        allowed.add("approved")
    values = {}
    for k in allowed:
        if k in fields:
            v = fields[k]
            if k in ("display_name", "headline", "bio"):
                v = str(v or "").strip()[: (80 if k != "bio" else 1200)]
            else:
                v = bool(v)
            values[k] = v
    if "display_name" in values and not values["display_name"]:
        raise CheckError("Please enter the name students will see.")
    existing = get_examiner(db, user_id)
    if existing:
        if values:
            rows = db.update("examiners", {"user_id": user_id}, values)
            return rows[0] if rows else existing
        return existing
    if not values.get("display_name"):
        raise CheckError("Please enter the name students will see.")
    row = {"user_id": user_id, "does_writing": True, "does_speaking": True, "accepting": True, "approved": False}
    row.update(values)
    return db.insert("examiners", row)


# --------------------------------------------------------------------------
# Creating and cancelling checks (called by billing)
# --------------------------------------------------------------------------

def _submission(db, kind, submission_id):
    table = "writing_submissions" if kind == "writing" else "speaking_submissions"
    try:
        sid = int(submission_id)
    except (TypeError, ValueError):
        return None
    rows = db.select(table, {"id": sid}, limit=1)
    return rows[0] if rows else None


def validate_new_check(db, user_id, kind, examiner_id, submission_id):
    examiner = get_examiner(db, examiner_id) if examiner_id else None
    if not examiner or not examiner.get("approved") or not examiner.get("accepting"):
        raise CheckError("This examiner is not taking new checks. Please choose another examiner.")
    if not examiner.get("does_writing" if kind == "writing" else "does_speaking"):
        raise CheckError(f"This examiner does not mark {kind}.")
    if examiner_id == user_id:
        raise CheckError("You cannot mark your own work.")
    sub = _submission(db, kind, submission_id)
    if not sub or sub.get("user_id") != user_id:
        raise CheckError("We could not find this submission in your account. Sign in before you submit a test.", 404)
    if kind == "speaking":
        if sub.get("status") != "completed":
            raise CheckError("Finish the Speaking test first.")
        if sub.get("recordings_deleted_at") or not db.select("recordings", {"submission_id": sub["id"]}, limit=1):
            raise CheckError("This Speaking test has no recordings to mark.")
    return examiner, sub


def create_check(db, order):
    kind = "writing" if order["kind"] == "writing_check" else "speaking"
    existing = db.select("checks", {"order_id": order["id"]}, limit=1)
    if existing:
        return existing[0]
    return db.insert("checks", {
        "order_id": order["id"], "kind": kind, "student_id": order["user_id"],
        "examiner_id": order["examiner_id"], "submission_id": order["submission_id"], "status": "waiting",
    }, ignore_conflict="order_id") or db.select("checks", {"order_id": order["id"]}, limit=1)[0]


def check_can_be_cancelled(db, order_id):
    rows = db.select("checks", {"order_id": order_id}, limit=1)
    return not rows or rows[0]["status"] in ("waiting", "cancelled")


def cancel_check_for_order(db, order_id):
    db.update("checks", {"order_id": order_id, "status": "waiting"}, {"status": "cancelled"})


# --------------------------------------------------------------------------
# Reading checks
# --------------------------------------------------------------------------

def get_check(db, check_id):
    try:
        rows = db.select("checks", {"id": int(check_id)}, limit=1)
    except (TypeError, ValueError):
        return None
    return rows[0] if rows else None


def public_check(check, examiner=None, include_result=True):
    out = {
        "id": check["id"],
        "kind": check["kind"],
        "status": check["status"],
        "submissionId": check["submission_id"],
        "examinerId": check["examiner_id"],
        "examinerName": (examiner or {}).get("display_name"),
        "overallBand": float(check["overall_band"]) if check.get("overall_band") is not None else None,
        "createdAt": check.get("created_at"),
        "completedAt": check.get("completed_at"),
        "rating": check.get("rating"),
        "review": check.get("review"),
    }
    if include_result and check["status"] == "completed":
        out["result"] = check.get("result")
    return out


def checks_for_student(db, student_id):
    rows = db.select("checks", {"student_id": student_id}, order=[("created_at", "desc")], limit=100)
    names = {e["user_id"]: e for e in db.select("examiners", {"user_id": ("in", list({r["examiner_id"] for r in rows}))})} if rows else {}
    return [public_check(r, names.get(r["examiner_id"]), include_result=False) for r in rows]


def checks_for_examiner(db, examiner_id):
    rows = db.select("checks", {"examiner_id": examiner_id, "status": ("in", ["waiting", "in_progress", "completed"])},
                     order=[("created_at", "asc")], limit=300)
    return [public_check(r, include_result=False) for r in rows]


# --------------------------------------------------------------------------
# Marking
# --------------------------------------------------------------------------

def _band(value):
    try:
        band = int(value)
    except (TypeError, ValueError):
        raise CheckError("Each criterion needs a whole band from 0 to 9.")
    if not 0 <= band <= 9:
        raise CheckError("Each criterion needs a whole band from 0 to 9.")
    return band


def _text(value, limit=MAX_TEXT):
    return str(value or "").strip()[:limit]


def _lines(value, limit=12):
    if isinstance(value, str):
        value = value.splitlines()
    return [_text(v, 600) for v in (value or []) if _text(v, 600)][:limit]


def _criteria(raw, keys, labels):
    out = {}
    for key in keys:
        item = (raw or {}).get(key) or {}
        out[key] = {"label": labels[key], "band": _band(item.get("band")), "feedback": _text(item.get("feedback"), 1500)}
    return out


def normalise_writing_result(raw):
    tasks = {}
    for n in (1, 2):
        t = ((raw or {}).get("tasks") or {}).get(str(n)) or {}
        criteria = _criteria(t.get("criteria"), WRITING_CRITERIA, writing.CRITERION_LABELS[n])
        corrections = []
        for c in (t.get("corrections") or [])[:20]:
            if _text(c.get("original")) and _text(c.get("corrected")):
                corrections.append({"original": _text(c.get("original"), 300), "corrected": _text(c.get("corrected"), 300),
                                    "explanation": _text(c.get("explanation"), 400)})
        tasks[str(n)] = {
            "band": writing.task_band(criteria),
            "criteria": criteria,
            "summary": _text(t.get("summary"), 1500),
            "strengths": _lines(t.get("strengths")),
            "improvements": _lines(t.get("improvements")),
            "corrections": corrections,
        }
    overall = writing.overall_writing_band(tasks["1"]["band"], tasks["2"]["band"])
    return {"tasks": tasks, "overallBand": overall, "comment": _text((raw or {}).get("comment"))}


def normalise_speaking_result(raw):
    criteria = _criteria((raw or {}).get("criteria"), SPEAKING_CRITERIA, SPEAKING_LABELS)
    band = writing.round_to_half_band(sum(c["band"] for c in criteria.values()) / 4)
    return {
        "criteria": criteria,
        "overallBand": band,
        "summary": _text((raw or {}).get("summary"), 1500),
        "strengths": _lines((raw or {}).get("strengths")),
        "improvements": _lines((raw or {}).get("improvements")),
        "comment": _text((raw or {}).get("comment")),
    }


def start_check(db, check, examiner_id):
    if check["examiner_id"] != examiner_id:
        raise CheckError("Check not found.", 404)
    if check["status"] == "waiting":
        rows = db.update("checks", {"id": check["id"], "status": "waiting"}, {"status": "in_progress", "started_at": iso(now())})
        return rows[0] if rows else get_check(db, check["id"])
    return check


def submit_result(db, check, examiner_id, raw):
    if check["examiner_id"] != examiner_id:
        raise CheckError("Check not found.", 404)
    if check["status"] not in ("waiting", "in_progress"):
        raise CheckError("This check is already finished.")
    result = normalise_writing_result(raw) if check["kind"] == "writing" else normalise_speaking_result(raw)
    rows = db.update("checks", {"id": check["id"], "status": ("in", ["waiting", "in_progress"])}, {
        "status": "completed", "result": result, "overall_band": result["overallBand"], "completed_at": iso(now()),
    })
    if not rows:
        raise CheckError("This check is already finished.")
    return rows[0]


def rate_check(db, check, student_id, rating, review):
    if check["student_id"] != student_id:
        raise CheckError("Check not found.", 404)
    if check["status"] != "completed":
        raise CheckError("You can rate the examiner after the check is finished.")
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        raise CheckError("Choose from 1 to 5 stars.")
    if not 1 <= rating <= 5:
        raise CheckError("Choose from 1 to 5 stars.")
    rows = db.update("checks", {"id": check["id"], "rating": None},
                     {"rating": rating, "review": _text(review, 1000) or None, "reviewed_at": iso(now())})
    if not rows:
        raise CheckError("You have already reviewed this check.")
    return rows[0]
