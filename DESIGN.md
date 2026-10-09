---
name: TestDay
description: Tashkent-metro wayfinding for IELTS practice; four module lines that all end at Test day.
colors:
  granite: "#142038"
  granite-2: "#1d2b47"
  granite-3: "#2c3c5d"
  granite-ink: "#eef2f8"
  granite-muted: "#a9b5ca"
  marble: "#f1f3f6"
  marble-2: "#e5e9ef"
  paper: "#ffffff"
  rule: "#d4dae3"
  rule-soft: "#e7ebf0"
  ink: "#141a22"
  ink-2: "#384252"
  muted: "#586273"
  line-l: "#1f5fbf"
  line-r: "#cf3a2c"
  line-w: "#1e7c42"
  line-s: "#e3a21a"
  line-l-soft: "#e3ecf9"
  line-r-soft: "#fbe6e3"
  line-w-soft: "#e1f1e7"
  line-s-soft: "#fcf0d5"
  line-s-ink: "#8a5a00"
  line-w-ink: "#1a7340"
  primary-hover: "#194f9f"
  ok: "#1a7340"
  ok-soft: "#e1f1e7"
  bad: "#b8322a"
  bad-soft: "#fbe6e3"
  warn: "#8a5a00"
  warn-soft: "#fcf0d5"
  info: "#1f5fbf"
  info-soft: "#e3ecf9"
typography:
  display:
    fontFamily: 'Jost, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "clamp(2rem, 1.1rem + 3vw, 3.4rem)"
    fontWeight: 650
    lineHeight: 1.04
    letterSpacing: "-0.025em"
  headline:
    fontFamily: 'Jost, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "clamp(1.8rem, 1.3rem + 1.6vw, 2.5rem)"
    fontWeight: 650
    lineHeight: 1.12
    letterSpacing: "-0.02em"
  title:
    fontFamily: 'Jost, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "1.6rem"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  plaque:
    fontFamily: 'Jost, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "1.22rem"
    fontWeight: 650
    lineHeight: 1.15
  station:
    fontFamily: 'Jost, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "0.9rem"
    fontWeight: 600
  numeral:
    fontFamily: 'Jost, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "2.7rem"
    fontWeight: 650
    lineHeight: 1
    fontFeature: '"tnum"'
  body:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
  lead:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "1.08rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "0.95em"
    fontWeight: 650
    lineHeight: 1.25
  caption:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "0.86rem"
    fontWeight: 400
  tag:
    fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "0.74rem"
    fontWeight: 750
rounded:
  tag: "6px"
  sm: "8px"
  control: "10px"
  md: "12px"
  card: "16px"
  board: "18px"
  pill: "999px"
spacing:
  gutter: "clamp(16px, 4vw, 40px)"
  section: "64px"
  block: "36px"
  plaque-x: "22px"
  stack: "12px"
  gap: "10px"
