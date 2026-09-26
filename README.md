# MockExam: IELTS-style Listening, Academic Reading & Writing practice

A free, distraction-free website for practising the **Listening**, **Academic Reading** and **Academic Writing** papers under realistic computer-delivered test conditions.

> **Independent site.** MockExam is not affiliated with, endorsed by or approved by the British Council, IDP IELTS or Cambridge University Press & Assessment. "IELTS" is a registered trademark of its owners and is used only to describe the exam this site helps people prepare for.

## What's inside

| Module | Content | Marking |
|---|---|---|
| **Listening** | 1 full test: 4 parts, 40 questions, 20 minutes of original recordings (form and note completion, map labelling, multiple choice, matching) | Instant: estimated band, per-part and per-question-type analysis, explanations, and the full transcript with every answer highlighted and a *Listen again* button |
| **Reading** | 4 full Academic tests: 12 original passages, 160 questions, every IELTS question type | Instant: estimated band, per-passage and per-question-type analysis, explanation for every answer |
| **Writing** | 5 full Academic tests: Task 1 line graph, bar chart, process diagram, pie charts and table, plus 5 Task 2 essays | Automatic checks (length, overview, position, paragraphing, linking, register) plus model answers. Optional **AI examiner** scores all four criteria and gives corrections |
| Speaking | – | Coming soon |

**All content is original** and written for this project. The recordings are voiced with the open-source Kokoro text-to-speech model (Apache 2.0). The previous Cambridge IELTS 17–19 material has been withdrawn because it is copyrighted (see [CONTENT_GUIDE.md](CONTENT_GUIDE.md)).

### Exam experience
- Split-screen passage/questions with a draggable divider, bottom question navigator, **Review** flags, and Part tabs with progress counts
- 60-minute countdown with 10- and 5-minute warnings and auto-submit, or **Practice mode** with no time limit
- Listening: a sound check before the test; in the timed test the recording plays once, straight through, then 2 minutes to check answers before auto-submit. Practice mode adds a full player (pause, ±10 s, seek, part select, 0.75–1.25× speed)
- Highlighting and notes, 4 contrast themes, 3 text sizes, and keyboard shortcuts (`Alt+N`, `Alt+P`, `Alt+R`)
- Answers and essays are **autosaved** in the browser, so an attempt can be resumed after a refresh
- Works on phones (single-pane view with a Passage/Questions switch)

### Question types supported
TRUE/FALSE/NOT GIVEN · YES/NO/NOT GIVEN · multiple choice · choose TWO · matching headings · matching information · matching features · matching sentence endings · classification · map/plan labelling · note, summary (with or without word list), table and flow-chart completion · sentence completion · short-answer questions.

## Quick start (local)

```bash
pip install -r requirements.txt
python server.py            # http://localhost:8080
```

Nothing else is required. Without configuration, tests are read from `content/` and attempts are stored in a local SQLite file (`data/local.sqlite3`). Copy `.env.example` to `.env` to enable Supabase and AI marking.

## Checks

```bash
python scripts/validate_content.py   # validates every test (answer keys, word limits, gaps, charts, audio)
python scripts/test_app.py           # 40 automated tests: scoring, API, Supabase client, AI examiner (mocked)
```

## Deploying

See **[DEPLOY.md](DEPLOY.md)** for step-by-step setup of Supabase, the AI examiner and Render.

## Project structure

```
server.py                 Tornado app: static site + JSON API, rate limits, security headers
mockexam/
  content.py              test model: walking, validation, answer-free public views
  scoring.py              reading/listening marking and band conversion
  writing.py              writing text analysis + Claude AI examiner
  storage.py              LocalStore (JSON + SQLite) and SupabaseStore (REST)
content/
  reading/*.json          original Academic Reading tests
  listening/*.json        original Listening tests: scripts, speakers, questions, line timings
  writing/*.json          original Academic Writing tests (with chart data and model answers)
public/
  index.html              single-page app shell
  css/portal.css          site, dashboard, results
  css/cd-ielts.css        exam environment, contrast themes, charts
  js/app.js               router, dashboard, instructions, resources and legal pages
  js/exam.js              reading, listening and writing exam engines
  js/results.js           results pages
  js/charts.js            Task 1 charts (line, bar, pie, table, process) and listening maps as SVG
  audio/<test-id>/*.mp3   listening recordings (generated, see CONTENT_GUIDE.md)
  js/highlighter.js       highlighting and notes
  js/util.js, scoring.js  helpers
supabase/schema.sql       database schema (run once in Supabase)
scripts/
  validate_content.py     content checker
  seed_supabase.py        upload content/ to Supabase
  build_listening_audio.py  generate listening MP3s from the scripts (Kokoro TTS)
  check_listening_audio.py  transcribe the MP3s with Whisper and check every answer is heard
  test_app.py             test suite
```

### Legacy files to delete
`data/tests.json`, `data/attempts.db` and `scripts/build_tests_data.py` hold the withdrawn Cambridge material. They are no longer loaded or served. Delete them from the repository before going live:

```bash
git rm data/tests.json data/attempts.db scripts/build_tests_data.py
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | health check |
| GET | `/api/config` | site name, whether AI marking is enabled |
| GET | `/api/tests` | test summaries |
| GET | `/api/tests/{id}` | one test **without** answers, transcripts or model answers |
| POST | `/api/reading/{id}/submit` | mark a reading attempt |
| POST | `/api/listening/{id}/submit` | mark a listening attempt (the response includes the transcript) |
| POST | `/api/writing/{id}/submit` | analyse (and optionally AI-mark) a writing attempt |
| GET | `/api/history?clientId=` | this browser's recent attempts |
| GET | `/api/admin/stats` | totals (`Authorization: Bearer $ADMIN_TOKEN`) |
| POST | `/api/admin/refresh` | reload content after editing it in Supabase |

## License
Code: MIT. Test content in `content/`: original work, all rights reserved by the site owner (see [CONTENT_GUIDE.md](CONTENT_GUIDE.md)).
