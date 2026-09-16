# IELTS Mock Exam Platform (Reading Module)

An authentic, distraction-free web platform for taking full IELTS Reading mock exams, designed to be **identical** to the official **Computer-Delivered (CD) IELTS exam** (British Council / IDP).

Includes complete, authentic Reading tests from the **3 latest Cambridge practice books**:
- **Cambridge IELTS 19 Academic** (Test 1: *How Tennis Rackets Have Changed*, *The Pirates of the Ancient Mediterranean*, *The Persistence and Peril of Misinformation*)
- **Cambridge IELTS 18 Academic** (Test 1: *Urban Farming*, *Forest Management in Pennsylvania*, *Conquering Earth's Space Junk Problem*)
- **Cambridge IELTS 17 Academic** (Test 1: *The Development of the London Underground Railway*, *Stadiums: Past, Present and Future*, *To Catch a King*)

---

## Key Features

### 1. Authentic Computer-Delivered (CD) IELTS Experience
- **Official Top Bar**: Displays candidate full name, candidate ID, test title badge, and countdown timer.
- **60:00 Countdown Timer**: Exact 60-minute countdown with:
  - **Hide/Show Time** toggle (turns into a subtle clock icon).
  - 10-minute and 5-minute remaining visual warning alerts.
  - Automatic submission upon timer expiration.
- **Interactive Highlighting & Notes**:
  - Select any text in the reading passage or questions to apply an authentic soft yellow highlighter marker.
  - Attach sticky observation notes to selections.
  - Right-click or tap highlighted text to remove highlights.
- **Resizable Split-Screen Workspace**:
  - Independent scrolling for Reading Passage (left) and Questions (right).
  - Smooth draggable vertical splitter divider to customize view width.
- **Accessibility & Display Controls**:
  - 4 Contrast Themes: Standard (Black on White), Black on Yellow, Yellow on Black, and White on Blue.
  - 3 Font Zoom Scales: Regular (100%), Large (120%), and Extra Large (140%).
  - Official Keyboard Navigation Shortcuts (`Alt+N` for Next, `Alt+P` for Previous, `Alt+R` for Review, `Tab`, `Space`).
- **Bottom Navigation Dock**:
  - Quick passage switcher: `Part 1`, `Part 2`, `Part 3`.
  - Numbered question buttons `1` to `40`.
  - Answered indicator (bottom blue underline / solid).
  - "Review" checkbox (flags marked questions with an orange corner indicator).
  - Finish Test modal displaying summary of answered vs unanswered questions.

### 2. Official IELTS Band Scoring & In-Depth Review
- Instant evaluation of all 40 questions against official Cambridge answer keys.
- Accurate IELTS Academic Reading Band Score calculation (Band 1.0 to 9.0) and CEFR proficiency mapping (B1, B2, C1, C2).
- Passage-by-passage performance breakdown with score bars.
- Question-by-question review with filters: **All**, **Correct**, **Incorrect**, and **Unanswered**.
- Explanations highlighting exact evidence quotes and paragraphs from the passage for every single question.

### 3. Distraction-Free Portal & Architecture
- Clean, focused interface with zero advertisements or distracting popups.
- Pre-test Candidate Verification screen mirroring official test-center procedures.
- Clearly marks **Listening**, **Writing**, and **Speaking** modules as **"Soon"**.
- Built with a lightweight Python backend (`server.py`) and zero-dependency modern ES6+ frontend.

---

## Quick Start

### Prerequisites
- Python 3.8+ (no npm or external build tools required)

### Launching the Application
```bash
python3 server.py
```
Or specify a custom port:
```bash
PORT=8000 python3 server.py
```

Open your browser and navigate to:
```
http://localhost:8000
```

---

## Project Structure

```
MockExam/
├── server.py              # Lightweight Python Tornado/HTTP server + REST API
├── data/
│   ├── tests.json         # Complete Cambridge 19, 18, 17 Reading test content (120 questions)
│   └── attempts.db        # SQLite database recording candidate test attempts
├── public/
│   ├── index.html         # Single-page application entry point
│   ├── css/
│   │   ├── cd-ielts.css   # Pixel-perfect CD-IELTS design system & contrast themes
│   │   └── portal.css     # Clean distraction-free dashboard and results styling
│   └── js/
│       ├── app.js         # Application controller and view router
│       ├── exam.js        # CD-IELTS exam engine (timer, splitter, navigation)
│       ├── highlighter.js # Text selection, highlighting, and sticky notes
│       └── scoring.js     # Official IELTS Academic Band score table & analytics
├── scripts/
│   └── build_tests_data.py # Generator script for Cambridge test dataset
└── README.md
```

---

## License
MIT License. Practice materials are derived from official Cambridge IELTS academic publications for educational preparation.