components:
  button-primary:
    backgroundColor: "{colors.granite}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "9px 18px"
    height: "42px"
  button-primary-hover:
    backgroundColor: "{colors.granite-3}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "9px 18px"
    height: "42px"
  button-line-l:
    backgroundColor: "{colors.line-l}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "9px 18px"
    height: "42px"
  button-line-r:
    backgroundColor: "{colors.line-r}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
  button-line-w:
    backgroundColor: "{colors.line-w}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
  button-line-s:
    backgroundColor: "{colors.line-s}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
  button-lg:
    padding: "12px 24px"
    height: "50px"
  button-sm:
    padding: "5px 12px"
    height: "34px"
  start-free-pill:
    backgroundColor: "{colors.line-l}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    padding: "4px"
    height: "40px"
  line-bullet:
    backgroundColor: "{colors.line-l}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    size: "28px"
  line-bullet-sm:
    size: "22px"
  line-bullet-lg:
    size: "40px"
  station-ring:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    size: "30px"
  station-ring-ridden:
    backgroundColor: "{colors.line-l}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    size: "44px"
  interchange-capsule:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    width: "36px"
    height: "62px"
  hub-plaque:
    backgroundColor: "{colors.granite}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "7px 12px 8px"
  station-sign:
    backgroundColor: "{colors.granite}"
    textColor: "{colors.granite-ink}"
    rounded: "14px"
    padding: "18px 22px"
  site-nav:
    backgroundColor: "{colors.granite}"
    textColor: "{colors.granite-ink}"
    padding: "0 clamp(16px, 4vw, 40px)"
    height: "68px"
  nav-link:
    textColor: "{colors.granite-muted}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
  nav-link-active:
    textColor: "{colors.paper}"
  nav-signin:
    backgroundColor: "{colors.granite-ink}"
    textColor: "{colors.granite}"
    rounded: "9px"
    padding: "8px 16px"
    height: "38px"
  lang-switch-active:
    backgroundColor: "{colors.granite-ink}"
    textColor: "{colors.granite}"
    rounded: "7px"
  site-footer:
    backgroundColor: "{colors.granite}"
    textColor: "{colors.granite-muted}"
  pass-card:
    backgroundColor: "{colors.granite}"
    textColor: "{colors.paper}"
    rounded: "20px"
    padding: "24px 26px"
  fare-board:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.board}"
  fare-head:
    backgroundColor: "{colors.granite}"
    textColor: "{colors.paper}"
    padding: "14px 22px"
  card-board:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.board}"
    padding: "22px 24px"
  card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "20px 22px"
  card-compact:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "16px 18px"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
    height: "46px"
  chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    padding: "6px 14px"
    height: "36px"
  chip-active:
    backgroundColor: "{colors.granite}"
    textColor: "{colors.paper}"
  tag:
    backgroundColor: "{colors.info-soft}"
    textColor: "{colors.info}"
    typography: "{typography.tag}"
    rounded: "{rounded.tag}"
    padding: "2px 8px"
  tag-ok:
    backgroundColor: "{colors.ok-soft}"
    textColor: "{colors.ok}"
  tag-warn:
    backgroundColor: "{colors.warn-soft}"
    textColor: "{colors.warn}"
  band-circle:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    size: "132px"
  notice-info:
    backgroundColor: "{colors.info-soft}"
    rounded: "{rounded.md}"
    padding: "14px 18px"
  toast:
    backgroundColor: "{colors.granite}"
    textColor: "{colors.paper}"
    rounded: "{rounded.md}"
    padding: "12px 18px"
---

# Design System: TestDay

## Overview

**Creative North Star: "The Interchange at Test Day"**

