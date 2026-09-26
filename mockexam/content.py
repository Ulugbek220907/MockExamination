"""
Content model helpers for reading, listening and writing tests.

Reading and listening tests share one question model. A test is made of
sections (reading "passages" or listening "parts"); each section has question
"groups" (one group = one IELTS instruction block such as "Questions 1-7,
TRUE/FALSE/NOT GIVEN"). A reading passage has paragraphs; a listening part has
a script (the recording's transcript) and an audio file.

This module walks that structure, validates it, locates listening answers in
the transcript, and produces the public (answer-free) versions that are sent
to candidates.
"""

import copy
import json
import os
import re

TFNG = ("TRUE", "FALSE", "NOT GIVEN")
YNNG = ("YES", "NO", "NOT GIVEN")

# Group types whose questions are answered by typing words from the text
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
    "map_labelling",
}
ALL_QUESTION_TYPES = (
    COMPLETION_TYPES
    | MATCHING_TYPES
    | {"true_false_not_given", "yes_no_not_given", "multiple_choice", "choose_multiple"}
)
ALL_READING_TYPES = ALL_QUESTION_TYPES  # backwards-compatible name

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

def sections(test):
    """Reading passages or listening parts."""
    return test.get("passages") or test.get("parts") or []


def section_number(section):
    return section.get("passageNumber", section.get("partNumber"))


def iter_groups(test):
    """Yield (section, group) for every question group in a reading or listening test."""
    for section in sections(test):
        for group in section.get("groups", []):
            yield section, group


def iter_questions(test):
    """Yield (section, group, question) for every numbered question."""
    for section, group in iter_groups(test):
        for q in group.get("questions", []):
            yield section, group, q


def question_numbers(group):
    return [q["number"] for q in group.get("questions", [])]


def spoken_lines(part):
    """Script lines that are speech (not pauses), with their index in the script."""
    return [(i, line) for i, line in enumerate(part.get("script", [])) if "text" in line]


def passage_text(section):
    """The text answers must come from: reading paragraphs or a listening transcript."""
    if "paragraphs" in section:
        return " ".join(p["text"] for p in section["paragraphs"])
    return " ".join(line["text"] for _, line in spoken_lines(section))


def count_words(text):
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def _normalize_for_search(text):
    text = text.lower().replace("’", "'").replace("‘", "'").replace("–", "-")
    return re.sub(r"\s+", " ", text)


def _appears_in(needle, haystack):
    needle = _normalize_for_search(needle)
    haystack = _normalize_for_search(haystack)
    return re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", haystack) is not None


def _answers_as_list(answer):
    return answer if isinstance(answer, list) else [answer]


# --------------------------------------------------------------------------
# Listening: where each answer is heard
# --------------------------------------------------------------------------

def question_cue(group, q):
    """Phrase that marks where the answer is heard: an explicit cue, or the answer itself."""
    if q.get("cue"):
        return q["cue"]
    if group["type"] in COMPLETION_TYPES and not group.get("options"):
        return _answers_as_list(q.get("answer"))[0]
    if group["type"] == "choose_multiple" and group.get("cue"):
        return group["cue"]
    return None


def _find_span(text, phrase):
    """(start, end) of `phrase` in `text`, ignoring case, quote style, dash style and spacing."""
    parts = []
    for ch in phrase:
        if ch in "'’‘":
            parts.append("['’‘]")
        elif ch in "-–":
            parts.append("[-–]")
        elif ch.isspace():
            parts.append(r"\s+")
        else:
            parts.append(re.escape(ch))
    m = re.search("".join(parts), text, re.IGNORECASE)
    return (m.start(), m.end()) if m else None


def locate_listening_cues(test):
    """
    Map each question number to the script line where its answer is heard:
    {number: {"part": part_index, "line": script_index, "text": cue, "span": [start, end]}}.
    `span` is the cue's character range in that line. Questions whose cue
    cannot be found are left out.
    """
    found = {}
    for pi, part in enumerate(test.get("parts", [])):
        lines = spoken_lines(part)
        for group in part.get("groups", []):
            for q in group.get("questions", []):
                cue = question_cue(group, q)
                if not cue:
                    continue
                for li, line in lines:
                    span = _find_span(line["text"], cue)
                    if span:
                        found[q["number"]] = {"part": pi, "line": li, "text": cue, "span": list(span)}
                        break
    return found


