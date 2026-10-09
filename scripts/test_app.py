#!/usr/bin/env python3
"""
Automated tests for content, scoring (reading and listening), writing
assessment, storage and the HTTP API.

    python scripts/test_app.py            # run everything
    python -m unittest scripts.test_app   # same, via unittest

Uses only the standard library plus tornado (already a dependency).
The AI examiner is tested against a fake Claude client, so no API key is needed.
"""

import asyncio
import datetime
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
for var in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_APP_SECRET", "ANTHROPIC_API_KEY",
            "PAYME_MERCHANT_ID", "PAYME_KEY", "CLICK_SERVICE_ID", "CLICK_MERCHANT_ID", "CLICK_SECRET_KEY"):
    os.environ.pop(var, None)
# Accounts: development sign-in codes, one admin, and card-transfer payments switched on.
os.environ["AUTH_DEV_CODES"] = "1"
os.environ["ADMIN_EMAILS"] = "owner@example.com"
os.environ["PAYMENT_CARD_NUMBER"] = "8600 0000 0000 0000"

from tornado.testing import AsyncHTTPTestCase  # noqa: E402

from mockexam import accounts, api, billing, checks, content, notify, scoring, speaking, storage, writing  # noqa: E402
from mockexam.db import SqliteDb, iso, now  # noqa: E402
from mockexam.files import LocalFiles  # noqa: E402
import server  # noqa: E402

TESTS = storage.load_local_tests()
READING = [t for t in TESTS if t["module"] == "reading"]
LISTENING = [t for t in TESTS if t["module"] == "listening"]
WRITING = [t for t in TESTS if t["module"] == "writing"]
SPEAKING = [t for t in TESTS if t["module"] == "speaking"]
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
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
        self.assertGreaterEqual(len(LISTENING), 1)
        self.assertGreaterEqual(len(WRITING), 4)

    def test_all_content_valid(self):
        for t in TESTS:
            self.assertEqual(content.validate_test(t, public_dir=PUBLIC_DIR), [], t["id"])

    def test_listening_audio_files_exist(self):
        for t in LISTENING:
            for part in t["parts"]:
                path = os.path.join(PUBLIC_DIR, part["audio"]["src"])
                self.assertTrue(os.path.getsize(path) > 100_000, path)
                self.assertGreater(part["audio"]["duration"], 120)

    def test_public_listening_view_hides_answers_and_transcript(self):
        for t in LISTENING:
            public = content.public_listening_test(t)
            for key in ("answer", "explanation", "cue", "script", "speakers", "pronunciations"):
                self.assertFalse(contains_key(public, key), f"{t['id']} leaks '{key}'")
            self.assertTrue(all(p["audio"]["src"].endswith(".mp3") for p in public["parts"]))
            self.assertTrue(contains_key(t, "script"))  # original untouched

    def test_listening_cues_located_in_the_right_part(self):
        for t in LISTENING:
            cues = content.locate_listening_cues(t)
            self.assertEqual(sorted(cues), list(range(1, 41)))
            for pi, part in enumerate(t["parts"]):
                for _, _, q in ((part, g, q) for g in part["groups"] for q in g["questions"]):
                    self.assertEqual(cues[q["number"]]["part"], pi)

    def test_validator_catches_missing_answer_in_transcript(self):
        t = json.loads(json.dumps(LISTENING[0]))
        t["parts"][0]["groups"][0]["questions"][0]["answer"] = ["Smith"]
        errors = content.validate_listening_test(t)
        self.assertTrue(any("Q1" in e and "transcript" in e for e in errors), errors)

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

    def test_speaking_tests_and_examiner_audio(self):
        self.assertGreaterEqual(len(SPEAKING), 3)
        for t in SPEAKING:
            keys = [q["key"] for _, q in content.speaking_questions(t)]
            self.assertEqual(len(keys), len(set(keys)))
            self.assertEqual(content.summarize_test(t)["totalQuestions"], len(keys))
            for _, q in content.speaking_questions(t):
                self.assertTrue(os.path.getsize(os.path.join(PUBLIC_DIR, q["audio"]["src"])) > 1000, q["key"])
        broken = json.loads(json.dumps(SPEAKING[0]))
        broken["parts"][1]["cueCard"]["points"] = []
        broken["parts"][0]["questions"][1]["key"] = broken["parts"][0]["questions"][0]["key"]
        errors = content.validate_speaking_test(broken)
        self.assertTrue(any("cue card" in e for e in errors) and any("duplicate" in e for e in errors), errors)

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


