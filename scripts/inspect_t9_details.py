import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from book_extractor_common import open_pdf, get_test_full_text, load_answer_keys

doc = open_pdf()
k = load_answer_keys(doc)[9]
txt = get_test_full_text(doc, 9)
txt = re.sub(r'(\b[a-zA-Z]+)-\n([a-zA-Z]+\b)', r'\1\2', txt)
txt = txt.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
txt = txt.replace('—', '—').replace('–', '-')

sec_matches = list(re.finditer(r'(?:^|\n)\s*Section\s*([123])\s*(?:\n|$)', txt, flags=re.I))
s1 = txt[sec_matches[0].end():sec_matches[1].start()]
s2 = txt[sec_matches[1].end():sec_matches[2].start()]
s3 = txt[sec_matches[2].end():]

print("=== Test 9 S1 ===")
idx = s1.find('Questions 1-4')
print(s1[idx:])

print("=== Test 9 S2 ===")
idx = s2.find('Questions 15')
print(s2[idx:])

print("=== Test 9 S3 ===")
idx = s3.find('Questions 28')
print(s3[idx:])
