"""
Storage backends.

LocalStore     – tests from content/*.json, attempts in a local SQLite file.
                 Zero configuration; ideal for development.
SupabaseStore  – tests and attempts in Supabase (Postgres) via its REST API.
                 Enabled automatically when SUPABASE_URL and
                 SUPABASE_SERVICE_ROLE_KEY are set.

Both expose the same methods, and all methods are synchronous (the server
calls them from a thread pool).
"""

import json
import logging
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import content

log = logging.getLogger("mockexam.storage")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, "content")
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "data", "local.sqlite3")


def load_local_tests():
    tests = []
    for module in ("reading", "writing"):
        tests += content.load_json_dir(os.path.join(CONTENT_DIR, module))
    return tests


class LocalStore:
    name = "local"

    def __init__(self, db_path=None):
        self.db_path = db_path or os.environ.get("SQLITE_PATH", DEFAULT_SQLITE_PATH)
        self._tests = None
        self._lock = threading.Lock()
        self._init_db()

    # -- content -----------------------------------------------------------
    def list_tests(self):
        if self._tests is None:
            self._tests = load_local_tests()
        return self._tests

    def get_test(self, test_id):
        return next((t for t in self.list_tests() if t["id"] == test_id), None)

    def refresh(self):
        self._tests = None

    # -- attempts ----------------------------------------------------------
    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=10.0)

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS reading_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    client_id TEXT,
                    candidate_name TEXT,
                    mode TEXT,
                    raw_score INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    band_score REAL NOT NULL,
                    time_spent_seconds INTEGER,
                    answers TEXT,
                    breakdown TEXT,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
                );
                CREATE TABLE IF NOT EXISTS writing_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    client_id TEXT,
                    candidate_name TEXT,
                    task1_text TEXT,
                    task2_text TEXT,
                    task1_words INTEGER,
                    task2_words INTEGER,
                    time_spent_seconds INTEGER,
                    analysis TEXT,
                    assessment TEXT,
                    overall_band REAL,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
                );
                CREATE INDEX IF NOT EXISTS idx_reading_client ON reading_attempts(client_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_writing_client ON writing_submissions(client_id, created_at);
                """
            )

    def save_reading_attempt(self, rec):
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO reading_attempts (test_id, client_id, candidate_name, mode, raw_score,
                   total_questions, band_score, time_spent_seconds, answers, breakdown)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (rec["test_id"], rec.get("client_id"), rec.get("candidate_name"), rec.get("mode"),
                 rec["raw_score"], rec["total_questions"], rec["band_score"], rec.get("time_spent_seconds"),
                 json.dumps(rec.get("answers")), json.dumps(rec.get("breakdown"))),
            )
            return cur.lastrowid

    def save_writing_submission(self, rec):
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO writing_submissions (test_id, client_id, candidate_name, task1_text, task2_text,
                   task1_words, task2_words, time_spent_seconds, analysis, assessment, overall_band)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (rec["test_id"], rec.get("client_id"), rec.get("candidate_name"), rec.get("task1_text"),
                 rec.get("task2_text"), rec.get("task1_words"), rec.get("task2_words"),
                 rec.get("time_spent_seconds"), json.dumps(rec.get("analysis")),
                 json.dumps(rec.get("assessment")), rec.get("overall_band")),
            )
            return cur.lastrowid

    def list_history(self, client_id, limit=20):
        with self._lock, self._connect() as conn:
            reading = conn.execute(
                """SELECT id, test_id, raw_score, total_questions, band_score, time_spent_seconds, mode, created_at
                   FROM reading_attempts WHERE client_id = ? ORDER BY id DESC LIMIT ?""",
                (client_id, limit),
            ).fetchall()
            writing = conn.execute(
                """SELECT id, test_id, task1_words, task2_words, overall_band, time_spent_seconds, created_at
                   FROM writing_submissions WHERE client_id = ? ORDER BY id DESC LIMIT ?""",
                (client_id, limit),
            ).fetchall()
        items = [
            {"module": "reading", "id": r[0], "testId": r[1], "rawScore": r[2], "totalQuestions": r[3],
             "bandScore": r[4], "timeSpentSeconds": r[5], "mode": r[6], "createdAt": r[7]}
            for r in reading
        ] + [
            {"module": "writing", "id": w[0], "testId": w[1], "task1Words": w[2], "task2Words": w[3],
             "bandScore": w[4], "timeSpentSeconds": w[5], "createdAt": w[6]}
            for w in writing
        ]
        items.sort(key=lambda i: i["createdAt"] or "", reverse=True)
        return items[:limit]

    def stats(self):
        with self._lock, self._connect() as conn:
            r = conn.execute("SELECT COUNT(*), AVG(band_score) FROM reading_attempts").fetchone()
            w = conn.execute("SELECT COUNT(*), AVG(overall_band) FROM writing_submissions").fetchone()
        return {"readingAttempts": r[0], "readingAvgBand": r[1], "writingSubmissions": w[0], "writingAvgBand": w[1]}


class SupabaseError(Exception):
    pass


class SupabaseStore:
    """Talks to Supabase's PostgREST API with the service-role key (server-side only)."""

    name = "supabase"
    CACHE_SECONDS = 300

    def __init__(self, url, service_key):
        self.rest = url.rstrip("/") + "/rest/v1"
        self.key = service_key
        self._cache = None
        self._cache_at = 0.0
        self._lock = threading.Lock()

    def _request(self, method, path, params=None, body=None, prefer=None):
        url = f"{self.rest}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            raise SupabaseError(f"{method} {path} failed ({e.code}): {detail}") from e
        except urllib.error.URLError as e:
            raise SupabaseError(f"{method} {path} failed: {e.reason}") from e

    # -- content -----------------------------------------------------------
    def list_tests(self):
        with self._lock:
            fresh = self._cache is not None and time.time() - self._cache_at < self.CACHE_SECONDS
            if fresh:
                return self._cache
        try:
            rows = self._request(
                "GET", "tests",
                {"select": "content", "is_published": "eq.true", "order": "module.asc,sort_order.asc,id.asc"},
            ) or []
            tests = [r["content"] for r in rows]
        except SupabaseError as e:
            log.error("Could not load tests from Supabase, using local content: %s", e)
            tests = []
        if not tests:
            # Not seeded yet (or unreachable): serve the bundled content so the site still works.
            tests = load_local_tests()
        with self._lock:
            self._cache, self._cache_at = tests, time.time()
        return tests

    def get_test(self, test_id):
        return next((t for t in self.list_tests() if t["id"] == test_id), None)

    def refresh(self):
        with self._lock:
            self._cache = None

    def upsert_test(self, test):
        row = {
            "id": test["id"],
            "module": test["module"],
            "variant": test.get("variant", "academic"),
            "title": test["title"],
            "sort_order": test.get("sortOrder", 999),
            "is_published": True,
            "content": test,
        }
        self._request("POST", "tests", {"on_conflict": "id"}, [row],
                      prefer="resolution=merge-duplicates,return=minimal")

    # -- attempts ----------------------------------------------------------
    def save_reading_attempt(self, rec):
        rows = self._request("POST", "reading_attempts", body=[rec], prefer="return=representation")
        return rows[0]["id"] if rows else None

    def save_writing_submission(self, rec):
        rows = self._request("POST", "writing_submissions", body=[rec], prefer="return=representation")
        return rows[0]["id"] if rows else None

    def list_history(self, client_id, limit=20):
        reading = self._request("GET", "reading_attempts", {
            "select": "id,test_id,raw_score,total_questions,band_score,time_spent_seconds,mode,created_at",
            "client_id": f"eq.{client_id}", "order": "created_at.desc", "limit": str(limit),
        }) or []
        writing = self._request("GET", "writing_submissions", {
            "select": "id,test_id,task1_words,task2_words,overall_band,time_spent_seconds,created_at",
            "client_id": f"eq.{client_id}", "order": "created_at.desc", "limit": str(limit),
        }) or []
        items = [
            {"module": "reading", "id": r["id"], "testId": r["test_id"], "rawScore": r["raw_score"],
             "totalQuestions": r["total_questions"], "bandScore": float(r["band_score"]),
             "timeSpentSeconds": r["time_spent_seconds"], "mode": r["mode"], "createdAt": r["created_at"]}
            for r in reading
        ] + [
            {"module": "writing", "id": w["id"], "testId": w["test_id"], "task1Words": w["task1_words"],
             "task2Words": w["task2_words"],
             "bandScore": float(w["overall_band"]) if w["overall_band"] is not None else None,
             "timeSpentSeconds": w["time_spent_seconds"], "createdAt": w["created_at"]}
            for w in writing
        ]
        items.sort(key=lambda i: i["createdAt"] or "", reverse=True)
        return items[:limit]

    def stats(self):
        def count(table):
            req = urllib.request.Request(
                f"{self.rest}/{table}?select=id&limit=1",
                headers={"apikey": self.key, "Authorization": f"Bearer {self.key}", "Prefer": "count=exact"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                rng = resp.headers.get("Content-Range", "*/0")
            return int(rng.split("/")[-1] or 0)

        return {"readingAttempts": count("reading_attempts"), "writingSubmissions": count("writing_submissions")}


def create_store():
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        log.info("Using Supabase storage at %s", url)
        return SupabaseStore(url, key)
    log.info("Using local storage (content/ + SQLite). Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to use Supabase.")
    return LocalStore()