class ListeningScoringTests(unittest.TestCase):
    def test_band_table(self):
        table = scoring.LISTENING_BANDS
        cases = {40: 9.0, 39: 9.0, 37: 8.5, 35: 8.0, 32: 7.5, 30: 7.0, 26: 6.5, 23: 6.0, 18: 5.5, 16: 5.0, 0: 2.0}
        for raw, band in cases.items():
            self.assertEqual(scoring.band_for_raw_score(raw, table), band, raw)

    def test_perfect_and_empty_scores(self):
        for t in LISTENING:
            r = scoring.evaluate_listening(t, perfect_answers(t))
            self.assertEqual((r["rawScore"], r["bandScore"]), (40, 9.0))
            self.assertEqual(sum(p["correct"] for p in r["partBreakdown"].values()), 40)
            r = scoring.evaluate_listening(t, {})
            self.assertEqual((r["rawScore"], r["bandScore"]), (0, 2.0))

    def test_answer_variants(self):
        t = LISTENING[0]
        r = scoring.evaluate_listening(t, {"1": "kowalski", "4": "six", "5": "off peak", "9": "photograph",
                                           "36": "belly", "40": "a jellyfish", "2": "24", "8": "pilate"})
        marks = {x["number"]: x["isCorrect"] for x in r["results"]}
        for n in (1, 4, 5, 9, 36, 40):
            self.assertTrue(marks[n], n)
        self.assertFalse(marks[2])   # 24 is the distractor, 42 is correct
        self.assertFalse(marks[8])   # spelling counts
        self.assertEqual(r["rawScore"], 6)

    def test_results_carry_transcript_and_cues(self):
        t = LISTENING[0]
        r = scoring.evaluate_listening(t, {})
        self.assertEqual(len(r["transcript"]), 4)
        self.assertTrue(all(p["lines"] and p["audio"]["src"] for p in r["transcript"]))
        for row in r["results"]:
            self.assertIsNotNone(row["cue"], row["number"])
            self.assertGreaterEqual(row["cue"]["start"], 0)
            self.assertIn("partNumber", row)
        q17 = next(x for x in r["results"] if x["number"] == 17)
        self.assertTrue(q17["correctAnswer"].startswith("C ("))  # option text shown with the letter


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
                a = writing.analyse_text(task["modelAnswer"], task["taskNumber"], task["minWords"], task.get("essayType"))
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
    """Runs SupabaseStore against a tiny fake Supabase REST server and checks the RPC calls it makes."""

    SECRET = "s" * 48

    @classmethod
    def setUpClass(cls):
        import http.server
        import threading

        cls.requests = []
        secret = cls.SECRET

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, payload):
                raw = json.dumps(payload).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else {}
                fn = self.path.rsplit("/", 1)[-1]
                cls.requests.append({"fn": fn, "path": self.path, "body": body,
                                     "headers": {k.lower(): v for k, v in self.headers.items()}})
                if body.get("p_key") != secret:
                    return self._send(403, {"code": "28000", "message": "invalid app key"})
                responses = {
                    "app_list_tests": [READING[0]],
                    "app_upsert_test": None,
                    "app_save_reading_attempt": 42,
                    "app_save_listening_attempt": 44,
                    "app_save_writing_submission": 43,
                    "app_history": {"reading": [{"id": 5, "test_id": "academic-reading-01", "raw_score": 30,
                                                 "total_questions": 40, "band_score": 7.0, "time_spent_seconds": 100,
                                                 "mode": "exam", "created_at": "2026-01-01T00:00:00Z"}],
                                    "listening": [{"id": 6, "test_id": "listening-01", "raw_score": 33,
                                                   "total_questions": 40, "band_score": 7.5, "time_spent_seconds": 1500,
                                                   "mode": "exam", "created_at": "2026-01-02T00:00:00Z"}],
                                    "writing": []},
                    "app_stats": {"readingAttempts": 7, "writingSubmissions": 2},
                }
                self._send(200, responses.get(fn))

        cls.httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_port}"
        cls.store = storage.SupabaseStore(cls.base, "sb_publishable_test", cls.SECRET)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def test_rpc_calls(self):
        tests = self.store.list_tests()
        self.assertEqual(tests[0]["id"], READING[0]["id"])
        call = self.requests[-1]
        self.assertEqual(call["path"], "/rest/v1/rpc/app_list_tests")
        self.assertEqual(call["headers"]["apikey"], "sb_publishable_test")
        self.assertNotIn("authorization", call["headers"])  # new-style keys only go in `apikey`

        self.store.upsert_test(WRITING[0])
        self.assertEqual(self.requests[-1]["body"]["p_test"]["id"], WRITING[0]["id"])

        self.assertEqual(self.store.save_reading_attempt({"test_id": "academic-reading-01"}), 42)
        self.assertEqual(self.store.save_writing_submission({"test_id": "academic-writing-01"}), 43)
        self.assertEqual(self.store.save_listening_attempt({"test_id": "listening-01"}), 44)
        self.assertEqual(self.requests[-1]["fn"], "app_save_listening_attempt")

        items = self.store.list_history(CLIENT_ID)
        self.assertEqual((items[0]["module"], items[0]["bandScore"]), ("listening", 7.5))  # newest first
        self.assertEqual((items[1]["module"], items[1]["bandScore"]), ("reading", 7.0))
        self.assertEqual(self.requests[-1]["body"]["p_client"], CLIENT_ID)
        self.assertEqual(self.store.stats()["readingAttempts"], 7)

    def test_jwt_keys_also_sent_as_bearer(self):
        store = storage.SupabaseStore(self.base, "eyJ.fake.jwt", self.SECRET)
        store.stats()
        self.assertEqual(self.requests[-1]["headers"]["authorization"], "Bearer eyJ.fake.jwt")

    def test_wrong_secret_raises_and_content_falls_back(self):
        bad = storage.SupabaseStore(self.base, "k", "wrong" * 10)
        with self.assertRaises(storage.SupabaseError):
            bad.save_reading_attempt({})
        self.assertEqual(len(bad.list_tests()), len(TESTS))  # bundled content still served

    def test_falls_back_to_local_content_when_unreachable(self):
        dead = storage.SupabaseStore("http://127.0.0.1:9", "k", self.SECRET)
        self.assertEqual(len(dead.list_tests()), len(TESTS))

    def _wait_for_reload(self, store):
        import time
        for _ in range(100):
            if not store._refreshing:
                return
            time.sleep(0.02)

    def test_stale_tests_served_while_reloading_in_background(self):
        store = storage.SupabaseStore(self.base, "k", self.SECRET)
        first = store.list_tests()
        calls = sum(r["fn"] == "app_list_tests" for r in self.requests)
        self.assertIs(store.list_tests(), first)  # fresh cache: no call
        self.assertEqual(sum(r["fn"] == "app_list_tests" for r in self.requests), calls)
        store._cache_at -= store.CACHE_SECONDS + 1
        self.assertIs(store.list_tests(), first)  # stale cache is returned at once...
        self._wait_for_reload(store)  # ...while it reloads in the background
        self.assertEqual(sum(r["fn"] == "app_list_tests" for r in self.requests), calls + 1)
        self.assertIsNot(store.list_tests(), first)

    def test_failed_background_reload_keeps_previous_tests(self):
        store = storage.SupabaseStore(self.base, "k", self.SECRET)
        first = store.list_tests()
        store.secret = "wrong" * 10
        store._cache_at -= store.CACHE_SECONDS + 1
        store.list_tests()
        self._wait_for_reload(store)
        self.assertIs(store.list_tests(), first)


class PoolTests(unittest.TestCase):
    """mockexam.pool keeps one connection per thread open and behaves like urllib on errors."""

    @classmethod
    def setUpClass(cls):
        import http.server
        import threading

        cls.ports = []

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                cls.ports.append(self.client_address[1])
                code = 404 if self.path == "/missing" else 200
                raw = json.dumps({"path": self.path}).encode()
                self.send_response(code)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                if self.path == "/drop":  # close the kept-alive connection without saying so
                    self.close_connection = True

        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def post(self, path):
        import urllib.request
        from mockexam import pool
        req = urllib.request.Request(self.base + path, data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json"})
        with pool.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())

    def test_reuses_connection_and_recovers_when_server_closes_it(self):
        from mockexam import pool
        pool._connections().clear()
        del self.ports[:]
        self.assertEqual(self.post("/a?x=1"), (200, {"path": "/a?x=1"}))
        self.post("/b")
        self.post("/c")
        self.assertEqual(len(set(self.ports)), 1)
        self.post("/drop")
        self.assertEqual(self.post("/d")[0], 200)  # retried on a new connection
        self.assertEqual(len(set(self.ports)), 2)
        self.assertEqual(len(pool._connections()), 1)

    def test_http_errors_raise_like_urllib(self):
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post("/missing")
        self.assertEqual(ctx.exception.code, 404)
        self.assertIn(b"/missing", ctx.exception.read())
        import urllib.request
        from mockexam import pool
        with self.assertRaises(urllib.error.URLError):
            pool.urlopen(urllib.request.Request("http://127.0.0.1:9/x", data=b"", method="POST"), timeout=2)


