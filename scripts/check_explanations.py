#!/usr/bin/env python3
"""
Report which questions in the free tests (Test 1 of each module) have no explanation.

The free tests are the first thing a new student sees, and the explanation under each
answer is what makes the result page worth reading, so every question should have one.
This only reports; it never changes content.

Checks:
  Reading    every question has an explanation and a reference (where the answer is;
             not needed for NOT GIVEN, which by definition is nowhere in the text)
  Listening  every question has an explanation, and its answer can be found in the
             recording's transcript (the results page links each answer to that line)
  Writing    every task has a model answer
  Speaking   every question has its recorded audio (Speaking has no per-question
             explanations: the self-check on the results page covers every answer)

  A "choose two" group shares one explanation and reference for its questions.

Usage: python scripts/check_explanations.py [--all]   (--all checks every test, not only the free ones)
Exit code 1 if anything is missing, so it can run in CI later if wanted.
"""

import glob
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from mockexam import content  # noqa: E402
from mockexam.accounts import test_access  # noqa: E402

CONTENT_DIR = os.path.join(BASE_DIR, "content")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")


def blank(value):
    return not (isinstance(value, str) and value.strip() and value.strip() not in ("—", "-", "TODO"))


def questions(test, part_key):
    """Each question with its group's shared explanation and location filled in where it has none."""
    for part in test.get(part_key) or []:
        for group in part.get("groups") or []:
            for q in group.get("questions") or []:
                merged = dict(q)
                for key in ("explanation", "reference", "cue", "answer"):
                    if blank(merged.get(key)) and not blank(group.get(key)):
                        merged[key] = group[key]
                yield part, merged


def check(test):
    """Missing items for one test, as readable lines."""
    module = test.get("module")
    missing = []
    if module == "reading":
        for _, q in questions(test, "passages"):
            located = str(q.get("answer", "")).strip().upper() != "NOT GIVEN"
            gaps = [name for name, needed in (("explanation", True), ("reference", located)) if needed and blank(q.get(name))]
            if gaps:
                missing.append(f"Q{q.get('number')}: no {' and no '.join(gaps)}")
    elif module == "listening":
        cues = content.locate_listening_cues(test)
        for _, q in questions(test, "parts"):
            gaps = (["explanation"] if blank(q.get("explanation")) else []) + \
                   ([] if q.get("number") in cues else ["place in the transcript"])
            if gaps:
                missing.append(f"Q{q.get('number')}: no {' and no '.join(gaps)}")
    elif module == "writing":
        for task in test.get("tasks") or []:
            if blank(task.get("modelAnswer")):
                missing.append(f"Task {task.get('taskNumber')}: no model answer")
    elif module == "speaking":
        for part in test.get("parts") or []:
            for q in part.get("questions") or []:
                audio = q.get("audio")
                src = audio.get("src") if isinstance(audio, dict) else audio
                if not src or not os.path.exists(os.path.join(PUBLIC_DIR, str(src).split("?")[0])):
                    missing.append(f"Part {part.get('partNumber')} '{q.get('key')}': no recorded audio")
    return missing


def main():
    everything = "--all" in sys.argv[1:]
    total = 0
    for path in sorted(glob.glob(os.path.join(CONTENT_DIR, "*", "*.json"))):
        with open(path, encoding="utf-8") as f:
            test = json.load(f)
        if not everything and test_access(test) != "free":
            continue
        missing = check(test)
        total += len(missing)
        name = f"{test.get('title', test.get('id'))} ({os.path.relpath(path, BASE_DIR)})"
        if missing:
            print(f"✗ {name}: {len(missing)} missing")
            for line in missing:
                print(f"    {line}")
        else:
            print(f"✓ {name}: complete")
    print(f"\n{total} item(s) missing." if total else "\nNothing missing.")
    return 1 if total else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
