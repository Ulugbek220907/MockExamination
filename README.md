# TestDay: IELTS-style Listening, Academic Reading, Writing & Speaking practice

**testday.uz** – a distraction-free website for practising the **Listening**, **Academic Reading**, **Academic Writing** and **Speaking** papers under realistic computer-delivered test conditions, with paid marking by human examiners.

> **Independent site.** TestDay is not affiliated with, endorsed by or approved by the British Council, IDP IELTS or Cambridge University Press & Assessment. "IELTS" is a registered trademark of its owners and is used only to describe the exam this site helps people prepare for.

> **Also in this repository:** `social-poster/` is a separate small service that posts a TestDay post every day to YouTube, TikTok, Instagram, Threads and Facebook. It is a second service in the repository's `render.yaml` (`testday-social`), with its own requirements and tests, and is not part of the website; see [social-poster/README.md](social-poster/README.md) for how to create it in Render (it is not created by a push).

## What's inside

| Module | Content | Marking |
|---|---|---|
| **Listening** | 3 full tests: 12 parts, 120 questions, about an hour of original recordings (form, note, table and flow-chart completion, map and plan labelling, multiple choice, choose two, matching) | Instant: estimated band, per-part and per-question-type analysis, explanations, and the full transcript with every answer highlighted and a *Listen again* button |
| **Reading** | 8 full Academic tests: 24 passages, 320 questions, every IELTS question type | Instant: estimated band, per-passage and per-question-type analysis, explanation for every answer |
| **Writing** | 5 full Academic tests: Task 1 line graph, bar chart, process diagram, pie charts and table, plus 5 Task 2 essays | Automatic checks (length, overview, position, paragraphing, linking, register) plus model answers. Optional **AI examiner** (through OpenRouter) scores all four criteria with instructions for each task type and gives corrections |
| **Speaking** | 100 full tests (5 free): Part 1 interview (10 questions), Part 2 cue card with 1 minute to prepare and 2 minutes to speak, Part 3 discussion (5 or 6 questions; the AI examiner can ask up to 10). The examiner's questions are original recordings | Answers are recorded in the browser and saved to the account. The candidate listens back, gets a self-check, and can order an examiner check. With the **AI examiner** the test is face to face with an animated examiner who asks the questions and moves on when the candidate stops talking, and **the test adapts to how the candidate speaks** (7 to 9 questions in Part 1, then the cue card, then 3 to 10 questions in Part 3; a weak performance stops at the short test); afterwards the AI listens to every answer (fillers, pauses, pronunciation) and gives an estimated band for each criterion, transcripts and feedback |
| **Examiner checks** | Students choose a human examiner (rated by other students) and pay per check: Writing 10,000 so'm, Speaking 20,000 so'm | The examiner marks the four official criteria (reading the essays or playing the recordings) with feedback; the student rates the examiner once |

### Free trial and the passes
- **Launch mode** (`COMMERCE_ENABLED` unset or `0`, the default): the first five tests of every module are free and every other test is shown blurred with "Coming soon…". Nothing is for sale: the Price, Examiners and Refund pages, the pass, orders and examiner checks are hidden in the site and answer 404 on the server. A test is free when its JSON says `"access": "free"` (or has no `access` and `sortOrder` is 5 or less); a test that says `"premium"` (or has no `access` and `sortOrder` above 5) is "soon" in launch mode, and refused by the API and the audio to everyone except admins and examiners, who can preview it. Listening, Reading and Writing need no sign-in; Speaking needs a (free) account because the recordings are saved to it.
- **Selling mode** (`COMMERCE_ENABLED=1`): the same `"premium"` tests need a pass that covers their paper, the Examiners pages and examiner checks come back, and the server enforces the pass. The Price page (with the passes and their prices) and the Refunds page are public in both modes, because payment services check for them. Passes: **All-in-one** (all four papers), **Speaking**, **Writing** and **Listening + Reading**, month by month, in so'm (Payme, Click, card transfer) or in US dollars by card through Dodo Payments (`mockexam/dodo.py`, see docs/PAYMENTS_CHECKLIST.md). AI marking has an allowance per person, bigger with a pass than on a free account (`mockexam/ai_usage.py`; the sums are in docs/COSTS.md, the safety checks in docs/AI_SAFETY.md, the protections against floods and runaway bills in docs/SECURITY.md).
- Prices are in `mockexam/billing.py` (`PLAN_PRICES`), a month: All-in-one 79,000 so'm or $7.99, Speaking 59,000 / $5.99, Writing 49,000 / $4.99, Listening + Reading 39,000 / $3.99.
- Sign-in uses a 6-digit email code, or Google in one click. Google's own button appears when `GOOGLE_CLIENT_ID` is set (see DEPLOY.md, "Sign in with Google"); the server checks Google's signed ID token itself. The older route, through Supabase's Google provider, still works when that is the one switched on. Attempts made before signing in are added to the account.
- Payments: a card in US dollars through Dodo Payments (a subscription that renews until the student cancels), and in so'm Click (Uzcard and Humo; Shop API plus Merchant API for refunds, one payment per pass, no renewal) or Payme, each switched on by environment variables. The admin page returns money through Dodo and Click.
- Admin panel for confirming payments, refunds, adding examiners and giving plan days, with revenue for the last 7 and 30 days (pass vs. examiner checks), passes active now and passes ending within 7 days.
- Progress page: the latest band per module with the change since the previous test, and a chart of band scores over time (timed Listening/Reading, marked Writing/Speaking), with a table view.
- Study goal: a target band and exam date, shown on the home page (days to the exam), on the progress tiles and as a dashed line on the chart.
- Practice by question type (`#/practice`): one Reading passage with only one type of question, weakest types first, no timer, no band and nothing saved. The results page links to the weakest type.
- The pass: a notice in its last 5 days and a reminder email 3 days before it ends (unless another month is already bought).
- Installable on phones and computers (`manifest.webmanifest`).
- Notifications (optional): emails through Resend to students, examiners and admins, and Telegram messages to the owner for payments, new checks and server errors (each error at most once per 15 minutes). Menu counters show payments to confirm and checks to mark.

