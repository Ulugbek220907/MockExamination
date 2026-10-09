/**
 * Application controller: routing, the home page (the line network),
 * pre-test instructions, launching exams, results, and the resources /
 * about pages.
 *
 * Routes: #/ (tests), #/resources, #/about, #/start (instructions),
 *         #/exam (active test), #/results (last result), #/speaking/<id>
 *         (a recorded Speaking test), and the account
 *         pages from account.js: #/pricing, #/account, #/examiners,
 *         #/check/<id>, #/examiner, #/admin.
 */
(function () {
  "use strict";

  const esc = (v) => U.escapeHtml(v);

  // Free official preparation material. We link to it; we never copy it.
  const OFFICIAL_RESOURCES = [
    {
      group: "res.familiar.group",
      note: "res.familiar.note",
      links: [
        { title: "IELTS on computer familiarisation test", org: "British Council", url: "https://takeielts.britishcouncil.org/take-ielts/prepare/free-ielts-english-practice-tests/ielts-on-computer/familiarisation-test" },
        { title: "IELTS familiarisation tests", org: "IDP IELTS", url: "https://ielts.idp.com/about/ielts-familiarisation-tests" },
      ],
    },
    {
      group: "res.samples.group",
      note: "res.samples.note",
      links: [
        { title: "Official sample test questions", org: "IELTS.org", url: "https://ielts.org/take-a-test/preparation-resources/sample-test-questions" },
        { title: "IELTS trial test", org: "IELTS.org", url: "https://ielts.org/take-a-test/preparation-resources/ielts-trial-test" },
        { title: "Free IELTS practice tests", org: "British Council", url: "https://takeielts.britishcouncil.org/take-ielts/prepare/free-ielts-english-practice-tests" },
        { title: "IELTS preparation materials", org: "IDP IELTS", url: "https://ielts.idp.com/prepare" },
        { title: "IELTS preparation", org: "Cambridge English", url: "https://www.cambridgeenglish.org/exams-and-tests/ielts/preparation/" },
      ],
    },
    {
      group: "res.format.group",
      note: "res.format.note",
      links: [
        { title: "Listening test format", org: "IELTS.org", url: "https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-listening" },
        { title: "Academic Reading test format", org: "IELTS.org", url: "https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-reading" },
        { title: "Academic Writing test format", org: "IELTS.org", url: "https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-writing" },
        { title: "Writing test preparation resources", org: "IELTS.org", url: "https://ielts.org/take-a-test/preparation-resources/writing-test-resources" },
        { title: "IELTS scoring in detail (band descriptors)", org: "IELTS.org", url: "https://ielts.org/organisations/ielts-for-organisations/ielts-scoring-in-detail" },
      ],
    },
    {
      group: "res.reading.group",
      note: "res.reading.note",
      links: [
        { title: "Featured articles", org: "Wikipedia (CC BY-SA)", url: "https://en.wikipedia.org/wiki/Wikipedia:Featured_articles" },
        { title: "Science and research news", org: "NASA (public domain)", url: "https://www.nasa.gov/news/" },
        { title: "Climate and ocean explainers", org: "NOAA (public domain)", url: "https://www.noaa.gov/education" },
        { title: "Free e-books of classic non-fiction", org: "Project Gutenberg", url: "https://www.gutenberg.org/" },
      ],
    },
    {
      group: "res.listening.group",
      note: "res.listening.note",
      links: [
        { title: "6 Minute English", org: "BBC Learning English", url: "https://www.bbc.co.uk/learningenglish/english/features/6-minute-english" },
        { title: "Talks with interactive transcripts", org: "TED", url: "https://www.ted.com/talks" },
        { title: "Science podcasts", org: "NASA", url: "https://www.nasa.gov/podcasts/" },
      ],
    },
  ];

  const MODULE_LABELS = { reading: "Reading", listening: "Listening", writing: "Writing", speaking: "Speaking" };

  // The four lines, in the order of the real test day.
  const LINES = [
    { module: "listening", letter: "L", cls: "line-l" },
    { module: "reading", letter: "R", cls: "line-r" },
    { module: "writing", letter: "W", cls: "line-w" },
    { module: "speaking", letter: "S", cls: "line-s" },
  ];
  const lineOf = (module) => LINES.find((l) => l.module === module) || LINES[1];

  const ICON_ARROW = `<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h9M8.5 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const ICON_LOCK = `<svg width="10" height="11" viewBox="0 0 10 11" aria-hidden="true"><path fill="currentColor" d="M8 4.5V3.4a3 3 0 0 0-6 0v1.1H1v6h8v-6H8zM3.4 3.4a1.6 1.6 0 0 1 3.2 0v1.1H3.4V3.4z"/></svg>`;

  class App {
    constructor() {
      this.config = { siteName: "TestDay", aiMarking: false, contactEmail: "" };
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
      I18N.applyStatic();
      window.addEventListener("hashchange", () => this.route());
      document.addEventListener("langchange", () => {
        Account.renderAccountSlot();
        if (!this.exam && document.getElementById("site-view").classList.contains("active")) this.route();
      });
      this.main.addEventListener("click", (e) => this.onMainClick(e));
      document.getElementById("account-slot").addEventListener("click", (e) => Account.onClick(e));
      document.addEventListener("keydown", (e) => { if (e.key === "Escape") this.closeSigns(); });
      Account.renderAccountSlot();
      try {
        const [config, data] = await Promise.all([U.api("/api/config"), U.api("/api/tests"), Account.refreshMe()]);
        this.config = { ...this.config, ...config };
        this.tests = data.tests || [];
        this.modules = data.modules || {};
      } catch (err) {
        this.loadError = true;
      }
      Account.setConfig(this.config);
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
      const [path, query] = hash.slice(1).split("?");
      const params = new URLSearchParams(query || "");
      const check = path.match(/^\/check\/(\d+)$/);
      const spoken = path.match(/^\/speaking\/(\d+)$/);
      window.scrollTo(0, 0);
      if (path === "/resources") this.renderResources();
      else if (path === "/about") this.renderAbout();
      else if (path === "/results" && this.lastResult) this.renderResults();
      else if (path === "/pricing") await Account.renderPricing(this.main);
      else if (path === "/account") await Account.renderAccount(this.main);
      else if (path === "/examiners") await Account.renderExaminers(this.main, params);
      else if (path === "/examiner") await Account.renderExaminerDashboard(this.main);
      else if (path === "/admin") await Account.renderAdmin(this.main, params);
      else if (check) await Account.renderCheck(this.main, check[1]);
      else if (spoken) await Speaking.renderResult(this.main, spoken[1]);
      else this.renderHome();
    }

    setNav(hash) {
      const path = hash.slice(1).split("?")[0];
      const key = { "/resources": "resources", "/about": "about", "/pricing": "pricing", "/examiners": "examiners",
        "/account": "account", "/examiner": "examiner", "/admin": "admin" }[path] || (path.startsWith("/check") ? "account" : "home");
      document.querySelectorAll("[data-nav]").forEach((a) => {
        if (a.dataset.nav === key) a.setAttribute("aria-current", "page");
        else a.removeAttribute("aria-current");
      });
    }

    showView(name) {
      const ids = { site: "site-view", verification: "verification-view", exam: "exam-screen" };
      Object.entries(ids).forEach(([k, id]) => document.getElementById(id).classList.toggle("active", k === name));
      document.body.classList.toggle("in-exam", name === "exam");
      // The instructions and the exam stay in English, like the real test.
      document.documentElement.lang = name === "site" ? I18N.lang() : "en";
    }

    onMainClick(e) {
      if (Account.onClick(e)) return;
      const station = e.target.closest("[data-station]");
      if (station) return this.toggleSign(station);
      const el = e.target.closest("[data-action]");
      if (!el) return;
      if (el.dataset.action === "start") this.prepare(el.dataset.test, el.dataset.mode);
      if (el.dataset.action === "retake" && this.lastResult) this.prepare(this.lastResult.testId, this.lastResult.mode || "exam");
      if (el.dataset.action === "scroll") {
        const target = document.getElementById(el.dataset.target);
        if (target) target.scrollIntoView({ block: "start" });
      }
    }

    /* Home: the network ------------------------------------------------ */
    renderHome() {
      document.title = `${this.config.siteName} – ${t("title.home")}`;
      this.main.innerHTML = `
        <section aria-labelledby="home-title">
          <div class="network-head">
            <div>
              <h1 id="home-title">${t("Every line ends at test day.")}</h1>
              <p>${t("home.lead")}</p>
            </div>
            <div class="network-key" aria-hidden="true">
              <span><i class="key-ring is-free"></i>${t("Free test")}</span>
              <span><i class="key-ring"></i>${t("With the pass")}</span>
              <span><i class="key-ring is-done"></i>${t("Taken, with your band")}</span>
            </div>
          </div>
          ${this.loadError ? `<div class="notice notice-warn"><strong>${t("Could not load the tests. Please refresh the page.")}</strong></div>` : ""}
          <div class="network" id="network">
            <svg class="network-svg" id="network-svg" aria-hidden="true"></svg>
            <ol class="lines-list" id="lines-list"></ol>
            <button type="button" class="hub" data-action="scroll" data-target="ride">
              <span class="hub-capsule" aria-hidden="true"></span>
              <span class="hub-text"><span class="hub-name">${t("Test day")}</span><span class="hub-sub">${t("All lines meet here")}</span></span>
            </button>
          </div>
        </section>

        <section class="home-section" id="ride" aria-labelledby="ride-title">
          <h2 id="ride-title">${t("How a test works")}</h2>
          <p class="muted-text">${t("ride.sub")}</p>
          <ol class="ride">
            <li><span class="ride-stop" aria-hidden="true"></span><div><h3>${t("ride.1.title")}</h3><p>${t("ride.1.text")}</p></div></li>
            <li><span class="ride-stop" aria-hidden="true"></span><div><h3>${t("ride.2.title")}</h3><p>${t("ride.2.text")}</p></div></li>
            <li><span class="ride-stop" aria-hidden="true"></span><div><h3>${t("ride.3.title")}</h3><p>${t("ride.3.text")}</p></div></li>
            <li><span class="ride-stop" aria-hidden="true"></span><div><h3>${t("ride.4.title")}</h3><p>${t("ride.4.text")}</p></div></li>
          </ol>
        </section>

        <section id="history-section" class="home-section" hidden></section>

        <section class="home-section pass-wrap" id="pass" aria-labelledby="pass-title">
          <div class="pass-card" aria-hidden="true">
            <div class="pass-stripes"><span style="background:var(--line-l)"></span><span style="background:var(--line-r)"></span><span style="background:var(--line-w)"></span><span style="background:var(--line-s)"></span></div>
            <div class="pass-top"><span class="site-name">${esc(this.config.siteName)}</span><span class="pass-kind">${t("Monthly pass")}</span></div>
            <div class="pass-price" data-price="plan">${this.prices ? this.priceHTML(this.prices.plan) : "&nbsp;"}</div>
            <div class="pass-bottom">
              <span class="pass-bullets">${LINES.map((l) => `<span class="bullet sm ${l.cls}">${l.letter}</span>`).join("")}</span>
              <span>${t("Every station")}</span>
            </div>
          </div>
          <div class="pass-copy">
            <h2 id="pass-title">${t("One pass opens every station")}</h2>
            <p class="muted-text">${t("pass.text")}</p>
            <ul class="plan-points">
              <li>${t("All Listening, Reading, Writing and Speaking tests")}</li>
              <li>${t("Your first payment gives you two months")}</li>
              <li>${t("No automatic charges: renew when you want")}</li>
            </ul>
            <div class="btn-row">
              <button type="button" class="btn-primary btn-lg" data-action="buy-plan">${Account.planActive() ? t("Add another month") : t("Get the pass")}</button>
              <a class="btn-secondary btn-lg" href="#/pricing">${t("See prices")}</a>
            </div>
            <p class="checks-line" data-checks>${this.checksLine()}</p>
          </div>
        </section>`;
      this.renderNetwork();
      this.loadHistory();
      this.loadPrices();
    }

    priceHTML(amount) {
      return `${esc(I18N.number(amount))}<small>${t("so'm / month")}</small>`;
    }

    checksLine() {
      const p = this.prices;
      const w = p ? esc(I18N.money(p.writing_check)) : "…";
      const s = p ? esc(I18N.money(p.speaking_check)) : "…";
      return `${t("checks.line", { writing: w, speaking: s })} <a href="#/examiners">${t("Meet the examiners")}</a>`;
    }

    async loadPrices() {
      if (this.prices) return;
      try {
        const b = await Account.billing();
        this.prices = b.prices || null;
      } catch (e) { return; }
      const price = this.main.querySelector('[data-price="plan"]');
      if (price && this.prices) price.innerHTML = this.priceHTML(this.prices.plan);
      const checks = this.main.querySelector("[data-checks]");
      if (checks) checks.innerHTML = this.checksLine();
    }

    hasProgress(testId) {
      return Boolean(U.store.get(`mockexam:progress:${testId}`));
    }

    canOpen(t) {
      return t.access === "free" || Account.planActive() || ["admin", "examiner"].includes(Account.role());
    }

    testsOf(module) {
      return this.tests.filter((x) => x.module === module).sort((a, b) => (a.sortOrder - b.sortOrder) || a.id.localeCompare(b.id));
    }

    testName(test) {
      const n = this.testsOf(test.module).indexOf(test) + 1;
      return t("Test {n}", { n: n || test.sortOrder || 1 });
    }

    lineMeta(module) {
      return {
        listening: t("line.listening"),
        reading: t("line.reading"),
        writing: t("line.writing"),
        speaking: t("line.speaking"),
      }[module];
    }

    renderNetwork() {
      const list = document.getElementById("lines-list");
      if (!list) return;
      list.innerHTML = LINES.map((line) => {
        const tests = this.testsOf(line.module);
        const done = tests.filter((x) => this.ridden[x.id]);
        const next = done.length ? tests.find((x) => !this.ridden[x.id]) : null;
        const free = tests.find((x) => x.access === "free" && !this.ridden[x.id]);
        return `
          <li class="line-row ${line.cls}" data-line="${line.module}">
            <div class="line-main">
              <div class="line-label">
                <span class="bullet">${line.letter}</span>
                <div><div class="line-name">${MODULE_LABELS[line.module]}</div><span class="line-meta">${esc(this.lineMeta(line.module))}</span></div>
                ${free ? `<button type="button" class="start-free start-free-mobile" data-action="start" data-test="${esc(free.id)}" data-mode="exam"
                  aria-label="${esc(t("Start {name}, free", { name: `${MODULE_LABELS[line.module]}, ${this.testName(free)}` }))}">${t("Start free")} ${ICON_ARROW}</button>` : ""}
              </div>
              <div class="track">
                <ol class="stations">${tests.map((x) => this.stationHTML(x, line, x === next)).join("")}</ol>
              </div>
            </div>
            <div class="station-sign" id="sign-${line.module}" role="region" aria-live="polite" hidden></div>
          </li>`;
      }).join("");
      this.drawNetwork();
    }

    stationHTML(test, line, isNext) {
      const ride = this.ridden[test.id];
      const name = this.testName(test);
      const label = `${MODULE_LABELS[test.module]}, ${name}`;
      const btn = (inner, extra = "") => `
        <button type="button" class="station-btn" data-station="${esc(test.id)}" aria-expanded="false"
          aria-controls="sign-${line.module}" aria-label="${esc(label)}: ${esc(t("details"))}" ${extra}>
          ${inner}<span class="station-name">${esc(name)}</span></button>`;
      if (test.access === "free" && !ride) {
        return `
          <li class="station is-free">
            <div class="station-start">
              ${btn(`<span class="station-ring" aria-hidden="true"></span>`)}
              <button type="button" class="start-free" data-action="start" data-test="${esc(test.id)}" data-mode="exam"
                aria-label="${esc(t("Start {name}, free", { name: label }))}">${t("Start free")} ${ICON_ARROW}</button>
            </div>
          </li>`;
      }
      const band = ride && ride.band !== null && ride.band !== undefined ? IeltsScoring.formatBand(ride.band) : "";
      const ring = ride
        ? `<span class="station-ring">${esc(band)}</span>`
        : `<span class="station-ring" aria-hidden="true">${this.canOpen(test) ? "" : ICON_LOCK}</span>`;
      return `<li class="station ${ride ? "is-done" : ""} ${isNext ? "is-next" : ""}">${btn(ring, isNext ? `data-next="${esc(t("Next"))}"` : "")}</li>`;
    }

    /** Curves that carry every line into the Test day interchange. */
    drawNetwork() {
      const net = document.getElementById("network");
      if (!net) return;
      const draw = () => {
        const svg = net.querySelector("#network-svg");
        const hub = net.querySelector(".hub-capsule");
        if (!svg || !hub) return;
        const box = net.getBoundingClientRect();
        const tracks = [...net.querySelectorAll(".track")];
        if (!tracks.length || !box.width) return;
        const step = 12;
        const n = tracks.length;
        // Wide screens: the lines curve into the interchange at the right. Phones: they turn
        // down a gutter on the right, side by side, into the interchange below the last line.
        const narrow = window.matchMedia("(max-width: 860px)").matches;
        hub.style.height = narrow ? "" : `${n * step + 14}px`;
        hub.style.width = narrow ? `${n * step + 14}px` : "";
        const hb = hub.getBoundingClientRect();
        const hx = hb.left - box.left + hb.width / 2;
        const hy = hb.top - box.top + hb.height / 2;
        const f = (v) => v.toFixed(1);
        const paths = tracks.map((tr, i) => {
          const r = tr.getBoundingClientRect();
          const x0 = r.right - box.left - 1;
          const y0 = r.top - box.top + r.height / 2;
          const color = getComputedStyle(tr).getPropertyValue("--line").trim();
          let d;
          if (narrow) {
            const lane = hx + ((n - 1) / 2 - i) * step;
            const rad = 14;
            d = `M${f(x0)},${f(y0)} H${f(lane - rad)} Q${f(lane)},${f(y0)} ${f(lane)},${f(y0 + rad)} V${f(hy)}`;
          } else {
            const y1 = hy + (i - (n - 1) / 2) * step;
            const mid = x0 + (hx - x0) * 0.5;
            d = `M${f(x0)},${f(y0)} C${f(mid)},${f(y0)} ${f(mid)},${f(y1)} ${f(hx)},${f(y1)}`;
          }
          return `<path d="${d}" fill="none" stroke="${color}" stroke-width="10" stroke-linecap="butt"/>`;
        });
        svg.setAttribute("viewBox", `0 0 ${box.width.toFixed(1)} ${box.height.toFixed(1)}`);
        svg.innerHTML = paths.join("");
      };
      draw();
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
      if (this.netObserver) this.netObserver.disconnect();
      if (window.ResizeObserver) {
        this.netObserver = new ResizeObserver(() => requestAnimationFrame(draw));
        this.netObserver.observe(net);
      }
    }

    closeSigns() {
      document.querySelectorAll(".station-sign").forEach((s) => { s.hidden = true; s.innerHTML = ""; });
      document.querySelectorAll(".station-btn[aria-expanded='true']").forEach((b) => b.setAttribute("aria-expanded", "false"));
    }

    toggleSign(btn) {
      const open = btn.getAttribute("aria-expanded") === "true";
      this.closeSigns();
      if (open) return;
      const test = this.tests.find((x) => x.id === btn.dataset.station);
      if (!test) return;
      const line = lineOf(test.module);
      const sign = document.getElementById(`sign-${test.module}`);
      btn.setAttribute("aria-expanded", "true");
      sign.innerHTML = this.signHTML(test, line);
      sign.hidden = false;
      this.drawNetwork();
      const primary = sign.querySelector(".btn-line");
      if (primary) primary.focus({ preventScroll: true });
      sign.scrollIntoView({ block: "nearest" });
    }

    signHTML(test, line) {
      const ride = this.ridden[test.id];
      const items = test.module === "reading" ? test.passages.map((p) => [`P${p.number}`, p.title])
        : test.module === "listening" ? test.parts.map((p) => [`${p.number}`, p.title])
          : test.module === "speaking" ? test.parts.map((p) => [`${p.number}`, (p.topics || []).join(" · ") || p.title])
            : test.tasks.map((k) => [`T${k.number}`, k.title]);
      const meta = test.module === "writing" ? t("{min} minutes · 2 tasks", { min: test.durationMinutes })
        : test.module === "speaking" ? t("11–14 minutes · {q} questions", { q: test.totalQuestions })
          : test.module === "listening" ? t("About {min} minutes · {q} questions", { min: test.durationMinutes, q: test.totalQuestions })
            : t("{min} minutes · {q} questions", { min: test.durationMinutes, q: test.totalQuestions });
      const tag = test.access === "free" ? `<span class="sign-tag is-free">${t("Free")}</span>`
        : this.canOpen(test) ? `<span class="sign-tag">${t("In your pass")}</span>`
          : `<span class="sign-tag">${t("With the pass")}</span>`;
      const extra = [
        this.hasProgress(test.id) ? t("Unfinished attempt saved") : "",
        ride && ride.band !== null && ride.band !== undefined ? t("Your last band: {band}", { band: IeltsScoring.formatBand(ride.band) }) : "",
      ].filter(Boolean).join(" · ");
      return `
        <div>
          <div class="sign-title"><span class="bullet sm">${line.letter}</span><h3>${esc(MODULE_LABELS[test.module])} · ${esc(this.testName(test))}</h3>${tag}</div>
          <ul class="sign-items">${items.map(([k, v]) => `<li><b>${esc(k)}</b>${esc(v)}</li>`).join("")}</ul>
          <p class="sign-meta">${esc(meta)}${extra ? ` · ${esc(extra)}` : ""}</p>
        </div>
        <div class="sign-actions">
          <button type="button" class="btn-secondary" data-action="start" data-test="${esc(test.id)}" data-mode="practice">${t("Practice, no timer")}</button>
          <button type="button" class="btn-line" data-action="start" data-test="${esc(test.id)}" data-mode="exam">${ride ? t("Take it again") : t("Start timed test")} ${ICON_ARROW}</button>
        </div>`;
    }

    async loadHistory() {
      let items = [];
      try {
        items = (await U.api(`/api/history?clientId=${encodeURIComponent(U.clientId())}`)).items || [];
      } catch (e) { return; }
      this.history = items;
      // The latest attempt at each test marks its station as ridden.
      const ridden = {};
      [...items].reverse().forEach((i) => { ridden[i.testId] = { band: i.bandScore, module: i.module }; });
      const changed = JSON.stringify(ridden) !== JSON.stringify(this.ridden);
      this.ridden = ridden;
      U.store.set("testday:ridden", ridden);
      if (changed && document.getElementById("lines-list")) this.renderNetwork();
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
            const line = lineOf(i.module);
            const name = test ? `${MODULE_LABELS[test.module]} · ${this.testName(test)}` : i.testId;
            return `
            <tr>
              <td>${esc(U.formatDate(i.createdAt))}</td>
              <td><span class="bullet sm ${line.cls}" aria-hidden="true">${line.letter}</span>${esc(name)}${i.mode === "practice" ? ` <span class="muted-text">(${t("practice")})</span>` : ""}</td>
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
      const band = i.bandScore !== null && i.bandScore !== undefined ? `<strong>${t("Band {band}", { band: IeltsScoring.formatBand(i.bandScore) })}</strong> ` : "";
      const status = i.checkStatus && i.checkStatus !== "completed" ? `<span class="muted-text">${t("Examiner marking")}</span> ` : "";
      return `${band}${status}<a href="#/speaking/${Number(i.id)}">${t("Listen ({n} answers)", { n: i.answered })}</a>`;
    }

    /* Pre-test instructions -------------------------------------------- */
    async prepare(testId, mode) {
      const summary = this.tests.find((x) => x.id === testId);
      if (summary && summary.module === "speaking" && !Account.user()) {
        // Recordings are saved to the account, so Speaking needs sign-in (Test 1 stays free).
        if (!(await Account.login(t("signin.speaking")))) return;
        this.renderIfHome();
      }
      try {
        const test = await U.api(`/api/tests/${encodeURIComponent(testId)}`);
        this.pending = { test, mode: mode === "practice" ? "practice" : "exam" };
        if (location.hash === "#/start") this.showVerification();
        else location.hash = "#/start";
      } catch (err) {
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
        U.modal({ title: t("Could not load the test"), bodyHTML: `<p>${esc(err.message)}</p>` });
      }
    }

    renderIfHome() {
      const path = (location.hash || "#/").slice(1).split("?")[0];
      if (path === "/" || path === "") this.renderHome();
    }

    showVerification() {
      const { test, mode } = this.pending;
      const module = test.module;
      const timed = mode === "exam";
      const progress = U.store.get(`mockexam:progress:${test.id}`);
      const canResume = progress && progress.mode === mode;
      const checkMinutes = test.checkMinutes || 2;
      const line = lineOf(module);
      const instructions = module === "speaking"
        ? [
          `There are <strong>3 parts</strong> and the test takes <strong>11–14 minutes</strong>. The examiner asks the questions; your answers are recorded.`,
          `<strong>Part 1:</strong> questions about familiar topics. <strong>Part 2:</strong> a topic card, <strong>1 minute</strong> to prepare and up to
            <strong>2 minutes</strong> to speak. <strong>Part 3:</strong> a discussion of wider questions.`,
          timed
            ? `Recording starts automatically after each question and stops when the answer time is up. Press <strong>Finish answer</strong> when you have finished.`
            : `Practice mode shows each question, and lets you listen to your answer and record it again before you move on.`,
          `Use headphones in a quiet room, and test your microphone below.`,
          `Only you can listen to your recordings, and an examiner if you order a check.`,
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
      card.className = `verification-card ${line.cls}`;
      card.innerHTML = `
        <div class="verification-header">
          <div class="vh-title"><span class="bullet sm">${line.letter}</span> ${["listening", "speaking"].includes(module) ? MODULE_LABELS[module] : `Academic ${MODULE_LABELS[module]}`}</div>
          <span class="vh-mode">${timed ? "Timed test" : "Practice mode"}</span>
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
            <button type="submit" class="btn-line btn-lg">Start test</button>
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
      this.showView("exam");
      const Exam = { writing: WritingExam, listening: ListeningExam, speaking: SpeakingExam }[test.module] || ReadingExam;
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

    renderResults() {
      const r = this.lastResult;
      document.title = `${t("Your results")} – ${this.config.siteName}`;
      if (r.module === "writing") Results.renderWriting(r, this.main);
      else if (r.module === "listening") Results.renderListening(r, this.main);
      else Results.renderReading(r, this.main);
    }

    /* Static pages ----------------------------------------------------- */
    renderResources() {
      document.title = `${t("Free official resources")} – ${this.config.siteName}`;
      this.main.innerHTML = `
        <section class="page">
          <h1>${t("Free official IELTS resources")}</h1>
          <p class="lead-text">${t("res.lead")}</p>
          ${OFFICIAL_RESOURCES.map((g) => `
            <div class="resource-group">
              <h2 class="section-title">${t(g.group)}</h2>
              <p class="muted-text">${t(g.note)}</p>
              <ul class="resource-list">
                ${g.links.map((l) => `
                  <li><a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer" lang="en">${esc(l.title)}</a>
                    <span class="resource-org">${esc(l.org)}</span></li>`).join("")}
              </ul>
            </div>`).join("")}
          <div class="notice notice-info"><strong>${t("Tip")}</strong><span>${t("res.tip")}</span></div>
        </section>`;
    }

    renderAbout() {
      document.title = `${t("About, privacy and legal")} – ${this.config.siteName}`;
      const name = esc(this.config.siteName);
      const contact = this.config.contactEmail
        ? `<a href="mailto:${esc(this.config.contactEmail)}">${esc(this.config.contactEmail)}</a>`
        : t("the contact address published by the site owner");
      const days = Number(this.config.speakingKeepDays) || 60;
      this.main.innerHTML = `
        <section class="page prose">
          <h1>${t("About {name}", { name })}</h1>
          <p class="lead-text">${t("about.lead", { name })}</p>

          <h2>${t("Independent website")}</h2>
          <p>${t("about.independent", { name })}</p>

          <h2>${t("Our content")}</h2>
          <ul>
            <li>${t("about.content.1")}</li>
            <li>${t("about.content.2")}</li>
            <li>${t("about.content.3")}</li>
            <li>${t("about.content.4")}</li>
          </ul>

          <h2>${t("About your scores")}</h2>
          <ul>
            <li>${t("about.scores.lr")}</li>
            <li>${this.config.aiMarking ? t("about.scores.writing.ai") : t("about.scores.writing")}</li>
            <li>${t("about.scores.speaking")}</li>
          </ul>

          <h2>${t("Privacy")}</h2>
          <ul>
            <li>${t("about.privacy.1")}</li>
            <li>${t("about.privacy.2")}</li>
            <li>${t("about.privacy.3", { days })}</li>
            <li>${t("about.privacy.4")}</li>
            <li>${t("about.privacy.5")}</li>
            ${this.config.aiMarking ? `<li>${t("about.privacy.ai")}</li>` : ""}
            <li>${t("about.privacy.6")}</li>
            <li>${t("about.privacy.7", { contact })}</li>
          </ul>
        </section>`;
    }
  }

  window.app = new App();
})();
