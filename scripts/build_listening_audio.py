#!/usr/bin/env python3
"""
Generate Listening test audio from the scripts in content/listening/*.json.

Speech is synthesised with Kokoro-82M (Apache-2.0 licence, commercial use
allowed) through the kokoro-onnx package. The model files are large, so they
are not committed; download them once:

    mkdir -p ~/tts-models && cd ~/tts-models
    curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
    curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
    pip install kokoro-onnx soundfile lameenc

Then:

    python scripts/build_listening_audio.py --models ~/tts-models            # all tests
    python scripts/build_listening_audio.py --models ~/tts-models --only listening-01

It writes public/audio/sound-check.mp3 (the volume check on the instructions
screen) and, for every part, public/audio/<test-id>/part<N>.mp3, and
records, in the content file, the duration of the part and the start/end time
of every script line (used for the transcript and "listen again" buttons).
Synthesised lines are cached in .tts-cache/, so re-running after editing one
line only re-synthesises that line.

If a word is mispronounced, add it to the test's "pronunciations" map with the
correct IPA (the phoneme set Kokoro uses), e.g. {"Pilates": "pɪlˈɑːtiːz"}, and
rebuild. A line's "tts" field can also replace the text that is spoken.
"""

import argparse
import hashlib
import json
import os
import re
import sys

import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, "content", "listening")
AUDIO_DIR = os.path.join(BASE_DIR, "public", "audio")
CACHE_DIR = os.path.join(BASE_DIR, ".tts-cache")

SAMPLE_RATE = 24000
BITRATE_KBPS = 48
LEAD_IN = 0.6          # silence at the start of each part (seconds)
GAP_SAME = 0.35        # between two lines by the same speaker
GAP_CHANGE = 0.5       # when the speaker changes
GAP_NARRATOR = 0.9     # around narrator instructions
TARGET_RMS_DB = -20.0  # every line is levelled to this loudness
PEAK_DB = -1.0

# Short clip played on the instructions screen so candidates can set their volume.
SOUND_CHECK_TEXT = ("This is a sound check. If you can hear this message clearly, you are ready to begin. "
                    "If not, turn up the volume on your device, or use the volume control on the screen.")
SOUND_CHECK_VOICE = ("bm_george", "en-gb")


def db_to_amp(db):
    return 10 ** (db / 20)


class Synth:
    def __init__(self, models_dir):
        from kokoro_onnx import Kokoro

        self.kokoro = Kokoro(
            os.path.join(models_dir, "kokoro-v1.0.onnx"),
            os.path.join(models_dir, "voices-v1.0.bin"),
        )
        os.makedirs(CACHE_DIR, exist_ok=True)

    def phonemes_with_fixes(self, text, lang, pronunciations):
        """
        Phonemes for `text` with mispronounced words corrected, or None when no
        word in `pronunciations` occurs in the text. `pronunciations` maps a
        word to its correct IPA, e.g. {"Pilates": "pɪlˈɑːtiːz"}.
        """
        hits = [w for w in pronunciations if re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE)]
        if not hits:
            return None
        phonemes = self.kokoro.tokenizer.phonemize(text, lang=lang)
        for word in hits:
            wrong = self.kokoro.tokenizer.phonemize(word, lang=lang).strip(" .")
            if wrong not in phonemes:
                raise RuntimeError(f"could not find the phonemes of {word!r} ({wrong}) in: {phonemes}")
            phonemes = phonemes.replace(wrong, pronunciations[word])
        return phonemes

    def speak(self, text, voice, lang, speed, pronunciations=None):
        phonemes = self.phonemes_with_fixes(text, lang, pronunciations or {})
        source = phonemes if phonemes is not None else text
        key = hashlib.sha1(f"{voice}|{lang}|{speed}|{source}".encode("utf-8")).hexdigest()
        path = os.path.join(CACHE_DIR, key + ".npy")
        if os.path.exists(path):
            return np.load(path)
        samples, sr = self.kokoro.create(source, voice=voice, speed=speed, lang=lang, is_phonemes=phonemes is not None)
        if sr != SAMPLE_RATE:
            raise RuntimeError(f"unexpected sample rate {sr}")
        samples = np.asarray(samples, dtype=np.float32)
        np.save(path, samples)
        return samples