class ApiTests(AsyncHTTPTestCase):
    def get_app(self):
        return server.make_app()

    def get_json(self, path):
        r = self.fetch(path)
        return r.code, json.loads(r.body)

    def post_json(self, path, body, headers=None):
        r = self.fetch(path, method="POST", body=json.dumps(body),
                       headers={"Content-Type": "application/json", **(headers or {})})
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
        self.assertEqual(modules, {"reading", "listening", "writing", "speaking"})
        self.assertTrue(all(m["status"] == "active" for m in data["modules"].values()))
        listening = next(t for t in data["tests"] if t["module"] == "listening")
        self.assertEqual([p["number"] for p in listening["parts"]], [1, 2, 3, 4])

    def test_single_test_has_no_answers(self):
        code, data = self.get_json("/api/tests/academic-reading-01")
        self.assertEqual(code, 200)
        self.assertFalse(contains_key(data, "answer"))
        code, data = self.get_json("/api/tests/academic-writing-01")
        self.assertFalse(contains_key(data, "modelAnswer"))
        code, data = self.get_json("/api/tests/listening-01")
        self.assertEqual(code, 200)
        for key in ("answer", "script", "cue", "explanation"):
            self.assertFalse(contains_key(data, key), key)
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

    def test_listening_submit_and_history(self):
        t = LISTENING[0]
        answers = perfect_answers(t)
        answers["2"] = "24"
        code, data = self.post_json(f"/api/listening/{t['id']}/submit", {
            "answers": answers, "candidateName": "Tester", "clientId": CLIENT_ID,
            "timeSpentSeconds": 1500, "mode": "exam"})
        self.assertEqual(code, 200)
        self.assertEqual((data["rawScore"], data["bandScore"]), (39, 9.0))
        self.assertIsNotNone(data["attemptId"])
        self.assertEqual(len(data["transcript"]), 4)
        self.assertIn("?v=", data["transcript"][0]["audio"]["src"])
        self.assertNotIn("?v=", t["parts"][0]["audio"]["src"])  # stored test left untouched
        code, hist = self.get_json(f"/api/history?clientId={CLIENT_ID}")
        self.assertTrue(any(i["module"] == "listening" and i["testId"] == t["id"] for i in hist["items"]))
        code, _ = self.post_json("/api/listening/academic-reading-01/submit", {})
        self.assertEqual(code, 404)
        code, _ = self.post_json(f"/api/reading/{t['id']}/submit", {})
        self.assertEqual(code, 404)

    def test_audio_served_with_ranges(self):
        code, data = self.get_json(f"/api/tests/{LISTENING[0]['id']}")
        src = data["parts"][0]["audio"]["src"]
        self.assertTrue(src.startswith(LISTENING[0]["parts"][0]["audio"]["src"] + "?v="))
        r = self.fetch(f"/{src}", headers={"Range": "bytes=0-1023"})
        self.assertEqual(r.code, 206)
        self.assertEqual(len(r.body), 1024)
        self.assertEqual(r.headers["Content-Type"], "audio/mpeg")
        self.assertEqual(r.headers["Cache-Control"], "private, max-age=31536000, immutable")

    def test_index_links_hashed_assets_cached_for_a_year(self):
        r = self.fetch("/")
        self.assertEqual(r.code, 200)
        self.assertEqual(r.headers["Cache-Control"], "no-cache")
        self.assertIn("Content-Security-Policy", r.headers)
        self.assertIn("Strict-Transport-Security", r.headers)
        page = r.body.decode()
        for asset in ("css/portal.css", "js/app.js", "js/exam.js", "js/account.js"):
            self.assertRegex(page, rf'"{asset}\?v=[0-9a-f]{{12}}"')
        versioned = page.split('src="', 1)[1].split('"', 1)[0]
        r = self.fetch(f"/{versioned}")
        self.assertEqual(r.code, 200)
        self.assertEqual(r.headers["Cache-Control"], "public, max-age=31536000, immutable")
        self.assertEqual(self.fetch("/js/app.js").headers["Cache-Control"], "no-cache")
        self.assertEqual(self.fetch("/", method="HEAD").code, 200)

    def test_test_list_revalidates_with_etag(self):
        r = self.fetch("/api/tests")
        self.assertEqual(r.headers["Cache-Control"], "private, no-cache")
        r = self.fetch("/api/tests", headers={"If-None-Match": r.headers["Etag"]})
        self.assertEqual(r.code, 304)

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
        r = self.fetch("/api/reading/academic-reading-01/submit", method="POST", body="not json",
                       headers={"Content-Type": "application/json"})
        self.assertEqual(r.code, 400)
        # Cross-site forms cannot post to the API (CSRF guard): JSON only.
        r = self.fetch("/api/reading/academic-reading-01/submit", method="POST", body="a=1",
                       headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(r.code, 415)
        code, _ = self.post_json("/api/writing/academic-writing-01/submit", {"responses": {"1": "x" * 20000}})
        self.assertEqual(code, 413)

    def test_admin_requires_token(self):
        self.assertEqual(self.fetch("/api/admin/stats").code, 401)
        r = self.fetch("/api/admin/stats", headers={"Authorization": "Bearer test-admin-token"})
        self.assertEqual(r.code, 200)
        stats = json.loads(r.body)
        self.assertIn("readingAttempts", stats)
        self.assertIn("listeningAttempts", stats)

    def test_static_and_security_headers(self):
        r = self.fetch("/")
        self.assertEqual(r.code, 200)
        self.assertIn(b"<html", r.body)
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.fetch("/api/unknown").code, 404)
        # content/ and data/ must never be served
        self.assertEqual(self.fetch("/content/reading/academic-reading-01.json").code, 404)


class AccountApiBase(AsyncHTTPTestCase):
    """Helpers: JSON calls with a session cookie, and signing in with development codes."""

    def get_app(self):
        return server.make_app()

    def call(self, method, path, body=None, cookie=None):
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        r = self.fetch(path, method=method, headers=headers, body=json.dumps(body) if body is not None else None,
                       allow_nonstandard_methods=True, follow_redirects=False)
        try:
            data = json.loads(r.body) if r.body else {}
        except ValueError:
            data = {}
        return r, data

    def login(self, email, client_id=None):
        api.CODE_PER_IP.hits.clear()  # every test signs in from 127.0.0.1
        r, data = self.call("POST", "/api/auth/code", {"email": email})
        self.assertEqual(r.code, 200, data)
        r, data = self.call("POST", "/api/auth/verify", {"email": email, "code": data["devCode"], "clientId": client_id})
        self.assertEqual(r.code, 200, data)
        cookie = r.headers["Set-Cookie"].split(";")[0]
        self.assertIn("HttpOnly", r.headers["Set-Cookie"])
        return cookie, data


