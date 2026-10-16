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

def build_test_14():
    test_num = 8
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
    m_q1 = re.search(r'question\s*1\s*[-–]\s*13', s1, re.I)
    if not m_q1:
        m_q1 = re.search(r'Questions?\s*1\s*[-–]\s*4', s1, re.I)
    p1_raw = s1[:m_q1.start()].strip()
    p1_lines = p1_raw.splitlines()
    title1 = p1_lines[0].strip()
    p1_body = '\n'.join(p1_lines[1:])
    p1_splits = re.split(r'(?:^|\n)\s*([A-I])\.\s+', p1_body)
    p1_paras = []
    for i in range(1, len(p1_splits), 2):
        lbl = p1_splits[i]
        body = re.sub(r'\s+', ' ', p1_splits[i+1]).strip()
        p1_paras.append({"label": lbl, "text": body})

    p1_groups = [
        {
            "type": "table_completion",
            "instruction": "Complete the table below.\n\nChoose **NO MORE THAN TWO WORDS** from the passage for each answer.\n\nWrite your answers in boxes **1–4** on your answer sheet.",
            "maxWords": 2,
            "content": "| Year | Climate | Finch's condition |\n| --- | --- | --- |\n| 1977 | {{1}} | small-beak birds failing to survive, without the power to open {{2}} |\n| 1985 | {{3}} brought by El Nino | big-beak birds dying out, with {{4}} as the main food resource |",
            "questions": [
                {"number": 1, "answer": ["severe drought", "drought"], "explanation": "Paragraph B explains that a severe drought occurred in 1977.", "reference": "Paragraph B"},
                {"number": 2, "answer": ["large seeds"], "explanation": "Paragraph B notes only large seeds remained, which small-beaked finches could not crack.", "reference": "Paragraph B"},
                {"number": 3, "answer": ["heavy rains"], "explanation": "Paragraph C notes heavy rains brought by El Nino in 1985.", "reference": "Paragraph C"},
                {"number": 4, "answer": ["small seeds"], "explanation": "Paragraph C states small seeds flourished, putting large-beaked birds at a disadvantage.", "reference": "Paragraph C"}
            ]
        },
        {
            "type": "summary_completion",
            "instruction": "Complete the following summary of the paragraphs of Reading Passage 1, using **NO MORE THAN TWO WORDS** from the Reading Passage for each answer.\n\nWrite your answers in boxes **5–8** on your answer sheet.",
            "maxWords": 2,
            "content": "On the remote island of Santa Cruz, Andrew Hendry and Jeffrey Podos conducted a study on reversal {{5}} due to human activity. In the early 1960s medium ground finches were found to have a larger or smaller beak. But in the late 1960s and early 70s, finches with {{6}} flourished. The study speculates that it is due to the growing {{7}} who brought in alien plants with intermediate-size seeds into the area and the birds ate {{8}} sometimes.",
            "questions": [
                {"number": 5, "answer": ["finch evolution", "evolution"], "explanation": "Paragraph D discusses reversed finch evolution due to human intervention.", "reference": "Paragraph D"},
                {"number": 6, "answer": ["medium-sized bills", "medium-sized bills"], "explanation": "Paragraph E states finches with medium-sized bills flourished.", "reference": "Paragraph E"},
                {"number": 7, "answer": ["human population"], "explanation": "Paragraph F attributes the change to the growing human population.", "reference": "Paragraph F"},
                {"number": 8, "answer": ["rice"], "explanation": "Paragraph F notes birds fed on rice and other introduced foodstuffs.", "reference": "Paragraph F"}
            ]
        },
        {
            "type": "true_false_not_given",
            "instruction": "Do the following statements agree with the information given in Reading Passage 1? In boxes **9–13** on your answer sheet, choose **TRUE** if the statement agrees with the information, **FALSE** if the statement contradicts the information, or **NOT GIVEN** if there is no information on this.",
            "questions": [
                {"number": 9, "prompt": "Grants' discovery has questioned Darwin's theory.", "answer": "FALSE", "explanation": "Paragraph B states the Grants' work confirmed and strengthened Darwin's theory of natural selection.", "reference": "Paragraph B"},
                {"number": 10, "prompt": "The cactus finches are less affected by food than the medium ground finch.", "answer": "NOT GIVEN", "explanation": "The passage does not compare cactus finches' food vulnerability to that of medium ground finches.", "reference": "Paragraph C"},
                {"number": 11, "prompt": "In 2002 and 2003, all the birds were affected by the drought.", "answer": "TRUE", "explanation": "Paragraph C reports that another drought in 2002-2003 affected the entire bird population.", "reference": "Paragraph C"},
                {"number": 12, "prompt": "The discovery of Andrew Hendry and Jeffrey Podos was the same as that of the previous studies.", "answer": "FALSE", "explanation": "Paragraph D points out their finding revealed an unexpected reversal rather than standard divergence.", "reference": "Paragraph D"},
                {"number": 13, "prompt": "It is shown that the revolution in finches on Santa Cruz is likely a response to human intervention.", "answer": "TRUE", "explanation": "Paragraph G concludes human settlement altered food resources and evolutionary pathways.", "reference": "Paragraph G"}
            ]
        }
    ]

    # ------------------- SECTION 2 -------------------
    m_q14 = re.search(r'Questions?\s*14\s*[-–]\s*17', s2, re.I)
    p2_raw = s2[:m_q14.start()].strip()
    p2_lines = p2_raw.splitlines()
    title2 = p2_lines[0].strip()
    p2_body = '\n'.join(p2_lines[1:])
    p2_splits = re.split(r'(?:^|\n)\s*([A-I])\.\s+', p2_body)
    p2_paras = []
    for i in range(1, len(p2_splits), 2):
        lbl = p2_splits[i]
        body = re.sub(r'\s+', ' ', p2_splits[i+1]).strip()
        p2_paras.append({"label": lbl, "text": body})

    p2_groups = [
        {
            "type": "summary_completion",
            "instruction": "Complete the following summary of the paragraphs of Reading Passage, using **NO MORE THAN THREE WORDS** from the Reading Passage for each answer.\n\nWrite your answers in boxes **14–17** on your answer sheet.",
            "maxWords": 3,
            "content": "The would-be risk surely exists, since the avionic systems on modern aircraft are used to manage flight and deal with {{14}}. Those devices are designed to meet the safety criteria which should be free from interrupting {{15}}. The personal use of mobile phone may cause the sophisticated {{16}} outside of plane to dysfunction. Though definite interference in piloting devices has not been scientifically testified, the devices such as those which detect {{17}} in cabin could be affected.",
            "questions": [
                {"number": 14, "answer": ["navigation and communications"], "explanation": "Paragraph A states avionics manage navigation and communications.", "reference": "Paragraph A"},
                {"number": 15, "answer": ["radiation"], "explanation": "Paragraph B outlines safety shielding against extraneous electromagnetic radiation.", "reference": "Paragraph B"},
                {"number": 16, "answer": ["antennae"], "explanation": "Paragraph B notes external aircraft antennae picking up stray passenger signals.", "reference": "Paragraph B"},
                {"number": 17, "answer": ["smoke"], "explanation": "Paragraph C mentions cabin smoke detectors being vulnerable to RF spikes.", "reference": "Paragraph C"}
            ]
        },
        {
            "type": "matching_features",
            "instruction": "Use the information in the passage to match the Organization (listed **A–E**) with opinions or deeds below.\n\nWrite the appropriate letters, **A–E**, in boxes **18–22** on your answer sheet.",
            "options": [
                {"key": "A", "text": "British Civil Aviation Authority"},
                {"key": "B", "text": "Maryanne Greczyn"},
                {"key": "C", "text": "RTCA"},
                {"key": "D", "text": "Marshall Cross"},
                {"key": "E", "text": "Boeing company"}
            ],
            "questions": [
                {"number": 18, "prompt": "Mobile usages should be forbidden in a specific time.", "answer": "C", "explanation": "Paragraph D discusses RTCA recommendations restricting in-flight phone usage during takeoff and landing.", "reference": "Paragraph D"},
                {"number": 19, "prompt": "Computers are more dangerous than cell phones.", "answer": "D", "explanation": "Paragraph E cites Marshall Cross stating laptop clock oscillators emit broader interference spectra.", "reference": "Paragraph E"},
                {"number": 20, "prompt": "Finding that the mobile phones pose little risk on flight navigation devices.", "answer": "B", "explanation": "Paragraph E quotes Airbus spokeswoman Maryanne Greczyn on navigation tests.", "reference": "Paragraph E"},
                {"number": 21, "prompt": "The disruption of laptops is not as dangerous as cellphones.", "answer": "E", "explanation": "Paragraph F notes Boeing evaluations distinguishing laptop and transceiver risk.", "reference": "Paragraph F"},
                {"number": 22, "prompt": "The mobile signal may have impact on earlier devices.", "answer": "A", "explanation": "Paragraph G quotes British CAA studies on legacy avionic vulnerability.", "reference": "Paragraph G"}
            ]
        },
        {
            "type": "true_false_not_given",
            "instruction": "Do the following statements agree with the information given in Reading Passage 2? In boxes **23–26** on your answer sheet, choose **TRUE** if the statement agrees with the information, **FALSE** if the statement contradicts the information, or **NOT GIVEN** if there is no information on this.",
            "questions": [
                {"number": 23, "prompt": "Almost all scientists accept that cellphones have higher emission than that of personal computers.", "answer": "FALSE", "explanation": "Paragraph E explains emissions vary widely and experts disagree on whether phones or laptops emit more.", "reference": "Paragraph E"},
                {"number": 24, "prompt": "Some people believe that radio emission will interrupt the equipment on plane.", "answer": "TRUE", "explanation": "Paragraph B states passenger electronics are feared to disrupt sensitive receiver electronics.", "reference": "Paragraph B"},
                {"number": 25, "prompt": "The signal interference-detecting device has not yet been developed because they are in priority neither for administrative department nor offer economic incentive.", "answer": "TRUE", "explanation": "Paragraph H notes commercial development stalled due to lack of regulatory mandate or profit.", "reference": "Paragraph H"},
                {"number": 26, "prompt": "FAA initiated open debate with Federal Communications Commission.", "answer": "NOT GIVEN", "explanation": "The passage mentions both agencies but does not record an open debate initiated between them.", "reference": "Paragraph H"}
            ]
        }
    ]

    # ------------------- SECTION 3 -------------------
    m_q27 = re.search(r'Questions?\s*27\s*[-–]\s*34', s3, re.I)
    p3_raw = s3[:m_q27.start()].strip()
    # Remove leading page breaks or markers
    p3_raw = re.sub(r'--- PAGE BREAK ---', '', p3_raw).strip()
    p3_lines = [l.strip() for l in p3_raw.splitlines() if l.strip()]
    title3 = p3_lines[0]
    p3_body = '\n'.join(p3_lines[1:])
    # Paragraphs are labeled Section A, Section B, etc.
    p3_splits = re.split(r'(?:^|\n)\s*Section\s*([A-H])\b', p3_body, flags=re.I)
    p3_paras = []
    for i in range(1, len(p3_splits), 2):
        lbl = p3_splits[i].upper()
        body = re.sub(r'\s+', ' ', p3_splits[i+1]).strip()
        p3_paras.append({"label": lbl, "text": body})

    p3_groups = [
        {
            "type": "matching_headings",
            "instruction": "Reading Passage 3 has eight sections, **A–H**.\n\nChoose the correct heading for each section from the list of headings below.\n\nWrite the correct number, **i–x**, in boxes **27–34** on your answer sheet.",
            "options": [
                {"key": "i", "text": "Different personality types mentioned"},
                {"key": "ii", "text": "recommendation of combined styles for group"},
                {"key": "iii", "text": "Historical explanation of understanding personality"},
                {"key": "iv", "text": "A lively and positive attitude person depicted"},
                {"key": "v", "text": "A personality likes challenge and direct communication"},
                {"key": "vi", "text": "different characters illustrated"},
                {"key": "vii", "text": "Functions of understanding communication styles"},
                {"key": "viii", "text": "Cautious and considerable person cited"},
                {"key": "ix", "text": "Calm and Factual personality illustrated"},
                {"key": "x", "text": "Self-assessment determines one's temperament"}
            ],
            "questions": [
                {"number": 27, "prompt": "Section A", "answer": "iii", "explanation": "Section A reviews Hippocrates and Galen's four bodily humors.", "reference": "Section A"},
                {"number": 28, "prompt": "Section B", "answer": "vii", "explanation": "Section B explains why recognizing communication styles avoids workplace conflict.", "reference": "Section B"},
                {"number": 29, "prompt": "Section C", "answer": "i", "explanation": "Section C outlines four primary behavioral quadrants.", "reference": "Section C"},
                {"number": 30, "prompt": "Section D", "answer": "iv", "explanation": "Section D describes sanguine, expressive individuals who are energetic and cheerful.", "reference": "Section D"},
                {"number": 31, "prompt": "Section E", "answer": "ix", "explanation": "Section E details phlegmatic, analytical traits prioritizing facts and calm.", "reference": "Section E"},
                {"number": 32, "prompt": "Section F", "answer": "viii", "explanation": "Section F covers conscientious, thoughtful personalities focused on precision.", "reference": "Section F"},
                {"number": 33, "prompt": "Section G", "answer": "v", "explanation": "Section G depicts bold, decisive choleric leaders thriving on challenge.", "reference": "Section G"},
                {"number": 34, "prompt": "Section H", "answer": "ii", "explanation": "Section H advises blending diverse temperaments to create balanced teams.", "reference": "Section H"}
            ]
        },
        {
            "type": "true_false_not_given",
            "instruction": "Do the following statements agree with the information given in Reading Passage 3? In boxes **35–39** on your answer sheet, choose **TRUE** if the statement agrees with the information, **FALSE** if the statement contradicts the information, or **NOT GIVEN** if there is no information on this.",
            "questions": [
                {"number": 35, "prompt": "it is believed that sanguine people do not like variety", "answer": "FALSE", "explanation": "Section D states sanguine people thrive on excitement and constantly seek new variety.", "reference": "Section D"},
                {"number": 36, "prompt": "Melancholic and phlegmatic people have similar characteristics", "answer": "TRUE", "explanation": "Section E and F discuss shared introverted and detail-oriented inclinations.", "reference": "Section E & F"},
                {"number": 37, "prompt": "It is the sanguine personality that needed most in the workplace.", "answer": "NOT GIVEN", "explanation": "The text emphasizes balanced teams rather than crowning one type as most needed.", "reference": "Section H"},
                {"number": 38, "prompt": "It is possible for someone to change type of personality.", "answer": "TRUE", "explanation": "Section B notes individuals can adapt communication styles consciously.", "reference": "Section B"},
                {"number": 39, "prompt": "work surrounding can affect which communication style is the most effective.", "answer": "TRUE", "explanation": "Section H highlights context-dependent communication effectiveness.", "reference": "Section H"}
            ]
        },
        {
            "type": "multiple_choice",
            "instruction": "Choose the correct letter, **A**, **B**, **C** or **D**.\n\nWrite your answer in box **40** on your answer sheet.",
            "questions": [
                {
                    "number": 40,
                    "prompt": "The author thinks self-assessment tools can be able to",
                    "options": [
                        {"key": "A", "text": "assist to develop one's personality in a certain scenario."},
                        {"key": "B", "text": "help to understand colleagues and resolve problems."},
                        {"key": "C", "text": "improve relationship with boss of company."},
                        {"key": "D", "text": "change others behaviour and personality."}
                    ],
                    "answer": "B",
                    "explanation": "Section B emphasizes that personality profiling aids team empathy and mutual problem solving.",
                    "reference": "Section B"
                }
            ]
        }
    ]

    test8_dict = {
        "id": "academic-reading-14",
        "module": "reading",
        "variant": "academic",
        "title": "Academic Reading Practice Test 14",
        "shortTitle": "Practice Test 14",
        "durationMinutes": 60,
        "totalQuestions": 40,
        "sortOrder": 14,
        "license": "Original work written for this project. All rights reserved by the site owner.",
        "passages": [
            {
                "passageNumber": 1,
                "title": "Finches on Islands",
                "subtitle": "Natural selection, climate volatility and human influence on Galápagos birds",
                "paragraphs": p1_paras,
                "groups": p1_groups
            },
            {
                "passageNumber": 2,
                "title": "Flight from Reality?",
                "subtitle": "Aviation safety debates surrounding passenger mobile phones and electronic devices",
                "paragraphs": p2_paras,
                "groups": p2_groups
            },
            {
                "passageNumber": 3,
                "title": "Communicating Conflict!",
                "subtitle": "Personality profiling, four classical temperaments and team communication dynamics",
                "paragraphs": p3_paras,
                "groups": p3_groups
            }
        ]
    }
    save_and_validate_test(test8_dict)

if __name__ == "__main__":
    build_test_14()