**All content is original** and written for this project. The recordings are voiced with the open-source Kokoro text-to-speech model (Apache 2.0). The previous Cambridge IELTS 17–19 material has been withdrawn because it is copyrighted (see [CONTENT_GUIDE.md](CONTENT_GUIDE.md)).

### Design
- The home page is one headline, the four modules (each with a *Start free* button and a link to its full list), and three numbers counted from the data. The header has only **About** (and **Price** once `COMMERCE_ENABLED=1`); the footer carries the contact email, the social links, the legal pages and Feedback. The design is described in DESIGN.md. Set `SOCIAL_TELEGRAM`, `SOCIAL_INSTAGRAM`, `SOCIAL_YOUTUBE` and `SOCIAL_TIKTOK` to show social links in the footer.
- The interface is in English only, like the exam itself (all text in `js/strings.js`; `t()` looks it up).
- The site opens straight away. The home page loads only what it needs (about 58 KB compressed, and its three data requests start while the scripts download). A test's questions, the exam screen's code and styles (`css/cd-ielts.css`, `exam.js`, `speaking.js`, `charts.js`, `highlighter.js`), the results page and the progress chart load when a test is started or a result is opened. `U.need()` in `util.js` downloads each bundle whole and runs it in order, so a dropped connection never leaves it half-loaded.
- Product context and the design direction live in `PRODUCT.md` and `.impeccable/surfaces/`; the visual system is documented in `DESIGN.md`.

### Pages for search engines
The app is one page whose sections are `#/` addresses, which search engines treat as one URL. So the things people search for have their own plain-HTML pages in `mockexam/seo.py`: a free practice test, one page for each paper (Listening, Reading, Writing, Speaking) and a band score calculator, each in English (`/en/...`), Uzbek (`/uz/...`) and Russian (`/ru/...`). Each has its own title, description, canonical address, `hreflang` links to its other-language versions, and a button into the app; `sitemap.xml` lists them all. The tests and the app stay in English, and the Uzbek and Russian pages say so. The calculator page (`public/js/seo-calc.js`) uses the same score tables as the app (`mockexam/scoring.py`). The pages about the real exam (computer-delivered format, fees in Uzbekistan, the state refund for IELTS 7.0+, what band 7 means) are in `mockexam/seo_guides.py`; they show the date their facts were checked and link to the official sources, and docs/SEO_FACTS.md says how often to check them again and which claims were left out. To add or change a page, edit `CONTENT` in `mockexam/seo.py` (titles up to 60 characters and descriptions up to 155 are checked by the tests). `/en/ielts-practice-tests-and-guides` is a hub that links to every page (and is linked from the home page's footer and from every page's footer), so crawlers and readers reach all of them in one click. `/pricing`, `/about`, `/terms`, `/privacy` and `/refunds` redirect to the matching `#/` section so a plain address can be given out. `robots.txt` lets crawlers load `/api/tests`, `/api/config` and `/api/me`, which the home page needs to draw; the rest of `/api/` stays closed.