class AccountApiTests(AccountApiBase):
    """Sign-in, locked tests, buying the plan, and a paid examiner check, all through the HTTP API."""

    def test_login_me_logout(self):
        r, data = self.call("GET", "/api/me")
        self.assertIsNone(data["user"])
        r, data = self.call("POST", "/api/auth/verify", {"email": "a@example.com", "code": "123456"})
        self.assertEqual(r.code, 400)
        cookie, data = self.login("Student.One@Example.com")
        self.assertEqual((data["user"]["email"], data["user"]["role"]), ("student.one@example.com", "student"))
        self.assertFalse(data["plan"]["active"])
        r, data = self.call("GET", "/api/me", cookie=cookie)
        self.assertEqual(data["user"]["email"], "student.one@example.com")
        r, data = self.call("POST", "/api/me", {"name": "  Aziz  Karimov "}, cookie=cookie)
        self.assertEqual(data["user"]["name"], "Aziz Karimov")
        r, _ = self.call("POST", "/api/auth/logout", {}, cookie=cookie)
        self.assertIn("mx_session=;", r.headers["Set-Cookie"].replace('""', ""))
        r, data = self.call("GET", "/api/me", cookie="mx_session=forged")
        self.assertIsNone(data["user"])

    def test_premium_tests_and_audio_are_locked(self):
        r, data = self.call("GET", "/api/tests")
        access = {t["id"]: t["access"] for t in data["tests"]}
        self.assertEqual((access["academic-reading-01"], access["academic-reading-02"]), ("free", "premium"))
        r, data = self.call("GET", "/api/tests/academic-reading-02")
        self.assertEqual((r.code, data["code"]), (401, "login_required"))
        self.assertEqual(self.fetch("/audio/listening-02/part1.mp3").code, 401)
        self.assertEqual(self.fetch("/audio/listening-01/part1.mp3", headers={"Range": "bytes=0-9"}).code, 206)
        cookie, _ = self.login("nopay@example.com")
        r, data = self.call("GET", "/api/tests/academic-reading-02", cookie=cookie)
        self.assertEqual((r.code, data["code"]), (402, "plan_required"))
        r, data = self.call("POST", "/api/reading/academic-reading-02/submit", {"answers": {}}, cookie=cookie)
        self.assertEqual(r.code, 402)
        self.assertEqual(self.fetch("/audio/listening-02/part1.mp3", headers={"Cookie": cookie}).code, 402)

    def test_buy_plan_by_card_transfer(self):
        cookie, _ = self.login("buyer@example.com")
        r, data = self.call("GET", "/api/billing")
        self.assertIn("manual", data["providers"])
        r, data = self.call("POST", "/api/orders", {"kind": "plan"}, cookie=cookie)
        order = data["order"]
        self.assertEqual((order["status"], order["amount"]), ("pending", billing.PRICES["plan"]))
        r, data = self.call("POST", f"/api/orders/{order['id']}/pay", {"method": "manual"}, cookie=cookie)
        self.assertEqual(data["manual"]["reference"], f"MX{order['id']}")
        r, data = self.call("POST", f"/api/orders/{order['id']}/pay", {"method": "payme"}, cookie=cookie)
        self.assertEqual(r.code, 400)  # Payme not configured in tests
        r, data = self.call("POST", f"/api/orders/{order['id']}/manual-paid", {}, cookie=cookie)
        self.assertEqual(data["order"]["status"], "awaiting_confirmation")
        # Someone else's order is invisible.
        other, _ = self.login("other@example.com")
        r, _ = self.call("POST", f"/api/orders/{order['id']}/manual-paid", {}, cookie=other)
        self.assertEqual(r.code, 404)
        # Students cannot use admin endpoints; the owner can.
        r, _ = self.call("GET", "/api/admin/orders", cookie=cookie)
        self.assertEqual(r.code, 403)
        admin, data = self.login("owner@example.com")
        self.assertEqual(data["user"]["role"], "admin")
        r, data = self.call("GET", "/api/admin/orders?status=awaiting_confirmation", cookie=admin)
        self.assertTrue(any(o["id"] == order["id"] and o["userEmail"] == "buyer@example.com" for o in data["orders"]))
        r, data = self.call("POST", f"/api/admin/orders/{order['id']}/confirm", {}, cookie=admin)
        self.assertEqual(data["order"]["status"], "paid")
        r, data = self.call("GET", "/api/me", cookie=cookie)
        self.assertTrue(data["plan"]["active"])
        r, _ = self.call("GET", "/api/tests/academic-reading-02", cookie=cookie)
        self.assertEqual(r.code, 200)
        self.assertEqual(self.fetch("/audio/listening-02/part1.mp3", headers={"Cookie": cookie, "Range": "bytes=0-9"}).code, 206)
        # Admin can also give plan days directly.
        r, data = self.call("POST", "/api/admin/plan", {"email": "other@example.com", "days": 7}, cookie=admin)
        self.assertTrue(data["plan"]["active"])

    def test_anonymous_attempts_join_the_account(self):
        client = "0f3a5c2e-1111-4222-8333-944455556666"
        r, data = self.call("POST", "/api/reading/academic-reading-01/submit",
                            {"answers": {}, "clientId": client, "candidateName": "Anon"})
        self.assertEqual(r.code, 200)
        cookie, _ = self.login("claimer@example.com", client_id=client)
        r, data = self.call("GET", "/api/history", cookie=cookie)
        self.assertEqual(len(data["items"]), 1)

    def test_progress_points(self):
        cookie, _ = self.login("progress@example.com")
        r, data = self.call("GET", "/api/progress")
        self.assertEqual(r.code, 401)
        t = READING[0]
        self.call("POST", f"/api/reading/{t['id']}/submit", {"answers": perfect_answers(t), "mode": "exam"}, cookie=cookie)
        self.call("POST", f"/api/reading/{t['id']}/submit", {"answers": {}, "mode": "practice"}, cookie=cookie)
        w = WRITING[0]
        r, data = self.call("POST", f"/api/writing/{w['id']}/submit", {"responses": {"1": "Short.", "2": "Short."}}, cookie=cookie)
        r, data = self.call("GET", "/api/progress", cookie=cookie)
        # Practice is left out; writing without an AI or examiner band has no score yet.
        self.assertEqual([(p["module"], p["band"], p["source"]) for p in data["points"]], [("reading", 9.0, "auto")])
        profile = accounts.find_profile_by_email(server.STORE.db, "progress@example.com")
        server.STORE.db.insert("checks", {"order_id": 990001, "kind": "writing", "student_id": profile["id"],
                                          "examiner_id": profile["id"], "submission_id": data["points"][0]["band"] and
                                          server.STORE.db.select("writing_submissions", {"user_id": profile["id"]})[0]["id"],
                                          "status": "completed", "overall_band": 6.5})
        r, data = self.call("GET", "/api/progress", cookie=cookie)
        self.assertEqual([(p["module"], p["band"], p["source"]) for p in data["points"]],
                         [("reading", 9.0, "auto"), ("writing", 6.5, "examiner")])

    def test_paid_writing_check_end_to_end(self):
        examiner, _ = self.login("examiner.one@example.com")
        admin, _ = self.login("owner@example.com")
        r, data = self.call("POST", "/api/admin/examiners", {"email": "nobody@example.com"}, cookie=admin)
        self.assertEqual(r.code, 404)
        r, data = self.call("POST", "/api/admin/examiners", {
            "email": "examiner.one@example.com", "displayName": "Dilnoza R.", "headline": "IELTS 8.5 · 7 years",
            "approved": True}, cookie=admin)
        self.assertEqual(r.code, 200, data)
        ex_id = data["examiner"]["id"]
        r, data = self.call("GET", "/api/examiners?kind=writing")
        self.assertTrue(any(e["id"] == ex_id and e["name"] == "Dilnoza R." for e in data["examiners"]))

        student, _ = self.login("writer@example.com")
        t = WRITING[0]
        r, data = self.call("POST", f"/api/writing/{t['id']}/submit",
                            {"responses": {"1": t["tasks"][0]["modelAnswer"], "2": t["tasks"][1]["modelAnswer"]}}, cookie=student)
        sub_id = data["submissionId"]
        self.assertTrue(data["signedIn"])
        r, data = self.call("POST", "/api/orders", {"kind": "writing_check", "examinerId": ex_id, "submissionId": sub_id + 999},
                            cookie=student)
        self.assertEqual(r.code, 404)  # not the student's submission
        r, data = self.call("POST", "/api/orders", {"kind": "writing_check", "examinerId": ex_id, "submissionId": sub_id},
                            cookie=student)
        order = data["order"]
        self.assertEqual(order["amount"], billing.PRICES["writing_check"])
        self.call("POST", f"/api/orders/{order['id']}/manual-paid", {}, cookie=student)
        self.call("POST", f"/api/admin/orders/{order['id']}/confirm", {}, cookie=admin)

        r, data = self.call("GET", "/api/checks", cookie=student)
        check_id = data["checks"][0]["id"]
        self.assertEqual(data["checks"][0]["status"], "waiting")
        r, _ = self.call("GET", f"/api/checks/{check_id}", cookie=self.login("stranger@example.com")[0])
        self.assertEqual(r.code, 404)
        r, data = self.call("GET", "/api/examiner/me", cookie=examiner)
        self.assertEqual([c["id"] for c in data["checks"]], [check_id])
        r, data = self.call("GET", f"/api/checks/{check_id}", cookie=examiner)
        self.assertEqual(data["check"]["viewerRole"], "examiner")
        self.assertIn("Task 1", [t["title"][:6] for t in data["check"]["submission"]["tasks"]][0] + "Task 1")
        self.assertTrue(data["check"]["submission"]["tasks"][1]["response"])
        self.call("POST", f"/api/examiner/checks/{check_id}/start", {}, cookie=examiner)
        crit = {k: {"band": 7, "feedback": "Clear."} for k in checks.WRITING_CRITERIA}
        r, data = self.call("POST", f"/api/examiner/checks/{check_id}/result", {"result": {"tasks": {
            "1": {"criteria": crit, "summary": "Good overview."},
            "2": {"criteria": dict(crit, task={"band": 8, "feedback": "Well argued."}), "strengths": "Position\nExamples"}},
            "comment": "Keep practising."}}, cookie=examiner)
        self.assertEqual(r.code, 200, data)
        self.assertEqual(data["check"]["overallBand"], 7.5)  # (7 + 2 × 7.5) / 3 = 7.33 → 7.5
        r, data = self.call("GET", f"/api/checks/{check_id}", cookie=student)
        result = data["check"]["result"]
        self.assertEqual((result["tasks"]["2"]["band"], result["tasks"]["2"]["strengths"]), (7.5, ["Position", "Examples"]))
        r, data = self.call("POST", f"/api/checks/{check_id}/rate", {"rating": 5, "review": "Very helpful"}, cookie=student)
        self.assertEqual(r.code, 200)
        r, data = self.call("POST", f"/api/checks/{check_id}/rate", {"rating": 1}, cookie=student)
        self.assertEqual(r.code, 400)  # one review per check
        r, data = self.call("GET", f"/api/examiners/{ex_id}")
        self.assertEqual((data["examiner"]["rating"], data["reviews"][0]["review"]), (5.0, "Very helpful"))


