import os
import sys
import re
import json
import pymupdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from mockexam import content

PDF_PATH = r"c:\Users\Пользователь\OneDrive\Desktop\34-Leaked-Past-Papers-Academic-IELTS-Reading.pdf"

# Start page (1-based) in PDF for each reading test (index 0 is Test 1)
TEST_PAGE_STARTS = [
    (1, 11), (2, 23), (3, 37), (4, 51), (5, 64), (6, 77), (7, 89), (8, 101),
    (9, 115), (10, 127), (11, 141), (12, 153), (13, 167), (14, 181), (15, 195),
    (16, 209), (17, 222), (18, 236), (19, 249), (20, 262), (21, 275), (22, 289),
    (23, 301), (24, 314), (25, 327), (26, 342), (27, 355), (28, 368), (29, 382),
    (30, 395), (31, 408), (32, 421), (33, 434), (34, 447), (35, 460)
]

def open_pdf():
    return pymupdf.open(PDF_PATH)

def clean_text(text):
    """Normalize unicode spaces, quotes, hyphens and clean up OCR artifacts."""
    if not text:
        return ""
    text = text.replace('\xa0', ' ')
    text = text.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    text = text.replace('—', '—').replace('–', '-')
    # Normalize multiple whitespace within lines
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def get_test_raw_pages(doc, test_num):
    """Return raw text for each page of the test."""
    start_p = TEST_PAGE_STARTS[test_num - 1][1]
    end_p = TEST_PAGE_STARTS[test_num][1]
    return [doc[p - 1].get_text() for p in range(start_p, end_p)]

def get_test_full_text(doc, test_num):
    pages = get_test_raw_pages(doc, test_num)
    return "\n--- PAGE BREAK ---\n".join(pages)

def load_answer_keys(doc):
    full_keys = ""
    for p in range(459, len(doc)):
        full_keys += f"\n<<<PAGE {p+1}>>>\n" + doc[p].get_text()

    parts = re.split(r'Reading Test (\d+)', full_keys)
    test_raw = {int(parts[i]): parts[i+1] for i in range(1, len(parts), 2)}

    all_keys = {}
    for t_num, txt in test_raw.items():
        txt = re.sub(r'<<<PAGE \d+>>>', '', txt)
        txt = re.sub(r'Section\s*[123]', '', txt, flags=re.IGNORECASE)
        tokens = [t.strip() for t in txt.split() if t.strip()]

        entries = []
        curr_q = None
        curr_words = []

        for tok in tokens:
            # Check if tok is a question number: must be 1..40 and if curr_q is set, must be > curr_q (or curr_q is None and tok == '1')
            is_q_num = False
            if tok.isdigit() and 1 <= int(tok) <= 40:
                val = int(tok)
                if curr_q is None:
                    if val == 1:
                        is_q_num = True
                else:
                    # In IELTS, question numbers increase (val >= curr_q)
                    # and usually val == curr_q + 1 (or + 2 if one was skipped)
                    if val > curr_q and val <= curr_q + 2:
                        is_q_num = True
                    elif val == curr_q: # Duplicate number in book typo
                        is_q_num = True

            if is_q_num:
                if curr_q is not None:
                    entries.append((curr_q, ' '.join(curr_words)))
                curr_q = int(tok)
                curr_words = []
            else:
                if curr_q is not None:
                    curr_words.append(tok)
        if curr_q is not None:
            entries.append((curr_q, ' '.join(curr_words)))

        fixed_answers = {}
        for i, (q, ans) in enumerate(entries):
            if q in fixed_answers:
                fixed_answers[q] = ans
            else:
                if i + 1 < len(entries) and entries[i+1][0] == q and (q - 1) not in fixed_answers:
                    fixed_answers[q - 1] = ans
                else:
                    fixed_answers[q] = ans
        all_keys[t_num] = fixed_answers
    return all_keys

def save_and_validate_test(test_dict):
    """Save test JSON to content/reading/ and validate it."""
    test_id = test_dict["id"]
    filepath = os.path.join(BASE_DIR, "content", "reading", f"{test_id}.json")
    
    # Run validation before saving
    problems = content.validate_reading_test(test_dict)
    if problems:
        print(f"Validation FAILED for {test_id}:")
        for p in problems:
            print(f"  ✗ {p}")
        raise ValueError(f"Test {test_id} failed validation with {len(problems)} errors.")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(test_dict, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved and validated {test_id} ({test_dict['title']})")
    return True
