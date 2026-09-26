/**
 * Computer-delivered exam engine.
 *
 * ExamShell     – timer, contrast/text-size controls, help, resizable split
 *                 panes, mobile pane switcher, progress autosave, leave guard.
 * ReadingExam   – renders passages and every question-group type, tracks answers.
 * ListeningExam – the same question engine in one column, driven by the
 *                 recording: plays each part once (timed test) or with full
 *                 player controls (practice), then gives time to check answers.
 * WritingExam   – renders Task 1/Task 2 prompts (with charts) and answer boxes.
 */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (v) => U.escapeHtml(v);
  const CONTRAST_THEMES = ["theme-default", "theme-black-on-yellow", "theme-yellow-on-black", "theme-white-on-blue"];
  const TEXT_SIZES = ["text-regular", "text-large", "text-extra-large"];

  function applyPreference(list, value) {
    list.forEach((c) => document.body.classList.remove(c));
    document.body.classList.add(list.includes(value) ? value : list[0]);
  }

  // Restore display preferences once at load.
  applyPreference(CONTRAST_THEMES, U.store.get("mockexam:contrast", "theme-default"));
  applyPreference(TEXT_SIZES, U.store.get("mockexam:textSize", "text-regular"));

  /* ======================================================================
     Shared shell
     ====================================================================== */
  class ExamShell {
    constructor(opts) {
      this.test = opts.test;
      this.candidateName = opts.candidateName || "Candidate";
      this.mode = opts.mode === "practice" ? "practice" : "exam";
      this.onFinish = opts.onFinish || (() => {});
      this.saved = opts.saved || null;
      this.duration = (this.test.durationMinutes || 60) * 60;
      this.elapsed = this.saved && this.saved.mode === this.mode ? this.saved.elapsed || 0 : 0;
      this.timerHidden = false;
      this.finished = false;
      this.abort = new AbortController();
      this.progressKey = `mockexam:progress:${this.test.id}`;
      this.saveTimer = null;
    }

    on(target, type, handler, options = {}) {
      target.addEventListener(type, handler, { ...options, signal: this.abort.signal });
    }

    mountShell(badge, leftLabel, rightLabel) {
      $("exam-candidate-name").textContent = this.candidateName;
      $("exam-test-title").textContent = badge;
      $("pane-switch-left").textContent = leftLabel;
      $("pane-switch-right").textContent = rightLabel;
      $("exam-pane-left").style.flex = "";
      $("exam-pane-right").style.flex = "";
      $("exam-pane-left").dataset.rendered = "";

      this.on($("btn-contrast"), "click", () => this.cycle(CONTRAST_THEMES, "mockexam:contrast"));
      this.on($("btn-text-size"), "click", () => this.cycle(TEXT_SIZES, "mockexam:textSize"));
      this.on($("btn-help"), "click", () => this.showHelp());
      this.on($("exam-timer-box"), "click", () => {
        this.timerHidden = !this.timerHidden;
        this.renderTimer();
      });
      this.on($("btn-submit-exam"), "click", () => this.confirmFinish());
      this.on(window, "beforeunload", (e) => {
        if (!this.finished) {
          this.saveProgress();
          e.preventDefault();
          e.returnValue = "";
        }
      });
      this.initSplitter();
      this.initPaneSwitch();
      this.startTimer();
    }

    cycle(list, key) {
      const idx = list.findIndex((c) => document.body.classList.contains(c));
      const next = list[(idx + 1) % list.length];
      applyPreference(list, next);
      U.store.set(key, next);
    }

    /* Timer ------------------------------------------------------------ */
    get remaining() {
      return this.duration - this.elapsed;
    }

    startTimer() {
      clearInterval(this.timer);
      this.renderTimer();
      this.timer = setInterval(() => {
        this.elapsed++;
        this.renderTimer();
        if (this.mode === "exam") {
          if (this.remaining === 600) U.toast("10 minutes remaining.", "warn");
          if (this.remaining === 300) U.toast("5 minutes remaining.", "warn");
          if (this.remaining <= 0) {
            clearInterval(this.timer);
            U.toast("Time is up. Your answers are being submitted.", "warn");
            this.submit();
            return;
          }
        }
        if (this.elapsed % 10 === 0) this.saveProgress();
      }, 1000);
    }

    renderTimer() {
      const box = $("exam-timer-box");
      const text = $("exam-timer-text");
      if (this.timerHidden) {
        text.textContent = "Show time";
        box.classList.remove("warning");
        return;
      }
      if (this.mode === "exam") {
        text.textContent = `${U.formatClock(this.remaining)} left`;
        box.classList.toggle("warning", this.remaining <= 600);
      } else {
        text.textContent = `Practice · ${U.formatClock(this.elapsed)}`;
        box.classList.remove("warning");
      }
    }

    /* Layout ----------------------------------------------------------- */
    initSplitter() {
      const resizer = $("exam-resizer");
      const left = $("exam-pane-left");
      const right = $("exam-pane-right");
      const ws = $("exam-workspace");
      let dragging = false;

      this.on(resizer, "pointerdown", (e) => {
        dragging = true;
        resizer.setPointerCapture(e.pointerId);
        resizer.classList.add("is-dragging");
        document.body.style.userSelect = "none";
      });
      this.on(resizer, "pointermove", (e) => {
        if (!dragging) return;
        const rect = ws.getBoundingClientRect();
        const x = e.clientX - rect.left;
        if (x < 260 || x > rect.width - 260) return;
        left.style.flex = `0 0 ${(x / rect.width) * 100}%`;
        right.style.flex = "1 1 0";
      });
      const stop = () => {
        dragging = false;
        resizer.classList.remove("is-dragging");
        document.body.style.userSelect = "";
      };
      this.on(resizer, "pointerup", stop);
      this.on(resizer, "pointercancel", stop);
    }

    initPaneSwitch() {
      const ws = $("exam-workspace");
      ws.classList.remove("show-right");
      document.querySelectorAll(".pane-switch-btn").forEach((btn) => {
        const isLeft = btn.dataset.pane === "left";
        btn.classList.toggle("active", isLeft);
        btn.setAttribute("aria-selected", String(isLeft));
        this.on(btn, "click", () => this.showPane(btn.dataset.pane));
      });
    }

    showPane(which) {
      $("exam-workspace").classList.toggle("show-right", which === "right");
      document.querySelectorAll(".pane-switch-btn").forEach((b) => {
        const active = b.dataset.pane === which;
        b.classList.toggle("active", active);
        b.setAttribute("aria-selected", String(active));
      });
    }

    showHelp() {
      U.modal({
        title: "Help",
        bodyHTML: this.helpHTML(),
        buttons: [{ label: "Close", className: "btn-primary", value: true }],
      });
    }

    helpHTML() {
      return `
        <p><strong>Tools</strong></p>
        <ul class="help-list">
          <li><strong>Timer:</strong> click the clock to hide or show it.</li>
          <li><strong>Contrast / Text size:</strong> change the colours and font size of the test.</li>
          <li><strong>Resize:</strong> drag the bar between the two panels.</li>
        </ul>`;
    }

    /* Progress autosave (per browser) ----------------------------------- */
    saveProgress() {
      if (this.finished) return;
      U.store.set(this.progressKey, { ...this.progressData(), elapsed: this.elapsed, mode: this.mode, savedAt: Date.now() });
    }

    saveProgressSoon() {
      clearTimeout(this.saveTimer);
      this.saveTimer = setTimeout(() => this.saveProgress(), 400);
    }

    clearProgress() {
      U.store.remove(this.progressKey);
    }

    resumeTimerAfterFailedSubmit() {
      this.finished = false;
      if (this.mode === "practice" || this.remaining > 0) this.startTimer();
    }

    destroy() {
      clearInterval(this.timer);
      clearTimeout(this.saveTimer);
      this.abort.abort();
      if (this.highlighter) this.highlighter.destroy();
      $("exam-pane-left").innerHTML = "";
      $("exam-pane-right").innerHTML = "";
      $("exam-pane-left").dataset.rendered = "";
      $("exam-part-tabs").innerHTML = "";
      $("exam-question-strip").innerHTML = "";
      document.querySelectorAll(".toast").forEach((t) => t.remove());
    }
  }

  /* ======================================================================
     Reading
     ====================================================================== */
  class ReadingExam extends ExamShell {
    constructor(opts) {
      super(opts);
      this.answers = (this.saved && this.saved.answers) || {};
      this.flagged = new Set((this.saved && this.saved.flagged) || []);
      this.passageIdx = 0;
      this.current = null;
      this.passageCache = {};
      this.qToPassage = {};
      this.numbers = [];
      // Reading passages or listening parts: both hold question groups.
      this.sections = this.test.passages || this.test.parts || [];
      this.sections.forEach((p, i) =>
        p.groups.forEach((g) =>
          g.questions.forEach((q) => {
            this.qToPassage[q.number] = i;
            this.numbers.push(q.number);
          })
        )
      );
      this.numbers.sort((a, b) => a - b);
      this.mount();
    }

    mount() {
      this.mountShell(`${this.test.shortTitle || this.test.title} · Reading`, "Passage", "Questions");
      $("exam-question-strip").hidden = false;
      $("exam-review-wrap").hidden = false;
      this.highlighter = new CdHighlighter("exam-workspace");
      this.bindReading();
      this.renderPassage(0);
      this.renderStrip();
      this.renderPartTabs();
      this.setCurrent(this.numbers[0], false);
    }

    helpHTML() {
      return `
        <p><strong>Answering</strong></p>
        <ul class="help-list">
          <li>Click an option, choose from a drop-down list, or type into a gap.</li>
          <li>Use the numbered buttons at the bottom to jump to any question.
            An underlined number means you have answered it.</li>
          <li>Tick <strong>Review</strong> to flag a question you want to come back to.</li>
        </ul>
        <p><strong>Highlighting</strong></p>
        <ul class="help-list">
          <li>Select text in the passage, then choose <em>Highlight</em> or <em>Note</em>.</li>
          <li>Click or tap a highlight to <em>remove</em> it, add or edit a note, or <em>clear all</em> highlights.</li>
          <li>To remove several highlights at once, select the text and choose <em>Clear</em>.</li>
        </ul>
        <p><strong>Keyboard shortcuts</strong></p>
        <ul class="help-list">
          <li><kbd>Alt</kbd> + <kbd>N</kbd> next question · <kbd>Alt</kbd> + <kbd>P</kbd> previous question</li>
          <li><kbd>Alt</kbd> + <kbd>R</kbd> mark the current question for review</li>
        </ul>
        ${super.helpHTML()}`;
    }

    progressData() {
      return { answers: this.answers, flagged: [...this.flagged] };
    }

    /* Events ----------------------------------------------------------- */
    bindReading() {
      const rp = $("exam-pane-right");

      this.on(rp, "click", (e) => {
        const item = e.target.closest("[data-qnums]");
        if (item) this.setCurrent(Number(item.dataset.qnums.split(" ")[0]), false);
        const btn = e.target.closest(".tfng-btn");
        if (btn) {
          this.setAnswer(Number(btn.dataset.q), btn.dataset.value);
          this.syncChoiceUI(Number(btn.dataset.q));
        }
      });

      this.on(rp, "change", (e) => {
        const t = e.target;
        if (t.matches("input[type=radio][data-q]")) {
          this.setAnswer(Number(t.dataset.q), t.value);
          this.syncChoiceUI(Number(t.dataset.q));
        } else if (t.matches("input[type=checkbox][data-group]")) {
          this.onMultiChange(t);
        } else if (t.matches("select[data-q]")) {
          this.setAnswer(Number(t.dataset.q), t.value);
          t.classList.toggle("has-value", Boolean(t.value));
        }
      });

      this.on(rp, "input", (e) => {
        const t = e.target;
        if (t.matches("input.gap-input[data-q]")) {
          const v = t.value.trim();
          this.setAnswer(Number(t.dataset.q), v);
          t.classList.toggle("has-value", Boolean(v));
        }
      });

      this.on(rp, "focusin", (e) => {
        const el = e.target.closest("[data-qnums]");
        if (el) this.setCurrent(Number(el.dataset.qnums.split(" ")[0]), false);
      });

      this.on($("exam-question-strip"), "click", (e) => {
        const b = e.target.closest(".q-nav-btn");
        if (b) this.goTo(Number(b.dataset.q));
      });

      this.on($("exam-part-tabs"), "click", (e) => {
        const b = e.target.closest(".part-tab-btn");
        if (!b) return;
        const idx = Number(b.dataset.p);
        const first = this.numbers.find((n) => this.qToPassage[n] === idx);
        this.setCurrent(first, true);
        this.showPane("left");
      });

      this.on($("btn-prev-q"), "click", () => this.step(-1));
      this.on($("btn-next-q"), "click", () => this.step(1));
      this.on($("exam-review-check"), "change", (e) => this.toggleFlag(this.current, e.target.checked));

      this.on(document, "keydown", (e) => {
        if (!e.altKey || e.target.tagName === "TEXTAREA") return;
        const k = e.key.toLowerCase();
        if (k === "n" || e.code === "KeyN") { e.preventDefault(); this.step(1); }
        else if (k === "p" || e.code === "KeyP") { e.preventDefault(); this.step(-1); }
        else if (k === "r" || e.code === "KeyR") {
          e.preventDefault();
          const box = $("exam-review-check");
          box.checked = !box.checked;
          this.toggleFlag(this.current, box.checked);
        }
      });
    }

    onMultiChange(cb) {
      const group = cb.dataset.group;
      const nums = group.split(" ").map(Number);
      const boxes = [...$("exam-pane-right").querySelectorAll(`input[data-group="${group}"]`)];
      const chosen = boxes.filter((b) => b.checked).map((b) => b.value);
      if (chosen.length > nums.length) {
        cb.checked = false;
        U.toast(`Choose ${nums.length === 2 ? "TWO" : nums.length} letters only.`, "warn");
        return;
      }
      chosen.sort();
      nums.forEach((n, i) => {
        if (chosen[i]) this.answers[n] = chosen[i];
        else delete this.answers[n];
        this.updatePill(n);
      });
      boxes.forEach((b) => b.closest(".option-item").classList.toggle("selected", b.checked));
      this.renderPartTabs();
      this.saveProgressSoon();
    }

    setAnswer(n, value) {
      if (value) this.answers[n] = value;
      else delete this.answers[n];
      this.updatePill(n);
      this.renderPartTabs();
      this.saveProgressSoon();
    }

    syncChoiceUI(n) {
      const rp = $("exam-pane-right");
      rp.querySelectorAll(`.tfng-btn[data-q="${n}"]`).forEach((b) => {
        const on = b.dataset.value === this.answers[n];
        b.classList.toggle("active", on);
        b.setAttribute("aria-pressed", String(on));
      });
      rp.querySelectorAll(`input[type=radio][data-q="${n}"]`).forEach((r) => {
        const option = r.closest(".option-item");
        if (option) option.classList.toggle("selected", r.checked);
      });
      const row = rp.querySelector(`.map-grid-row[data-qnums="${n}"]`);
      if (row) row.classList.toggle("has-value", Boolean(this.answers[n]));
    }

    toggleFlag(n, on) {
      if (on) this.flagged.add(n);
      else this.flagged.delete(n);
      this.updatePill(n);
      this.saveProgressSoon();
    }

    /* Navigation ------------------------------------------------------- */
    step(delta) {
      const i = this.numbers.indexOf(this.current);
      const next = this.numbers[i + delta];
      if (next !== undefined) this.goTo(next);
    }

    goTo(n) {
      this.setCurrent(n, true);
      this.showPane("right");
      const el = this.questionEl(n);
      const input = el && el.querySelector("input:not([type=checkbox]):not([type=radio]), select");
      if (input && el.classList.contains("gap")) input.focus({ preventScroll: true });
    }

    questionEl(n) {
      return $("exam-pane-right").querySelector(`[data-qnums~="${n}"]`);
    }

    setCurrent(n, scroll) {
      if (n === undefined || n === null) return;
      this.current = n;
      const pIdx = this.qToPassage[n];
      if (pIdx !== this.passageIdx || $("exam-pane-left").dataset.rendered !== "1") {
        this.renderPassage(pIdx);
        this.renderPartTabs();
      }
      $("exam-question-strip").querySelectorAll(".q-nav-btn").forEach((b) => {
        const on = Number(b.dataset.q) === n;
        b.classList.toggle("current", on);
        if (on) b.scrollIntoView({ block: "nearest", inline: "nearest" });
      });
      const rp = $("exam-pane-right");
      rp.querySelectorAll(".active-question").forEach((el) => el.classList.remove("active-question"));
      const el = this.questionEl(n);
      if (el) {
        el.classList.add("active-question");
        if (scroll) el.scrollIntoView({ block: "center", behavior: "smooth" });
      }
      $("exam-review-check").checked = this.flagged.has(n);
      $("btn-prev-q").disabled = n === this.numbers[0];
      $("btn-next-q").disabled = n === this.numbers[this.numbers.length - 1];
    }

    /* Footer ----------------------------------------------------------- */
    renderStrip() {
      $("exam-question-strip").innerHTML = this.numbers
        .map((n) => `<button type="button" class="q-nav-btn" data-q="${n}" aria-label="Question ${n}">${n}</button>`)
        .join("");
      this.numbers.forEach((n) => this.updatePill(n));
    }

    updatePill(n) {
      const b = $("exam-question-strip").querySelector(`.q-nav-btn[data-q="${n}"]`);
      if (!b) return;
      b.classList.toggle("answered", Boolean(this.answers[n]));
      b.classList.toggle("flagged", this.flagged.has(n));
      b.classList.toggle("in-part", this.qToPassage[n] === this.passageIdx);
    }

    renderPartTabs() {
      $("exam-part-tabs").innerHTML = this.sections
        .map((p, i) => {
          const nums = this.numbers.filter((n) => this.qToPassage[n] === i);
          const done = nums.filter((n) => this.answers[n]).length;
          return `<button type="button" class="part-tab-btn ${i === this.passageIdx ? "active" : ""}" data-p="${i}">
            Part ${p.passageNumber || p.partNumber} <span class="part-count">${done} of ${nums.length}</span></button>`;
        })
        .join("");
      this.numbers.forEach((n) => {
        const b = $("exam-question-strip").querySelector(`.q-nav-btn[data-q="${n}"]`);
        if (b) b.classList.toggle("in-part", this.qToPassage[n] === this.passageIdx);
      });
    }

    /* Rendering -------------------------------------------------------- */
    renderPassage(idx) {
      const left = $("exam-pane-left");
      if (left.dataset.rendered === "1") this.passageCache[this.passageIdx] = left.innerHTML;
      if (this.highlighter) {
        this.highlighter.hideMenu();
        this.highlighter.closeNotes();
      }
      this.passageIdx = idx;
      const p = this.sections[idx];
      left.innerHTML = this.passageCache[idx] || this.passageHTML(p);
      left.dataset.rendered = "1";
      left.scrollTop = 0;
      const right = $("exam-pane-right");
      right.innerHTML = `<div class="questions-container">${p.groups.map((g) => this.groupHTML(g, p)).join("")}</div>`;
      right.scrollTop = 0;
    }

    passageHTML(p) {
      const nums = this.numbers.filter((n) => this.qToPassage[n] === this.sections.indexOf(p));
      return `
        <div class="passage-header">
          <div class="passage-part-label">Reading Passage ${p.passageNumber}</div>
          <h2 class="passage-title">${esc(p.title)}</h2>
          ${p.subtitle ? `<div class="passage-subtitle">${esc(p.subtitle)}</div>` : ""}
        </div>
        <div class="passage-instruction-bar">
          You should spend about 20 minutes on <strong>Questions ${nums[0]}–${nums[nums.length - 1]}</strong>,
          which are based on Reading Passage ${p.passageNumber}.
        </div>
        <div class="passage-body">
          ${p.paragraphs.map((para) => `
            <p class="passage-paragraph">${para.label ? `<span class="paragraph-label">${esc(para.label)}</span>` : ""}${esc(para.text)}</p>`).join("")}
        </div>`;
    }

    groupHTML(g, p) {
      const nums = g.questions.map((q) => q.number);
      const range = nums.length > 1 ? `${nums[0]}–${nums[nums.length - 1]}` : `${nums[0]}`;
      return `
        <section class="q-group" data-type="${esc(g.type)}">
          <div class="question-group-header">
            <div class="question-group-title">Questions ${range}</div>
            <div class="question-group-instruction">${U.richText(g.instruction)}</div>
          </div>
          ${this.groupBody(g, p)}
        </section>`;
    }

    groupBody(g, p) {
      switch (g.type) {
        case "true_false_not_given":
        case "yes_no_not_given":
          return this.tfngHTML(g);
        case "multiple_choice":
          return g.questions.map((q) => this.mcqHTML(q)).join("");
        case "choose_multiple":
          return this.chooseMultipleHTML(g);
        case "matching_headings":
        case "matching_information":
        case "matching_features":
        case "matching_sentence_endings":
        case "classification":
          return this.matchingHTML(g, p);
        case "map_labelling":
          return this.mapHTML(g);
        case "note_completion":
          return this.notesHTML(g);
        case "summary_completion":
          return this.summaryHTML(g);
        case "table_completion":
          return this.tableHTML(g);
        case "flow_chart_completion":
          return this.flowHTML(g);
        case "sentence_completion":
          return g.questions.map((q) => `<div class="question-card q-sentence">${this.fill(q.prompt, g)}</div>`).join("");
        case "short_answer":
          return g.questions.map((q) => this.shortAnswerHTML(q)).join("");
        default:
          return "";
      }
    }

    badge(n) {
      return `<span class="question-number-badge">${n}</span>`;
    }

    tfngHTML(g) {
      const opts = g.type === "true_false_not_given" ? ["TRUE", "FALSE", "NOT GIVEN"] : ["YES", "NO", "NOT GIVEN"];
      return g.questions.map((q) => {
        const ans = this.answers[q.number];
        return `
          <div class="question-card" data-qnums="${q.number}">
            <div class="q-line">${this.badge(q.number)}<span class="question-prompt">${esc(q.prompt)}</span></div>
            <div class="tfng-buttons" role="group" aria-label="Question ${q.number}">
              ${opts.map((o) => `<button type="button" class="tfng-btn ${ans === o ? "active" : ""}" aria-pressed="${ans === o}" data-q="${q.number}" data-value="${o}">${o}</button>`).join("")}
            </div>
          </div>`;
      }).join("");
    }

    mcqHTML(q) {
      const ans = this.answers[q.number];
      return `
        <div class="question-card" data-qnums="${q.number}">
          <div class="q-line">${this.badge(q.number)}<span class="question-prompt">${esc(q.prompt)}</span></div>
          <div class="options-list" role="radiogroup" aria-label="Question ${q.number}">
            ${q.options.map((o) => `
              <label class="option-item ${ans === o.key ? "selected" : ""}">
                <input type="radio" name="q${q.number}" value="${esc(o.key)}" data-q="${q.number}" ${ans === o.key ? "checked" : ""} />
                <span class="opt-key">${esc(o.key)}</span><span>${esc(o.text)}</span>
              </label>`).join("")}
          </div>
        </div>`;
    }

    chooseMultipleHTML(g) {
      const nums = g.questions.map((q) => q.number);
      const chosen = nums.map((n) => this.answers[n]).filter(Boolean);
      const group = nums.join(" ");
      return `
        <div class="question-card" data-qnums="${group}">
          <div class="q-line">${this.badge(`${nums[0]}–${nums[nums.length - 1]}`)}<span class="question-prompt">${esc(g.prompt)}</span></div>
          <div class="options-list" role="group" aria-label="Questions ${nums.join(" and ")}">
            ${g.options.map((o) => `
              <label class="option-item ${chosen.includes(o.key) ? "selected" : ""}">
                <input type="checkbox" value="${esc(o.key)}" data-group="${group}" ${chosen.includes(o.key) ? "checked" : ""} />
                <span class="opt-key">${esc(o.key)}</span><span>${esc(o.text)}</span>
              </label>`).join("")}
          </div>
        </div>`;
    }

    optionsBox(g) {
      if (!g.options) return "";
      return `
        <div class="options-box">
          <div class="options-box-title">${esc(g.optionsTitle || "Options")}</div>
          <ul>${g.options.map((o) => `<li><span class="opt-key">${esc(o.key)}</span><span>${esc(o.text)}</span></li>`).join("")}</ul>
        </div>`;
    }

    matchingHTML(g, p) {
      const keys = g.options ? g.options.map((o) => o.key) : p.paragraphs.map((x) => x.label).filter(Boolean);
      const items = g.questions.map((q) => {
        const ans = this.answers[q.number] || "";
        return `
          <div class="question-card q-matching" data-qnums="${q.number}">
            <div class="q-line">${this.badge(q.number)}<span class="question-prompt">${esc(q.prompt)}</span></div>
            <select class="matching-select ${ans ? "has-value" : ""}" data-q="${q.number}" aria-label="Answer for question ${q.number}">
              <option value="">Choose…</option>
              ${keys.map((k) => `<option value="${esc(k)}" ${ans === k ? "selected" : ""}>${esc(k)}</option>`).join("")}
            </select>
          </div>`;
      }).join("");
      return this.optionsBox(g) + items;
    }

    /** Map/plan labelling: the map, then a grid with one row per question and one radio per letter. */
    mapHTML(g) {
      const letters = g.options.map((o) => o.key);
      const rows = g.questions.map((q) => {
        const ans = this.answers[q.number] || "";
        return `
          <tr class="map-grid-row ${ans ? "has-value" : ""}" data-qnums="${q.number}">
            <th scope="row"><span class="q-line">${this.badge(q.number)}<span class="question-prompt">${esc(q.prompt)}</span></span></th>
            ${letters.map((l) => `
              <td><input type="radio" name="q${q.number}" value="${esc(l)}" data-q="${q.number}" ${ans === l ? "checked" : ""}
                aria-label="Question ${q.number}, ${esc(q.prompt)}: ${esc(l)}" /></td>`).join("")}
          </tr>`;
      }).join("");
      return `
        <div class="map-layout">
          ${TaskCharts.renderMap(g.map)}
          <div class="table-scroll"><table class="map-grid">
            <thead><tr><th scope="col"><span class="sr-only">Place</span></th>${letters.map((l) => `<th scope="col">${esc(l)}</th>`).join("")}</tr></thead>
            <tbody>${rows}</tbody>
          </table></div>
        </div>`;
    }

    gapHTML(n, g) {
      const val = this.answers[n] || "";
      if (g.options) {
        return `<span class="gap" data-qnums="${n}"><select class="gap-select ${val ? "has-value" : ""}" data-q="${n}" aria-label="Question ${n}">
          <option value="">${n}</option>
          ${g.options.map((o) => `<option value="${esc(o.key)}" ${val === o.key ? "selected" : ""}>${esc(o.key)}</option>`).join("")}
        </select></span>`;
      }
      return `<span class="gap" data-qnums="${n}"><input type="text" class="gap-input ${val ? "has-value" : ""}" data-q="${n}"
        value="${esc(val)}" placeholder="${n}" aria-label="Question ${n}" autocomplete="off" autocapitalize="off" spellcheck="false" maxlength="60" /></span>`;
    }

    fill(text, g) {
      return U.richText(text).replace(/\{\{(\d+)\}\}/g, (_, n) => this.gapHTML(Number(n), g));
    }

    notesHTML(g) {
      let html = `<div class="notes-box">${g.title ? `<h4 class="box-title">${esc(g.title)}</h4>` : ""}`;
      let open = false;
      g.content.forEach((line) => {
        if (line.startsWith("• ")) {
          if (!open) { html += "<ul>"; open = true; }
          html += `<li>${this.fill(line.slice(2), g)}</li>`;
          return;
        }
        if (open) { html += "</ul>"; open = false; }
        html += line.startsWith("## ") ? `<h5>${esc(line.slice(3))}</h5>` : `<p>${this.fill(line, g)}</p>`;
      });
      if (open) html += "</ul>";
      return html + "</div>";
    }

    summaryHTML(g) {
      return `
        <div class="notes-box summary-box">
          ${g.title ? `<h4 class="box-title">${esc(g.title)}</h4>` : ""}
          <p>${this.fill(g.content, g)}</p>
        </div>
        ${this.optionsBox(g)}`;
    }

    tableHTML(g) {
      const c = g.content;
      return `
        <div class="notes-box">
          ${g.title ? `<h4 class="box-title">${esc(g.title)}</h4>` : ""}
          <div class="table-scroll"><table class="q-table">
            <thead><tr>${c.headers.map((h) => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead>
            <tbody>${c.rows.map((r) => `<tr>${r.map((cell) => `<td>${this.fill(cell, g)}</td>`).join("")}</tr>`).join("")}</tbody>
          </table></div>
        </div>
        ${this.optionsBox(g)}`;
    }

    flowHTML(g) {
      return `
        <div class="notes-box">
          ${g.title ? `<h4 class="box-title">${esc(g.title)}</h4>` : ""}
          <ol class="flow-steps">${g.content.map((s) => `<li>${this.fill(s, g)}</li>`).join("")}</ol>
        </div>
        ${this.optionsBox(g)}`;
    }

    shortAnswerHTML(q) {
      const val = this.answers[q.number] || "";
      return `
        <div class="question-card" data-qnums="${q.number}">
          <div class="q-line">${this.badge(q.number)}<span class="question-prompt">${esc(q.prompt)}</span></div>
          <input type="text" class="gap-input short-input ${val ? "has-value" : ""}" data-q="${q.number}" value="${esc(val)}"
            aria-label="Answer for question ${q.number}" autocomplete="off" autocapitalize="off" spellcheck="false" maxlength="60" />
        </div>`;
    }

    /* Finish ----------------------------------------------------------- */
    get moduleName() {
      return "Reading";
    }

    /** Extra warning shown in the finish dialog (used by Listening while the recording plays). */
    finishWarning() {
      return "";
    }

    async confirmFinish() {
      const answered = this.numbers.filter((n) => this.answers[n]).length;
      const unanswered = this.numbers.length - answered;
      const flagged = this.flagged.size;
      const ok = await U.modal({
        title: `Finish the ${this.moduleName} test?`,
        bodyHTML: `
          <div class="summary-rows">
            <div><span>Answered</span><strong>${answered} of ${this.numbers.length}</strong></div>
            <div class="${unanswered ? "is-warn" : ""}"><span>Unanswered</span><strong>${unanswered}</strong></div>
            <div><span>Marked for review</span><strong>${flagged}</strong></div>
          </div>
          ${this.finishWarning()}
          ${unanswered ? `<p class="warn-text">Unanswered questions are marked as incorrect. There is no penalty for guessing.</p>` : ""}`,
        buttons: [
          { label: "Return to test", className: "btn-secondary", value: false },
          { label: "Submit answers", className: "btn-danger", value: true },
        ],
      });
      if (ok) this.submit();
    }

    async submit() {
      if (this.finished) return;
      this.finished = true;
      clearInterval(this.timer);
      const done = U.loadingOverlay("Marking your answers…", "Calculating your estimated band score.");
      try {
        const result = await U.api(`/api/${this.moduleName.toLowerCase()}/${encodeURIComponent(this.test.id)}/submit`, {
          method: "POST",
          body: JSON.stringify({
            answers: this.answers,
            candidateName: this.candidateName,
            clientId: U.clientId(),
            mode: this.mode,
            timeSpentSeconds: this.elapsed,
          }),
        });
        this.clearProgress();
        done();
        this.onFinish(result);
      } catch (err) {
        done();
        this.saveProgress();
        this.resumeTimerAfterFailedSubmit();
        U.modal({
          title: "Could not submit",
          bodyHTML: `<p>${esc(err.message)}</p><p>Your answers are saved in this browser. Check your connection and press <strong>Finish test</strong> again.</p>`,
        });
      }
    }
  }

  /* ======================================================================
     Listening
     ====================================================================== */
  const ICONS = {
    play: `<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>`,
    pause: `<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M7 5h4v14H7zM13 5h4v14h-4z" fill="currentColor"/></svg>`,
    volume: `<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor"/>
      <path d="M16 8.5a4.5 4.5 0 0 1 0 7M18.5 6a8 8 0 0 1 0 12" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round"/></svg>`,
  };
  const RATES = [0.75, 0.9, 1, 1.1, 1.25];

  class ListeningExam extends ReadingExam {
    // ReadingExam's constructor calls mount(), so every listening field is initialised here.
    mount() {
      const saved = this.saved && this.saved.mode === this.mode ? this.saved : null;
      this.parts = this.test.parts;
      this.checkSeconds = Math.round((this.test.checkMinutes || 2) * 60);
      this.audioPart = saved && saved.audioPart >= 0 && saved.audioPart < this.parts.length ? saved.audioPart : 0;
      // On resume, go back a couple of seconds so the sentence that was cut off is heard again.
      this.resumeAt = saved && saved.audioTime ? Math.max(0, saved.audioTime - 2) : 0;
      this.phase = saved && saved.phase === "checking" && this.mode === "exam" ? "checking" : "listening";
      this.checkLeft = this.phase === "checking" ? Math.max(5, saved.checkLeft || 0) : this.checkSeconds;
      this.volume = Math.min(1, Math.max(0, Number(U.store.get("mockexam:volume", 0.8)) || 0));
      this.rate = 1;
      this.audioState = "loading"; // loading | playing | paused | blocked | error | ended

      $("exam-screen").classList.add("listening-mode");
      this.mountShell(`${this.test.shortTitle || this.test.title} · Listening`, "Questions", "Questions");
      $("exam-question-strip").hidden = false;
      $("exam-review-wrap").hidden = false;
      this.highlighter = new CdHighlighter("exam-pane-right");
      this.bindReading();
      this.renderAudioBar();
      this.renderPassage(this.audioPart);
      this.renderStrip();
      this.renderPartTabs();
      this.setCurrent(this.firstQuestion(this.audioPart), false);
      this.startAudio();
    }

    get moduleName() {
      return "Listening";
    }

    firstQuestion(partIdx) {
      return this.numbers.find((n) => this.qToPassage[n] === partIdx);
    }

    helpHTML() {
      const minutes = this.checkSeconds / 60;
      return `
        <p><strong>The recording</strong></p>
        <ul class="help-list">
          ${this.mode === "exam"
            ? `<li>The recording plays once, from start to finish, as in the real test. You cannot pause or replay it.</li>
               <li>Before each part you have time to read the questions. When the recording ends you have
                 ${minutes} minutes to check your answers, then they are submitted automatically.</li>`
            : `<li>Use the player to pause, go back or forward 10 seconds, choose a part, or slow the recording down.</li>`}
          <li>Change the volume with the slider in the audio bar.</li>
          <li>When a new part starts, its questions are shown. Use the <strong>Part</strong> buttons to go back to earlier questions at any time.</li>
        </ul>
        <p><strong>Answering</strong></p>
        <ul class="help-list">
          <li>Type into a gap, click an option, or choose a letter. Spelling counts.</li>
          <li>Use the numbered buttons at the bottom to jump to any question; tick <strong>Review</strong> to flag one.</li>
          <li><kbd>Alt</kbd> + <kbd>N</kbd> next question · <kbd>Alt</kbd> + <kbd>P</kbd> previous · <kbd>Alt</kbd> + <kbd>R</kbd> review</li>
        </ul>
        <p><strong>Tools</strong></p>
        <ul class="help-list">
          <li><strong>Timer:</strong> click the clock to hide or show it.</li>
          <li><strong>Contrast / Text size:</strong> change the colours and font size of the test.</li>
          <li>Select text in a question to highlight it.</li>
        </ul>`;
    }

    progressData() {
      return {
        answers: this.answers,
        flagged: [...this.flagged],
        audioPart: this.audioPart,
        audioTime: this.audio ? this.audio.currentTime || 0 : this.resumeAt,
        phase: this.phase,
        checkLeft: this.checkLeft,
      };
    }

    /* Questions: one column, one part at a time --------------------------- */
    renderPassage(idx) {
      if (this.highlighter) {
        this.highlighter.hideMenu();
        this.highlighter.closeNotes();
      }
      this.passageIdx = idx;
      $("exam-pane-left").dataset.rendered = "1";
      const p = this.sections[idx];
      const nums = this.numbers.filter((n) => this.qToPassage[n] === idx);
      const right = $("exam-pane-right");
      right.innerHTML = `
        <div class="questions-container listening-questions">
          <div class="passage-header listening-part-head">
            <div class="passage-part-label">Part ${p.partNumber}</div>
            <div class="listening-part-questions">Questions ${nums[0]}–${nums[nums.length - 1]}</div>
          </div>
          ${p.groups.map((g) => this.groupHTML(g, p)).join("")}
        </div>`;
      right.scrollTop = 0;
    }

    renderPartTabs() {
      super.renderPartTabs();
      if (!this.parts || this.phase !== "listening" || this.audioState === "ended") return;
      const tab = $("exam-part-tabs").querySelector(`.part-tab-btn[data-p="${this.audioPart}"]`);
      if (tab) {
        tab.classList.add("is-playing");
        tab.title = "The recording is playing this part";
      }
    }

    /* Audio ----------------------------------------------------------------- */
    renderAudioBar() {
      const bar = $("exam-audio-bar");
      const practice = this.mode === "practice";
      bar.hidden = false;
      bar.classList.toggle("is-checking", this.phase === "checking");
      bar.innerHTML = `
        <div class="audio-bar-inner ${practice ? "is-practice" : "is-exam"}">
          ${practice ? `
            <button type="button" class="audio-btn audio-play" id="audio-play" aria-label="Play">${ICONS.play}</button>
            <button type="button" class="audio-btn" id="audio-back" title="Back 10 seconds" aria-label="Back 10 seconds">−10s</button>
            <button type="button" class="audio-btn" id="audio-fwd" title="Forward 10 seconds" aria-label="Forward 10 seconds">+10s</button>
            <select class="audio-select" id="audio-part" aria-label="Part of the recording">
              ${this.parts.map((p, i) => `<option value="${i}">Part ${p.partNumber}</option>`).join("")}
            </select>`
            : `<span class="audio-live-dot" aria-hidden="true"></span>`}
          <span class="audio-status" id="audio-status" aria-live="polite"></span>
          ${practice
            ? `<input type="range" class="audio-seek" id="audio-seek" min="0" max="1" step="0.1" value="0" aria-label="Position in the recording" />`
            : `<div class="audio-track" aria-hidden="true"><div class="audio-track-fill" id="audio-track-fill"></div></div>`}
          <span class="audio-time" id="audio-time"></span>
          ${practice ? `
            <select class="audio-select" id="audio-rate" aria-label="Playback speed" title="Playback speed">
              ${RATES.map((r) => `<option value="${r}" ${r === 1 ? "selected" : ""}>${r}×</option>`).join("")}
            </select>` : ""}
          <label class="audio-volume" title="Volume">${ICONS.volume}<span class="sr-only">Volume</span>
            <input type="range" id="audio-volume" min="0" max="100" step="5" value="${Math.round(this.volume * 100)}" /></label>
          <button type="button" class="audio-start-btn" id="audio-start" hidden></button>
        </div>`;

      const audio = document.createElement("audio");
      audio.id = "exam-audio";
      audio.preload = "auto";
      audio.volume = this.volume;
      bar.appendChild(audio);
      this.audio = audio;

      this.on(audio, "timeupdate", () => this.updateAudioUI());
      this.on(audio, "loadedmetadata", () => this.updateAudioUI());
      this.on(audio, "playing", () => this.setAudioState("playing"));
      this.on(audio, "waiting", () => this.setAudioState("loading"));
      this.on(audio, "pause", () => {
        if (!audio.ended && this.audioState !== "blocked") this.setAudioState("paused");
      });
      this.on(audio, "ended", () => this.onPartEnded());
      this.on(audio, "error", () => {
        if (audio.getAttribute("src")) this.setAudioState("error");
      });
      this.on($("audio-volume"), "input", (e) => {
        this.volume = Number(e.target.value) / 100;
        audio.volume = this.volume;
        U.store.set("mockexam:volume", this.volume);
      });
      this.on($("audio-start"), "click", () => {
        if (this.audioState === "error") this.loadPart(this.audioPart, this.lastTime || 0, true);
        else this.play();
      });
      if (practice) {
        this.on($("audio-play"), "click", () => (audio.paused ? this.play() : audio.pause()));
        this.on($("audio-back"), "click", () => this.seekBy(-10));
        this.on($("audio-fwd"), "click", () => this.seekBy(10));
        this.on($("audio-seek"), "input", (e) => {
          audio.currentTime = Number(e.target.value);
          this.updateAudioUI();
        });
        this.on($("audio-part"), "change", (e) => this.switchPart(Number(e.target.value)));
        this.on($("audio-rate"), "change", (e) => {
          this.rate = Number(e.target.value);
          audio.defaultPlaybackRate = this.rate;
          audio.playbackRate = this.rate;
        });
      }
    }

    startAudio() {
      if (this.phase === "checking") {
        // Resumed during the checking time: the recording is already over.
        this.setAudioState("ended");
        return;
      }
      this.loadPart(this.audioPart, this.resumeAt, true);
    }

    loadPart(idx, at = 0, autoplay = true) {
      const part = this.parts[idx];
      const a = this.audio;
      this.audioPart = idx;
      this.audioState = "loading";
      a.src = part.audio.src;
      a.defaultPlaybackRate = this.rate;
      a.playbackRate = this.rate;
      if (at > 0) {
        const seek = () => { a.currentTime = Math.min(at, Math.max(0, (part.audio.duration || a.duration) - 1)); };
        if (a.readyState >= 1) seek();
        else a.addEventListener("loadedmetadata", seek, { once: true });
      }
      if (autoplay) this.play();
      this.renderPartTabs();
      this.updateAudioUI();
    }

    play() {
      if (!this.audio || this.finished) return;
      const p = this.audio.play();
      if (p && typeof p.catch === "function") {
        p.catch((err) => {
          // Browsers block sound until the page has been clicked; ask for a click.
          if (err && err.name === "NotAllowedError") this.setAudioState("blocked");
        });
      }
    }

    seekBy(delta) {
      const a = this.audio;
      const dur = this.parts[this.audioPart].audio.duration || a.duration || 0;
      a.currentTime = Math.max(0, Math.min(dur - 0.25, (a.currentTime || 0) + delta));
      this.updateAudioUI();
    }

    switchPart(idx) {
      this.loadPart(idx, 0, true);
      this.setCurrent(this.firstQuestion(idx), false);
      this.saveProgressSoon();
    }

    onPartEnded() {
      if (this.finished) return;
      const next = this.audioPart + 1;
      if (next < this.parts.length) {
        this.loadPart(next, 0, true);
        // Show the new part's questions; earlier parts stay one click away.
        this.setCurrent(this.firstQuestion(next), false);
        this.saveProgressSoon();
        return;
      }
      if (this.mode === "exam") {
        this.phase = "checking";
        U.toast(`The recording has finished. You have ${this.checkSeconds / 60} minutes to check your answers.`, "warn");
      } else {
        U.toast("End of the recording. Check your answers, then press Finish test.");
      }
      $("exam-audio-bar").classList.toggle("is-checking", this.phase === "checking");
      this.setAudioState("ended");
      this.renderPartTabs();
      this.renderTimer();
      this.saveProgressSoon();
    }

    setAudioState(state) {
      if (state === "error" && this.audio) this.lastTime = this.audio.currentTime || 0;
      this.audioState = state;
      this.updateAudioUI();
    }

    updateAudioUI() {
      const a = this.audio;
      if (!a) return;
      const part = this.parts[this.audioPart];
      const dur = part.audio.duration || a.duration || 0;
      const t = Math.min(a.currentTime || 0, dur);
      $("audio-time").textContent = `${U.formatClock(t)} / ${U.formatClock(dur)}`;
      if (this.mode === "practice") {
        const seek = $("audio-seek");
        seek.max = String(dur);
        seek.value = String(t);
        const btn = $("audio-play");
        const playing = !a.paused;
        if (btn.dataset.playing !== String(playing)) {
          btn.dataset.playing = String(playing);
          btn.innerHTML = playing ? ICONS.pause : ICONS.play;
          btn.setAttribute("aria-label", playing ? "Pause" : "Play");
        }
        $("audio-part").value = String(this.audioPart);
      } else {
        $("audio-track-fill").style.width = `${dur ? (t / dur) * 100 : 0}%`;
      }

      const n = part.partNumber;
      let status;
      let action = "";
      if (this.phase === "checking") status = "The recording has finished. Check your answers.";
      else if (this.audioState === "ended") status = "End of the recording";
      else if (this.audioState === "error") [status, action] = ["The recording could not be loaded.", "Try again"];
      else if (this.audioState === "blocked") [status, action] = ["Your browser is waiting for you to start the sound.", "Start the recording"];
      else if (this.audioState === "loading") status = `Loading Part ${n}…`;
      else if (this.mode === "exam" && a.paused) [status, action] = [`Part ${n} was paused.`, "Continue the recording"];
      else status = this.mode === "exam" ? `Part ${n} of ${this.parts.length} is playing` : `Part ${n}`;

      const statusEl = $("audio-status");
      if (statusEl.textContent !== status) statusEl.textContent = status;
      // In practice mode the part selector already names the part.
      statusEl.classList.toggle("is-plain", this.mode === "practice" && status === `Part ${n}`);
      const start = $("audio-start");
      start.hidden = !action || this.finished;
      if (action && start.textContent !== action) start.textContent = action;
    }

    /* Timer: the recording sets the pace --------------------------------------- */
    get audioRemaining() {
      let left = 0;
      this.parts.forEach((p, i) => {
        if (i > this.audioPart) left += p.audio.duration;
        else if (i === this.audioPart) left += Math.max(0, p.audio.duration - (this.audio ? this.audio.currentTime || 0 : this.resumeAt));
      });
      return left;
    }

    startTimer() {
      clearInterval(this.timer);
      this.renderTimer();
      this.timer = setInterval(() => {
        this.elapsed++;
        if (this.mode === "exam" && this.phase === "checking") {
          this.checkLeft--;
          if (this.checkLeft === 30) U.toast("30 seconds left to check your answers.", "warn");
          if (this.checkLeft <= 0) {
            clearInterval(this.timer);
            U.toast("Time is up. Your answers are being submitted.", "warn");
            this.submit();
            return;
          }
        }
        this.renderTimer();
        if (this.elapsed % 5 === 0) this.saveProgress();
      }, 1000);
    }

    renderTimer() {
      const box = $("exam-timer-box");
      const text = $("exam-timer-text");
      if (this.timerHidden) {
        text.textContent = "Show time";
        box.classList.remove("warning");
        return;
      }
      if (this.mode === "exam") {
        const checking = this.phase === "checking";
        const left = checking ? this.checkLeft : this.audioRemaining + this.checkSeconds;
        text.textContent = checking ? `Check answers · ${U.formatClock(left)}` : `${U.formatClock(left)} left`;
        box.classList.toggle("warning", checking);
      } else {
        text.textContent = `Practice · ${U.formatClock(this.elapsed)}`;
        box.classList.remove("warning");
      }
    }

    /* Finish ----------------------------------------------------------------- */
    finishWarning() {
      if (this.mode === "exam" && this.phase === "listening") {
        return `<p class="warn-text">The recording is still playing. If you finish now, you will not hear the rest of it.</p>`;
      }
      return "";
    }

    async submit() {
      if (this.finished) return;
      if (this.audio) this.audio.pause();
      return super.submit();
    }

    resumeTimerAfterFailedSubmit() {
      this.finished = false;
      if (this.mode === "practice" || this.phase === "listening" || this.checkLeft > 0) this.startTimer();
      if (this.mode === "exam" && this.phase === "listening") this.play();
    }

    destroy() {
      if (this.audio) {
        const a = this.audio;
        this.audio = null;
        a.pause();
        a.removeAttribute("src");
        a.load();
      }
      const bar = $("exam-audio-bar");
      bar.innerHTML = "";
      bar.hidden = true;
      bar.classList.remove("is-checking");
      $("exam-screen").classList.remove("listening-mode");
      super.destroy();
    }
  }

  /* ======================================================================
     Writing
     ====================================================================== */
  class WritingExam extends ExamShell {
    constructor(opts) {
      super(opts);
      this.aiMarking = Boolean(opts.aiMarking);
      this.responses = (this.saved && this.saved.responses) || { 1: "", 2: "" };
      this.taskIdx = 0;
      this.promptCache = {};
      this.mount();
    }

    mount() {
      this.mountShell(`${this.test.shortTitle || this.test.title} · Writing`, "Task", "Your answer");
      $("exam-question-strip").hidden = true;
      $("exam-review-wrap").hidden = true;
      this.highlighter = new CdHighlighter("exam-pane-left");

      this.on($("exam-part-tabs"), "click", (e) => {
        const b = e.target.closest(".part-tab-btn");
        if (b) this.renderTask(Number(b.dataset.t));
      });
      this.on($("btn-prev-q"), "click", () => this.renderTask(this.taskIdx - 1));
      this.on($("btn-next-q"), "click", () => this.renderTask(this.taskIdx + 1));
      this.renderTask(0);
    }

    helpHTML() {
      return `
        <p><strong>Writing</strong></p>
        <ul class="help-list">
          <li>Use the <strong>Part 1</strong> and <strong>Part 2</strong> buttons to move between tasks. Your text is kept when you switch.</li>
          <li>The word count updates as you type. Task 1 needs at least 150 words and Task 2 at least 250.</li>
          <li>Spell-check is switched off, as in the real computer-delivered test.</li>
          <li>Your answers are saved in this browser as you type.</li>
        </ul>
        ${super.helpHTML()}`;
    }

    progressData() {
      return { responses: this.responses };
    }

    renderTask(i) {
      if (i < 0 || i >= this.test.tasks.length) return;
      const left = $("exam-pane-left");
      // Keep the candidate's highlights when switching between tasks.
      if (left.dataset.rendered === "1") this.promptCache[this.taskIdx] = left.innerHTML;
      if (this.highlighter) {
        this.highlighter.hideMenu();
        this.highlighter.closeNotes();
      }
      this.taskIdx = i;
      const t = this.test.tasks[i];
      const n = t.taskNumber;
      left.innerHTML = this.promptCache[i] || `
        <div class="passage-header"><div class="passage-part-label">Part ${n}</div></div>
        <div class="passage-instruction-bar">
          You should spend about ${t.recommendedMinutes} minutes on this task. Write at least ${t.minWords} words.
        </div>
        <div class="task-prompt">${U.paragraphs(t.prompt)}</div>
        ${TaskCharts.render(t.visual)}`;
      left.dataset.rendered = "1";
      left.scrollTop = 0;

      $("exam-pane-right").innerHTML = `
        <div class="writing-area">
          <label class="sr-only" for="writing-input">Your answer for Part ${n}</label>
          <textarea id="writing-input" class="writing-input" spellcheck="false" autocomplete="off"
            autocorrect="off" autocapitalize="off" placeholder="Type your answer here…"></textarea>
          <div class="word-count" aria-live="polite">Words: <strong id="word-count-val">0</strong>
            <span class="word-target">(minimum ${t.minWords})</span></div>
        </div>`;
      const ta = $("writing-input");
      ta.value = this.responses[n] || "";
      this.on(ta, "input", () => {
        this.responses[n] = ta.value;
        this.updateWordCount();
        this.saveProgressSoon();
      });
      this.updateWordCount();
      $("btn-prev-q").disabled = i === 0;
      $("btn-next-q").disabled = i === this.test.tasks.length - 1;
    }

    updateWordCount() {
      const t = this.test.tasks[this.taskIdx];
      const words = U.countWords(this.responses[t.taskNumber]);
      const el = $("word-count-val");
      if (el) {
        el.textContent = words;
        el.parentElement.classList.toggle("is-under", words < t.minWords);
      }
      this.renderTabs();
    }

    renderTabs() {
      $("exam-part-tabs").innerHTML = this.test.tasks
        .map((t, i) => `<button type="button" class="part-tab-btn ${i === this.taskIdx ? "active" : ""}" data-t="${i}">
            Part ${t.taskNumber} <span class="part-count">${U.countWords(this.responses[t.taskNumber])} words</span></button>`)
        .join("");
    }

    async confirmFinish() {
      const rows = this.test.tasks.map((t) => {
        const w = U.countWords(this.responses[t.taskNumber]);
        return `<div class="${w < t.minWords ? "is-warn" : ""}"><span>Task ${t.taskNumber} (min ${t.minWords})</span><strong>${w} words</strong></div>`;
      }).join("");
      const under = this.test.tasks.some((t) => U.countWords(this.responses[t.taskNumber]) < t.minWords);
      let wantAi = this.aiMarking;
      const ok = await U.modal({
        title: "Finish the Writing test?",
        bodyHTML: `
          <div class="summary-rows">${rows}</div>
          ${under ? `<p class="warn-text">At least one answer is below the minimum word count. Short answers lose marks.</p>` : ""}
          ${this.aiMarking
            ? `<label class="check-row"><input type="checkbox" id="ai-mark-check" checked /> Get AI examiner feedback and an estimated band score (takes about a minute)</label>`
            : `<p class="muted-text">You will get automatic feedback, a checklist and model answers.</p>`}`,
        buttons: [
          { label: "Return to test", className: "btn-secondary", value: false },
          { label: "Submit writing", className: "btn-danger", value: true },
        ],
        onClose: (value, root) => {
          const box = root.querySelector("#ai-mark-check");
          if (box) wantAi = box.checked;
        },
      });
      if (ok) this.submit(wantAi);
    }

    async submit(wantAi = this.aiMarking) {
      if (this.finished) return;
      this.finished = true;
      clearInterval(this.timer);
      const done = wantAi
        ? U.loadingOverlay("The examiner is marking your writing…", "This usually takes 30–90 seconds. Please keep this page open.")
        : U.loadingOverlay("Analysing your writing…", "Preparing your feedback.");
      try {
        const result = await U.api(`/api/writing/${encodeURIComponent(this.test.id)}/submit`, {
          method: "POST",
          body: JSON.stringify({
            responses: this.responses,
            candidateName: this.candidateName,
            clientId: U.clientId(),
            mode: this.mode,
            timeSpentSeconds: this.elapsed,
            requestAssessment: wantAi,
          }),
        });
        this.clearProgress();
        done();
        this.onFinish(result);
      } catch (err) {
        done();
        this.saveProgress();
        this.resumeTimerAfterFailedSubmit();
        U.modal({
          title: "Could not submit",
          bodyHTML: `<p>${esc(err.message)}</p><p>Your writing is saved in this browser. Check your connection and press <strong>Finish test</strong> again.</p>`,
        });
      }
    }
  }

  window.ReadingExam = ReadingExam;
  window.ListeningExam = ListeningExam;
  window.WritingExam = WritingExam;
})();
