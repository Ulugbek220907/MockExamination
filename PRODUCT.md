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
- All passages, recordings, questions and tasks are original and written for the site, so they are new to candidates and legal to use.
- Human examiners (rated by students) mark Writing and Speaking checks for a small fee, paid locally with Payme or Click.
- Priced for Uzbekistan: the first test of every module is free; the monthly plan is 39,000 so'm (first payment gives two months, no automatic renewal).

## Operating Context

- Free Listening, Reading and Writing tests need no account; Speaking needs a free account because recordings are saved to it.
- Payment through Payme, Click, or a card transfer confirmed by an admin. Prices in so'm.
- Sign-in by a 6-digit email code (Google sign-in when enabled in Supabase).
- Answers and essays autosave in the browser so an attempt survives a refresh.
- Hosted on Render with Supabase; pages must load fast on mobile data in Uzbekistan.

## Capabilities and Constraints

- Modules and content today: Listening 3 tests, Academic Reading 4, Academic Writing 5, Speaking 3. Test 1 of each module is free; the rest need the plan.
- Results: estimated band, per-section and per-question-type breakdown, explanation for every answer, listening transcript with answers highlighted and "listen again".
- Progress page with latest band per module and band over time; history of attempts.
- Examiner checks: Writing 10,000 so'm, Speaking 20,000 so'm; examiners mark the four official criteria and are rated once per check.
- Stack: plain HTML/CSS/JavaScript single-page app served by a Python (Tornado) server; no build step and no framework. Keep it that way.
- Interface languages: English, Uzbek and Russian with a switch. Test content (passages, recordings, questions, tasks) stays in English.
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
5. Local: so'm prices, local payment methods, and an interface in Uzbek, Russian or English.

## Accessibility & Inclusion

- Exam screens keep the computer-delivered test's contrast themes and text sizes.
- Body text and controls must stay readable on small phones in daylight; touch targets sized for thumbs.
