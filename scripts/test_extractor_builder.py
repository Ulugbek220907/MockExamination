import os
import sys
import re
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from mockexam import content
from book_extractor_common import open_pdf, clean_text, TEST_PAGE_STARTS, load_answer_keys, save_and_validate_test
from test_parser_foundation import get_test_raw_text

doc = open_pdf()
all_keys = load_answer_keys(doc)

def inspect_test_structure(test_num):
    raw = get_test_raw_text(test_num)
    k = all_keys[test_num]
    print(f"\n==================== TEST {test_num} ====================")
    
    # Split on Section 1, 2, 3 or READING PASSAGE 1, 2, 3
    sec_splits = re.split(r'(?:SECTION|READING PASSAGE)\s*([123])', raw, flags=re.I)
    print(f"Sections found: {len(sec_splits) // 2}")
    for i in range(1, len(sec_splits), 2):
        s_num = int(sec_splits[i])
        s_txt = sec_splits[i+1].strip()
        lines = [l.strip() for l in s_txt.splitlines() if l.strip()]
        title = lines[0] if lines else ""
        if "spend about 20 minutes" in title.lower() and len(lines) > 2:
            title = lines[2]
        
        # Check paragraph labels
        p_labels = re.findall(r'(?:^|\n)\s*([A-I])\.\s+[A-Z]', s_txt)
        q_markers = re.findall(r'Questions?\s*\d+\s*[-–]\s*\d+', s_txt, re.I)
        print(f"  Section {s_num}: title={title!r}, paras={p_labels}, questions={q_markers}")

if __name__ == "__main__":
    for t in [6, 7, 8, 9, 10]:
        inspect_test_structure(t)
