#!/usr/bin/env python3
"""
Generate Academic Reading Practice Tests 07 through 40 from data/book_34_tests.json.

Each test is mapped to:
  id: academic-reading-07 .. academic-reading-40
  title: Academic Reading Practice Test 7 .. 40
  shortTitle: Practice Test 7 .. 40
  module: reading
  variant: academic
  sortOrder: 7 .. 40
  durationMinutes: 60
  totalQuestions: 40
  license: Past papers for practice and exam preparation.
"""

import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "book_34_tests.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "content", "reading")


def main():
    if not os.path.exists(DATA_PATH):
        sys.exit(f"Data file not found: {DATA_PATH}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        tests = json.load(f)

    if len(tests) != 34:
        sys.exit(f"Expected 34 tests in {DATA_PATH}, found {len(tests)}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    created = []
    for idx, test in enumerate(tests):
        test_num = idx + 7
        test_id = f"academic-reading-{test_num:02d}"
        file_path = os.path.join(OUTPUT_DIR, f"{test_id}.json")

        test_data = {
            "id": test_id,
            "title": f"Academic Reading Practice Test {test_num}",
            "module": "reading",
            "license": "Past papers for practice and exam preparation.",
            "variant": "academic",
            "passages": test["passages"],
            "sortOrder": test_num,
            "shortTitle": f"Practice Test {test_num}",
            "totalQuestions": 40,
            "durationMinutes": 60,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        created.append(test_id)
        print(f"✓ Generated {test_id} ({test_data['title']})")

    print(f"\nSuccessfully generated {len(created)} reading test files (academic-reading-07 through academic-reading-40).")


if __name__ == "__main__":
    main()