# --------------------------------------------------------------------------
# Public (answer-free) views
# --------------------------------------------------------------------------

_PRIVATE_QUESTION_KEYS = ("answer", "explanation", "reference", "cue")
_PRIVATE_GROUP_KEYS = ("answer", "explanation", "reference", "cue")


def _strip_answers(sections_list):
    for section in sections_list:
        section.pop("factSources", None)
        for group in section.get("groups", []):
            for key in _PRIVATE_GROUP_KEYS:
                group.pop(key, None)
            for q in group.get("questions", []):
                for key in _PRIVATE_QUESTION_KEYS:
                    q.pop(key, None)


def public_reading_test(test):
    """Return a deep copy of a reading test with answer keys removed."""
    clean = copy.deepcopy(test)
    _strip_answers(clean.get("passages", []))
    return clean


def public_listening_test(test):
    """
    Return a deep copy of a listening test for candidates: no answers, and no
    transcript (the script contains every answer). Only the audio is kept.
    """
    clean = copy.deepcopy(test)
    clean.pop("speakers", None)
    clean.pop("pronunciations", None)
    for part in clean.get("parts", []):
        part.pop("script", None)
        part.pop("title", None)
        part.pop("context", None)
    _strip_answers(clean.get("parts", []))
    return clean


def public_writing_test(test):
    """Return a deep copy of a writing test without model answers or marking notes."""
    clean = copy.deepcopy(test)
    for task in clean.get("tasks", []):
        task.pop("modelAnswer", None)
        task.pop("examinerNotes", None)
    return clean


def public_test(test):
    module = test.get("module", "reading")
    if module == "writing":
        return public_writing_test(test)
    if module == "listening":
        return public_listening_test(test)
    return public_reading_test(test)


def listening_transcript(test):
    """
    Transcript for the results page: per part, the spoken lines with speaker
    names and times. `marks` gives the character range where each question's
    answer is heard, so the page can highlight it.
    """
    speakers = test.get("speakers", {})
    marks = {}
    for number, loc in locate_listening_cues(test).items():
        marks.setdefault((loc["part"], loc["line"]), []).append(
            {"q": number, "start": loc["span"][0], "end": loc["span"][1]})
    parts = []
    for pi, part in enumerate(test.get("parts", [])):
        lines = []
        for i, line in enumerate(part.get("script", [])):
            if "text" not in line:
                continue
            spk = speakers.get(line["speaker"], {})
            lines.append({
                "index": i,
                "speaker": spk.get("name", line["speaker"].title()),
                "narrator": line["speaker"] == "narrator",
                "text": line["text"],
                "start": line.get("start"),
                "end": line.get("end"),
                "marks": sorted(marks.get((pi, i), []), key=lambda m: m["start"]),
            })
        parts.append({
            "partNumber": part["partNumber"],
            "title": part.get("title", ""),
            "context": part.get("context", ""),
            "audio": part.get("audio"),
            "lines": lines,
        })
    return parts


def summarize_test(test):
    """Small card-sized summary used by the dashboard."""
    module = test.get("module", "reading")
    summary = {
        "id": test["id"],
        "module": module,
        "variant": test.get("variant", "academic"),
        "title": test["title"],
        "shortTitle": test.get("shortTitle", test["title"]),
        "durationMinutes": test.get("durationMinutes", 60),
        "sortOrder": test.get("sortOrder", 999),
    }
    if module == "reading":
        summary["totalQuestions"] = test.get("totalQuestions", 40)
        summary["passages"] = [{"number": p["passageNumber"], "title": p["title"]} for p in test.get("passages", [])]
    elif module == "listening":
        # Recording time plus the time to check answers at the end.
        summary["durationMinutes"] = test.get("durationMinutes", 30) + test.get("checkMinutes", 2)
        summary["totalQuestions"] = test.get("totalQuestions", 40)
        summary["parts"] = [{"number": p["partNumber"], "title": p.get("title", "")} for p in test.get("parts", [])]
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

