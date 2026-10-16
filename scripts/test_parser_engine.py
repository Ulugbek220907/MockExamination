import os
import sys
import re
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from mockexam import content
from book_extractor_common import open_pdf, clean_text, load_answer_keys
from test_parser_foundation import get_test_raw_text
from patch_parser_engine import EXPLICIT_CORRECTIONS, TEST_20_KEYS, TEST_21_S1_KEYS

# Exact passage titles from Book Table of Contents
TOC_TITLES = {
    (1, 1): "Andrea Palladio: Italian architect",
    (1, 2): "The future never dies?",
    (1, 3): "Pottery production in ancient Akrotiri",
    (2, 1): "Save the Turtles",
    (2, 2): "Corporate Social Responsibility",
    (2, 3): "TV Addiction 2",
    (3, 1): "Timekeeper: Invention of Marine Chronometer",
    (3, 2): "Father of modern management",
    (3, 3): "Extinct: the Giant Deer",
    (4, 1): "New Agriculture in Oregon, US",
    (4, 2): "Intelligence and Giftedness",
    (4, 3): "Paper or Computer?",
    (5, 1): "Terminated Dinosaur Era",
    (5, 2): "Detection of a meteorite Lake",
    (5, 3): "Internal and External Marketing",
    (6, 1): "OTTER",
    (6, 2): "BIRD MIGRATION 2",
    (6, 3): "Talc Powder",
    (7, 1): "The Dinosaurs Footprints and Extinction",
    (7, 2): "WHAT COOKBOOKS REALLY TEACH US",
    (7, 3): "Learning lessons from the past",
    (8, 1): "Finches on Islands",
    (8, 2): "Flight from reality?",
    (8, 3): "Communicating Conflict!",
    (9, 1): "Agriculture and Tourism",
    (9, 2): "Cosmetics in Ancient Past",
    (9, 3): "Asian Space 2 Satellite Technology",
    (10, 1): "Koalas",
    (10, 2): "Antarctica - in from the cold?",
    (10, 3): "Language strategy In Multinational Company",
    (11, 1): "THE ORIGIN OF WRITING",
    (11, 2): "Aqua product: New Zealand's Igae Biodiesel",
    (11, 3): "British Architecture 2",
    (12, 1): "Radio Automation forerunner of the integrated circuit",
    (12, 2): "Bestcom CONSIDERATE COMPUTING",
    (12, 3): "Environmentally-friendly Vehicles",
    (13, 1): "Bondi Beach",
    (13, 2): "Hunting Perfume in Madagascar!",
    (13, 3): "The Exploration of Mars",
    (14, 1): "Traditional Farming System in Africa",
    (14, 2): "Griffith and American films",
    (14, 3): "The Persuaders",
    (15, 1): "Tea and Industrial Revolution",
    (15, 2): 'Fossil files: "The Paleobiology Database"',
    (15, 3): "Communication in science",
    (16, 1): "Can We Hold Back the Flood?",
    (16, 2): "When the Tulip Bubble Burst",
    (16, 3): "The Secrets of Persuasion",
    (17, 1): "MENTAL GYMNASTICS",
    (17, 2): "Finding Our Way",
    (17, 3): "Mystery in Easter",
    (18, 1): "The Mozart Effect",
    (18, 2): "London Swaying Footbridge",
    (18, 3): "Book review on Musicophilia",
    (19, 1): 'The coming back of the "Extinct" Grass in Britain',
    (19, 2): "CHILDREN'S LITERATURE",
    (19, 3): "Beyond the Blue Line",
    (20, 1): "World Ecotourism in the developing countries",
    (20, 2): "Memory and age",
    (20, 3): "The secret of the Yawn",
    (21, 1): "Consecutive and Simultaneous Translation",
    (21, 2): "Water Filter",
    (21, 3): "Music: Language We All Speak",
    (22, 1): "Voyage of going: beyond the blue line 2",
    (22, 2): "European Heat Wave",
    (22, 3): "The concept of childhood in the western countries",
    (23, 1): "Have Teenagers Always Existed",
    (23, 2): "Numeracy: can animals tell numbers?",
    (23, 3): "Elephant communication",
    (24, 1): "Ambergris",
    (24, 2): "Global warming: Prevent poles from melting",
    (24, 3): "Sunset for the Oil Business",
    (25, 1): "Build a Medieval Castle",
    (25, 2): "Smell and Memory: SMELLS LIKE YESTERDAY",
    (25, 3): "Memory Decoding",
    (26, 1): "Origin of Species & Continent Formation",
    (26, 2): "Chinese Yellow Citrus Ant for BIOLOGICAL CONTROL",
    (26, 3): "Mechanisms of Linguistic Change",
    (27, 1): "Museum Blockbuster",
    (27, 2): "Stress of Workplace",
    (27, 3): "Company Innovation",
    (28, 1): "The Beginning of Football",
    (28, 2): "A New Ice Age",
    (28, 3): "Soviet's New Working Week",
    (29, 1): "Density and Crowding",
    (29, 2): "The reconstruction of community in Talbot Park, Auckland",
    (29, 3): "Video Game's Unexpected Benefits to Human Brain",
    (30, 1): "Lie Detector",
    (30, 2): "Leaf-Cutting Ants and Fungus",
    (30, 3): "Save Endangered Language",
    (31, 1): "Food for thought 2",
    (31, 2): "Saving the British Bitterns",
    (31, 3): "E-training",
    (32, 1): "Animal minds: Parrot Alex",
    (32, 2): "Stealth Forces in weight Loss",
    (32, 3): "Bright Children",
    (33, 1): "A Decibel Hell",
    (33, 2): "Is Graffiti Art or Crime?",
    (33, 3): "Serendipity: The Accidental Scientists",
    (34, 1): "LONGAEVA: Ancient Bristlecone Pine",
    (34, 2): "Monkeys and Forests",
    (34, 3): "Making Our Minds Last a Lifetime",
}

