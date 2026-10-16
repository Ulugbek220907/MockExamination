import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mockexam.content import validate_reading_test

with open("content/reading/book_34_tests.json", "r", encoding="utf-8") as f:
    tests = json.load(f)

total_errors = 0
for i, t in enumerate(tests, 1):
    errs = validate_reading_test(t)
    if errs:
        total_errors += len(errs)
        print(f"Test {i} ({t.get('id')}) has {len(errs)} errors:")
        for e in errs:
            print("  -", e)

print(f"\nTotal validation errors across 34 tests: {total_errors}")
