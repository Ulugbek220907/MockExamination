import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from book_extractor_common import open_pdf, get_test_full_text, load_answer_keys

doc = open_pdf()
keys = load_answer_keys(doc)

for t in [7, 8, 9, 10]:
    txt = get_test_full_text(doc, t)
    txt = re.sub(r'(\b[a-zA-Z]+)-\n([a-zA-Z]+\b)', r'\1\2', txt)
    txt = re.sub(r'Q\s*ụ\s*est\s*ị\s*on', 'Question', txt, flags=re.I)
    
    print(f"\n==================== TEST {t} ====================")
    # Find all question group markers
    markers = list(re.finditer(r'(?:Questions?)\s*(\d+)\s*[-–]\s*(\d+)', txt, re.I))
    for m in markers:
        q1, q2 = int(m.group(1)), int(m.group(2))
        snippet = txt[m.start():m.start() + 250].replace('\n', ' ')
        print(f"  Q{q1:2d}-{q2:2d}: {snippet[:120]}")
