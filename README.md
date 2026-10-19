# TestDay: IELTS-style Listening, Academic Reading, Writing & Speaking practice

**testday.uz** – a distraction-free website for practising the **Listening**, **Academic Reading**, **Academic Writing** and **Speaking** papers under realistic computer-delivered test conditions, with paid marking by human examiners.

> **Independent site.** TestDay is not affiliated with, endorsed by or approved by the British Council, IDP IELTS or Cambridge University Press & Assessment. "IELTS" is a registered trademark of its owners and is used only to describe the exam this site helps people prepare for.

## What's inside

| Module | Content | Marking |
|---|---|---|
| **Listening** | 3 full tests: 12 parts, 120 questions, about an hour of original recordings (form, note, table and flow-chart completion, map and plan labelling, multiple choice, choose two, matching) | Instant: estimated band, per-part and per-question-type analysis, explanations, and the full transcript with every answer highlighted and a *Listen again* button |
| **Reading** | 8 full Academic tests: 24 passages, 320 questions, every IELTS question type | Instant: estimated band, per-passage and per-question-type analysis, explanation for every answer |
| **Writing** | 5 full Academic tests: Task 1 line graph, bar chart, process diagram, pie charts and table, plus 5 Task 2 essays | Automatic checks (length, overview, position, paragraphing, linking, register) plus model answers. Optional **AI examiner** scores all four criteria and gives corrections |
| **Speaking** | 3 full tests: Part 1 interview (8 questions), Part 2 cue card with 1 minute to prepare and 2 minutes to speak, Part 3 discussion (5 questions). The examiner's questions are original recordings | Answers are recorded in the browser and saved to the account. The candidate listens back, gets a self-check, and can order an examiner check |
| **Examiner checks** | Students choose a human examiner (rated by other students) and pay per check: Writing 10,000 so'm, Speaking 20,000 so'm | The examiner marks the four official criteria (reading the essays or playing the recordings) with feedback; the student rates the examiner once |

### Free trial and the monthly plan
- Free tests: 15 Reading tests and one test of each other module (a test is free when its JSON has `"access": "free"`; every other test is `"premium"`). Listening, Reading and Writing need no sign-in; Speaking needs a (free) account because the recordings are saved to it. The other tests and their audio need the monthly plan, and the server enforces this.
- The plan costs 39,000 so'm a month (configurable). The first payment gives two months, and nothing renews automatically.
- Sign-in uses a 6-digit email code or Google (Supabase Auth). Attempts made before signing in are added to the account.
- Payments: Payme and Click (merchant APIs built in, switched on by environment variables), or a card transfer confirmed by an admin.
- Admin panel for confirming payments, refunds, adding examiners and giving plan days.
- Progress page: the latest band per module with the change since the previous test, and a chart of band scores over time (timed Listening/Reading, marked Writing/Speaking), with a table view.
- Notifications (optional): emails through Resend to students, examiners and admins, and Telegram messages to the owner for payments and new checks. Menu counters show payments to confirm and checks to mark.

**All content is original** and written for this project. The recordings are voiced with the open-source Kokoro text-to-speech model (Apache 2.0). The previous Cambridge IELTS 17–19 material has been withdrawn because it is copyrighted (see [CONTENT_GUIDE.md](CONTENT_GUIDE.md)).

### Design
- The home page is one headline, the four modules (each with a *Start free* button and a link to its full list), and three numbers counted from the data. The header has only **Price** and **About**; the footer carries the contact email, the social links, the legal pages and Feedback. The design is described in DESIGN.md. Set `SOCIAL_TELEGRAM`, `SOCIAL_INSTAGRAM`, `SOCIAL_YOUTUBE` and `SOCIAL_TIKTOK` to show social links in the footer.
- The interface is in English only, like the exam itself (all text in `js/strings.js`; `t()` looks it up).
- The site opens straight away. The home page loads only what it needs (about 58 KB compressed, and its three data requests start while the scripts download). A test's questions, the exam screen's code and styles (`css/cd-ielts.css`, `exam.js`, `speaking.js`, `charts.js`, `highlighter.js`), the results page and the progress chart load when a test is started or a result is opened. `U.need()` in `util.js` downloads each bundle whole and runs it in order, so a dropped connection never leaves it half-loaded.
- Product context and the design direction live in `PRODUCT.md` and `.impeccable/surfaces/`; the visual system is documented in `DESIGN.md`.

