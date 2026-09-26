"""
Storage backends.

LocalStore     – tests from content/<module>/*.json, attempts in a local SQLite file.
                 Zero configuration; ideal for development.
SupabaseStore  – tests and attempts in Supabase (Postgres) through the server
                 API functions in supabase/schema.sql. Enabled when
                 SUPABASE_URL, SUPABASE_KEY and SUPABASE_APP_SECRET are set.

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
import urllib.request

from . import content

log = logging.getLogger("mockexam.storage")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, "content")
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "data", "local.sqlite3")


MODULES = ("reading", "listening", "writing")


def load_local_tests():
    tests = []
    for module in MODULES:
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
                CREATE TABLE IF NOT EXISTS listening_attempts (
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
                CREATE INDEX IF NOT EXISTS idx_listening_client ON listening_attempts(client_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_writing_client ON writing_submissions(client_id, created_at);
                """
            )

    def _save_scored_attempt(self, table, rec):
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                f"""INSERT INTO {table} (test_id, client_id, candidate_name, mode, raw_score,
                   total_questions, band_score, time_spent_seconds, answers, breakdown)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (rec["test_id"], rec.get("client_id"), rec.get("candidate_name"), rec.get("mode"),
                 rec["raw_score"], rec["total_questions"], rec["band_score"], rec.get("time_spent_seconds"),
                 json.dumps(rec.get("answers")), json.dumps(rec.get("breakdown"))),
            )
            return cur.lastrowid

    def save_reading_attempt(self, rec):
        return self._save_scored_attempt("reading_attempts", rec)

    def save_listening_attempt(self, rec):
        return self._save_scored_attempt("listening_attempts", rec)

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
            scored = []
            for module in ("reading", "listening"):
                rows = conn.execute(
                    f"""SELECT id, test_id, raw_score, total_questions, band_score, time_spent_seconds, mode, created_at
                       FROM {module}_attempts WHERE client_id = ? ORDER BY id DESC LIMIT ?""",
                    (client_id, limit),
                ).fetchall()
                scored += [(module, r) for r in rows]
            writing = conn.execute(
                """SELECT id, test_id, task1_words, task2_words, overall_band, time_spent_seconds, created_at
                   FROM writing_submissions WHERE client_id = ? ORDER BY id DESC LIMIT ?""",
                (client_id, limit),
            ).fetchall()
        items = [
            {"module": module, "id": r[0], "testId": r[1], "rawScore": r[2], "totalQuestions": r[3],
             "bandScore": r[4], "timeSpentSeconds": r[5], "mode": r[6], "createdAt": r[7]}
            for module, r in scored
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
            li = conn.execute("SELECT COUNT(*), AVG(band_score) FROM listening_attempts").fetchone()
            w = conn.execute("SELECT COUNT(*), AVG(overall_band) FROM writing_submissions").fetchone()
        return {"readingAttempts": r[0], "readingAvgBand": r[1], "listeningAttempts": li[0], "listeningAvgBand": li[1],
                "writingSubmissions": w[0], "writingAvgBand": w[1]}


class SupabaseError(Exception):
    pass


class SupabaseStore:
    """
    Talks to Supabase through the server API functions defined in supabase/schema.sql
    (POST /rest/v1/rpc/app_*). Works with the public publishable/anon key: every
    function also requires the server secret, and the tables themselves stay closed.
    """

    name = "supabase"
    CACHE_SECONDS = 300

    def __init__(self, url, api_key, app_secret):
        self.rest = url.rstrip("/") + "/rest/v1"
        self.key = api_key
        self.secret = app_secret
        self._cache = None
        self._cache_at = 0.0
        self._lock = threading.Lock()

    def _rpc(self, function, **params):
        headers = {
            "apikey": self.key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # Legacy anon/service keys are JWTs and also go in Authorization; new
        # sb_publishable_/sb_secret_ keys must only be sent as `apikey`.
        if self.key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {self.key}"
        body = json.dumps({"p_key": self.secret, **params}).encode("utf-8")
        req = urllib.request.Request(f"{self.rest}/rpc/{function}", data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            raise SupabaseError(f"{function} failed ({e.code}): {detail}") from e
        except urllib.error.URLError as e:
            raise SupabaseError(f"{function} failed: {e.reason}") from e

    # -- content -----------------------------------------------------------
    def list_tests(self):
        with self._lock:
            fresh = self._cache is not None and time.time() - self._cache_at < self.CACHE_SECONDS
            if fresh:
                return self._cache
        try:
            tests = self._rpc("app_list_tests") or []
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
        self._rpc("app_upsert_test", p_test=test)

    # -- attempts ----------------------------------------------------------
    def save_reading_attempt(self, rec):
        return self._rpc("app_save_reading_attempt", p_row=rec)

    def save_listening_attempt(self, rec):
        return self._rpc("app_save_listening_attempt", p_row=rec)

    def save_writing_submission(self, rec):
        return self._rpc("app_save_writing_submission", p_row=rec)

    def list_history(self, client_id, limit=20):
        data = self._rpc("app_history", p_client=client_id, p_limit=limit) or {}
        items = [
            {"module": module, "id": r["id"], "testId": r["test_id"], "rawScore": r["raw_score"],
             "totalQuestions": r["total_questions"], "bandScore": float(r["band_score"]),
             "timeSpentSeconds": r["time_spent_seconds"], "mode": r["mode"], "createdAt": r["created_at"]}
            for module in ("reading", "listening")
            for r in data.get(module, [])
        ] + [
            {"module": "writing", "id": w["id"], "testId": w["test_id"], "task1Words": w["task1_words"],
             "task2Words": w["task2_words"],
             "bandScore": float(w["overall_band"]) if w["overall_band"] is not None else None,
             "timeSpentSeconds": w["time_spent_seconds"], "createdAt": w["created_at"]}
            for w in data.get("writing", [])
        ]
        items.sort(key=lambda i: i["createdAt"] or "", reverse=True)
        return items[:limit]

    def stats(self):
        return self._rpc("app_stats") or {}


def create_store():
    url = os.environ.get("SUPABASE_URL", "").strip()
    # Any Supabase API key works (publishable/anon recommended); SUPABASE_SERVICE_ROLE_KEY is accepted too.
    key = (os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    secret = os.environ.get("SUPABASE_APP_SECRET", "").strip()
    if url and key and secret:
        log.info("Using Supabase storage at %s", url)
        return SupabaseStore(url, key, secret)
    if url or key or secret:
        log.warning("Supabase is partly configured: SUPABASE_URL, SUPABASE_KEY and SUPABASE_APP_SECRET are all required.")
    log.info("Using local storage (content/ + SQLite).")
    return LocalStore()
