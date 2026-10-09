---
version: 1
slug: "public-index-html"
primary_target: "public/index.html"
related_targets: ["public/js/app.js","public/css/portal.css"]
---

# Surface brief: TestDay home and portal

Scope: the home page (Persuade) and the portal screens that inherit its world (tests, prices, examiners, account, progress, results; Operate). The exam screens are out of scope apart from comfort fixes: they keep the computer-delivered IELTS look and English labels.

Audience and job: Uzbek IELTS candidates, mostly on phones, full tests on laptops. First action: start a free test in one or two taps, no sign-up (Listening, Reading, Writing). Proof on hand: the real tests, the prices, the feature list. No testimonials or user counts exist; none may be invented.

Constraints: plain HTML/CSS/JS, no framework, no build step; self-hosted fonts only (CSP font-src 'self'); light on mobile data. Interface in English, Uzbek and Russian with a switch.

Must not feel: a cold corporate template; cluttered.

## Direction contract

THESIS: The four IELTS modules are four metro lines that all terminate at one interchange, Test day. Every test is a station; practising is riding the line. Refuses the category's centred headline over three feature cards and a pricing table.

OWN-WORLD: Tashkent metro wayfinding. Cool station-marble ground, polished-granite navy shell for header, plaques and footer, four committed line colours (Listening blue, Reading red, Writing green, Speaking amber) doing module identity everywhere; thick round-capped line strokes, white station rings, interchange circles, line bullets with a letter. Station-name plaques in a geometric Soviet-modernist sans (Jost), UI and body in the system stack.

STORY: The visitor sees the whole network at once, understands that each module is a line with a free first station, picks a line, taps its first station and starts a free test; later the pass (monthly plan) opens every station and their ridden stations fill in with their band.

FIRST VIEWPORT: Desktop: a plaque-style header; one line of headline and a one-line offer at upper left; below it, spanning the width, the four horizontal lines with their stations, converging on the Test day interchange at the right; the free first station of each line carries a filled "Start free" control. Phone: the four lines stay horizontal and stacked, each with its name and a Start free button on one row above its stations; the lines turn down a right-hand gutter, side by side, into the Test day interchange below the last line. All four Start free buttons sit within the first screen at 390x844.

FORM: Tashkent metro wayfinding, my top-ranked grounded candidate (rank 1, chosen by the user as the pick card over the assigned security-print report); seed key 11de548f. Signature interaction: tapping a station opens its station sign (test details and Start) anchored to the station; ridden stations show the band inside the ring and a "you are here" marker sits on the next station.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