### Exam experience
- Split-screen passage/questions with a draggable divider, bottom question navigator, **Review** flags, and Part tabs with progress counts
- 60-minute countdown with 10- and 5-minute warnings and auto-submit, or **Practice mode** with no time limit
- Listening: a sound check before the test; in the timed test the recording plays once, straight through, then 2 minutes to check answers before auto-submit. Practice mode adds a full player (pause, ±10 s, seek, part select, 0.75–1.25× speed)
- Speaking: a microphone check (records 4 seconds and plays it back). The examiner asks each question, recording starts automatically and stops when the answer time is up (30 s / 2 min / 1 min) or when the candidate presses *Finish answer*. Answers upload in the background with retries. Practice mode shows the questions and lets the candidate listen back and re-record. Recordings are private (owner, their examiner, admin) and deleted after 60 days
- Speaking with the AI examiner (`mockexam/speaking_adaptive.py`): every answer is analysed in the background as soon as it has been uploaded, so the examiner knows how the candidate is doing while the test goes on. Part 1 has 7 questions, 8 from an estimated band of 5.5 and 9 from 7. Part 2 (the cue card and its follow-up question) is always asked. Part 3 starts with 3 questions, and after each answer the examiner decides whether to ask one more, from the performance in Parts 1 and 2 and the answers so far: at band 5 or below it stops at 3, and every half band above 5 adds a question, up to 10 (from band 8.5). The extra Part 3 questions are marked `adaptiveOnly` in the content, so a test taken without the AI examiner (practice, no key, `SPEAKING_ADAPTIVE=0`) keeps its usual length. The final rating reuses these analyses, so an adaptive test makes no more AI calls than a fixed one, and fewer when it stops early
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
  writing.py              writing text analysis + AI examiner (rubric for each task type)
  ai.py                   AI models through OpenRouter (JSON answers, audio input)
  storage.py              LocalStore (JSON + SQLite) and SupabaseStore (REST)
  db.py                   table access for accounts/payments: SQLite locally, Supabase REST in production
  dbcache.py              short-lived read cache in front of db.py (the database can be far from the server)
  auth.py                 sign-in with email codes (and Google through Supabase Auth); development mode
  google_signin.py        "Continue with Google": checks Google's ID token (RS256, issuer, audience, expiry, verified email)
  accounts.py             profiles, roles, the passes (by paper), which tests a user may open
  dodo.py                 Dodo Payments: checkout, payment lookup, refunds and the webhook signature
  billing.py              prices, orders, Dodo subscriptions, Payme Merchant API, Click SHOP API
  click_merchant.py       Click Merchant API client: payment lookup and reversal (refunds)
  checks.py               examiner profiles, paid checks, marking, one review per check
  speaking.py             Speaking submissions, recorded answers, who may listen, clean-up of old recordings
  speaking_ai.py          the AI Speaking examiner: measures pauses, listens to each answer, rates the test
  speaking_adaptive.py    the adaptive Speaking test: judges each answer as it comes in and decides how many questions to ask
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
  seed_supabase.py        upload content/ to Supabase (only for TESTS_SOURCE=supabase)
  build_listening_audio.py  generate listening MP3s from the scripts (Kokoro TTS)
  build_speaking_audio.py   generate the Speaking examiner's questions (Kokoro TTS)
  check_listening_audio.py  transcribe the MP3s with Whisper and check every answer is heard
  test_app.py             test suite (prints the number of tests)
  make_ornaments.py       draws the logo mark and the ornament bands (public/img/orn/, favicon.svg, the mark in index.html)
  make_og_image.js        draws public/img/og.png (the picture shown when the site is shared) and the app icons (Node + Playwright)
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
| POST | `/api/speaking/submissions/{id}/plan` | AI-examiner tests: the ordered question keys so far; with `{"after": key}` at the end of Part 1 or Part 3 the examiner may add one question |
| POST | `/api/speaking/submissions/{id}/complete` | finish the test |
| GET | `/api/speaking/submissions/{id}`, `/api/speaking/recordings/{id}` | questions with recordings; play one recording (owner, its examiner, admin) |
| … | `/api/auth/*`, `/api/me`, `/api/orders`, `/api/pay/*`, `/api/examiners`, `/api/checks`, `/api/examiner/*`, `/api/admin/*` | accounts, payments and examiner checks; see the top of `mockexam/api.py` |
| GET | `/api/admin/stats` | totals (`Authorization: Bearer $ADMIN_TOKEN`) |
| POST | `/api/admin/refresh` | reload content after editing it in Supabase |

## License
Code: MIT. Test content in `content/`: original work, all rights reserved by the site owner (see [CONTENT_GUIDE.md](CONTENT_GUIDE.md)).
