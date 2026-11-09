"""
The adaptive Speaking test: with the AI examiner, how many questions the candidate gets depends on how they speak.

  Part 1   7 questions to begin with, 8 or 9 when the candidate is doing well.
  Part 2   the long turn (cue card) and its follow-up question, always.
  Part 3   3 questions to begin with. Then, after each answer, the examiner decides whether to ask one more:
           a candidate whose first two parts and answers so far are around band 5 or below stops at 3, and the stronger
           the performance the more questions follow, up to 9 or 10 for the strongest.

How the examiner knows: every answer is analysed in the background as soon as it has been uploaded, with the same
"listen to one answer" call the final rating uses (speaking_ai.analyse_answer), so the analysis is ready while the
candidate answers the next questions. Each answer gets a provisional band, and the bands are averaged with weights
(a long answer says more than a short one; the Part 2 long turn counts most). The final rating of the whole test reuses
these analyses, so the adaptive test costs no more AI calls than the fixed one, and fewer when the examiner stops early.

The browser asks for the plan (POST /api/speaking/submissions/<id>/plan) when it reaches the end of what is planned in
Part 1 or Part 3: the answer is the ordered list of question keys, one longer when the examiner wants one more. The plan
only ever grows by one question at a time, and only after the last planned question of that part has been answered.

What is kept: the plan (how many questions in Parts 1 and 3) in speaking_submissions.ai_review["adaptive"], a few bytes;
the analyses stay in memory while the test runs (and are rebuilt by the final rating if the server restarted).
SPEAKING_ADAPTIVE=0 switches it off: the test is then the fixed one.
"""

import concurrent.futures
import logging
import os
import threading
import time

from . import content, speaking_ai
from .db import iso, now
from .writing import round_to_half_band

log = logging.getLogger("mockexam.speaking_adaptive")

ENABLED = os.environ.get("SPEAKING_ADAPTIVE", "1").strip() != "0"

PART1_MIN, PART1_MAX = 7, 9
PART3_MIN, PART3_MAX = 3, 10
# What the examiner does not yet know enough to judge: the length of the earlier fixed test (6 in Part 3) is kept short.
PART3_UNKNOWN = 5
MIN_EVIDENCE = 3         # analysed answers needed before the examiner trusts its own estimate
PRIOR_BAND = 5.5         # one answer's worth of doubt, so that a single answer cannot decide the test
PRIOR_WEIGHT = 1.0
NO_ANSWER_BAND = 2.0     # an answer with nothing in it
GATE_WAIT_SECONDS = 8    # how long the first Part 3 decision waits for the Part 2 analysis, if it is still running
KEEP_SECONDS = 6 * 3600  # analyses of a test nobody finished are forgotten after this

# What the examiner wants, from the estimated band: Part 1 questions, and Part 3 questions.
PART1_STRONG, PART1_FAIR = 7.0, 5.5
PART3_FLOOR = 5.0        # at this band or below, Part 3 stays at its 3 core questions


class AdaptiveError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def enabled():
    return ENABLED and speaking_ai.configured()


# --------------------------------------------------------------------------
# The test's questions
# --------------------------------------------------------------------------

def part_keys(test, number):
    """The question keys of one part, in the order they are asked."""
    return [q["key"] for part in test.get("parts", []) if part.get("partNumber") == number for q in part.get("questions", [])]


def limits(test):
    """(most questions Part 1 can have, most questions Part 3 can have) in this test."""
    return min(PART1_MAX, len(part_keys(test, 1))), min(PART3_MAX, len(part_keys(test, 3)))


def initial_state(test):
    return {"v": 1, "plan": {"part1": min(PART1_MIN, len(part_keys(test, 1))), "part3": min(PART3_MIN, len(part_keys(test, 3)))},
            "log": []}


def plan_keys(test, plan):
    """Every question key the test has so far, in order."""
    return (part_keys(test, 1)[:plan["part1"]] + part_keys(test, 2) + part_keys(test, 3)[:plan["part3"]])


