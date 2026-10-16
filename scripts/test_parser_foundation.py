import sys
import os
import re
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from mockexam import content
from book_extractor_common import open_pdf, clean_text, TEST_PAGE_STARTS, load_answer_keys

doc = open_pdf()
all_keys = load_answer_keys(doc)

def get_test_raw_text(test_num):
    start_p = TEST_PAGE_STARTS[test_num - 1][1]
    end_p = TEST_PAGE_STARTS[test_num][1]
    pages = [doc[p - 1].get_text() for p in range(start_p, end_p)]
    # Join pages cleanly
    raw = "\n".join(pages)
    # Normalize broken hyphens at line ends: e.g. "experi-\nment" -> "experiment"
    raw = re.sub(r'(\b[a-zA-Z]+)-\n([a-zA-Z]+\b)', r'\1\2', raw)
    # Normalize unicode accents and quotes
    raw = raw.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    raw = raw.replace('—', '—').replace('–', '-')
    # Normalize typos in Question markers
    raw = re.sub(r'Q\s*ụ\s*est\s*ị\s*on', 'Question', raw, flags=re.I)
    return raw

if __name__ == "__main__":
    t5_text = get_test_raw_text(5)
    print("Test 5 raw text length:", len(t5_text))
    # Print occurrences of Question
    for m in re.finditer(r'Questions?\s*\d+\s*[-–]\s*\d+', t5_text, re.I):
        print(f"  {m.group(0)} at pos {m.start()}")
