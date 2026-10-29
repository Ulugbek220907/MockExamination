#!/usr/bin/env python3
"""
Build data/bank.json, the pool of daily posts, and write it next to the service.

    python scripts/build_bank.py            # from the repository root's content/ (run it inside the repo)

The service itself reads only data/bank.json, so it can be deployed from this folder alone. This script
adds what the TestDay tests already hold (Speaking Part 2 cue cards and Writing Task 2 questions, which
TestDay wrote itself) to the vocabulary, tips and promotional posts written below. Add your own items to
the lists, run the script, and commit the new bank.json.
"""

import glob
import json
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "data", "bank.json")
CONTENT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "content")

# word, part of speech, meaning, example, a phrase that goes with it, where to use it
VOCAB = [
    ("mitigate", "verb", "make something less serious or harmful", "Governments should act to mitigate the effects of climate change.", "mitigate the impact of", "Writing Task 2"),
    ("substantial", "adjective", "large in amount or importance", "There has been a substantial rise in the number of people working from home.", "a substantial increase", "Writing Task 1 and 2"),
    ("undermine", "verb", "weaken something little by little", "Constant criticism can undermine a child's confidence.", "undermine confidence", "Writing Task 2"),
    ("fluctuate", "verb", "go up and down in an irregular way", "House prices fluctuated sharply over the decade.", "fluctuate between X and Y", "Writing Task 1"),
    ("curb", "verb", "control or limit something harmful", "Higher taxes could curb the consumption of sugary drinks.", "curb spending", "Writing Task 2"),
    ("detrimental", "adjective", "causing harm", "Too much screen time can be detrimental to children's sleep.", "detrimental to health", "Writing Task 2"),
    ("plausible", "adjective", "seeming reasonable or likely to be true", "It is plausible that remote work will stay popular.", "a plausible explanation", "Speaking Part 3"),
    ("inevitable", "adjective", "certain to happen; impossible to avoid", "Some job losses are inevitable as technology advances.", "an inevitable consequence", "Writing Task 2"),
    ("tackle", "verb", "try to deal with a problem", "Cities must tackle traffic congestion before it gets worse.", "tackle a problem", "Writing Task 2"),
    ("incentive", "noun", "something that encourages people to act", "Tax incentives encourage firms to hire young graduates.", "offer an incentive", "Writing Task 2"),
    ("sustainable", "adjective", "able to continue without harming the environment or running out", "We need more sustainable sources of energy.", "sustainable development", "Writing Task 2"),
    ("widespread", "adjective", "found in many places or among many people", "Mobile phone use is now widespread among teenagers.", "widespread concern", "Writing Task 2"),
    ("compelling", "adjective", "very convincing; hard to resist", "There is compelling evidence that exercise improves memory.", "compelling evidence", "Speaking Part 3"),
    ("comprehensive", "adjective", "including everything that is needed", "The report gives a comprehensive overview of the market.", "a comprehensive survey", "Writing Task 1"),
    ("abundant", "adjective", "existing in large quantities", "Solar energy is abundant in desert regions.", "abundant supplies", "Writing Task 2"),
    ("scarce", "adjective", "not enough of something; hard to find", "Fresh water is becoming scarce in many regions.", "scarce resources", "Writing Task 2"),
    ("diminish", "verb", "become smaller or less important", "The value of old computers diminishes quickly.", "diminish in importance", "Writing Task 1 and 2"),
    ("enhance", "verb", "improve the quality of something", "Music can enhance concentration while studying.", "enhance performance", "Writing Task 2"),
    ("hinder", "verb", "make it harder for something to happen", "Poor transport links hinder economic growth.", "hinder progress", "Writing Task 2"),
    ("vulnerable", "adjective", "easy to harm or hurt", "Elderly people are especially vulnerable to heat waves.", "vulnerable to", "Writing Task 2"),
    ("reluctant", "adjective", "unwilling and hesitating", "Many teenagers are reluctant to speak in class.", "reluctant to admit", "Speaking Part 1 and 3"),
    ("considerable", "adjective", "fairly large or important", "Smartphones save people a considerable amount of time.", "a considerable amount of", "Writing Task 1 and 2"),
    ("deteriorate", "verb", "become worse", "Air quality has deteriorated in many large cities.", "deteriorate rapidly", "Writing Task 1 and 2"),
    ("contemporary", "adjective", "belonging to the present time", "Contemporary art attracts a younger audience.", "contemporary society", "Speaking and Writing"),
    ("thrive", "verb", "grow and succeed", "Small businesses thrive when regulations are simple.", "thrive on", "Writing Task 2"),
    ("deprive", "verb", "prevent someone from having something", "Long working hours deprive parents of time with their children.", "deprive someone of", "Writing Task 2"),
    ("foster", "verb", "help something to develop", "Schools should foster creativity as well as knowledge.", "foster a sense of", "Writing Task 2"),
    ("alleviate", "verb", "make a problem or pain less severe", "New bus lanes could alleviate traffic congestion.", "alleviate poverty", "Writing Task 2"),
    ("prevalent", "adjective", "common at a particular time or place", "Obesity is increasingly prevalent among children.", "become more prevalent", "Writing Task 2"),
    ("disparity", "noun", "a big difference between things that should be equal", "There is a growing disparity between rich and poor.", "a disparity in income", "Writing Task 1 and 2"),
    ("allocate", "verb", "give money or time for a particular purpose", "Governments should allocate more money to public transport.", "allocate resources", "Writing Task 2"),
    ("outweigh", "verb", "be greater or more important than something else", "For most students, the benefits of studying abroad outweigh the costs.", "the advantages outweigh the disadvantages", "Writing Task 2"),
    ("contribute to", "phrasal verb", "help to cause something", "A poor diet contributes to many health problems.", "contribute to the problem", "Writing Task 2"),
    ("resilient", "adjective", "able to recover quickly after difficulty", "Resilient communities recover faster after floods.", "a resilient economy", "Speaking Part 3"),
    ("mundane", "adjective", "ordinary and rather boring", "Robots could do the mundane tasks in offices.", "mundane tasks", "Speaking Part 1 and 3"),
    ("versatile", "adjective", "able to be used in many ways", "Bamboo is a versatile building material.", "a versatile tool", "Speaking Part 1 and 2"),
    ("inhabitants", "noun", "the people who live in a place", "The city has two million inhabitants.", "local inhabitants", "Writing Task 1"),
    ("rely on", "phrasal verb", "depend on someone or something", "Many farmers rely on rainfall rather than irrigation.", "rely heavily on", "Writing and Speaking"),
    ("phenomenon", "noun", "something that exists and can be seen or studied", "Remote working is a relatively new phenomenon.", "a global phenomenon", "Writing Task 2"),
    ("crucial", "adjective", "extremely important", "Sleep is crucial for memory.", "play a crucial role", "Writing Task 2"),
    ("gradual", "adjective", "happening slowly, a little at a time", "The chart shows a gradual decline in sales.", "a gradual increase", "Writing Task 1"),
    ("surge", "noun", "a sudden large increase", "There was a surge in online shopping in 2020.", "a surge in demand", "Writing Task 1"),
    ("plummet", "verb", "fall very quickly and by a large amount", "Prices plummeted in the second year.", "plummet to", "Writing Task 1"),
    ("plateau", "verb", "stop rising or falling and stay at the same level", "Sales plateaued at around 200 units a month.", "plateau at", "Writing Task 1"),
    ("proportion", "noun", "a part of a whole", "A large proportion of students study abroad.", "a significant proportion of", "Writing Task 1"),
    ("approximately", "adverb", "about; not exactly", "Approximately 40 per cent of the visitors were under 25.", "approximately half", "Writing Task 1"),
    ("peak", "verb", "reach the highest point", "Sales peaked in July at 12,000 units.", "peak at", "Writing Task 1"),
    ("revenue", "noun", "the money a company or government receives", "Tourism brings in a large share of the country's revenue.", "tax revenue", "Writing Task 1 and 2"),
    ("accommodate", "verb", "have enough space for; adapt to", "The new stadium can accommodate 50,000 people.", "accommodate a growing population", "Writing Task 1 and 2"),
    ("negligible", "adjective", "so small that it is not important", "The cost of the change was negligible.", "a negligible amount", "Writing Task 1"),
    ("inadequate", "adjective", "not enough, or not good enough", "Public transport in rural areas is often inadequate.", "inadequate facilities", "Writing Task 2"),
    ("retain", "verb", "keep something", "Companies want to retain their most skilled staff.", "retain employees", "Writing Task 2"),
    ("pursue", "verb", "try to achieve something over a period of time", "She decided to pursue a career in medicine.", "pursue a career", "Speaking Part 1 and 2"),
    ("overwhelming", "adjective", "very great in amount or effect", "An overwhelming majority of people support the plan.", "an overwhelming majority", "Writing Task 1 and 2"),
    ("hectic", "adjective", "very busy and full of activity", "My week at university is usually quite hectic.", "a hectic schedule", "Speaking Part 1"),
    ("laid-back", "adjective", "relaxed and not easily worried", "My brother is very laid-back about exams.", "a laid-back attitude", "Speaking Part 1 and 2"),
    ("keen on", "phrase", "interested in something and enjoying it", "I've always been keen on photography.", "be keen on", "Speaking Part 1"),
    ("get the hang of", "phrase", "learn how to do something", "It took me a month to get the hang of cooking rice properly.", "get the hang of it", "Speaking Part 2"),
    ("come across", "phrasal verb", "find or meet by chance", "I came across an old photo of my grandfather last week.", "come across as friendly", "Speaking Part 2"),
    ("tend to", "phrase", "usually do something; often be a certain way", "People in my city tend to eat dinner quite late.", "tend to prefer", "Speaking Part 1 and 3"),
    ("a blessing in disguise", "idiom", "something that seems bad at first but turns out well", "Missing the bus was a blessing in disguise because I met my best friend.", "turn out to be a blessing in disguise", "Speaking Part 2"),
    ("at the end of the day", "phrase", "when everything is considered", "At the end of the day, practice matters more than talent.", "at the end of the day, it depends", "Speaking Part 3"),
]

