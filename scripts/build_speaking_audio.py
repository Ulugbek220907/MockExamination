#!/usr/bin/env python3
"""
Generate the examiner's voice for the Speaking tests in content/speaking/*.json.

Uses the same Kokoro-82M setup as the Listening audio (see
scripts/build_listening_audio.py for installing the model files):

    python scripts/build_speaking_audio.py --models ~/tts-models
    python scripts/build_speaking_audio.py --models ~/tts-models --only speaking-01
    python scripts/build_speaking_audio.py --models ~/tts-models --only speaking-34,speaking-35
    python scripts/build_speaking_audio.py --models ~/tts-models --missing   # only clips not built yet

Every question's "say" text (what the examiner says before the candidate
answers) becomes public/audio/<test-id>/<question-key>.mp3, and so do the
test's "prompts" (e.g. "start speaking now", "end of the test"). The file and
its duration are recorded in the content file as "audio": {"src", "duration"}.

    python scripts/build_speaking_audio.py --models ~/tts-models --phrases

builds the short phrases the AI examiner uses between questions ("Thank you.")
in every examiner's voice, as public/audio/examiners/<voice>/<phrase>.mp3.
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_listening_audio import BASE_DIR, SAMPLE_RATE, Synth, encode_mp3, level, silence  # noqa: E402

CONTENT_DIR = os.path.join(BASE_DIR, "content", "speaking")
GAP_SENTENCE = 0.35  # pause between sentences in one prompt


def split_sentences(text):
    """Speak long prompts sentence by sentence so the pauses sound natural."""
    parts, current = [], ""
    for chunk in text.replace("? ", "?\n").replace(". ", ".\n").replace("! ", "!\n").split("\n"):
        current = f"{current} {chunk}".strip()
        if len(current) > 25:  # keep very short sentences ("All right?") with the next one
            parts.append(current)
            current = ""
    if current:
        parts.append(current)
    return parts


def build_clip(synth, test, key, text):
    ex = test["examiner"]
    chunks = [silence(0.3)]
    for i, sentence in enumerate(split_sentences(text)):
        if i:
            chunks.append(silence(GAP_SENTENCE))
        chunks.append(level(synth.speak(sentence, ex["voice"], ex["lang"], ex.get("speed", 1.0),
                                        test.get("pronunciations"))))
    chunks.append(silence(0.2))
    samples = np.concatenate(chunks)
    rel = f"audio/{test['id']}/{key}.mp3"
    size = encode_mp3(samples, os.path.join(BASE_DIR, "public", rel))
    return {"src": rel, "duration": round(len(samples) / SAMPLE_RATE, 2)}, size


# What the AI examiner can say between questions, in every examiner's voice.
EXAMINER_PHRASES = {
    "thank-you": "Thank you.",
    "more": "Can you tell me anything more about that?",
}


def build_phrases(synth):
    voices = {}
    for name in sorted(f for f in os.listdir(CONTENT_DIR) if f.endswith(".json")):
        with open(os.path.join(CONTENT_DIR, name), encoding="utf-8") as f:
            ex = json.load(f)["examiner"]
        voices[ex["voice"]] = ex
    for voice, ex in sorted(voices.items()):
        for key, text in EXAMINER_PHRASES.items():
            samples = np.concatenate([silence(0.1), level(synth.speak(text, voice, ex["lang"], ex.get("speed", 1.0))), silence(0.15)])
            encode_mp3(samples, os.path.join(BASE_DIR, "public", "audio", "examiners", voice, f"{key}.mp3"))
        print(f"✓ {voice}: {len(EXAMINER_PHRASES)} phrases")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", default=os.path.expanduser("~/tts-models"), help="folder with the Kokoro model files")
    parser.add_argument("--only", help="build only these test ids, comma-separated, e.g. speaking-01,speaking-02")
    parser.add_argument("--missing", action="store_true", help="build only clips that have no audio file yet")
    parser.add_argument("--phrases", action="store_true", help="build only the AI examiner's phrases")
    args = parser.parse_args()

    synth = Synth(args.models)
    if args.phrases:
        return build_phrases(synth)
    only = set(args.only.split(",")) if args.only else None
    public = os.path.join(BASE_DIR, "public")
    for name in sorted(f for f in os.listdir(CONTENT_DIR) if f.endswith(".json")):
        path = os.path.join(CONTENT_DIR, name)
        with open(path, encoding="utf-8") as f:
            test = json.load(f)
        if only and test["id"] not in only:
            continue
        total_size, total_time = 0, 0.0
        items = [(q["key"], q) for part in test["parts"] for q in part["questions"]]
        items += list(test.get("prompts", {}).items())
        if args.missing:
            items = [(key, item) for key, item in items
                     if not (item.get("audio") or {}).get("src") or not os.path.exists(os.path.join(public, item["audio"]["src"]))]
            if not items:
                continue
        for key, item in items:
            item["audio"], size = build_clip(synth, test, key, item["say"])
            total_size += size
            total_time += item["audio"]["duration"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(test, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"✓ {test['id']}: {len(items)} clips, {total_time / 60:.1f} min, {total_size / 1e6:.1f} MB")


if __name__ == "__main__":
    sys.exit(main())
