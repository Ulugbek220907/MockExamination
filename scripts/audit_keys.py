import re
import pymupdf
from explore_extractor import STARTS, parse_all_keys

PDF_PATH = r"c:\Users\Пользователь\OneDrive\Desktop\34-Leaked-Past-Papers-Academic-IELTS-Reading.pdf"

doc = pymupdf.open(PDF_PATH)
all_keys = parse_all_keys(doc)

def get_test_text(t_num):
    p_start, p_end = STARTS[t_num - 1][1], STARTS[t_num][1]
    return '\n'.join([doc[p - 1].get_text() for p in range(p_start, p_end)])

for t in range(3, 35):
    raw = get_test_text(t)
    keys = all_keys[t]
    print(f"\n=================== TEST {t} ===================")
    # Find all question group headers
    groups = list(re.finditer(r'Questions?\s*(\d+)\s*[-–]\s*(\d+)', raw, re.I))
    for m in groups:
        q_start = int(m.group(1))
        q_end = int(m.group(2))
        snippet = raw[m.start():m.start() + 400]
        # Detect type from snippet
        detected = "unknown"
        if re.search(r'TRUE|FALSE|NOT GIVEN', snippet, re.I):
            detected = "TFNG"
        elif re.search(r'YES|NO|NOT GIVEN', snippet, re.I):
            detected = "YNNG"
        elif re.search(r'heading', snippet, re.I):
            detected = "headings"
        elif re.search(r'which paragraph contains', snippet, re.I):
            detected = "matching_info"
        elif re.search(r'summary', snippet, re.I):
            detected = "summary"
        elif re.search(r'choose\s+(?:two|three)\s+letters', snippet, re.I):
            detected = "choose_multiple"
        elif re.search(r'choose the correct letter|write the correct letter', snippet, re.I):
            detected = "MCQ_or_match"
        elif re.search(r'no more than', snippet, re.I):
            detected = "completion/short_answer"
        
        sample_keys = [keys.get(q) for q in range(q_start, min(q_end + 1, q_start + 4))]
        print(f"  Q{q_start}-{q_end} [{detected}]: sample answers = {sample_keys}")
