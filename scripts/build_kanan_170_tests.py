import os
import sys
import re
import json
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_DIR = os.path.join(BASE_DIR, "data", "kanan_html")
CATALOG_PATH = os.path.join(BASE_DIR, "kanan_170_catalog.json")

def clean_txt(t):
    if not t:
        return ""
    t = t.replace("\xa0", " ")
    t = t.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    t = t.replace("—", "—").replace("–", "-")
    return re.sub(r"\s+", " ", t).strip()

def parse_answer_table(soup):
    answers = {}
    tables = soup.find_all("table")
    for tab in tables:
        cells = [clean_txt(c.get_text()) for r in tab.find_all("tr") for c in r.find_all(["td", "th"])]
        for cell in cells:
            m = re.match(r"^(\d+)[\.\s]+(.+)$", cell)
            if m:
                qnum = int(m.group(1))
                ans = clean_txt(m.group(2))
                # Normalize common answers
                ans_upper = ans.upper()
                if ans_upper in ("TRUE", "FALSE", "NOT GIVEN", "YES", "NO"):
                    answers[qnum] = ans_upper
                else:
                    answers[qnum] = ans
    return answers

def parse_explanations(soup):
    exps = {}
    h2s = soup.find_all("h2")
    if len(h2s) < 3:
        return exps
    curr = h2s[2].find_next_sibling()
    q_counter = 1
    while curr:
        txt = clean_txt(curr.get_text())
        if "explanation:" in txt.lower():
            # Check if there is an explicit question number
            m = re.search(r"\b(\d+)[\.\s]+(?:\(?[A-Z0-9\s]+\)?[\.\s]+)?(?:explanation:)?\s*(.*)", txt, re.I)
            if m and int(m.group(1)) < 50:
                q_num = int(m.group(1))
                exps[q_num] = clean_txt(m.group(2))
            else:
                exp_text = re.sub(r"^.*?explanation:\s*", "", txt, flags=re.I).strip()
                exps[q_counter] = exp_text
                q_counter += 1
        curr = curr.find_next_sibling()
    return exps

def detect_group_type(text):
    tl = text.lower()
    if "list of headings" in tl or "matching heading" in tl or "matching headings" in tl:
        return "matching_headings"
    if "which paragraph" in tl or "locating information" in tl or "which paragraphs" in tl:
        return "matching_information"
    if "true" in tl and "false" in tl:
        return "true_false_not_given"
    if "yes" in tl and "no" in tl:
        return "yes_no_not_given"
    if "choose the correct letter" in tl or "multiple choice" in tl:
        if "choose two" in tl or "choose three" in tl:
            return "choose_multiple"
        return "multiple_choice"
    if "table completion" in tl:
        return "table_completion"
    if "summary" in tl:
        return "summary_completion"
    if "note" in tl:
        return "note_completion"
    if "sentence" in tl:
        return "sentence_completion"
    if "match" in tl:
        return "matching_features"
    return "short_answer"

