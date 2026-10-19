---
name: TestDay
description: Quiet and typographic. One big headline, hairlines instead of boxes, one deep ink on a warm ground, one filled button.
colors:
  ground: "#e9e8e2"
  field: "#dedcd6"
  paper: "#f4f3ef"
  ink: "#0f1a30"
  ink-2: "#2d3950"
  muted: "#4a566b"
  ink-soft: "#aeb8cb"
  rule: "#c7c6be"
  edge: "#767f90"
  ok: "#1a6b3a"
  bad: "#b02e25"
  warn: "#7a5000"
typography:
  display:
    fontFamily: '"Schibsted Grotesk", "Schibsted Fallback", system-ui, sans-serif'
    fontSize: "clamp(3rem, 0.9rem + 7.4vw, 7rem)"
    fontWeight: 600
    lineHeight: 0.96
    letterSpacing: "-0.03em"
  figure:
    fontSize: "clamp(2rem, 1.2rem + 3vw, 3.75rem)"
    fontWeight: 600
  lead:
    fontSize: "clamp(1.125rem, 1rem + 0.5vw, 1.5rem)"
    lineHeight: 1.3
  body:
    fontSize: "1rem"
    lineHeight: 1.5
rounded:
  panel: "6px"
  button: "999px"
---

# Design system

TestDay used to be a Tashkent-metro map. It is now plain: a warm off-white page, one deep navy ink, and big type doing the work that boxes and colours used to do. The look is meant to read as expensive by being calm, not by adding things. Every page answers one question and says little.

The exam screens (`public/css/cd-ielts.css`) are a different world on purpose: they imitate the real computer-delivered IELTS and are not restyled with the site.

## Principles

1. **One gesture per page.** The home page's gesture is the display headline. Everything else stays quiet.
2. **Type and space, not decoration.** Rows are separated by 1px hairlines and space. No card grids, no shadows at rest, no gradients, no icons for decoration, no letter badges.
3. **One filled shape.** A fully round ink button is the main action on a page. The second action is an outlined round button, or an underlined link.
4. **Say little.** The home page is a headline, one line, four rows and three numbers. Numbers are counted from the data (`/api/tests`, `/api/billing`), never typed in.
5. **Fast on a phone.** No images on the home page. Three font files, the browser fetches only the ones a page needs. No animation libraries.

## Colour

| Token | Value | Use |
|---|---|---|
| `--ground` | `#e9e8e2` | the page |
| `--paper` | `#f4f3ef` | raised surfaces: inputs, panels, dialogs |
| `--field` | `#dedcd6` | tinted fills (key caps, tracks) |
| `--ink` | `#0f1a30` | text, filled buttons, the footer band |
| `--ink-2` | `#2d3950` | body text under a heading |
| `--muted` | `#4a566b` | captions (6.0:1 on the ground) |
| `--ink-soft` | `#aeb8cb` | small text on ink (8.7:1) |
| `--rule` | `#c7c6be` | hairlines |
| `--edge` | `#767f90` | the border of a form field (3.3:1) |

Status colours (`--ok`, `--bad`, `--warn`, `--info`) appear only for results and notices. The four module colours are gone from the UI. They survive only as `--series-1…4` in the progress chart, where four lines must be told apart.

Ink on ground is 14.1:1. Never put muted text on `--field` below 14px.

## Type

One family, Schibsted Grotesk (OFL), self-hosted in three files: `core` (ASCII and common punctuation, 24 KB) is declared last so it wins for those characters; `latin` and `latin-ext` are fetched only when a page uses characters outside `core`. A fallback face (`Schibsted Fallback`, Arial with size-adjust and ascent/descent overrides) keeps layout from shifting while the font loads.

- Display: `--t-display`, weight 600, line-height 0.96, tracking −0.03em (−0.04em from 1024px). The home headline and each page's `h1`.
- Figure: `--t-figure`. Module names on the home page, the three numbers, prices.
- Lead: `--t-lead`. The line under a headline, and captions under figures.
- Body: 16px, line-height 1.5. Never smaller for anything a student must read; the one 14px size (`--t-small`) is for facts and captions.

Sentence case everywhere. No all-caps labels, no eyebrows above headings, no accent word inside a headline. Tabular figures are on for whole-number columns only (this font draws full-width punctuation with them on), so bands such as 6.5 and dates use normal figures.

## Layout

A 12-column grid from 1024px with a `clamp(1.25rem, …, 2rem)` gutter; one column below. The page is capped at 1760px, not at a reading width: only text measures are constrained (`ch`).

- Home, from 1024px: the one-line summary sits in the left third, the headline, the four module rows and the figures in the right two thirds.
- About and the legal pages: the heading in the left third, the text in the right two thirds, text at most 62ch.
- Test lists and Prices use the full width, with hairline rows.
- Sections are 96–200px apart; the space is the structure.

## Components

- **Header:** the wordmark, **Price**, **About**, and the account (a round "Sign in" button, or an avatar). Nothing else. It is not sticky.
- **Footer:** the last thing on every page. An ink band with the contact email, the social links from `config.social` (`SOCIAL_*` env vars; each shows only when set), Price, About, Examiners, Terms, Privacy, Refunds, Feedback, the one-line independence disclaimer and a giant wordmark. The full trademark text lives on About and the legal pages.
- **Module row (home):** name, "N tests, K free" (the count links to the module's list), one format line, and one button: *Start free* (or *Start* / *Next test* for a pass holder), or *All tests* when nothing is left to start. On hover (mouse only) the row inverts to ink.
- **Test row (list page):** name, the passage or task titles, a tag (*Free*, *Pass* with a lock, *In your pass*), and *Practice* and *Start*; a locked test has one quiet action, *Get the pass*.
- **Buttons:** `btn-primary` (ink, round), `btn-secondary` (outline, round), `btn-link` (underlined text), `btn-danger`. Minimum 44px tall on every viewport for primary controls.
- **Chips and inputs:** 44px tall, 1.5px `--edge` border, round for chips and the search box, 6px for text fields.
- **Panels** (account, results, examiners): `--paper` on `--ground`, 1px `--rule` border, 6–8px radius, no shadow. Dialogs are the only thing that casts a shadow.
- **Tables:** hairline rows, no stripes.

## Motion

CSS only, subtle, and off under `prefers-reduced-motion`. A 160ms colour change on hover and focus, a 0.97 scale on press, and a 220ms rise for dialogs. Nothing animates on scroll and no number counts up. Hover effects are wrapped in `@media (hover: hover) and (pointer: fine)`.

## Do not

- Add images, video, canvas or an animation library to the home page.
- Reintroduce module colours, letter badges, transit vocabulary (lines, stations, interchange, fares) or card grids.
- Use more than one filled button in a view.
- Hide the main action behind a menu.
- Type a number the data can count.
- Claim anything the site cannot show: no testimonials, user counts or pass rates, and do not call the tests original (see PRODUCT.md, Content status).

## Where it lives

| What | Where |
|---|---|
| Tokens, every site style | `public/css/portal.css` |
| Header, footer, the loading skeleton | `public/index.html` |
| Home, test lists, About, legal pages, footer data | `public/js/app.js` |
| Prices | `renderPricing` in `public/js/account.js` |
| Copy | `public/js/strings.js` |
| Fonts | `public/fonts/` |
| Share image and logos | `scripts/make_og_image.js` |
