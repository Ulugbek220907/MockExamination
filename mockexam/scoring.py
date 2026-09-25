"""
Reading scoring: answer normalisation, per-question marking, and the
approximate raw-score → band conversion for Academic Reading.
"""

import re

from . import content

# Approximate Academic Reading conversion (raw score out of 40 → band).
ACADEMIC_READING_BANDS = [
    (39, 9.0), (37, 8.5), (35, 8.0), (33, 7.5), (30, 7.0), (27, 6.5), (23, 6.0),
    (19, 5.5), (15, 5.0), (13, 4.5), (10, 4.0), (8, 3.5), (6, 3.0), (4, 2.5), (0, 2.0),
]

TYPE_LABELS = {
    "true_false_not_given": "True / False / Not Given",
    "yes_no_not_given": "Yes / No / Not Given",
    "multiple_choice": "Multiple choice",
    "choose_multiple": "Multiple choice (choose more than one)",
    "matching_headings": "Matching headings",
    "matching_information": "Matching information",
    "matching_features": "Matching features",
    "matching_sentence_endings": "Matching sentence endings",
    "classification": "Classification",
    "note_completion": "Note completion",
    "summary_completion": "Summary completion",
    "table_completion": "Table completion",
    "flow_chart_completion": "Flow-chart completion",
    "sentence_completion": "Sentence completion",
    "short_answer": "Short-answer questions",
}


def band_for_raw_score(raw):
    for minimum, band in ACADEMIC_READING_BANDS:
        if raw >= minimum:
            return band
    return 2.0


def cefr_for_band(band):
    if band >= 8.5:
        return "C2"
    if band >= 7.0:
        return "C1"
    if band >= 5.5:
        return "B2"
    if band >= 4.0:
        return "B1"
    return "A2 or below"


_EDGE_PUNCT = " \t\n.,;:!?\"'“”‘’()[]"


def normalize_answer(value):
    if value is None:
        return ""
    text = str(value).lower().replace("’", "'").replace("‘", "'")
    text = text.replace("-", " ").replace("–", " ")
    text = re.sub(r"\s+", " ", text).strip(_EDGE_PUNCT)
    return text


def _display_answer(answer):
    if isinstance(answer, list):
        return " / ".join(answer)
    return str(answer)


def _gap_context(group, number):
    """Text around a gap, used as the 'question' shown on the results page."""
    marker = "{{%d}}" % number
    c = group.get("content")
    fragment = ""
    if isinstance(c, str):
        for sentence in re.split(r"(?<=[.!?])\s+", c):
            if marker in sentence:
                fragment = sentence
                break
    elif isinstance(c, list):
        fragment = next((line for line in c if marker in line), "")
    elif isinstance(c, dict):
        for row in c.get("rows", []):
            if any(marker in cell for cell in row):
                fragment = " | ".join(row)
                break
    fragment = fragment.lstrip("•#- ").replace(marker, "______")
    return re.sub(r"\{\{\d+\}\}", "…", fragment)


def _question_prompt(group, q):
    gtype = group["type"]
    if gtype in content.CONTENT_GAP_TYPES:
        return _gap_context(group, q["number"])
    if gtype == "sentence_completion":
        return re.sub(r"\{\{\d+\}\}", "______", q.get("prompt", ""))
    if gtype == "choose_multiple":
        return group.get("prompt", "")
    return q.get("prompt", "")


def _strip_article(text):
    return re.sub(r"^(the|a|an) ", "", text)


def _is_correct_single(group, q, candidate):
    cand = normalize_answer(candidate)
    if not cand:
        return False
    raw_answers = q["answer"] if isinstance(q["answer"], list) else [q["answer"]]
    answers = [normalize_answer(a) for a in raw_answers]
    if group["type"] in content.COMPLETION_TYPES and not group.get("options"):
        # Typed answers may carry an optional leading article, e.g. "the rimu" for "rimu".
        cand = _strip_article(cand)
        answers = [_strip_article(a) for a in answers]
    return cand in answers


def evaluate_reading(test, submitted, candidate_name="Candidate", time_spent=0):
    submitted = {str(k): v for k, v in (submitted or {}).items()}
    results = []
    passage_breakdown = {}
    type_breakdown = {}

    for passage in test["passages"]:
        pnum = passage["passageNumber"]
        passage_breakdown[str(pnum)] = {"title": passage["title"], "total": 0, "correct": 0}

        for group in passage["groups"]:
            gtype = group["type"]
            numbers = content.question_numbers(group)
            marks = {}

            if gtype == "choose_multiple":
                correct_set = {normalize_answer(a) for a in group["answer"]}
                used = set()
                for n in numbers:
                    cand = normalize_answer(submitted.get(str(n), ""))
                    ok = bool(cand) and cand in correct_set and cand not in used
                    if ok:
                        used.add(cand)
                    marks[n] = ok
            else:
                for q in group["questions"]:
                    marks[q["number"]] = _is_correct_single(group, q, submitted.get(str(q["number"]), ""))

            tb = type_breakdown.setdefault(gtype, {"label": TYPE_LABELS.get(gtype, gtype), "total": 0, "correct": 0})
            for q in group["questions"]:
                n = q["number"]
                ok = marks[n]
                passage_breakdown[str(pnum)]["total"] += 1
                tb["total"] += 1
                if ok:
                    passage_breakdown[str(pnum)]["correct"] += 1
                    tb["correct"] += 1

                if gtype == "choose_multiple":
                    correct_display = " and ".join(group["answer"]) + " (in either order)"
                    explanation = group.get("explanation", "")
                    reference = group.get("reference", "")
                else:
                    correct_display = _display_answer(q["answer"])
                    if group.get("options") and gtype in content.COMPLETION_TYPES:
                        opt = next((o for o in group["options"] if o["key"] == q["answer"]), None)
                        if opt:
                            correct_display = f"{q['answer']} ({opt['text']})"
                    explanation = q.get("explanation", "")
                    reference = q.get("reference", "")

                results.append({
                    "number": n,
                    "passageNumber": pnum,
                    "type": gtype,
                    "typeLabel": TYPE_LABELS.get(gtype, gtype),
                    "prompt": _question_prompt(group, q),
                    "candidateAnswer": submitted.get(str(n), ""),
                    "correctAnswer": correct_display,
                    "isCorrect": ok,
                    "explanation": explanation,
                    "reference": reference,
                })

    results.sort(key=lambda r: r["number"])
    raw = sum(1 for r in results if r["isCorrect"])
    band = band_for_raw_score(raw)
    return {
        "testId": test["id"],
        "title": test["title"],
        "candidateName": candidate_name,
        "rawScore": raw,
        "totalQuestions": len(results),
        "bandScore": band,
        "cefrLevel": cefr_for_band(band),
        "timeSpentSeconds": int(time_spent or 0),
        "passageBreakdown": passage_breakdown,
        "typeBreakdown": type_breakdown,
        "results": results,
    }
