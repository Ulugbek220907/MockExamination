#!/usr/bin/env python3
"""
Automated tests for content, scoring, writing assessment and the HTTP API.

    python scripts/test_app.py            # run everything
    python -m unittest scripts.test_app   # same, via unittest

Uses only the standard library plus tornado (already a dependency).
The AI examiner is tested against a fake Claude client, so no API key is needed.
"""

import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Isolate the test database and make sure no real credentials are used.
_TMP = tempfile.mkdtemp()
os.environ["SQLITE_PATH"] = os.path.join(_TMP, "test.sqlite3")
os.environ["ADMIN_TOKEN"] = "test-admin-token"
for var in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "ANTHROPIC_API_KEY"):
    os.environ.pop(var, None)

from tornado.testing import AsyncHTTPTestCase  # noqa: E402

from mockexam import content, scoring, storage, writing  # noqa: E402
import server  # noqa: E402

TESTS = storage.load_local_tests()
READING = [t for t in TESTS if t["module"] == "reading"]
WRITING = [t for t in TESTS if t["module"] == "writing"]
CLIENT_ID = "123e4567-e89b-12d3-a456-426614174000"


def perfect_answers(test):
    answers = {}
    for _, group in content.iter_groups(test):
        if group["type"] == "choose_multiple":
            for q, letter in zip(group["questions"], group["answer"]):
                answers[str(q["number"])] = letter
        else:
            for q in group["questions"]:
                a = q["answer"]
                answers[str(q["number"])] = a[0] if isinstance(a, list) else a
    return answers