# module, title, body
TIPS = [
    ("Listening", "Use the preview time", "Before each part starts, read the questions and underline the key words. Decide what kind of answer you need: a number, a name, a place."),
    ("Listening", "Answers come in order", "In every section the answers are heard in the same order as the questions. If you miss one, let it go and listen for the next."),
    ("Listening", "Listen for corrections", "Speakers often change their minds: \"Tuesday, no, sorry, Thursday.\" The final version is the answer, not the first one you hear."),
    ("Listening", "Spelling counts", "A misspelled answer loses the mark. Both British and American spelling are accepted, but check names, plurals and endings."),
    ("Listening", "Respect the word limit", "If the instructions say NO MORE THAN TWO WORDS, a three-word answer scores zero. Check the limit on every question."),
    ("Listening", "Plurals and numbers", "Listen for the final -s. \"Book\" and \"books\" are different answers. Write numbers carefully: 13 and 30 sound alike."),
    ("Listening", "Find your starting point on a map", "On a map or plan question, find where you are and the compass points before the recording starts. Then follow the directions step by step."),
    ("Listening", "Beware of distractors", "The speaker may mention every option. Listen for the one that is not rejected, changed or corrected."),
    ("Reading", "Skim first, then scan", "Do not read every word. Skim the title and the first lines of each paragraph for the structure, then scan for key words from the question."),
    ("Reading", "True, False or Not Given", "False means the text says the opposite. Not Given means the text does not say. Use only the passage, never your own knowledge."),
    ("Reading", "Matching headings", "Read the first and last sentences of each paragraph. The heading is the main idea of the paragraph, not a detail from it."),
    ("Reading", "Never leave an answer blank", "There is no penalty for a wrong answer. Move on from a hard question, come back if you have time, and guess before you finish."),
    ("Reading", "Yes, No or Not Given", "These questions are about the writer's opinion or claims, not facts. Look for words such as \"believes\", \"argues\" and \"suggests\"."),
    ("Reading", "Look for synonyms", "The question rarely uses the exact words of the passage. Find the paraphrase: \"increase\" in the question may be \"rise\" in the text."),
    ("Reading", "Copy words exactly", "In gap-fill questions copy the word exactly as it appears in the text, check the word limit, and make sure the answer fits the grammar of the sentence."),
    ("Reading", "Watch your time", "You have 60 minutes for three passages, about 20 for each. Do not spend more than a minute on one question at first."),
    ("Writing", "Always write an overview", "In Task 1, one or two sentences about the main trends or the biggest differences is the key part of a good answer. Do not give opinions."),
    ("Writing", "Task 2 counts double", "Task 2 carries twice the marks of Task 1. Aim for about 20 minutes on Task 1 and 40 on Task 2."),
    ("Writing", "Answer every part of the question", "If the question asks for causes and solutions, write about both. Missing a part limits your score for task response."),
    ("Writing", "Plan for five minutes", "Before you write, choose your position and two main ideas, each with an example. A short plan makes the essay clearer and faster to write."),
    ("Writing", "One idea per paragraph", "Start each body paragraph with a topic sentence, explain it, then give an example. Do not mix two ideas in one paragraph."),
    ("Writing", "Do not memorise essays", "Examiners recognise memorised answers, and they can lower your score. Learn useful phrases instead and write about the actual question."),
    ("Writing", "Accuracy beats length", "A few complex sentences that are correct are better than many long sentences full of mistakes. Keep your grammar under control."),
    ("Writing", "Use linking words with care", "\"However\" and \"In addition\" are useful, but not at the start of every sentence. Make the ideas connect first, then add the link."),
    ("Writing", "Paraphrase the question", "In your introduction, do not copy the question. Change the key words and the structure, then state your position."),
    ("Writing", "Check your essay", "Keep two or three minutes at the end to check verb tenses, articles (a, an, the), plurals and spelling."),
    ("Speaking", "Extend your answers in Part 1", "Do not give one-word answers. Say your answer, give a reason, and add a short example: two or three sentences is about right."),
    ("Speaking", "Use your minute in Part 2", "Write key words, not sentences. Cover every point on the card and keep speaking until the examiner stops you after two minutes."),
    ("Speaking", "Develop your ideas in Part 3", "Give your opinion, explain why, add an example, and compare the past and the present or different groups of people."),
    ("Speaking", "It is fine to ask", "If you do not understand a question, ask the examiner to repeat it. It does not lower your score."),
    ("Speaking", "Do not memorise answers", "Examiners can tell when an answer is learned by heart. Speak naturally about your own life and ideas."),
    ("Speaking", "Fluency before perfection", "Correct yourself calmly and keep going. Phrases like \"Well, let me think\" give you a moment without a long silence."),
    ("Speaking", "Stress the important words", "Good pronunciation is not an accent. It is clear sounds, stressed key words and a natural pace that is neither rushed nor slow."),
    ("Speaking", "Paraphrase to show range", "If you cannot remember a word, explain it in other words. Using a range of vocabulary matters more than using rare words."),
]

