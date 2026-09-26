#!/usr/bin/env python3
"""
Mock exam platform server (Tornado).

Serves the single-page app from public/ and a small JSON API:

  GET  /api/health                     health check for the host
  GET  /api/config                     public feature flags (AI marking on/off, site name)
  GET  /api/tests                      dashboard summaries of every published test
  GET  /api/tests/<id>                 one test, WITHOUT answer keys / model answers / transcripts
  POST /api/reading/<id>/submit        mark a reading test, store the attempt, return results
  POST /api/listening/<id>/submit      mark a listening test (results include the transcript)
  POST /api/writing/<id>/submit        analyse (and optionally AI-mark) a writing test
  GET  /api/history?clientId=<uuid>    a browser's own recent attempts
  GET  /api/admin/stats                totals (requires ADMIN_TOKEN)
  POST /api/admin/refresh              reload test content (requires ADMIN_TOKEN)

Configuration is entirely through environment variables – see .env.example.
"""

import asyncio
import collections
import datetime
import hmac
import json
import logging
import os
import re
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

from mockexam import content, scoring, storage, writing  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mockexam")

PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
SITE_NAME = os.environ.get("SITE_NAME", "MockExam")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "")
TRUST_PROXY = os.environ.get("TRUST_PROXY", "1") != "0"

AI_PER_IP_PER_HOUR = int(os.environ.get("AI_PER_IP_PER_HOUR", 6))
AI_DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT", 300))
AI_MAX_CONCURRENT = int(os.environ.get("AI_MAX_CONCURRENT", 4))
MAX_ESSAY_CHARS = 12000
MAX_BODY_BYTES = 256 * 1024

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
TEST_ID_PATTERN = r"([a-z0-9][a-z0-9\-]{0,80})"

MODULES = {
    "reading": {"name": "Reading", "status": "active"},
    "writing": {"name": "Writing", "status": "active"},
    "listening": {"name": "Listening", "status": "active"},
    "speaking": {"name": "Speaking", "status": "soon"},
}

STORE = storage.create_store()


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

async def in_thread(fn, *args):
    return await tornado.ioloop.IOLoop.current().run_in_executor(None, fn, *args)


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


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
}


class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        for k, v in SECURITY_HEADERS.items():
            self.set_header(k, v)

    def send_json(self, payload, status=200):
        self.set_status(status)
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.set_header("Cache-Control", "no-store")
        self.finish(json.dumps(payload, ensure_ascii=False))

    def send_error_json(self, status, message):
        self.send_json({"error": message}, status)

    def body_json(self):
        if len(self.request.body or b"") > MAX_BODY_BYTES:
            raise tornado.web.HTTPError(413)
        try:
            data = json.loads(self.request.body or b"{}")
        except (ValueError, UnicodeDecodeError):
            raise tornado.web.HTTPError(400, "Invalid JSON")
        if not isinstance(data, dict):
            raise tornado.web.HTTPError(400, "Expected a JSON object")
        return data

    def write_error(self, status_code, **kwargs):
        reason = self._reason if status_code < 500 else "Internal server error"
        self.send_json({"error": reason}, status_code)

    def client_ip(self):
        """
        Real client IP for rate limiting. Behind a proxy (Render, Docker ingress) the
        proxy appends the address it saw as the LAST X-Forwarded-For entry, which a
        client cannot forge. Set TRUST_PROXY=0 when the server is exposed directly.
        """
        if TRUST_PROXY:
            forwarded = self.request.headers.get("X-Forwarded-For", "")
            if forwarded:
                return forwarded.split(",")[-1].strip()
        return self.request.remote_ip

    def require_admin(self):
        supplied = self.request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not ADMIN_TOKEN or not hmac.compare_digest(supplied, ADMIN_TOKEN):
            raise tornado.web.HTTPError(401, "Admin token required")


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
    def get(self):
        self.send_json({
            "siteName": SITE_NAME,
            "aiMarking": writing.ai_configured(),
            "contactEmail": CONTACT_EMAIL,
            "storage": STORE.name,
        })


class TestsHandler(BaseHandler):
    async def get(self):
        tests = await in_thread(STORE.list_tests)
        summaries = [content.summarize_test(t) for t in tests]
        summaries.sort(key=lambda s: (s["module"], s["sortOrder"], s["id"]))
        self.send_json({"modules": MODULES, "tests": summaries})


class TestHandler(BaseHandler):
    async def get(self, test_id):
        test = await in_thread(STORE.get_test, test_id)
        if not test:
            return self.send_error_json(404, "Test not found")
        self.send_json(content.public_test(test))


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
        test = await in_thread(STORE.get_test, test_id)
        if not test or test.get("module") != self.MODULE:
            return self.send_error_json(404, f"{self.MODULE.title()} test not found")
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

        record = {
            "test_id": test["id"],
            "client_id": clean_client_id(body.get("clientId")),
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
        test = await in_thread(STORE.get_test, test_id)
        if not test or test.get("module") != "writing":
            return self.send_error_json(404, "Writing test not found")
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
        }

        record = {
            "test_id": test["id"],
            "client_id": clean_client_id(body.get("clientId")),
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
        client_id = clean_client_id(self.get_query_argument("clientId", ""))
        if not client_id:
            return self.send_json({"items": []})
        try:
            items = await in_thread(STORE.list_history, client_id, 20)
        except Exception:
            log.exception("Could not load history")
            items = []
        self.send_json({"items": items})


class AdminStatsHandler(BaseHandler):
    async def get(self):
        self.require_admin()
        stats = await in_thread(STORE.stats)
        stats["storage"] = STORE.name
        stats["tests"] = len(await in_thread(STORE.list_tests))
        self.send_json(stats)


class AdminRefreshHandler(BaseHandler):
    async def post(self):
        self.require_admin()
        STORE.refresh()
        tests = await in_thread(STORE.list_tests)
        self.send_json({"reloaded": len(tests)})


class ApiNotFoundHandler(BaseHandler):
    def prepare(self):
        self.send_error_json(404, "Endpoint not found")


class StaticHandler(tornado.web.StaticFileHandler):
    """Serves public/ with security headers; always revalidates so deploys show up immediately."""

    def set_default_headers(self):
        for k, v in SECURITY_HEADERS.items():
            self.set_header(k, v)

    def set_extra_headers(self, path):
        self.set_header("Cache-Control", "no-cache")


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
            (r"/api/.*", ApiNotFoundHandler),
            (r"/(.*)", StaticHandler, {"path": PUBLIC_DIR, "default_filename": "index.html"}),
        ],
        compress_response=True,
    )


def main():
    tests = STORE.list_tests()
    counts = collections.Counter(t.get("module") for t in tests)
    app = make_app()
    app.listen(PORT, address="0.0.0.0", max_body_size=MAX_BODY_BYTES)
    log.info("%s running on http://0.0.0.0:%d (storage=%s, AI marking=%s)",
             SITE_NAME, PORT, STORE.name, "on" if writing.ai_configured() else "off")
    log.info("Loaded %d reading, %d listening and %d writing tests",
             counts["reading"], counts["listening"], counts["writing"])
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    if sys.version_info < (3, 10):
        sys.exit("Python 3.10 or newer is required.")
    main()
