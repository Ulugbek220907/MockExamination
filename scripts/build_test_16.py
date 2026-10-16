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

def build_test_16():
    test_num = 10
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
    m_q1 = re.search(r'Questions?\s*1\s*[-–]\s*5', s1, re.I)
    p1_raw = s1[:m_q1.start()].strip()
    p1_lines = p1_raw.splitlines()
    title1 = p1_lines[0].strip()
    p1_body = '\n'.join(p1_lines[1:])
    p1_paras = [{"label": "", "text": re.sub(r'\s+', ' ', p).strip()} for p in re.split(r'\n\s*\n', p1_body) if p.strip()]

    p1_groups = [
        {
            "type": "multiple_choice",
            "instruction": "Choose the correct letter, **A**, **B**, **C** or **D**.\n\nWrite the correct letter in boxes **1–5** on your answer sheet.",
            "questions": [
                {
                    "number": 1,
                    "prompt": "The main reason why koala declined is that they are killed EXCEPT FOR",
                    "options": [
                        {"key": "A", "text": "by poachers"},
                        {"key": "B", "text": "by diseases they got"},
                        {"key": "C", "text": "giving too many birth yet survived little"},
                        {"key": "D", "text": "accidents on the road"}
                    ],
                    "answer": "C",
                    "explanation": "The text lists hunting, disease, bushfires, and car strikes, but not high birth mortality.",
                    "reference": "Passage 1"
                },
                {
                    "number": 2,
                    "prompt": "What can help koalas fully digest their food?",
                    "options": [
                        {"key": "A", "text": "toxic substance in the leaves"},
                        {"key": "B", "text": "organs that dissolve the fibres"},
                        {"key": "C", "text": "remaining inactive for a period to digest"},
                        {"key": "D", "text": "eating eucalyptus trees"}
                    ],
                    "answer": "C",
                    "explanation": "The passage explains koalas conserve energy and spend up to 20 hours asleep or resting to break down toxic eucalyptus oils.",
                    "reference": "Passage 1"
                },
                {
                    "number": 3,
                    "prompt": "What would koalas do when facing the dangerous situation?",
                    "options": [
                        {"key": "A", "text": "show signs of being offended"},
                        {"key": "B", "text": "counter attack furiously"},
                        {"key": "C", "text": "use sharp claws to rip the man"},
                        {"key": "D", "text": "use claws to grip the bark of trees"}
                    ],
                    "answer": "A",
                    "explanation": "The passage notes stressed koalas display distress signals rather than attacking.",
                    "reference": "Passage 1"
                },
                {
                    "number": 4,
                    "prompt": "In what ways Australian zoos exploit koalas?",
                    "options": [
                        {"key": "A", "text": "encourage people to breed koalas as pets"},
                        {"key": "B", "text": "allow tourists to hug the koalas"},
                        {"key": "C", "text": "put them on the trees as a symbol"},
                        {"key": "D", "text": "establish a koala campaign"}
                    ],
                    "answer": "B",
                    "explanation": "The text criticizes commercial handling and cuddle sessions offered to foreign visitors.",
                    "reference": "Passage 1"
                },
                {
                    "number": 5,
                    "prompt": "What would the government do to protect koalas from being endangered?",
                    "options": [
                        {"key": "A", "text": "introduce koala protection guidelines"},
                        {"key": "B", "text": "close some of the zoos"},
                        {"key": "C", "text": "encourage people to resist visiting the zoos"},
                        {"key": "D", "text": "persuade the public to learn more knowledge"}
                    ],
                    "answer": "A",
                    "explanation": "State authorities enacted habitat and handling guidelines.",
                    "reference": "Passage 1"
                }
            ]
        },
        {
            "type": "yes_no_not_given",
            "instruction": "Do the following statements agree with the information given in Reading Passage 1? In boxes **6–12** on your answer sheet, choose **YES** if the statement agrees with the information, **NO** if the statement contradicts the information, or **NOT GIVEN** if there is no information on this.",
            "questions": [
                {"number": 6, "prompt": "new coming human settlers caused danger to koalas.", "answer": "YES", "explanation": "European land clearing devastated koala woodland corridors.", "reference": "Passage 1"},
                {"number": 7, "prompt": "Koalas can still be seen in most of the places in Australia.", "answer": "NO", "explanation": "Their range has contracted drastically across southeastern Australia.", "reference": "Passage 1"},
                {"number": 8, "prompt": "it takes decade for the eucalyptus trees to recover after the fire.", "answer": "NO", "explanation": "Eucalyptus forests regenerate rapidly within months after fire.", "reference": "Passage 1"},
                {"number": 9, "prompt": "Koalas will fight each other when food becomes scarce.", "answer": "NOT GIVEN", "explanation": "The passage mentions territory spacing without describing violent fights.", "reference": "Passage 1"},
                {"number": 10, "prompt": "It is not easy to notice that koalas are ill.", "answer": "YES", "explanation": "Koalas mask signs of chlamydial infection until advanced stages.", "reference": "Passage 1"},
                {"number": 11, "prompt": "Koalas are easily infected with human contagious disease via cuddling.", "answer": "NOT GIVEN", "explanation": "Stress from handling is highlighted, not transmission of human contagion.", "reference": "Passage 1"},
                {"number": 12, "prompt": "Koalas like to hold a person's arm when they are embraced.", "answer": "YES", "explanation": "The text describes instinctual clinging to handlers' arms.", "reference": "Passage 1"}
            ]
        },
        {
            "type": "multiple_choice",
            "instruction": "Choose the correct letter, **A**, **B**, **C** or **D**.\n\nWrite the correct letter in box **13** on your answer sheet.",
            "questions": [
                {
                    "number": 13,
                    "prompt": "From your opinion this article written by",
                    "options": [
                        {"key": "A", "text": "a journalist who write for magazine"},
                        {"key": "B", "text": "a zoo keeper in London Zoo."},
                        {"key": "C", "text": "a tourist who traveling back from Australia"},
                        {"key": "D", "text": "a government official who studies koalas to establish a law"}
                    ],
                    "answer": "A",
                    "explanation": "The narrative perspective and investigative tone correspond to feature journalism.",
                    "reference": "Passage 1"
                }
            ]
        }
    ]

    # ------------------- SECTION 2 -------------------
    m_q14 = re.search(r'Questions?\s*14\s*[-–]\s*18', s2, re.I)
    p2_raw = s2[:m_q14.start()].strip()
    p2_lines = p2_raw.splitlines()
    title2 = p2_lines[0].strip()
    p2_body = '\n'.join(p2_lines[1:])
    p2_splits = re.split(r'(?:^|\n)\s*([A-F])\.\s+', p2_body)
    p2_paras = []
    for i in range(1, len(p2_splits), 2):
        lbl = p2_splits[i]
        body = re.sub(r'\s+', ' ', p2_splits[i+1]).strip()
        p2_paras.append({"label": lbl, "text": body})

    p2_groups = [
        {
            "type": "matching_information",
            "instruction": "Reading Passage 2 has six paragraphs, **A–F**.\n\nWhich paragraph contains the following information?\n\nWrite the correct letter, **A–F**, in boxes **14–18** on your answer sheet.",
            "questions": [
                {"number": 14, "prompt": "The example of research on weather prediction on agriculture", "answer": "D", "explanation": "Paragraph D discusses predicting seasonal Australian rainfall to optimize wheat cropping.", "reference": "Paragraph D"},
                {"number": 15, "prompt": "Antarctic sea ice brings life back to the world oceans' vitality.", "answer": "F", "explanation": "Paragraph F shows deep Antarctic bottom water circulating essential nutrients globally.", "reference": "Paragraph F"},
                {"number": 16, "prompt": "A food chain that influence the animals living pattern based on Antarctic fresh sea ice", "answer": "E", "explanation": "Paragraph E charts krill algae grazing beneath sea ice sustaining penguins, seals and whales.", "reference": "Paragraph E"},
                {"number": 17, "prompt": "The explanation of how atmosphere pressure above Antarctica can impose effect on global climate change", "answer": "C", "explanation": "Paragraph C describes polar vortex circulations and Southern Oscillation indices driving planetary weather.", "reference": "Paragraph C"},
                {"number": 18, "prompt": "Antarctica was once thought to be a forgotten and insignificant continent", "answer": "A", "explanation": "Paragraph A recalls nineteenth-century perceptions of a frozen wasteland detached from global affairs.", "reference": "Paragraph A"}
            ]
        },
        {
            "type": "matching_features",
            "instruction": "Please match the natural phenomenon with correct determined factor.\n\nChoose the correct letter, **A–F**, in boxes **19–21** on your answer sheet.\n\n* **A** Antarctic Circumpolar Current (ACC)\n* **B** katabatic winds\n* **C** rainfall\n* **D** temperature\n* **E** glaciers\n* **F** pressure",
            "options": [
                {"key": "A", "text": "Antarctic Circumpolar Current (ACC)"},
                {"key": "B", "text": "katabatic winds"},
                {"key": "C", "text": "rainfall"},
                {"key": "D", "text": "temperature"},
                {"key": "E", "text": "glaciers"},
                {"key": "F", "text": "pressure"}
            ],
            "questions": [
                {"number": 19, "prompt": "Globally, mass Antarctica's size and {{19}} influence the climate change.", "answer": "D", "explanation": "Paragraph B emphasizes the continent's immense thermal sink and sub-zero temperatures.", "reference": "Paragraph B"},
                {"number": 20, "prompt": "{{20}} contributory to western wind.", "answer": "A", "explanation": "Paragraph B links the ACC and strong circumpolar westerly gale belts.", "reference": "Paragraph B"},
                {"number": 21, "prompt": "Southern Oscillation Index based on air pressure can predict {{21}} in Australia.", "answer": "C", "explanation": "Paragraph D explains pressure differences forecasting drought and rainfall patterns.", "reference": "Paragraph D"}
            ]
        },
        {
            "type": "multiple_choice",
            "instruction": "Choose the correct letter, **A**, **B**, **C** or **D**.\n\nWrite your answers in boxes **22–26** on your answer sheet.",
            "questions": [
                {
                    "number": 22,
                    "prompt": "In the paragraph B, the author want to tell which of the following truth about Antarctic?",
                    "options": [
                        {"key": "A", "text": "To show Antarctica has been a central topic of global warming in Mass media"},
                        {"key": "B", "text": "To illustrate its huge sea ice brings food to million lives to places in the world"},
                        {"key": "C", "text": "To show it is the heart and its significance to the global climate and current"},
                        {"key": "D", "text": "To illustrate it locates in the central spot on Earth geographically"}
                    ],
                    "answer": "C",
                    "explanation": "Paragraph B portrays Antarctica as the planetary engine regulating oceanic and atmospheric currents.",
                    "reference": "Paragraph B"
                },
                {
                    "number": 23,
                    "prompt": "Why do Australian farmers keep an eye on the Antarctic ocean temperature?",
                    "options": [
                        {"key": "A", "text": "Help farmers reduce their economic or ecological losses"},
                        {"key": "B", "text": "Retrieve grassland decreased in the overgrazing process"},
                        {"key": "C", "text": "Prevent animal from dying"},
                        {"key": "D", "text": "A cell provides fertilizer for the grassland"}
                    ],
                    "answer": "A",
                    "explanation": "Paragraph D notes accurate seasonal forecasts mitigate crop failures and drought losses.",
                    "reference": "Paragraph D"
                },
                {
                    "number": 24,
                    "prompt": "What is the final effect of katabatic winds?",
                    "options": [
                        {"key": "A", "text": "Increase the moving speed of ocean current"},
                        {"key": "B", "text": "Increase salt level near ocean surface"},
                        {"key": "C", "text": "Bring fresh ice into southern oceans"},
                        {"key": "D", "text": "Pile up the mountainous ice cap respected by mariners"}
                    ],
                    "answer": "C",
                    "explanation": "Paragraph C explains powerful downslope winds push newly formed ice offshore, exposing open polynyas.",
                    "reference": "Paragraph C"
                },
                {
                    "number": 25,
                    "prompt": "The break of the continental shelf is due to the",
                    "options": [
                        {"key": "A", "text": "Salt and density increase"},
                        {"key": "B", "text": "Salt and density decrease"},
                        {"key": "C", "text": "global warming resulting a rising temperature"},
                        {"key": "D", "text": "fresh ice melting into ocean water"}
                    ],
                    "answer": "C",
                    "explanation": "Paragraph D highlights thermal fracturing and warming shelf margins.",
                    "reference": "Paragraph D"
                },
                {
                    "number": 26,
                    "prompt": "The decrease in number of Whales and seabirds is due to",
                    "options": [
                        {"key": "A", "text": "killer whales are more active around"},
                        {"key": "B", "text": "Sea birds are affected by high sea level salt"},
                        {"key": "C", "text": "less sea ice reduces productivity of food source"},
                        {"key": "D", "text": "seals fail to reproduce babies"}
                    ],
                    "answer": "C",
                    "explanation": "Paragraph E explains declining winter ice diminishes krill nursery habitat.",
                    "reference": "Paragraph E"
                }
            ]
        }
    ]

    # ------------------- SECTION 3 -------------------
    m_q27 = re.search(r'Questions?\s*27\s*[-–]\s*32', s3, re.I)
    p3_raw = s3[:m_q27.start()].strip()
    p3_lines = [l.strip() for l in p3_raw.splitlines() if l.strip()]
    title3 = p3_lines[0]
    p3_body = '\n'.join(p3_lines[1:])
    p3_splits = re.split(r'(?:^|\n)\s*([A-F])\.\s+', p3_body)
    p3_paras = []
    for i in range(1, len(p3_splits), 2):
        lbl = p3_splits[i]
        body = re.sub(r'\s+', ' ', p3_splits[i+1]).strip()
        p3_paras.append({"label": lbl, "text": body})

    p3_groups = [
        {
            "type": "summary_completion",
            "instruction": "Complete the following summary of the Whole Paragraphs of Reading Passage, choosing **A–L** words from the following options.\n\nWrite your answers in boxes **27–32** on your answer sheet.",
            "options": [
                {"key": "A", "text": "gestures"},
                {"key": "B", "text": "clients"},
                {"key": "C", "text": "transaction"},
                {"key": "D", "text": "understanding and assumption"},
                {"key": "E", "text": "accurate"},
                {"key": "F", "text": "documents"},
                {"key": "G", "text": "managers"},
                {"key": "H", "text": "body language"},
                {"key": "I", "text": "long-term"},
                {"key": "J", "text": "effective"},
                {"key": "K", "text": "rivals"},
                {"key": "L", "text": "costly"}
            ],
            "content": "MNCs often encounter language barrier in their daily strategy, then they seek several approaches to solve such problems. First, native language gives them a realistic base in a different language speaking country, but problem turned up when they deal with oversea {{27}}. For example, operation on translation of some key {{28}}, it is inevitable to generate differences by rules from different countries. Another way is to rely on a combination of spoken language and {{29}}, yet a report written that over one-tenth business {{30}} processed in a party language setting. Third way: hire translators. However, firstly it is {{31}}, besides if they are not well-prepared, they have to resort to his/her own {{32}} work.",
            "questions": [
                {"number": 27, "answer": "B", "explanation": "Paragraph B outlines difficulties communicating directly with overseas clients.", "reference": "Paragraph B"},
                {"number": 28, "answer": "F", "explanation": "Paragraph B notes discrepancies translating binding commercial documents.", "reference": "Paragraph B"},
                {"number": 29, "answer": "A", "explanation": "Paragraph C discusses pairing words with gestures.", "reference": "Paragraph C"},
                {"number": 30, "answer": "C", "explanation": "Paragraph C cites surveys indicating transactions compromised by language gaps.", "reference": "Paragraph C"},
                {"number": 31, "answer": "L", "explanation": "Paragraph D points out external translators are expensive and costly.", "reference": "Paragraph D"},
                {"number": 32, "answer": "D", "explanation": "Paragraph D notes translators must make personal assumptions when briefing is incomplete.", "reference": "Paragraph D"}
            ]
        },
        {
            "type": "short_answer",
            "instruction": "Answer the questions below.\n\nChoose **NO MORE THAN THREE WORDS AND/OR A NUMBER** from the passage for each answer.\n\nWrite your answers in boxes **33–39** on your answer sheet.",
            "maxWords": 3,
            "questions": [
                {"number": 33, "prompt": "What understandable reaction does Training pay attention to according to the author?", "answer": ["personnel development"], "explanation": "Paragraph E states training responds to demands for personnel development.", "reference": "Paragraph E"},
                {"number": 34, "prompt": "In what term does the writer describe training during economy depression?", "answer": ["luxury", "the first luxury", "first luxury", "luxuries"], "explanation": "Paragraph E notes training is viewed as the first luxury to be cut.", "reference": "Paragraph E"},
                {"number": 35, "prompt": "What contribution does Volkswagen Group set up for multinational companies?", "answer": ["language strategy", "a language strategy", "model"], "explanation": "Paragraph F describes Volkswagen creating a model language strategy.", "reference": "Paragraph F"},
                {"number": 36, "prompt": "What does Volkswagen Group consider language training as in their company?", "answer": ["strategic solution", "strategic", "tactical solution", "strategic rather than"], "explanation": "Paragraph F explains training is treated as a strategic rather than tactical solution.", "reference": "Paragraph F"},
                {"number": 37, "prompt": "How many stages are needed from basic course to advanced in training?", "answer": ["6", "6 stages", "6 language stages", "six stages"], "explanation": "Paragraph F details a 6-stage progression curriculum.", "reference": "Paragraph F"},
                {"number": 38, "prompt": "How long does a refresher course (single stage) need normally?", "answer": ["90 hours"], "explanation": "Paragraph F states each single stage demands approximately 90 hours.", "reference": "Paragraph F"},
                {"number": 39, "prompt": "At least how long is needed for a specific professional to acquire a foreign language?", "answer": ["three years", "3 years"], "explanation": "Paragraph F indicates a minimum of three years of sustained study.", "reference": "Paragraph F"}
            ]
        },
        {
            "type": "multiple_choice",
            "instruction": "Choose the correct letter, **A**, **B**, **C** or **D**.\n\nWrite your answers in box **40** on your answer sheet.",
            "questions": [
                {
                    "number": 40,
                    "prompt": "What is the Main function of this passage?",
                    "options": [
                        {"key": "A", "text": "to reveal all kinds of language problems that companies may encounter"},
                        {"key": "B", "text": "to exhibits some well-known companies successfully dealing with language difficulties"},
                        {"key": "C", "text": "to evaluate various approaches for language barrier in multinational companies"},
                        {"key": "D", "text": "to testify that training is only feasible approach to solve language problem"}
                    ],
                    "answer": "C",
                    "explanation": "The passage evaluates language policies, translation outsourcing and internal corporate training.",
                    "reference": "Paragraphs A-F"
                }
            ]
        }
    ]

    test10_dict = {
        "id": "academic-reading-16",
        "module": "reading",
        "variant": "academic",
        "title": "Academic Reading Practice Test 16",
        "shortTitle": "Practice Test 16",
        "durationMinutes": 60,
        "totalQuestions": 40,
        "sortOrder": 16,
        "license": "Original work written for this project. All rights reserved by the site owner.",
        "passages": [
            {
                "passageNumber": 1,
                "title": "Koalas",
                "subtitle": "Ecology, physiological digestion and conservation controversies in Australian marsupials",
                "paragraphs": p1_paras,
                "groups": p1_groups
            },
            {
                "passageNumber": 2,
                "title": "Antarctica: In from the Cold?",
                "subtitle": "Polar ice dynamics, katabatic winds and atmospheric influences on global climate",
                "paragraphs": p2_paras,
                "groups": p2_groups
            },
            {
                "passageNumber": 3,
                "title": "Language Strategy in Multinational Companies",
                "subtitle": "Evaluating linguistic barriers, outsourced translation and corporate communication policies",
                "paragraphs": p3_paras,
                "groups": p3_groups
            }
        ]
    }
    save_and_validate_test(test10_dict)

if __name__ == "__main__":
    build_test_16()