def build_test(entry):
    sno = int(entry["sno"])
    html_file = os.path.join(HTML_DIR, f"test_{sno:03d}.html")
    if not os.path.exists(html_file):
        return None
    
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    
    h1 = soup.find("h1")
    raw_title = clean_txt(h1.get_text()) if h1 else f"Practice Test {sno}"
    title = re.sub(r"\s+Reading Answers.*$", "", raw_title, flags=re.I).strip()
    
    answers = parse_answer_table(soup)
    explanations = parse_explanations(soup)
    h2s = soup.find_all("h2")
    
    # 1. Extract Paragraphs
    paragraphs = []
    if h2s:
        curr = h2s[0].find_next_sibling()
        while curr and (len(h2s) < 2 or curr != h2s[1]):
            txt = clean_txt(curr.get_text())
            if txt and not txt.lower().startswith("before giving") and not txt.lower().startswith("download"):
                # Check for paragraph letter label A-N
                m = re.match(r"^([A-N])[\.\s]+(.*)$", txt)
                if m:
                    paragraphs.append({"label": m.group(1), "text": m.group(2)})
                else:
                    paragraphs.append({"label": None, "text": txt})
            curr = curr.find_next_sibling()
            
    if not paragraphs:
        paragraphs = [{"label": None, "text": f"Reading passage for {title}."}]

    # 2. Extract Question Groups
    groups = []
    if len(h2s) >= 2:
        curr = h2s[1].find_next_sibling()
        current_gtype = "short_answer"
        current_instruction = "Answer the questions below."
        current_qs = []
        
        while curr and (len(h2s) < 3 or curr != h2s[2]):
            tag_name = curr.name
            txt = clean_txt(curr.get_text())
            
            if tag_name in ["h3", "h4", "h5"] or (tag_name == "p" and re.search(r"Questions?\s*\(\d+[-–]\d+\)|Questions?\s*\d+[-–]\d+", txt, re.I)):
                # Flush previous group if any
                if current_qs:
                    groups.append({
                        "type": current_gtype,
                        "instruction": current_instruction,
                        "questions": current_qs
                    })
                    current_qs = []
                
                # Check new group range & type
                current_gtype = detect_group_type(txt)
                current_instruction = txt
            elif tag_name == "p":
                # Check if it has instructions like Choose no more than...
                if any(k in txt.lower() for k in ["choose", "write", "complete", "do the following"]):
                    current_instruction += f"\n{txt}"
                    if current_gtype == "short_answer":
                        current_gtype = detect_group_type(txt)
                else:
                    # Check if it's a question
                    qm = re.match(r"^(\d+)[\.\s]+(.*)$", txt)
                    if qm:
                        qn = int(qm.group(1))
                        qprompt = qm.group(2).strip()
                        ans = answers.get(qn, "")
                        exp = explanations.get(qn, f"Refer to the reading passage regarding Question {qn}.")
                        current_qs.append({
                            "number": qn,
                            "prompt": qprompt if qprompt else f"Question {qn}",
                            "answer": ans,
                            "explanation": exp
                        })
            elif tag_name in ["ol", "ul"]:
                # Could be options for previous question or list of headings
                items = [clean_txt(li.get_text()) for li in curr.find_all("li")]
                if current_qs and current_gtype == "multiple_choice":
                    opts = []
                    for i, itm in enumerate(items):
                        key = chr(ord('A') + i)
                        opts.append({"key": key, "text": itm})
                    current_qs[-1]["options"] = opts
            
            curr = curr.find_next_sibling()
            
        if current_qs:
            groups.append({
                "type": current_gtype,
                "instruction": current_instruction,
                "questions": current_qs
            })

    # If groups could not be extracted by HTML tags or questions were sparse, construct from answers
    total_q_found = sum(len(g.get("questions", [])) for g in groups)
    if total_q_found < len(answers):
        # Fallback: create well-formed question groups directly from the parsed answer table
        all_qnums = sorted(answers.keys())
        if all_qnums:
            groups = []
            qs = []
            for n in all_qnums:
                ans = answers[n]
                exp = explanations.get(n, f"The correct answer for question {n} is {ans}.")
                qs.append({
                    "number": n,
                    "prompt": f"Question {n}",
                    "answer": ans,
                    "explanation": exp
                })
            # Check type of first few answers
            first_ans = str(answers.get(all_qnums[0], "")).upper()
            if first_ans in ["TRUE", "FALSE", "NOT GIVEN"]:
                gtype = "true_false_not_given"
            elif first_ans in ["YES", "NO"]:
                gtype = "yes_no_not_given"
            elif first_ans in ["A", "B", "C", "D"]:
                gtype = "multiple_choice"
            else:
                gtype = "summary_completion"
                
            groups.append({
                "type": gtype,
                "instruction": "Complete the questions below using information from the passage.",
                "questions": qs
            })

    test_obj = {
        "id": f"kanan-reading-{sno:03d}",
        "module": "reading",
        "variant": "academic",
        "testNumber": sno,
        "title": f"Academic Reading Test {sno}: {title}",
        "shortTitle": f"Kanan Test {sno}",
        "durationMinutes": 20 if len(answers) <= 15 else 60,
        "totalQuestions": len(answers),
        "sortOrder": 100 + sno,
        "pdfUrl": entry["pdf_url"],
        "sourceUrl": entry["ans_url"],
        "passages": [
            {
                "passageNumber": 1,
                "title": title,
                "paragraphs": paragraphs,
                "groups": groups
            }
        ]
    }
    return test_obj

def main():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    
    print(f"Building {len(catalog)} Kanan reading tests from HTML and PDFs...")
    all_tests = []
    for entry in catalog:
        t = build_test(entry)
        if t:
            all_tests.append(t)
    
    print(f"\nSuccessfully parsed {len(all_tests)} / {len(catalog)} tests!")
    
    # Save to data/kanan_170_tests.json
    out_data = os.path.join(BASE_DIR, "data", "kanan_170_tests.json")
    os.makedirs(os.path.dirname(out_data), exist_ok=True)
    with open(out_data, "w", encoding="utf-8") as f:
        json.dump(all_tests, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved to {out_data} ({os.path.getsize(out_data):,} bytes)")

    # Save to content/reading/kanan_170_tests.json
    out_content = os.path.join(BASE_DIR, "content", "reading", "kanan_170_tests.json")
    with open(out_content, "w", encoding="utf-8") as f:
        json.dump(all_tests, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved to {out_content} ({os.path.getsize(out_content):,} bytes)")

if __name__ == "__main__":
    main()
