import os
import json
import re
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_DIR = os.path.join(BASE_DIR, "data", "kanan_html")

def parse_answer_table(soup):
    answers = {}
    # Find table with answers
    tables = soup.find_all("table")
    for tab in tables:
        cells = [c.get_text(strip=True) for r in tab.find_all("tr") for c in r.find_all(["td", "th"])]
        for cell in cells:
            m = re.match(r"^(\d+)[\.\s]+(.+)$", cell)
            if m:
                qnum = int(m.group(1))
                ans = m.group(2).strip()
                answers[qnum] = ans
    return answers

def parse_test(sno):
    html_path = os.path.join(HTML_DIR, f"test_{sno:03d}.html")
    if not os.path.exists(html_path):
        return None
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else f"Practice Test {sno}"
    title = re.sub(r"\s+Reading Answers.*$", "", title, flags=re.I).strip()
    
    answers = parse_answer_table(soup)
    h2s = soup.find_all("h2")
    
    # Passage text
    passage_title = title
    paragraphs = []
    if h2s:
        p_h2 = h2s[0]
        curr = p_h2.find_next_sibling()
        while curr and (len(h2s) < 2 or curr != h2s[1]):
            txt = curr.get_text(strip=True)
            if txt and not txt.startswith("Before giving") and not txt.startswith("Download"):
                # Check if paragraph has label A-N
                m_lbl = re.match(r"^([A-N])[\.\s]+(.*)$", txt)
                if m_lbl:
                    paragraphs.append({"label": m_lbl.group(1), "text": m_lbl.group(2)})
                else:
                    paragraphs.append({"label": None, "text": txt})
            curr = curr.find_next_sibling()

    return {
        "id": f"kanan-reading-{sno:03d}",
        "module": "reading",
        "variant": "academic",
        "testNumber": sno,
        "title": f"Academic Reading Test {sno}: {title}",
        "shortTitle": f"Kanan Test {sno}",
        "durationMinutes": 20 if len(answers) <= 15 else 60,
        "totalQuestions": len(answers),
        "sortOrder": 100 + sno,
        "passage": {
            "title": passage_title,
            "paragraphs": paragraphs
        },
        "answers": answers
    }

for s in [1, 2, 3, 50, 100, 170]:
    t = parse_test(s)
    if t:
        print(f"Test {s:3d}: '{t['title']}' -> {len(t['passage']['paragraphs'])} paras, {len(t['answers'])} answers: min={min(t['answers'].keys() or [0])}, max={max(t['answers'].keys() or [0])}")