def _validate_groups(test, label, errors):
    """Checks shared by reading and listening tests. Appends to `errors`."""
    tid = test.get("id", "<no id>")
    numbers = []
    for section, group in iter_groups(test):
        gtype = group.get("type")
        where = f"{tid} {label}{section_number(section)} [{gtype}]"
        text = passage_text(section)
        labels = {p.get("label") for p in section.get("paragraphs", []) if p.get("label")}

        if gtype not in ALL_QUESTION_TYPES:
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
            if gtype == "map_labelling":
                letters = {i.get("letter") for i in (group.get("map") or {}).get("items", []) if i.get("type") == "letter"}
                if not group.get("map"):
                    errors.append(f"{where}: map_labelling needs a map")
                elif set(option_keys) != letters:
                    errors.append(f"{where}: map letters {sorted(letters)} != options {option_keys}")
            for q in qs:
                if q.get("answer") not in keys:
                    errors.append(f"{where} Q{q['number']}: answer {q.get('answer')!r} not in {keys}")
                if not q.get("prompt"):
                    errors.append(f"{where} Q{q['number']}: missing prompt")

        if gtype in COMPLETION_TYPES:
            max_words = group.get("maxWords")
            has_word_list = bool(option_keys)
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
                    errors.append(f"{where} Q{q['number']}: none of {answers} found in the {'passage' if label == 'P' else 'transcript'}")

    expected = list(range(1, test.get("totalQuestions", 40) + 1))
    if sorted(numbers) != expected:
        missing = sorted(set(expected) - set(numbers))
        dupes = sorted({n for n in numbers if numbers.count(n) > 1})
        errors.append(f"{tid}: question numbers wrong (missing={missing}, duplicates={dupes})")


def validate_reading_test(test):
    """Return a list of human-readable problems (empty list = valid)."""
    errors = []
    tid = test.get("id", "<no id>")
    for key in ("id", "title", "passages"):
        if key not in test:
            errors.append(f"{tid}: missing '{key}'")
    if errors:
        return errors
    _validate_groups(test, "P", errors)
    return errors


def validate_listening_test(test, public_dir=None):
    """
    Return a list of problems. Checks the questions, the script, the speakers,
    that every answer can be located in the transcript, and (when public_dir is
    given) that each part's audio file exists and has been built.
    """
    errors = []
    tid = test.get("id", "<no id>")
    for key in ("id", "title", "parts", "speakers"):
        if key not in test:
            errors.append(f"{tid}: missing '{key}'")
    if errors:
        return errors
    parts = test["parts"]
    if [p.get("partNumber") for p in parts] != [1, 2, 3, 4]:
        errors.append(f"{tid}: must have parts 1-4")
    speakers = test["speakers"]
    for spk in speakers.values():
        if not spk.get("voice") or not spk.get("name"):
            errors.append(f"{tid}: each speaker needs a name and a voice")
    for part in parts:
        where = f"{tid} Part {part.get('partNumber')}"
        lines = spoken_lines(part)
        if not lines:
            errors.append(f"{where}: empty script")
        for i, line in lines:
            if line.get("speaker") not in speakers:
                errors.append(f"{where} line {i}: unknown speaker {line.get('speaker')!r}")
        if public_dir is not None:
            audio = part.get("audio") or {}
            if not audio.get("src") or not os.path.exists(os.path.join(public_dir, audio["src"])):
                errors.append(f"{where}: audio not built (run scripts/build_listening_audio.py)")
            elif any("start" not in line or "end" not in line for _, line in lines):
                errors.append(f"{where}: script timings missing (rebuild the audio)")
    _validate_groups(test, "Part ", errors)

    cues = locate_listening_cues(test)
    for pi, part in enumerate(parts):
        for group in part.get("groups", []):
            for q in group.get("questions", []):
                loc = cues.get(q["number"])
                if not loc:
                    errors.append(f"{tid} Q{q['number']}: cue {question_cue(group, q)!r} not found in the transcript")
                elif loc["part"] != pi:
                    errors.append(f"{tid} Q{q['number']}: cue found in the wrong part")
    return errors


def validate_test(test, public_dir=None):
    """Validate a test of any module (public_dir enables the listening audio checks)."""
    module = test.get("module")
    if module == "reading":
        return validate_reading_test(test)
    if module == "listening":
        return validate_listening_test(test, public_dir)
    if module == "writing":
        return validate_writing_test(test)
    return [f"{test.get('id', '<no id>')}: unknown module {module!r}"]


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
