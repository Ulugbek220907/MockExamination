import re
import json
import pymupdf

PDF_PATH = r"c:\Users\Пользователь\OneDrive\Desktop\34-Leaked-Past-Papers-Academic-IELTS-Reading.pdf"

# Page ranges in PDF for each test (1-indexed start page)
STARTS = [
    (1, 11), (2, 23), (3, 37), (4, 51), (5, 64), (6, 77), (7, 89), (8, 101),
    (9, 115), (10, 127), (11, 141), (12, 153), (13, 167), (14, 181), (15, 195),
    (16, 209), (17, 222), (18, 236), (19, 249), (20, 262), (21, 275), (22, 289),
    (23, 301), (24, 314), (25, 327), (26, 342), (27, 355), (28, 368), (29, 382),
    (30, 395), (31, 408), (32, 421), (33, 434), (34, 447), (35, 460)
]

def load_doc():
    return pymupdf.open(PDF_PATH)

def get_test_raw_pages(doc, test_num):
    start_p = STARTS[test_num - 1][1]
    end_p = STARTS[test_num][1]
    return [doc[p - 1].get_text() for p in range(start_p, end_p)]

def parse_all_keys(doc):
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
            if tok.isdigit() and 1 <= int(tok) <= 40:
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

if __name__ == "__main__":
    doc = load_doc()
    keys = parse_all_keys(doc)
    print("Parsed keys for tests:", len(keys))
    for t in range(1, 35):
        k = keys[t]
        print(f"Test {t:2d}: {len(k)}/40 answers")

