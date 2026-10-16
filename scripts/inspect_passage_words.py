import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from scripts.book_extractor_common import open_pdf
from scripts.test_parser_foundation import get_test_raw_text
from scripts.test_parser_engine import split_test_into_sections

doc = open_pdf()

searches = [
    (17, 3, ["racist", "assumption", "archeological", "historical", "inhuman", "behavior"]),
    (18, 1, ["repetitive", "complex"]),
    (18, 2, ["horizontal", "force"]),
    (19, 2, ["adventure"]),
    (22, 2, ["1988", "2002"]),
    (23, 3, ["body"]),
    (25, 1, ["mason", "heating"]),
    (26, 1, ["vicar"]),
    (31, 1, ["85%"]),
    (31, 2, ["shy", "otter", "hare", "partnership"]),
    (32, 1, ["100", "word"]),
    (33, 1, ["noise", "map", "frequency"]),
    (33, 2, ["tag"]),
    (34, 1, ["mountain", "air"])
]

for tnum, pnum, words in searches:
    raw = get_test_raw_text(tnum)
    secs = split_test_into_sections(raw)
    sec_txt = secs[pnum - 1]
    print(f"--- Test {tnum} P{pnum} ---")
    for w in words:
        matches = [m.start() for m in re.finditer(re.escape(w), sec_txt, re.I)]
        if matches:
            contexts = [sec_txt[max(0, p-30):min(len(sec_txt), p+40)].replace("\n", " ") for p in matches[:2]]
            print(f"  '{w}': found {len(matches)} times: {contexts}")
        else:
            print(f"  '{w}': NOT FOUND")
