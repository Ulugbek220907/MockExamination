#!/usr/bin/env python3
"""
Patch and refine data/book_34_tests.json:
- Fix defective/merged options in Test 22 (Q12-13) and Test 39 (Q20-21, Q22-23).
- Correct answer keys for Test 27 (Q10-13: ['B', 'C', 'E', 'F']) and Test 39 (Q20-21: ['B', 'D'], Q22-23: ['B', 'D']).
- Add authentic explanations and references for choose_multiple questions in Tests 21, 22, 24, 27, 31, 33, 37, 39.
- Clean OCR artifacts and watermark remnants from passages and prompts.
- Re-export data/book_34_tests.json.
"""

import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "book_34_tests.json")


def clean_text_replacements(text):
    if not isinstance(text, str):
        return text
    replacements = [
        ("route m ạp", "route map"),
        ("Daphne Ma ịor", "Daphne Major"),
        ("the ốothic cathedral", "the Gothic cathedral"),
        ("No w ừes", "No wires"),
        ("two c ữcuits", "two circuits"),
        ("one that ỈB always", "one that is always"),
        ("statement ừ false", "statement is false"),
        ("models of the ữ own", "models of their own"),
        ("life saver ỉn the", "life saver in the"),
        ("flask ỈS fitted", "flask is fitted"),
        ("th ứd faster", "third faster"),
        ("information ừ not given", "information is not given"),
        ("an ầttp://w«bo.com/iclti9 idea", "an idea"),
        ("recalling\ngame Ị", "recalling game"),
        ("recalling game Ị", "recalling game"),
        ("in the ữ descriptions", "in their descriptions"),
        ("Blockbusters requ ừe", "Blockbusters require"),
        ("given ỉn Reading", "given in Reading"),
        ("who cha ừs", "who chairs"),
        ("meltin ị Arctic ice", "melting Arctic ice"),
        ("skills requ ừed", "skills required"),
        ("idea of a b ừd", "idea of a bird"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def deep_clean_strings(obj):
    if isinstance(obj, dict):
        return {k: deep_clean_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deep_clean_strings(v) for v in obj]
    if isinstance(obj, str):
        return clean_text_replacements(obj)
    return obj


def patch_tests():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        tests = json.load(f)

    # Clean OCR strings throughout dataset
    tests = deep_clean_strings(tests)

    # 1. Test 21 (index 14) Passage 2 Q23-24
    t21 = tests[14]
    p2 = t21["passages"][1]
    for g in p2["groups"]:
        if g["type"] == "choose_multiple":
            g["prompt"] = "Which TWO of the following statements are true about the Paleobiology Database according to the passage?"
            g["explanation"] = "Paragraph A states that the database 'aspires to be an online repository of information about every fossil ever dug up' (D). Paragraph B notes that while the project attracts harsh criticism from some experts who believe it is flawed, supporters see great value in it, showing it intrigues both positive and negative opinions (B)."
            g["reference"] = "Paragraph A and Paragraph B"
            for q in g["questions"]:
                if q["number"] == 23:
                    q["explanation"] = "Paragraph B notes that while the project attracts harsh criticism from some experts who believe it is flawed, supporters see value in it, intriguing both positive and negative opinions."
                    q["reference"] = "Paragraph B"
                elif q["number"] == 24:
                    q["explanation"] = "Paragraph A states that the database 'aspires to be an online repository of information about every fossil ever dug up' (aims to embrace all fossil information globally)."
                    q["reference"] = "Paragraph A"

    # 2. Test 22 (index 15) Passage 1 Q12-13
    t22 = tests[15]
    p1 = t22["passages"][0]
    for g in p1["groups"]:
        if g["type"] == "choose_multiple":
            g["instruction"] = "Choose TWO letters, A–E.\nWrite your answers in boxes 12–13 on your answer sheet."
            g["prompt"] = "What TWO benefits will the new approach in the UK and Austria bring according to this passage?"
            g["options"] = [
                {"key": "A", "text": "We can prepare before flood comes"},
                {"key": "B", "text": "It may stop the flood involving the whole area"},
                {"key": "C", "text": "Decrease strong rainfalls around Alps simply by engineering constructions"},
                {"key": "D", "text": "Reserve water to protect downstream towns"},
                {"key": "E", "text": "Store tons of water in downstream area"},
            ]
            g["answer"] = ["B", "D"]
            g["explanation"] = "Paragraph D notes that while forecasts help cities prepare, a new engineering approach is needed to stop floods from involving the whole area (B). Paragraph E explains that restored flood plains store up to 10 million cubic metres of water and slow storm surges, reserving water to protect downstream towns (D)."
            g["reference"] = "Paragraph D and Paragraph E"
            for q in g["questions"]:
                if q["number"] == 12:
                    q["explanation"] = "Paragraph D states that forecasting may help cities prepare, but stopping floods requires a new engineering approach to prevent flooding across the whole area."
                    q["reference"] = "Paragraph D"
                elif q["number"] == 13:
                    q["explanation"] = "Paragraph E explains that restored flood plains can store up to 10 million cubic metres of water and slow storm surges, protecting and reserving water to safeguard downstream towns."
                    q["reference"] = "Paragraph E"

    # 3. Test 24 (index 17) Passage 2 Q14-17
    t24 = tests[17]
    p2 = t24["passages"][1]
    for g in p2["groups"]:
        if g["type"] == "choose_multiple":
            g["prompt"] = "Which FOUR of the following statements are true about the London Swaying Footbridge according to the passage?"
            g["explanation"] = "Paragraph B describes how the bridge began to sway slightly, and then the wobble intensified into unexpected sideway movement (D), which increased in frequency and amplitude (A). Paragraph C explains that this movement was sufficiently large for pedestrians to have difficulty walking and to stop to retain their balance (E), and the vibrations were easily detected and felt by pedestrians on the deck (G)."
            g["reference"] = "Paragraph B and Paragraph C"
            for q in g["questions"]:
                if q["number"] == 14:
                    q["explanation"] = "Paragraph B describes how the bridge began to sway slightly and then the wobble intensified, showing unexpected sideway movement (D) and increasing frequency/amplitude (A)."
                    q["reference"] = "Paragraph B"
                elif q["number"] == 15:
                    q["explanation"] = "Paragraph B notes the wobble intensified almost from one moment to the next as large crowds crossed, with significant lateral sway."
                    q["reference"] = "Paragraph B"
                elif q["number"] == 16:
                    q["explanation"] = "Paragraph C states that deck movement became sufficiently large for people to stop walking to retain their balance and hold onto handrails (difficulty in walking on the deck)."
                    q["reference"] = "Paragraph C"
                elif q["number"] == 17:
                    q["explanation"] = "Paragraph C notes that deck movement was noticeable and uncomfortable enough to raise public safety concerns, readily detected as vibration by pedestrians."
                    q["reference"] = "Paragraph C"

    # 4. Test 27 (index 20) Passage 1 Q10-13
    t27 = tests[20]
    p1 = t27["passages"][0]
    for g in p1["groups"]:
        if g["type"] == "choose_multiple":
            g["prompt"] = "Which of the following factors influence the difficulty of interpreting according to the passage?"
            g["answer"] = ["B", "C", "E", "F"]
            g["explanation"] = "Paragraph D mentions the presence of background noise (C), the awareness that major decisions depend upon precision and accuracy (F), and cultural differences between source and target language (E). Paragraph F notes research into how interpreting is affected by poor listening conditions and the speed at which the source language is spoken (B)."
            g["reference"] = "Paragraph D and Paragraph F"
            for q in g["questions"]:
                if q["number"] == 10:
                    q["explanation"] = "Paragraph F notes that successful interpreting is affected by the speed at which the source language is spoken."
                    q["reference"] = "Paragraph F"
                elif q["number"] == 11:
                    q["explanation"] = "Paragraph D highlights the presence of background noise as a complicating factor."
                    q["reference"] = "Paragraph D"
                elif q["number"] == 12:
                    q["explanation"] = "Paragraph D emphasizes cultural background considerations and differences between source and target language."
                    q["reference"] = "Paragraph D"
                elif q["number"] == 13:
                    q["explanation"] = "Paragraph D cites the awareness that major decisions may depend upon the accuracy and precision of the interpreter's work."
                    q["reference"] = "Paragraph D"

    # 5. Test 31 (index 24) Passage 1 Q11-13 & Passage 3 Q37-38, Q39-40
    t31 = tests[24]
    p1 = t31["passages"][0]
    for g in p1["groups"]:
        if g["type"] == "choose_multiple":
            g["prompt"] = "Why is the construction of Guedelon Castle taking a long time according to the passage?"
            g["answer"] = ["C", "E", "F"]
            g["explanation"] = "Paragraph C states that craftsmen are using only medieval tools and techniques (F) and workers adhere to standard modern work shifts of eight hours a day (C). Paragraph D notes that construction progress often has to give way to accommodate tourists and visitors (E)."
            g["reference"] = "Paragraph C and Paragraph D"
            for q in g["questions"]:
                if q["number"] == 11:
                    q["explanation"] = "Paragraph C explains that workers bang on chisels for eight hours a day, following modern regulated working hours."
                    q["reference"] = "Paragraph C"
                elif q["number"] == 12:
                    q["explanation"] = "Paragraph D states that construction progress has to give way to tourists and visitors."
                    q["reference"] = "Paragraph D"
                elif q["number"] == 13:
                    q["explanation"] = "Paragraph C states that building is slow because craftsmen use only medieval tools and techniques."
                    q["reference"] = "Paragraph C"

    p3 = t31["passages"][2]
    for g in p3["groups"]:
        if g["type"] == "choose_multiple":
            nums = [q["number"] for q in g["questions"]]
            if nums == [37, 38]:
                g["prompt"] = "Which tasks were used in the World Memory Championships according to the passage?"
                g["answer"] = ["A", "D"]
                g["explanation"] = "Paragraph A states that competitors were challenged to 'memorize rows of 40-digit numbers' (A: order for a large group of digits) and 'recall the names of 110 people after looking at their photographs' (D: match names with pictures and features)."
                g["reference"] = "Paragraph A"
                for q in g["questions"]:
                    if q["number"] == 37:
                        q["explanation"] = "Paragraph A states contestants had to memorize rows of 40-digit numbers (order for a large group of each digit)."
                        q["reference"] = "Paragraph A"
                    elif q["number"] == 38:
                        q["explanation"] = "Paragraph A states contestants were challenged to recall the names of 110 people after looking at their photographs (match name with pictures and features)."
                        q["reference"] = "Paragraph A"
            elif nums == [39, 40]:
                g["prompt"] = "What did brain scan studies reveal about the memory champions according to the passage?"
                g["answer"] = ["B", "E"]
                g["explanation"] = "Paragraph B explains that researchers analyzing brain scans found marked differences between the scan images of champions and control subjects when memorizing numbers (B). These scans revealed that champions activated regions like the right posterior hippocampus, known to be involved in visual and spatial memory (E)."
                g["reference"] = "Paragraph B"
                for q in g["questions"]:
                    if q["number"] == 39:
                        q["explanation"] = "Paragraph B states that brain scans revealed champions activating different brain regions from control subjects during numerical memorization."
                        q["reference"] = "Paragraph B"
                    elif q["number"] == 40:
                        q["explanation"] = "Paragraph B notes that activated regions in champions included the right posterior hippocampus, known to be involved in visual memory and spatial navigation."
                        q["reference"] = "Paragraph B"

    # 6. Test 33 (index 26) Passage 1 Q9-10 & Q11-13
    t33 = tests[26]
    p1 = t33["passages"][0]
    for g in p1["groups"]:
        if g["type"] == "choose_multiple":
            nums = [q["number"] for q in g["questions"]]
            if nums == [9, 10]:
                g["prompt"] = "What are two benefits of blockbuster exhibitions mentioned in the passage?"
                g["answer"] = ["A", "D"]
                g["explanation"] = "Paragraph E explains that blockbuster earnings provide museums with money to 'repair buildings that are in need of attention' (A). Paragraph G states that blockbuster crowds are good for the local economy, increasing business for local shops, hotels, restaurants, and transport (D)."
                g["reference"] = "Paragraph E and Paragraph G"
                for q in g["questions"]:
                    if q["number"] == 9:
                        q["explanation"] = "Paragraph E states that overseas museums use blockbuster earnings to update collections or repair buildings in need of attention."
                        q["reference"] = "Paragraph E"
                    elif q["number"] == 10:
                        q["explanation"] = "Paragraph G states that blockbuster crowds are good for the local economy, increasing employment for shops, hotels, restaurants, and retailers."
                        q["reference"] = "Paragraph G"
            elif nums == [11, 12, 13]:
                g["prompt"] = "What are three negative effects of blockbuster exhibitions mentioned in the passage?"
                g["answer"] = ["B", "C", "E"]
                g["explanation"] = "Paragraph F explains that mounting blockbusters requires large capital expenditure across all branches (E) and is exhausting for museum staff due to heavy workloads (B). Paragraph H concludes that institutions risk being seen as part of the entertainment and tourism industry rather than cultural icons (C)."
                g["reference"] = "Paragraph F and Paragraph H"
                for q in g["questions"]:
                    if q["number"] == 11:
                        q["explanation"] = "Paragraph F notes that creating, mounting, or hiring blockbusters is exhausting for staff (tired of workloads)."
                        q["reference"] = "Paragraph F"
                    elif q["number"] == 12:
                        q["explanation"] = "Paragraph H states that museums risk being treated as part of the entertainment and tourism industry rather than as cultural icons."
                        q["reference"] = "Paragraph H"
                    elif q["number"] == 13:
                        q["explanation"] = "Paragraph F highlights that blockbusters require large capital expenditure and draw on resources across all branches and specialists."
                        q["reference"] = "Paragraph F"

    # 7. Test 37 (index 30) Passage 1 Q12-13 & Passage 3 Q38-40
    t37 = tests[30]
    p1 = t37["passages"][0]
    for g in p1["groups"]:
        if g["type"] == "choose_multiple":
            g["prompt"] = "Which two statements are true about the school at Msekeni according to the passage?"
            g["answer"] = ["A", "C"]
            g["explanation"] = "Paragraph A states that due to classroom shortages, half the lessons take place in the shade of acacia trees (A). Paragraph E explains that the influx of new pupils was not accompanied by any increase in the number of teachers (C)."
            g["reference"] = "Paragraph A and Paragraph E"
            for q in g["questions"]:
                if q["number"] == 12:
                    q["explanation"] = "Paragraph A states that there are not enough classrooms, so half the lessons take place in the shade of acacia trees (taught in the open air)."
                    q["reference"] = "Paragraph A"
                elif q["number"] == 13:
                    q["explanation"] = "Paragraph E notes that the large influx of pupils was not accompanied by any increase in teachers (no new staff recruited)."
                    q["reference"] = "Paragraph E"

    p3 = t37["passages"][2]
    for g in p3["groups"]:
        if g["type"] == "choose_multiple":
            g["prompt"] = "What are three limitations of e-training mentioned in the passage?"
            g["answer"] = ["B", "C", "E"]
            g["explanation"] = "Paragraph D explicitly notes: bandwidth limitations still restrict multimedia presentation (B); e-training is ineffective for imparting corporate cultural values to new employees (C); and substantial person-hours (500 to 1,000 hours) are required to prepare and update online courses (E)."
            g["reference"] = "Paragraph D"
            for q in g["questions"]:
                if q["number"] == 38:
                    q["explanation"] = "Paragraph D states that bandwidth limitations are still an issue in presenting multimedia over the Internet."
                    q["reference"] = "Paragraph D"
                elif q["number"] == 39:
                    q["explanation"] = "Paragraph D notes that e-training is rather ineffective for imparting cultural values or conveying unique corporate culture to new employees."
                    q["reference"] = "Paragraph D"
                elif q["number"] == 40:
                    q["explanation"] = "Paragraph D highlights that 500 to 1,000 person-hours of preparation time are required to keep online courses current and useful."
                    q["reference"] = "Paragraph D"

    # 8. Test 39 (index 32) Passage 2 Q20-21 & Q22-23
    t39 = tests[32]
    p2 = t39["passages"][1]
    for g in p2["groups"]:
        if g["type"] == "choose_multiple":
            nums = [q["number"] for q in g["questions"]]
            if nums == [20, 21]:
                g["instruction"] = "Choose TWO letters, A–E.\nWrite your answers in boxes 20–21 on your answer sheet."
                g["prompt"] = "Which two statements are true concerning the removal of graffiti according to the passage?"
                g["options"] = [
                    {"key": "A", "text": "cocktail removal can be safer than water treatment"},
                    {"key": "B", "text": "small patch trial before applying large scale of removing"},
                    {"key": "C", "text": "Chemical treatments are the most expensive way of removing"},
                    {"key": "D", "text": "there are risks for both Chemical and mechanical method"},
                    {"key": "E", "text": "mechanical removals are much more applicable than Chemical treatments"},
                ]
                g["answer"] = ["B", "D"]
                g["explanation"] = "Paragraph D explains that both chemical and mechanical cleaning methods carry risks and hazards to health and substrates (D), and advises that small trial areas should be tested first if there is any doubt about surface resistance before applying large-scale treatment (B)."
                g["reference"] = "Paragraph D"
                for q in g["questions"]:
                    if q["number"] == 20:
                        q["explanation"] = "Paragraph D advises that if there is doubt regarding the substrate's ability to withstand treatment, small trial areas should be undertaken first."
                        q["reference"] = "Paragraph D"
                    elif q["number"] == 21:
                        q["explanation"] = "Paragraph D notes safety and physical risks associated with both chemical and mechanical cleaning treatments."
                        q["reference"] = "Paragraph D"
            elif nums == [22, 23]:
                g["instruction"] = "Choose TWO letters, A–E.\nWrite your answers in boxes 22–23 on your answer sheet."
                g["prompt"] = "Which TWO preventive measures against graffiti are mentioned effective in the passage?"
                g["options"] = [
                    {"key": "A", "text": "organise more anti graffiti movement in the city communities"},
                    {"key": "B", "text": "increase the police patrols on the street"},
                    {"key": "C", "text": "Build a new building with material repelling to water"},
                    {"key": "D", "text": "installing more visible security cameras"},
                    {"key": "E", "text": "Provide a whole new surface with chemical coat"},
                ]
                g["answer"] = ["B", "D"]
                g["explanation"] = "Paragraph E highlights that prominently placed surveillance cameras (closed-circuit television) have been shown to reduce anti-social behavior including graffiti (D), and security patrols also act as an effective deterrent against recurring attacks (B)."
                g["reference"] = "Paragraph E"
                for q in g["questions"]:
                    if q["number"] == 22:
                        q["explanation"] = "Paragraph E notes that security patrols act as a deterrent to prevent recurring graffiti attacks."
                        q["reference"] = "Paragraph E"
                    elif q["number"] == 23:
                        q["explanation"] = "Paragraph E states that prominently placed closed-circuit television cameras have been shown to reduce anti-social behaviour including graffiti."
                        q["reference"] = "Paragraph E"

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(tests, f, ensure_ascii=False, indent=2)

    print(f"✓ Patched and saved {DATA_PATH}")


if __name__ == "__main__":
    patch_tests()
