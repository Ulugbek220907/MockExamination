"""
Content model helpers for reading and writing tests.

A reading test is made of passages; each passage has paragraphs and question
"groups" (one group = one IELTS instruction block such as "Questions 1-7,
TRUE/FALSE/NOT GIVEN"). This module walks that structure, validates it, and
produces the public (answer-free) version that is sent to candidates.
"""

import copy
import json
import os
import re

TFNG = ("TRUE", "FALSE", "NOT GIVEN")
YNNG = ("YES", "NO", "NOT GIVEN")

# Group types whose questions are answered by typing words from the passage
# (unless the group provides a word list, in which case a letter is chosen).
COMPLETION_TYPES = {
    "note_completion",
    "summary_completion",
    "table_completion",
    "flow_chart_completion",
    "sentence_completion",
    "short_answer",
}
# Types whose gaps are embedded in the group's "content" (rather than each question prompt)
CONTENT_GAP_TYPES = {"note_completion", "summary_completion", "table_completion", "flow_chart_completion"}
MATCHING_TYPES = {
    "matching_headings",
    "matching_information",
    "matching_features",
    "matching_sentence_endings",
    "classification",
}
ALL_READING_TYPES = (
    COMPLETION_TYPES
    | MATCHING_TYPES
    | {"true_false_not_given", "yes_no_not_given", "multiple_choice", "choose_multiple"}
)

GAP_RE = re.compile(r"\{\{(\d+)\}\}")
NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15",
    "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19",
    "twenty": "20",
}


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def load_json_dir(directory):
    """Load every *.json file in a directory, sorted by sortOrder then id."""
    items = []
    if not os.path.isdir(directory):
        return items
    for name in sorted(os.listdir(directory)):
        if name.endswith(".json"):
            with open(os.path.join(directory, name), "r", encoding="utf-8") as f:
                items.append(json.load(f))
    items.sort(key=lambda t: (t.get("sortOrder", 999), t.get("id", "")))
    return items


# --------------------------------------------------------------------------
# Walking the structure
# --------------------------------------------------------------------------

def iter_groups(test):
    """Yield (passage, group) for every question group in a reading test."""
    for passage in test.get("passages", []):
        for group in passage.get("groups", []):
            yield passage, group


def iter_questions(test):
    """Yield (passage, group, question) for every numbered question."""
    for passage, group in iter_groups(test):
        for q in group.get("questions", []):
            yield passage, group, q


def question_numbers(group):
    return [q["number"] for q in group.get("questions", [])]


def passage_text(passage):
    return " ".join(p["text"] for p in passage.get("paragraphs", []))


def count_words(text):
    return len([w for w in re.split(r"\s+", text.strip()) if w])


# --------------------------------------------------------------------------
# Public (answer-free) views
# --------------------------------------------------------------------------

_PRIVATE_QUESTION_KEYS = ("answer", "explanation", "reference")
_PRIVATE_GROUP_KEYS = ("answer", "explanation", "reference")


def public_reading_test(test):
    """Return a deep copy of a reading test with answer keys removed."""
    clean = copy.deepcopy(test)
    for passage in clean.get("passages", []):
        passage.pop("factSources", None)
        for group in passage.get("groups", []):
            for key in _PRIVATE_GROUP_KEYS:
                group.pop(key, None)
            for q in group.get("questions", []):
                for key in _PRIVATE_QUESTION_KEYS:
                    q.pop(key, None)
    return clean


def public_writing_test(test):
    """Return a deep copy of a writing test without model answers or marking notes."""
    clean = copy.deepcopy(test)
    for task in clean.get("tasks", []):
        task.pop("modelAnswer", None)
        task.pop("examinerNotes", None)
    return clean


def summarize_test(test):
    """Small card-sized summary used by the dashboard."""
    summary = {
        "id": test["id"],
        "module": test.get("module", "reading"),
        "variant": test.get("variant", "academic"),
        "title": test["title"],
        "shortTitle": test.get("shortTitle", test["title"]),
        "durationMinutes": test.get("durationMinutes", 60),
        "sortOrder": test.get("sortOrder", 999),
    }
    if summary["module"] == "reading":
        summary["totalQuestions"] = test.get("totalQuestions", 40)
        summary["passages"] = [
            {"number": p["passageNumber"], "title": p["title"]} for p in test.get("passages", [])
        ]
    else:
        summary["tasks"] = [
            {
                "number": t["taskNumber"],
                "title": t.get("title", f"Task {t['taskNumber']}"),
                "visualType": (t.get("visual") or {}).get("type"),
            }
            for t in test.get("tasks", [])
        ]
    return summary


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def _answers_as_list(answer):
    return answer if isinstance(answer, list) else [answer]


def _normalize_for_search(text):
    text = text.lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text)


def _appears_in(needle, haystack):
    needle = _normalize_for_search(needle)
    haystack = _normalize_for_search(haystack)
    return re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", haystack) is not None