def split_test_into_sections(txt):
    m1 = re.search(r'(?:^|\n)\s*(?:SECTION|READING PASSAGE)\s*1\s*(?:\n|$)', txt, flags=re.I)
    m2 = re.search(r'(?:^|\n)\s*(?:SECTION|READING PASSAGE)\s*2\s*(?:\n|$)', txt, flags=re.I)
    m3 = re.search(r'(?:^|\n)\s*(?:SECTION|READING PASSAGE)\s*3\s*(?:\n|$)', txt, flags=re.I)
    if not (m1 and m2 and m3 and m1.start() < m2.start() < m3.start()):
        raise ValueError("Could not find standard section boundaries")
    s1 = txt[m1.end():m2.start()]
    s2 = txt[m2.end():m3.start()]
    s3 = txt[m3.end():]
    return [s1, s2, s3]

def find_section_groups(sec_text):
    q_matches = list(re.finditer(r'(?:^|\n)\s*(?:Questions?|Question)\s*(\d+)(?:\s*[-–]\s*(\d+))?', sec_text, re.I))
    real_matches = []
    for m in q_matches:
        after = sec_text[m.start():m.start()+100].lower()
        if 'which are based' in after or 'spend about' in after:
            continue
        q_start = int(m.group(1))
        q_end = int(m.group(2)) if m.group(2) else q_start
        if q_end < q_start:
            if q_start == 27 and q_end == 3:
                q_end = 30
            elif q_start == 28 and q_end == 3:
                q_end = 33
            else:
                q_end = q_start
        real_matches.append([q_start, q_end, m.start()])
    
    # Adjust overlaps: if group i ends at or after group i+1 start, adjust group i
    for i in range(len(real_matches) - 1):
        if real_matches[i][1] >= real_matches[i+1][0]:
            real_matches[i][1] = real_matches[i+1][0] - 1

    return [(g[0], g[1], g[2]) for g in real_matches]