PROMOS = [
    ("Five free full tests in every module", "Listening, Reading, Writing and Speaking: five full tests of each are free on TestDay. Listening, Reading and Writing need no sign-up."),
    ("Practise on a screen like test day", "Timer, question navigator, highlighting and notes: TestDay tests look and work like the computer-delivered IELTS."),
    ("Instant band estimates", "Finish a Listening or Reading test and see your band estimate, your answers and an explanation for every question straight away."),
    ("Listen as in the real test", "Four-part Listening tests with recordings you play once, just like the exam. Five of them are free."),
    ("Speak, record, listen back", "Take a full Speaking test with the examiner's questions played aloud, record your answers and listen back. The first five tests are free."),
    ("Writing practice with a timer", "Task 1 and Task 2 in one 60-minute test, with model answers to compare. Five Writing tests are free."),
]


def load(pattern):
    out = []
    for path in sorted(glob.glob(os.path.join(CONTENT, pattern))):
        with open(path, encoding="utf-8") as f:
            out.append(json.load(f))
    return out


def speaking_cards():
    cards = []
    for test in load("speaking/*.json"):
        for part in test.get("parts", []):
            card = part.get("cueCard")
            if card and card.get("topic") and card.get("points"):
                cards.append({"topic": card["topic"].strip(), "points": [p.strip() for p in card["points"]],
                              "explain": (card.get("explain") or "").strip(), "source": test["id"]})
    return cards


