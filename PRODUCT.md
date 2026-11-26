# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

IELTS candidates in Uzbekistan preparing for the computer-delivered IELTS. They practise on their phones in short sessions (commutes, breaks, evenings) and sit full timed tests on a laptop or desktop when they can, because the real test is taken on a computer. Many are school leavers and university students working towards a target band for admission or a scholarship.

Secondary users: examiners who mark paid Writing and Speaking checks, and the site owner/admin who confirms payments and manages examiners.

## Product Purpose

TestDay (testday.uz) lets candidates rehearse the real computer-delivered IELTS: Listening, Academic Reading, Academic Writing and Speaking under the same screen layout, timing and rules, then see an estimated band, why every answer was right or wrong, and how they are progressing. Success is a candidate who knows what test day will feel like and which question types to work on next, and who comes back to take the next test.

## Positioning

- The exam screens reproduce the computer-delivered IELTS: split screen, timer, question navigator, Review flags, highlighting and notes, contrast and text-size options, a sound check, and listening that plays once in timed mode.
- Listening, Writing and Speaking tests and Reading tests 1–6 are written for the site. See Content status below for the rest of the Reading bank.
- Human examiners (rated by students) mark Writing and Speaking checks for a small fee, paid locally with Payme or Click.
- The Speaking AI examiner (needs `OPENROUTER_API_KEY`) is face to face and adapts the test to the candidate: it listens to every answer as the test goes on and asks 7 to 9 questions in Part 1, the cue card in Part 2, and 3 to 10 questions in Part 3, fewer when the candidate is struggling and more when they are doing well. The report says how long the test was and why.
- Launch: five full tests of every module are free and the rest show "Coming soon…" (blurred); the passes are not on sale and examiner checks are hidden (`COMMERCE_ENABLED=0`), but the Price page (with the prices) and the Refund policy are public. When selling starts (`COMMERCE_ENABLED=1`) there are four monthly passes: All-in-one (79,000 so'm a month), Speaking (59,000), Writing (49,000) and Listening + Reading (39,000), or in US dollars by card through Dodo Payments ($7.99, $5.99, $4.99, $3.99); card passes are subscriptions that renew until cancelled, so'm passes are one payment. AI marking with a pass: 30 Speaking tests and 30 Writing scripts per 30 days; a free account gets one of each, once (docs/COSTS.md, docs/AI_SAFETY.md, docs/SECURITY.md).

## Operating Context

- Free Listening, Reading and Writing tests need no account; Speaking needs a free account because recordings are saved to it.
- Payment by card in US dollars through Dodo Payments: a pass is a subscription that renews every month until the student cancels (Payme, Click or other local methods can be added). No payment is confirmed by hand.
- Sign-in by a 6-digit email code, or in one click with Google (when `GOOGLE_CLIENT_ID` is set).
- Answers and essays autosave in the browser so an attempt survives a refresh.
- Hosted on Render with Supabase; pages must load fast on mobile data in Uzbekistan.

## Capabilities and Constraints

- Modules and content today: Listening 56 tests, Academic Reading 96, Academic Writing 35, Speaking 100. Each module has 5 free tests; the rest are "Coming soon" until selling starts.
- Content status: Reading tests 1–6 are original. Most of the remaining Reading tests are practice material of mixed origin, repaired and checked but not original; they are to be replaced by original tests over time, and until then the site must not call its content original. Listening has 16 tests (about 16–20 minutes each, written for the site and voiced with open-licence text-to-speech; tests 12–16 were added as "Coming soon") and is the next thing to grow.
- Results: estimated band, per-section and per-question-type breakdown, explanation for every answer, listening transcript with answers highlighted and "listen again".
- Progress page with latest band per module and band over time; history of attempts.
- Examiner checks: Writing 10,000 so'm, Speaking 20,000 so'm; examiners mark the four official criteria and are rated once per check.
- Stack: plain HTML/CSS/JavaScript single-page app served by a Python (Tornado) server; no build step and no framework. Keep it that way.
- Interface language: English only. Students come to practise the test, which is in English; there is no language switch. Test content (passages, recordings, questions, tasks) is in English.
- Band scores are practice estimates, not official results.

## Brand Commitments

- Name: TestDay, at testday.uz.
- Independent site: must state it is not affiliated with, endorsed by or approved by the British Council, IDP IELTS or Cambridge University Press & Assessment, and that IELTS is a trademark of its owners used only descriptively. "IELTS" must not appear in the logo or brand name.

## Evidence on Hand

- Real: the test content in `content/`, the recordings in `public/audio/`, the prices above, the feature list in README.md.
- Absent: testimonials, user counts, pass rates, partner logos, press. Do not invent any of them.

## Product Principles

1. Rehearsal, not a quiz app: the exam screens behave like the real test; everything around them helps the candidate prepare and reflect.
2. Free first, then pay: a candidate can start a full free test in one or two taps, with no sign-up for Listening, Reading and Writing.
3. Honest feedback: estimated bands are labelled as estimates; every mark is explained.
4. Light and fast on a phone: small pages, no heavy media, works on slow mobile connections.
5. Local: so'm prices and local payment methods; the interface stays in English, like the exam.

## Accessibility & Inclusion

- Exam screens keep the computer-delivered test's contrast themes and text sizes.
- Body text and controls must stay readable on small phones in daylight; touch targets sized for thumbs.