def state_of(sub):
    review = sub.get("ai_review") if isinstance(sub.get("ai_review"), dict) else {}
    state = review.get("adaptive")
    return state if isinstance(state, dict) and isinstance(state.get("plan"), dict) else None


def asked_keys(test, state):
    """The questions the examiner asked (for the final rating); the fixed test's questions when the test was not adaptive."""
    if not state:
        return {q["key"] for _, q in content.fixed_speaking_questions(test)}
    return set(plan_keys(test, state["plan"]))


# --------------------------------------------------------------------------
# Judging performance (no I/O: these are what the tests check)
# --------------------------------------------------------------------------

def _clamp(value, low, high):
    return max(low, min(high, value))


def answer_band(analysis):
    """One answer's provisional band, or None when there is nothing to judge (the model could not listen)."""
    if not analysis or analysis.get("error"):
        return None
    notes = analysis.get("notes") or {}
    stats = analysis.get("stats") or {}
    if notes.get("relevance") == "no answer" or not stats.get("words"):
        return NO_ANSWER_BAND
    bands = [v for v in (notes.get("bands") or {}).values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not bands:
        return None
    band = sum(bands) / len(bands)
    if notes.get("english") is False:
        band = min(band, 3.0)
    if notes.get("relevance") == "off topic":
        band = min(band, 4.0)
    elif notes.get("relevance") == "partly answers":
        band -= 0.5
    return _clamp(band, 0.0, 9.0)


def answer_weight(analysis, part_number, long_turn=False):
    """How much one answer counts: more for a longer answer, and most for the Part 2 long turn."""
    stats = (analysis or {}).get("stats") or {}
    if long_turn:
        return 2.0 * _clamp((stats.get("speakingTime") or 0) / 60.0, 0.6, 2.0)
    scale = 30.0 if part_number == 1 else 50.0
    return _clamp((stats.get("words") or 0) / scale, 0.35, 1.5)


def weighted_band(items):
    """(band rounded to a half band, number of answers) for [(band, weight)], with a little doubt mixed in."""
    items = [(b, w) for b, w in items if b is not None]
    if not items:
        return None, 0
    total = sum(w for _, w in items)
    band = (sum(b * w for b, w in items) + PRIOR_BAND * PRIOR_WEIGHT) / (total + PRIOR_WEIGHT)
    return round_to_half_band(band), len(items)


def performance(test, records, parts=(1, 2, 3)):
    """
    {"parts": {1: (band, answers), 2: ..., 3: ...}, "overall": (band, answers)} from the analyses so far
    ({question key: analysis}). `parts` limits which parts count towards "overall".
    """
    by_part = {1: [], 2: [], 3: []}
    for part, q in content.speaking_questions(test):
        rec = records.get(q["key"])
        if rec is None:
            continue
        number = part["partNumber"]
        band = answer_band(rec)
        if band is not None and number in by_part:
            by_part[number].append((band, answer_weight(rec, number, q.get("type") == "long_turn")))
    return {"parts": {n: weighted_band(items) for n, items in by_part.items()},
            "overall": weighted_band([x for n in parts for x in by_part[n]])}


def part1_target(band, evidence):
    """How many Part 1 questions this performance deserves: 7, 8 or 9."""
    if band is None or evidence < MIN_EVIDENCE:
        return PART1_MIN
    if band >= PART1_STRONG:
        return PART1_MAX
    if band >= PART1_FAIR:
        return PART1_MIN + 1
    return PART1_MIN


def part3_target(band, evidence):
    """How many Part 3 questions this performance deserves: 3 at band 5 or below, one more for each half band above."""
    if band is None or evidence < MIN_EVIDENCE:
        return PART3_UNKNOWN
    return int(_clamp(PART3_MIN + round(2 * (band - PART3_FLOOR)), PART3_MIN, PART3_MAX))


def decide(test, plan, after, records):
    """
    The plan after the candidate has answered `after`, and why: (plan, note). The plan grows by at most one question,
    and only when `after` is the last question planned in Part 1 or in Part 3.
    """
    plan = dict(plan)
    most1, most3 = limits(test)
    p1, p3 = part_keys(test, 1), part_keys(test, 3)
    if p1 and plan["part1"] < most1 and after == p1[plan["part1"] - 1]:
        band, evidence = performance(test, records, parts=(1,))["overall"]
        if part1_target(band, evidence) > plan["part1"]:
            plan["part1"] += 1
            return plan, {"after": after, "part": 1, "band": band, "answers": evidence, "more": True}
        return plan, {"after": after, "part": 1, "band": band, "answers": evidence, "more": False}
    if p3 and plan["part3"] < most3 and after == p3[plan["part3"] - 1]:
        band, evidence = performance(test, records)["overall"]
        if part3_target(band, evidence) > plan["part3"]:
            plan["part3"] += 1
            return plan, {"after": after, "part": 3, "band": band, "answers": evidence, "more": True}
        return plan, {"after": after, "part": 3, "band": band, "answers": evidence, "more": False}
    return plan, None


# --------------------------------------------------------------------------
# Analysing answers as they arrive
# --------------------------------------------------------------------------

_LOCK = threading.Lock()
_RESULTS = {}    # submission id -> {question key: analysis}
_INFLIGHT = {}   # (submission id, question key) -> Future


def _prune():
    """Forget the analyses of tests nobody has touched for KEEP_SECONDS (abandoned tests). Call with _LOCK held."""
    cutoff = time.time() - KEEP_SECONDS
    for sub_id in [s for s, answers in _RESULTS.items() if all(a.get("at", 0) < cutoff for a in answers.values())]:
        del _RESULTS[sub_id]


def analyses(sub_id):
    """The analyses finished so far for one test: {question key: analysis}."""
    with _LOCK:
        return dict(_RESULTS.get(sub_id, {}))


def forget(sub_id):
    with _LOCK:
        _RESULTS.pop(sub_id, None)
        for key in [k for k in _INFLIGHT if k[0] == sub_id]:
            _INFLIGHT.pop(key, None)


def _analyse(db, files, store, sub_id, test_id, key, rec_id):
    result = {"rec": rec_id, "error": True, "at": time.time()}
    try:
        rows = db.select("recordings", {"submission_id": sub_id, "question_key": key}, limit=1)
        if rows and rows[0]["id"] == rec_id:  # not replaced by a newer recording meanwhile
            test = store.get_test(test_id)
            part, q = next((p, q) for p, q in content.speaking_questions(test) if q["key"] == key)
            data = files.get(rows[0]["path"])
            if data is None:
                raise speaking_ai.ReviewError("A recording is missing.")
            result = {**speaking_ai.analyse_answer(part, q, rows[0], data), "rec": rec_id, "at": time.time()}
    except Exception as e:  # the final rating tries again for an answer that failed here
        log.warning("Adaptive Speaking: could not analyse %s of submission %s: %s", key, sub_id, e)
    with _LOCK:
        _prune()
        _RESULTS.setdefault(sub_id, {})[key] = result
    return result


def queue_analysis(db, files, store, sub, key, rec_id):
    """
    Start analysing a saved answer in the background (only for a test that adapts). Does nothing when this very recording
    is already being analysed or has been analysed, so asking twice never costs a second AI call.
    """
    if not state_of(sub) or sub.get("mode") != "ai":
        return None
    slot = (sub["id"], key)
    with _LOCK:
        known = _INFLIGHT.get(slot)
        if known and known[0] == rec_id:
            return known[1]
        if (_RESULTS.get(sub["id"], {}).get(key) or {}).get("rec") == rec_id:
            return None
        future = speaking_ai._POOL.submit(_analyse, db, files, store, sub["id"], sub["test_id"], key, rec_id)
        _INFLIGHT[slot] = (rec_id, future)

    def done(f):
        with _LOCK:
            if (_INFLIGHT.get(slot) or (None, None))[1] is f:
                del _INFLIGHT[slot]
    future.add_done_callback(done)
    return future


def wait_for(sub_id, keys=None, timeout=GATE_WAIT_SECONDS):
    """Wait for analyses that are still running (all of this test's, or only `keys`). Returns when done or on timeout."""
    with _LOCK:
        pending = [f for (s, k), (_, f) in _INFLIGHT.items() if s == sub_id and (keys is None or k in keys)]
    if pending:
        concurrent.futures.wait(pending, timeout=timeout)


def usable(sub_id, recordings):
    """{key: analysis} for the analyses that belong to the recordings the test now has (not to replaced ones)."""
    current = {r["question_key"]: r["id"] for r in recordings}
    return {key: a for key, a in analyses(sub_id).items() if current.get(key) == a.get("rec") and not a.get("error")}


# --------------------------------------------------------------------------
# The plan
# --------------------------------------------------------------------------

def public_plan(test, state, note=None):
    plan = state["plan"]
    out = {"keys": plan_keys(test, plan), "part1": plan["part1"], "part3": plan["part3"]}
    if note is not None:
        out["more"] = bool(note.get("more"))
    return out


def next_plan(db, files, store, sub, test, after=None):
    """
    The plan for a test that adapts, after the candidate answered `after` (a question key; none = just the plan).
    May wait a few seconds the first time Part 3 is decided, for the Part 2 analysis to finish.
    """
    state = state_of(sub)
    if not state or sub.get("mode") != "ai":
        raise AdaptiveError("This test does not adapt to your answers.", 409)
    review = sub["ai_review"]
    recordings = db.select("recordings", {"submission_id": sub["id"]}, limit=100)
    # After a restart the analyses are gone: start them again for the answers that are here (a no-op for the others).
    known = analyses(sub["id"])
    for r in recordings:
        if (known.get(r["question_key"]) or {}).get("rec") != r["id"]:
            queue_analysis(db, files, store, sub, r["question_key"], r["id"])

    if review.get("status") != "recording" or after is None:
        return public_plan(test, state)
    p3 = part_keys(test, 3)
    if p3 and state["plan"]["part3"] == min(PART3_MIN, len(p3)) and after == p3[state["plan"]["part3"] - 1]:
        wait_for(sub["id"], {"p2-talk"})  # the first Part 3 decision rests on how Part 2 went
    plan, note = decide(test, state["plan"], after, usable(sub["id"], recordings))
    if note is not None and note["answers"] < MIN_EVIDENCE:
        # Too little to go on: the model is slower than the candidate. Wait a few seconds for the answers it is still
        # listening to, rather than deciding in the dark.
        wait_for(sub["id"], timeout=GATE_WAIT_SECONDS)
        plan, note = decide(test, state["plan"], after, usable(sub["id"], recordings))
    if note is None:
        return public_plan(test, state)
    state = dict(state)
    state["plan"] = plan
    state["log"] = (state.get("log") or [])[-30:] + [{**note, "at": iso(now())}]
    review = dict(review)
    review["adaptive"] = state
    db.update("speaking_submissions", {"id": sub["id"], "status": "recording"}, {"ai_review": review})
    return public_plan(test, state, note)


def summary(test, state, records=None):
    """What the report says about how the test adapted (no analyses, no bands of single answers)."""
    most1, most3 = limits(test)
    plan = state["plan"]
    out = {"plan": {"part1": plan["part1"], "part3": plan["part3"]},   # so the finished test still knows what was asked
           "part1Questions": plan["part1"], "part3Questions": plan["part3"], "part1Most": most1, "part3Most": most3,
           "part1Core": min(PART1_MIN, most1), "part3Core": min(PART3_MIN, most3)}
    if records:
        perf = performance(test, records)
        out["parts"] = {str(n): band for n, (band, _) in perf["parts"].items() if band is not None}
    return out
