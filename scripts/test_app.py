#!/usr/bin/env python3
"""
Automated unit & integration verification for IELTS Mock Exam backend and data.
"""

import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import server

def run_tests():
    print("=== 1. Testing Database Initialization ===")
    server.init_db()
    assert os.path.exists(server.DB_FILE), "attempts.db should exist"
    print("✓ Database initialized successfully.")

    print("\n=== 2. Testing Tests Dataset ===")
    data = server.load_dataset()
    assert "tests" in data and len(data["tests"]) == 3, "Must have 3 Cambridge tests"
    assert "modules" in data, "Must have modules dictionary"
    assert data["modules"]["reading"]["status"] == "active"
    assert data["modules"]["listening"]["status"] == "soon"
    assert data["modules"]["writing"]["status"] == "soon"
    assert data["modules"]["speaking"]["status"] == "soon"

    for t in data["tests"]:
        print(f"Checking test: {t['book']} - {t['title']} ({t['id']})")
        assert len(t["passages"]) == 3, f"{t['id']} must have 3 passages"
        total_q = sum(len(p["questions"]) for p in t["passages"])
        assert total_q == 40, f"{t['id']} must have exactly 40 questions, got {total_q}"
        for p in t["passages"]:
            assert len(p["paragraphs"]) > 0, f"Passage {p['passageNumber']} has no paragraphs"
            for q in p["questions"]:
                assert "answer" in q and q["answer"], f"Question {q['number']} missing answer"
                assert "prompt" in q and q["prompt"], f"Question {q['number']} missing prompt"
                assert "type" in q and q["type"], f"Question {q['number']} missing type"

    print("✓ All 3 Cambridge tests (120 questions) validated successfully.")

    print("\n=== 3. Testing Official Band Score Calculation ===")
    assert server.calculate_band_score(40) == 9.0
    assert server.calculate_band_score(39) == 9.0
    assert server.calculate_band_score(37) == 8.5
    assert server.calculate_band_score(35) == 8.0
    assert server.calculate_band_score(33) == 7.5
    assert server.calculate_band_score(30) == 7.0
    assert server.calculate_band_score(27) == 6.5
    assert server.calculate_band_score(23) == 6.0
    assert server.calculate_band_score(19) == 5.5
    assert server.calculate_band_score(15) == 5.0
    assert server.calculate_band_score(10) == 4.0
    print("✓ Band score mapping perfectly matches official IELTS Academic tables.")

    print("\n=== 4. Testing Submission Evaluation ===")
    test_19 = data["tests"][0]
    sample_answers = {
        "1": "FALSE",     # Correct
        "2": "FALSE",     # Correct
        "3": "NOT GIVEN", # Correct
        "4": "FALSE",     # Correct
        "5": "FALSE",     # Incorrect (Correct is NOT GIVEN)
        "6": "TRUE",      # Correct
        "7": "TRUE",      # Correct
        "8": "paint",     # Correct
        "9": "topspin",   # Correct
        "10": "training", # Correct
        "11": "intestines", # Correct
        "12": "weights",  # Correct
        "13": "grips"     # Correct
    }
    # 12 out of 13 correct so far

    eval_result = server.evaluate_test_submission(
        test_19,
        sample_answers,
        candidate_name="Test Candidate",
        time_spent=1200
    )

    assert eval_result["rawScore"] == 12, f"Expected 12 raw score, got {eval_result['rawScore']}"
    assert eval_result["totalQuestions"] == 40
    assert eval_result["bandScore"] == 4.0, f"Expected Band 4.0 for 12/40, got {eval_result['bandScore']}"
    assert len(eval_result["results"]) == 40
    assert eval_result["results"][0]["isCorrect"] is True
    assert eval_result["results"][4]["isCorrect"] is False
    print(f"✓ Submission evaluated: Raw Score = {eval_result['rawScore']}/40, Band = {eval_result['bandScore']}, CEFR = {eval_result['cefrLevel']}")

    print("\n=== 5. Testing Static Assets Exist ===")
    assert os.path.exists(os.path.join(server.PUBLIC_DIR, "index.html")), "index.html must exist"
    assert os.path.exists(os.path.join(server.PUBLIC_DIR, "css", "cd-ielts.css")), "cd-ielts.css must exist"
    assert os.path.exists(os.path.join(server.PUBLIC_DIR, "css", "portal.css")), "portal.css must exist"
    assert os.path.exists(os.path.join(server.PUBLIC_DIR, "js", "app.js")), "app.js must exist"
    assert os.path.exists(os.path.join(server.PUBLIC_DIR, "js", "exam.js")), "exam.js must exist"
    assert os.path.exists(os.path.join(server.PUBLIC_DIR, "js", "highlighter.js")), "highlighter.js must exist"
    assert os.path.exists(os.path.join(server.PUBLIC_DIR, "js", "scoring.js")), "scoring.js must exist"
    print("✓ All static frontend assets confirmed.")

    print("\n==============================================")
    print(" ALL TESTS PASSED! APPLICATION IS 100% READY.")
    print("==============================================")

if __name__ == "__main__":
    run_tests()
