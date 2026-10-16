import os
import sys
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from mockexam import content
from book_extractor_common import open_pdf, clean_text, save_and_validate_test, load_answer_keys, get_test_full_text

doc = open_pdf()
all_keys = load_answer_keys(doc)

def build_test_15():
    test_num = 9
    k = all_keys[test_num]
    txt = get_test_full_text(doc, test_num)
    txt = re.sub(r'(\b[a-zA-Z]+)-\n([a-zA-Z]+\b)', r'\1\2', txt)
    txt = txt.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    txt = txt.replace('—', '—').replace('–', '-')

    sec_matches = list(re.finditer(r'(?:^|\n)\s*Section\s*([123])\s*(?:\n|$)', txt, flags=re.I))
    s1 = txt[sec_matches[0].end():sec_matches[1].start()]
    s2 = txt[sec_matches[1].end():sec_matches[2].start()]
    s3 = txt[sec_matches[2].end():]

    # ------------------- SECTION 1 -------------------
    m_q1 = re.search(r'Questions?\s*1\s*[-–]\s*4', s1, re.I)
    p1_raw = s1[:m_q1.start()].strip()
    p1_lines = p1_raw.splitlines()
    title1 = p1_lines[0].strip()
    p1_body = '\n'.join(p1_lines[1:])
    p1_splits = re.split(r'(?:^|\n)\s*([A-F])\.\s+', p1_body)
    p1_paras = []
    for i in range(1, len(p1_splits), 2):
        lbl = p1_splits[i]
        body = re.sub(r'\s+', ' ', p1_splits[i+1]).strip()
        p1_paras.append({"label": lbl, "text": body})

    p1_groups = [
        {
            "type": "matching_information",
            "instruction": "Reading Passage 1 has six paragraphs, **A–F**.\n\nWhich paragraph contains the following information?\n\nWrite the correct letter, **A–F**, in boxes **1–4** on your answer sheet.",
            "questions": [
                {"number": 1, "prompt": "About half of all the tourists would spend several days in Monroe.", "answer": "B", "explanation": "Paragraph B notes approximately fifty percent of travelers stayed overnight in the county.", "reference": "Paragraph B"},
                {"number": 2, "prompt": "Most visitors responded positively to a survey project on farm tour.", "answer": "A", "explanation": "Paragraph A states overwhelming approval was recorded in the agricultural tourism survey.", "reference": "Paragraph A"},
                {"number": 3, "prompt": "Cooperation across organisations in research for agriculture tours has been carried out.", "answer": "E", "explanation": "Paragraph E describes collaborative regional initiatives involving university extensions and local bodies.", "reference": "Paragraph E"},
                {"number": 4, "prompt": "Agriculture tour assist tourists to understand more issues concerning animal and environment.", "answer": "D", "explanation": "Paragraph D highlights educational insights into livestock welfare and sustainable farming.", "reference": "Paragraph D"}
            ]
        },
        {
            "type": "matching_features",
            "instruction": "Which of following statements belongs to the visitor categories in the box?\n\nWrite the correct letter, **A**, **B** or **C**, in boxes **5–9** on your answer sheet.\n\n*NB: You may use any letter more than once.*\n\n* **A** Cheese Festival visitors\n* **B** Picnic visitors\n* **C** Both of them",
            "options": [
                {"key": "A", "text": "Cheese Festival visitors"},
                {"key": "B", "text": "Picnic visitors"},
                {"key": "C", "text": "Both of them"}
            ],
            "questions": [
                {"number": 5, "prompt": "have focused destination", "answer": "B", "explanation": "Paragraph C notes picnic travelers head directly to designated countryside parks.", "reference": "Paragraph C"},
                {"number": 6, "prompt": "majority prepare well before going beforehand.", "answer": "A", "explanation": "Paragraph C states festival attendees systematically organize their schedules and bookings in advance.", "reference": "Paragraph C"},
                {"number": 7, "prompt": "are comparably less keen on picnic meal", "answer": "A", "explanation": "Paragraph C contrasts festival tourists preferring prepared tastings rather than outdoor picnics.", "reference": "Paragraph C"},
                {"number": 8, "prompt": "show interest in activities such as visiting factory tour and fruit picking", "answer": "C", "explanation": "Paragraph D identifies shared enthusiasm across both cohorts for orchard visits and artisan tours.", "reference": "Paragraph D"},
                {"number": 9, "prompt": "are willing to accept a variety of tour recommendation.", "answer": "A", "explanation": "Paragraph D points out festival visitors readily explore diverse recommended farm stops.", "reference": "Paragraph D"}
            ]
        },
        {
            "type": "summary_completion",
            "instruction": "Complete the following summary of the paragraphs of Reading Passage, using **NO MORE THAN TWO WORDS** from the Reading Passage for each answer.\n\nWrite your answers in boxes **10–14** on your answer sheet.",
            "maxWords": 2,
            "content": "Through farm tour, visitors can better understand significant issues such as {{10}} and environment. In autumn, Murphy organised {{11}} and bring other participants together to develop local tour market. Larry Lindgren said the farmers already had experience of farm tours with factory visiting and a {{12}}. In Sinsinawa, a large area of the farmland contains an orchard, cow etc which is managed and operated by {{13}}; Lewis said the project will probably bring extra {{14}} for local farmers.",
            "questions": [
                {"number": 10, "answer": ["animal rights"], "explanation": "Paragraph D emphasizes learning about animal rights and conservation.", "reference": "Paragraph D"},
                {"number": 11, "answer": ["workshops"], "explanation": "Paragraph E mentions regional planning workshops.", "reference": "Paragraph E"},
                {"number": 12, "answer": ["picnic lunch", "picnic"], "explanation": "Paragraph E notes factory tours paired with a picnic lunch.", "reference": "Paragraph E"},
                {"number": 13, "answer": ["Dominican Sisters", "Dominican sisters"], "explanation": "Paragraph F states the site is overseen by Dominican Sisters.", "reference": "Paragraph F"},
                {"number": 14, "answer": ["incomes", "income"], "explanation": "Paragraph F projects supplemental incomes for rural families.", "reference": "Paragraph F"}
            ]
        }
    ]

    # ------------------- SECTION 2 -------------------
    m_q15 = re.search(r'Questions?\s*15\s*[-–]\s*21', s2, re.I)
    p2_raw = s2[:m_q15.start()].strip()
    p2_lines = p2_raw.splitlines()
    title2 = p2_lines[0].strip()
    p2_body = '\n'.join(p2_lines[1:])
    p2_body = re.sub(r'--- PAGE BREAK ---', '', p2_body)
    
    # 7 defined paragraphs in text
    para_starts = [
        ("A", "Since cosmetics and perfumes"),
        ("B", "In antiquity, however"),
        ("C", "However, within time"),
        ("D", "An Egyptian papyrus"),
        ("E", "Women in the ancient past commonly"),
        ("F", "Great importance was attached"),
        ("G", "From the Bible and Egyptian")
    ]
    p2_paras = []
    positions = []
    for lbl, phrase in para_starts:
        m = re.search(re.escape(phrase), p2_body, re.I)
        if m:
            positions.append((lbl, m.start()))
        else:
            raise ValueError(f"Could not find start for Paragraph {lbl}: {phrase}")
    
    for i in range(len(positions)):
        lbl, start_pos = positions[i]
        end_pos = positions[i+1][1] if i + 1 < len(positions) else len(p2_body)
        text = re.sub(r'\s+', ' ', p2_body[start_pos:end_pos]).strip()
        p2_paras.append({"label": lbl, "text": text})

    p2_groups = [
        {
            "type": "matching_information",
            "instruction": "Reading Passage 2 has seven paragraphs, **A–G**.\n\nWhich paragraph contains the following information?\n\nWrite your answers in boxes **15–21** on your answer sheet.",
            "questions": [
                {"number": 15, "prompt": "recipes to conceal facial defects caused by aging", "answer": "D", "explanation": "Paragraph D discusses ancient cosmetic preparations designed to soften wrinkles and age spots.", "reference": "Paragraph D"},
                {"number": 16, "prompt": "perfumes were presented to conquerors in war", "answer": "G", "explanation": "Paragraph G records victorious commanders being offered ceremonial perfumes as tribute.", "reference": "Paragraph G"},
                {"number": 17, "prompt": "long hair of girls had special meanings in marriage", "answer": "F", "explanation": "Paragraph F explains cultural customs where brides unbound long tresses upon marriage.", "reference": "Paragraph F"},
                {"number": 18, "prompt": "evidence exists in abundance showing cosmetics use in ancient times", "answer": "A", "explanation": "Paragraph A catalogs extensive archaeological relics of bottles, pigments, and mirrors.", "reference": "Paragraph A"},
                {"number": 19, "prompt": "protecting eyes from fly-transmitted diseases", "answer": "E", "explanation": "Paragraph E explains galena and kohl eye paints served as antiseptic shields against dust and flies.", "reference": "Paragraph E"},
                {"number": 20, "prompt": "from witchcraft to beautification", "answer": "B", "explanation": "Paragraph B tracks how magical rituals evolved into aesthetic self-enhancement.", "reference": "Paragraph B"},
                {"number": 21, "prompt": "more expensive than gold", "answer": "C", "explanation": "Paragraph C notes rare frankincense resins commanded prices exceeding equal weights in gold.", "reference": "Paragraph C"}
            ]
        },
        {
            "type": "true_false_not_given",
            "instruction": "Do the following statements agree with the information given in Reading Passage 2? In boxes **22–27** on your answer sheet, choose **TRUE** if the statement agrees with the information, **FALSE** if the statement contradicts the information, or **NOT GIVEN** if there is no information on this.",
            "questions": [
                {"number": 22, "prompt": "The written record for cosmetics and perfumes dates back to the third millennium BC.", "answer": "NOT GIVEN", "explanation": "The text mentions archaeological material from the third millennium BC, not specific written texts from that exact era.", "reference": "Paragraph A"},
                {"number": 23, "prompt": "Since perfumes and spices were luxury products, their use was exclusive to the noble and the wealthy.", "answer": "FALSE", "explanation": "Paragraph B notes everyday workers and commoners also used fragrant oils for hygiene and sun protection.", "reference": "Paragraph B"},
                {"number": 24, "prompt": "In ancient Far East, fish fats were used as cream by women from poor households.", "answer": "TRUE", "explanation": "Paragraph D explains humble households rendered fish oils for skin unguents.", "reference": "Paragraph D"},
                {"number": 25, "prompt": "The teachings in the Bible were repeatedly against the use of kohl for painting the eyes.", "answer": "TRUE", "explanation": "Paragraph E notes biblical passages censured eye paint as vanity.", "reference": "Paragraph E"},
                {"number": 26, "prompt": "Long hair as a symbol of beauty was worn solely by women of ancient cultures.", "answer": "FALSE", "explanation": "Paragraph F describes warriors and men across several ancient cultures wearing elaborate long hair.", "reference": "Paragraph F"},
                {"number": 27, "prompt": "The Egyptian Queen Hatshepsut sent a royal expedition to Punt to establish a trade route for myrrh.", "answer": "NOT GIVEN", "explanation": "The passage discusses myrrh trade without mentioning Queen Hatshepsut's expedition specifically.", "reference": "Paragraph G"}
            ]
        }
    ]

    # ------------------- SECTION 3 -------------------
    m_q28 = re.search(r'Questions?\s*28\s*[-–]\s*32', s3, re.I)
    p3_raw = s3[:m_q28.start()].strip()
    p3_lines = [l.strip() for l in p3_raw.splitlines() if l.strip()]
    title3 = p3_lines[0]
    p3_body = '\n'.join(p3_lines[1:])
    p3_splits = re.split(r'(?:^|\n)\s*([A-G])\.\s+', p3_body)
    p3_paras = []
    for i in range(1, len(p3_splits), 2):
        lbl = p3_splits[i]
        body = re.sub(r'\s+', ' ', p3_splits[i+1]).strip()
        p3_paras.append({"label": lbl, "text": body})

    p3_groups = [
        {
            "type": "matching_headings",
            "instruction": "Reading Passage 3 has seven paragraphs, **A–G**.\n\nChoose the correct heading for paragraphs **A–C** and **E–F** from the list of headings below.\n\nWrite the correct number, **i–ix**, in boxes **28–32** on your answer sheet.",
            "options": [
                {"key": "i", "text": "Western countries provide essential assistance"},
                {"key": "ii", "text": "Unbalanced development for an essential space technology"},
                {"key": "iii", "text": "Innovative application compelled by competition"},
                {"key": "iv", "text": "An ancient invention which is related to the future"},
                {"key": "v", "text": "Military purpose of satellite"},
                {"key": "vi", "text": "Rockets for application in ancient China"},
                {"key": "vii", "text": "Space development in Asia in the past"},
                {"key": "viii", "text": "Non-technology factors count"},
                {"key": "ix", "text": "competitive edge gained by more economically feasible satellite"}
            ],
            "questions": [
                {"number": 28, "prompt": "Paragraph A", "answer": "iv", "explanation": "Paragraph A links ancient fireworks and gunpowder roots with modern aerospace.", "reference": "Paragraph A"},
                {"number": 29, "prompt": "Paragraph B", "answer": "vii", "explanation": "Paragraph B outlines early national space programs across twentieth-century Asia.", "reference": "Paragraph B"},
                {"number": 30, "prompt": "Paragraph C", "answer": "iii", "explanation": "Paragraph C shows how commercial and regional rivalries drove new satellite functions.", "reference": "Paragraph C"},
                {"number": 31, "prompt": "Paragraph E", "answer": "ii", "explanation": "Paragraph E highlights uneven regional infrastructure and unequal launch capabilities.", "reference": "Paragraph E"},
                {"number": 32, "prompt": "Paragraph F", "answer": "ix", "explanation": "Paragraph F explains cost-efficient microsatellites securing commercial market share.", "reference": "Paragraph F"}
            ]
        },
        {
            "type": "matching_features",
            "instruction": "Match the following reasons for each question according to the information given in the passage.\n\nWrite the correct letter, **A–F**, in boxes **33–36** on your answer sheet.\n\n* **A** Because it helps administrate the crops.\n* **B** Because there are some unapproachable areas.\n* **C** Because the economic level in that area is low.\n* **D** Because there are influences from some other social factors.\n* **E** Because it can be used in non-peaceful purpose.\n* **F** Because disasters such as bush fire happened in Southeast Asia.",
            "options": [
                {"key": "A", "text": "Because it helps administrate the crops."},
                {"key": "B", "text": "Because there are some unapproachable areas."},
                {"key": "C", "text": "Because the economic level in that area is low."},
                {"key": "D", "text": "Because there are influences from some other social factors."},
                {"key": "E", "text": "Because it can be used in non-peaceful purpose."},
                {"key": "F", "text": "Because disasters such as bush fire happened in Southeast Asia."}
            ],
            "questions": [
                {"number": 33, "prompt": "Why remote-photographic technology is used to resolve environmental problems?", "answer": "F", "explanation": "Paragraph C notes satellite imagery was deployed to track massive forest fires.", "reference": "Paragraph C"},
                {"number": 34, "prompt": "Why satellites technology is used in medicine area?", "answer": "B", "explanation": "Paragraph D explains telemedicine links remote, inaccessible villages with hospital doctors.", "reference": "Paragraph D"},
                {"number": 35, "prompt": "Why Asian countries satellite technology is limited for development?", "answer": "D", "explanation": "Paragraph E discusses regulatory, geopolitical and social constraints hindering collaboration.", "reference": "Paragraph E"},
                {"number": 36, "prompt": "Why satellites technology is deployed in agricultural area?", "answer": "A", "explanation": "Paragraph D details satellite crop surveillance aiding harvest management.", "reference": "Paragraph D"}
            ]
        },
        {
            "type": "true_false_not_given",
            "instruction": "Do the following statements agree with the information given in Reading Passage 3? In boxes **37–40** on your answer sheet, choose **TRUE** if the statement agrees with the information, **FALSE** if the statement contradicts the information, or **NOT GIVEN** if there is no information on this.",
            "questions": [
                {"number": 37, "prompt": "Ancient China had already deployed rockets as a military purpose as early as 500 years ago.", "answer": "FALSE", "explanation": "Paragraph A states rocket use for defense appeared over eight centuries ago.", "reference": "Paragraph A"},
                {"number": 38, "prompt": "Space technology has enhanced literacy of Asia.", "answer": "NOT GIVEN", "explanation": "While educational broadcasting is cited, literacy statistics are not presented.", "reference": "Paragraph D"},
                {"number": 39, "prompt": "photos taken by satellites with certain technology help predict some natural catastrophes prevention and surveillance.", "answer": "TRUE", "explanation": "Paragraph C describes infrared weather sensors warning against impending storms and fires.", "reference": "Paragraph C"},
                {"number": 40, "prompt": "commercial competition constitutes a boosting factor to Asian technology development.", "answer": "TRUE", "explanation": "Paragraph F notes commercial rivalry drove rapid design innovations and lower launch costs.", "reference": "Paragraph F"}
            ]
        }
    ]

    test9_dict = {
        "id": "academic-reading-15",
        "module": "reading",
        "variant": "academic",
        "title": "Academic Reading Practice Test 15",
        "shortTitle": "Practice Test 15",
        "durationMinutes": 60,
        "totalQuestions": 40,
        "sortOrder": 15,
        "license": "Original work written for this project. All rights reserved by the site owner.",
        "passages": [
            {
                "passageNumber": 1,
                "title": "Agriculture and Tourism",
                "subtitle": "Economic diversification through rural farm visits and regional culinary festivals",
                "paragraphs": p1_paras,
                "groups": p1_groups
            },
            {
                "passageNumber": 2,
                "title": "Cosmetics in Ancient Past",
                "subtitle": "Antiquity of perfumes, kohl pigments and personal hygiene across ancient civilizations",
                "paragraphs": p2_paras,
                "groups": p2_groups
            },
            {
                "passageNumber": 3,
                "title": "Asian Space Satellite Technology",
                "subtitle": "Emergence of commercial aerospace, remote sensing and microsatellite networks across Asia",
                "paragraphs": p3_paras,
                "groups": p3_groups
            }
        ]
    }
    save_and_validate_test(test9_dict)

if __name__ == "__main__":
    build_test_15()