def validate_reading_test(test):
    """Return a list of human-readable problems (empty list = valid)."""
    errors = []
    tid = test.get("id", "<no id>")

    for key in ("id", "title", "passages"):
        if key not in test:
            errors.append(f"{tid}: missing '{key}'")
    if errors:
        return errors

    numbers = []
    for passage, group in iter_groups(test):
        gtype = group.get("type")
        where = f"{tid} P{passage.get('passageNumber')} [{gtype}]"
        text = passage_text(passage)
        labels = {p.get("label") for p in passage.get("paragraphs", []) if p.get("label")}

        if gtype not in ALL_READING_TYPES:
            errors.append(f"{where}: unknown group type")
            continue
        if not group.get("instruction"):
            errors.append(f"{where}: missing instruction")
        qs = group.get("questions", [])
        if not qs:
            errors.append(f"{where}: no questions")
        numbers.extend(question_numbers(group))

        option_keys = [o["key"] for o in group.get("options", [])]
        if len(option_keys) != len(set(option_keys)):
            errors.append(f"{where}: duplicate option keys")

        if gtype in ("true_false_not_given", "yes_no_not_given"):
            allowed = TFNG if gtype == "true_false_not_given" else YNNG
            for q in qs:
                if q.get("answer") not in allowed:
                    errors.append(f"{where} Q{q['number']}: answer must be one of {allowed}")
                if not q.get("prompt"):
                    errors.append(f"{where} Q{q['number']}: missing prompt")

        elif gtype == "multiple_choice":
            for q in qs:
                keys = [o["key"] for o in q.get("options", [])]
                if q.get("answer") not in keys:
                    errors.append(f"{where} Q{q['number']}: answer not among options")
                if not q.get("prompt"):
                    errors.append(f"{where} Q{q['number']}: missing prompt")

        elif gtype == "choose_multiple":
            ans = group.get("answer", [])
            if not isinstance(ans, list) or len(ans) != len(qs):
                errors.append(f"{where}: group answer must list {len(qs)} letters")
            elif len(set(ans)) != len(ans) or any(a not in option_keys for a in ans):
                errors.append(f"{where}: group answer letters invalid")
            if not group.get("prompt"):
                errors.append(f"{where}: missing prompt")

        elif gtype in MATCHING_TYPES:
            keys = option_keys or sorted(labels)
            if gtype == "matching_information" and not option_keys and not labels:
                errors.append(f"{where}: needs labelled paragraphs or options")
            for q in qs:
                if q.get("answer") not in keys:
                    errors.append(f"{where} Q{q['number']}: answer {q.get('answer')!r} not in {keys}")
                if not q.get("prompt"):
                    errors.append(f"{where} Q{q['number']}: missing prompt")

        if gtype in COMPLETION_TYPES:
            max_words = group.get("maxWords")
            has_word_list = bool(option_keys)
            # Gap placement
            if gtype in CONTENT_GAP_TYPES:
                blob = json.dumps(group.get("content", ""), ensure_ascii=False)
                gaps = [int(n) for n in GAP_RE.findall(blob)]
                if sorted(gaps) != sorted(question_numbers(group)):
                    errors.append(f"{where}: content gaps {sorted(gaps)} != questions {question_numbers(group)}")
            elif gtype == "sentence_completion":
                for q in qs:
                    if GAP_RE.findall(q.get("prompt", "")) != [str(q["number"])]:
                        errors.append(f"{where} Q{q['number']}: prompt needs exactly one {{{{{q['number']}}}}} gap")
            else:  # short_answer
                for q in qs:
                    if not q.get("prompt"):
                        errors.append(f"{where} Q{q['number']}: missing prompt")

            for q in qs:
                answers = _answers_as_list(q.get("answer"))
                if not answers or not all(isinstance(a, str) and a for a in answers):
                    errors.append(f"{where} Q{q['number']}: empty answer")
                    continue
                if has_word_list:
                    if len(answers) != 1 or answers[0] not in option_keys:
                        errors.append(f"{where} Q{q['number']}: word-list answer must be one option key")
                    continue
                if not max_words:
                    errors.append(f"{where}: completion group without word list needs maxWords")
                    continue
                for a in answers:
                    if count_words(a) > max_words:
                        errors.append(f"{where} Q{q['number']}: '{a}' exceeds {max_words} word(s)")
                found = False
                for a in answers:
                    candidates = {a}
                    if a in NUMBER_WORDS.values():
                        candidates |= {w for w, d in NUMBER_WORDS.items() if d == a}
                    if any(_appears_in(c, text) for c in candidates):
                        found = True
                        break
                if not found:
                    errors.append(f"{where} Q{q['number']}: none of {answers} found in passage text")

    expected = list(range(1, test.get("totalQuestions", 40) + 1))
    if sorted(numbers) != expected:
        missing = sorted(set(expected) - set(numbers))
        dupes = sorted({n for n in numbers if numbers.count(n) > 1})
        errors.append(f"{tid}: question numbers wrong (missing={missing}, duplicates={dupes})")
    return errors


def validate_writing_test(test):
    errors = []
    tid = test.get("id", "<no id>")
    tasks = test.get("tasks", [])
    if [t.get("taskNumber") for t in tasks] != [1, 2]:
        errors.append(f"{tid}: must contain Task 1 and Task 2")
    for t in tasks:
        where = f"{tid} Task {t.get('taskNumber')}"
        for key in ("prompt", "minWords", "recommendedMinutes", "modelAnswer"):
            if not t.get(key):
                errors.append(f"{where}: missing {key}")
        model = t.get("modelAnswer") or ""
        if model and count_words(model) < t.get("minWords", 0):
            errors.append(f"{where}: model answer is shorter than the minimum word count")
        visual = t.get("visual")
        if t.get("taskNumber") == 1:
            if not visual or visual.get("type") not in ("line", "bar", "pie", "table", "process"):
                errors.append(f"{where}: Task 1 needs a visual of type line/bar/pie/table/process")
            elif visual["type"] in ("line", "bar"):
                n = len(visual.get("categories", []))
                for s in visual.get("series", []):
                    if len(s.get("values", [])) != n:
                        errors.append(f"{where}: series '{s.get('name')}' has wrong number of values")
            elif visual["type"] == "pie":
                for chart in visual.get("charts", []):
                    total = sum(sl["value"] for sl in chart.get("slices", []))
                    if abs(total - 100) > 0.51:
                        errors.append(f"{where}: pie '{chart.get('title')}' sums to {total}, not 100")
    return errors
