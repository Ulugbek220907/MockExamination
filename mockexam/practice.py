"""
Practice by question type: short Reading sets with only one type of question.

A set is one passage of a full test with only the question groups of the
chosen type. Sets are untimed, have no band, and are not saved, so they never
change the student's history or progress chart.

  types_overview(tests, rows)     every type with its sets and the student's accuracy, weakest first
  sets_for(tests, gtype)          [(test, passage index)] that hold the type, in test order
  build_set(test, index, gtype)   the set as a reading test (still with answers; use content.public_test)
  mark_set(test, index, gtype, answers)  marked like a full test, without a band
"""

import copy

from . import content, scoring

MODULE = "reading"


def sets_for(tests, gtype):
    out = []
    for test in tests:
        if test.get("module") != MODULE:
            continue
        for i, passage in enumerate(test.get("passages", [])):
            if any(g.get("type") == gtype for g in passage.get("groups", [])):
                out.append((test, i))
    return out


def known_types(tests):
    """Every Reading question type found in the tests, in the order of TYPE_LABELS."""
    found = {g.get("type") for t in tests if t.get("module") == MODULE for _, g in content.iter_groups(t)}
    return [k for k in scoring.TYPE_LABELS if k in found]


def build_set(test, index, gtype):
    passage = copy.deepcopy(test["passages"][index])
    passage["groups"] = [g for g in passage.get("groups", []) if g.get("type") == gtype]
    label = scoring.TYPE_LABELS.get(gtype, gtype)
    questions = sum(len(g.get("questions", [])) for g in passage["groups"])
    return {
        "id": f"practice-{gtype.replace('_', '-')}",
        "module": MODULE,
        "variant": test.get("variant", "academic"),
        "title": label,
        "shortTitle": label,
        "durationMinutes": 0,
        "totalQuestions": questions,
        "passages": [passage],
        "practice": {"type": gtype, "testId": test["id"], "passage": index},
    }


def mark_set(test, index, gtype, answers):
    drill = build_set(test, index, gtype)
    results, _, types = scoring.mark_sections(drill, answers)
    for r in results:
        r["passageNumber"] = r.pop("section")
    return {
        "type": gtype,
        "title": drill["title"],
        "rawScore": sum(1 for r in results if r["isCorrect"]),
        "totalQuestions": len(results),
        "results": results,
        "typeBreakdown": types,
        "practice": drill["practice"],
    }


def accuracy(rows):
    """{type: [correct, total]} summed over Reading attempts' saved breakdowns."""
    out = {}
    for row in rows or []:
        types = ((row.get("breakdown") or {}).get("types")) or {}
        for key, v in types.items():
            if not isinstance(v, dict):
                continue
            acc = out.setdefault(key, [0, 0])
            acc[0] += int(v.get("correct") or 0)
            acc[1] += int(v.get("total") or 0)
    return out


def types_overview(tests, rows):
    """
    One entry per Reading question type. Types the student has answered come
    first, weakest first; the ones they have not met yet follow in the usual order.
    """
    acc = accuracy(rows)
    items = []
    for i, key in enumerate(known_types(tests)):
        correct, total = acc.get(key, (0, 0))
        items.append({
            "type": key, "label": scoring.TYPE_LABELS[key], "sets": len(sets_for(tests, key)),
            "correct": correct, "total": total, "order": i,
        })
    items.sort(key=lambda x: (x["total"] == 0, x["correct"] / x["total"] if x["total"] else 0, x["order"]))
    for x in items:
        x.pop("order")
    return items
