import sys
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from book_extractor_common import open_pdf, get_test_full_text, load_answer_keys

doc = open_pdf()
all_keys = load_answer_keys(doc)
keys = all_keys[7]

txt = get_test_full_text(doc, 7)
txt = re.sub(r'(\b[a-zA-Z]+)-\n([a-zA-Z]+\b)', r'\1\2', txt)
txt = txt.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
txt = txt.replace('—', '—').replace('–', '-')

sec_matches = list(re.finditer(r'(?:^|\n)\s*Section\s*([123])\s*(?:\n|$)', txt, flags=re.I))
s1 = txt[sec_matches[0].end():sec_matches[1].start()]
s2 = txt[sec_matches[1].end():sec_matches[2].start()]
s3 = txt[sec_matches[2].end():]

print("=== S1 Questions ===")
m1 = list(re.finditer(r'Questions?\s*(\d+)\s*[-–]\s*(\d+)', s1, re.I))
for m in m1:
    print(m.group(0))
    print(s1[m.start():m.start()+300])
    print("-" * 30)

print("=== S2 Questions ===")
m2 = list(re.finditer(r'Questions?\s*(\d+)\s*[-–]\s*(\d+)', s2, re.I))
for m in m2:
    print(m.group(0))
    print(s2[m.start():m.start()+300])
    print("-" * 30)

print("=== S3 Questions ===")
m3 = list(re.finditer(r'Questions?\s*(\d+)\s*[-–]\s*(\d+)', s3, re.I))
for m in m3:
    print(m.group(0))
    print(s3[m.start():m.start()+300])
    print("-" * 30)