def level(samples):
    """Normalise one utterance to the target loudness so all voices sound equally loud."""
    rms = float(np.sqrt(np.mean(samples ** 2))) or 1e-9
    out = samples * (db_to_amp(TARGET_RMS_DB) / rms)
    peak = float(np.max(np.abs(out))) or 1e-9
    limit = db_to_amp(PEAK_DB)
    if peak > limit:
        out *= limit / peak
    return out


def silence(seconds):
    return np.zeros(int(round(seconds * SAMPLE_RATE)), dtype=np.float32)


def encode_mp3(samples, path):
    import lameenc

    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767).astype("<i2").tobytes()
    enc = lameenc.Encoder()
    enc.set_bit_rate(BITRATE_KBPS)
    enc.set_in_sample_rate(SAMPLE_RATE)
    enc.set_channels(1)
    enc.set_quality(2)
    data = enc.encode(pcm) + enc.flush()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def build_part(synth, test, part, speakers):
    chunks = [silence(LEAD_IN)]
    cursor = LEAD_IN
    previous = None
    for item in part["script"]:
        if "pause" in item:
            chunks.append(silence(item["pause"]))
            cursor += item["pause"]
            previous = None
            continue
        spk = speakers[item["speaker"]]
        if previous is not None:
            gap = GAP_NARRATOR if "narrator" in (previous, item["speaker"]) else (
                GAP_SAME if previous == item["speaker"] else GAP_CHANGE)
            chunks.append(silence(gap))
            cursor += gap
        audio = level(synth.speak(item.get("tts", item["text"]), spk["voice"], spk["lang"], spk.get("speed", 1.0),
                                  test.get("pronunciations")))
        item["start"] = round(cursor, 2)
        cursor += len(audio) / SAMPLE_RATE
        item["end"] = round(cursor, 2)
        chunks.append(audio)
        previous = item["speaker"]
    chunks.append(silence(0.8))
    samples = np.concatenate(chunks)
    rel = f"audio/{test['id']}/part{part['partNumber']}.mp3"
    size = encode_mp3(samples, os.path.join(BASE_DIR, "public", rel))
    duration = round(len(samples) / SAMPLE_RATE, 2)
    part["audio"] = {"src": rel, "duration": duration}
    return duration, size


def build_sound_check(synth):
    voice, lang = SOUND_CHECK_VOICE
    audio = level(synth.speak(SOUND_CHECK_TEXT, voice, lang, 1.0))
    samples = np.concatenate([silence(0.3), audio, silence(0.5)])
    size = encode_mp3(samples, os.path.join(AUDIO_DIR, "sound-check.mp3"))
    print(f"  sound check: {len(samples) / SAMPLE_RATE:.1f} s, {size / 1e3:.0f} kB")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", default=os.path.expanduser("~/tts-models"), help="folder with the Kokoro model files")
    parser.add_argument("--only", help="build a single test id, e.g. listening-01")
    args = parser.parse_args()

    files = sorted(f for f in os.listdir(CONTENT_DIR) if f.endswith(".json"))
    synth = Synth(args.models)
    build_sound_check(synth)
    for name in files:
        path = os.path.join(CONTENT_DIR, name)
        with open(path, encoding="utf-8") as f:
            test = json.load(f)
        if args.only and test["id"] != args.only:
            continue
        total = 0.0
        for part in test["parts"]:
            duration, size = build_part(synth, test, part, test["speakers"])
            total += duration
            print(f"  {test['id']} part {part['partNumber']}: {duration / 60:.1f} min, {size / 1e6:.1f} MB")
        test["durationMinutes"] = int(round(total / 60))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(test, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"✓ {test['id']}: {total / 60:.1f} minutes of audio")


if __name__ == "__main__":
    sys.exit(main())