FAKE_AUDIO = b"\x1aE\xdf\xa3" + bytes(range(256)) * 8


class SpeakingApiTests(AccountApiBase):
    """Recording a Speaking test, playing it back, and a paid Speaking check."""

    def upload(self, cookie, sub_id, key, body=FAKE_AUDIO, ctype="audio/webm;codecs=opus", duration="12.5"):
        headers = {"Content-Type": ctype, "X-Duration": duration}
        if cookie:
            headers["Cookie"] = cookie
        r = self.fetch(f"/api/speaking/submissions/{sub_id}/answers/{key}", method="POST", headers=headers, body=body)
        return r, (json.loads(r.body) if r.body else {})

    def record_test(self, cookie, test, keys=None):
        r, data = self.call("POST", f"/api/speaking/{test['id']}/start", {"candidateName": "Aziz", "mode": "exam"}, cookie=cookie)
        self.assertEqual(r.code, 200, data)
        sub_id = data["submissionId"]
        for _, q in content.speaking_questions(test):
            if keys is None or q["key"] in keys:
                r, data = self.upload(cookie, sub_id, q["key"])
                self.assertEqual(r.code, 200, data)
        return sub_id

    def test_start_needs_sign_in_and_plan(self):
        r, data = self.call("POST", f"/api/speaking/{SPEAKING[0]['id']}/start", {})
        self.assertEqual((r.code, data["code"]), (401, "login_required"))
        cookie, _ = self.login("speaker.free@example.com")
        r, data = self.call("POST", f"/api/speaking/{SPEAKING[1]['id']}/start", {}, cookie=cookie)
        self.assertEqual((r.code, data["code"]), (402, "plan_required"))
        self.assertEqual(self.fetch(f"/audio/{SPEAKING[1]['id']}/p1-1.mp3", headers={"Cookie": cookie}).code, 402)
        self.assertEqual(self.fetch(f"/audio/{SPEAKING[0]['id']}/p1-1.mp3").code, 200)
        r, data = self.call("POST", "/api/speaking/academic-reading-01/start", {}, cookie=cookie)
        self.assertEqual(r.code, 404)

    def test_record_complete_and_play_back(self):
        t = SPEAKING[0]
        cookie, _ = self.login("speaker@example.com")
        r, data = self.call("POST", f"/api/speaking/{t['id']}/start", {"candidateName": "Aziz"}, cookie=cookie)
        sub_id = data["submissionId"]
        # Only audio bodies are accepted, from the owner, for real questions.
        self.assertEqual(self.upload(cookie, sub_id, "p1-1", ctype="application/json")[0].code, 415)
        self.assertEqual(self.upload(cookie, sub_id, "p1-1", ctype="text/plain")[0].code, 415)
        self.assertEqual(self.upload(None, sub_id, "p1-1")[0].code, 401)
        self.assertEqual(self.upload(self.login("intruder@example.com")[0], sub_id, "p1-1")[0].code, 404)
        self.assertEqual(self.upload(cookie, sub_id, "p9-9")[0].code, 404)
        self.assertEqual(self.upload(cookie, sub_id, "p1-1", body=b"x" * 50)[0].code, 400)
        too_big = self.upload(cookie, sub_id, "p1-1", body=b"x" * (speaking.MAX_RECORDING_BYTES + 1))[0].code
        self.assertIn(too_big, (400, 413))
        # Finishing without any answer is refused.
        r, data = self.call("POST", f"/api/speaking/submissions/{sub_id}/complete", {}, cookie=cookie)
        self.assertEqual(r.code, 400)
        r, first = self.upload(cookie, sub_id, "p1-1")
        self.assertEqual((r.code, first["recording"]["duration"]), (200, 12.5))
        r, second = self.upload(cookie, sub_id, "p1-1", body=FAKE_AUDIO + b"more")  # a retry replaces the answer
        r, _ = self.upload(cookie, sub_id, "p2-talk", ctype="audio/mp4")
        r, data = self.call("POST", f"/api/speaking/submissions/{sub_id}/complete",
                            {"notes": "place - Samarkand", "timeSpentSeconds": 700}, cookie=cookie)
        self.assertEqual(r.code, 200, data)
        view = data["submission"]
        self.assertEqual((view["status"], view["answered"], view["notes"]), ("completed", 2, "place - Samarkand"))
        self.assertEqual(view["parts"][1]["cueCard"]["topic"], t["parts"][1]["cueCard"]["topic"])
        rec = view["parts"][0]["questions"][0]["recording"]
        self.assertEqual(rec["id"], second["recording"]["id"])
        self.assertEqual(self.upload(cookie, sub_id, "p1-2")[0].code, 409)  # finished tests are closed
        # Playback: whole file and a byte range, for the owner only.
        r = self.fetch(f"/api/speaking/recordings/{rec['id']}", headers={"Cookie": cookie})
        self.assertEqual((r.code, r.body, r.headers["Content-Type"]), (200, FAKE_AUDIO + b"more", "audio/webm"))
        r = self.fetch(f"/api/speaking/recordings/{rec['id']}", headers={"Cookie": cookie, "Range": "bytes=4-7"})
        self.assertEqual((r.code, r.body, r.headers["Content-Range"]), (206, bytes(range(4)), f"bytes 4-7/{len(FAKE_AUDIO) + 4}"))
        self.assertEqual(self.fetch(f"/api/speaking/recordings/{first['recording']['id']}", headers={"Cookie": cookie}).code, 404)
        stranger = self.login("stranger2@example.com")[0]
        self.assertEqual(self.fetch(f"/api/speaking/recordings/{rec['id']}", headers={"Cookie": stranger}).code, 404)
        r, _ = self.call("GET", f"/api/speaking/submissions/{sub_id}", cookie=stranger)
        self.assertEqual(r.code, 404)
        r, data = self.call("GET", f"/api/speaking/submissions/{sub_id}", cookie=cookie)
        self.assertEqual((data["submission"]["viewerRole"], data["submission"]["check"]), ("owner", None))
        r, data = self.call("GET", "/api/history", cookie=cookie)
        self.assertEqual([(i["module"], i["answered"]) for i in data["items"] if i["module"] == "speaking"], [("speaking", 2)])

    def test_paid_speaking_check(self):
        examiner, _ = self.login("speaking.examiner@example.com")
        admin, _ = self.login("owner@example.com")
        r, data = self.call("POST", "/api/admin/examiners", {"email": "speaking.examiner@example.com",
                                                              "displayName": "Kamola T.", "approved": True}, cookie=admin)
        ex_id = data["examiner"]["id"]
        student, _ = self.login("speaker.paid@example.com")
        t = SPEAKING[0]
        sub_id = self.record_test(student, t, keys={"p1-1", "p2-talk", "p3-1"})
        r, data = self.call("POST", "/api/orders", {"kind": "speaking_check", "examinerId": ex_id, "submissionId": sub_id},
                            cookie=student)
        self.assertEqual(r.code, 400)  # not finished yet
        self.call("POST", f"/api/speaking/submissions/{sub_id}/complete", {}, cookie=student)
        r, data = self.call("POST", "/api/orders", {"kind": "speaking_check", "examinerId": ex_id, "submissionId": sub_id},
                            cookie=student)
        order = data["order"]
        self.assertEqual(order["amount"], billing.PRICES["speaking_check"])
        self.call("POST", f"/api/orders/{order['id']}/manual-paid", {}, cookie=student)
        self.call("POST", f"/api/admin/orders/{order['id']}/confirm", {}, cookie=admin)
        r, data = self.call("GET", f"/api/speaking/submissions/{sub_id}", cookie=student)
        self.assertEqual(data["submission"]["check"]["status"], "waiting")
        check_id = data["submission"]["check"]["id"]
        # The examiner sees the questions and can play the answers.
        r, data = self.call("GET", f"/api/checks/{check_id}", cookie=examiner)
        sub = data["check"]["submission"]
        rec_id = sub["parts"][0]["questions"][0]["recording"]["id"]
        self.assertEqual((sub["answered"], sub["parts"][0]["questions"][1]["recording"]), (3, None))
        self.assertEqual(self.fetch(f"/api/speaking/recordings/{rec_id}", headers={"Cookie": examiner}).code, 200)
        crit = {k: {"band": 6, "feedback": "OK"} for k in checks.SPEAKING_CRITERIA}
        crit["pronunciation"] = {"band": 7, "feedback": "Clear"}
        r, data = self.call("POST", f"/api/examiner/checks/{check_id}/result",
                            {"result": {"criteria": crit, "summary": "Good range.", "strengths": "Fluent\nIdeas"}}, cookie=examiner)
        self.assertEqual((r.code, data["check"]["overallBand"]), (200, 6.5))  # 25 / 4 = 6.25 -> 6.5
        r, data = self.call("GET", "/api/history", cookie=student)
        item = next(i for i in data["items"] if i["module"] == "speaking")
        self.assertEqual((item["bandScore"], item["checkId"]), (6.5, check_id))
        r, data = self.call("GET", f"/api/checks/{check_id}", cookie=student)
        self.assertEqual(data["check"]["result"]["criteria"]["pronunciation"]["band"], 7)


