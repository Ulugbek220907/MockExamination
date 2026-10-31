/**
 * Application controller: routing, the home page, the test lists,
 * pre-test instructions, launching exams, results, and the about and legal pages.
 *
 * Routes: #/ (home), #/tests/<module> (every test of one module), #/practice (practice by question type),
 *         #/about, #/start (instructions),
 *         #/exam (active test), #/results (last result), #/speaking/<id>
 *         (a recorded Speaking test), and the account
 *         pages from account.js: #/pricing, #/account, #/examiners,
 *         #/check/<id>, #/examiner, #/admin.
 */
(function () {
  "use strict";

  const esc = (v) => U.escapeHtml(v);

  // Shown on the legal pages when the server has no CONTACT_EMAIL (never a blank).
  const SUPPORT_EMAIL = "ulugbekisoqov22@gmail.com";
  const MODULE_LABELS = { reading: "Reading", listening: "Listening", writing: "Writing", speaking: "Speaking" };
  const CATALOG_PAGE = 24;
  // The test list and settings from the last visit (see init); bump the version when their shape changes.
  const BOOT_KEY = "testday:boot";
  const BOOT_VERSION = 3;

  // The four modules, in the order of the real test day.
  const MODULES = ["listening", "reading", "writing", "speaking"];

  const ICON_BACK = `<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M13 8H4M7.5 4l-4 4 4 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const ICON_LOCK = `<svg width="10" height="11" viewBox="0 0 10 11" aria-hidden="true"><path fill="currentColor" d="M8 4.5V3.4a3 3 0 0 0-6 0v1.1H1v6h8v-6H8zM3.4 3.4a1.6 1.6 0 0 1 3.2 0v1.1H3.4V3.4z"/></svg>`;

  class App {
    constructor() {
      this.config = { siteName: "TestDay", aiMarking: false, contactEmail: SUPPORT_EMAIL, commerce: false };
      this.tests = [];
      this.exam = null;
      this.pending = null;
      this.ridden = U.store.get("testday:ridden", {});
      this.history = null;
      this.prices = null;
      this.lastResult = U.store.get("mockexam:lastResult", null);
      this.main = document.getElementById("site-main");
      this.init();
    }

    async init() {
      window.addEventListener("hashchange", () => this.route());
      // Funnel: one visit a day per browser (the server drops repeats too), and the main buttons' clicks.
      const day = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Tashkent" });
      if (U.store.get("testday:visitDay") !== day) {
        U.store.set("testday:visitDay", day);
        U.track("visit");
      }
      document.addEventListener("click", (e) => {
        const el = e.target.closest("[data-track]");
        if (el) U.track("cta_click", { detail: el.dataset.track });
      });
      document.getElementById("feedback-open").addEventListener("click", () => this.openFeedback());
      this.renderFooter();
      this.main.addEventListener("click", (e) => this.onMainClick(e));
      document.getElementById("account-slot").addEventListener("click", (e) => Account.onClick(e));

      // Warm bundle and test data as soon as the user hovers or focuses on a start button
      const onIntent = (e) => {
        const target = e.target.closest("[data-test], [data-action='start']");
        if (!target) return;
        U.prefetch("exam");
        // Only tests this visitor can open: a locked one would just be refused (401/402).
        const testId = target.dataset.test;
        const test = testId && this.tests.find((x) => x.id === testId);
        if (test && this.canOpen(test)) U.api(`/api/tests/${encodeURIComponent(testId)}`).catch(() => {});
      };
      this.main.addEventListener("pointerover", onIntent, { passive: true });
      this.main.addEventListener("focusin", onIntent, { passive: true });

      // Draw at once from what this browser saw last time, then bring it up to date: nobody waits
      // for the server (or the database behind it) before seeing the page.
      const boot = U.store.get(BOOT_KEY, null);
      const fromBoot = Boolean(boot && boot.v === BOOT_VERSION && Array.isArray(boot.tests) && boot.tests.length);
      Account.primeMe();
      if (fromBoot) this.applyBoot(boot);
      Account.renderAccountSlot();
      const me = Account.refreshMe();
      let firstDraw = fromBoot ? this.firstRoute() : null;

      let fresh = null;
      try {
        const [config, data] = await Promise.all([U.api("/api/config"), U.api("/api/tests")]);
        fresh = { v: BOOT_VERSION, config, tests: data.tests || [], modules: data.modules || {} };
        U.store.set(BOOT_KEY, fresh);
      } catch (err) {
        if (!fromBoot) this.loadError = true;
      }
      const seenMe = JSON.stringify(Account.state.me);
      if (fresh) {
        const changed = !fromBoot || JSON.stringify([boot.config, boot.tests, boot.modules]) !== JSON.stringify([fresh.config, fresh.tests, fresh.modules]);
        this.applyBoot(fresh);
        if (changed && firstDraw) await firstDraw.then(() => this.renderIfHome());
      }
      if (!firstDraw) firstDraw = this.firstRoute();
      await me;
      // The account decides which tests are open: redraw the home page if it changed.
      if (JSON.stringify(Account.state.me) !== seenMe) {
        await firstDraw;
        this.renderIfHome();
      }
    }

    applyBoot(data) {
      this.config = { ...this.config, ...(data.config || {}) };
      this.tests = data.tests || [];
      this.modules = data.modules || {};
      this.loadError = false;
      Account.setConfig(this.config);
      this.applyCommerce();
      document.querySelectorAll("[data-site-name]").forEach((el) => { el.textContent = this.config.siteName; });
      this.renderFooter();
    }

    /** True once the site sells the pass and examiner checks. Until then visitors only take tests and sign in. */
    commerce() {
      return Boolean(this.config.commerce);
    }

    /** Price, Examiners and Refunds links are in the page but hidden until commerce is on. */
    applyCommerce() {
      const on = this.commerce();
      document.querySelectorAll("[data-commerce]").forEach((el) => { el.hidden = !on; });
    }

    /** The footer is the end of every page: the contact email, the social links the owner has set, and the year. */
    renderFooter() {
      const contact = document.getElementById("footer-contact");
      if (contact) contact.innerHTML = this.contactHTML();
      const social = document.getElementById("footer-social");
      if (social) {
        social.innerHTML = (this.config.social || [])
          .map((x) => `<a href="${esc(x.url)}" target="_blank" rel="noopener noreferrer">${esc(x.name)}</a>`).join("");
      }
      const year = document.getElementById("footer-year");
      if (year) year.textContent = String(new Date().getFullYear());
    }

    firstRoute() {
      return Promise.resolve(this.route()).finally(() => {
        this.main.removeAttribute("aria-busy");
        // Prefetch exam and results bundles when the browser is idle so test launch is instant
        const warmIdle = () => {
          U.prefetch("exam");
          U.prefetch("results");
        };
        if (U.lowData()) return; // a data-saver connection downloads the test code only when a test starts
        if ("requestIdleCallback" in window) {
          requestIdleCallback(warmIdle, { timeout: 3000 });
        } else {
          setTimeout(warmIdle, 1200);
        }
      });
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
      const [path, query] = hash.slice(1).split("?");
      const params = new URLSearchParams(query || "");
      if (!this.commerce() && /^\/(pricing|refunds|examiners?|check\/\d+)$/.test(path)) return location.replace("#/");
      const check = path.match(/^\/check\/(\d+)$/);
      const spoken = path.match(/^\/speaking\/(\d+)$/);
      window.scrollTo(0, 0);
      const catalog = path.match(/^\/tests\/(listening|reading|writing|speaking)$/);
      if (catalog) this.renderCatalog(catalog[1]);
      else if (path === "/practice") await this.renderPractice();
      else if (path === "/about") this.renderAbout();
      else if (path === "/terms") this.renderLegal("terms");
      else if (path === "/privacy") this.renderLegal("privacy");
      else if (path === "/refunds") this.renderLegal("refunds");
      else if (path === "/results" && this.lastResult) await this.renderResults();
      else if (path === "/pricing") await Account.renderPricing(this.main);
      else if (path === "/account") await Account.renderAccount(this.main);
      else if (path === "/examiners") await Account.renderExaminers(this.main, params);
      else if (path === "/examiner") await Account.renderExaminerDashboard(this.main);
      else if (path === "/admin") await Account.renderAdmin(this.main, params);
      else if (check) await Account.renderCheck(this.main, check[1]);
      else if (spoken) { if (await this.loadFor("exam")) await Speaking.renderResult(this.main, spoken[1]); }
      else this.renderHome();
    }

    setNav(hash) {
      const path = hash.slice(1).split("?")[0];
      const key = { "/about": "about", "/pricing": "pricing", "/account": "account", "/examiner": "examiner", "/admin": "admin" }[path]
        || (path.startsWith("/check") ? "account" : "");
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
      if (Account.onClick(e)) return;
      const chip = e.target.closest("[data-catalog-filter]");
      if (chip && this.catalogModule) {
        const st = this.catalogStateOf(this.catalogModule);
        st.filter = chip.dataset.catalogFilter;
        st.shown = CATALOG_PAGE;
        this.main.querySelectorAll("[data-catalog-filter]").forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
        return this.renderCatalogGrid();
      }
      if (e.target.closest("[data-catalog-more]") && this.catalogModule) {
        this.catalogStateOf(this.catalogModule).shown += CATALOG_PAGE;
        return this.renderCatalogGrid();
      }
      const el = e.target.closest("[data-action]");
      if (!el) return;
      if (el.dataset.action === "start") this.prepare(el.dataset.test, el.dataset.mode, el);
      if (el.dataset.action === "practice-type") this.startPractice(el.dataset.type, el);
      if (el.dataset.action === "retake" && this.lastResult) {
        if (this.lastResult.module === "practice") this.startPractice(this.lastResult.type, el);
        else this.prepare(this.lastResult.testId, this.lastResult.mode || "exam");
      }
    }

    /* Home: what TestDay is, the four modules, three numbers ------------------------ */
    renderHome() {
      document.title = `${this.config.siteName} – ${t("title.home")}`;
      this.main.innerHTML = `
        <div class="home">
          <h1 class="home-title">${t("home.title")}</h1>
          <p class="hero-lead">${this.leadText()}</p>
          <div class="home-notice" id="home-account-notes">${this.accountNotesHTML()}</div>
          ${this.loadError ? `<div class="notice notice-warn home-notice"><strong>${t("Could not load the tests. Please refresh the page.")}</strong></div>` : ""}
          <h2 class="sr-only">${t("Tests")}</h2>
          <ul class="ledger" id="ledger"></ul>
          ${this.testsOf("reading").length ? `<p class="practice-line" id="practice-line">${t("practice.line")}
            <a href="#/practice" data-track="home_practice">${t("Practise one question type")}</a></p>` : ""}
          <section id="history-section" aria-label="${esc(t("Your recent tests"))}" hidden></section>
          <section class="facts" id="facts" aria-label="${esc(t("Price and marking"))}"></section>
        </div>`;
      this.renderLedger();
      this.renderFacts();
      this.loadHistory();
      this.loadPrices();
    }

    /** For a signed-in student: the pass-ending notice and their goal (or an invitation to set one). */
    accountNotesHTML() {
      if (!Account.user()) return "";
      const g = Account.goal();
      let goal;
      if (g.targetBand || g.examDate) {
        const days = Account.daysUntil(g.examDate);
        const parts = [];
        if (g.targetBand) parts.push(t("Your goal: band {band}", { band: `<strong>${esc(IeltsScoring.formatBand(g.targetBand))}</strong>` }));
        if (days !== null && days >= 0) {
          parts.push(days === 0 ? t("Your exam is today. Good luck!") : `${plural(days, "Exam in {n} day", "Exam in {n} days")}<span class="muted-text"> (${esc(new Date(`${g.examDate}T12:00:00`).toLocaleDateString(U.LOCALE, { day: "numeric", month: "long" }))})</span>`);
        }
        goal = `<p class="goal-strip">${parts.join(" · ")} <a href="#/account">${t("Change")}</a></p>`;
      } else {
        goal = `<p class="goal-strip"><a href="#/account" data-track="home_goal">${t("Set your target band and exam date")}</a></p>`;
      }
      return Account.planEndingHTML() + goal;
    }

    /** "167 timed tests for Listening, Reading, Writing and Speaking. 18 are free." Counted from the tests, never typed. */
    leadText() {
      if (!this.tests.length) return t("home.lead.empty");
      const free = this.tests.filter((x) => x.access === "free").length;
      if (!this.commerce()) return t("home.lead.free", { free: esc(U.number(free)) });
      return t("home.lead", { total: esc(U.number(this.tests.length)), free: esc(U.number(free)) });
    }

    formatOf(module) {
      return t(`format.${module}`);
    }

    /** The test a visitor can start from the home page: the first one they can open and have not taken. */
    nextToStart(module) {
      return this.testsOf(module).find((x) => this.canOpen(x) && !this.ridden[x.id]) || null;
    }

    renderLedger() {
      const list = document.getElementById("ledger");
      if (!list) return;
      const commerce = this.commerce();
      const everything = commerce && (Account.planActive() || ["admin", "examiner"].includes(Account.role()));
      list.innerHTML = MODULES.map((module) => {
        const tests = this.testsOf(module);
        if (!tests.length) return "";
        const free = tests.filter((x) => x.access === "free").length;
        const count = commerce ? plural(tests.length, "{n} test", "{n} tests") : plural(free, "{n} free test", "{n} free tests");
        const rest = commerce ? (everything ? t("all open") : t("{n} free", { n: free })) : (free < tests.length ? t("more coming soon") : "");
        const label = MODULE_LABELS[module];
        const start = this.nextToStart(module);
        const taken = tests.some((x) => this.ridden[x.id]);
        const action = start
          ? `<button type="button" class="btn-primary" data-action="start" data-test="${esc(start.id)}" data-mode="exam"
              aria-label="${esc(t("Start {name}", { name: `${label}, ${this.testName(start)}` }))}">${taken ? t("Next test") : start.access === "free" ? t("Start free") : t("Start")}</button>`
          : `<a class="btn-secondary" href="#/tests/${module}" aria-label="${esc(t("All {n} {module} tests", { n: tests.length, module: label }))}">${t("All tests")}</a>`;
        return `
          <li class="ledger-row">
            <h3 class="ledger-name">${label}</h3>
            <p class="ledger-facts"><a href="#/tests/${module}" aria-label="${esc(t("All {n} {module} tests", { n: tests.length, module: label }))}">${count}</a>${rest ? `, ${rest}` : ""}<span class="fmt">${esc(this.formatOf(module))}</span></p>
            <div class="ledger-act">${action}</div>
          </li>`;
      }).join("");
    }

    /** Three facts, each with the figure first: how long a test is, what the pass costs, how long marking takes. */
    renderFacts() {
      const box = document.getElementById("facts");
      if (!box) return;
      box.hidden = !this.commerce();
      if (!this.commerce()) { box.innerHTML = ""; return; }
      const reading = this.testsOf("reading")[0];
      const questions = reading ? reading.totalQuestions : 40;
      const minutes = reading ? reading.durationMinutes : 60;
      box.innerHTML = `
        <div class="fact"><p class="fact-fig">${t("{q} questions in {min} minutes", { q: questions, min: minutes })}</p>
          <p class="fact-cap">${t("The length of a Reading test, as in the exam.")}</p></div>
        <div class="fact" data-fact="price"><p class="fact-fig" data-price="plan">${this.priceText()}</p>
          <p class="fact-cap">${t("facts.pass", { n: esc(U.number(this.tests.length)) })}</p></div>
        <div class="fact"><p class="fact-fig">${t("About 48 hours")}</p>
          <p class="fact-cap">${t("For an examiner to mark your Writing or Speaking test.")}</p></div>
        <div class="facts-act">
          <button type="button" class="btn-primary btn-lg" data-action="buy-plan" data-track="home_pass">${Account.planActive() ? t("Add another month") : t("Get the pass")}</button>
          <a href="#/pricing">${t("Price")}</a>
        </div>`;
    }

    priceText() {
      return this.prices && this.prices.plan ? t("{price} a month", { price: esc(U.money(this.prices.plan)) }) : "&nbsp;";
    }

    async loadPrices() {
      if (this.prices || !this.commerce()) return;
      try {
        const b = await Account.billing();
        this.prices = b.prices || null;
      } catch (e) { return; }
      const price = this.main.querySelector('[data-price="plan"]');
      if (price && this.prices) price.innerHTML = this.priceText();
    }

    hasProgress(testId) {
      return Boolean(U.store.get(`mockexam:progress:${testId}`));
    }

    canOpen(t) {
      if (t.access === "free" || ["admin", "examiner"].includes(Account.role())) return true;
      return t.access === "premium" && Account.planActive();
    }

    testsOf(module) {
      return this.tests.filter((x) => x.module === module).sort((a, b) => (a.sortOrder - b.sortOrder) || a.id.localeCompare(b.id));
    }

    testName(test) {
      const n = this.testsOf(test.module).indexOf(test) + 1;
      return t("Test {n}", { n: n || test.sortOrder || 1 });
    }

    /** What a test row says about a test. */
    testFacts(test) {
      const ride = this.ridden[test.id];
      const items = test.module === "reading" ? (test.passages || []).map((p) => [`P${p.number}`, p.title])
        : test.module === "listening" ? (test.parts || []).map((p) => [`${p.number}`, p.title])
          : test.module === "speaking" ? (test.parts || []).map((p) => [`${p.number}`, (p.topics || []).join(" · ") || p.title])
            : (test.tasks || []).map((k) => [`T${k.number}`, k.title]);
      const meta = test.module === "writing" ? t("{min} minutes · 2 tasks", { min: test.durationMinutes })
        : test.module === "speaking" ? t("11–14 minutes · {q} questions", { q: test.totalQuestions })
          : test.module === "listening" ? t("About {min} minutes · {q} questions", { min: test.durationMinutes, q: test.totalQuestions })
            : t("{min} minutes · {q} questions", { min: test.durationMinutes, q: test.totalQuestions });
      const locked = !this.canOpen(test);
      const band = ride && ride.band !== null && ride.band !== undefined ? IeltsScoring.formatBand(ride.band) : "";
      const soon = test.access === "soon";
      const tag = test.access === "free" ? `<span class="test-tag is-free">${t("Free")}</span>`
        : soon ? `<span class="test-tag is-soon">${locked ? t("Coming soon…") : t("Not public yet")}</span>`
          : !locked ? `<span class="test-tag">${t("In your pass")}</span>`
            : `<span class="test-tag is-locked">${ICON_LOCK} ${t("Pass")}</span>`;
      const extra = [
        this.hasProgress(test.id) ? t("Unfinished attempt saved") : "",
        band ? t("Your last band: {band}", { band }) : "",
      ].filter(Boolean).join(" · ");
      return { ride, items, meta, locked, soon: soon && locked, band, tag, extra };
    }

    /** The buttons of a test row. A locked test has one quiet action: the pass. */
    testActionsHTML(test, facts) {
      const name = `${MODULE_LABELS[test.module]}, ${this.testName(test)}`;
      if (facts.soon) return "";
      if (facts.locked) {
        return `<button type="button" class="btn-link" data-action="buy-plan" aria-label="${esc(t("Get the pass to open {name}", { name }))}">${t("Get the pass")}</button>`;
      }
      const start = facts.ride ? t("Take it again") : test.access === "free" ? t("Start free") : t("Start");
      return `
          <button type="button" class="btn-secondary btn-sm" data-action="start" data-test="${esc(test.id)}" data-mode="practice"
            aria-label="${esc(t("Practice {name} without a timer", { name }))}">${t("Practice")}</button>
          <button type="button" class="btn-primary btn-sm" data-action="start" data-test="${esc(test.id)}" data-mode="exam"
            aria-label="${esc(t("Start {name}, timed", { name }))}">${start}</button>`;
    }

    /* A module's own page: every test, searchable ------------------------ */
    catalogStateOf(module) {
      if (!this.catalogState) this.catalogState = {};
      if (!this.catalogState[module]) this.catalogState[module] = { filter: "all", q: "", shown: CATALOG_PAGE };
      return this.catalogState[module];
    }

    renderCatalog(module) {
      const tests = this.testsOf(module);
      const st = this.catalogStateOf(module);
      this.catalogModule = module;
      const title = t("{module} tests", { module: MODULE_LABELS[module] });
      document.title = `${title} – ${this.config.siteName}`;
      const done = tests.filter((x) => this.ridden[x.id]).length;
      const free = tests.filter((x) => x.access === "free").length;
      const openable = tests.filter((x) => this.canOpen(x));
      const filters = [["all", t("All"), tests.length], ["free", t("Free"), free], ["open", t("Not taken yet"), openable.filter((x) => !this.ridden[x.id]).length], ["done", t("Taken"), done]];
      this.main.innerHTML = `
        <section class="page catalog" aria-labelledby="catalog-title">
          <a class="back-link" href="#/">${ICON_BACK} ${t("Home")}</a>
          <div class="catalog-head">
            <h1 id="catalog-title">${esc(title)}</h1>
            <p>${esc(this.commerce() ? t("catalog.sub", { format: this.formatOf(module), n: tests.length, free }) : t("catalog.sub.free", { format: this.formatOf(module), free }))}</p>
          </div>
          <div class="catalog-tools">
            <div class="chip-row" role="group" aria-label="${esc(t("Show"))}">
              ${filters.map(([k, label, n]) => `<button type="button" class="chip" data-catalog-filter="${k}" aria-pressed="${st.filter === k}">${esc(label)} <span class="chip-count">${n}</span></button>`).join("")}
            </div>
            <input type="search" class="catalog-search" id="catalog-search" value="${esc(st.q)}" autocomplete="off"
              placeholder="${esc(t("Search by topic"))}" aria-label="${esc(t("Search these tests by topic"))}">
          </div>
          <p class="catalog-count muted-text" id="catalog-count" aria-live="polite"></p>
          <ol class="test-list" id="catalog-grid"></ol>
          <div class="catalog-more" id="catalog-more"></div>
        </section>`;
      let timer = null;
      this.main.querySelector("#catalog-search").addEventListener("input", (e) => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          st.q = e.target.value;
          st.shown = CATALOG_PAGE;
          this.renderCatalogGrid();
        }, 120);
      });
      this.renderCatalogGrid();
      this.loadHistory();
    }

    renderCatalogGrid() {
      const module = this.catalogModule;
      const grid = document.getElementById("catalog-grid");
      if (!grid || !module) return;
      const st = this.catalogStateOf(module);
      const words = st.q.toLowerCase().split(/\s+/).filter(Boolean);
      const list = this.testsOf(module).filter((test) => {
        const taken = Boolean(this.ridden[test.id]);
        if ((st.filter === "open" && (taken || !this.canOpen(test))) || (st.filter === "done" && !taken) || (st.filter === "free" && test.access !== "free")) return false;
        if (!words.length) return true;
        const hay = [this.testName(test), ...this.testFacts(test).items.map(([, v]) => v)].join(" ").toLowerCase();
        return words.every((w) => hay.includes(w));
      });
      grid.innerHTML = list.slice(0, st.shown).map((test) => this.catalogRowHTML(test)).join("")
        || `<li class="empty-note">${esc(t("No tests match. Try another word or show all tests."))}</li>`;
      document.getElementById("catalog-count").textContent = words.length || st.filter !== "all"
        ? t("{n} of {total} tests", { n: list.length, total: this.testsOf(module).length }) : "";
      const rest = list.length - st.shown;
      document.getElementById("catalog-more").innerHTML = rest > 0
        ? `<button type="button" class="btn-secondary" data-catalog-more>${esc(t("Show {n} more", { n: Math.min(rest, CATALOG_PAGE) }))}</button>` : "";
    }

    catalogRowHTML(test) {
      const f = this.testFacts(test);
      const topics = f.items.map(([, v]) => v).filter(Boolean).join(" / ");
      const notes = [f.band ? t("Band {band}", { band: f.band }) : "", this.hasProgress(test.id) ? t("In progress") : ""].filter(Boolean);
      // A test that is not open yet is shown blurred, with "Coming soon…" over it. The blurred text is hidden from
      // screen readers, which hear the test's name and "Coming soon…" instead.
      if (f.soon) {
        return `
        <li class="test-row is-soon">
          <h2 class="test-row-name" aria-hidden="true">${esc(this.testName(test))}</h2>
          <p class="test-row-topics" aria-hidden="true">${esc(topics)}</p>
          <div class="test-row-tag" aria-hidden="true">${f.tag}</div>
          <p class="soon-label"><span class="sr-only">${esc(this.testName(test))}: </span>${t("Coming soon…")}</p>
        </li>`;
      }
      return `
        <li class="test-row">
          <h2 class="test-row-name">${esc(this.testName(test))}${notes.map((n) => `<span class="test-row-band">${esc(n)}</span>`).join("")}</h2>
          <p class="test-row-topics">${esc(topics)}</p>
          <div class="test-row-tag">${f.tag}</div>
          <div class="test-row-act">${this.testActionsHTML(test, f)}</div>
        </li>`;
    }

    async loadHistory() {
      let items = [];
      try {
        items = (await U.api(`/api/history?clientId=${encodeURIComponent(U.clientId())}`)).items || [];
      } catch (e) { return; }
      this.history = items;
      // The latest attempt at each test marks it as taken.
      const ridden = {};
      [...items].reverse().forEach((i) => { ridden[i.testId] = { band: i.bandScore, module: i.module }; });
      const changed = JSON.stringify(ridden) !== JSON.stringify(this.ridden);
      this.ridden = ridden;
      U.store.set("testday:ridden", ridden);
      if (changed && document.getElementById("ledger")) this.renderLedger();
      if (changed && document.getElementById("catalog-grid")) this.renderCatalogGrid();
      this.renderHistory(items);
    }

    renderHistory(items) {
      const section = document.getElementById("history-section");
      if (!section || !items.length) return;
      const testOf = (id) => this.tests.find((x) => x.id === id);
      section.hidden = false;
      section.innerHTML = `
        <h2 class="section-title">${t("Your recent tests")}</h2>
        <p class="muted-text section-sub">${Account.user() ? t("Saved in your account.") : t("Saved for this browser only. Sign in to keep them on every device.")}</p>
        <div class="table-scroll"><table class="history-table">
          <thead><tr><th scope="col">${t("Date")}</th><th scope="col">${t("Test")}</th><th scope="col">${t("Result")}</th><th scope="col">${t("Time used")}</th></tr></thead>
          <tbody>${items.slice(0, 10).map((i) => {
            const test = testOf(i.testId);
            const name = test ? `${MODULE_LABELS[test.module]}, ${this.testName(test)}` : i.testId;
            return `
            <tr>
              <td>${esc(U.formatDate(i.createdAt))}</td>
              <td>${esc(name)}${i.mode === "practice" ? ` <span class="muted-text">(${t("practice")})</span>` : ""}</td>
              <td>${i.module === "speaking" ? this.speakingHistoryCell(i)
                : i.module !== "writing"
                ? `<strong>${t("Band {band}", { band: IeltsScoring.formatBand(i.bandScore) })}</strong> <span class="muted-text">(${i.rawScore}/${i.totalQuestions})</span>`
                : i.bandScore !== null && i.bandScore !== undefined ? `<strong>${t("Band {band}", { band: IeltsScoring.formatBand(i.bandScore) })}</strong>`
                  : `<span class="muted-text">${t("Feedback only ({words} words)", { words: `${i.task1Words}+${i.task2Words}` })}</span>`}</td>
              <td>${U.formatDuration(i.timeSpentSeconds)}</td>
            </tr>`;
          }).join("")}</tbody>
        </table></div>`;
    }

    speakingHistoryCell(i) {
      const band = i.bandScore !== null && i.bandScore !== undefined ? `<strong>${t("Band {band}", { band: IeltsScoring.formatBand(i.bandScore) })}</strong> `
        : i.aiBand !== null && i.aiBand !== undefined ? `<strong>${t("Band {band}", { band: IeltsScoring.formatBand(i.aiBand) })}</strong> <span class="muted-text">${t("(AI examiner)")}</span> ` : "";
      const status = i.checkStatus && i.checkStatus !== "completed" ? `<span class="muted-text">${t("Examiner marking")}</span> ` : "";
      return `${band}${status}<a href="#/speaking/${Number(i.id)}">${t("Listen ({n} answers)", { n: i.answered })}</a>`;
    }

    /* Practice by question type ------------------------------------------ */
    async renderPractice() {
      document.title = `${t("Practise one question type")} – ${this.config.siteName}`;
      this.main.innerHTML = `
        <section class="page catalog practice-page" aria-labelledby="practice-title">
          <a class="back-link" href="#/">${ICON_BACK} ${t("Home")}</a>
          <div class="catalog-head">
            <h1 id="practice-title">${t("Practise one question type")}</h1>
            <p>${t("practice.sub")}</p>
          </div>
          <ol class="test-list" id="practice-list"><li class="skeleton" style="height:64px"></li></ol>
        </section>`;
      let types = [];
      try {
        types = (await U.api(`/api/practice?clientId=${encodeURIComponent(U.clientId())}`)).types || [];
      } catch (err) {
        const list = document.getElementById("practice-list");
        if (list) list.innerHTML = `<li class="empty-note">${t("Could not load this page. Check your connection and try again.")}</li>`;
        return;
      }
      const list = document.getElementById("practice-list");
      if (!list) return;
      const tried = types.some((x) => x.total);
      list.innerHTML = (tried ? "" : `<li class="empty-note">${t("practice.untried")}</li>`) + types.map((x) => {
        const pct = x.total ? Math.round((x.correct / x.total) * 100) : 0;
        const score = x.total
          ? `<span class="practice-score"><span class="passage-progress-bar"><span class="passage-progress-fill" style="width:${pct}%"></span></span>
              ${t("{n} of {total} correct in your tests", { n: x.correct, total: x.total })}</span>`
          : `<span class="muted-text">${t("Not tried yet")}</span>`;
        return `
          <li class="test-row practice-row">
            <h2 class="test-row-name">${esc(x.label)}</h2>
            <p class="test-row-topics">${score}</p>
            <div class="test-row-tag"><span class="test-tag">${plural(x.sets, "{n} set", "{n} sets")}</span></div>
            <div class="test-row-act"><button type="button" class="btn-primary btn-sm" data-action="practice-type" data-type="${esc(x.type)}"
              aria-label="${esc(t("Practise {type}", { type: x.label }))}">${t("Practise")}</button></div>
          </li>`;
      }).join("");
    }

    /** Open the next set of one question type: one passage, only that type, no timer and no band. */
    async startPractice(type, button) {
      if (this.preparing || !type) return;
      const key = `testday:practiceSet:${type}`;
      const n = Number(U.store.get(key, 0)) || 0;
      this.preparing = true;
      if (button) { button.classList.add("is-busy"); button.setAttribute("aria-busy", "true"); }
      try {
        const [data] = await Promise.all([U.api(`/api/practice/${encodeURIComponent(type.replace(/_/g, "-"))}?set=${n}`), U.need("exam")]);
        U.store.set(key, data.set + 1); // the next time, the next set
        U.store.remove(`mockexam:progress:${data.test.id}`);
        this.launch(data.test, "practice", U.store.get("mockexam:name", "") || "Candidate", null);
      } catch (err) {
        if (!err.loadFailed) {
          U.modal({ title: t("Could not load the test"), bodyHTML: `<p>${esc(err.status ? err.message : t("Could not load this page. Check your connection and try again."))}</p>` });
        }
      } finally {
        this.preparing = false;
        if (button && button.isConnected) { button.classList.remove("is-busy"); button.removeAttribute("aria-busy"); }
      }
    }

    /* Pre-test instructions -------------------------------------------- */
    async prepare(testId, mode, button) {
      if (this.preparing) return; // a second tap while this test is still loading
      const summary = this.tests.find((x) => x.id === testId);
      if (summary && summary.module === "speaking" && !Account.user()) {
        // Recordings are saved to the account, so Speaking needs sign-in (Test 1 stays free).
        if (!(await Account.login(t("signin.speaking")))) return;
        this.renderIfHome();
        button = null; // the page has been drawn again
      }
      // Nothing of the test is loaded until now: its questions, and the exam screen's code and styles.
      this.preparing = true;
      if (button) { button.classList.add("is-busy"); button.setAttribute("aria-busy", "true"); }
      const settle = () => {
        this.preparing = false;
        if (button) { button.classList.remove("is-busy"); button.removeAttribute("aria-busy"); }
      };
      try {
        const [test] = await Promise.all([U.api(`/api/tests/${encodeURIComponent(testId)}`), U.need("exam")]);
        // A timed Speaking test is always with the examiner bot ("ai" in older links means the same).
        this.pending = { test, mode: mode === "practice" ? "practice" : "exam" };
        if (location.hash === "#/start") this.showVerification();
        else location.hash = "#/start";
        settle();
      } catch (err) {
        settle(); // before the sign-in and plan flows below, which start this again
        // Locked tests: sign in first, or offer the plan. Retry once the user can open it.
        if (err.status === 401) {
          if (await Account.login(t("signin.locked"))) {
            this.renderIfHome();
            return this.prepare(testId, mode);
          }
          return;
        }
        if (err.status === 402) {
          const signedIn = await Account.paywall(this.tests.find((x) => x.id === testId));
          if (signedIn) {
            this.renderIfHome();
            if (Account.planActive()) return this.prepare(testId, mode);
          }
          return;
        }
        if (err.status === 403) {
          U.modal({ title: t("Coming soon…"), bodyHTML: `<p>${t("This test is not open yet. Try one of the free tests in the meantime.")}</p>` });
          return;
        }
        if (err.loadFailed) return; // U.need has already said so
        // A server answer carries its own message; with no answer at all it is the connection.
        const why = err.status ? err.message : t("Could not load this page. Check your connection and try again.");
        U.modal({ title: t("Could not load the test"), bodyHTML: `<p>${esc(why)}</p>` });
      }
    }

    /** Redraw the page if it shows tests (after sign-in, a payment or fresh data). */
    renderIfHome() {
      const path = (location.hash || "#/").slice(1).split("?")[0];
      const catalog = path.match(/^\/tests\/(listening|reading|writing|speaking)$/);
      if (path === "/" || path === "") this.renderHome();
      else if (catalog) this.renderCatalog(catalog[1]);
    }

    showVerification() {
      const { test, mode } = this.pending;
      const module = test.module;
      const timed = mode === "exam";
      const withAi = module === "speaking" && timed; // the examiner bot
      const rated = withAi && this.config.aiSpeaking; // ...that also gives a band
      const progress = U.store.get(`mockexam:progress:${test.id}`);
      const canResume = progress && progress.mode === mode;
      const checkMinutes = test.checkMinutes || 2;

      // Preload first audio file while candidate reads instructions and checks sound
      if (module === "listening" && test.parts && test.parts[0] && test.parts[0].audio && test.parts[0].audio.src) {
        try {
          const a = new Audio();
          a.preload = "auto";
          a.src = test.parts[0].audio.src;
        } catch (e) {}
      } else if (module === "speaking" && test.parts && test.parts[0] && test.parts[0].questions && test.parts[0].questions[0] && test.parts[0].questions[0].audio && test.parts[0].questions[0].audio.src) {
        try {
          const a = new Audio();
          a.preload = "auto";
          a.src = test.parts[0].questions[0].audio.src;
        } catch (e) {}
      }
      const perDay = Number(this.config.aiSpeakingPerDay) || 3;
      const instructions = module === "speaking" && withAi
        ? [
          `You talk with the <strong>examiner</strong>, face to face on screen, as in the real test. The examiner asks every question out loud; you answer by speaking. Like a real examiner, it does not reply to your answers.`,
          `<strong>Part 1:</strong> questions about familiar topics. <strong>Part 2:</strong> a topic card, <strong>1 minute</strong> to prepare and up to
            <strong>2 minutes</strong> to speak. <strong>Part 3:</strong> a discussion of wider questions. The test takes <strong>11–14 minutes</strong>.`,
          `Answer fully and naturally. When you stop talking for a few seconds the examiner moves on, so take a short breath to think if you need to, but do not stop for long. You may ask for a question to be repeated once.`,
          rated
            ? `At the end the AI examiner listens to your whole test: fluency, pauses and hesitation ("um", "er"), vocabulary, grammar and pronunciation. You get an <strong>estimated band</strong> for each official criterion, with feedback, in about a minute. You can have ${perDay} tests rated a day.`
            : `Your answers are recorded and saved to your account, so you can listen to them afterwards.`,
          `Use headphones in a quiet room, and test your microphone below.`,
        ]
        : module === "speaking"
        ? [
          `There are <strong>3 parts</strong> and the test takes <strong>11–14 minutes</strong>. The examiner asks the questions; your answers are recorded.`,
          `<strong>Part 1:</strong> questions about familiar topics. <strong>Part 2:</strong> a topic card, <strong>1 minute</strong> to prepare and up to
            <strong>2 minutes</strong> to speak. <strong>Part 3:</strong> a discussion of wider questions.`,
          timed
            ? `Recording starts automatically after each question and stops when the answer time is up. Press <strong>Finish answer</strong> when you have finished.`
            : `Practice mode shows each question, and lets you listen to your answer and record it again before you move on.`,
          `Use headphones in a quiet room, and test your microphone below.`,
          this.commerce() ? `Only you can listen to your recordings, and an examiner if you order a check.` : `Only you can listen to your recordings.`,
        ]
        : module === "listening"
        ? [
          `There are <strong>4 parts</strong> and <strong>40 questions</strong>. The recording lasts about <strong>${test.durationMinutes} minutes</strong>.`,
          timed
            ? `You will hear each part <strong>once only</strong>. The recording cannot be paused. Before each part you have time to read the questions.`
            : `Practice mode lets you <strong>pause, rewind and replay</strong> the recording, choose a part and change its speed.`,
          timed
            ? `When the recording ends you have <strong>${checkMinutes} minutes</strong> to check your answers. They are then submitted automatically.`
            : `Press <strong>Finish test</strong> when you are ready to see your score and the transcript.`,
          `Write your answers on screen as you listen. Spelling counts. Wrong answers do not lose marks.`,
          `Use headphones if you can, and check the sound below before you start.`,
        ]
        : module === "reading"
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

      const card = document.getElementById("verification-card");
      card.className = "verification-card";
      card.innerHTML = `
        <div class="verification-header">
          <div class="vh-title">${["listening", "speaking"].includes(module) ? MODULE_LABELS[module] : `Academic ${MODULE_LABELS[module]}`}</div>
          <span class="vh-mode">${rated ? "With the AI examiner" : timed ? "Timed test" : "Practice mode"}</span>
        </div>
        <form class="verification-body" id="verify-form">
          <h1 class="verify-title">${esc(test.title)}</h1>
          <div class="verification-instructions">
            <strong>Instructions to candidates</strong>
            <ul>${instructions.map((i) => `<li>${i}</li>`).join("")}</ul>
          </div>
          ${module === "listening" ? `
            <div class="sound-check">
              <div class="sound-check-text"><strong>Sound check</strong>
                <span>Press <em>Play sound</em> and set the volume so that you can hear the voice clearly.</span></div>
              <div class="sound-check-controls">
                <button type="button" class="btn-secondary" id="sound-check-btn">Play sound</button>
                <label class="sound-check-volume">Volume
                  <input type="range" id="sound-check-volume" min="0" max="100" step="5"
                    value="${Math.round(Number(U.store.get("mockexam:volume", 0.8)) * 100)}" /></label>
              </div>
            </div>` : ""}
          ${module === "speaking" ? `
            <div class="sound-check mic-check">
              <div class="sound-check-text"><strong>Microphone check</strong>
                <span id="mic-status" class="mic-status">Press <em>Test microphone</em>, allow the microphone, and say a sentence. You will hear it played back.</span>
                <div class="speak-level mic-level" aria-hidden="true"><span id="mic-level"></span></div></div>
              <div class="sound-check-controls"><button type="button" class="btn-secondary" id="mic-test-btn">Test microphone</button></div>
            </div>` : ""}
          ${canResume ? `
            <label class="check-row resume-row"><input type="checkbox" id="resume-check" checked />
              Resume my unfinished attempt (saved ${esc(U.formatDate(new Date(progress.savedAt).toISOString(), "en-GB"))})</label>` : ""}
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
      const stopSoundCheck = module === "listening" ? this.bindSoundCheck()
        : module === "speaking" ? Speaking.bindMicCheck(card) : () => {};
      document.getElementById("verify-cancel").addEventListener("click", () => {
        stopSoundCheck();
        this.pending = null;
        location.hash = "#/";
      });
      document.getElementById("verify-form").addEventListener("submit", (e) => {
        e.preventDefault();
        stopSoundCheck();
        const name = document.getElementById("cand-name").value.trim() || "Candidate";
        U.store.set("mockexam:name", name);
        const resumeBox = document.getElementById("resume-check");
        const resume = Boolean(resumeBox && resumeBox.checked);
        if (!resume) U.store.remove(`mockexam:progress:${test.id}`);
        this.launch(test, mode, name, resume ? progress : null);
      });
      // On a phone the keyboard would cover the instructions; focus the name only where there is room.
      if (window.matchMedia("(min-width: 720px)").matches) document.getElementById("cand-name").focus();
    }

    /** Sound check on the Listening instructions screen. Returns a function that stops it. */
    bindSoundCheck() {
      const btn = document.getElementById("sound-check-btn");
      const slider = document.getElementById("sound-check-volume");
      const audio = new Audio("audio/sound-check.mp3");
      audio.volume = Number(slider.value) / 100;
      const setLabel = () => { btn.textContent = audio.paused ? "Play sound" : "Stop"; };
      btn.addEventListener("click", () => {
        if (audio.paused) {
          audio.currentTime = 0;
          audio.play().catch(() => U.toast("Your browser blocked the sound. Check that this tab is not muted.", "warn"));
        } else {
          audio.pause();
        }
      });
      ["play", "pause", "ended"].forEach((ev) => audio.addEventListener(ev, setLabel));
      slider.addEventListener("input", () => {
        audio.volume = Number(slider.value) / 100;
        U.store.set("mockexam:volume", audio.volume);
      });
      return () => audio.pause();
    }

    launch(test, mode, name, saved) {
      this.pending = null;
      const summary = !test.practice && this.tests.find((x) => x.id === test.id);
      if (summary && summary.access === "free") U.track("free_test_started", { module: test.module, testId: test.id });
      this.showView("exam");
      const Exam = test.module === "speaking" && mode !== "practice" ? AiSpeakingExam
        : { writing: WritingExam, listening: ListeningExam, speaking: SpeakingExam }[test.module] || ReadingExam;
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
      result.module = test.practice ? "practice" : test.module;
      result.mode = mode;
      if (test.module === "speaking") {
        // Speaking results live on the server (the recordings), at their own address.
        location.hash = `#/speaking/${result.submissionId}`;
        return;
      }
      this.lastResult = result;
      U.store.set("mockexam:lastResult", result);
      if (location.hash === "#/results") this.route();
      else location.hash = "#/results";
    }

    /** Load a bundle for the page being opened; if it cannot load, say so on the page (U.need has shown a toast). */
    async loadFor(name) {
      try {
        await U.need(name);
        return true;
      } catch (err) {
        this.main.innerHTML = `<section class="page"><div class="notice notice-warn"><strong>${t("Could not load this page. Check your connection and try again.")}</strong></div></section>`;
        return false;
      }
    }

    async renderResults() {
      const r = this.lastResult;
      // Writing results draw the Task 1 charts, which come with the exam bundle.
      if (!(await this.loadFor(r.module === "writing" ? "exam" : "results"))) return;
      document.title = `${t("Your results")} – ${this.config.siteName}`;
      if (r.module === "practice") return Results.renderPractice(r, this.main);
      await this.loadPrices();
      const extra = {
        commerce: this.commerce(),
        next: this.nextStopHTML(r.module, r.testId, r.typeBreakdown),
        checkPrice: this.prices && this.prices.writing_check ? U.money(this.prices.writing_check) : "",
      };
      if (r.module === "writing") Results.renderWriting(r, this.main, extra);
      else if (r.module === "listening") Results.renderListening(r, this.main, extra);
      else Results.renderReading(r, this.main, extra);
    }

    nextStopHTML(module, testId, typeBreakdown) {
      const weak = Object.entries(typeBreakdown || {})
        .filter(([, v]) => v.total > 0 && v.correct < v.total)
        .sort(([, a], [, b]) => (a.correct / a.total - b.correct / b.total) || (b.total - a.total))[0];
      const tests = this.testsOf(module);
      const at = tests.findIndex((x) => x.id === testId);
      const commerce = this.commerce();
      const others = tests.slice(at + 1).concat(tests.slice(0, Math.max(at, 0)));
      const next = others.filter((x) => commerce || this.canOpen(x)).find((x) => !this.ridden[x.id]);
      const waiting = !commerce && !next && others.some((x) => !this.canOpen(x));
      if (!weak && !next && !waiting) return "";
      // Reading types can be practised on their own; the practice sets are Reading passages.
      const drill = weak && module === "reading" && this.testsOf("reading").length;
      const focus = weak ? `
        <div class="next-card">
          <h3>${t("Practise: {type}", { type: esc(weak[1].label) })}</h3>
          <p>${esc(t(`tip.${weak[0]}`))}</p>
          <p class="muted-text small-text">${t("{n} of {total} correct in this test", { n: weak[1].correct, total: weak[1].total })}</p>
          ${drill ? `<div class="next-actions"><button type="button" class="btn-secondary" data-action="practice-type" data-type="${esc(weak[0])}"
            data-track="next_practice">${t("Practise this type")}</button></div>` : ""}
        </div>` : "";
      const name = next ? this.testName(next) : "";
      const price = this.prices && this.prices.plan ? U.money(this.prices.plan) : "";
      const card = next ? `
        <div class="next-card">
          <h3>${esc(MODULE_LABELS[module])}, ${esc(name)}</h3>
          ${this.canOpen(next)
            ? `<p>${t("next.open", { module: esc(MODULE_LABELS[module]) })}</p>
              <div class="next-actions"><button type="button" class="btn-primary" data-action="start" data-test="${esc(next.id)}" data-mode="exam"
                data-track="next_test">${t("Start {name}", { name: esc(name) })}</button></div>`
            : `<p>${price ? t("next.locked", { price: `<strong>${esc(price)}</strong>` }) : t("next.locked.noprice")}</p>
              <div class="next-actions"><button type="button" class="btn-primary" data-action="buy-plan" data-track="next_test_pass">${t("Get the pass")}</button>
                <a class="btn-secondary" href="#/pricing">${t("Price")}</a></div>`}
        </div>` : waiting ? `
        <div class="next-card">
          <h3>${esc(MODULE_LABELS[module])}</h3>
          <p>${t("soon.next", { module: esc(MODULE_LABELS[module]) })}</p>
          <div class="next-actions"><a class="btn-secondary" href="#/tests/${module}">${t("All tests")}</a></div>
        </div>` : "";
      return `
        <section class="next-stop" aria-labelledby="next-stop-title">
          <h2 class="section-title" id="next-stop-title">${t("What next")}</h2>
          <div class="next-grid">${focus}${card}</div>
        </section>`;
    }

    /* Feedback ----------------------------------------------------------- */
    openFeedback() {
      const page = location.hash && location.hash.length < 80 ? location.hash : "#/";
      const rating = [1, 2, 3, 4, 5].map((n) => `
        <label class="rate-opt"><input type="radio" name="rating" value="${n}" /><span>${n}</span></label>`).join("");
      U.modal({
        title: t("Feedback"),
        buttons: [],
        bodyHTML: `
          <form id="feedback-form" class="feedback-form" novalidate>
            <label for="fb-message">${t("What should we know? Ideas, problems, anything.")}</label>
            <textarea id="fb-message" name="message" rows="5" maxlength="2000" required></textarea>
            <fieldset class="rate-row"><legend>${t("How useful is TestDay so far? (optional)")}</legend>
              <div class="rate-opts">${rating}</div>
              <div class="rate-ends"><span>${t("Not useful")}</span><span>${t("Very useful")}</span></div>
            </fieldset>
            <label for="fb-email">${t("Your email, if you would like a reply (optional)")}</label>
            <input id="fb-email" name="email" type="email" maxlength="254" autocomplete="email" />
            <p class="form-error" id="fb-error" role="alert" hidden></p>
            <div class="feedback-actions">
              <button type="button" class="btn-secondary" data-close>${t("Cancel")}</button>
              <button type="submit" class="btn-primary">${t("Send")}</button>
            </div>
          </form>`,
        onOpen: (root, close) => {
          const form = root.querySelector("#feedback-form");
          const error = root.querySelector("#fb-error");
          root.querySelector("[data-close]").addEventListener("click", () => close(null));
          root.querySelector("#fb-message").focus();
          form.addEventListener("input", () => { error.hidden = true; });
          form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const message = form.message.value.trim();
            if (!message) {
              error.textContent = t("Please write a message.");
              error.hidden = false;
              form.message.focus();
              return;
            }
            const button = form.querySelector('button[type="submit"]');
            button.disabled = true;
            button.classList.add("is-busy");
            try {
              await U.api("/api/feedback", { method: "POST", body: JSON.stringify({
                message, rating: Number(form.rating.value) || null, email: form.email.value.trim(), page, clientId: U.clientId(),
              }) });
              close(true);
              U.toast(t("Thank you! We read every message."));
            } catch (err) {
              error.textContent = err.message;
              error.hidden = false;
              button.disabled = false;
              button.classList.remove("is-busy");
            }
          });
        },
      });
    }

    /* Static pages ----------------------------------------------------- */

    /** The site's email for support and requests: CONTACT_EMAIL, or the owner's address. */
    contactHTML() {
      const email = this.config.contactEmail || SUPPORT_EMAIL;
      return `<a href="mailto:${esc(email)}">${esc(email)}</a>`;
    }

    /** Terms of use, privacy policy and refund policy. The wording lives in strings.js. */
    renderLegal(page) {
      const name = esc(this.config.siteName);
      const contact = this.contactHTML();
      const days = Number(this.config.speakingKeepDays) || 60;
      const p = this.prices || {};
      const price = (n) => (n ? esc(U.money(n)) : "…");
      const commerce = this.commerce();
      const v = (key) => (commerce ? key : `${key}.free`); // the wording for a site that sells nothing yet
      const section = (key, vars, bodyKey = key) => `<h2>${t(`${key}.h`, { name })}</h2><p>${t(bodyKey, { name, ...vars })}</p>`;
      const pages = {
        terms: [t("Terms of use"), `
          <p class="lead-text">${t(v("terms.lead"), { name })}</p>
          ${section("terms.service")}
          ${section("terms.account", {}, v("terms.account"))}
          ${commerce ? `${section("terms.pass", { price: price(p.plan) })}
          ${section("terms.checks", { writing: price(p.writing_check), speaking: price(p.speaking_check) })}
          ${section("terms.payment")}
          ${section("terms.refunds")}` : ""}
          ${section("terms.use", {}, v("terms.use"))}
          ${section("terms.work", { days }, v("terms.work"))}
          ${section("terms.availability", {}, v("terms.availability"))}
          ${section("terms.liability", {}, v("terms.liability"))}
          ${section("terms.law")}`],
        privacy: [t("Privacy policy"), `
          <p class="lead-text">${t("privacy.lead", { name })}</p>
          <h2>${t("privacy.collect.h")}</h2>
          <ul>
            <li>${t("about.privacy.1")}</li>
            <li>${t(v("about.privacy.2"))}</li>
            <li>${t(v("about.privacy.3"), { days })}</li>
            ${commerce ? `<li>${t("about.privacy.4")}</li>
            <li>${t("about.privacy.5")}</li>` : ""}
            ${this.config.aiMarking ? `<li>${t("about.privacy.ai")}</li>` : ""}
            <li>${t(v("privacy.analytics"))}</li>
            <li>${t("privacy.feedback")}</li>
            <li>${t("about.privacy.6")}</li>
            <li>${t("privacy.cookies")}</li>
          </ul>
          <h2>${t("privacy.where.h")}</h2><p>${t(v("privacy.where"))}</p>
          <h2>${t("privacy.keep.h")}</h2><p>${t(v("privacy.keep"), { days })}</p>
          <h2>${t("privacy.rights.h")}</h2><p>${t(v("privacy.rights"), { contact })}</p>
          <p>${t("privacy.children", { name })}</p>`],
        refunds: [t("Refund policy"), `
          <p class="lead-text">${t("refund.lead")}</p>
          ${section("refund.pass")}
          ${section("refund.checks")}
          ${section("refund.how", { contact })}
          ${section("refund.money")}`],
      };
      const [title, body] = pages[page];
      document.title = `${title} – ${this.config.siteName}`;
      this.main.innerHTML = `
        <section class="page prose legal-page">
          <h1>${title}</h1>
          <p class="muted-text small-text">${t("legal.updated", { date: "16 October 2026" })}</p>
          ${body}
          <p class="legal-contact">${t("legal.contact", { contact })}</p>
          <p class="muted-text small-text">${t("about.independent", { name })}</p>
        </section>`;
      // The terms quote the prices; draw again once they arrive (only if they did, so a failure cannot loop).
      if (!this.prices && page === "terms") {
        this.loadPrices().then(() => { if (this.prices && location.hash === "#/terms") this.renderLegal(page); });
      }
    }

    renderAbout() {
      document.title = `${t("About")} – ${this.config.siteName}`;
      const name = esc(this.config.siteName);
      this.main.innerHTML = `
        <section class="page prose">
          <h1>${t("About {name}", { name })}</h1>
          <p class="lead-text">${t("about.lead", { name })}</p>

          <h2>${t("What is inside")}</h2>
          <ul>
            <li>${t("about.content.1")}</li>
            <li>${t("about.content.2")}</li>
            <li>${t("about.content.3")}</li>
          </ul>

          <h2>${t("About your scores")}</h2>
          <ul>
            <li>${t("about.scores.lr")}</li>
            <li>${this.config.aiMarking ? t("about.scores.writing.ai") : t("about.scores.writing")}</li>
            <li>${t(this.commerce() ? "about.scores.speaking" : "about.scores.speaking.free")}</li>
          </ul>

          <h2>${t("Independent website")}</h2>
          <p>${t("about.independent", { name })}</p>

          <h2>${this.commerce() ? t("Privacy, terms and refunds") : t("Privacy and terms")}</h2>
          <p>${t(this.commerce() ? "about.legal" : "about.legal.free", { name })}</p>
          <ul class="legal-links">
            <li><a href="#/privacy">${t("Privacy policy")}</a></li>
            <li><a href="#/terms">${t("Terms of use")}</a></li>
            ${this.commerce() ? `<li><a href="#/refunds">${t("Refund policy")}</a></li>` : ""}
          </ul>
          <h2>${t("Contact")}</h2>
          <p>${this.contactHTML()}</p>
        </section>`;
    }
  }

  window.app = new App();
})();