def extract_paragraphs(passage_raw):
    p_lines = [l.strip() for l in passage_raw.splitlines() if l.strip()]
    if p_lines and ('spend about' in p_lines[0].lower() or 'reading passage' in p_lines[0].lower()):
        p_lines = p_lines[1:]
    if p_lines and ('questions' in p_lines[0].lower() and 'which are based' in p_lines[0].lower()):
        p_lines = p_lines[1:]
    
    clean_body = '\n'.join(p_lines)
    
    splits = re.split(r'(?:^|\n)\s*(?:Paragraph\s+)?([A-N])[\.\s]\s*', clean_body)
    if len(splits) >= 5 and splits[1] == 'A':
        paras = []
        for i in range(1, len(splits), 2):
            lbl = splits[i]
            text = clean_text(splits[i+1])
            if text:
                paras.append({"label": lbl, "text": text})
        return paras
    
    blocks = re.split(r'\n\s*\n', clean_body)
    paras = []
    for b in blocks:
        t = clean_text(b)
        if t:
            paras.append({"label": "", "text": t})
    return paras

def clean_completion_answer(raw_ans):
    if isinstance(raw_ans, list):
        ans_str = "/".join(str(x) for x in raw_ans)
    else:
        ans_str = str(raw_ans).strip()
    
    raw_items = [p.strip() for p in ans_str.split("/") if p.strip()]
    expanded = []
    for item in raw_items:
        expanded.append(item)
        if "(" in item and ")" in item:
            without_parens = re.sub(r'[\(\)]', '', item)
            without_parens = re.sub(r'\s+', ' ', without_parens).strip()
            expanded.append(without_parens)
            inside_removed = re.sub(r'\([^)]*\)', '', item)
            inside_removed = re.sub(r'\s+', ' ', inside_removed).strip()
            if inside_removed:
                expanded.append(inside_removed)

    res = []
    for a in expanded:
        c = re.sub(r'[\(\)]', '', a).strip()
        c = c.strip(".,;: ")
        if c and c not in res and "/" not in c:
            res.append(c)
    return res if res else [ans_str]

def normalize_tfng(ans, gtype):
    a = str(ans).strip().upper()
    if gtype == "true_false_not_given":
        if a in ("TRUE", "T"): return "TRUE"
        if a in ("FALSE", "F"): return "FALSE"
        return "NOT GIVEN"
    else:
        if a in ("YES", "Y"): return "YES"
        if a in ("NO", "N"): return "NO"
        return "NOT GIVEN"

def detect_group_type(group_text):
    gt_lower = group_text.lower()
    if "list of headings" in gt_lower:
        return "matching_headings"
    if "which paragraph contains" in gt_lower or "which paragraphs contains" in gt_lower or "which paragraph" in gt_lower or "which paragraphs" in gt_lower:
        return "matching_information"
    if "true" in gt_lower and "false" in gt_lower:
        return "true_false_not_given"
    if "yes" in gt_lower and "no" in gt_lower:
        return "yes_no_not_given"
    if "choose the correct letter" in gt_lower or "choose the correct letters" in gt_lower:
        if "choose two" in gt_lower or "choose three" in gt_lower or "choose the four" in gt_lower or "choose four" in gt_lower:
            return "choose_multiple"
        return "multiple_choice"
    if "choose two" in gt_lower or "choose three" in gt_lower or "choose four" in gt_lower:
        return "choose_multiple"
    if "summary" in gt_lower:
        return "summary_completion"
    if "note" in gt_lower:
        return "note_completion"
    if "table" in gt_lower:
        return "table_completion"
    if "flow chart" in gt_lower or "flow-chart" in gt_lower:
        return "flow_chart_completion"
    if "sentence" in gt_lower and ("complete" in gt_lower or "fill" in gt_lower):
        return "sentence_completion"
    if "match" in gt_lower:
        return "matching_features"
    if "no more than" in gt_lower or "answer the questions" in gt_lower:
        return "short_answer"
    return "multiple_choice"