class NotificationTests(AccountApiBase):
    """Emails and Telegram messages at each step of a paid check (transports replaced by a recorder)."""

    def setUp(self):
        super().setUp()
        self.sent = []
        notify.SYNC = True
        env = {"RESEND_API_KEY": "re_test", "EMAIL_FROM": "MockExam <noreply@example.com>",
               "TELEGRAM_BOT_TOKEN": "123:abc", "TELEGRAM_ADMIN_CHAT_ID": "42", "SITE_URL": "https://mock.example"}
        self.patches = [mock.patch.dict(os.environ, env),
                        mock.patch.object(notify, "_post_json", lambda url, payload, headers=None: self.sent.append((url, payload)))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        notify.SYNC = False
        super().tearDown()

    def emails(self, to=None):
        return [p for u, p in self.sent if "resend" in u and (to is None or to in p["to"])]

    def telegrams(self):
        return [p["text"] for u, p in self.sent if "telegram" in u]

    def test_paid_check_notifications(self):
        examiner, _ = self.login("notify.examiner@example.com")
        admin, _ = self.login("owner@example.com")
        r, data = self.call("POST", "/api/admin/examiners", {"email": "notify.examiner@example.com", "displayName": "N. E.",
                                                              "approved": True}, cookie=admin)
        ex_id = data["examiner"]["id"]
        student, _ = self.login("notify.student@example.com")
        t = WRITING[0]
        r, data = self.call("POST", f"/api/writing/{t['id']}/submit",
                            {"responses": {"1": t["tasks"][0]["modelAnswer"], "2": t["tasks"][1]["modelAnswer"]}}, cookie=student)
        r, data = self.call("POST", "/api/orders", {"kind": "writing_check", "examinerId": ex_id, "submissionId": data["submissionId"]},
                            cookie=student)
        order_id = data["order"]["id"]
        self.sent.clear()
        self.call("POST", f"/api/orders/{order_id}/manual-paid", {}, cookie=student)
        self.call("POST", f"/api/orders/{order_id}/manual-paid", {}, cookie=student)  # repeated press: one message
        claimed = self.emails("owner@example.com")
        self.assertEqual(len(claimed), 1)
        self.assertIn(f"MX{order_id}", claimed[0]["subject"])
        self.assertIn("https://mock.example/#/admin?tab=payments", claimed[0]["text"])
        self.assertTrue(any(f"MX{order_id}" in m for m in self.telegrams()))
        r, data = self.call("GET", "/api/me", cookie=admin)
        self.assertGreaterEqual(data["todo"]["payments"], 1)

        self.sent.clear()
        self.call("POST", f"/api/admin/orders/{order_id}/confirm", {}, cookie=admin)
        self.call("POST", f"/api/admin/orders/{order_id}/confirm", {}, cookie=admin)  # repeated: no second round
        self.assertEqual([e["subject"] for e in self.emails("notify.student@example.com")], ["Payment received: Writing check"])
        to_examiner = self.emails("notify.examiner@example.com")
        self.assertEqual(len(to_examiner), 1)
        self.assertRegex(to_examiner[0]["text"], r"https://mock\.example/#/check/\d+")
        self.assertIn("<a href=", to_examiner[0]["html"])
        self.assertFalse(any("New payment" in m for m in self.telegrams()))  # the admin confirmed it themselves
        r, data = self.call("GET", "/api/me", cookie=examiner)
        self.assertEqual(data["todo"]["checks"], 1)

        check_id = self.call("GET", "/api/checks", cookie=student)[1]["checks"][0]["id"]
        crit = {k: {"band": 6, "feedback": "OK"} for k in checks.WRITING_CRITERIA}
        self.sent.clear()
        self.call("POST", f"/api/examiner/checks/{check_id}/result",
                  {"result": {"tasks": {"1": {"criteria": crit}, "2": {"criteria": crit}}}}, cookie=examiner)
        done = self.emails("notify.student@example.com")
        self.assertEqual(len(done), 1)
        self.assertIn("band 6.0", done[0]["text"])
        self.assertEqual(self.call("GET", "/api/me", cookie=examiner)[1]["todo"]["checks"], 0)

    def test_nothing_sent_without_configuration(self):
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": "", "TELEGRAM_BOT_TOKEN": ""}):
            self.assertFalse(notify.send_email("a@example.com", "Hi", "Text"))
            self.assertFalse(notify.send_telegram("Hi"))
        self.assertEqual(self.sent, [])


class SpeakingCleanupTests(unittest.TestCase):
    def test_old_recordings_are_deleted(self):
        tmp = tempfile.mkdtemp()
        db = SqliteDb(os.path.join(tmp, "c.sqlite3"))
        files = LocalFiles(os.path.join(tmp, "rec"))
        t = SPEAKING[0]

        def make(status, days_old, check_status=None):
            sub = db.insert("speaking_submissions", {"user_id": "u1", "test_id": t["id"], "status": status,
                                                     "created_at": iso(now() - datetime.timedelta(days=days_old))})
            speaking.save_recording(db, files, dict(sub, status="recording"), t, "p1-1", FAKE_AUDIO, "audio/webm", 3)
            if check_status:
                db.insert("checks", {"order_id": sub["id"] + 1000, "kind": "speaking", "student_id": "u1", "examiner_id": "e1",
                                     "submission_id": sub["id"], "status": check_status})
            return sub

        abandoned, fresh, expired, marking = make("recording", 3), make("completed", 5), make("completed", 90), \
            make("completed", 90, "in_progress")
        self.assertEqual(speaking.cleanup(db, files), (1, 2))
        self.assertIsNone(speaking.get_submission(db, abandoned["id"]))
        self.assertEqual(len(speaking.recordings_for(db, fresh["id"])), 1)
        self.assertEqual(len(speaking.recordings_for(db, expired["id"])), 0)
        self.assertTrue(speaking.get_submission(db, expired["id"])["recordings_deleted_at"])
        self.assertEqual(len(speaking.recordings_for(db, marking["id"])), 1)
        self.assertEqual(sum(len(f) for _, _, f in os.walk(os.path.join(tmp, "rec"))), 2)


class SupabaseAuthTests(unittest.TestCase):
    """SupabaseAuth against a fake Supabase Auth server: request shapes and error messages."""

    @classmethod
    def setUpClass(cls):
        import http.server
        import threading
        from mockexam import auth as auth_mod

        cls.calls = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, payload):
                raw = json.dumps(payload).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                cls.calls.append({"path": self.path, "body": body, "apikey": self.headers.get("apikey")})
                if self.path.startswith("/auth/v1/otp"):
                    if body["email"].endswith("@example.com"):
                        return self._send(400, {"code": 400, "error_code": "email_address_invalid", "msg": "invalid"})
                    return self._send(200, {})
                if self.path == "/auth/v1/verify":
                    if body.get("token") != "123456":
                        return self._send(403, {"code": 403, "error_code": "otp_expired", "msg": "Token has expired or is invalid"})
                    return self._send(200, {"access_token": "t", "user": {"id": "u-1", "email": body["email"],
                                                                         "user_metadata": {"full_name": "Aziz"}}})
                self._send(404, {})

            def do_GET(self):
                cls.calls.append({"path": self.path, "auth": self.headers.get("Authorization")})
                if self.path == "/auth/v1/settings":
                    return self._send(200, {"external": {"email": True, "google": True}})
                if self.headers.get("Authorization") == "Bearer good-token":
                    return self._send(200, {"id": "u-2", "email": "G@Gmail.com", "user_metadata": {"name": "Guli"}})
                self._send(401, {"code": 401, "error_code": "bad_jwt", "msg": "invalid JWT"})

        cls.httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.auth = auth_mod.SupabaseAuth(f"http://127.0.0.1:{cls.httpd.server_port}", "sb_publishable_x")
        cls.AuthError = auth_mod.AuthError

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def test_send_code(self):
        self.auth.send_code("student@gmail.com", "https://site/auth-callback.html")
        call = self.calls[-1]
        self.assertIn("redirect_to=https%3A%2F%2Fsite%2Fauth-callback.html", call["path"])
        self.assertEqual((call["body"]["create_user"], call["apikey"]), (True, "sb_publishable_x"))
        with self.assertRaises(self.AuthError) as e:
            self.auth.send_code("bad@example.com", "https://site/")
        self.assertIn("valid email", str(e.exception))

    def test_verify_code_and_token(self):
        identity = self.auth.verify_code("student@gmail.com", "123456")
        self.assertEqual(identity, {"id": "u-1", "email": "student@gmail.com", "name": "Aziz"})
        with self.assertRaises(self.AuthError) as e:
            self.auth.verify_code("student@gmail.com", "000000")
        self.assertIn("wrong or has expired", str(e.exception))
        self.assertEqual(self.auth.user_from_token("good-token"), {"id": "u-2", "email": "g@gmail.com", "name": "Guli"})
        with self.assertRaises(self.AuthError) as e:
            self.auth.user_from_token("bad-token")
        self.assertIn("expired", str(e.exception))
        self.assertIn("provider=google", self.auth.google_url("https://site/auth-callback.html"))
        self.assertTrue(self.auth.google_enabled())


