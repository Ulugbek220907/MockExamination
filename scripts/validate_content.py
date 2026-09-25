#!/usr/bin/env python3
"""
Validate every reading and writing test in content/.

Checks question numbering, answer keys against options, completion answers
against the passage text and word limits, gap placement, chart data, and
model-answer lengths. Also prints word counts and answer distributions so a
human editor can spot unbalanced keys (e.g. too many TRUE answers).

Usage: python scripts/validate_content.py
"""

import os
import sys
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from mockexam import content  # noqa: E402

CONTENT_DIR = os.path.join(BASE_DIR, "content")


def main():
    problems = []

    for test in content.load_json_dir(os.path.join(CONTENT_DIR, "reading")):
        problems += content.validate_reading_test(test)
        print(f"\n{test['id']}  —  {test['title']}")
        for p in test["passages"]:
            words = content.count_words(content.passage_text(p))
            nums = [q["number"] for g in p["groups"] for q in g["questions"]]
            print(f"  Passage {p['passageNumber']}: {p['title']!r}  {words} words, Q{min(nums)}–{max(nums)} ({len(nums)})")
            for g in p["groups"]:
                if g["type"] == "choose_multiple":
                    keys = g.get("answer", [])
                else:
                    keys = [q.get("answer") if not isinstance(q.get("answer"), list) else "text" for q in g["questions"]]
                dist = dict(Counter(keys)) if g["type"] not in content.COMPLETION_TYPES or g.get("options") else ""
                print(f"    {g['type']:<28} {dist}")

    for test in content.load_json_dir(os.path.join(CONTENT_DIR, "writing")):
        problems += content.validate_writing_test(test)
        print(f"\n{test['id']}  —  {test['title']}")
        for t in test["tasks"]:
            model_words = content.count_words(t.get("modelAnswer", ""))
            vis = (t.get("visual") or {}).get("type", "-")
            print(f"  Task {t['taskNumber']}: visual={vis}, model answer {model_words} words (min {t.get('minWords')})")

    print()
    if problems:
        print(f"FOUND {len(problems)} PROBLEM(S):")
        for p in problems:
            print("  ✗", p)
        sys.exit(1)
    print("✓ All content valid.")


if __name__ == "__main__":
    main()
