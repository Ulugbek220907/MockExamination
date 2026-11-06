#!/usr/bin/env python3
"""
Tests for the pieces of scripts/build_listening_audio.py that can be checked without the speech model.
They need numpy (the audio tools' only library for these): pip install -r scripts/requirements-audio.txt

    python scripts/test_audio_builder.py
"""

import importlib.util
import os
import sys
import unittest

try:
    import numpy as np
except ImportError:  # the website itself does not need numpy
    np = None

HERE = os.path.dirname(os.path.abspath(__file__))


def load_builder():
    spec = importlib.util.spec_from_file_location("build_listening_audio", os.path.join(HERE, "build_listening_audio.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipIf(np is None, "numpy is not installed")
class SpelledNameEndingTests(unittest.TestCase):
    """
    "M-A-R-S-H-A-L-L" is dictated by a British voice as "... A, double L". The last unit is two sounds with a dip
    between them, and the quiet "L" is the second one. Cutting the tail from 0.45 s on (shorten_tail, made for a
    vowel that rings on) took the dip for the end and cut the L off, so students heard "Marsha, double".
    """

    def setUp(self):
        self.b = load_builder()
        sr = self.b.SAMPLE_RATE
        t = lambda seconds: np.arange(int(seconds * sr)) / sr
        loud = 0.5 * np.sin(2 * np.pi * 180 * t(0.40))   # "double"
        gap = np.zeros(int(0.05 * sr))                    # the dip
        quiet = 0.1 * np.sin(2 * np.pi * 220 * t(0.20))   # the "L": a fifth of the loudest sound
        ring = 0.004 * np.sin(2 * np.pi * 220 * t(0.30))  # a faint tail
        self.clip = np.concatenate([loud, gap, quiet, ring]).astype(np.float32)
        self.sr = sr

    def seconds(self, samples):
        return len(samples) / self.sr

    def test_shorten_tail_would_cut_the_letter_off(self):
        # The reason the doubled ending has its own trimming (this is what happened).
        self.assertLess(self.seconds(self.b.shorten_tail(self.clip)), 0.5)

    def test_trim_tail_keeps_the_quiet_letter_and_drops_the_silence(self):
        out = self.b.trim_tail(self.clip)
        self.assertGreaterEqual(self.seconds(out), 0.65)    # the L (0.45 to 0.65 s) is all there
        self.assertLess(self.seconds(out), 0.75)            # the faint tail is not
        self.assertAlmostEqual(float(abs(out[-1])), 0.0, places=3)  # and it ends with a fade, not a click

    def test_trim_tail_leaves_an_empty_or_tiny_clip_alone(self):
        self.assertEqual(len(self.b.trim_tail(np.zeros(5, dtype=np.float32))), 5)

    def test_only_british_words_that_end_in_a_doubled_letter_are_made_again(self):
        v = self.b.spell_cache_version
        self.assertEqual(v("MARSHALL", "en-gb"), "spell12")
        self.assertEqual(v("HARTWELL", "en-gb"), "spell12")
        self.assertEqual(v("MARSHALL", "en-us"), "spell11")   # an American voice says L, L: nothing was lost
        self.assertEqual(v("MALLORY", "en-gb"), "spell11")    # a double letter inside the word: it was fine
        self.assertEqual(v("SHERWOOD", "en-gb"), "spell11")
        self.assertEqual(v("KOWALSKI", "en-gb"), "spell11")


if __name__ == "__main__":
    unittest.main(verbosity=2)
