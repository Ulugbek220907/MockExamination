"""
Speaking tests: submissions, recorded answers, who may listen, and clean-up.

A signed-in candidate starts a submission, the browser uploads one recording
per question as the test goes on, and finally marks the submission complete.
The candidate can listen to their answers and order an examiner check; the
examiner (and the site admin) can then play the recordings too.

Audio goes to private file storage (files.py); the `recordings` table keeps
who owns each file and which question it answers. Recordings are deleted
KEEP_DAYS after the test unless an examiner is still marking them.
"""

import datetime
import os
import uuid

from . import content
from .db import iso, now, parse_time

AUDIO_TYPES = {
    "audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/x-m4a": "m4a",
    "audio/aac": "aac", "audio/mpeg": "mp3", "audio/wav": "wav",
}
MAX_RECORDING_BYTES = 4 * 1024 * 1024
MIN_RECORDING_BYTES = 200
MAX_NOTES = 2000


def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


STARTS_PER_DAY = _int_env("SPEAKING_TESTS_PER_DAY", 8)
UPLOAD_BYTES_PER_DAY = _int_env("SPEAKING_UPLOAD_MB_PER_DAY", 80) * 1024 * 1024
KEEP_DAYS = _int_env("SPEAKING_KEEP_DAYS", 60)
ABANDONED_HOURS = 48


class SpeakingError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def base_mime(value):
    return str(value or "").split(";")[0].strip().lower()


def _id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# Submissions
# --------------------------------------------------------------------------

def start_submission(db, user_id, test, candidate_name, mode):
    since = now() - datetime.timedelta(days=1)
    recent = db.select("speaking_submissions", {"user_id": user_id, "created_at": ("gte", iso(since))}, limit=STARTS_PER_DAY + 1)
    if len(recent) >= STARTS_PER_DAY:
        raise SpeakingError(f"You can start {STARTS_PER_DAY} Speaking tests a day. Please come back tomorrow.", 429)
    return db.insert("speaking_submissions", {
        "user_id": user_id, "test_id": test["id"], "candidate_name": candidate_name,
        "mode": "practice" if mode == "practice" else "exam", "status": "recording",
    })


def get_submission(db, submission_id):
    sid = _id(submission_id)
    rows = db.select("speaking_submissions", {"id": sid}, limit=1) if sid is not None else []
    return rows[0] if rows else None


def own_submission(db, submission_id, user_id):
    sub = get_submission(db, submission_id)
    if not sub or sub["user_id"] != user_id:
        raise SpeakingError("Speaking test not found.", 404)
    return sub


def recordings_for(db, submission_id):
    return db.select("recordings", {"submission_id": submission_id}, order=[("created_at", "asc")], limit=100)


def save_recording(db, files, sub, test, key, data, mime, duration):
    """Store one answer. Uploading the same question again replaces the earlier answer."""
    if sub["status"] != "recording":
        raise SpeakingError("This Speaking test is already finished.", 409)
    if key not in {q["key"] for _, q in content.speaking_questions(test)}:
        raise SpeakingError("Unknown question.", 404)
    mime = base_mime(mime)
    if mime not in AUDIO_TYPES:
        raise SpeakingError("This audio format is not supported.", 415)
    if len(data) < MIN_RECORDING_BYTES:
        raise SpeakingError("The recording is empty. Check your microphone.", 400)
    if len(data) > MAX_RECORDING_BYTES:
        raise SpeakingError("The recording is too long.", 413)
    since = iso(now() - datetime.timedelta(days=1))
    used = sum(r["size"] for r in db.select("recordings", {"user_id": sub["user_id"], "created_at": ("gte", since)}, limit=2000))
    if used + len(data) > UPLOAD_BYTES_PER_DAY:
        raise SpeakingError("You have reached today's recording limit. Please come back tomorrow.", 429)
    try:
        duration = max(0.0, min(float(duration or 0), 600.0))
    except (TypeError, ValueError):
        duration = 0.0

    rec_id = str(uuid.uuid4())
    path = f"{sub['user_id']}/{sub['id']}/{key}-{rec_id}.{AUDIO_TYPES[mime]}"
    files.put(path, data, mime)
    old = db.select("recordings", {"submission_id": sub["id"], "question_key": key}, limit=1)
    if old:
        db.delete("recordings", {"id": old[0]["id"]})
    try:
        row = db.insert("recordings", {
            "id": rec_id, "user_id": sub["user_id"], "submission_id": sub["id"], "question_key": key,
            "mime": mime, "duration": round(duration, 2), "size": len(data), "path": path,
        })
    except Exception:
        files.delete([path])
        raise
    if old:
        files.delete([old[0]["path"]])
    return public_recording(row)


def complete_submission(db, sub, notes, seconds):
    if sub["status"] == "completed":
        return sub
    if not recordings_for(db, sub["id"]):
        raise SpeakingError("No answers were recorded. Check your microphone and try again.", 400)
    rows = db.update("speaking_submissions", {"id": sub["id"], "status": "recording"}, {
        "status": "completed", "completed_at": iso(now()),
        "notes": str(notes or "")[:MAX_NOTES] or None, "time_spent_seconds": seconds,
    })
    return rows[0] if rows else get_submission(db, sub["id"])


# --------------------------------------------------------------------------
# Views and access
# --------------------------------------------------------------------------

def public_recording(row):
    return {"id": row["id"], "key": row["question_key"], "duration": row.get("duration"), "size": row["size"],
            "mime": row["mime"]}