def _db_with_order(kind="plan"):
    db = SqliteDb(os.path.join(tempfile.mkdtemp(), "pay.sqlite3"))
    uid = "11111111-2222-4333-8444-555555555555"
    accounts.upsert_profile(db, {"id": uid, "email": "payer@example.com", "name": ""})
    return db, uid, billing.create_order(db, uid, kind)


def _payme(api, method, params, key="secret-key"):
    import base64
    auth = "Basic " + base64.b64encode(f"Paycom:{key}".encode()).decode()
    return api.handle(json.dumps({"method": method, "params": params, "id": 7}).encode(), auth)


class PaymeTests(unittest.TestCase):
    def setUp(self):
        self.db, self.uid, self.order = _db_with_order()
        self.api = billing.PaymeApi(self.db, key="secret-key")
        self.amount = self.order["amount"] * 100
        self.account = {"order_id": str(self.order["id"])}

    def test_auth_and_validation(self):
        self.assertEqual(_payme(self.api, "CheckPerformTransaction", {}, key="wrong")["error"]["code"], -32504)
        self.assertEqual(_payme(self.api, "Nope", {})["error"]["code"], -32601)
        r = _payme(self.api, "CheckPerformTransaction", {"amount": self.amount, "account": self.account})
        self.assertEqual(r["result"], {"allow": True})
        r = _payme(self.api, "CheckPerformTransaction", {"amount": self.amount + 100, "account": self.account})
        self.assertEqual(r["error"]["code"], -31001)
        r = _payme(self.api, "CheckPerformTransaction", {"amount": self.amount, "account": {"order_id": "999999"}})
        self.assertEqual((r["error"]["code"], r["error"]["data"]), (-31050, "order_id"))

    def test_create_perform_check_cancel(self):
        p = {"id": "pm-1", "time": 1700000000000, "amount": self.amount, "account": self.account}
        r1 = _payme(self.api, "CreateTransaction", p)["result"]
        self.assertEqual(r1["state"], 1)
        self.assertEqual(_payme(self.api, "CreateTransaction", p)["result"]["create_time"], r1["create_time"])
        other = dict(p, id="pm-2")
        self.assertEqual(_payme(self.api, "CreateTransaction", other)["error"]["code"], -31052)
        r2 = _payme(self.api, "PerformTransaction", {"id": "pm-1"})["result"]
        self.assertEqual(r2["state"], 2)
        self.assertEqual(_payme(self.api, "PerformTransaction", {"id": "pm-1"})["result"]["perform_time"], r2["perform_time"])
        self.assertTrue(accounts.plan_status(self.db, self.uid)["active"])
        self.assertEqual(billing.get_order(self.db, self.order["id"])["status"], "paid")
        chk = _payme(self.api, "CheckTransaction", {"id": "pm-1"})["result"]
        self.assertEqual((chk["state"], chk["transaction"]), (2, "pm-1"))
        st = _payme(self.api, "GetStatement", {"from": 1690000000000, "to": 1710000000000})["result"]["transactions"]
        self.assertEqual([t["id"] for t in st], ["pm-1"])
        r3 = _payme(self.api, "CancelTransaction", {"id": "pm-1", "reason": 5})["result"]
        self.assertEqual(r3["state"], -2)
        self.assertFalse(accounts.plan_status(self.db, self.uid)["active"])
        self.assertEqual(billing.get_order(self.db, self.order["id"])["status"], "refunded")
        self.assertEqual(_payme(self.api, "PerformTransaction", {"id": "pm-1"})["error"]["code"], -31008)
        self.assertEqual(_payme(self.api, "CheckTransaction", {"id": "nope"})["error"]["code"], -31003)

    def test_cancel_before_perform_and_timeout(self):
        p = {"id": "pm-3", "time": 1700000000000, "amount": self.amount, "account": self.account}
        _payme(self.api, "CreateTransaction", p)
        r = _payme(self.api, "CancelTransaction", {"id": "pm-3", "reason": 3})["result"]
        self.assertEqual(r["state"], -1)
        self.assertEqual(billing.get_order(self.db, self.order["id"])["status"], "cancelled")
        db, uid, order = _db_with_order()
        api = billing.PaymeApi(db, key="secret-key")
        _payme(api, "CreateTransaction", {"id": "pm-4", "time": 1, "amount": order["amount"] * 100,
                                          "account": {"order_id": str(order["id"])}})
        db.update("payme_transactions", {"id": "pm-4"}, {"create_time": 1000})  # 12+ hours ago
        self.assertEqual(_payme(api, "PerformTransaction", {"id": "pm-4"})["error"]["code"], -31008)
        self.assertEqual(db.select("payme_transactions", {"id": "pm-4"})[0]["state"], -1)
        self.assertFalse(accounts.plan_status(db, uid)["active"])


