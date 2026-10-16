import pymupdf, re
from book_extractor_common import open_pdf, TEST_PAGE_STARTS, load_answer_keys

doc = open_pdf()
keys = load_answer_keys(doc)

for t in [3, 4, 5, 6]:
    start_p = TEST_PAGE_STARTS[t - 1][1]
    end_p = TEST_PAGE_STARTS[t][1]
    raw = "\n".join([doc[p - 1].get_text() for p in range(start_p, end_p)])
    print(f"\n==================== TEST {t} ====================")
    # Print answer keys 1..40
    print("Answers:", {q: keys[t][q] for q in range(1, 41)})
    
    # Print question groups
    groups = list(re.finditer(r'Questions?\s*(\d+)\s*[-–]\s*(\d+)', raw, re.I))
    for m in groups:
        q_start = int(m.group(1))
        q_end = int(m.group(2))
        snippet = raw[m.start():m.start() + 250].replace('\n', ' ')
        print(f"  Q{q_start}-{q_end}: {snippet[:120]}")
