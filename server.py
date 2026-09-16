#!/usr/bin/env python3
"""
IELTS Mock Exam Platform Server
Provides REST API endpoints for tests, answer evaluation, band score calculation,
and serves static web assets. Uses Tornado with fallback to standard http.server.
"""

import os
import sys
import json
import sqlite3
import datetime

PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "tests.json")
DB_FILE = os.path.join(BASE_DIR, "data", "attempts.db")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

# Initialize SQLite database for storing mock exam attempts
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT NOT NULL,
            candidate_name TEXT NOT NULL,
            raw_score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            band_score REAL NOT NULL,
            time_spent_seconds INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary_json TEXT
        )
    """)
    conn.commit()
    conn.close()

# Load tests dataset
def load_dataset():
    if not os.path.exists(DATA_FILE):
        return {"modules": {}, "tests": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Official IELTS Academic Reading Band Score conversion
def calculate_band_score(raw_score):
    if raw_score >= 39:
        return 9.0
    elif raw_score >= 37:
        return 8.5
    elif raw_score >= 35:
        return 8.0
    elif raw_score >= 33:
        return 7.5
    elif raw_score >= 30:
        return 7.0
    elif raw_score >= 27:
        return 6.5
    elif raw_score >= 23:
        return 6.0
    elif raw_score >= 19:
        return 5.5
    elif raw_score >= 15:
        return 5.0
    elif raw_score >= 13:
        return 4.5
    elif raw_score >= 10:
        return 4.0
    elif raw_score >= 8:
        return 3.5
    elif raw_score >= 6:
        return 3.0
    elif raw_score >= 4:
        return 2.5
    else:
        return 2.0

def get_cefr_level(band_score):
    if band_score >= 8.5:
        return "C2 (Proficient)"
    elif band_score >= 7.0:
        return "C1 (Advanced)"
    elif band_score >= 5.5:
        return "B2 (Independent)"
    elif band_score >= 4.0:
        return "B1 (Intermediate)"
    else:
        return "A2 / Basic"

def normalize_text(val):
    if val is None:
        return ""
    return str(val).strip().lower()

def evaluate_test_submission(test_data, submitted_answers, candidate_name="Candidate", time_spent=0):
    total_q = 0
    raw_score = 0
    passage_breakdown = {}
    detailed_results = []

    # Map questions
    q_map = {}
    for p in test_data["passages"]:
        p_num = p["passageNumber"]
        passage_breakdown[p_num] = {"title": p["title"], "total": 0, "correct": 0}
        for q in p["questions"]:
            q_map[str(q["number"])] = (p_num, q)

    # Handle multi-select pairs (e.g. Q20 & Q21, Q22 & Q23, Q23 & Q24, Q25 & Q26)
    # Check each question
    for q_num_str, (p_num, q) in q_map.items():
        total_q += 1
        passage_breakdown[p_num]["total"] += 1

        cand_val = submitted_answers.get(q_num_str, "")
        correct_ans = q["answer"]

        is_correct = False

        if isinstance(correct_ans, list):
            # Either alternative correct answers OR multi-select pair
            cand_norm = normalize_text(cand_val)
            for alt in correct_ans:
                if cand_norm == normalize_text(alt):
                    is_correct = True
                    break
        else:
            cand_norm = normalize_text(cand_val)
            corr_norm = normalize_text(correct_ans)
            if cand_norm == corr_norm:
                is_correct = True

        if is_correct:
            raw_score += 1
            passage_breakdown[p_num]["correct"] += 1

        detailed_results.append({
            "number": q["number"],
            "passageNumber": p_num,
            "type": q["type"],
            "prompt": q["prompt"],
            "candidateAnswer": cand_val,
            "correctAnswer": correct_ans,
            "isCorrect": is_correct,
            "explanation": q.get("explanation", ""),
            "passageReference": q.get("passageReference", "")
        })

    detailed_results.sort(key=lambda x: x["number"])
    band_score = calculate_band_score(raw_score)
    cefr = get_cefr_level(band_score)

    # Save to SQLite
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO attempts (test_id, candidate_name, raw_score, total_questions, band_score, time_spent_seconds, summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            test_data["id"],
            candidate_name,
            raw_score,
            total_q,
            band_score,
            time_spent,
            json.dumps({"breakdown": passage_breakdown, "cefr": cefr})
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving attempt: {e}", file=sys.stderr)

    return {
        "testId": test_data["id"],
        "book": test_data["book"],
        "title": test_data["title"],
        "candidateName": candidate_name,
        "rawScore": raw_score,
        "totalQuestions": total_q,
        "bandScore": band_score,
        "cefrLevel": cefr,
        "timeSpentSeconds": time_spent,
        "passageBreakdown": passage_breakdown,
        "results": detailed_results
    }

# Implement Tornado Application
try:
    import tornado.ioloop
    import tornado.web
    import tornado.gen

    class ApiTestsHandler(tornado.web.RequestHandler):
        def get(self):
            dataset = load_dataset()
            tests_summary = []
            for t in dataset.get("tests", []):
                tests_summary.append({
                    "id": t["id"],
                    "book": t["book"],
                    "bookShort": t.get("bookShort", t["book"]),
                    "testNumber": t["testNumber"],
                    "title": t["title"],
                    "durationMinutes": t["durationMinutes"],
                    "totalQuestions": t["totalQuestions"],
                    "passages": [
                        {"number": p["passageNumber"], "title": p["title"]}
                        for p in t["passages"]
                    ]
                })
            self.set_header("Content-Type", "application/json; charset=utf-8")
            self.write(json.dumps({
                "modules": dataset.get("modules", {}),
                "tests": tests_summary
            }))

    class ApiSingleTestHandler(tornado.web.RequestHandler):
        def get(self, test_id):
            dataset = load_dataset()
            for t in dataset.get("tests", []):
                if t["id"] == test_id:
                    self.set_header("Content-Type", "application/json; charset=utf-8")
                    self.write(json.dumps(t))
                    return
            self.set_status(404)
            self.write({"error": "Test not found"})

    class ApiSubmitHandler(tornado.web.RequestHandler):
        def post(self, test_id):
            dataset = load_dataset()
            target_test = None
            for t in dataset.get("tests", []):
                if t["id"] == test_id:
                    target_test = t
                    break
            
            if not target_test:
                self.set_status(404)
                self.write({"error": "Test not found"})
                return

            try:
                body = json.loads(self.request.body)
            except Exception:
                body = {}

            answers = body.get("answers", {})
            candidate_name = body.get("candidateName", "Candidate")
            time_spent = body.get("timeSpentSeconds", 0)

            result = evaluate_test_submission(target_test, answers, candidate_name, time_spent)
            self.set_header("Content-Type", "application/json; charset=utf-8")
            self.write(json.dumps(result))

    class ApiAttemptsHandler(tornado.web.RequestHandler):
        def get(self):
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""
                SELECT id, test_id, candidate_name, raw_score, total_questions, band_score, time_spent_seconds, completed_at, summary_json
                FROM attempts ORDER BY id DESC LIMIT 50
            """)
            rows = c.fetchall()
            conn.close()

            attempts = []
            for r in rows:
                attempts.append({
                    "id": r[0],
                    "testId": r[1],
                    "candidateName": r[2],
                    "rawScore": r[3],
                    "totalQuestions": r[4],
                    "bandScore": r[5],
                    "timeSpentSeconds": r[6],
                    "completedAt": r[7],
                    "summary": json.loads(r[8]) if r[8] else {}
                })
            self.set_header("Content-Type", "application/json; charset=utf-8")
            self.write(json.dumps({"attempts": attempts}))

    def make_app():
        return tornado.web.Application([
            (r"/api/tests", ApiTestsHandler),
            (r"/api/tests/([a-zA-Z0-9_\-]+)", ApiSingleTestHandler),
            (r"/api/tests/([a-zA-Z0-9_\-]+)/submit", ApiSubmitHandler),
            (r"/api/attempts", ApiAttemptsHandler),
            (r"/(.*)", tornado.web.StaticFileHandler, {
                "path": PUBLIC_DIR,
                "default_filename": "index.html"
            })
        ])

    def run_server():
        init_db()
        app = make_app()
        app.listen(PORT)
        print(f"IELTS Mock Exam Platform running at http://localhost:{PORT}")
        print("Ready for tests: Cambridge 17, 18, 19 (Academic Reading)")
        tornado.ioloop.IOLoop.current().start()

except ImportError:
    # Standard library fallback
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    import urllib.parse

    class FallbackHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/tests":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                dataset = load_dataset()
                tests_summary = [{
                    "id": t["id"],
                    "book": t["book"],
                    "bookShort": t.get("bookShort", t["book"]),
                    "testNumber": t["testNumber"],
                    "title": t["title"],
                    "durationMinutes": t["durationMinutes"],
                    "totalQuestions": t["totalQuestions"]
                } for t in dataset.get("tests", [])]
                self.wfile.write(json.dumps({
                    "modules": dataset.get("modules", {}),
                    "tests": tests_summary
                }).encode("utf-8"))
            elif parsed.path.startswith("/api/tests/"):
                test_id = parsed.path.split("/")[3]
                dataset = load_dataset()
                for t in dataset.get("tests", []):
                    if t["id"] == test_id:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(t).encode("utf-8"))
                        return
                self.send_error(404, "Test not found")
            else:
                super().do_GET()

    def run_server():
        init_db()
        server = HTTPServer(("0.0.0.0", PORT), FallbackHandler)
        print(f"IELTS Mock Exam Platform (Fallback HTTP) running at http://localhost:{PORT}")
        server.serve_forever()

if __name__ == "__main__":
    run_server()
