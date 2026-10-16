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
  /** "Test 7" with the word in its own span, so a crowded line can show just "7". */
  const stationLabel = (name) => {
    const m = /^(\D+?)\s*(\d+)$/.exec(name);
    return m ? `<span class="station-word">${esc(m[1])} </span>${esc(m[2])}` : esc(name);
  };

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
      this.main.addEventListener("click", (e) => this.onMainClick(e));
      document.getElementById("account-slot").addEventListener("click", (e) => Account.onClick(e));
      document.addEventListener("keydown", (e) => { if (e.key === "Escape") this.closeSigns(); });

      // Warm bundle and test data as soon as the user hovers or focuses on a station or button
      const onIntent = (e) => {
        const target = e.target.closest("[data-station], [data-test], [data-action='start']");
        if (!target) return;
        U.prefetch("exam");
        // Only tests this visitor can open: a locked one would just be refused (401/402).
        const testId = target.dataset.station || target.dataset.test;
        const test = testId && this.tests.find((x) => x.id === testId);
        if (test && this.canOpen(test)) U.api(`/api/tests/${encodeURIComponent(testId)}`).catch(() => {});
      };
      this.main.addEventListener("pointerover", onIntent, { passive: true });
      this.main.addEventListener("focusin", onIntent, { passive: true });

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
      Account.renderAccountSlot();
      document.querySelectorAll("[data-site-name]").forEach((el) => { el.textContent = this.config.siteName; });
      Promise.resolve(this.route()).finally(() => {
        this.main.removeAttribute("aria-busy");
        // Prefetch exam and results bundles when the browser is idle so test launch is instant
        const warmIdle = () => {
          U.prefetch("exam");
          U.prefetch("results");
        };
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
      const check = path.match(/^\/check\/(\d+)$/);
      const spoken = path.match(/^\/speaking\/(\d+)$/);
      window.scrollTo(0, 0);
      if (path === "/resources") this.renderResources();
      else if (path === "/about") this.renderAbout();
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
    }

    onMainClick(e) {
      if (Account.onClick(e)) return;
      const station = e.target.closest("[data-station]");
      if (station) return this.toggleSign(station);
      const nextStation = e.target.closest("[data-next-station]");
      if (nextStation) {
        const target = document.querySelector(`.station-btn[data-station="${CSS.escape(nextStation.dataset.nextStation)}"]`);
        if (target) return this.toggleSign(target);
      }
      const el = e.target.closest("[data-action]");
      if (!el) return;
      if (el.dataset.action === "start") this.prepare(el.dataset.test, el.dataset.mode, el);
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
            <h1 id="home-title">${t("Every line ends at test day.")}</h1>
            <p>${t("home.lead")}</p>
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
          <div class="network-key">
            <span><i class="key-ring is-free" aria-hidden="true"></i>${t("Free test")}</span>
            <span><i class="key-ring" aria-hidden="true">${ICON_LOCK}</i>${t("Opens with the pass")}</span>
            <span><i class="key-ring is-done" aria-hidden="true"></i>${t("Taken, with your band")}</span>
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
          ${Account.passCardHTML(this.prices && this.prices.plan)}
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

    checksLine() {
      const p = this.prices;
      const w = p ? esc(U.money(p.writing_check)) : "…";
      const s = p ? esc(U.money(p.speaking_check)) : "…";
      return `${t("checks.line", { writing: w, speaking: s })} <a href="#/examiners">${t("Meet the examiners")}</a>`;
    }

    async loadPrices() {
      if (this.prices) return;
      try {
        const b = await Account.billing();
        this.prices = b.prices || null;
      } catch (e) { return; }
      const price = this.main.querySelector('[data-price="plan"]');
      if (price && this.prices) price.innerHTML = Account.passPriceHTML(this.prices.plan);
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
      const longest = Math.max(1, ...LINES.map((l) => this.testsOf(l.module).length));
      list.style.setProperty("--rest", String(Math.max(1, longest - 1)));
      list.innerHTML = LINES.map((line) => {
        const tests = this.testsOf(line.module);
        const done = tests.filter((x) => this.ridden[x.id]);
        const next = done.length ? tests.find((x) => !this.ridden[x.id]) : null;
        const free = tests.find((x) => x.access === "free" && !this.ridden[x.id]);
        // On phones the station labels are too narrow for a "Next" tag, so the line's row names the next station.
        const nextButton = !free && next ? `<button type="button" class="next-mobile" data-next-station="${esc(next.id)}"
                  aria-controls="sign-${line.module}">${esc(t("Next: {name}", { name: this.testName(next) }))} ${ICON_ARROW}</button>` : "";
        return `
          <li class="line-row ${line.cls}" data-line="${line.module}">
            <div class="line-main">
              <div class="line-label">
                <span class="bullet">${line.letter}</span>
                <div><div class="line-name">${MODULE_LABELS[line.module]}</div><span class="line-meta">${esc(this.lineMeta(line.module))}</span></div>
                ${free ? `<button type="button" class="start-free start-free-mobile" data-action="start" data-test="${esc(free.id)}" data-mode="exam"
                  aria-label="${esc(t("Start {name}, free", { name: `${MODULE_LABELS[line.module]}, ${this.testName(free)}` }))}">${t("start.short")} ${ICON_ARROW}</button>` : nextButton}
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
      // What a screen reader says for the station: the line, the test, and its state.
      const state = ride
        ? (ride.band !== null && ride.band !== undefined ? t("taken, band {band}", { band: IeltsScoring.formatBand(ride.band) }) : t("taken"))
        : this.canOpen(test) ? "" : t("opens with the pass");
      const label = [MODULE_LABELS[test.module], name, state, isNext ? t("Next") : ""].filter(Boolean).join(", ");
      const btn = (inner, extra = "") => `
        <button type="button" class="station-btn" data-station="${esc(test.id)}" aria-expanded="false"
          aria-controls="sign-${line.module}" aria-label="${esc(label)}: ${esc(t("details"))}" ${extra}>
          ${inner}<span class="station-name">${stationLabel(name)}</span></button>`;
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
        : this.canOpen(test) ? `<span class="station-ring" aria-hidden="true"></span>`
          : `<span class="station-ring is-locked" aria-hidden="true">${ICON_LOCK}</span>`;
      return `<li class="station ${ride ? "is-done" : ""} ${isNext ? "is-next" : ""}">${btn(ring, isNext ? `data-next="${esc(t("Next"))}"` : "")}</li>`;
    }

    /** Curves that carry every line into the Test day interchange. */
    drawNetwork() {
      const net = document.getElementById("network");
      if (!net) return;
      let lastCellWidth = 0;
      let lastHubNarrow = null;

      const draw = () => {
        const svg = net.querySelector("#network-svg");
        const hub = net.querySelector(".hub-capsule");
        const list = net.querySelector("#lines-list");
        if (!svg || !hub || !list) return;

        // The first column fits the widest first station: the whole Start free pill (ring and button) plus the
        // station's own right padding. Its content is measured, not the column, so nothing is reset (no reflow loop).
        const firsts = [...net.querySelectorAll(".station:first-child")];
        if (firsts.length) {
          const maxW = Math.ceil(Math.max(...firsts.map((li) => {
            const body = li.firstElementChild;
            return (body ? body.getBoundingClientRect().width : 0) + (parseFloat(getComputedStyle(li).paddingRight) || 0);
          })));
          if (maxW > 0 && maxW !== lastCellWidth) {
            lastCellWidth = maxW;
            list.style.setProperty("--first-cell", `${maxW}px`);
          }
        }

        // Many tests on a narrow screen: rings shrink to fit their column and labels drop "Test".
        const cell = list.querySelector(".station:nth-child(2)");
        if (cell) {
          const pitch = cell.getBoundingClientRect().width;
          list.style.setProperty("--ring", `${Math.max(18, Math.min(30, Math.floor(pitch - 6)))}px`);
          list.style.setProperty("--ring-done", `${Math.max(26, Math.min(44, Math.floor(pitch - 2)))}px`);
          net.classList.toggle("is-tight", pitch < 56);
        }

        const box = net.getBoundingClientRect();
        const tracks = [...net.querySelectorAll(".track")];
        if (!tracks.length || !box.width) return;
        this.netPaths = {};
        const step = 12;
        const n = tracks.length;
        const narrow = window.matchMedia("(max-width: 860px)").matches;

        if (narrow !== lastHubNarrow) {
          lastHubNarrow = narrow;
          hub.style.height = narrow ? "" : `${n * step + 14}px`;
          hub.style.width = narrow ? `${n * step + 14}px` : "";
        }

        const hb = hub.getBoundingClientRect();
        const hx = hb.left - box.left + hb.width / 2;
        const hy = hb.top - box.top + hb.height / 2;
        const f = (v) => v.toFixed(1);

        const lineColors = {
          listening: "var(--line-l)",
          reading: "var(--line-r)",
          writing: "var(--line-w)",
          speaking: "var(--line-s)",
        };

        const paths = tracks.map((tr, i) => {
          const lineKey = tr.closest(".line-row")?.dataset.line;
          const r = tr.getBoundingClientRect();
          const x0 = r.right - box.left - 1;
          const y0 = r.top - box.top + r.height / 2;
          const color = lineColors[lineKey] || getComputedStyle(tr).getPropertyValue("--line").trim();
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
          if (lineKey) this.netPaths[lineKey] = { x0, y0, d, box };
          return `<path d="${d}" fill="none" stroke="${color}" stroke-width="10" stroke-linecap="butt"/>`;
        });
        svg.setAttribute("viewBox", `0 0 ${box.width.toFixed(1)} ${box.height.toFixed(1)}`);
        svg.innerHTML = paths.join("");
      };

      draw();
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
      if (this.netObserver) this.netObserver.disconnect();
      if (window.ResizeObserver) {
        let rafId = null;
        let lastW = 0;
        let lastH = 0;
        this.netObserver = new ResizeObserver((entries) => {
          const rect = entries[0]?.contentRect;
          if (rect && Math.abs(rect.width - lastW) < 1 && Math.abs(rect.height - lastH) < 1) return;
          if (rect) { lastW = rect.width; lastH = rect.height; }
          if (rafId) cancelAnimationFrame(rafId);
          rafId = requestAnimationFrame(draw);
        });
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
      // Point the sign at its station.
      const ring = btn.querySelector(".station-ring");
      const at = ring.getBoundingClientRect();
      sign.style.setProperty("--notch-x", `${Math.round(at.left + at.width / 2 - sign.getBoundingClientRect().left)}px`);
      this.drawNetwork();
      this.runTrain(test.module, btn);
      const primary = sign.querySelector(".btn-line, .btn-primary");
      if (primary) primary.focus({ preventScroll: true });
      sign.scrollIntoView({ block: "nearest" });
    }

    /** A train leaves the opened station and runs along its line to Test day: this line leads there. */
    runTrain(module, btn) {
      const path = this.netPaths && this.netPaths[module];
      const svg = document.getElementById("network-svg");
      if (!path || !svg || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const ring = btn.querySelector(".station-ring").getBoundingClientRect();
      const box = document.getElementById("network").getBoundingClientRect();
      const sx = ring.left + ring.width / 2 - box.left;
      const sy = ring.top + ring.height / 2 - box.top;
      const route = `M${sx.toFixed(1)},${sy.toFixed(1)} L${path.x0.toFixed(1)},${path.y0.toFixed(1)} ${path.d.slice(path.d.indexOf(" ") + 1)}`;
      svg.querySelectorAll(".network-train").forEach((el) => el.remove());
      const ns = "http://www.w3.org/2000/svg";
      const train = document.createElementNS(ns, "circle");
      train.setAttribute("r", "6");
      train.setAttribute("class", "network-train");
      const move = document.createElementNS(ns, "animateMotion");
      move.setAttribute("dur", "1.3s");
      move.setAttribute("fill", "freeze");
      move.setAttribute("calcMode", "spline");
      move.setAttribute("keyTimes", "0;1");
      move.setAttribute("keySplines", "0.45 0 0.2 1");
      move.setAttribute("path", route);
      train.appendChild(move);
      svg.appendChild(train);
      if (move.beginElement) move.beginElement();
      setTimeout(() => train.remove(), 1500);
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
      const locked = !this.canOpen(test);
      const tag = test.access === "free" ? `<span class="sign-tag is-free">${t("Free")}</span>`
        : !locked ? `<span class="sign-tag">${t("In your pass")}</span>`
          : `<span class="sign-tag is-locked">${t("Opens with the pass")}</span>`;
      const extra = [
        this.hasProgress(test.id) ? t("Unfinished attempt saved") : "",
        ride && ride.band !== null && ride.band !== undefined ? t("Your last band: {band}", { band: IeltsScoring.formatBand(ride.band) }) : "",
      ].filter(Boolean).join(" · ");
      return `
        <div>
          <div class="sign-title"><span class="bullet sm">${line.letter}</span><h3>${esc(MODULE_LABELS[test.module])} · ${esc(this.testName(test))}</h3>${tag}</div>
          <ul class="sign-items">${items.map(([k, v]) => `<li><b>${esc(k)}</b>${esc(v)}</li>`).join("")}</ul>
          <p class="sign-meta">${esc(meta)}${extra ? ` · ${esc(extra)}` : ""}</p>
          ${locked ? `<p class="sign-pass">${this.prices
            ? t("This station opens with the monthly pass: {price} a month, and your first payment gives two months.", { price: `<strong>${esc(U.money(this.prices.plan))}</strong>` })
            : t("This station opens with the monthly pass.")}</p>` : ""}
        </div>
        <div class="sign-actions">
          ${locked ? `
          <a class="btn-secondary" href="#/pricing">${t("See prices")}</a>
          <button type="button" class="btn-line" data-action="buy-plan">${t("Get the pass")} ${ICON_ARROW}</button>` : `
          <button type="button" class="btn-secondary" data-action="start" data-test="${esc(test.id)}" data-mode="practice">${t("Practice, no timer")}</button>
          <button type="button" class="btn-line" data-action="start" data-test="${esc(test.id)}" data-mode="exam">${ride ? t("Take it again") : t("Start timed test")} ${ICON_ARROW}</button>`}
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
        if (err.loadFailed) return; // U.need has already said so
        // A server answer carries its own message; with no answer at all it is the connection.
        const why = err.status ? err.message : t("Could not load this page. Check your connection and try again.");
        U.modal({ title: t("Could not load the test"), bodyHTML: `<p>${esc(why)}</p>` });
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
      const summary = this.tests.find((x) => x.id === test.id);
      if (summary && summary.access === "free") U.track("free_test_started", { module: test.module, testId: test.id });
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
      await this.loadPrices();
      const extra = {
        next: this.nextStopHTML(r.module, r.testId, r.typeBreakdown),
        checkPrice: this.prices && this.prices.writing_check ? U.money(this.prices.writing_check) : "",
      };
      if (r.module === "writing") Results.renderWriting(r, this.main, extra);
      else if (r.module === "listening") Results.renderListening(r, this.main, extra);
      else Results.renderReading(r, this.main, extra);
    }

    /**
     * "Your next stop" on a results page: the question type to practise (Reading and Listening)
     * and the next test on the same line. Without the pass, a locked test says it opens with the
     * pass and what that costs; with the pass (or as staff) there is only a Start button.
     */
    nextStopHTML(module, testId, typeBreakdown) {
      const line = lineOf(module);
      const weak = Object.entries(typeBreakdown || {})
        .filter(([, v]) => v.total > 0 && v.correct < v.total)
        .sort(([, a], [, b]) => (a.correct / a.total - b.correct / b.total) || (b.total - a.total))[0];
      const tests = this.testsOf(module);
      const at = tests.findIndex((x) => x.id === testId);
      const next = tests.slice(at + 1).concat(tests.slice(0, Math.max(at, 0))).find((x) => !this.ridden[x.id]);
      if (!weak && !next) return "";
      const focus = weak ? `
        <div class="next-card">
          <h3>${t("Practise: {type}", { type: esc(weak[1].label) })}</h3>
          <p>${esc(t(`tip.${weak[0]}`))}</p>
          <p class="muted-text small-text">${t("{n} of {total} correct in this test", { n: weak[1].correct, total: weak[1].total })}</p>
        </div>` : "";
      const name = next ? this.testName(next) : "";
      const price = this.prices && this.prices.plan ? U.money(this.prices.plan) : "";
      const ride = next ? `
        <div class="next-card">
          <div class="next-ride"><span class="bullet" aria-hidden="true">${line.letter}</span>
            <h3>${esc(MODULE_LABELS[module])} · ${esc(name)}</h3></div>
          ${this.canOpen(next)
            ? `<p>${t("next.open")}</p>
              <div class="next-actions"><button type="button" class="btn-line" data-action="start" data-test="${esc(next.id)}" data-mode="exam"
                data-track="next_test">${t("Start {name}", { name: esc(name) })} ${ICON_ARROW}</button></div>`
            : `<p>${price ? t("next.locked", { price: `<strong>${esc(price)}</strong>` }) : t("next.locked.noprice")}</p>
              <div class="next-actions"><button type="button" class="btn-line" data-action="buy-plan" data-track="next_test_pass">${t("Get the pass")}</button>
                <a class="btn-secondary" href="#/pricing">${t("See prices")}</a></div>`}
        </div>` : "";
      return `
        <section class="next-stop ${line.cls}" aria-labelledby="next-stop-title">
          <h2 class="section-title" id="next-stop-title">${t("Your next stop")}</h2>
          <div class="next-grid">${focus}${ride}</div>
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