BOILERPLATE = re.compile(r"^(write about the following topic:|give reasons for your answer.*)$", re.I)


def writing_prompts():
    prompts = []
    for test in load("writing/*.json"):
        for task in test.get("tasks", []):
            if task.get("taskNumber") != 2:
                continue
            lines = [l.strip() for l in task["prompt"].splitlines() if l.strip() and not BOILERPLATE.match(l.strip())]
            if lines:
                prompts.append({"lines": lines, "type": task.get("essayType") or "", "source": test["id"]})
    return prompts


def shuffled(items, seed):
    items = list(items)
    random.Random(seed).shuffle(items)
    return items


def main():
    bank = {
        "vocab": [{"id": f"v{i:03d}", "word": w, "pos": pos, "meaning": m, "example": ex, "phrase": ph, "use": use}
                  for i, (w, pos, m, ex, ph, use) in enumerate(shuffled(VOCAB, 11), 1)],
        "tips": [{"id": f"t{i:03d}", "module": mod, "title": title, "body": body}
                 for i, (mod, title, body) in enumerate(shuffled(TIPS, 5), 1)],
        "speaking": [dict(id=f"s{i:03d}", **c) for i, c in enumerate(shuffled(speaking_cards(), 3), 1)],
        "writing": [dict(id=f"w{i:03d}", **p) for i, p in enumerate(shuffled(writing_prompts(), 9), 1)],
        "promo": [{"id": f"p{i:03d}", "title": t, "body": b} for i, (t, b) in enumerate(PROMOS, 1)],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print({k: len(v) for k, v in bank.items()}, "->", OUT)


if __name__ == "__main__":
    main()
