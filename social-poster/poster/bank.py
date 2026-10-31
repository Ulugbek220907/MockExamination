"""
What to post on a given day.

The post is a pure function of the date and data/bank.json: the same day always gives the same post, so a
restart never changes it and the admin page can show the next two weeks ahead. Each weekday has a kind of
post, and each kind walks through its pool in order, so nothing repeats until the pool is used up.
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK_PATH = os.path.join(BASE_DIR, "data", "bank.json")

# Monday to Sunday. Words are the most useful single thing for a candidate, so they come twice a week.
WEEK = ("vocab", "speaking", "tip", "writing", "vocab", "tip", "promo")
ANCHOR = date(2026, 1, 5)  # a Monday: the pools start here
POOLS = {"vocab": "vocab", "speaking": "speaking", "tip": "tips", "writing": "writing", "promo": "promo"}  # kind -> key in bank.json

KICKERS = {"vocab": "IELTS WORD OF THE DAY", "speaking": "IELTS SPEAKING PART 2", "writing": "IELTS WRITING TASK 2",
           "tip": "IELTS TIP", "promo": "TESTDAY"}
ESSAY_TYPES = {"opinion": "Opinion essay", "discussion": "Discussion essay", "problem_solution": "Problem and solution essay",
               "advantages_disadvantages": "Advantages and disadvantages essay", "two_part": "Two-part question"}
KIND_TAGS = {"vocab": ("IELTSvocabulary", "EnglishVocabulary"), "speaking": ("IELTSspeaking",), "writing": ("IELTSwriting",),
             "tip": ("IELTStips",), "promo": ("IELTSpractice",)}
CTA_LINES = ["Practise free on TestDay", "Five free full tests in every module", "testday.uz"]


@dataclass
class Scene:
    kicker: str
    headline: str
    lines: list = field(default_factory=list)
    seconds: float = 4.0
    dark: bool = False


@dataclass
class Post:
    day: str
    kind: str
    item_id: str
    kicker: str
    headline: str
    lines: list
    scenes: list
    text: str          # the post in a few paragraphs (captions are built from it)
    short: str         # the same in two or three short lines (Threads, 500 characters at most)
    title: str         # a short title (YouTube)
    hashtags: list

    def to_dict(self):
        return {"day": self.day, "kind": self.kind, "itemId": self.item_id, "kicker": self.kicker, "headline": self.headline,
                "lines": self.lines, "title": self.title, "text": self.text, "short": self.short, "hashtags": self.hashtags,
                "scenes": [{"kicker": s.kicker, "headline": s.headline, "lines": s.lines, "seconds": s.seconds, "dark": s.dark}
                           for s in self.scenes]}


_bank = None


def load_bank(path=BANK_PATH):
    global _bank
    if _bank is None or path != BANK_PATH:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if path != BANK_PATH:
            return data
        _bank = data
    return _bank


def kind_for(day):
    return WEEK[day.weekday()]


def occurrence(day, kind):
    """How many days before `day` (counting from ANCHOR) had this kind of post: the position in its pool."""
    days = (day - ANCHOR).days
    if days < 0:
        days = days % (7 * 1000)
    weeks, rest = divmod(days, 7)
    return weeks * WEEK.count(kind) + WEEK[:rest].count(kind)


def seconds_for(*texts, low=3.0, high=9.0):
    words = sum(len(t.split()) for t in texts)
    return round(min(high, max(low, 1.5 + words / 2.6)), 1)


def cta_scene():
    return Scene("TESTDAY", "Practise free", ["Five free full tests in every module", "testday.uz"], 3.5, dark=True)


def trim(text, limit):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1].rstrip(" ,;:.") + "…"


def hashtags(kind, cfg_extra=()):
    tags = ["IELTS", "IELTSpreparation", *KIND_TAGS[kind], "TestDay", *cfg_extra]
    seen, out = set(), []
    for tag in tags:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            out.append(tag)
    return out


# --------------------------------------------------------------------------- builders

def _vocab(day, item, extra):
    word, pos, meaning, example = item["word"], item["pos"], item["meaning"], item["example"]
    scenes = [
        Scene(KICKERS["vocab"], word, [pos], 3.5),
        Scene("MEANING", word, [meaning[0].upper() + meaning[1:]], seconds_for(meaning, low=4.0)),
        Scene("EXAMPLE", word, [f"“{example}”"], seconds_for(example, low=5.0)),
        Scene("USE IT", word, [f"Often: {item['phrase']}", f"Good for: {item['use']}"], 4.5),
        cta_scene(),
    ]
    text = (f"IELTS word of the day: {word} ({pos})\n\nMeaning: {meaning}.\nExample: {example}\n"
            f"Often used as: {item['phrase']}\nGood for: {item['use']}")
    short = f"IELTS word of the day: {word} ({pos}) — {meaning}.\n\n“{example}”"
    return Post(day.isoformat(), "vocab", item["id"], f"{KICKERS['vocab']} · {pos.upper()}", word, [meaning[0].upper() + meaning[1:] + ".", f"“{example}”"],
                scenes, text, short, f"IELTS word of the day: {word}", hashtags("vocab", extra))


def _tip(day, item, extra):
    module, title, body = item["module"], item["title"], item["body"]
    kicker = f"IELTS {module.upper()} TIP"
    sentences = re.split(r"(?<=[.!?])\s+", body)
    chunks, current = [], ""
    for sentence in sentences:  # one to three short scenes, each at most about 22 words
        if current and len((current + " " + sentence).split()) > 22:
            chunks.append(current)
            current = sentence
        else:
            current = (current + " " + sentence).strip()
    if current:
        chunks.append(current)
    scenes = [Scene(kicker, title, [], 3.5)]
    scenes += [Scene(kicker, title, [c], seconds_for(c, low=4.0)) for c in chunks]
    scenes.append(cta_scene())
    text = f"IELTS {module} tip: {title}\n\n{body}"
    short = f"IELTS {module} tip: {title}.\n\n{body}"
    return Post(day.isoformat(), "tip", item["id"], kicker, title, [body], scenes, text, short,
                f"IELTS {module} tip: {title}", hashtags("tip", extra) + [f"IELTS{module}"])


def _speaking(day, item, extra):
    topic, points, explain = item["topic"], item["points"], item["explain"]
    said = [*points, explain] if explain else list(points)
    scenes = [
        Scene(KICKERS["speaking"], topic, [], seconds_for(topic, low=4.0)),
        Scene("YOU SHOULD SAY", topic, said, seconds_for(*said, low=6.0, high=10.0)),
        Scene("YOUR TURN", "Take one minute to prepare", ["Then speak for two minutes"], 4.0, dark=True),
        Scene("TESTDAY", "Record your answer", ["Free Speaking tests", "testday.uz"], 3.5, dark=True),
    ]
    bullets = "\n".join(f"- {p}" for p in points)
    text = (f"IELTS Speaking Part 2: {topic}\n\nYou should say:\n{bullets}\n{explain}\n\n"
            "Take one minute to prepare, then speak for two minutes. How would you answer?")
    short = f"IELTS Speaking Part 2: {topic}\n\nSay: " + "; ".join(points) + (f"; {explain}" if explain else "")
    return Post(day.isoformat(), "speaking", item["id"], KICKERS["speaking"], topic, [*said], scenes, text, short,
                f"IELTS Speaking Part 2: {topic}", hashtags("speaking", extra))


def _writing(day, item, extra):
    label = ESSAY_TYPES.get(item.get("type"), "Essay question")
    lines = item["lines"]
    scenes = [
        Scene(KICKERS["writing"], label, [], 3.5),
        Scene(label.upper(), "The question", lines, seconds_for(*lines, low=7.0, high=11.0)),
        Scene("YOUR TURN", "Plan for 5 minutes", ["Write at least 250 words", "You have 40 minutes"], 4.0, dark=True),
        cta_scene(),
    ]
    question = "\n".join(lines)
    text = (f"IELTS Writing Task 2 ({label.lower()}):\n\n{question}\n\n"
            "Plan for 5 minutes, then write at least 250 words in 40 minutes. What is your position?")
    short = f"IELTS Writing Task 2 ({label.lower()}):\n\n{question}"
    return Post(day.isoformat(), "writing", item["id"], KICKERS["writing"], label, lines, scenes, text, short,
                f"IELTS Writing Task 2: {label}", hashtags("writing", extra))


def _promo(day, item, extra):
    title, body = item["title"], item["body"]
    scenes = [
        Scene(KICKERS["promo"], title, [], 3.5),
        Scene("TESTDAY", title, [body], seconds_for(body, low=5.0)),
        Scene("TESTDAY", "Start free", ["Listening · Reading", "Writing · Speaking", "testday.uz"], 4.0, dark=True),
    ]
    text = f"{title}\n\n{body}"
    return Post(day.isoformat(), "promo", item["id"], KICKERS["promo"], title, [body], scenes, text, f"{title}. {body}",
                title, hashtags("promo", extra))


BUILDERS = {"vocab": _vocab, "tip": _tip, "speaking": _speaking, "writing": _writing, "promo": _promo}


def post_for(day, extra_hashtags=(), bank=None):
    """The post for a date (a datetime.date or an ISO string)."""
    if isinstance(day, str):
        day = date.fromisoformat(day)
    if isinstance(day, datetime):
        day = day.date()
    bank = bank or load_bank()
    kind = kind_for(day)
    pool = bank[POOLS[kind]]
    item = pool[occurrence(day, kind) % len(pool)]
    return BUILDERS[kind](day, item, tuple(extra_hashtags))


def caption(post, platform, site_link, extra_tags=()):
    """The text that goes with the post on one platform, within that platform's limits."""
    tags = " ".join(f"#{t}" for t in post.hashtags)
    if platform == "threads":  # 500 characters in all, so shorten the text and keep the link
        room = 500 - len(site_link) - 4
        return f"{trim_lines(post.short, room)}\n\n{site_link}"
    cta = "Practise free on TestDay: five full tests in every module."
    if platform == "instagram":  # a link in a caption is not clickable
        return f"{post.text}\n\n{cta} Link in bio: testday.uz\n\n{tags}"[:2200]
    if platform == "youtube":
        return f"{post.text}\n\n{cta}\n{site_link}\n\n{tags} #Shorts"[:4900]
    return f"{post.text}\n\n{cta}\n{site_link}\n\n{tags}"[:2200]


def trim_lines(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit - 1]
    cut = cut.rsplit("\n", 1)[0] if "\n" in cut and len(cut.rsplit("\n", 1)[0]) > limit // 2 else cut
    return cut.rstrip(" ,;:.-—") + "…"


def youtube_title(post):
    return trim(f"{post.title} #Shorts", 100) if len(f"{post.title} #Shorts") <= 100 else trim(post.title, 91) + " #Shorts"
