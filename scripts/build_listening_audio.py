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
SPELL_SPEED = 0.8        # letters are said a little slower than speech, as when dictating
SPELL_GAP_LETTER = 0.2   # between two letters of a spelled word
SPELL_GAP_GROUP = 0.45   # between groups of letters
SPELL_GAP_AROUND = 0.35  # between a spelled word and the words around it
SPELLING = re.compile(r"\b[A-Z](?:-[A-Z]){2,}\b")  # K-O-W-A-L-S-K-I
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

        self.models_dir = models_dir
        self._timed = None

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


    def timed_kokoro(self):
        """
        The Kokoro model with a second output, the duration of every phoneme in 25 ms frames. The model as
        released only returns the audio; the duration is computed inside it, so the output is added to the
        graph (needs the `onnx` package). kokoro-onnx then reports when each phoneme is spoken.
        """
        if self._timed is None:
            import onnx
            import onnxruntime

            model = onnx.load(os.path.join(self.models_dir, "kokoro-v1.0.onnx"))
            rounds = [n for n in model.graph.node if n.op_type == "Round" and n.name == "/encoder/Round"]
            if len(rounds) != 1:
                raise RuntimeError("this Kokoro model does not have the duration node this script expects")
            model.graph.output.append(onnx.helper.make_tensor_value_info("duration", onnx.TensorProto.FLOAT, None))
            model.graph.node.append(onnx.helper.make_node("Identity", [rounds[0].output[0]], ["duration"]))
            session = onnxruntime.InferenceSession(model.SerializeToString(), providers=["CPUExecutionProvider"])
            session._model_path = os.path.join(self.models_dir, "kokoro-v1.0.onnx")
            self._timed = self.kokoro.__class__.from_session(
                session, os.path.join(self.models_dir, "voices-v1.0.bin"))
        return self._timed

    def spell(self, word, voice, lang, speed):
        """
        A word spelled out the way a person dictates it: letter by letter, in groups of about three, a short
        pause between letters and a longer one between groups. British speakers say "double O" for a repeated
        letter. `word` is the hyphenated form, e.g. "H-A-R-W-O-O-D".

        The model rushes a run of letters together, and a letter synthesised alone gets a stray sound in
        front of it. So the letters are voiced as a comma-separated list, where each one is clear, then cut
        apart at the moments the model reports for each phoneme and put back with real pauses between them.
        """
        letters = word.replace("-", "")
        key = hashlib.sha1(f"spell10|{voice}|{lang}|{speed}|{letters}".encode("utf-8")).hexdigest()
        path = os.path.join(CACHE_DIR, key + ".npy")
        if os.path.exists(path):
            return np.load(path)

        units = []  # IPA of each thing said: a letter, or "double" and a letter
        for i, ch in enumerate(letters):
            name = self.kokoro.tokenizer.phonemize(ch, lang=lang).strip(" .,")
            if lang == "en-gb" and i and letters[i - 1] == ch and not units[-1].startswith("dˈʌbəl"):
                units[-1] = "dˈʌbəl " + name
            else:
                units.append(name)
        kokoro = self.timed_kokoro()
        # A throwaway word first: a letter that opens the recording, like "F" (ɛf), would get a stray sound
        # in front of it. The word is cut off again below.
        lead = kokoro.tokenizer.phonemize("Okay", lang=lang).strip(" .,")
        phonemes = lead + ", " + ", ".join(units) + "."
        audio, sr, timings = kokoro.create_timed(
            phonemes, voice, speed=speed * SPELL_SPEED, lang=lang, is_phonemes=True, trim=False,
            sentence_pause=0.0, clause_pause=0.0)
        known = kokoro.tokenizer.known
        if sr != SAMPLE_RATE or len(timings) != len(known(phonemes)):
            raise RuntimeError(f"unexpected timings while spelling {word}")
        pos = len(known(lead))
        spans = [(timings[0].start, timings[pos - 1].end)]  # the lead-in word, then every letter
        pos += len(known(", "))
        for unit in units:
            n = len(known(unit))
            spans.append((timings[pos].start, timings[pos + n - 1].end))
            pos += n + len(known(", "))
        # The timings are in 25 ms frames, so a cut at the reported edge can clip the start of the next sound.
        # Cut each pair of neighbours at the quietest moment between them instead.
        edges = [quietest(audio, sr, spans[i][1] - 0.02, spans[i + 1][0] + 0.02) for i in range(len(spans) - 1)]
        edges.append(min(len(audio), int((spans[-1][1] + 0.08) * sr)))
        chunks = []
        done = 0
        for g, size in enumerate(spelling_groups(len(units))):
            for j in range(size):
                clip = trim_silence(np.asarray(audio[edges[done]:edges[done + 1]], dtype=np.float32))
                if done == len(units) - 1:
                    clip = shorten_tail(clip)
                chunks.append(level(clip))
                done += 1
                if done < len(units):
                    chunks.append(silence(SPELL_GAP_GROUP if j == size - 1 else SPELL_GAP_LETTER))
        samples = np.concatenate(chunks)
        np.save(path, samples)
        return samples

    def speak_line(self, text, voice, lang, speed, pronunciations=None):
        """A script line; any hyphenated spelling in it (K-O-W-A-L-S-K-I) is voiced letter by letter."""
        pieces, pos = [], 0
        for m in SPELLING.finditer(text):
            pieces.append(("say", text[pos:m.start()]))
            pieces.append(("spell", m.group(0)))
            pos = m.end()
        pieces.append(("say", text[pos:]))
        pieces = [(kind, s) for kind, s in pieces if kind == "spell" or re.search(r"\w", s)]
        if not any(kind == "spell" for kind, _ in pieces):
            return self.speak(text, voice, lang, speed, pronunciations)
        chunks = []
        for kind, s in pieces:
            if chunks:
                chunks.append(silence(SPELL_GAP_AROUND))
            if kind == "spell":
                chunks.append(self.spell(s, voice, lang, speed))
            else:
                chunks.append(level(trim_silence(self.speak(s.strip(), voice, lang, speed, pronunciations))))
        return np.concatenate(chunks)


