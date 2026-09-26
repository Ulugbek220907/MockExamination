#!/usr/bin/env python3
"""
Quality check for generated Listening audio.

Transcribes every part with Whisper (faster-whisper) and checks, for every
question, that the words of its answer (completion questions) or its cue
phrase (other question types) can actually be heard at the time recorded for
that script line. This catches mispronounced names, numbers and key words
before the audio is published.

    pip install faster-whisper
    python scripts/check_listening_audio.py [--only listening-01] [--model base.en]
"""

import argparse
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from mockexam import content  # noqa: E402

NUMBER_WORDS = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven",
    "8": "eight", "9": "nine", "10": "ten", "11": "eleven", "12": "twelve", "20": "twenty", "30": "thirty",
    "40": "forty", "50": "fifty",
}


def norm_tokens(text):
    text = text.lower().replace("’", "'").replace("-", " ")
    return re.findall(r"[a-z0-9']+", text)


def expand_numbers(tokens):
    out = []
    for t in tokens:
        if t.isdigit() and len(t) == 2 and t not in NUMBER_WORDS:
            tens, ones = t[0] + "0", t[1]
            out += [NUMBER_WORDS.get(tens, tens)] + ([NUMBER_WORDS[ones]] if ones != "0" else [])
        else:
            out.append(NUMBER_WORDS.get(t, t))
    return out


def heard(expected, words):
    """True if the expected tokens (or their spelled-number form) occur in order in the heard words."""
    heard_tokens = []
    for w in words:
        heard_tokens += expand_numbers(norm_tokens(w))
    joined = " " + " ".join(heard_tokens) + " "
    target = " ".join(expand_numbers(norm_tokens(expected)))
    if f" {target} " in joined:
        return True
    # Spelled-out words (K-O-W-A-L-S-K-I) may be heard as single letters or as the word.
    letters = "".join(norm_tokens(expected))
    return letters and letters in "".join(heard_tokens)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    parser.add_argument("--model", default="base.en")
    args = parser.parse_args()

    from faster_whisper import WhisperModel

    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    failures = 0
    for test in content.load_json_dir(os.path.join(BASE_DIR, "content", "listening")):
        if args.only and test["id"] != args.only:
            continue
        cues = content.locate_listening_cues(test)
        for pi, part in enumerate(test["parts"]):
            audio = os.path.join(BASE_DIR, "public", part["audio"]["src"])
            segments, _ = model.transcribe(audio, language="en", word_timestamps=True, vad_filter=False)
            words = [(w.start, w.end, w.word) for s in segments for w in (s.words or [])]
            for _, group in content.iter_groups(test):
                for q in group["questions"]:
                    loc = cues.get(q["number"])
                    if not loc or loc["part"] != pi:
                        continue
                    line = part["script"][loc["line"]]
                    window = [w for s, e, w in words if s >= line["start"] - 1.5 and e <= line["end"] + 1.5]
                    if group["type"] in content.COMPLETION_TYPES and not group.get("options"):
                        answers = q["answer"] if isinstance(q["answer"], list) else [q["answer"]]
                        ok = any(heard(a, window) for a in answers)
                        what = answers[0]
                    else:
                        ok = heard(q.get("cue", ""), window) or len(norm_tokens(q.get("cue", ""))) > 4 and \
                            sum(t in norm_tokens(" ".join(window)) for t in norm_tokens(q["cue"])) >= 0.75 * len(norm_tokens(q["cue"]))
                        what = q.get("cue", "")
                    status = "ok " if ok else "MISS"
                    if not ok:
                        failures += 1
                    print(f"{status} {test['id']} Q{q['number']:>2} [{line['start']:6.1f}s] expected “{what}” | heard: {' '.join(window)[:110]}")
    print(f"\n{failures} problem(s) found.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
