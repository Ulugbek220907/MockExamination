#!/usr/bin/env python3
"""
Mock exam platform server (Tornado).

Serves the single-page app from public/ and a JSON API:

  GET  /api/health                     health check for the host
  GET  /api/config                     public feature flags (AI marking, sign-in methods, site name)
  GET  /api/tests                      dashboard summaries of every published test (with free/premium)
  GET  /api/tests/<id>                 one test, WITHOUT answer keys / model answers / transcripts
  POST /api/reading/<id>/submit        mark a reading test, store the attempt, return results
  POST /api/listening/<id>/submit      mark a listening test (results include the transcript)
  POST /api/writing/<id>/submit        analyse (and optionally AI-mark) a writing test
  /api/speaking/...                    record a speaking test and play it back (see mockexam/api.py)
  GET  /api/history[?clientId=<uuid>]  recent attempts: the account's, or this browser's
  GET  /api/admin/stats                totals (admin session or ADMIN_TOKEN)
  POST /api/admin/refresh              reload test content (admin session or ADMIN_TOKEN)
  /api/auth, /api/me, /api/orders, /api/pay, /api/examiners, /api/checks, /api/examiner, /api/admin/*
                                       accounts, payments and examiner checks (see mockexam/api.py)

Free tests (the first of each module) are open to everyone. Other tests, and
their audio, need the monthly plan.

Configuration is entirely through environment variables – see .env.example.
"""

import asyncio
import collections
import datetime
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sys
import threading
import time

import tornado.ioloop
import tornado.web