def submission_view(db, store, sub):
    """The test's questions with the candidate's recordings, for the results and check pages."""
    test = store.get_test(sub["test_id"]) or {"parts": []}
    recs = {r["question_key"]: public_recording(r) for r in recordings_for(db, sub["id"])}
    parts = []
    for part in test.get("parts", []):
        parts.append({
            "partNumber": part["partNumber"],
            "title": part.get("title", ""),
            "cueCard": part.get("cueCard"),
            "questions": [{"key": q["key"], "text": q["text"], "topic": q.get("topic"), "type": q.get("type"),
                           "answerSeconds": q.get("answerSeconds"), "recording": recs.get(q["key"])}
                          for q in part.get("questions", [])],
        })
    total = sum(1 for p in parts for _ in p["questions"])
    return {
        "id": sub["id"], "testId": sub["test_id"], "title": test.get("title", sub["test_id"]),
        "candidateName": sub.get("candidate_name"), "mode": sub.get("mode"), "status": sub["status"],
        "createdAt": sub.get("created_at"), "completedAt": sub.get("completed_at"),
        "timeSpentSeconds": sub.get("time_spent_seconds"), "notes": sub.get("notes") or "",
        "answered": len(recs), "totalQuestions": total,
        "recordingsDeleted": bool(sub.get("recordings_deleted_at")), "keepDays": KEEP_DAYS,
        "parts": parts,
    }


def viewer_role(db, profile, sub):
    """'owner', 'examiner' (has a check on it), 'admin', or None."""
    if not profile:
        return None
    if sub["user_id"] == profile["id"]:
        return "owner"
    if profile["role"] == "admin":
        return "admin"
    for c in db.select("checks", {"kind": "speaking", "submission_id": sub["id"], "examiner_id": profile["id"]}, limit=5):
        if c["status"] != "cancelled":
            return "examiner"
    return None


def recording_for(db, profile, recording_id):
    rows = db.select("recordings", {"id": recording_id}, limit=1)
    if not rows:
        return None
    sub = get_submission(db, rows[0]["submission_id"])
    if not sub or not viewer_role(db, profile, sub):
        return None
    return rows[0]


def checks_by_submission(db, user_id):
    """Latest examiner check of each of the user's Speaking submissions."""
    out = {}
    for c in db.select("checks", {"student_id": user_id, "kind": "speaking"}, order=[("created_at", "asc")], limit=200):
        if c["status"] != "cancelled":
            out[c["submission_id"]] = c
    return out


def history_items(db, user_id, limit=20):
    subs = db.select("speaking_submissions", {"user_id": user_id, "status": "completed"},
                     order=[("created_at", "desc")], limit=limit)
    if not subs:
        return []
    counts = {}
    for r in db.select("recordings", {"submission_id": ("in", [s["id"] for s in subs])}, limit=2000):
        counts[r["submission_id"]] = counts.get(r["submission_id"], 0) + 1
    checks = checks_by_submission(db, user_id)
    items = []
    for s in subs:
        c = checks.get(s["id"])
        items.append({
            "module": "speaking", "id": s["id"], "testId": s["test_id"], "createdAt": s["created_at"],
            "timeSpentSeconds": s.get("time_spent_seconds"), "mode": s.get("mode"), "answered": counts.get(s["id"], 0),
            "bandScore": float(c["overall_band"]) if c and c.get("overall_band") is not None else None,
            "checkId": c["id"] if c else None, "checkStatus": c["status"] if c else None,
        })
    return items


# --------------------------------------------------------------------------
# Clean-up
# --------------------------------------------------------------------------

def _delete_recordings(db, files, submission_id):
    rows = recordings_for(db, submission_id)
    if rows:
        files.delete([r["path"] for r in rows])
        db.delete("recordings", {"submission_id": submission_id})
    return len(rows)


def cleanup(db, files, at=None):
    """
    Delete abandoned tests (never finished, older than ABANDONED_HOURS) and the
    recordings of finished tests older than KEEP_DAYS, unless an examiner is
    still marking them. Returns (abandoned tests removed, recordings deleted).
    """
    at = at or now()
    abandoned = removed = 0
    old = iso(at - datetime.timedelta(hours=ABANDONED_HOURS))
    for sub in db.select("speaking_submissions", {"status": "recording", "created_at": ("lt", old)}, limit=200):
        removed += _delete_recordings(db, files, sub["id"])
        db.delete("speaking_submissions", {"id": sub["id"], "status": "recording"})
        abandoned += 1
    expired = iso(at - datetime.timedelta(days=KEEP_DAYS))
    for sub in db.select("speaking_submissions", {"status": "completed", "created_at": ("lt", expired),
                                                  "recordings_deleted_at": None}, limit=200):
        busy = db.select("checks", {"kind": "speaking", "submission_id": sub["id"],
                                    "status": ("in", ["waiting", "in_progress"])}, limit=1)
        if busy:
            continue
        done = [c for c in db.select("checks", {"kind": "speaking", "submission_id": sub["id"], "status": "completed"}, limit=5)]
        # A marked test keeps its recordings for KEEP_DAYS after the marks arrived.
        if any(parse_time(c.get("completed_at")) and parse_time(c["completed_at"]) > at - datetime.timedelta(days=KEEP_DAYS)
               for c in done):
            continue
        removed += _delete_recordings(db, files, sub["id"])
        db.update("speaking_submissions", {"id": sub["id"]}, {"recordings_deleted_at": iso(at)})
    return abandoned, removed