### Exam experience
- Split-screen passage/questions with a draggable divider, bottom question navigator, **Review** flags, and Part tabs with progress counts
- 60-minute countdown with 10- and 5-minute warnings and auto-submit, or **Practice mode** with no time limit
- Listening: a sound check before the test; in the timed test the recording plays once, straight through, then 2 minutes to check answers before auto-submit. Practice mode adds a full player (pause, ±10 s, seek, part select, 0.75–1.25× speed)
- Speaking: a microphone check (records 4 seconds and plays it back). The examiner asks each question, recording starts automatically and stops when the answer time is up (30 s / 2 min / 1 min) or when the candidate presses *Finish answer*. Answers upload in the background with retries. Practice mode shows the questions and lets the candidate listen back and re-record. Recordings are private (owner, their examiner, admin) and deleted after 60 days
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
python scripts/test_app.py           # the automated tests (it prints the count): scoring, API, caching, interface text, sign-in, plan, Payme, Click, examiner checks, Speaking, notifications
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
  db.py                   table access for accounts/payments: SQLite locally, Supabase REST in production
  dbcache.py              short-lived read cache in front of db.py (the database can be far from the server)
  auth.py                 sign-in with email codes and Google (Supabase Auth); development mode
  accounts.py             profiles, roles, the monthly plan, which tests a user may open
  billing.py              prices, orders, Payme Merchant API, Click SHOP API, card transfers
  checks.py               examiner profiles, paid checks, marking, one review per check
  speaking.py             Speaking submissions, recorded answers, who may listen, clean-up of old recordings
  files.py                private file storage for recordings: a local folder, or a Supabase Storage bucket
  notify.py               email (Resend) and Telegram notifications for payments and checks
  api.py                  HTTP API for all of the above
  web.py                  shared handler code: security headers, sessions, roles
content/
  reading/*.json          Academic Reading tests (1–6 are original; see PRODUCT.md, Content status)
  listening/*.json        original Listening tests: scripts, speakers, questions, line timings
  speaking/*.json         original Speaking tests: examiner's questions, cue cards, answer times
  writing/*.json          original Academic Writing tests (with chart data and model answers)
public/
  index.html              single-page app shell (header, footer, loading skeleton)
  css/portal.css          site design system: tokens and every page outside the exam
  fonts/                  Schibsted Grotesk (self-hosted, three woff2 files, OFL)
  js/strings.js           interface text (English) and t()
  css/cd-ielts.css        exam environment, contrast themes, charts (loads when a test starts)
  js/app.js               router, the home page, test lists, footer, instructions, About and legal pages
  js/account.js           sign-in, paywall, payments, pricing, account, examiners, checks, admin
  js/progress.js          progress tiles and band-over-time chart on the account page (loads on demand)
  auth-callback.html      landing page after Google / email-link sign-in
  js/exam.js              reading, listening and writing exam engines (this and the exam scripts below load on demand)
  js/speaking.js          Speaking test (recorder, uploads), microphone check, results, examiner marking form
  js/results.js           results pages (loads with a test or a result)
  js/charts.js            Task 1 charts (line, bar, pie, table, process) and listening maps as SVG
  audio/<test-id>/*.mp3   listening recordings and the Speaking examiner's questions (generated, see CONTENT_GUIDE.md)
  js/highlighter.js       highlighting and notes
  js/util.js, scoring.js  helpers
supabase/schema.sql       database schema (run once in Supabase)
scripts/
  validate_content.py     content checker
  seed_supabase.py        upload content/ to Supabase
  build_listening_audio.py  generate listening MP3s from the scripts (Kokoro TTS)
  build_speaking_audio.py   generate the Speaking examiner's questions (Kokoro TTS)
  check_listening_audio.py  transcribe the MP3s with Whisper and check every answer is heard
  test_app.py             test suite (prints the number of tests)
  make_og_image.js        draws public/img/og.png, the picture shown when the site is shared (Node + Playwright)
docs/
  PAYMENTS_CHECKLIST.md   step-by-step test purchase and refund on production
.github/workflows/ci.yml  runs the content check and the tests on every push and pull request
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/robots.txt`, `/sitemap.xml` | for search engines; both use `SITE_URL` |
| POST | `/api/events` | funnel events from the browser: visit, free_test_started, cta_click (204) |
| POST | `/api/feedback` | a message from the Feedback button |
| GET | `/api/admin/feedback` | admins: the latest feedback (the funnel is in `/api/admin/stats`) |
| GET | `/api/health` | health check |
| GET | `/api/config` | site name, whether AI marking is enabled |
| GET | `/api/tests` | test summaries |
| GET | `/api/tests/{id}` | one test **without** answers, transcripts or model answers |
| POST | `/api/reading/{id}/submit` | mark a reading attempt |
| POST | `/api/listening/{id}/submit` | mark a listening attempt (the response includes the transcript) |
| POST | `/api/writing/{id}/submit` | analyse (and optionally AI-mark) a writing attempt |
| GET | `/api/history?clientId=` | recent attempts (the account's when signed in) |
| POST | `/api/speaking/{id}/start` | start a Speaking test (signed in) |
| POST | `/api/speaking/submissions/{id}/answers/{key}` | upload one recorded answer (raw `audio/*` body, max 4 MB) |
| POST | `/api/speaking/submissions/{id}/complete` | finish the test |
| GET | `/api/speaking/submissions/{id}`, `/api/speaking/recordings/{id}` | questions with recordings; play one recording (owner, its examiner, admin) |
| … | `/api/auth/*`, `/api/me`, `/api/orders`, `/api/pay/*`, `/api/examiners`, `/api/checks`, `/api/examiner/*`, `/api/admin/*` | accounts, payments and examiner checks; see the top of `mockexam/api.py` |
| GET | `/api/admin/stats` | totals (`Authorization: Bearer $ADMIN_TOKEN`) |
| POST | `/api/admin/refresh` | reload content after editing it in Supabase |

## License
Code: MIT. Test content in `content/`: original work, all rights reserved by the site owner (see [CONTENT_GUIDE.md](CONTENT_GUIDE.md)).
