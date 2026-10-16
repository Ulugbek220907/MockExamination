import sys
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from book_extractor_common import open_pdf, get_test_full_text, load_answer_keys

doc = open_pdf()
keys = load_answer_keys(doc)

def parse_section_groups(sec_text, start_q, end_q, t_keys):
    # Find question markers in sec_text
    markers = list(re.finditer(r'Questions?\s*(\d+)\s*[-–]\s*(\d+)', sec_text, re.I))
    # Filter markers within start_q and end_q
    valid_markers = []
    for m in markers:
        q1, q2 = int(m.group(1)), int(m.group(2))
        if start_q <= q1 and q2 <= end_q:
            valid_markers.append((q1, q2, m.start(), m.end()))
    
    print(f"Found {len(valid_markers)} groups:")
    for q1, q2, s, e in valid_markers:
        print(f"  Q{q1}-{q2} at {s}..{e}")

if __name__ == "__main__":
    txt = get_test_full_text(doc, 6)
    sec_matches = list(re.finditer(r'(?:^|\n)\s*(?:SECTION|READING PASSAGE)\s*([123])\s*(?:\n|$)', txt, flags=re.I))
    for i, m in enumerate(sec_matches):
        s_num = int(m.group(1))
        start = m.end()
        end = sec_matches[i+1].start() if i + 1 < len(sec_matches) else len(txt)
        sec_text = txt[start:end]
        print(f"\n--- Section {s_num} ---")
        if s_num == 1: parse_section_groups(sec_text, 1, 13, keys[6])
        elif s_num == 2: parse_section_groups(sec_text, 14, 26, keys[6])
        else: parse_section_groups(sec_text, 27, 40, keys[6])