def load_dotenv(path):
    """Minimal .env support for local development (real env vars always win)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from mockexam import accounts, api, auth, content, scoring, speaking, storage, writing  # noqa: E402
from mockexam.web import (  # noqa: E402
    ADMIN_TOKEN, MAX_BODY_BYTES, SECURITY_HEADERS, SESSION_COOKIE, SESSION_DAYS, BaseHandler, in_thread,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mockexam")

PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
SITE_NAME = os.environ.get("SITE_NAME", "MockExam")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "")

AI_PER_IP_PER_HOUR = int(os.environ.get("AI_PER_IP_PER_HOUR", 6))
AI_DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT", 300))
AI_MAX_CONCURRENT = int(os.environ.get("AI_MAX_CONCURRENT", 4))
MAX_ESSAY_CHARS = 12000

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
TEST_ID_PATTERN = r"([a-z0-9][a-z0-9\-]{0,80})"

MODULES = {
    "reading": {"name": "Reading", "status": "active"},
    "writing": {"name": "Writing", "status": "active"},
    "listening": {"name": "Listening", "status": "active"},
    "speaking": {"name": "Speaking", "status": "active"},
}

STORE = storage.create_store()


def create_auth():
    if STORE.name == "supabase":
        key = (os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        return auth.SupabaseAuth(os.environ["SUPABASE_URL"].strip(), key)
    log.warning("Sign-in runs in development mode: codes are written to this log instead of being emailed.")
    return auth.DevAuth()


def cookie_secret():
    """Secret that signs session cookies. Stable across restarts when a server secret is configured."""
    explicit = os.environ.get("SESSION_SECRET", "").strip()
    if explicit:
        return explicit
    base = os.environ.get("SUPABASE_APP_SECRET", "").strip() or ADMIN_TOKEN
    if base:
        return hmac.new(base.encode("utf-8"), b"mockexam-session-v1", hashlib.sha256).hexdigest()
    log.warning("No SESSION_SECRET: sign-ins will not survive a restart.")
    return secrets.token_hex(32)


AUTH = create_auth()


# --------------------------------------------------------------------------
# Rate limiting for paid AI calls
# --------------------------------------------------------------------------

class AiLimiter:
    """In-memory limits: N assessments per IP per hour, and a global daily cap."""

    def __init__(self, per_ip_per_hour, daily_limit):
        self.per_ip = per_ip_per_hour
        self.daily = daily_limit
        self.hits = collections.defaultdict(collections.deque)
        self.day = datetime.date.today()
        self.day_count = 0
        self.lock = threading.Lock()

    def try_acquire(self, ip):
        now = time.time()
        with self.lock:
            today = datetime.date.today()
            if today != self.day:
                self.day, self.day_count = today, 0
            if self.day_count >= self.daily:
                return "The daily limit for AI marking has been reached. Please try again tomorrow."
            q = self.hits[ip]
            while q and now - q[0] > 3600:
                q.popleft()
            if len(q) >= self.per_ip:
                return f"You can request AI marking {self.per_ip} times per hour. Please try again later."
            q.append(now)
            self.day_count += 1
            return None


AI_LIMITER = AiLimiter(AI_PER_IP_PER_HOUR, AI_DAILY_LIMIT)
AI_SEMAPHORE = asyncio.Semaphore(AI_MAX_CONCURRENT)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def clean_name(value):
    name = re.sub(r"\s+", " ", str(value or "")).strip()
    return name[:80] or "Candidate"


def clean_client_id(value):
    value = str(value or "").strip().lower()
    return value if UUID_RE.match(value) else None


def clean_seconds(value):
    try:
        return max(0, min(int(value), 4 * 3600))
    except (TypeError, ValueError):
        return 0


class PlanCache:
    """Plan status per user for a minute, so audio range requests do not each hit the database."""

    TTL = 60

    def __init__(self):
        self.items = {}
        self.lock = threading.Lock()

    def get(self, db, user_id):
        now = time.time()
        with self.lock:
            hit = self.items.get(user_id)
            if hit and hit[1] > now:
                return hit[0]
        plan = accounts.plan_status(db, user_id)
        if plan["active"]:  # never cache "no plan", so a new payment unlocks tests at once
            with self.lock:
                if len(self.items) > 5000:
                    self.items.clear()
                self.items[user_id] = (plan, now + self.TTL)
        return plan

    def forget(self, user_id):
        with self.lock:
            self.items.pop(user_id, None)


PLAN_CACHE = PlanCache()


class ProfileCache:
    """Profiles for a minute, for audio: a recording is fetched in many range requests."""

    TTL = 60

    def __init__(self):
        self.items = {}
        self.lock = threading.Lock()

    def get(self, db, user_id):
        now = time.time()
        with self.lock:
            hit = self.items.get(user_id)
            if hit and hit[1] > now:
                return hit[0]
        profile = accounts.get_profile(db, user_id)
        if profile:
            with self.lock:
                if len(self.items) > 5000:
                    self.items.clear()
                self.items[user_id] = (profile, now + self.TTL)
        return profile


PROFILE_CACHE = ProfileCache()


# --------------------------------------------------------------------------
# Content: prepared once per load, with hashed asset URLs
# --------------------------------------------------------------------------

def versioned(path):
    """`path` under public/ with a content hash appended, so browsers can cache it for a year."""
    version = tornado.web.StaticFileHandler.get_version({"static_path": PUBLIC_DIR}, path)
    return f"{path}?v={version[:12]}" if version else path


class Catalog:
    """
    The current tests plus the JSON the API serves for them, built once per content
    load instead of on every request.
    """

    def __init__(self, tests):
        self.tests = tests
        self.by_id = {t["id"]: t for t in tests}
        summaries = []
        for t in tests:
            summary = content.summarize_test(t)
            summary["access"] = accounts.test_access(t)
            summaries.append(summary)
        summaries.sort(key=lambda s: (s["module"], s["sortOrder"], s["id"]))
        self.index_json = json.dumps({"modules": MODULES, "tests": summaries}, ensure_ascii=False)
        self._public_json = {}
        self._versions = {}

    def public_json(self, test):
        cached = self._public_json.get(test["id"])
        if cached is None:
            public = self.with_audio_versions(content.public_test(test))
            cached = self._public_json[test["id"]] = json.dumps(public, ensure_ascii=False, default=str)
        return cached

    def with_audio_versions(self, value):
        """A copy of `value` in which every {"audio": {"src": ...}} points at a hashed URL."""
        if isinstance(value, list):
            return [self.with_audio_versions(v) for v in value]
        if not isinstance(value, dict):
            return value
        out = {k: self.with_audio_versions(v) for k, v in value.items()}
        audio = out.get("audio")
        if isinstance(audio, dict) and isinstance(audio.get("src"), str) and audio["src"].startswith("audio/"):
            src = audio["src"]
            if src not in self._versions:
                self._versions[src] = versioned(src)
            out["audio"] = {**audio, "src": self._versions[src]}
        return out


_CATALOG = Catalog([])


async def catalog():
    global _CATALOG
    tests = await in_thread(STORE.list_tests)
    if tests is not _CATALOG.tests:
        _CATALOG = await in_thread(Catalog, tests)
    return _CATALOG


async def allowed_to_open(test, profile):
    """(ok, error_status, error_code) for a signed-in (or anonymous) user and a test."""
    if accounts.test_access(test) == "free":
        return True, None, None
    if not profile:
        return False, 401, "login_required"
    plan = await in_thread(PLAN_CACHE.get, STORE.db, profile["id"])
    if accounts.can_open_test(test, profile, plan):
        return True, None, None
    return False, 402, "plan_required"


async def require_test_access(handler, test):
    """The signed-in profile (or None for a free test); raises 401/402 if the test is locked."""
    profile = await handler.load_profile()
    ok, status, code = await allowed_to_open(test, profile)
    if not ok:
        message = "Sign in to open this test." if code == "login_required" else "This test is part of the monthly plan."
        raise api.ApiError(status, message, code)
    return profile


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------

class HealthHandler(BaseHandler):
    def get(self):
        self.send_json({
            "status": "healthy",
            "service": "mock-exam",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })


class ConfigHandler(BaseHandler):
    async def get(self):
        self.send_json({
            "siteName": SITE_NAME,
            "aiMarking": writing.ai_configured(),
            "contactEmail": CONTACT_EMAIL,
            "storage": STORE.name,
            "auth": {"email": True, "google": await in_thread(AUTH.google_enabled), "dev": AUTH.name == "dev"},
            "speakingKeepDays": speaking.KEEP_DAYS,
        })


def send_cached_json(handler, text):
    """Prepared JSON that the browser may keep and revalidate (304 via the ETag)."""
    handler.set_header("Content-Type", "application/json; charset=utf-8")
    handler.set_header("Cache-Control", "private, no-cache")
    handler.finish(text)


class TestsHandler(BaseHandler):
    async def get(self):
        send_cached_json(self, (await catalog()).index_json)


class TestHandler(BaseHandler):
    async def get(self, test_id):
        cat = await catalog()
        test = cat.by_id.get(test_id)
        if not test:
            return self.send_error_json(404, "Test not found")
        await require_test_access(self, test)
        send_cached_json(self, cat.public_json(test))


class ScoredSubmitHandler(BaseHandler):
    """Marks a reading or listening test, stores the attempt and returns the results."""

    MODULE = "reading"

    def evaluate(self, test, answers, name, seconds):
        return scoring.evaluate_reading(test, answers, name, seconds)

    def breakdown(self, result):
        return {"passages": result["passageBreakdown"], "types": result["typeBreakdown"]}

    def save(self, record):
        return STORE.save_reading_attempt(record)

    async def post(self, test_id):
        cat = await catalog()
        test = cat.by_id.get(test_id)
        if not test or test.get("module") != self.MODULE:
            return self.send_error_json(404, f"{self.MODULE.title()} test not found")
        profile = await require_test_access(self, test)
        body = self.body_json()

        raw_answers = body.get("answers") or {}
        answers = {}
        if isinstance(raw_answers, dict):
            for k, v in raw_answers.items():
                if str(k).isdigit() and isinstance(v, str) and v.strip():
                    answers[str(int(k))] = v.strip()[:100]

        name = clean_name(body.get("candidateName"))
        seconds = clean_seconds(body.get("timeSpentSeconds"))
        mode = "practice" if body.get("mode") == "practice" else "exam"
        result = self.evaluate(test, answers, name, seconds)
        result["mode"] = mode
        if "transcript" in result:
            result["transcript"] = cat.with_audio_versions(result["transcript"])

        record = {
            "test_id": test["id"],
            "client_id": clean_client_id(body.get("clientId")),
            "user_id": profile["id"] if profile else None,
            "candidate_name": name,
            "mode": mode,
            "raw_score": result["rawScore"],
            "total_questions": result["totalQuestions"],
            "band_score": result["bandScore"],
            "time_spent_seconds": seconds,
            "answers": answers,
            "breakdown": self.breakdown(result),
        }
        try:
            result["attemptId"] = await in_thread(self.save, record)
        except Exception:
            log.exception("Could not save %s attempt", self.MODULE)
            result["attemptId"] = None
        self.send_json(result)


class ReadingSubmitHandler(ScoredSubmitHandler):
    MODULE = "reading"


class ListeningSubmitHandler(ScoredSubmitHandler):
    MODULE = "listening"

    def evaluate(self, test, answers, name, seconds):
        return scoring.evaluate_listening(test, answers, name, seconds)

    def breakdown(self, result):
        return {"parts": result["partBreakdown"], "types": result["typeBreakdown"]}

    def save(self, record):
        return STORE.save_listening_attempt(record)


class WritingSubmitHandler(BaseHandler):
    async def post(self, test_id):
        test = (await catalog()).by_id.get(test_id)
        if not test or test.get("module") != "writing":
            return self.send_error_json(404, "Writing test not found")
        profile = await require_test_access(self, test)
        body = self.body_json()

        raw = body.get("responses") or {}
        responses = {}
        for n in (1, 2):
            text = raw.get(str(n), "") if isinstance(raw, dict) else ""
            text = text if isinstance(text, str) else ""
            if len(text) > MAX_ESSAY_CHARS:
                return self.send_error_json(413, f"Task {n} is too long.")
            responses[n] = text.replace("\r\n", "\n").strip()

        tasks = {t["taskNumber"]: t for t in test["tasks"]}
        analyses = {
            n: writing.analyse_text(responses[n], n, tasks[n]["minWords"], tasks[n].get("essayType"))
            for n in (1, 2)
        }
        name = clean_name(body.get("candidateName"))
        seconds = clean_seconds(body.get("timeSpentSeconds"))

        assessment, status, message = None, "not_requested", ""
        if not writing.ai_configured():
            status, message = "not_configured", "AI marking is not enabled on this site yet."
        elif body.get("requestAssessment", True):
            if all(analyses[n]["wordCount"] < writing.MIN_WORDS_FOR_AI for n in (1, 2)):
                status, message = "too_short", "Both responses are too short to be marked."
            else:
                limited = AI_LIMITER.try_acquire(self.client_ip())
                if limited:
                    status, message = "rate_limited", limited
                else:
                    try:
                        async with AI_SEMAPHORE:
                            assessment = await writing.assess_with_claude(test, responses, analyses)
                        status = "complete"
                    except writing.AssessmentUnavailable as e:
                        status, message = "error", str(e)
                    except Exception:
                        log.exception("AI assessment failed")
                        status, message = "error", "The AI examiner could not mark this script. Please try again later."

        result = {
            "testId": test["id"],
            "title": test["title"],
            "candidateName": name,
            "timeSpentSeconds": seconds,
            "tasks": [
                {
                    "taskNumber": n,
                    "title": tasks[n].get("title", f"Task {n}"),
                    "prompt": tasks[n]["prompt"],
                    "minWords": tasks[n]["minWords"],
                    "visual": tasks[n].get("visual"),
                    "response": responses[n],
                    "analysis": analyses[n],
                    "modelAnswer": tasks[n].get("modelAnswer", ""),
                }
                for n in (1, 2)
            ],
            "assessment": assessment,
            "assessmentStatus": status,
            "assessmentMessage": message,
            "overallBand": assessment["overallBand"] if assessment else None,
            "signedIn": bool(profile),
        }

        record = {
            "test_id": test["id"],
            "client_id": clean_client_id(body.get("clientId")),
            "user_id": profile["id"] if profile else None,
            "candidate_name": name,
            "task1_text": responses[1],
            "task2_text": responses[2],
            "task1_words": analyses[1]["wordCount"],
            "task2_words": analyses[2]["wordCount"],
            "time_spent_seconds": seconds,
            "analysis": analyses,
            "assessment": assessment,
            "overall_band": result["overallBand"],
        }
        try:
            result["submissionId"] = await in_thread(STORE.save_writing_submission, record)
        except Exception:
            log.exception("Could not save writing submission")
            result["submissionId"] = None
        self.send_json(result)


class HistoryHandler(BaseHandler):
    async def get(self):
        user_id = self.current_user
        client_id = clean_client_id(self.get_query_argument("clientId", ""))
        if not user_id and not client_id:
            return self.send_json({"items": []})
        try:
            items = await in_thread(lambda: STORE.list_history(client_id, 20, user_id=user_id))
        except Exception:
            log.exception("Could not load history")
            items = []
        if user_id:
            try:
                items += await in_thread(speaking.history_items, STORE.db, user_id, 20)
                items.sort(key=lambda i: i["createdAt"] or "", reverse=True)
            except Exception:
                log.exception("Could not load speaking history")
        self.send_json({"items": items[:20]})


class AdminStatsHandler(api.AdminHandler):
    async def get(self):
        await self.require_admin()
        stats = await in_thread(STORE.stats)
        stats["storage"] = STORE.name
        stats["tests"] = len(await in_thread(STORE.list_tests))
        self.send_json(stats)


class AdminRefreshHandler(api.AdminHandler):
    async def post(self):
        await self.require_admin()
        STORE.refresh()
        tests = await in_thread(STORE.list_tests)
        self.send_json({"reloaded": len(tests)})


class ApiNotFoundHandler(BaseHandler):
    def prepare(self):
        self.send_error_json(404, "Endpoint not found")


ASSET_REF_RE = re.compile(r'((?:href|src)=")((?:css|js)/[^"?]+|favicon\.svg)(")')


class IndexHandler(BaseHandler):
    """
    The app shell, with a content hash on every CSS/JS link. The page itself is always
    revalidated, so a deploy shows up immediately, while the assets it points to are
    cached for a year and only downloaded again when they change.
    """

    _html = None

    @classmethod
    def html(cls):
        if cls._html is None:
            with open(os.path.join(PUBLIC_DIR, "index.html"), encoding="utf-8") as f:
                page = f.read()
            cls._html = ASSET_REF_RE.sub(lambda m: m.group(1) + versioned(m.group(2)) + m.group(3), page)
        return cls._html

    def get(self):
        self.head()
        self.finish(self.html())

    def head(self):  # uptime monitors often ping with HEAD
        self.set_header("Content-Type", "text/html; charset=utf-8")
        self.set_header("Cache-Control", "no-cache")


class StaticHandler(tornado.web.StaticFileHandler):
    """
    Serves public/ with security headers. Hash-versioned URLs (?v=...) never change, so
    they are cached for a year; anything else is revalidated on every use.
    """

    CACHE_SCOPE = "public"

    def set_default_headers(self):
        for k, v in SECURITY_HEADERS.items():
            self.set_header(k, v)

    def set_extra_headers(self, path):
        if self.get_query_argument("v", None):
            self.set_header("Cache-Control", f"{self.CACHE_SCOPE}, max-age=31536000, immutable")
        else:
            self.set_header("Cache-Control", "no-cache" if self.CACHE_SCOPE == "public" else "private, no-cache")


class AudioHandler(StaticHandler):
    """Listening recordings: open for free tests, plan-only for the others."""

    CACHE_SCOPE = "private"

    async def prepare(self):
        test_id = (self.path_args[0] if self.path_args else "").split("/", 1)[0]
        test = (await catalog()).by_id.get(test_id) if test_id else None
        if not test or accounts.test_access(test) == "free":
            return
        user_id = None
        raw = self.get_signed_cookie(SESSION_COOKIE, max_age_days=SESSION_DAYS)
        if raw:
            try:
                user_id = json.loads(raw).get("uid")
            except (ValueError, AttributeError):
                user_id = None
        profile = await in_thread(PROFILE_CACHE.get, STORE.db, user_id) if user_id else None
        ok, status, _ = await allowed_to_open(test, profile)
        if not ok:
            raise tornado.web.HTTPError(status)


def make_app():
    return tornado.web.Application(
        [
            (r"/api/health", HealthHandler),
            (r"/healthz", HealthHandler),
            (r"/api/config", ConfigHandler),
            (r"/api/tests", TestsHandler),
            (rf"/api/tests/{TEST_ID_PATTERN}", TestHandler),
            (rf"/api/reading/{TEST_ID_PATTERN}/submit", ReadingSubmitHandler),
            (rf"/api/listening/{TEST_ID_PATTERN}/submit", ListeningSubmitHandler),
            (rf"/api/writing/{TEST_ID_PATTERN}/submit", WritingSubmitHandler),
            (r"/api/history", HistoryHandler),
            (r"/api/admin/stats", AdminStatsHandler),
            (r"/api/admin/refresh", AdminRefreshHandler),
            *api.routes(),
            (r"/api/.*", ApiNotFoundHandler),
            (r"/audio/(.*)", AudioHandler, {"path": os.path.join(PUBLIC_DIR, "audio")}),
            (r"/(?:index\.html)?", IndexHandler),
            (r"/(.*)", StaticHandler, {"path": PUBLIC_DIR, "default_filename": "index.html"}),
        ],
        compress_response=True,
        cookie_secret=cookie_secret(),
        store=STORE,
        auth=AUTH,
    )


async def clean_up_recordings():
    """Deletes old Speaking recordings (see speaking.cleanup); runs a few times a day."""
    try:
        abandoned, removed = await in_thread(speaking.cleanup, STORE.db, STORE.files)
        if abandoned or removed:
            log.info("Speaking clean-up: %d unfinished tests and %d recordings deleted", abandoned, removed)
    except Exception:
        log.exception("Speaking clean-up failed")


def main():
    global _CATALOG
    tests = STORE.list_tests()
    # Build the API responses and asset hashes before taking traffic.
    _CATALOG = Catalog(tests)
    for test in tests:
        _CATALOG.public_json(test)
    IndexHandler.html()
    counts = collections.Counter(t.get("module") for t in tests)
    app = make_app()
    app.listen(PORT, address="0.0.0.0", max_body_size=MAX_BODY_BYTES)
    log.info("%s running on http://0.0.0.0:%d (storage=%s, sign-in=%s, AI marking=%s)",
             SITE_NAME, PORT, STORE.name, AUTH.name, "on" if writing.ai_configured() else "off")
    log.info("Loaded %d reading, %d listening, %d writing and %d speaking tests",
             counts["reading"], counts["listening"], counts["writing"], counts["speaking"])
    loop = tornado.ioloop.IOLoop.current()
    loop.call_later(60, clean_up_recordings)
    tornado.ioloop.PeriodicCallback(clean_up_recordings, 6 * 3600 * 1000).start()
    loop.start()


if __name__ == "__main__":
    if sys.version_info < (3, 10):
        sys.exit("Python 3.10 or newer is required.")
    main()