def contains_key(obj, key):
    if isinstance(obj, dict):
        return key in obj or any(contains_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(contains_key(v, key) for v in obj)
    return False


class ContentTests(unittest.TestCase):
    def test_expected_tests_present(self):
        self.assertGreaterEqual(len(READING), 3)
        self.assertGreaterEqual(len(WRITING), 4)

    def test_all_content_valid(self):
        for t in READING:
            self.assertEqual(content.validate_reading_test(t), [], t["id"])
        for t in WRITING:
            self.assertEqual(content.validate_writing_test(t), [], t["id"])

    def test_no_cambridge_material_served(self):
        for t in TESTS:
            self.assertNotIn("cambridge", t["id"].lower())
            self.assertNotIn("Cambridge", t["title"])

    def test_public_reading_view_has_no_answers(self):
        for t in READING:
            public = content.public_reading_test(t)
            for key in ("answer", "explanation", "reference"):
                self.assertFalse(contains_key(public, key), f"{t['id']} leaks '{key}'")
            # original untouched
            self.assertTrue(contains_key(t, "answer"))

    def test_public_writing_view_has_no_model_answers(self):
        for t in WRITING:
            public = content.public_writing_test(t)
            self.assertFalse(contains_key(public, "modelAnswer"))
            self.assertFalse(contains_key(public, "examinerNotes"))


class ReadingScoringTests(unittest.TestCase):
    def test_band_table(self):
        expected = {40: 9.0, 39: 9.0, 38: 8.5, 35: 8.0, 33: 7.5, 30: 7.0, 27: 6.5, 23: 6.0,
                    19: 5.5, 15: 5.0, 13: 4.5, 10: 4.0, 8: 3.5, 6: 3.0, 4: 2.5, 0: 2.0}
        for raw, band in expected.items():
            self.assertEqual(scoring.band_for_raw_score(raw), band, raw)

    def test_perfect_and_empty_scores(self):
        for t in READING:
            r = scoring.evaluate_reading(t, perfect_answers(t))
            self.assertEqual((r["rawScore"], r["bandScore"]), (40, 9.0), t["id"])
            r = scoring.evaluate_reading(t, {})
            self.assertEqual(r["rawScore"], 0)
            self.assertEqual(len(r["results"]), 40)

    def test_choose_two_counts_each_letter_once(self):
        t = next(x for x in READING if x["id"] == "academic-reading-01")
        # Correct letters are C and E for Q21-22.
        self.assertEqual(scoring.evaluate_reading(t, {"21": "C", "22": "C"})["rawScore"], 1)
        self.assertEqual(scoring.evaluate_reading(t, {"21": "E", "22": "C"})["rawScore"], 2)
        self.assertEqual(scoring.evaluate_reading(t, {"21": "A", "22": "E"})["rawScore"], 1)

    def test_completion_answers_are_normalised(self):
        t = next(x for x in READING if x["id"] == "academic-reading-03")
        r = scoring.evaluate_reading(t, {"3": "  stewart ISLAND. ", "5": "the rimu", "4": "fifty-one", "31": "Opportunity Costs"})
        marks = {x["number"]: x["isCorrect"] for x in r["results"]}
        self.assertTrue(marks[3] and marks[5] and marks[4] and marks[31])

    def test_wrong_and_blank_answers(self):
        t = next(x for x in READING if x["id"] == "academic-reading-02")
        r = scoring.evaluate_reading(t, {"1": "national parks", "7": "FALSE"})
        marks = {x["number"]: x["isCorrect"] for x in r["results"]}
        self.assertFalse(marks[1])
        self.assertFalse(marks[7])

    def test_word_list_answer_shows_word(self):
        t = next(x for x in READING if x["id"] == "academic-reading-01")
        r = scoring.evaluate_reading(t, {"23": "C"})
        q23 = next(x for x in r["results"] if x["number"] == 23)
        self.assertTrue(q23["isCorrect"])
        self.assertEqual(q23["correctAnswer"], "C (flat)")
        self.assertIn("______", q23["prompt"])


class WritingTests(unittest.TestCase):
    def test_rounding(self):
        self.assertEqual(writing.round_to_half_band(6.25), 6.5)
        self.assertEqual(writing.round_to_half_band(6.2), 6.0)
        self.assertEqual(writing.round_to_half_band(6.75), 7.0)
        self.assertEqual(writing.round_to_half_band(6.5), 6.5)
        self.assertEqual(writing.overall_writing_band(6.0, 7.0), 6.5)  # 6.67 → 6.5
        self.assertEqual(writing.overall_writing_band(5.5, 7.0), 6.5)  # 6.5
        self.assertEqual(writing.overall_writing_band(6.5, 7.0), 7.0)  # 6.83 → 7.0

    def test_analysis_flags_problems(self):
        a = writing.analyse_text("I don't think so. It's gonna be ok", 2, 250)
        texts = " ".join(c["text"] for c in a["checks"] if not c["ok"])
        self.assertIn("Under length", texts)
        self.assertIn("Contractions", texts)
        self.assertIn("informal", texts)

    def test_model_answers_pass_checks(self):
        for t in WRITING:
            for task in t["tasks"]:
                a = writing.analyse_text(task["modelAnswer"], task["taskNumber"], task["minWords"])
                failed = [c["text"] for c in a["checks"] if not c["ok"]]
                self.assertEqual(failed, [], f"{t['id']} task {task['taskNumber']}")

    def test_ai_assessment_with_fake_client(self):
        t = WRITING[0]
        payload = {
            "criteria": {k: {"band": b, "feedback": f"{k} feedback"} for k, b in
                         (("task", 6), ("coherence_cohesion", 7), ("lexical_resource", 6), ("grammar", 6))},
            "summary": "Solid response.",
            "strengths": ["Clear overview"],
            "improvements": ["Add more data"],
            "corrections": [{"original": "peoples", "corrected": "people", "explanation": "Plural"}],
        }
        calls = []

        class FakeMessages:
            async def create(self, **kwargs):
                calls.append(kwargs)
                return types.SimpleNamespace(
                    stop_reason="end_turn", model="claude-opus-5",
                    content=[types.SimpleNamespace(type="thinking", thinking=""),
                             types.SimpleNamespace(type="text", text=json.dumps(payload))])

        class FakeClient:
            def __init__(self, **kwargs):
                self.beta = types.SimpleNamespace(messages=FakeMessages())

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

        essay = "word " * 300
        responses = {1: essay, 2: essay}
        analyses = {n: writing.analyse_text(responses[n], n, 150 if n == 1 else 250) for n in (1, 2)}
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
                mock.patch("anthropic.AsyncAnthropic", FakeClient):
            result = asyncio.run(writing.assess_with_claude(t, responses, analyses))

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["fallbacks"], "default")
        self.assertEqual(calls[0]["output_config"]["format"]["type"], "json_schema")
        self.assertIn("RESPONSE>>>", calls[0]["messages"][0]["content"])
        self.assertEqual(result["tasks"]["1"]["band"], 6.5)  # (6+7+6+6)/4 = 6.25 → 6.5
        self.assertEqual(result["overallBand"], 6.5)
        self.assertEqual(result["tasks"]["2"]["criteria"]["task"]["label"], "Task Response")

    def test_ai_refusal_raises(self):
        class FakeMessages:
            async def create(self, **kwargs):
                return types.SimpleNamespace(stop_reason="refusal", model="x", content=[])

        class FakeClient:
            def __init__(self, **kwargs):
                self.beta = types.SimpleNamespace(messages=FakeMessages())

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

        t = WRITING[0]
        essay = "word " * 300
        analyses = {n: writing.analyse_text(essay, n, 150) for n in (1, 2)}
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
                mock.patch("anthropic.AsyncAnthropic", FakeClient):
            with self.assertRaises(writing.AssessmentUnavailable):
                asyncio.run(writing.assess_with_claude(t, {1: essay, 2: essay}, analyses))

    def test_blank_task_not_sent_to_ai(self):
        result = asyncio.run(writing._not_attempted(1, 0))
        self.assertEqual(result["band"], 0.0)

    def test_rate_limiter(self):
        limiter = server.AiLimiter(per_ip_per_hour=2, daily_limit=3)
        self.assertIsNone(limiter.try_acquire("1.1.1.1"))
        self.assertIsNone(limiter.try_acquire("1.1.1.1"))
        self.assertIsNotNone(limiter.try_acquire("1.1.1.1"))
        self.assertIsNone(limiter.try_acquire("2.2.2.2"))
        self.assertIsNotNone(limiter.try_acquire("3.3.3.3"))  # daily cap