TestDay is drawn as a Tashkent metro map. The four IELTS modules are four lines: Listening blue, Reading red, Writing green, Speaking amber. Every test is a station on its line, and every line runs into one interchange, Test day. The site shell is polished granite (the header, footer, station signs, the fare board's head and the monthly pass), and the ground under it is cool station marble with plain paper boards. Line colour, a letter bullet and a station ring show which module a surface belongs to. The mark is a ring of four arcs, one per line, meeting as one interchange.

Density is calm and legible rather than packed. Large Jost headings set the tone, content sits on paper boards with hairline borders, and nothing floats except the things that really lift off the map: dialogs, toasts, the replay bar, the transit-pass card and the Start-free pill. Motion is wayfinding motion. A station ring swells when it is pointed at, the station sign drops into place under its station, and a small train runs along the line to the interchange when a sign opens. All of it stops under reduced motion.

The confirmed anti-reference for this world: not a cold corporate template, and not cluttered. One region is exempt. The exam screens (`public/css/cd-ielts.css`, the split-screen test, its dialogs, contrast themes and text sizes) copy the real computer-delivered IELTS and stay outside this world on purpose. They keep their own `--cd-*` tokens and English labels. The pre-test instructions card and the site dialogs belong to this world; the exam's own dialogs do not.

**Key Characteristics:**
- Four committed line colours that carry module identity, each paired with its letter bullet (L, R, W, S).
- A granite shell and granite plaques over station-marble ground and paper boards.
- Jost (self-hosted, variable 300–800) for the network's voice; the system stack for running text and controls.
- Circles for stops and bars for lines, everywhere from the home network to FAQ markers.
- Flat at rest; shadow only on things that lift off the map.
- One four-colour band in fixed L, R, W, S order marks the header, footer and pass.
- The exam screens are exempt and keep the computer-delivered IELTS look.

## Colors

A cool granite-and-marble station palette carrying four saturated line colours, with Listening blue and amber also doing two fixed interface jobs.

### Primary
- **Polished Granite** (#142038): the shell and every plaque. Used for the header, footer, station signs, the Test day hub label, the fare-board head, the pass card, primary buttons, the active filter chip, toasts and the replay bar. Also used for the interchange capsule's stroke and the "How a test works" ride line.
- **Granite Plate** (#1d2b47): a raised plate on granite, used for the brand plate in the header, hovered nav links, the pre-test card header and the hub label on hover.
- **Granite Edge** (#2c3c5d): the engraved hairline on granite plates, the hover state of primary buttons, the borders of ghost buttons on granite, and the language switch outline.
- **Plaque Lettering** (#eef2f8): body text on granite. It is also the fill of light controls on granite (Sign in, the active language).
- **Weathered Plaque Grey** (#a9b5ca): secondary text on granite, such as nav links at rest, the hub subtitle, sign meta lines and footer copy.

### Secondary
The four lines. Each `.line-*` class sets `--line`, `--line-soft`, `--line-ink` and `--line-on` for everything inside it.
- **Listening Line Blue** (#1f5fbf), with **Listening Tint** (#e3ecf9): Listening's line, bullets and results. Outside a module it is also the link colour, the caret, the focus border on inputs and the transcript play buttons. **Deep Listening Blue** (#194f9f, `--primary-hover`) is the hover colour for links and link buttons.
- **Reading Line Red** (#cf3a2c), with **Reading Tint** (#fbe6e3): Reading's line, bullets and results. Outside a module it is the fill of the unread-count pill in the header.
- **Writing Line Green** (#1e7c42), with **Writing Tint** (#e1f1e7) and **Writing Ink** (#1a7340): Writing's line, bullets, results and the task-band pill. Writing text and tags use Writing Ink, which reads at 5.0:1 on the tint where the line colour is 4.47:1; `.line-w` sets `--line-ink` to it.
- **Speaking Line Amber** (#e3a21a), with **Speaking Tint** (#fcf0d5) and **Amber Ink** (#8a5a00): Speaking's line and bullets. Outside a module it marks the current place: the underline under the active nav link, the focus ring on granite ground, star ratings and the avatar. Speaking Tint is also the ground of answer explanations and examiner comments.

### Tertiary
State colours. Three of the four reuse a line's hex value or its ink; only Error Red is its own colour.
- **Correct Green** (#1a7340) on (#e1f1e7): correct answers, completed checks and positive deltas. It is Writing Ink, a shade deeper than the Writing line, so it reads at 5.0:1 as text on its tint.
- **Error Red** (#b8322a) on (#fbe6e3): wrong answers, form errors, danger buttons and negative deltas. It is darker than Reading red.
- **Caution Ink** (#8a5a00) on (#fcf0d5): unanswered items, pending orders and the resume row. It is the same value as Amber Ink.
- **Info Blue** (#1f5fbf) on (#e3ecf9): info notices, in-progress checks and default tags. It is the same hex as Listening.

### Neutral
- **Station Marble** (#f1f3f6): the page ground, plus inset wells such as the answer box, the instruction panel, criterion cards and stat chips.
- **Veined Marble** (#e5e9ef): the tracks of progress bars and meters, neutral badges and the spinner track.
- **Station Board White** (#ffffff): every board and card, the inside of station rings, inputs, and text on line and granite fills.
- **Grout Line** (#d4dae3): 1px card borders, 1.5px control borders and the dotted fare leader.
- **Faint Grout** (#e7ebf0): dividers inside a board (between line rows, fare rows, table rows and review rows).
- **Timetable Ink** (#141a22): headings and body text, and text set on amber.
- **Slate Ink** (#384252): secondary copy, lead paragraphs and form labels.
- **Platform Grey** (#586273): meta text, captions, table headers and empty states (5.5:1 on marble).

### Named Rules
**The Four Lines Rule.** Wherever a module appears, its line colour carries it: the bullet, the track, the station rings, the result's band circle, the progress series and the pass stripes. Set the line with `.line-l`, `.line-r`, `.line-w` or `.line-s` on an ancestor and read `var(--line)`, `var(--line-soft)`, `var(--line-ink)` and `var(--line-on)` in the component. Never pick a hex value directly.

**The Amber Ink Rule.** Speaking amber (#e3a21a) is a fill and a stroke, never text on a light ground, because it measures 2.2:1 on paper. Speaking text uses Amber Ink (#8a5a00), and anything set on an amber fill is in Timetable Ink, not white. `.line-s` already sets `--line-on` to ink and `--line-ink` to Amber Ink.

**The Granite Shell Rule.** Granite frames the site and carries plaques. Running content (passages, explanations, prose pages, results) sits on paper or marble. Granite carries plaque copy (a sign, a fare head, a pass, a toast) and the footer's small print.

## Typography

**Display Font:** Jost (self-hosted variable woff2, weights 300–800; subsets for Latin, Latin Extended and Cyrillic), falling back to the system stack.
**Body Font:** the system stack (system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif).

**Character:** Jost is a geometric Soviet-modernist sans, the lettering of a station plaque: round bowls, a single-storey a, confident at 650. The system stack does the reading and the controls, so pages stay light on mobile data and familiar in all three languages.

### Hierarchy
- **Display** (Jost 650, clamp(2rem, 1.1rem + 3vw, 3.4rem), line-height 1.04, -0.025em): the home headline only, one line at upper left.
- **Headline** (Jost 650, clamp(1.8rem, 1.3rem + 1.6vw, 2.5rem), 1.12, -0.02em): page titles (Prices, Examiners, About, Account). Results titles step down to clamp(1.6rem, 1.2rem + 1.4vw, 2.2rem).
- **Title** (Jost 650, 1.6rem, 1.2): section headings on the home and pricing pages, and the pass copy heading.
- **Plaque** (Jost 650, 1.22rem, 1.15): line names in the network. The same voice at 1.2–1.3rem sets station-sign titles, fare-board and plaque heads, account-card headings and the hub name (1.08rem).
- **Station** (Jost 600, 0.9rem, Slate Ink): station names under their rings (0.84rem on phones).
- **Numeral** (Jost 650, up to 2.7rem, line-height 1, tabular): band values, the pass price, fare prices (1.25rem), stat values and criterion bands.
- **Body** (system 400, 16px, 1.55): all running text; prose measures cap at 68–72ch.
- **Lead** (system 400, 1.08rem, Slate Ink): the one-line offer under a page headline.
- **Label** (system 650, 0.95em, 1.25): buttons, form labels (0.88–0.9em) and chips.
- **Caption** (system 400, 0.86rem, Platform Grey): line meta, network key, score notes and the footer.
- **Tag** (system 750, 0.74rem): sign tags, badges and status pills.

Weights 650 and 750 are deliberate variable-font weights. Jost renders them exactly. The system stack renders them where its font is variable and rounds them elsewhere.

### Named Rules
**The Plaque Voice Rule.** Jost speaks for the network: headings, nav links, line and station names, the hub, line-bullet letters, prices, band numerals and the avatar. Running text, buttons, form fields and tables stay in the system stack.

**The Tabular Numbers Rule.** Every band, price, count, time and score is set with `font-variant-numeric: tabular-nums`, so columns of numbers line up like a timetable.

## Layout

The site is a single column inside a 1180px container with a fluid gutter of clamp(16px, 4vw, 40px). Prose pages narrow to 860px, and pricing, account, examiners and admin use the full 1180px. The main area opens 36px below the header and closes 64px above the footer. Home sections are spaced 64px apart, results blocks 36px apart, and cards in a grid 12–16px apart. Plaques and boards inset their content 22px horizontally.

The home network is the defining layout. On desktop each line is a row in a grid with three columns: a 210px label column (the bullet, line name and meta), a flexible track, and a 270px hub column. The stations sit in a grid whose first cell is as wide as the widest free station, so "Test n" stops line up across all four lines. The four tracks curve into the Test day capsule at the right on cubic connectors drawn in an absolutely positioned SVG, landing 12px apart.

At 860px and below, the lines stay horizontal and stack. Each row puts the line's name and its Start-free pill (or a "Next: Test n" button) on one line above its stations. The connectors run right, turn a 14px corner and go down a 72px right-hand gutter side by side into the interchange below the last line. All four Start-free pills sit in the first 390×844 screen.

Breakpoints are 1020px (narrower label and hub columns; the pass and copy stack), 860px (the phone layout above, a scrolling nav row, and the ride turning vertical), 520px (line meta hidden) and 420px (smaller mark, band circle and language buttons). The examiner check layout splits in two at min-width 1000px.

### Named Rules
**The Horizontal Network Rule.** The network's four lines stay horizontal at every width. On phones they stack and turn down a right-hand gutter into the interchange; they never rotate into a vertical list. The "How a test works" ride, a separate single line, does turn vertical on phones.

## Elevation & Depth

The system is flat at rest and layered by tone. Marble ground, paper boards with a 1px Grout Line border, and granite plaques make the three levels; `--shadow` is `none`. Depth inside a plaque comes from engraved hairlines (an inset 1px Granite Edge) rather than drop shadows. Ridden stations and the "taken" key carry an inner 2px paper halo that reads as a double ring.

### Shadow Vocabulary
- **Pop** (`box-shadow: 0 18px 40px -12px rgba(20, 26, 34, 0.35), 0 2px 6px rgba(20, 26, 34, 0.08)`): anything that floats over the page, such as site dialogs, toasts, the listening replay bar, the progress chart tooltip and the sign-in callback card.
- **Pass lift** (`box-shadow: 0 24px 40px -22px rgba(20, 26, 34, 0.55)`): the transit-pass card only, a physical card lying on the page.
- **Start pill** (`box-shadow: 0 6px 14px -8px rgba(20, 26, 34, 0.55)`): the Start-free pill on each line, the one action that sits proud of the map.
- **Plaque edge** (`box-shadow: inset 0 0 0 1px #2c3c5d`): the brand plate and the hub label, an engraved rim on granite.

### Named Rules
**The Flat Station Rule.** Cards and boards never take a shadow at rest. Shadow belongs to things that lift off the map (dialogs, toasts, tooltips) and to two physical objects: the pass card and the Start-free pill.

## Shapes

The form language is the metro diagram's: circles are stops, bars are lines, and pills are the actions that ride on a line. Station rings are 30px circles with a 5px line-colour stroke and a paper centre. Line bullets are filled circles (22, 28 or 40px) holding the module letter. The band circle on results is a 132px ring with a 12px line stroke, and the interchange is a paper capsule with a 5px granite stroke. Lines are plain bars with square ends: a 10px track, 10px SVG connectors, a 6px rounded ride line, 3px connectors in stop lists, a 4px four-colour header band, a 6px footer band and 10px pass stripes.

Corners step up with size: tags 6px, nav links 8px, controls and inputs 10px, compact cards and notices 12px, the station sign 14px, cards 16px, boards (the network, the fare board, the score banner, dialogs, plaques) 18px, the pass card 20px, and pills and rings fully round. Borders are 1px on boards and 1.5px on controls.

### Named Rules
**The Stop and Line Rule.** Steps and points are drawn as stops on a line. Each item gets a ring (paper fill, line-colour or granite stroke) and a bar joins the rings. A filled ring means reached, open or chosen: a ridden station, the last stop of the ride, an open FAQ item, a good feedback block.

**The Four-Colour Band Rule.** The four line colours appear together only as one band of equal quarters in fixed order: Listening, Reading, Writing, Speaking. It marks the header's bottom edge, the top of the footer and the pass card's top; the mark bends the same order into a ring.

## Components

### Buttons
Solid, compact and quietly physical; they press down 1px on `:active`.
- **Shape:** gently rounded (10px), 1.5px border, at least 42px tall (50px large, 34px small).
- **Primary:** granite fill with white label, padding 9px 18px; the main commitment on a page (Get the pass, Sign in).
- **Line:** the line's colour with `--line-on` text; the action that starts or opens a station (Start timed test, Get the pass on a sign, the opening-soon free test). Hover darkens it to `brightness(0.92)`.
- **Secondary:** paper fill, Grout Line border, ink label; the border darkens to Slate Ink on hover. On granite it becomes a ghost with a Granite Edge border and white label.
- **Danger:** Error Red fill, deepening to #962820 on hover.
- **Link button:** Listening blue text at 650 with no box; it underlines on hover.
- **Hover / Focus:** background, border and colour ease over 0.16s. Disabled buttons drop to 0.55 opacity; a busy button hides its label behind an 18px spinner.

### Chips
- **Style:** pill (999px), 36px tall, paper fill, 1.5px Grout Line border, Slate Ink label at 650. Used for review filters, transcript parts and task jumps.
- **State:** hover darkens the border to Slate Ink; the active chip fills with granite and turns its label white.

### Tags and Badges
- **Style:** 6px corners (status pills on review cards are fully round), 0.74–0.8rem at 700–750, a soft tint with matching ink: Correct Green on its tint for correct and done, Caution Ink on Speaking Tint for waiting, Info Blue on Listening Tint for in progress and for examiner tags, Veined Marble and Platform Grey for neutral. An examiner's module tag takes its line's tint and ink. On a station sign, the Free tag takes the line's fill, "In your pass" sits on Granite Edge, and "Opens with the pass" is a hairline outline.

### Cards / Containers
- **Corner Style:** boards 18px, cards 16px, compact cards 12px.
- **Background:** paper on marble; inset wells inside a card use marble.
- **Shadow Strategy:** none (see The Flat Station Rule).
- **Border:** 1px Grout Line; Faint Grout dividers inside.
- **Internal Padding:** 22–26px on boards, 20–22px on cards, 16–18px on compact cards.

### Inputs / Fields
- **Style:** paper, 1.5px Grout Line border, 10px corners, 46–48px tall, padding 10–11px 14px, inheriting the system font at 1em.
- **Focus:** the border turns Listening blue and a 3px Listening Tint outline sits flush (offset 0).
- **Error / Disabled:** errors are Error Red text at 0.9em below the field; the six-digit code field sets 1.6em tabular digits with 0.4em tracking.

### Navigation
- **Header:** a sticky granite bar at least 68px tall, closed by a 4px four-colour band. The brand plate (mark and Jost name on Granite Plate with an engraved Granite Edge rim, 12px corners) sits at the left. Nav links are Jost 550 at 1rem in Weathered Plaque Grey, turning white on a Granite Plate wash on hover. The current page is white with a 3px amber bar under it. At the right are a segmented EN/UZ/RU switch (Granite Edge outline, the active language filled with Plaque Lettering) and a light Sign in button.
- **Phones (≤860px):** brand and tools share the first row, and the links scroll sideways as a second row under a Granite Plate hairline, fading out at the right edge.
- **Footer:** a 6px four-colour band over granite, with the mark, the independence statement in Weathered Plaque Grey at 0.86rem, and a column of Plaque Lettering links.

### Focus
The focus ring is a 3px outline at a 2px offset with 4px corners, in the colour that stands out from the ground it sits on. On marble and paper it is Granite (14.6:1 on marble). On granite ground (the header, the footer, the station sign, the pass card, the fare board's head) and inside the exam screens, whose bars are dark in every contrast theme, it is Speaking amber (7.3:1 on granite). Never put an amber ring on light ground: it measures 2.0–2.2:1 there, below the 3:1 non-text floor. A focused Start free draws the ring around the whole pill, station ring included. Inputs use their own Listening-blue focus (above).

### The Network (signature)
The home page's metro map, built on a paper board (18px).
- **Line row:** a letter bullet, a Jost line name and a caption of meta at the left. The 10px line-colour track runs to the right, and the stations sit on it. Rows are divided by Faint Grout.
- **Free station:** the first station of every line is a 32px ring with a 6px stroke and a paper halo, set inside a line-colour pill that reads "Start free →" (750, 0.92rem). The pill carries the Start-pill shadow, and its arrow nudges 3px right on hover. On phones the ring becomes a filled 34px disc, and the pill moves up beside the line name.
- **Station states:** open stations are white rings; locked stations hold a small lock in the line's ink; ridden stations grow to 44px, fill with the line colour, keep an inner paper halo and show the band inside in tabular Jost. The next station after a ridden one carries a small granite "Next" tag above it (on phones, its name gets the granite plaque instead). Hovering or opening a station scales its ring to 1.18 over 0.18s.
- **Interchange:** a paper capsule with a 5px granite stroke, sized by script to fit the four connectors (62px tall on desktop; 62px wide and 34px tall on phones). Next to it sits a granite hub plaque reading "Test day / All lines meet here".
- **Station sign:** tapping a station opens a granite plaque (14px corners, padding 18px 22px) under its line, with a 10px notch pointing at the station. It holds the bullet, a Jost title, a tag, the parts or passages with bold keys, a meta line, a pass note when locked, and the actions: a ghost secondary button and a line button. It drops in over 0.22s (fade and 6px rise). At the same time a 6px paper train with a granite rim runs from the station along the line into the interchange over 1.3s.
- **Key:** below the board, an 18px ring legend for free, locked and taken stations.

### The Ride
"How a test works" as four stops on a 6px granite line: 36px rings with 6px granite strokes. The last stop is filled with a paper halo, because it is the destination. It runs horizontally on desktop and vertically on phones.

### The Pass Card
The monthly plan as a transit card: ID-1 proportions (aspect-ratio 1.586), granite, 20px corners, the four-colour band (10px) across the top, the brand name and a small card-type legend at the top, a Jost price numeral in the middle, and a row of the four small bullets with the first-payment note at the bottom. It takes the Pass-lift shadow. The home page and the prices page share it.

### The Fare Board
Prices as a station fare board: a paper board (18px) with a granite head ("Fares" and a link). Each row has the line bullets it covers, the fare name with a caption, a 2px dotted Grout Line leader, and a Jost tabular price. A caption foot names the payment methods. On phones the bullets wrap above the name.

### Results
A results head with a large line bullet. Below it a score banner: a paper board holding the band circle (a 132px ring in the line colour with the band in a 2.7rem Jost numeral), a description, and three stats divided by 1px rules. Breakdowns use 8px marble bars filled with the line colour. Review cards are paper with a number badge (granite, Correct Green or Error Red), an answer well in marble and an explanation on Speaking Tint. Listening transcripts underline each answer with a 2px inset in its state colour.

## Do's and Don'ts

### Do:
- **Do** set module colour by putting `.line-l`, `.line-r`, `.line-w` or `.line-s` on an ancestor and reading `var(--line)`, `var(--line-soft)`, `var(--line-ink)` and `var(--line-on)` in the component.
- **Do** pair every line colour with its letter bullet (L, R, W, S) or the module name, so identity never rests on colour alone.
- **Do** keep cards and boards flat: paper (#ffffff), a 1px Grout Line border (#d4dae3), 12–18px corners.
- **Do** draw lists of steps or points as stops on a line: rings joined by a bar, filled when reached.
- **Do** show the four-colour band only in Listening, Reading, Writing, Speaking order, in equal quarters.
- **Do** set bands, prices, counts and times in tabular numerals.
- **Do** load Jost only from `public/fonts/` (CSP `font-src 'self'`). The three subsets cover English, Uzbek Latin (including oʻ and gʻ at U+02BB) and Russian.
- **Do** stop the sign drop, the train and smooth scrolling under `prefers-reduced-motion`.

### Don't:
- **Don't** carry this world into the exam screens. `cd-ielts.css` keeps the computer-delivered IELTS look, its `--cd-*` tokens, four contrast themes, three text sizes and English labels.
- **Don't** set Speaking amber (#e3a21a) as text on marble or paper; use Amber Ink (#8a5a00).
- **Don't** put a shadow on a resting card or board.
- **Don't** rotate the network's lines into a vertical list on phones.
- **Don't** put "IELTS" in the mark or the brand name. The mark is the four-arc interchange ring.
- **Don't** set running content on granite. It carries plaque copy and the footer's small print only.