class ClickTests(unittest.TestCase):
    SECRET = "click-secret"

    def setUp(self):
        self.db, self.uid, self.order = _db_with_order()
        self.api = billing.ClickApi(self.db, service_id="777", secret_key=self.SECRET)

    def form(self, action, prepare_id="", amount=None, error="0", sign=None):
        import hashlib
        f = {"click_trans_id": "555", "service_id": "777", "click_paydoc_id": "1", "merchant_trans_id": str(self.order["id"]),
             "amount": str(amount if amount is not None else self.order["amount"]), "action": str(action), "error": error,
             "error_note": "", "sign_time": "2026-09-28 10:00:00"}
        if action == 1:
            f["merchant_prepare_id"] = str(prepare_id)
        raw = f["click_trans_id"] + f["service_id"] + self.SECRET + f["merchant_trans_id"] + \
            (f.get("merchant_prepare_id", "") if action == 1 else "") + f["amount"] + f["action"] + f["sign_time"]
        f["sign_string"] = sign or hashlib.md5(raw.encode()).hexdigest()
        return f

    def test_prepare_and_complete(self):
        self.assertEqual(self.api.prepare(self.form(0, sign="0" * 32))["error"], -1)
        self.assertEqual(self.api.prepare(self.form(0, amount=1))["error"], -2)
        prep = self.api.prepare(self.form(0))
        self.assertEqual(prep["error"], 0)
        done = self.api.complete(self.form(1, prep["merchant_prepare_id"]))
        self.assertEqual((done["error"], done["merchant_confirm_id"]), (0, prep["merchant_prepare_id"]))
        self.assertTrue(accounts.plan_status(self.db, self.uid)["active"])
        self.assertEqual(self.api.complete(self.form(1, prep["merchant_prepare_id"]))["error"], -4)
        self.assertEqual(self.api.prepare(self.form(0))["error"], -4)

    def test_failed_payment_cancels(self):
        prep = self.api.prepare(self.form(0))
        r = self.api.complete(self.form(1, prep["merchant_prepare_id"], error="-5017"))
        self.assertEqual(r["error"], -9)
        self.assertEqual(billing.get_order(self.db, self.order["id"])["status"], "cancelled")
        self.assertEqual(self.api.complete(self.form(1, 999))["error"], -6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
