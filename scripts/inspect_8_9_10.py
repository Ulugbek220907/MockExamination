import sys
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from book_extractor_common import open_pdf, get_test_full_text, load_answer_keys

doc = open_pdf()
all_keys = load_answer_keys(doc)

for t in [8, 9, 10]:
    k = all_keys[t]
    txt = get_test_full_text(doc, t)
    txt = re.sub(r'(\b[a-zA-Z]+)-\n([a-zA-Z]+\b)', r'\1\2', txt)
    txt = txt.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    txt = txt.replace('—', '—').replace('–', '-')
    sec_matches = list(re.finditer(r'(?:^|\n)\s*Section\s*([123])\s*(?:\n|$)', txt, flags=re.I))
    
    print(f"\n==================== TEST {t} ====================")
    for s_idx, sm in enumerate(sec_matches):
        s_num = s_idx + 1
        start = sm.end()
        end = sec_matches[s_idx+1].start() if s_idx + 1 < len(sec_matches) else len(txt)
        stext = txt[start:end].strip()
        lines = [l.strip() for l in stext.splitlines() if l.strip()]
        title = lines[0] if lines else "UNKNOWN"
        print(f"--- Section {s_num}: title={title!r} (length {len(stext)}) ---")
        for m in re.finditer(r'Questions?\s*(\d+)\s*[-–]\s*(\d+)', stext, re.I):
            q1, q2 = int(m.group(1)), int(m.group(2))
            snip = stext[m.start():m.start()+200].replace('\n', ' ')
            sample = [f"Q{q}:{k.get(q)}" for q in range(q1, min(q2+1, q1+3))]
            print(f"  Q{q1}-{q2}: keys={sample} | {snip[:80]}")
