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
| Official IELTS or Cambridge recordings, podcasts, radio, YouTube | **No** | Audio is copyrighted just like text |
| Open-licence text-to-speech (Kokoro-82M, Apache 2.0) | **Yes** | What this project uses for Listening. No real person's voice is copied |
| Your own recordings, or voice actors with a signed release | Yes | Best quality; keep the release form |

Facts themselves are not copyrighted. Reading widely and then writing a new passage in your own words, with your own structure, is the safe approach. That is how every passage in `content/` was produced.

## Current content

| Test | Passages / tasks |
|---|---|
| Listening 1 | Leisure centre membership form · Country park map and talk · Students plan a food-waste presentation · Lecture on bioluminescence |
| Listening 2 | Booking a family cycle tour · Radio interview about a food festival · Tutorial on a citizen science project · Lecture on seed banks |
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

## Adding a listening test

A listening test is a script (who says what, in order) plus questions. The audio is generated from the script, so editing a line and rebuilding is all it takes to fix a recording.

```jsonc
{
  "id": "listening-03", "module": "listening", "variant": "academic",
  "title": "Listening Practice Test 3", "shortTitle": "Practice Test 3",
  "checkMinutes": 2, "totalQuestions": 40, "sortOrder": 3,
  "speakers": {                                   // Kokoro voices, see the list below
    "narrator": { "name": "Narrator", "voice": "bm_george", "lang": "en-gb" },
    "anna":     { "name": "Anna", "voice": "af_heart", "lang": "en-us" }
  },
  "pronunciations": { "Pilates": "pɪlˈɑːtiːz" },  // optional IPA fixes for misread words
  "parts": [{
    "partNumber": 1, "title": "…", "context": "one line shown above the transcript",
    "script": [
      { "speaker": "narrator", "text": "Part 1. You will hear … First, you have some time to look at questions 1 to 5." },
      { "pause": 20 },                            // seconds of silence (reading time)
      { "speaker": "anna", "text": "…", "tts": "optional text to speak instead of `text`" }
    ],
    "groups": [ /* same question groups as reading, plus map_labelling */ ]
  }]
}
```

- Every question needs a `cue`: a short phrase from the script where the answer is heard (completion questions can omit it; their answer is used). The validator checks that each cue is found in the right part; the results page highlights it in the transcript and plays the recording from there.
- `map_labelling` groups add a `map` (`width`, `height`, `items`: `area`, `trees`, `ellipse` (`path-ring` or `water`), `line`, `rect` (`parking`/`building`), `gate`, `compass` and `letter`) and one option per letter.
- Follow the real test's shape: Part 1 an everyday conversation (form or note completion, one word and/or a number), Part 2 a monologue (map or multiple choice), Part 3 a discussion between students and/or a tutor, Part 4 a lecture (note completion, one word only). Include natural distractors: a speaker corrects a number, or mentions an option and rules it out.
- Good voices: `af_heart`, `af_bella` (US female), `bf_emma`, `bf_isabella` (UK female), `am_michael`, `am_puck` (US male), `bm_george`, `bm_fable` (UK male).

Build and check the audio (needs the Kokoro model files, about 340 MB, see the top of the script):

```bash
pip install -r scripts/requirements-audio.txt
python scripts/build_listening_audio.py --models ~/tts-models --only listening-03
python scripts/check_listening_audio.py --only listening-03   # Whisper transcribes the MP3s
python scripts/validate_content.py
```

The build writes `public/audio/<id>/part<N>.mp3` and records the start and end time of every line in the JSON (used by the transcript). The check fails if an answer cannot be heard where the script says it is, which catches mispronounced names and numbers. Commit the JSON and the MP3s together.

## Quality checklist for new passages
- 750–950 words, academic register, a clear line of argument
- Questions in passage order within each group (except matching information and headings)
- NOT GIVEN statements must be genuinely unaddressed, not just paraphrased
- Test paraphrase rather than word-matching: rephrase statements and prompts
- Have a second person take the test "cold" before publishing, and compare their answers with the key