class SupabaseStoreTests(unittest.TestCase):
    """Runs SupabaseStore against a tiny fake PostgREST server and checks the requests it sends."""

    @classmethod
    def setUpClass(cls):
        import http.server
        import threading

        cls.requests = []
        test_row = {"content": READING[0]}

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _record(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                cls.requests.append({"method": self.command, "path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})

            def _send(self, payload, extra=None):
                raw = json.dumps(payload).encode()
                self.send_response(200 if self.command == "GET" else 201)
                self.send_header("Content-Type", "application/json")
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                self._record()
                if self.path.startswith("/rest/v1/tests"):
                    self._send([test_row])
                elif "limit=1" in self.path:
                    self._send([], {"Content-Range": "0-0/7"})
                elif self.path.startswith("/rest/v1/reading_attempts"):
                    self._send([{"id": 5, "test_id": "academic-reading-01", "raw_score": 30, "total_questions": 40,
                                 "band_score": 7.0, "time_spent_seconds": 100, "mode": "exam",
                                 "created_at": "2026-01-01T00:00:00Z"}])
                else:
                    self._send([])

            def do_POST(self):
                self._record()
                if self.path.startswith("/rest/v1/tests"):
                    self.send_response(201)
                    self.end_headers()
                else:
                    self._send([{"id": 42}])

        cls.httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.store = storage.SupabaseStore(f"http://127.0.0.1:{cls.httpd.server_port}", "service-key")

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def test_reads_and_writes(self):
        tests = self.store.list_tests()
        self.assertEqual(tests[0]["id"], READING[0]["id"])
        get = self.requests[-1]
        self.assertEqual(get["headers"]["apikey"], "service-key")
        self.assertEqual(get["headers"]["authorization"], "Bearer service-key")
        self.assertIn("is_published=eq.true", get["path"])

        self.store.upsert_test(WRITING[0])
        post = self.requests[-1]
        self.assertIn("on_conflict=id", post["path"])
        self.assertIn("merge-duplicates", post["headers"]["prefer"])
        self.assertEqual(post["body"][0]["module"], "writing")

        new_id = self.store.save_reading_attempt({"test_id": "academic-reading-01", "raw_score": 30,
                                                  "total_questions": 40, "band_score": 7.0})
        self.assertEqual(new_id, 42)
        self.assertEqual(self.store.save_writing_submission({"test_id": "academic-writing-01"}), 42)

        items = self.store.list_history(CLIENT_ID)
        self.assertEqual(items[0]["bandScore"], 7.0)
        self.assertIn(f"client_id=eq.{CLIENT_ID}", self.requests[-2]["path"])

        self.assertEqual(self.store.stats()["readingAttempts"], 7)

    def test_falls_back_to_local_content_when_unreachable(self):
        dead = storage.SupabaseStore("http://127.0.0.1:9", "k")
        self.assertEqual(len(dead.list_tests()), len(TESTS))


class ApiTests(AsyncHTTPTestCase):
    def get_app(self):
        return server.make_app()

    def get_json(self, path):
        r = self.fetch(path)
        return r.code, json.loads(r.body)

    def post_json(self, path, body):
        r = self.fetch(path, method="POST", body=json.dumps(body))
        return r.code, json.loads(r.body)

    def test_health_and_config(self):
        code, data = self.get_json("/api/health")
        self.assertEqual((code, data["status"]), (200, "healthy"))
        code, data = self.get_json("/api/config")
        self.assertFalse(data["aiMarking"])

    def test_tests_list(self):
        code, data = self.get_json("/api/tests")
        self.assertEqual(code, 200)
        modules = {t["module"] for t in data["tests"]}
        self.assertEqual(modules, {"reading", "writing"})
        self.assertEqual(data["modules"]["writing"]["status"], "active")

    def test_single_test_has_no_answers(self):
        code, data = self.get_json("/api/tests/academic-reading-01")
        self.assertEqual(code, 200)
        self.assertFalse(contains_key(data, "answer"))
        code, data = self.get_json("/api/tests/academic-writing-01")
        self.assertFalse(contains_key(data, "modelAnswer"))
        code, _ = self.get_json("/api/tests/does-not-exist")
        self.assertEqual(code, 404)

    def test_reading_submit_and_history(self):
        t = READING[0]
        code, data = self.post_json(f"/api/reading/{t['id']}/submit", {
            "answers": perfect_answers(t), "candidateName": "<b>Tester</b>",
            "clientId": CLIENT_ID, "timeSpentSeconds": 1234, "mode": "practice"})
        self.assertEqual(code, 200)
        self.assertEqual((data["rawScore"], data["bandScore"], data["mode"]), (40, 9.0, "practice"))
        self.assertTrue(data["results"][0]["explanation"])
        code, hist = self.get_json(f"/api/history?clientId={CLIENT_ID}")
        self.assertTrue(any(i["testId"] == t["id"] for i in hist["items"]))
        code, hist = self.get_json("/api/history?clientId=not-a-uuid")
        self.assertEqual(hist["items"], [])

    def test_writing_submit_without_ai(self):
        t = WRITING[0]
        code, data = self.post_json(f"/api/writing/{t['id']}/submit", {
            "responses": {"1": t["tasks"][0]["modelAnswer"], "2": "Too short."},
            "clientId": CLIENT_ID, "requestAssessment": True})
        self.assertEqual(code, 200)
        self.assertEqual(data["assessmentStatus"], "not_configured")
        self.assertIsNone(data["assessment"])
        self.assertTrue(data["tasks"][0]["modelAnswer"])
        self.assertGreater(data["tasks"][0]["analysis"]["wordCount"], 150)

    def test_module_mismatch_and_bad_input(self):
        code, _ = self.post_json("/api/reading/academic-writing-01/submit", {})
        self.assertEqual(code, 404)
        r = self.fetch("/api/reading/academic-reading-01/submit", method="POST", body="not json")
        self.assertEqual(r.code, 400)
        code, _ = self.post_json("/api/writing/academic-writing-01/submit", {"responses": {"1": "x" * 20000}})
        self.assertEqual(code, 413)

    def test_admin_requires_token(self):
        self.assertEqual(self.fetch("/api/admin/stats").code, 401)
        r = self.fetch("/api/admin/stats", headers={"Authorization": "Bearer test-admin-token"})
        self.assertEqual(r.code, 200)
        self.assertIn("readingAttempts", json.loads(r.body))

    def test_static_and_security_headers(self):
        r = self.fetch("/")
        self.assertEqual(r.code, 200)
        self.assertIn(b"<html", r.body)
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.fetch("/api/unknown").code, 404)
        # content/ and data/ must never be served
        self.assertEqual(self.fetch("/content/reading/academic-reading-01.json").code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
