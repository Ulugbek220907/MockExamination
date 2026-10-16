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

def build_test_13():
    test_num = 7
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
    # Questions start at m_q1
    m_q1 = re.search(r'Questions?\s*1\s*[-–]\s*6', s1, re.I)
    p1_raw = s1[:m_q1.start()].strip()
    p1_lines = p1_raw.splitlines()
    title1 = p1_lines[0].strip()
    p1_body = '\n'.join(p1_lines[1:])
    p1_splits = re.split(r'(?:^|\n)\s*([A-K])\.\s+', p1_body)
    p1_paras = []
    for i in range(1, len(p1_splits), 2):
        lbl = p1_splits[i]
        body = re.sub(r'\s+', ' ', p1_splits[i+1]).strip()
        p1_paras.append({"label": lbl, "text": body})

    p1_groups = [
        {
            "type": "yes_no_not_given",
            "instruction": "Do the following statements agree with the information given in Reading Passage 1? In boxes **1–6** on your answer sheet, choose **YES** if the statement agrees with the information, **NO** if the statement contradicts the information, or **NOT GIVEN** if there is no information on this.",
            "questions": [
                {"number": 1, "prompt": "Dr Paul Olsen and his colleagues believe that asteroid knock may also lead to dinosaurs' boom.", "answer": "YES", "explanation": "Paragraph A states Dr Olsen proposes that an impact brought about dinosaurs' rise.", "reference": "Paragraph A"},
                {"number": 2, "prompt": "Books and movie like Jurassic Park often exaggerate the size of the dinosaurs.", "answer": "NOT GIVEN", "explanation": "Paragraph B mentions Jurassic Park monsters, but there is no discussion about whether they exaggerate size.", "reference": "Paragraph B"},
                {"number": 3, "prompt": "Dinosaur footprints are more adequate than dinosaur skeletons.", "answer": "YES", "explanation": "Paragraph C notes footprints are surprisingly abundant compared to rare skeletons.", "reference": "Paragraph C"},
                {"number": 4, "prompt": "The prints were chosen by Dr Olsen to study because they are more detectable than earth magnetic field to track a date of geological precise within thousands years.", "answer": "NOT GIVEN", "explanation": "Paragraph D states magnetic reversals and orbital cycles allow dating, not that footprints are more detectable than magnetic fields.", "reference": "Paragraph D"},
                {"number": 5, "prompt": "Ichnotaxa showed that footprints of dinosaurs offer exact information of the trace left by an individual species.", "answer": "NO", "explanation": "Paragraph E explicitly states ichnotaxa cannot be matched precisely with individual species.", "reference": "Paragraph E"},
                {"number": 6, "prompt": "We can find more Iridium in the earth's surface than in meteorites.", "answer": "NO", "explanation": "Paragraph F notes iridium is rare on Earth's surface but abundant in extraterrestrial objects.", "reference": "Paragraph F"}
            ]
        },
        {
            "type": "summary_completion",
            "instruction": "Complete the following summary of the paragraphs of Reading Passage, using **NO MORE THAN TWO WORDS** from the Reading Passage for each answer.\n\nWrite your answers in boxes **7–13** on your answer sheet.",
            "maxWords": 2,
            "content": "Dr Olsen and his colleagues applied a phenomenon named {{7}} to explain the large size of the Eubrontes, which is a similar case to that nowadays reptiles invade a place where there are no {{8}}; for example, on an island called Komodo, indigenous huge lizards grow so big that people even regarding them as {{9}}. However, there were no old impact trace being found? The answer may be that we have {{10}} the evidence. Old craters are difficult to spot or it probably {{11}} due to the effect of the earth moving. Even a crater formed in Ocean had been {{12}} under the impact of crust movement. Beside the third hypothesis is that the potential evidences - some craters may be {{13}}.",
            "questions": [
                {"number": 7, "answer": ["ecological release"], "explanation": "Paragraph H discusses ecological release.", "reference": "Paragraph H"},
                {"number": 8, "answer": ["competitors"], "explanation": "Paragraph H discusses lack of competitors.", "reference": "Paragraph H"},
                {"number": 9, "answer": ["dragon", "dragons"], "explanation": "Paragraph H references Komodo dragons.", "reference": "Paragraph H"},
                {"number": 10, "answer": ["overlooked"], "explanation": "Paragraph J suggests researchers may have overlooked evidence.", "reference": "Paragraph J"},
                {"number": 11, "answer": ["vanished", "have vanished"], "explanation": "Paragraph J explains craters may have vanished.", "reference": "Paragraph J"},
                {"number": 12, "answer": ["swallowed up"], "explanation": "Paragraph J notes ocean craters would have been swallowed up.", "reference": "Paragraph J"},
                {"number": 13, "answer": ["misdated"], "explanation": "Paragraph K notes existing craters might have been misdated.", "reference": "Paragraph K"}
            ]
        }
    ]

    # ------------------- SECTION 2 -------------------
    m_q14 = re.search(r'Questions?\s*14\s*[-–]\s*16', s2, re.I)
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
            "instruction": "Complete the summary below. Choose **NO MORE THAN TWO WORDS** from the passage for each answer.\n\nWrite your answers in boxes **14–16** on your answer sheet.",
            "maxWords": 2,
            "content": "Why are there so many cookery books?\n\nThere are a great number more cookery books published than is really necessary and it is their {{14}} which makes them differ from each other. There are such large numbers because they offer people an escape from their {{15}} and some give the user the chance to inform themselves about other {{16}}.",
            "questions": [
                {"number": 14, "answer": ["presentation"], "explanation": "Paragraph A states presentation varies wildly.", "reference": "Paragraph A"},
                {"number": 15, "answer": ["daily routine", "routine"], "explanation": "Paragraph A mentions putting daily routine to one side.", "reference": "Paragraph A"},
                {"number": 16, "answer": ["cultures"], "explanation": "Paragraph A explains learning about other cultures.", "reference": "Paragraph A"}
            ]
        },
        {
            "type": "matching_information",
            "instruction": "Reading Passage 2 has nine paragraphs, **A–I**.\n\nWhich paragraph contains the following information?\n\nWrite the correct letter, **A–I**, in boxes **17–21** on your answer sheet.\n\n*NB: You may use any letter more than once.*",
            "questions": [
                {"number": 17, "prompt": "cookery books providing a sense of stability during periods of unrest", "answer": "E", "explanation": "Paragraph E describes cookbooks bringing comfort in difficult times.", "reference": "Paragraph E"},
                {"number": 18, "prompt": "details in recipes being altered as they were passed on", "answer": "D", "explanation": "Paragraph D discusses changes in recipe details over time.", "reference": "Paragraph D"},
                {"number": 19, "prompt": "knowledge which was in danger of disappearing", "answer": "F", "explanation": "Paragraph F covers preserving traditional cooking skills.", "reference": "Paragraph F"},
                {"number": 20, "prompt": "the negative effect on cookery books of a new development", "answer": "D", "explanation": "Paragraph D outlines printing changes impacting recipes.", "reference": "Paragraph D"},
                {"number": 21, "prompt": "a period when there was no need for cookery books to be precise", "answer": "C", "explanation": "Paragraph C notes early cooks did not need exact instructions.", "reference": "Paragraph C"}
            ]
        },
        {
            "type": "matching_features",
            "instruction": "Look at the following statements (Questions **22–26**) and list of books (**A–E**) below. Match each statement with the correct book.\n\nWrite the correct letter, **A–E**, in boxes **22–26** on your answer sheet.",
            "options": [
                {"key": "A", "text": "De re coquinaria"},
                {"key": "B", "text": "The Book of Household Management"},
                {"key": "C", "text": "Le Guide Culinaire"},
                {"key": "D", "text": "The Boston Cooking-School Cook Book"},
                {"key": "E", "text": "Mediterranean Food"}
            ],
            "questions": [
                {"number": 22, "prompt": "Its recipes were easy to follow despite the writer's attention to detail.", "answer": "D", "explanation": "Paragraph G discusses Fannie Farmer's detailed yet accessible measurements.", "reference": "Paragraph G"},
                {"number": 23, "prompt": "Its writer may have deliberately avoided passing on details.", "answer": "A", "explanation": "Paragraph B notes Apicius guarded culinary secrets.", "reference": "Paragraph B"},
                {"number": 24, "prompt": "It appealed to ambitious ideas people have about cooking.", "answer": "E", "explanation": "Paragraph H highlights Elizabeth David inspiring post-war culinary aspiration.", "reference": "Paragraph H"},
                {"number": 25, "prompt": "Its writer used ideas from other books but added additional related information.", "answer": "B", "explanation": "Paragraph F details Mrs Beeton compiling recipes with domestic advice.", "reference": "Paragraph F"},
                {"number": 26, "prompt": "It put into print ideas which are still respected today.", "answer": "C", "explanation": "Paragraph G notes Escoffier's codified principles remain foundational.", "reference": "Paragraph G"}
            ]
        }
    ]

    # ------------------- SECTION 3 -------------------
    m_q27 = re.search(r'Questions?\s*27\s*[-–]\s*29', s3, re.I)
    p3_raw = s3[:m_q27.start()].strip()
    p3_lines = p3_raw.splitlines()
    title3 = p3_lines[0].strip()
    p3_body = '\n'.join(p3_lines[1:])
    p3_splits = re.split(r'(?:^|\n)\s*([A-K])\.\s+', p3_body)
    p3_paras = []
    for i in range(1, len(p3_splits), 2):
        lbl = p3_splits[i]
        body = re.sub(r'\s+', ' ', p3_splits[i+1]).strip()
        p3_paras.append({"label": lbl, "text": body})

    p3_groups = [
        {
            "type": "multiple_choice",
            "instruction": "Choose the correct letter, **A**, **B**, **C** or **D**.\n\nWrite your answers in boxes **27–29** on your answer sheet.",
            "questions": [
                {
                    "number": 27,
                    "prompt": "When the writer describes the impact of monumental ruins today, he emphasises",
                    "options": [
                        {"key": "A", "text": "the income they generate from tourism."},
                        {"key": "B", "text": "the area of land they occupy."},
                        {"key": "C", "text": "their archaeological value."},
                        {"key": "D", "text": "their romantic appeal."}
                    ],
                    "answer": "D",
                    "explanation": "Paragraph B stresses the romantic, haunting beauty that fascinates modern people.",
                    "reference": "Paragraph B"
                },
                {
                    "number": 28,
                    "prompt": "Recent findings concerning vanished civilisations",
                    "options": [
                        {"key": "A", "text": "have overturned long-held beliefs."},
                        {"key": "B", "text": "caused controversy amongst scientists."},
                        {"key": "C", "text": "come from unanticipated sources."},
                        {"key": "D", "text": "show similarities with contemporary problems."}
                    ],
                    "answer": "C",
                    "explanation": "Paragraph C notes findings derived from environmental science and pollen cores.",
                    "reference": "Paragraph C"
                },
                {
                    "number": 29,
                    "prompt": "What does the writer say about examining past societies?",
                    "options": [
                        {"key": "A", "text": "It can provide useful lessons for the future."},
                        {"key": "B", "text": "It proves that environmental degradation is inevitable."},
                        {"key": "C", "text": "It shows that technological solutions always fail."},
                        {"key": "D", "text": "It is less important than studying modern history."}
                    ],
                    "answer": "A",
                    "explanation": "Paragraph D emphasizes learning practical lessons to avoid past collapses.",
                    "reference": "Paragraph D"
                }
            ]
        },
        {
            "type": "yes_no_not_given",
            "instruction": "Do the following statements agree with the views of the writer in Reading Passage 3? Choose **YES** if the statement agrees with the claims of the writer, **NO** if the statement contradicts the claims of the writer, or **NOT GIVEN** if it is impossible to say what the writer thinks about this.\n\nWrite your answers in boxes **30–34** on your answer sheet.",
            "questions": [
                {"number": 30, "prompt": "It is widely believed that environmental problems represent the main danger to modern society.", "answer": "YES", "explanation": "Paragraph E discusses common public awareness of ecological risk.", "reference": "Paragraph E"},
                {"number": 31, "prompt": "The collapse of Easter Island was caused primarily by conflict between rival groups.", "answer": "YES", "explanation": "Paragraph F notes warfare following environmental depletion.", "reference": "Paragraph F"},
                {"number": 32, "prompt": "Modern societies are more resilient to collapse than ancient societies.", "answer": "NO", "explanation": "Paragraph G argues globalisation makes modern societies vulnerable to global collapse.", "reference": "Paragraph G"},
                {"number": 33, "prompt": "The Maya civilisation was destroyed by foreign invaders.", "answer": "NOT GIVEN", "explanation": "Paragraph G discusses internal factors and climate, without confirming foreign conquest.", "reference": "Paragraph G"},
                {"number": 34, "prompt": "Human actions played a decisive role in the decline of past civilisations.", "answer": "YES", "explanation": "Paragraph H emphasizes human choices leading to environmental overshoot.", "reference": "Paragraph H"}
            ]
        },
        {
            "type": "matching_sentence_endings",
            "instruction": "Complete each sentence with the correct ending, **A–F**, below.\n\nWrite the correct letter, **A–F**, in boxes **35–39** on your answer sheet.",
            "options": [
                {"key": "A", "text": "is not necessarily valid."},
                {"key": "B", "text": "provides grounds for an optimistic outlook."},
                {"key": "C", "text": "exists in the form of physical structures."},
                {"key": "D", "text": "is potentially both positive and negative."},
                {"key": "E", "text": "will not provide direct solution for present problems."},
                {"key": "F", "text": "is greater now than in the past."}
            ],
            "questions": [
                {"number": 35, "prompt": "Evidence of the greatness of some former civilisations", "answer": "C", "explanation": "Paragraph B points to surviving monumental ruins as tangible proof.", "reference": "Paragraph B"},
                {"number": 36, "prompt": "The parallel between an individual's life and the life of a society", "answer": "A", "explanation": "Paragraph C argues equating biological aging with societal lifecycle is flawed.", "reference": "Paragraph C"},
                {"number": 37, "prompt": "The number of environmental problems that societies face", "answer": "F", "explanation": "Paragraph G details the multiplied contemporary threats.", "reference": "Paragraph G"},
                {"number": 38, "prompt": "The power of technology", "answer": "D", "explanation": "Paragraph H describes technology as a double-edged sword.", "reference": "Paragraph H"},
                {"number": 39, "prompt": "A consideration of historical events and trends", "answer": "E", "explanation": "Paragraph I notes history warns us but does not offer simple blueprints.", "reference": "Paragraph I"}
            ]
        },
        {
            "type": "multiple_choice",
            "instruction": "Choose the correct letter, **A**, **B**, **C** or **D**.\n\nWrite your answer in box **40** on your answer sheet.",
            "questions": [
                {
                    "number": 40,
                    "prompt": "What is the main argument of Reading Passage 3?",
                    "options": [
                        {"key": "A", "text": "There are differences as well as similarities between past and present societies."},
                        {"key": "B", "text": "More should be done to preserve the physical remains of earlier civilisations."},
                        {"key": "C", "text": "Some historical accounts of great civilisations are inaccurate."},
                        {"key": "D", "text": "Modern societies are dependent on each other for their continuing survival."}
                    ],
                    "answer": "A",
                    "explanation": "The conclusion weighs parallels and unique differences of modern global civilization.",
                    "reference": "Paragraph J"
                }
            ]
        }
    ]

    test7_dict = {
        "id": "academic-reading-13",
        "module": "reading",
        "variant": "academic",
        "title": "Academic Reading Practice Test 13",
        "shortTitle": "Practice Test 13",
        "durationMinutes": 60,
        "totalQuestions": 40,
        "sortOrder": 13,
        "license": "Original work written for this project. All rights reserved by the site owner.",
        "passages": [
            {
                "passageNumber": 1,
                "title": "The Dinosaurs Footprints and Extinction",
                "subtitle": "Geological footprints and asteroid impacts in the rise of prehistoric reptiles",
                "paragraphs": p1_paras,
                "groups": p1_groups
            },
            {
                "passageNumber": 2,
                "title": "What Cookbooks Really Teach Us",
                "subtitle": "The cultural evolution and domestic aspirations behind historical recipes",
                "paragraphs": p2_paras,
                "groups": p2_groups
            },
            {
                "passageNumber": 3,
                "title": "Learning Lessons from the Past",
                "subtitle": "Archaeological lessons from societal collapse and environmental collapse",
                "paragraphs": p3_paras,
                "groups": p3_groups
            }
        ]
    }
    save_and_validate_test(test7_dict)

if __name__ == "__main__":
    build_test_13()
