# Content guide: what's legal, and how to add tests

## Why the Cambridge tests were removed

The earlier version of this project contained tests labelled *Cambridge IELTS 17, 18 and 19*. Those books, and every official IELTS test, are copyrighted by Cambridge University Press & Assessment and the IELTS partners. Their [copyright and trade mark statement](https://ielts.org/legal/ielts-copyright-and-trade-mark-statement) explicitly forbids republishing their material on another website, modifying it, or using it commercially. Close paraphrases of those passages with the same titles and question sets are derivative works and carry the same risk. Publishing them would expose the site to takedown notices and legal claims, so they are no longer loaded or served.

## Where legal content can come from

| Source | Can we use it? | Notes |
|---|---|---|
| Official IELTS tests, Cambridge IELTS books, British Council / IDP practice tests | **No** (copy or adapt) · **Yes** (link to them) | See the in-app *Free official resources* page, which links out |
| **Original writing** | **Yes, best option** | What this project uses. You own it and competitors cannot copy it |
| US federal government works (NASA, NOAA, NIH, NPS, USGS…) | Yes | Public domain in the US; fine as a factual source or to adapt |
| Wikipedia | Yes, with conditions | CC BY-SA 4.0: adapted passages must credit Wikipedia **and** be released under CC BY-SA, so others may reuse them |
| OpenStax textbooks | Only if the site stays non-commercial | Currently CC BY-NC-SA ("NonCommercial"). Avoid if you will ever charge |
| The Conversation | Not for IELTS passages | CC BY-ND means no edits; IELTS passages must be cut and adapted |
| Project Gutenberg / pre-1930 texts | Yes | Public domain, but the language is usually too old-fashioned for IELTS |
| News sites, blogs, magazines | No | Copyrighted unless the licence says otherwise |

Facts themselves are not copyrighted. Reading widely and then writing a new passage in your own words, with your own structure, is the safe approach. That is how every passage in `content/` was produced.

## Current content

| Test | Passages / tasks |
|---|---|
| Reading 1 | The Language of the Hive · The Box That Shrank the World · The Puzzle of the Placebo |
| Reading 2 | The Return of the Wolf · The Problem of Longitude · Does Language Shape the Way We Think? |
| Reading 3 | Saving the Kākāpō · The Rock That Built the Modern World · Too Much of a Good Thing? |
| Reading 4 | The Unlikely History of the Pencil · Cities That Heat Up · The Wisdom of Crowds |
| Writing 1 | Line graph (payment methods) · Discussion essay (purpose of university) |
| Writing 2 | Bar chart (leisure by age) · Two-part essay (living alone) |
| Writing 3 | Process diagram (glass recycling) · Opinion essay (roads vs public transport) |
| Writing 4 | Pie charts (household energy) · Advantages/disadvantages essay (early language learning) |
| Writing 5 | Table (museum visitors) · Causes and solutions essay (children spending time outdoors) |

All Task 1 chart data is fictional and labelled as such on the chart.

## Adding a reading test

Create `content/reading/academic-reading-04.json` following the existing files. Structure:

```jsonc
{
  "id": "academic-reading-04", "module": "reading", "variant": "academic",
  "title": "Academic Reading Practice Test 4", "shortTitle": "Practice Test 4",
  "durationMinutes": 60, "totalQuestions": 40, "sortOrder": 4,
  "passages": [{
    "passageNumber": 1, "title": "…", "subtitle": "…",
    "paragraphs": [{ "label": "A", "text": "…" }],      // label null when not needed
    "groups": [ /* question groups, see below */ ]
  }]
}
```

Each group is one instruction block. Supported `type` values:

| type | Extra fields | Question fields |
|---|---|---|
| `true_false_not_given`, `yes_no_not_given` | – | `prompt`, `answer` |
| `multiple_choice` | – | `prompt`, `options[{key,text}]`, `answer` |
| `choose_multiple` | `prompt`, `options`, `answer: ["C","E"]` | `{number}` only, one per letter |
| `matching_headings`, `matching_features`, `matching_sentence_endings`, `classification` | `options`, `optionsTitle` | `prompt`, `answer` (option key) |
| `matching_information` | – (uses paragraph labels) | `prompt`, `answer` (paragraph letter) |
| `note_completion` | `title`, `content: ["## Heading", "• text {{7}}"]`, `maxWords` | `answer: ["word", "alternative"]` |
| `summary_completion` | `title`, `content: "text {{23}} …"`, `maxWords` **or** `options` (word list) | `answer` (words, or option key) |
| `table_completion` | `content: {headers, rows}` with `{{n}}` in cells, `maxWords` | `answer` |
| `flow_chart_completion` | `content: ["step {{n}}", …]`, `maxWords` | `answer` |
| `sentence_completion` | `maxWords` | `prompt` containing `{{n}}`, `answer` |
| `short_answer` | `maxWords` | `prompt`, `answer` |

Every question should have an `explanation` (quote the evidence) and a `reference` ("Paragraph C").

Then run:

```bash
python scripts/validate_content.py
```

The validator checks numbering (1–40), that every answer exists in its options, that each completion answer appears **word-for-word in the passage** and respects the word limit, that every `{{n}}` gap appears exactly once, and it prints answer distributions so you can balance TRUE/FALSE/NOT GIVEN keys.

Writing tests (`content/writing/*.json`) need Task 1 with a `visual` (`line`, `bar`, `pie`, `table` or `process`), both tasks with a `prompt`, `minWords`, `recommendedMinutes` and `modelAnswer`, and optional `examinerNotes` that guide the AI examiner.

## Quality checklist for new passages
- 750–950 words, academic register, a clear line of argument
- Questions in passage order within each group (except matching information and headings)
- NOT GIVEN statements must be genuinely unaddressed, not just paraphrased
- Test paraphrase rather than word-matching: rephrase statements and prompts
- Have a second person take the test "cold" before publishing, and compare their answers with the key
