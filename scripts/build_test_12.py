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

def build_test_12():
    txt = get_test_full_text(doc, 6)
    # Fix broken hyphens
    txt = re.sub(r'(\b[a-zA-Z]+)-\n([a-zA-Z]+\b)', r'\1\2', txt)
    txt = txt.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    txt = txt.replace('—', '—').replace('–', '-')

    sec_matches = list(re.finditer(r'(?:^|\n)\s*(?:SECTION|READING PASSAGE)\s*([123])\s*(?:\n|$)', txt, flags=re.I))
    
    # ------------------- SECTION 1 -------------------
    s1 = txt[sec_matches[0].end():sec_matches[1].start()]
    m_q1 = re.search(r'Questions?\s*1\s*[-–]\s*9', s1, re.I)
    p1_raw = s1[:m_q1.start()].strip()
    # Remove title
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
            "type": "matching_information",
            "instruction": "Reading Passage 1 has seven paragraphs, **A–G**.\n\nWhich paragraph contains the following information?\n\nWrite the correct letter, **A–G**, in boxes **1–9** on your answer sheet.\n\n*NB: You may use any letter more than once.*",
            "questions": [
                {"number": 1, "prompt": "A description of how otters regulate vision underwater", "answer": "B", "explanation": "Paragraph B explains how otters focus underwater.", "reference": "Paragraph B"},
                {"number": 2, "prompt": "The fit-for-purpose characteristics of otter's body shape", "answer": "A", "explanation": "Paragraph A describes long, thin bodies and short legs.", "reference": "Paragraph A"},
                {"number": 3, "prompt": "A reference to an underdeveloped sense", "answer": "B", "explanation": "Paragraph B refers to scent and sensory traits.", "reference": "Paragraph B"},
                {"number": 4, "prompt": "An explanation of why historical hunting was conducted", "answer": "F", "explanation": "Paragraph F notes historical hunting for pelts and sport.", "reference": "Paragraph F"},
                {"number": 5, "prompt": "A reference to the varied dietary preferences of otters", "answer": "C", "explanation": "Paragraph C details diet of fish, crabs, and occasional small mammals.", "reference": "Paragraph C"},
                {"number": 6, "prompt": "A description of breeding habits and birth chambers", "answer": "E", "explanation": "Paragraph E outlines giving birth in secure holts and dens.", "reference": "Paragraph E"},
                {"number": 7, "prompt": "A description of modern threats to recovering otter populations", "answer": "G", "explanation": "Paragraph G mentions road kills and pollution.", "reference": "Paragraph G"},
                {"number": 8, "prompt": "The reintroduction and recovery across river habitats", "answer": "G", "explanation": "Paragraph G describes population recovery across Britain.", "reference": "Paragraph G"},
                {"number": 9, "prompt": "Physical swimming adaptations such as webbed feet and rudders", "answer": "A", "explanation": "Paragraph A discusses tails used as rudders and webbed paws.", "reference": "Paragraph A"}
            ]
        },
        {
            "type": "short_answer",
            "instruction": "Answer the questions below. Choose **NO MORE THAN THREE WORDS AND/OR A NUMBER** from the passage for each answer.\n\nWrite your answers in boxes **10–13** on your answer sheet.",
            "maxWords": 3,
            "questions": [
                {"number": 10, "prompt": "What affects the outer fur of otters?", "answer": ["sea water", "salt"], "explanation": "Paragraph B and E discuss the effect of sea water and salt on fur.", "reference": "Paragraph B & E"},
                {"number": 11, "prompt": "What skill is not necessary for Asian short-clawed otters?", "answer": ["swimming speed"], "explanation": "Paragraph A explains short-clawed otters do not require great swimming speed.", "reference": "Paragraph A"},
                {"number": 12, "prompt": "Which type of otters has the shortest range?", "answer": ["coastal otters"], "explanation": "Paragraph C states coastal otters have much smaller ranges.", "reference": "Paragraph C"},
                {"number": 13, "prompt": "Which type of animals do otters hunt occasionally?", "answer": ["small mammals"], "explanation": "Paragraph C notes small mammals are occasionally taken.", "reference": "Paragraph C"}
            ]
        }
    ]

    # ------------------- SECTION 2 -------------------
    s2 = txt[sec_matches[1].end():sec_matches[2].start()]
    m_q14 = re.search(r'Questions?\s*14\s*[-–]\s*20', s2, re.I)
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
            "type": "matching_headings",
            "instruction": "Reading Passage 2 has seven paragraphs, **A–G**.\n\nChoose the correct heading for each paragraph from the list of headings below.\n\nWrite the correct number, **i–x**, in boxes **14–20** on your answer sheet.",
            "options": [
                {"key": "i", "text": "The role of weather and climate in navigation"},
                {"key": "ii", "text": "Unexplained distances traveled beyond breeding requirements"},
                {"key": "iii", "text": "Anatomy of flight and wing structure"},
                {"key": "iv", "text": "Unique physical adaptations enabling long flights"},
                {"key": "v", "text": "The primary underlying motivation for migration"},
                {"key": "vi", "text": "Feeding habits during flight stops"},
                {"key": "vii", "text": "Navigational cues and internal compass systems"},
                {"key": "viii", "text": "Flock communication during darkness"},
                {"key": "ix", "text": "Mating calls across migratory routes"},
                {"key": "x", "text": "The mystery of innate route discovery in juvenile birds"}
            ],
            "questions": [
                {"number": 14, "prompt": "Paragraph A", "answer": "iv", "explanation": "Paragraph A details physiological flight design features.", "reference": "Paragraph A"},
                {"number": 15, "prompt": "Paragraph B", "answer": "v", "explanation": "Paragraph B outlines the fundamental reason birds migrate to find food.", "reference": "Paragraph B"},
                {"number": 16, "prompt": "Paragraph C", "answer": "ii", "explanation": "Paragraph C examines why birds journey further than strictly needed.", "reference": "Paragraph C"},
                {"number": 17, "prompt": "Paragraph D", "answer": "x", "explanation": "Paragraph D discusses how young cuckoos navigate without parents.", "reference": "Paragraph D"},
                {"number": 18, "prompt": "Paragraph E", "answer": "vii", "explanation": "Paragraph E outlines compass mechanisms using sun and stars.", "reference": "Paragraph E"},
                {"number": 19, "prompt": "Paragraph F", "answer": "i", "explanation": "Paragraph F covers weather hazards, winds, and sensing weather changes.", "reference": "Paragraph F"},
                {"number": 20, "prompt": "Paragraph G", "answer": "vii", "explanation": "Paragraph G illustrates homing feats and sensory navigation.", "reference": "Paragraph G"}
            ]
        },
        {
            "type": "choose_multiple",
            "instruction": "Choose **TWO** letters, **A–E**.\n\nWrite the correct letters in boxes **21** and **22** on your answer sheet.",
            "prompt": "Which **TWO** of the following statements are true of bird migration?",
            "options": [
                {"key": "A", "text": "Birds often fly further than they need to."},
                {"key": "B", "text": "Birds traveling in family groups are safe."},
                {"key": "C", "text": "Birds flying at night need less water."},
                {"key": "D", "text": "Birds have much sharper eye-sight than humans."},
                {"key": "E", "text": "Only shore birds are resistant to strong winds."}
            ],
            "answer": ["A", "C"],
            "questions": [
                {"number": 21, "explanation": "Paragraph C notes many birds journey much further than necessary.", "reference": "Paragraph C"},
                {"number": 22, "explanation": "Paragraph F explains nocturnal flight minimizes water loss.", "reference": "Paragraph F"}
            ]
        },
        {
            "type": "sentence_completion",
            "instruction": "Complete the sentences below using **NO MORE THAN TWO WORDS** from the passage.\n\nWrite your answers in boxes **23–26** on your answer sheet.",
            "maxWords": 2,
            "questions": [
                {"number": 23, "prompt": "It is a great mystery that young birds like cuckoos can find their wintering grounds without {{23}}.", "answer": ["parental guidance"], "explanation": "Paragraph D states juveniles reach destinations without parental guidance.", "reference": "Paragraph D"},
                {"number": 24, "prompt": "Evidence shows birds can tell directions like a {{24}} by observing the sun and stars.", "answer": ["compass"], "explanation": "Paragraph E notes birds use solar and stellar cues like a compass.", "reference": "Paragraph E"},
                {"number": 25, "prompt": "One advantage for birds flying at night is that they can avoid contact with {{25}}.", "answer": ["predators"], "explanation": "Paragraph F points out night travel reduces exposure to predators.", "reference": "Paragraph F"},
                {"number": 26, "prompt": "Laboratory tests show that birds can detect weather changes without {{26}} signs.", "answer": ["visible"], "explanation": "Paragraph F explains detection occurs before any visible signs.", "reference": "Paragraph F"}
            ]
        }
    ]

    # ------------------- SECTION 3 -------------------
    s3 = txt[sec_matches[2].end():]
    m_q27 = re.search(r'Questions?\s*27\s*[-–]\s*32', s3, re.I)
    p3_raw = s3[:m_q27.start()].strip()
    p3_lines = p3_raw.splitlines()
    title3 = p3_lines[0].strip()
    p3_body = '\n'.join(p3_lines[1:])
    p3_splits = re.split(r'(?:^|\n)\s*([A-I])\.\s+', p3_body)
    p3_paras = []
    for i in range(1, len(p3_splits), 2):
        lbl = p3_splits[i]
        body = re.sub(r'\s+', ' ', p3_splits[i+1]).strip()
        p3_paras.append({"label": lbl, "text": body})

    p3_groups = [
        {
            "type": "matching_features",
            "instruction": "Use the information in the passage to match each use of talc powder with the correct application (**A–C**).\n\nWrite the appropriate letters, **A–C**, in boxes **27–32** on your answer sheet.\n\n*NB: You may use any letter more than once.*\n\n* **A** Fruit protection\n* **B** Chewing gum business\n* **C** Olive oil extraction",
            "options": [
                {"key": "A", "text": "Fruit protection"},
                {"key": "B", "text": "Chewing gum business"},
                {"key": "C", "text": "Olive oil extraction"}
            ],
            "questions": [
                {"number": 27, "prompt": "Talc is used to increase the size of drops.", "answer": "C", "explanation": "Paragraph E notes talc increases droplet size in oil processing.", "reference": "Paragraph E"},
                {"number": 28, "prompt": "Talc is applied to reduce foaming.", "answer": "C", "explanation": "Paragraph E notes reduction of foam in oil extraction.", "reference": "Paragraph E"},
                {"number": 29, "prompt": "Talc is employed as a filler of base.", "answer": "B", "explanation": "Paragraph C discusses talc as gum base filler.", "reference": "Paragraph C"},
                {"number": 30, "prompt": "Talc is modified and prevented sunburn.", "answer": "A", "explanation": "Paragraph G explains talc sprays protecting fruit crops from sunburn.", "reference": "Paragraph G"},
                {"number": 31, "prompt": "Talc is added to stop stickiness.", "answer": "B", "explanation": "Paragraph B outlines talc eliminating stickiness in gum manufacturing.", "reference": "Paragraph B"},
                {"number": 32, "prompt": "Talc is used to increase production.", "answer": "C", "explanation": "Paragraph E explains talc boosts olive oil extraction yields.", "reference": "Paragraph E"}
            ]
        },
        {
            "type": "summary_completion",
            "instruction": "Complete the following summary of the paragraphs of Reading Passage, using **NO MORE THAN TWO WORDS** from the Reading Passage for each answer.\n\nWrite your answers in boxes **33–38** on your answer sheet.",
            "maxWords": 2,
            "content": "Spanish olive oil industry has been using talc in oil extraction process for about {{33}} years. It is useful in dealing with difficult olives which often produce high amount of {{34}} because of the high content of solid materials. When smaller factories release {{35}}, it could be {{36}} to the environment because it is hard to {{37}} and usually takes time as it contains emulsified oil. However, talc powder added in the process is able to absorb the emulsified oil. It improves the oil extraction production, because with aid of talc powder, size of oil {{38}} increased.",
            "questions": [
                {"number": 33, "answer": ["20"], "explanation": "Paragraph E notes Spanish processors have used talc for about 20 years.", "reference": "Paragraph E"},
                {"number": 34, "answer": ["foam"], "explanation": "Paragraph E mentions troublesome foam produced by difficult olives.", "reference": "Paragraph E"},
                {"number": 35, "answer": ["waste water", "wastewater"], "explanation": "Paragraph F discusses disposal of waste water.", "reference": "Paragraph F"},
                {"number": 36, "answer": ["harmful"], "explanation": "Paragraph F describes environmental harm from untreated waste water.", "reference": "Paragraph F"},
                {"number": 37, "answer": ["biodegrade", "bodegrade"], "explanation": "Paragraph F explains wastewater is hard to biodegrade.", "reference": "Paragraph F"},
                {"number": 38, "answer": ["droplets"], "explanation": "Paragraph E states oil droplets increase in size.", "reference": "Paragraph E"}
            ]
        },
        {
            "type": "short_answer",
            "instruction": "Answer the questions below using **NO MORE THAN THREE WORDS** from the passage for each answer.\n\nWrite your answers in boxes **39** and **40** on your answer sheet.",
            "maxWords": 3,
            "questions": [
                {"number": 39, "prompt": "In which process is talc used to clear the stickiness of chewing gum?", "answer": ["lamination and packing"], "explanation": "Paragraph D specifies lamination and packing.", "reference": "Paragraph D"},
                {"number": 40, "prompt": "Which group of farmers does Invelop intend to target in a long view?", "answer": ["grape growers"], "explanation": "Paragraph H highlights grape growers as prime target users.", "reference": "Paragraph H"}
            ]
        }
    ]

    test6_dict = {
        "id": "academic-reading-12",
        "module": "reading",
        "variant": "academic",
        "title": "Academic Reading Practice Test 12",
        "shortTitle": "Practice Test 12",
        "durationMinutes": 60,
        "totalQuestions": 40,
        "sortOrder": 12,
        "license": "Original work written for this project. All rights reserved by the site owner.",
        "passages": [
            {
                "passageNumber": 1,
                "title": "Otter",
                "subtitle": "Anatomical adaptations and conservation of semiaquatic predators",
                "paragraphs": p1_paras,
                "groups": p1_groups
            },
            {
                "passageNumber": 2,
                "title": "Bird Migration 2",
                "subtitle": "Sensory, celestial and geomagnetic navigation mechanisms of migratory birds",
                "paragraphs": p2_paras,
                "groups": p2_groups
            },
            {
                "passageNumber": 3,
                "title": "Talc Powder",
                "subtitle": "Diverse industrial and agricultural uses of magnesium silicate mineral",
                "paragraphs": p3_paras,
                "groups": p3_groups
            }
        ]
    }
    save_and_validate_test(test6_dict)

if __name__ == "__main__":
    build_test_12()
