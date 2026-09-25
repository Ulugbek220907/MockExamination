/**
 * Application controller: routing, dashboard, pre-test instructions,
 * launching exams, results, and the resources / about pages.
 *
 * Routes: #/ (tests), #/resources, #/about, #/start (instructions),
 *         #/exam (active test), #/results (last result).
 */
(function () {
  "use strict";

  const esc = (v) => U.escapeHtml(v);

  // Free official preparation material. We link to it; we never copy it.
  const OFFICIAL_RESOURCES = [
    {
      group: "Official computer-delivered familiarisation tests",
      note: "Try the real test software. Reading and Listening are marked automatically.",
      links: [
        { title: "IELTS on computer familiarisation test", org: "British Council", url: "https://takeielts.britishcouncil.org/take-ielts/prepare/free-ielts-english-practice-tests/ielts-on-computer/familiarisation-test" },
        { title: "IELTS familiarisation tests", org: "IDP IELTS", url: "https://ielts.idp.com/about/ielts-familiarisation-tests" },
      ],
    },
    {
      group: "Official sample questions and practice tests",
      note: "Sample tasks written by the test makers, with answers.",
      links: [
        { title: "Official sample test questions", org: "IELTS.org", url: "https://ielts.org/take-a-test/preparation-resources/sample-test-questions" },
        { title: "IELTS trial test", org: "IELTS.org", url: "https://ielts.org/take-a-test/preparation-resources/ielts-trial-test" },
        { title: "Free IELTS practice tests", org: "British Council", url: "https://takeielts.britishcouncil.org/take-ielts/prepare/free-ielts-english-practice-tests" },
        { title: "IELTS preparation materials", org: "IDP IELTS", url: "https://ielts.idp.com/prepare" },
        { title: "IELTS preparation", org: "Cambridge English", url: "https://www.cambridgeenglish.org/exams-and-tests/ielts/preparation/" },
      ],
    },
    {
      group: "How the test works and how it is scored",
      note: "Read these before you practise, so you know exactly what examiners look for.",
      links: [
        { title: "Academic Reading test format", org: "IELTS.org", url: "https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-reading" },
        { title: "Academic Writing test format", org: "IELTS.org", url: "https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-writing" },
        { title: "Writing test preparation resources", org: "IELTS.org", url: "https://ielts.org/take-a-test/preparation-resources/writing-test-resources" },
        { title: "IELTS scoring in detail (band descriptors)", org: "IELTS.org", url: "https://ielts.org/organisations/ielts-for-organisations/ielts-scoring-in-detail" },
      ],
    },
    {
      group: "Free reading material for daily practice",
      note: "Academic-style texts that are free to read. Practise skimming, scanning and summarising.",
      links: [
        { title: "Featured articles", org: "Wikipedia (CC BY-SA)", url: "https://en.wikipedia.org/wiki/Wikipedia:Featured_articles" },
        { title: "Science and research news", org: "NASA (public domain)", url: "https://www.nasa.gov/news/" },
        { title: "Climate and ocean explainers", org: "NOAA (public domain)", url: "https://www.noaa.gov/education" },
        { title: "Free e-books of classic non-fiction", org: "Project Gutenberg", url: "https://www.gutenberg.org/" },
      ],
    },
  ];

  class App {
    constructor() {
      this.config = { siteName: "MockExam", aiMarking: false, contactEmail: "" };
      this.tests = [];
      this.module = U.store.get("mockexam:module", "reading");
      this.exam = null;
      this.pending = null;
      this.lastResult = U.store.get("mockexam:lastResult", null);
      this.main = document.getElementById("site-main");
      this.init();
    }

    async init() {
      window.addEventListener("hashchange", () => this.route());
      this.main.addEventListener("click", (e) => this.onMainClick(e));
      try {
        const [config, data] = await Promise.all([U.api("/api/config"), U.api("/api/tests")]);
        this.config = { ...this.config, ...config };
        this.tests = data.tests || [];
        this.modules = data.modules || {};
      } catch (err) {
        this.loadError = "Could not load the tests. Please refresh the page.";
      }
      document.querySelectorAll("[data-site-name]").forEach((el) => { el.textContent = this.config.siteName; });
      this.route();
    }

    /* Routing ---------------------------------------------------------- */
    async route() {
      const hash = location.hash || "#/";

      if (this.exam) {
        if (hash === "#/exam") return;
        const leave = await U.modal({
          title: "Leave the test?",
          bodyHTML: "<p>Your answers are saved in this browser. You can resume this attempt later from the test list.</p>",
          buttons: [
            { label: "Leave test", className: "btn-secondary", value: true },
            { label: "Stay in test", className: "btn-primary", value: false },
          ],
        });
        if (!leave) {
          location.hash = "#/exam";
          return;
        }
        this.exam.saveProgress();
        this.exam.finished = true;
        this.exam.destroy();
        this.exam = null;
      }

      if (hash === "#/exam") return location.replace("#/");
      if (hash === "#/start") {
        if (this.pending) return this.showVerification();
        return location.replace("#/");
      }

      this.showView("site");
      this.setNav(hash);
      if (hash.startsWith("#/resources")) this.renderResources();
      else if (hash.startsWith("#/about")) this.renderAbout();
      else if (hash.startsWith("#/results") && this.lastResult) this.renderResults();
      else this.renderHome();
      window.scrollTo(0, 0);
    }

    setNav(hash) {
      const key = hash.startsWith("#/resources") ? "resources" : hash.startsWith("#/about") ? "about" : "home";
      document.querySelectorAll("[data-nav]").forEach((a) => {
        if (a.dataset.nav === key) a.setAttribute("aria-current", "page");
        else a.removeAttribute("aria-current");
      });
    }

    showView(name) {
      const ids = { site: "site-view", verification: "verification-view", exam: "exam-screen" };
      Object.entries(ids).forEach(([k, id]) => document.getElementById(id).classList.toggle("active", k === name));
      document.body.classList.toggle("in-exam", name === "exam");
    }

    onMainClick(e) {
      const el = e.target.closest("[data-action], [data-module]");
      if (!el) return;
      if (el.dataset.module) {
        if (el.disabled) return;
        this.module = el.dataset.module;
        U.store.set("mockexam:module", this.module);
        this.renderHome();
        return;
      }
      if (el.dataset.action === "start") this.prepare(el.dataset.test, el.dataset.mode);
      if (el.dataset.action === "retake" && this.lastResult) this.prepare(this.lastResult.testId, this.lastResult.mode || "exam");
    }

    /* Dashboard -------------------------------------------------------- */
    renderHome() {
      document.title = `${this.config.siteName} – IELTS-style Academic Reading & Writing practice`;
      const mod = this.module === "writing" ? "writing" : "reading";
      const tests = this.tests.filter((t) => t.module === mod);
      const modules = [
        ["reading", "Reading", true],
        ["writing", "Writing", true],
        ["listening", "Listening", false],
        ["speaking", "Speaking", false],
      ];
      this.main.innerHTML = `
        <section class="hero">
          <h1>Free IELTS-style Academic practice tests</h1>
          <p>Timed, computer-delivered practice for Academic Reading and Writing, with original passages,
            instant reading scores, answer explanations and detailed writing feedback.</p>
        </section>

        <div class="modules-nav" role="tablist" aria-label="Choose a module">
          ${modules.map(([key, label, on]) => `
            <button type="button" role="tab" class="module-tab-btn ${key === mod ? "active" : ""} ${on ? "" : "disabled"}"
              data-module="${key}" aria-selected="${key === mod}" ${on ? "" : "disabled"}>
              ${label}${on ? "" : ` <span class="module-badge">Coming soon</span>`}
            </button>`).join("")}
        </div>

        ${this.loadError ? `<div class="notice notice-warn"><strong>${esc(this.loadError)}</strong></div>` : ""}

        <section>
          <div class="section-head">
            <h2 class="section-title">${mod === "reading" ? "Academic Reading" : "Academic Writing"}</h2>
            <p class="muted-text">${mod === "reading"
              ? "3 passages · 40 questions · 60 minutes. Answers are marked instantly with explanations."
              : `2 tasks · 60 minutes. ${this.config.aiMarking ? "Get an AI examiner’s band estimate and feedback on all four criteria." : "Get automatic feedback, a checklist and model answers."}`}</p>
          </div>
          <div class="books-grid">${tests.map((t) => this.testCard(t)).join("") || `<p class="empty-note">No tests available yet.</p>`}</div>
        </section>

        <section id="history-section" hidden></section>

        <section class="how-grid" aria-label="How it works">
          <div class="how-card"><span class="how-num">1</span><h3>Real test conditions</h3>
            <p>The same split-screen layout, timer, highlighter and navigation you will see in the computer-delivered test.</p></div>
          <div class="how-card"><span class="how-num">2</span><h3>Instant, honest feedback</h3>
            <p>See your estimated band, your weakest question types and why every answer is right or wrong.</p></div>
          <div class="how-card"><span class="how-num">3</span><h3>Original material</h3>
            <p>Every passage, question and task here is written for this site, so it is new to you and legal to use.</p></div>
        </section>`;
      this.loadHistory();
    }

    hasProgress(testId) {
      return Boolean(U.store.get(`mockexam:progress:${testId}`));
    }

    testCard(t) {
      const inProgress = this.hasProgress(t.id);
      const body = t.module === "reading"
        ? `<ul class="test-passages-list">${t.passages.map((p) => `
            <li class="test-passage-item"><span class="p-badge">P${p.number}</span><span>${esc(p.title)}</span></li>`).join("")}</ul>`
        : `<ul class="test-passages-list">${t.tasks.map((k) => `
            <li class="test-passage-item"><span class="p-badge">T${k.number}</span><span>${esc(k.title)}</span></li>`).join("")}</ul>`;
      const meta = t.module === "reading"
        ? `<span>${t.durationMinutes} minutes</span><span>${t.totalQuestions} questions</span>`
        : `<span>${t.durationMinutes} minutes</span><span>2 tasks</span>`;
      return `
        <article class="test-card">
          <div>
            <div class="test-card-header">
              <span class="test-card-book">Academic ${t.module === "reading" ? "Reading" : "Writing"}</span>
              ${inProgress ? `<span class="badge-progress">In progress</span>` : ""}
            </div>
            <h3 class="test-card-title">${esc(t.shortTitle)}</h3>
            ${body}
          </div>
          <div>
            <div class="test-card-meta">${meta}</div>
            <div class="test-card-actions">
              <button type="button" class="btn-start-exam" data-action="start" data-test="${esc(t.id)}" data-mode="exam">Start timed test</button>
              <button type="button" class="btn-practice-mode" data-action="start" data-test="${esc(t.id)}" data-mode="practice" title="No time limit">Practice</button>
            </div>
          </div>
        </article>`;
    }

    async loadHistory() {
      const section = document.getElementById("history-section");
      if (!section) return;
      let items = [];
      try {
        items = (await U.api(`/api/history?clientId=${encodeURIComponent(U.clientId())}`)).items || [];
      } catch (e) { return; }
      if (!items.length || !document.body.contains(section)) return;
      const titleOf = (id) => {
        const t = this.tests.find((x) => x.id === id);
        return t ? `${t.module === "reading" ? "Reading" : "Writing"} · ${t.shortTitle}` : id;
      };
      section.hidden = false;
      section.innerHTML = `
        <h2 class="section-title">Your recent attempts</h2>
        <p class="muted-text section-sub">Saved for this browser only.</p>
        <div class="table-scroll"><table class="history-table">
          <thead><tr><th scope="col">Date</th><th scope="col">Test</th><th scope="col">Result</th><th scope="col">Time used</th></tr></thead>
          <tbody>${items.slice(0, 10).map((i) => `
            <tr>
              <td>${esc(U.formatDate(i.createdAt))}</td>
              <td>${esc(titleOf(i.testId))}${i.mode === "practice" ? ` <span class="muted-text">(practice)</span>` : ""}</td>
              <td>${i.module === "reading"
                ? `<strong>Band ${IeltsScoring.formatBand(i.bandScore)}</strong> <span class="muted-text">(${i.rawScore}/${i.totalQuestions})</span>`
                : i.bandScore !== null && i.bandScore !== undefined ? `<strong>Band ${IeltsScoring.formatBand(i.bandScore)}</strong>` : `<span class="muted-text">Feedback only (${i.task1Words}+${i.task2Words} words)</span>`}</td>
              <td>${U.formatDuration(i.timeSpentSeconds)}</td>
            </tr>`).join("")}</tbody>
        </table></div>`;
    }

    /* Pre-test instructions -------------------------------------------- */
    async prepare(testId, mode) {
      try {
        const test = await U.api(`/api/tests/${encodeURIComponent(testId)}`);
        this.pending = { test, mode: mode === "practice" ? "practice" : "exam" };
        if (location.hash === "#/start") this.showVerification();
        else location.hash = "#/start";
      } catch (err) {
        U.modal({ title: "Could not load the test", bodyHTML: `<p>${esc(err.message)}</p>` });
      }
    }

    showVerification() {
      const { test, mode } = this.pending;
      const reading = test.module === "reading";
      const timed = mode === "exam";
      const progress = U.store.get(`mockexam:progress:${test.id}`);
      const canResume = progress && progress.mode === mode;
      const instructions = reading
        ? [
          `There are <strong>3 passages</strong> and <strong>40 questions</strong>.`,
          timed ? `You have <strong>60 minutes</strong>. The test is submitted automatically when time runs out.` : `Practice mode has <strong>no time limit</strong>. The clock shows how long you have spent.`,
          `Write your answers directly on screen. There is no extra time to transfer answers.`,
          `Spelling counts in gap-fill questions. Wrong answers do not lose marks, so answer every question.`,
          `Select text to <strong>highlight</strong> it or add a <strong>note</strong>. Tick <strong>Review</strong> to flag a question.`,
        ]
        : [
          `There are <strong>2 tasks</strong>. Task 2 counts twice as much as Task 1.`,
          timed ? `You have <strong>60 minutes</strong> in total. Spend about 20 minutes on Task 1 and 40 minutes on Task 2.` : `Practice mode has <strong>no time limit</strong>.`,
          `Write at least <strong>150 words</strong> for Task 1 and <strong>250 words</strong> for Task 2.`,
          `Spell-check is switched off, as in the real computer-delivered test.`,
          `Your writing is saved in this browser as you type.`,
        ];

      document.getElementById("verification-card").innerHTML = `
        <div class="verification-header">
          <div class="vh-title"><span class="site-logo small" aria-hidden="true">M</span> Academic ${reading ? "Reading" : "Writing"}</div>
          <span class="vh-mode">${timed ? "Timed test" : "Practice mode"}</span>
        </div>
        <form class="verification-body" id="verify-form">
          <h1 class="verify-title">${esc(test.title)}</h1>
          <div class="verification-instructions">
            <strong>Instructions to candidates</strong>
            <ul>${instructions.map((i) => `<li>${i}</li>`).join("")}</ul>
          </div>
          ${canResume ? `
            <label class="check-row resume-row"><input type="checkbox" id="resume-check" checked />
              Resume my unfinished attempt (saved ${esc(U.formatDate(new Date(progress.savedAt).toISOString()))})</label>` : ""}
          <div class="candidate-field-group">
            <label for="cand-name">Your name (shown on your results)</label>
            <input id="cand-name" maxlength="80" autocomplete="name" value="${esc(U.store.get("mockexam:name", ""))}" placeholder="Candidate" />
          </div>
          <div class="verification-footer">
            <button type="button" class="btn-secondary" id="verify-cancel">Back to tests</button>
            <button type="submit" class="btn-primary btn-lg">Start test</button>
          </div>
        </form>`;
      this.showView("verification");
      document.getElementById("verify-cancel").addEventListener("click", () => {
        this.pending = null;
        location.hash = "#/";
      });
      document.getElementById("verify-form").addEventListener("submit", (e) => {
        e.preventDefault();
        const name = document.getElementById("cand-name").value.trim() || "Candidate";
        U.store.set("mockexam:name", name);
        const resumeBox = document.getElementById("resume-check");
        const resume = Boolean(resumeBox && resumeBox.checked);
        if (!resume) U.store.remove(`mockexam:progress:${test.id}`);
        this.launch(test, mode, name, resume ? progress : null);
      });
      document.getElementById("cand-name").focus();
    }

    launch(test, mode, name, saved) {
      this.pending = null;
      this.showView("exam");
      const Exam = test.module === "writing" ? WritingExam : ReadingExam;
      this.exam = new Exam({
        test, mode, saved,
        candidateName: name,
        aiMarking: this.config.aiMarking,
        onFinish: (result) => this.finish(result, test, mode),
      });
      location.hash = "#/exam";
    }

    finish(result, test, mode) {
      if (this.exam) {
        this.exam.destroy();
        this.exam = null;
      }
      result.module = test.module;
      result.mode = mode;
      this.lastResult = result;
      U.store.set("mockexam:lastResult", result);
      if (location.hash === "#/results") this.route();
      else location.hash = "#/results";
    }

    renderResults() {
      const r = this.lastResult;
      document.title = `Your results – ${this.config.siteName}`;
      if (r.module === "writing") Results.renderWriting(r, this.main);
      else Results.renderReading(r, this.main);
    }

    /* Static pages ----------------------------------------------------- */
    renderResources() {
      document.title = `Free official resources – ${this.config.siteName}`;
      this.main.innerHTML = `
        <section class="page">
          <h1>Free official IELTS resources</h1>
          <p class="lead-text">Combine our practice tests with the free material published by the organisations that run the exam.
            These links open the official websites. We do not copy or host their material.</p>
          ${OFFICIAL_RESOURCES.map((g) => `
            <div class="resource-group">
              <h2 class="section-title">${esc(g.group)}</h2>
              <p class="muted-text">${esc(g.note)}</p>
              <ul class="resource-list">
                ${g.links.map((l) => `
                  <li><a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.title)}</a>
                    <span class="resource-org">${esc(l.org)}</span></li>`).join("")}
              </ul>
            </div>`).join("")}
          <div class="notice notice-info"><strong>Tip</strong><span>Take one of our timed tests first to find your weakest
            question types, then use the official samples to check that your technique matches the real exam.</span></div>
        </section>`;
    }

    renderAbout() {
      document.title = `About & legal – ${this.config.siteName}`;
      const name = esc(this.config.siteName);
      const contact = this.config.contactEmail
        ? `<a href="mailto:${esc(this.config.contactEmail)}">${esc(this.config.contactEmail)}</a>`
        : "the contact address published by the site owner";
      this.main.innerHTML = `
        <section class="page prose">
          <h1>About ${name}</h1>
          <p class="lead-text">${name} is a free practice website for people preparing for the Academic Reading and Writing
            papers of the IELTS test. It recreates the computer-delivered test environment so you can practise under realistic conditions.</p>

          <h2>Independent website</h2>
          <p>${name} is not affiliated with, endorsed by or approved by the British Council, IDP IELTS or Cambridge University
            Press &amp; Assessment (the IELTS partners). “IELTS” is a registered trademark of its owners and is used on this site
            only to describe the exam that our practice material helps you prepare for.</p>

          <h2>Our content</h2>
          <ul>
            <li>All reading passages, questions, answer explanations, writing tasks and model answers were written specifically for this site.
              They are not copied or adapted from official IELTS tests or from published practice books.</li>
            <li>Facts in the reading passages come from widely available public knowledge. The data in Writing Task 1 charts is fictional and exists only for practice.</li>
            <li>For official practice material, see our <a href="#/resources">free official resources</a> page, which links to the official websites.</li>
          </ul>

          <h2>About your scores</h2>
          <ul>
            <li><strong>Reading:</strong> your band is estimated from your raw score using a typical Academic Reading conversion table.
              Official tests adjust this table slightly for each version.</li>
            <li><strong>Writing:</strong> ${this.config.aiMarking
              ? "when you request it, an AI examiner estimates a band for each of the four public Writing criteria."
              : "automatic feedback checks length, structure and language features."}
              These are practice estimates only and are not official IELTS results.</li>
          </ul>

          <h2>Privacy</h2>
          <ul>
            <li>When you submit a test we store the name you typed, your answers or essays, your scores and an anonymous ID for this browser,
              so that we can show your recent attempts. We do not ask for your email address or create an account.</li>
            ${this.config.aiMarking ? `<li>If you request AI feedback, your essays are sent to our AI provider (Anthropic) for marking.
              Do not include personal information in your essays.</li>` : ""}
            <li>Unfinished answers, your display preferences and your last result are kept in your own browser's local storage.</li>
            <li>We do not sell your data or show advertising. To have your stored attempts deleted, contact ${contact}.</li>
          </ul>
        </section>`;
    }
  }

  window.app = new App();
})();