def trim_silence(samples, threshold=0.03, margin=0.02):
    """Cut the quiet lead-in and tail off a short clip (keeps `margin` seconds), with a tiny fade at each end."""
    loud = np.where(np.abs(samples) > threshold * float(np.max(np.abs(samples)) or 1e-9))[0]
    if not len(loud):
        return samples
    keep = int(margin * SAMPLE_RATE)
    out = samples[max(0, loud[0] - keep):loud[-1] + keep].copy()
    fade = min(len(out) // 4, int(0.008 * SAMPLE_RATE))
    ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
    out[:fade] *= ramp
    out[len(out) - fade:] *= ramp[::-1]
    return out


def quietest(audio, sr, begin, end, frame=0.005):
    """Sample index of the quietest `frame` seconds between two moments (in seconds)."""
    n = int(frame * sr)
    lo, hi = max(0, int(begin * sr)), min(len(audio) - n, int(end * sr))
    if hi <= lo:
        return max(0, min(len(audio), (lo + hi) // 2))
    rms = [float(np.sqrt(np.mean(audio[i:i + n] ** 2))) for i in range(lo, hi, n)]
    return lo + int(np.argmin(rms)) * n + n // 2


def shorten_tail(samples, keep=0.45, floor=0.2):
    """
    The last letter of a spelling is stretched by the model (a sentence-final vowel can ring on for a
    second). Cut it where it has died away, no sooner than `keep` seconds in, with a short fade.
    """
    start = int(keep * SAMPLE_RATE)
    if len(samples) <= start + int(0.1 * SAMPLE_RATE):
        return samples
    frame = int(0.01 * SAMPLE_RATE)
    peak = float(np.max(np.abs(samples))) or 1e-9
    end = len(samples)
    for i in range(start, len(samples) - frame, frame):
        if float(np.sqrt(np.mean(samples[i:i + frame] ** 2))) < floor * peak:
            end = i + frame
            break
    else:
        end = min(len(samples), start + int(0.15 * SAMPLE_RATE))
    out = samples[:end].copy()
    fade = min(len(out), int(0.04 * SAMPLE_RATE))
    out[len(out) - fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    return out


def spelling_groups(n):
    """Sizes of the groups a spelling is dictated in: threes, with a leftover single letter joining the last group."""
    sizes = [3] * (n // 3)
    if n % 3 == 1 and sizes:
        sizes[-1] += 1
    elif n % 3:
        sizes.append(n % 3)
    return sizes or [n]


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
        audio = level(synth.speak_line(item.get("tts", item["text"]), spk["voice"], spk["lang"], spk.get("speed", 1.0),
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