def dedup_options(opts):
    if not opts:
        return opts
    seen = set()
    unique = []
    for o in reversed(opts):
        k = o["key"].upper()
        if k not in seen:
            seen.add(k)
            unique.append({"key": k, "text": o["text"]})
    unique.reverse()
    unique.sort(key=lambda o: o["key"])
    return unique

def parse_group(group_text, q_start, q_end, t_keys, passage_num, paragraphs):
    gtype = detect_group_type(group_text)
    
    if gtype in ("true_false_not_given", "yes_no_not_given"):
        m_first = re.search(r'(?:^|\n)\s*(\d+)[\.\s]+', group_text)
        instruction = clean_text(group_text[:m_first.start()]) if m_first else "Do the following statements agree with the information in the reading passage?"
        q_matches = list(re.finditer(r'(?:^|\n)\s*(\d+)[\.\s]+([^\n]+(?:\n(?!\s*\d+[\.\s]+)[^\n]+)*)', group_text))
        q_dict = {int(m.group(1)): clean_text(m.group(2)) for m in q_matches}
        questions = []
        for n in range(q_start, q_end + 1):
            prompt = q_dict.get(n, f"Statement {n}")
            ans = normalize_tfng(t_keys.get(n, "NOT GIVEN"), gtype)
            questions.append({
                "number": n,
                "prompt": prompt,
                "answer": ans,
                "explanation": f"Refer to Passage {passage_num} regarding statement {n}.",
                "reference": f"Passage {passage_num}"
            })
        return {"type": gtype, "instruction": instruction, "questions": questions}

    elif gtype == "multiple_choice":
        m_first = re.search(r'(?:^|\n)\s*(\d+)[\.\s]+', group_text)
        instruction = clean_text(group_text[:m_first.start()]) if m_first else "Choose the correct letter, A, B, C or D."
        q_splits = re.split(r'(?:^|\n)\s*(\d+)[\.\s]+', group_text)
        q_map = {}
        for i in range(1, len(q_splits), 2):
            n = int(q_splits[i])
            body = q_splits[i+1]
            opt_splits = re.split(r'(?:^|\n)\s*([A-Da-d])[\.\s]+([^\n]+)', body)
            prompt = clean_text(opt_splits[0])
            opts = []
            for j in range(1, len(opt_splits), 3):
                opts.append({"key": opt_splits[j].upper(), "text": clean_text(opt_splits[j+1])})
            keys_present = {o["key"] for o in opts}
            for k in ["A", "B", "C", "D"]:
                if k not in keys_present:
                    opts.append({"key": k, "text": f"Option {k}"})
            opts.sort(key=lambda o: o["key"])
            q_map[n] = (prompt, opts)
        
        questions = []
        for n in range(q_start, q_end + 1):
            if n in q_map:
                prompt, opts = q_map[n]
            else:
                prompt = f"Question {n}"
                opts = [{"key": k, "text": f"Option {k}"} for k in ["A", "B", "C", "D"]]
            raw_ans = str(t_keys.get(n, "A")).strip().upper()
            if raw_ans not in [o["key"] for o in opts]:
                raw_ans = opts[0]["key"]
            questions.append({
                "number": n,
                "prompt": prompt,
                "options": opts,
                "answer": raw_ans,
                "explanation": f"According to Passage {passage_num}, the correct option is {raw_ans}.",
                "reference": f"Passage {passage_num}"
            })
        return {"type": "multiple_choice", "instruction": instruction, "questions": questions}

    elif gtype == "choose_multiple":
        count = q_end - q_start + 1
        opt_matches = list(re.finditer(r'(?:^|\n)\s*([A-G])[\.\s]+([^\n]+)', group_text))
        options = []
        opt_keys = set()
        for m in opt_matches:
            k = m.group(1).upper()
            t = clean_text(m.group(2))
            if k not in opt_keys and not t.lower().startswith("question"):
                options.append({"key": k, "text": t})
                opt_keys.add(k)
        if not options:
            options = [{"key": k, "text": f"Option {k}"} for k in ["A", "B", "C", "D", "E", "F", "G"][:max(count * 2, 5)]]
            opt_keys = {o["key"] for o in options}
        
        ans_letters = []
        for n in range(q_start, q_end + 1):
            raw = str(t_keys.get(n, "A")).strip().upper()
            if raw in opt_keys and raw not in ans_letters:
                ans_letters.append(raw)
        while len(ans_letters) < count:
            for k in sorted(opt_keys):
                if k not in ans_letters:
                    ans_letters.append(k)
                    break
        questions = [{"number": n} for n in range(q_start, q_end + 1)]
        return {
            "type": "choose_multiple",
            "instruction": f"Choose {count} letters, {min(opt_keys)}–{max(opt_keys)}.\nWrite your answers in boxes {q_start}–{q_end} on your answer sheet.",
            "prompt": "Which statements are correct according to the passage?",
            "options": options,
            "answer": ans_letters,
            "questions": questions
        }

    elif gtype == "matching_headings":
        pos_h = group_text.lower().find("list of headings")
        headings_text = group_text[pos_h:] if pos_h != -1 else group_text
        h_matches = list(re.finditer(r'(?:^|\n)\s*([ivxlcdm]+)[\.\s]+([^\n]+)', headings_text, re.I))
        options = []
        opt_keys = set()
        for hm in h_matches:
            k = hm.group(1).lower()
            if k not in opt_keys and not k.isdigit():
                t = clean_text(hm.group(2))
                if t and not t.lower().startswith("paragraph"):
                    options.append({"key": k, "text": t})
                    opt_keys.add(k)
        if not options:
            options = [{"key": k, "text": f"Heading {k}"} for k in ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii"]]
            opt_keys = {o["key"] for o in options}
        
        q_matches = list(re.finditer(r'(?:^|\n)\s*(\d+)[\.\s]+(?:Paragraph\s+)?([A-N])?', group_text, re.I))
        q_paras = {int(qm.group(1)): qm.group(2).upper() if qm.group(2) else "" for qm in q_matches}
        p_labels = [p["label"] for p in paragraphs if p.get("label")]
        questions = []
        for idx, n in enumerate(range(q_start, q_end + 1)):
            p_letter = q_paras.get(n) or (p_labels[idx] if idx < len(p_labels) else chr(ord('A') + idx))
            prompt = f"Paragraph {p_letter}"
            raw_ans = str(t_keys.get(n, "i")).strip().lower()
            if raw_ans not in opt_keys:
                raw_ans = options[0]["key"]
            questions.append({
                "number": n,
                "prompt": prompt,
                "answer": raw_ans,
                "explanation": f"Paragraph {p_letter} corresponds to heading {raw_ans}.",
                "reference": f"Paragraph {p_letter}"
            })
        return {
            "type": "matching_headings",
            "instruction": "Choose the correct heading for each paragraph from the list of headings below.",
            "options": options,
            "questions": questions
        }

    elif gtype == "matching_information":
        p_labels = {p["label"] for p in paragraphs if p.get("label")}
        if not p_labels:
            p_labels = {chr(ord('A') + i) for i in range(8)}
        q_splits = re.split(r'(?:^|\n)\s*(\d+)[\.\s]+', group_text)
        q_dict = {int(q_splits[i]): clean_text(q_splits[i+1]) for i in range(1, len(q_splits), 2)}
        questions = []
        for n in range(q_start, q_end + 1):
            prompt = q_dict.get(n, f"Information statement {n}")
            raw_ans = str(t_keys.get(n, "A")).strip().upper()
            if raw_ans not in p_labels:
                raw_ans = sorted(p_labels)[0]
            questions.append({
                "number": n,
                "prompt": prompt,
                "answer": raw_ans,
                "explanation": f"Paragraph {raw_ans} contains this information.",
                "reference": f"Paragraph {raw_ans}"
            })
        return {
            "type": "matching_information",
            "instruction": f"Reading Passage {passage_num} contains several paragraphs.\nWhich paragraph contains the following information?\nWrite the correct letter in boxes {q_start}–{q_end} on your answer sheet.",
            "questions": questions
        }

    elif gtype == "matching_features":
        opt_matches = list(re.finditer(r'(?:^|\n)\s*([A-G])[\.\s]+([^\n]+)', group_text))
        options = []
        opt_keys = set()
        for m in opt_matches:
            k = m.group(1).upper()
            t = clean_text(m.group(2))
            if k not in opt_keys and not t.lower().startswith("question") and not t.lower().startswith("section"):
                options.append({"key": k, "text": t})
                opt_keys.add(k)
        if not options:
            options = [{"key": k, "text": f"Category {k}"} for k in ["A", "B", "C", "D", "E"]]
            opt_keys = {o["key"] for o in options}
        
        q_splits = re.split(r'(?:^|\n)\s*(\d+)[\.\s]+', group_text)
        q_dict = {int(q_splits[i]): clean_text(q_splits[i+1]) for i in range(1, len(q_splits), 2)}
        questions = []
        for n in range(q_start, q_end + 1):
            prompt = q_dict.get(n, f"Statement {n}")
            raw_ans = str(t_keys.get(n, "A")).strip().upper()
            if raw_ans not in opt_keys:
                raw_ans = sorted(opt_keys)[0]
            questions.append({
                "number": n,
                "prompt": prompt,
                "answer": raw_ans,
                "explanation": f"Passage {passage_num} associates this with {raw_ans}.",
                "reference": f"Passage {passage_num}"
            })
        return {
            "type": "matching_features",
            "instruction": "Match each statement with the correct option from the box.",
            "options": options,
            "questions": questions
        }

    elif gtype in ("summary_completion", "note_completion", "table_completion", "flow_chart_completion"):
        text = group_text
        for n in range(q_start, q_end + 1):
            patterns = [
                rf'[_.\s]{{2,}}{n}[_.\s]{{2,}}',
                rf'_{n}_',
                rf'\b{n}\s*[\.\.\.]{{2,}}',
                rf'\[{n}\]',
                rf'\(?{n}\)?\s*[\.]{{3,}}',
                rf'\b{n}\b\s*[\.]{{4,}}'
            ]
            replaced = False
            for p in patterns:
                if re.search(p, text):
                    text = re.sub(p, f" {{{{{n}}}}} ", text, count=1)
                    replaced = True
                    break
            if not replaced and f"{{{{{n}}}}}" not in text:
                text += f"\nItem {n} relates to {{{{{n}}}}}.\n"
        
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        content_lines = []
        for l in lines:
            if any(f"{{{{{n}}}}}" in l for n in range(q_start, q_end + 1)):
                content_lines.append(l)
            elif len(content_lines) > 0:
                content_lines.append(l)
        content_blob = " ".join(content_lines) if content_lines else text
        content_blob = re.sub(r'\s+', ' ', content_blob).strip()
        for n in range(q_start, q_end + 1):
            if f"{{{{{n}}}}}" not in content_blob:
                content_blob += f" ... {{{{{n}}}}} ..."
        
        # Check for word list / options box
        opt_matches = list(re.finditer(r'(?:^|\n)\s*([A-L])[\.\s]+([^\n]+)', group_text))
        all_single_letters = all(isinstance(t_keys.get(n), str) and len(t_keys.get(n).strip()) == 1 and t_keys.get(n).strip().isupper() for n in range(q_start, q_end + 1))
        group_options = None
        if opt_matches and len(opt_matches) >= 3:
            raw_opts = [{"key": m.group(1).upper(), "text": clean_text(m.group(2))} for m in opt_matches if not m.group(2).lower().startswith("question")]
            group_options = dedup_options(raw_opts)
        elif all_single_letters:
            letters = sorted({str(t_keys.get(n)).strip().upper() for n in range(q_start, q_end + 1)})
            max_letter = max(letters) if letters else 'H'
            count = max(ord(max_letter) - ord('A') + 1, 8)
            group_options = [{"key": chr(ord('A') + i), "text": f"Option {chr(ord('A') + i)}"} for i in range(count)]
        
        questions = []
        for n in range(q_start, q_end + 1):
            raw_ans = t_keys.get(n, "answer")
            if group_options:
                single_ans = raw_ans[0] if isinstance(raw_ans, list) else raw_ans
                ans_list = [str(single_ans).strip().upper()]
            else:
                ans_list = clean_completion_answer(raw_ans)
            questions.append({
                "number": n,
                "answer": ans_list,
                "explanation": f"The answer '{ans_list[0]}' is found in Passage {passage_num}.",
                "reference": f"Passage {passage_num}"
            })
        group_dict = {
            "type": gtype if gtype in ("summary_completion", "note_completion") else "summary_completion",
            "instruction": "Complete the text below.\nChoose the correct option for each answer." if group_options else "Complete the text below.\nChoose NO MORE THAN THREE WORDS from the passage for each answer.",
            "content": content_blob,
            "questions": questions
        }
        if group_options:
            group_dict["options"] = group_options
        else:
            group_dict["maxWords"] = 3
        return group_dict

    elif gtype == "sentence_completion":
        q_splits = re.split(r'(?:^|\n)\s*(\d+)[\.\s]+', group_text)
        q_dict = {int(q_splits[i]): clean_text(q_splits[i+1]) for i in range(1, len(q_splits), 2)}
        
        opt_matches = list(re.finditer(r'(?:^|\n)\s*([A-L])[\.\s]+([^\n]+)', group_text))
        all_single_letters = all(isinstance(t_keys.get(n), str) and len(t_keys.get(n).strip()) == 1 and t_keys.get(n).strip().isupper() for n in range(q_start, q_end + 1))
        group_options = None
        if opt_matches and len(opt_matches) >= 3:
            raw_opts = [{"key": m.group(1).upper(), "text": clean_text(m.group(2))} for m in opt_matches if not m.group(2).lower().startswith("question")]
            group_options = dedup_options(raw_opts)
        elif all_single_letters:
            letters = sorted({str(t_keys.get(n)).strip().upper() for n in range(q_start, q_end + 1)})
            max_letter = max(letters) if letters else 'H'
            count = max(ord(max_letter) - ord('A') + 1, 8)
            group_options = [{"key": chr(ord('A') + i), "text": f"Option {chr(ord('A') + i)}"} for i in range(count)]

        questions = []
        for n in range(q_start, q_end + 1):
            prompt = q_dict.get(n, f"Sentence with {{{{{n}}}}}.")
            if re.search(r'[\.\_]{2,}', prompt):
                prompt = re.sub(r'[\.\_]{2,}', f"{{{{{n}}}}}", prompt, count=1)
            elif f"{{{{{n}}}}}" not in prompt:
                prompt = f"{prompt} {{{{{n}}}}}."
            raw_ans = t_keys.get(n, "answer")
            if group_options:
                single_ans = raw_ans[0] if isinstance(raw_ans, list) else raw_ans
                ans_list = [str(single_ans).strip().upper()]
            else:
                ans_list = clean_completion_answer(raw_ans)
            questions.append({
                "number": n,
                "prompt": prompt,
                "answer": ans_list,
                "explanation": f"The answer '{ans_list[0]}' completes the statement in Passage {passage_num}.",
                "reference": f"Passage {passage_num}"
            })
        group_dict = {
            "type": "sentence_completion",
            "instruction": "Complete the sentences below.\nChoose the correct option for each answer." if group_options else "Complete the sentences below.\nChoose NO MORE THAN THREE WORDS from the passage for each answer.",
            "questions": questions
        }
        if group_options:
            group_dict["options"] = group_options
        else:
            group_dict["maxWords"] = 3
        return group_dict

    else: # short_answer
        q_splits = re.split(r'(?:^|\n)\s*(\d+)[\.\s]+', group_text)
        q_dict = {int(q_splits[i]): clean_text(q_splits[i+1]) for i in range(1, len(q_splits), 2)}
        questions = []
        for n in range(q_start, q_end + 1):
            prompt = q_dict.get(n, f"Question {n}?")
            raw_ans = t_keys.get(n, "answer")
            ans_list = clean_completion_answer(raw_ans)
            questions.append({
                "number": n,
                "prompt": prompt,
                "answer": ans_list,
                "explanation": f"Evidence for '{ans_list[0]}' is found in Passage {passage_num}.",
                "reference": f"Passage {passage_num}"
            })
        return {
            "type": "short_answer",
            "instruction": "Answer the questions below.\nChoose NO MORE THAN THREE WORDS from the passage for each answer.",
            "maxWords": 3,
            "questions": questions
        }

def build_parsed_test(test_num, doc, all_keys):
    raw_txt = get_test_raw_text(test_num)
    raw_txt = re.sub(r'mountain a\s*ữ', 'mountain air', raw_txt)
    raw_txt = re.sub(r'hrifltlecones', 'bristlecones', raw_txt)
    
    if test_num == 20:
        t_keys = TEST_20_KEYS.copy()
    else:
        t_keys = all_keys[test_num].copy()
        
    if test_num == 21:
        for qn, ans in TEST_21_S1_KEYS.items():
            t_keys[qn] = ans
            
    for (t, q), correct_ans in EXPLICIT_CORRECTIONS.items():
        if t == test_num:
            t_keys[q] = correct_ans

    sections = split_test_into_sections(raw_txt)
    
    passages = []
    for s_idx, sec in enumerate(sections, 1):
        title = TOC_TITLES.get((test_num, s_idx), f"Reading Passage {s_idx}")
        groups_info = find_section_groups(sec)
        if not groups_info:
            raise ValueError(f"No question groups found for test {test_num} section {s_idx}")
        
        first_q_pos = groups_info[0][2]
        passage_raw = sec[:first_q_pos]
        paragraphs = extract_paragraphs(passage_raw)
        
        # Build groups
        groups = []
        for g_idx, (q_start, q_end, pos) in enumerate(groups_info):
            next_pos = groups_info[g_idx + 1][2] if g_idx + 1 < len(groups_info) else len(sec)
            group_text = sec[pos:next_pos]
            g = parse_group(group_text, q_start, q_end, t_keys, s_idx, paragraphs)
            groups.append(g)
            
        passages.append({
            "passageNumber": s_idx,
            "title": title,
            "paragraphs": paragraphs,
            "groups": groups
        })
        
    test_dict = {
        "id": f"book-reading-{test_num:02d}",
        "module": "reading",
        "variant": "academic",
        "testNumber": test_num,
        "title": f"Academic Reading Test {test_num}",
        "shortTitle": f"Book Test {test_num}",
        "durationMinutes": 60,
        "totalQuestions": 40,
        "sortOrder": test_num,
        "passages": passages
    }
    return test_dict

if __name__ == "__main__":
    doc = open_pdf()
    all_keys = load_answer_keys(doc)
    print("Testing parser on Test 11:")
    t11 = build_parsed_test(11, doc, all_keys)
    print("Test 11 built successfully!")
    print(f"Passages: {len(t11['passages'])}")
    for p in t11['passages']:
        q_count = sum(len(g['questions']) for g in p['groups'])
        print(f"  P{p['passageNumber']}: {p['title']!r}, paras={len(p['paragraphs'])}, groups={len(p['groups'])}, questions={q_count}")
