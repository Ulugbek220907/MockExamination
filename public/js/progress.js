/**
 * Progress on the account page:
 *   - an estimated overall band and a stat tile per module (latest band, the
 *     change since the previous test, best band and the gap to the goal);
 *   - the band card: the last 30 days left to right and bands 0–9 bottom to top,
 *     one tab for all tests and one per module. A day with a test rises to its
 *     band (the average if there were several); other days stay at 0. Tap,
 *     hover or use the arrow keys to read a day; it opens on the latest test day.
 *     The line rises from 0 when it first comes into view (at once with reduced
 *     motion), and every result is also listed in a table;
 *   - an activity calendar: a month at a time, each day filled by how many tests
 *     were taken, with streaks and the day's tests on tap.
 *
 * Progress.render(el, points, activity, opts) – from GET /api/progress:
 *   points   [{module, date, band, testId, source}] oldest first (scored tests)
 *   activity [{module, date, mode, testId, band}] oldest first (every finished test)
 *   opts.goal the student's target band (or null): a dashed line on the chart and a note on the tiles
 */
(function () {
  "use strict";

  const esc = (v) => U.escapeHtml(v);
  // Colour follows the module, never its rank (validated categorical slots 1–4).
  const SERIES = [
    ["listening", "Listening", "var(--series-1)"],
    ["reading", "Reading", "var(--series-2)"],
    ["writing", "Writing", "var(--series-3)"],
    ["speaking", "Speaking", "var(--series-4)"],
  ];
  const SOURCE = { auto: "marked automatically", ai: "AI estimate", examiner: "examiner" };
  const DAYS = 30;
  const DAY = 86400000;

  const band = (v) => IeltsScoring.formatBand(v);
  const loc = () => U.LOCALE;
  const localKey = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const shortDate = (t) => new Date(t).toLocaleDateString(loc(), { day: "numeric", month: "short" });
  const longDate = (t) => new Date(t).toLocaleDateString(loc(), { weekday: "short", day: "numeric", month: "long" });
  const moduleLabel = (key) => (SERIES.find((s) => s[0] === key) || [, key])[1];
  const ARROW = (up) => `<svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="${up ? "M5 1.5 9 7.5H1z" : "M5 8.5 1 2.5h8z"}" fill="currentColor"/></svg>`;
  const titleOf = (id) => {
    const t = ((window.app && window.app.tests) || []).find((x) => x.id === id);
    return t ? t.shortTitle : id;
  };

  /* ---------------------------------------------------------------- drawing */
  const reduceMotion = () => !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const ease = (k) => 1 - Math.pow(1 - k, 3);
  const f1 = (v) => v.toFixed(1);
  let gradients = 0;

  /** A smooth path through [x, y] points that never overshoots them (monotone cubic, like d3's curveMonotoneX). */
  function smoothPath(pts) {
    const n = pts.length;
    if (!n) return "";
    let d = `M${f1(pts[0][0])},${f1(pts[0][1])}`;
    if (n === 2) return `${d}L${f1(pts[1][0])},${f1(pts[1][1])}`;
    const dx = [];
    const m = [];
    for (let i = 0; i < n - 1; i++) {
      dx[i] = pts[i + 1][0] - pts[i][0];
      m[i] = dx[i] ? (pts[i + 1][1] - pts[i][1]) / dx[i] : 0;
    }
    const tan = [m[0]];
    for (let i = 1; i < n - 1; i++) {
      tan[i] = m[i - 1] * m[i] <= 0 ? 0 : (3 * (dx[i - 1] + dx[i])) / ((2 * dx[i] + dx[i - 1]) / m[i - 1] + (dx[i] + 2 * dx[i - 1]) / m[i]);
    }
    tan[n - 1] = m[n - 2];
    for (let i = 0; i < n - 1; i++) {
      const h = dx[i] / 3;
      d += `C${f1(pts[i][0] + h)},${f1(pts[i][1] + tan[i] * h)},${f1(pts[i + 1][0] - h)},${f1(pts[i + 1][1] - tan[i + 1] * h)},${f1(pts[i + 1][0])},${f1(pts[i + 1][1])}`;
    }
    return d;
  }

  const areaPath = (pts, floor) => (pts.length < 2 ? ""
    : `${smoothPath(pts)}L${f1(pts[pts.length - 1][0])},${f1(floor)}L${f1(pts[0][0])},${f1(floor)}Z`);

  const gradient = (id, color) => `<linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" style="stop-color:${color};stop-opacity:0.28"/><stop offset="1" style="stop-color:${color};stop-opacity:0.02"/></linearGradient>`;

  /**
   * Calls frame(k) with k easing from 0 to 1 once `el` comes into view, so the line starts flat at 0 and
   * rises to its bands. Without animate, or with reduced motion, it draws the end state at once.
   */
  function rise(el, frame, animate, ms = 1000) {
    if (!animate || reduceMotion()) {
      frame(1);
      return;
    }
    frame(0);
    const run = () => {
      const start = performance.now();
      const step = (now) => {
        const k = Math.min(1, (now - start) / ms);
        frame(ease(k));
        if (k < 1 && el.isConnected) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };
    if (!window.IntersectionObserver) return run();
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        io.disconnect();
        run();
      }
    }, { threshold: 0.3 });
    io.observe(el);
  }

  /* ------------------------------------------------------------------ tiles */
  function goalLine(last, goal) {
    if (!goal || !last) return "";
    const gap = goal - last.band;
    return gap <= 0
      ? `<div class="tile-goal is-met">${t("Goal {band} reached", { band: band(goal) })}</div>`
      : `<div class="tile-goal">${t("{gap} to your goal of {band}", { gap: band(gap), band: band(goal) })}</div>`;
  }

  function tiles(points, goal) {
    return `<div class="progress-tiles">${SERIES.map(([key, label, color]) => {
      const pts = points.filter((p) => p.module === key);
      const last = pts[pts.length - 1];
      const prev = pts[pts.length - 2];
      let delta = `<span class="tile-delta is-flat">${pts.length ? t("First test") : t("No tests yet")}</span>`;
      if (last && prev) {
        const d = last.band - prev.band;
        delta = d === 0
          ? `<span class="tile-delta is-flat">${t("Same as last time")}</span>`
          : `<span class="tile-delta ${d > 0 ? "is-up" : "is-down"}">${ARROW(d > 0)}
              ${t("{delta} since last time", { delta: `${d > 0 ? "+" : "−"}${band(Math.abs(d))}` })}</span>`;
      }
      const best = pts.length ? Math.max(...pts.map((p) => p.band)) : null;
      return `
        <div class="progress-tile">
          <div class="tile-label"><span class="line-key" style="background:${color}" aria-hidden="true"></span>${label}</div>
          <div class="tile-value">${last ? band(last.band) : "–"}</div>
          ${delta}
          <div class="tile-sub">${pts.length ? `${t("Best {band}", { band: band(best) })} · ${plural(pts.length, "{n} test", "{n} tests")}` : "&nbsp;"}</div>
          ${goalLine(last, goal)}
        </div>`;
    }).join("")}</div>`;
  }

  function table(points) {
    return `
      <details class="fold pv-table">
        <summary>${t("Every result as a table")}</summary>
        <div class="table-scroll"><table class="history-table">
          <thead><tr><th scope="col">${t("Date")}</th><th scope="col">${t("Module")}</th><th scope="col">${t("Test")}</th><th scope="col">${t("Band")}</th><th scope="col">${t("Marked by")}</th></tr></thead>
          <tbody>${points.slice().reverse().map((p) => `
            <tr><td>${esc(U.formatDate(p.date))}</td><td>${esc(moduleLabel(p.module))}</td>
              <td>${esc(titleOf(p.testId))}</td><td><strong>${band(p.band)}</strong></td><td>${esc(t(SOURCE[p.source] || ""))}</td></tr>`).join("")}</tbody>
        </table></div>
      </details>`;
  }

  /* ---------------------------------------------------------------- overall */
  /** The mean of some bands, rounded to a whole or half band as in the real test. */
  function roundOverall(mean) {
    const whole = Math.floor(mean);
    const frac = mean - whole;
    return frac < 0.25 ? whole : frac < 0.75 ? whole + 0.5 : whole + 1;
  }

  function overallHTML(points) {
    const latest = SERIES.map(([key]) => points.filter((p) => p.module === key).pop()).filter(Boolean);
    if (!latest.length) return "";
    const overall = roundOverall(latest.reduce((a, p) => a + p.band, 0) / latest.length);
    const all = latest.length === 4;
    return `
      <div class="overall-band">
        <div class="overall-fig"><span>${band(overall)}</span></div>
        <div>
          <strong>${t(all ? "Your estimated overall band" : "Your estimated band so far")}</strong>
          <p class="muted-text">${all ? t("The average of your latest band in each module, rounded as in the real test.")
            : t("From your latest {modules}. Take the other modules for a full overall band.", { modules: latest.map((p) => moduleLabel(p.module)).join(", ") })}</p>
        </div>
      </div>`;
  }

  /* -------------------------------------------------------------- band card */
  // The last 30 days, one tab for all tests and one per module.
  const ALL = ["all", "All tests", "var(--series-0)"];

  /** The 30 days ending today, oldest first: each with its tests in this series and their band (0 if none). */
  function lastDays(points, key) {
    const byDay = {};
    points.filter((p) => key === "all" || p.module === key).forEach((p) => {
      const k = localKey(new Date(p.date));
      (byDay[k] = byDay[k] || []).push(p);
    });
    const now = new Date();
    const days = [];
    for (let i = DAYS - 1; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
      const tests = byDay[localKey(d)] || [];
      days.push({ t: d.getTime(), tests, band: tests.length ? roundOverall(tests.reduce((a, p) => a + p.band, 0) / tests.length) : 0 });
    }
    return days;
  }

  function bandCardHTML(points) {
    const choices = [ALL, ...SERIES.filter(([key]) => points.some((p) => p.module === key))];
    return `
      <div class="band-card">
        <div class="seg" role="group" aria-label="${esc(t("Show the band for"))}">
          ${choices.map(([key, label], i) => `<button type="button" class="seg-btn" data-series="${key}" aria-pressed="${i === 0}">${esc(t(label))}</button>`).join("")}
        </div>
        <div class="bc-head"></div>
        <div class="bc-readout" aria-live="polite"></div>
        <div class="bc-plot"></div>
        <dl class="mc-stats bc-stats"></dl>
      </div>`;
  }

  function bandHeadHTML(days) {
    const tested = days.filter((d) => d.tests.length);
    const last = tested[tested.length - 1];
    const prev = tested[tested.length - 2];
    let delta = "";
    if (last && prev) {
      const d = last.band - prev.band;
      delta = d === 0 ? `<span class="tile-delta is-flat">${t("Same as the test day before")}</span>`
        : `<span class="tile-delta ${d > 0 ? "is-up" : "is-down"}">${ARROW(d > 0)}${d > 0 ? "+" : "−"}${band(Math.abs(d))}</span>`;
    }
    return `
      <div class="bc-title"><strong>${t("Band score")}</strong> <span>${esc(t("(last 30 days)"))}</span></div>
      <div class="bc-figure"><span class="bc-value">${last ? band(last.band) : "–"}</span>${delta}</div>`;
  }

  function bandStatsHTML(days) {
    const tests = days.flatMap((d) => d.tests);
    if (!tests.length) return `<div><dt>${t("No tests in the last 30 days")}</dt><dd></dd></div>`;
    const bands = tests.map((p) => p.band);
    return `<div><dt>${t("Tests")}</dt><dd>${tests.length}</dd></div>
      <div><dt>${t("Days with a test")}</dt><dd>${days.filter((d) => d.tests.length).length}</dd></div>
      <div><dt>${t("Best")}</dt><dd>${band(Math.max(...bands))}</dd></div>
      <div><dt>${t("Average")}</dt><dd>${(bands.reduce((a, b) => a + b, 0) / bands.length).toFixed(1)}</dd></div>`;
  }

  /** Draws the 30 days at the plot's real width; the chosen day is marked on both axes. */
  function mountBandChart(card, color, days, animate, goal) {
    const plot = card.querySelector(".bc-plot");
    const readout = card.querySelector(".bc-readout");
    const value = card.querySelector(".bc-value");
    const W = Math.round(plot.clientWidth);
    if (!W) return;
    const H = W < 520 ? 230 : 270;
    const L = 4;
    const R = 40;
    const T = 12;
    const B = 30;
    const x0 = L + 6;
    const x1 = W - R - 12;
    const X = (i) => x0 + (i / (DAYS - 1)) * (x1 - x0);
    const Y = (b) => T + (1 - b / 9) * (H - T - B);
    const floor = Y(0);
    const every = (H - T - B) / 9 >= 20 ? 1 : 3;
    const id = `pvg-${++gradients}`;

    const grid = [];
    for (let b = 0; b <= 9; b++) {
      grid.push(`<line x1="${L}" x2="${W - R}" y1="${Y(b)}" y2="${Y(b)}" class="pv-grid${b === 0 ? " is-base" : ""}"/>`);
      if (b % every === 0) grid.push(`<text x="${W - R + 10}" y="${Y(b) + 4}" class="pv-tick">${b}</text>`);
    }
    if (goal) {
      grid.push(`<line x1="${L}" x2="${W - R}" y1="${Y(goal)}" y2="${Y(goal)}" class="pv-goal"/>
        <text x="${L + 6}" y="${Y(goal) - 6}" class="pv-goal-label">${esc(t("Goal {band}", { band: band(goal) }))}</text>`);
    }
    // A date under every week, counted back from today.
    const labelled = [];
    for (let i = DAYS - 1; i >= 0; i -= 7) labelled.push(i);
    const xLabels = labelled.map((i) => `<text class="pv-tick bc-xl" x="${X(i)}" y="${H - 11}" text-anchor="${i === DAYS - 1 ? "end" : i < 3 ? "start" : "middle"}">${esc(i === DAYS - 1 ? t("Today") : shortDate(days[i].t))}</text>`).join("");

    plot.innerHTML = `
      <svg class="bc-svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" tabindex="0"
        aria-label="${esc(t("Your band on each of the last 30 days, from 0 to 9. Use the left and right arrow keys to read each day."))}">
        <defs>${gradient(id, color)}</defs>
        ${grid.join("")}
        <path class="bc-area" fill="url(#${id})"/>
        <path class="bc-line" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
        <line class="bc-vx" y1="${T - 6}" y2="${floor}"/>
        <line class="bc-hy" x1="${L}" x2="${W - R}"/>
        <g class="bc-dots">${days.map((d) => (d.tests.length ? `<circle r="3.5" fill="${color}" stroke="var(--pv-surface)" stroke-width="1.5"/>` : "<g/>")).join("")}</g>
        <circle class="bc-sel" r="7" fill="${color}" stroke="var(--pv-surface)" stroke-width="3"/>
        <g class="bc-badge"><rect x="${W - R + 3}" width="${R - 4}" height="22" rx="6"/><text x="${W - R + 3 + (R - 4) / 2}" text-anchor="middle"></text></g>
        ${xLabels}
        <g class="bc-pill"><rect height="22" rx="6" y="${H - 27}"/><text y="${H - 11}" text-anchor="middle"></text></g>
        <rect x="0" y="0" width="${W - R}" height="${H}" fill="transparent"/>
      </svg>`;
    const svg = plot.querySelector("svg");
    const $ = (sel) => svg.querySelector(sel);
    const line = $(".bc-line");
    const area = $(".bc-area");
    const dots = [...$(".bc-dots").children]; // one per day; days without a test hold an empty group
    const sel = $(".bc-sel");
    const vx = $(".bc-vx");
    const hy = $(".bc-hy");
    const badge = $(".bc-badge");
    const badgeRect = $(".bc-badge rect");
    const badgeText = $(".bc-badge text");
    const pillRect = $(".bc-pill rect");
    const pillText = $(".bc-pill text");
    const xls = svg.querySelectorAll(".bc-xl");
    const tested = days.map((d, i) => (d.tests.length ? i : -1)).filter((i) => i >= 0);
    const latest = tested.length ? tested[tested.length - 1] : DAYS - 1;
    let k = 0;
    let current = latest;

    const paint = () => {
      const at = days.map((d, i) => [X(i), floor + (Y(d.band) - floor) * k]);
      line.setAttribute("d", smoothPath(at));
      area.setAttribute("d", areaPath(at, floor));
      dots.forEach((c, i) => {
        if (c.tagName !== "circle") return;
        c.setAttribute("cx", f1(at[i][0]));
        c.setAttribute("cy", f1(at[i][1]));
      });
      const [sx, sy] = at[current];
      const has = days[current].tests.length > 0;
      sel.setAttribute("visibility", has ? "visible" : "hidden");
      sel.setAttribute("cx", f1(sx));
      sel.setAttribute("cy", f1(sy));
      vx.setAttribute("x1", f1(sx));
      vx.setAttribute("x2", f1(sx));
      hy.setAttribute("visibility", has ? "visible" : "hidden");
      hy.setAttribute("y1", f1(sy));
      hy.setAttribute("y2", f1(sy));
      badge.setAttribute("visibility", has ? "visible" : "hidden");
      // The numbers count up with the line.
      const shown = k === 1 ? band(days[current].band) : (days[current].band * k).toFixed(1);
      badgeRect.setAttribute("y", f1(sy - 11));
      badgeText.setAttribute("y", f1(sy + 4));
      badgeText.textContent = shown;
      if (value && current === latest && has) value.textContent = shown;
    };

    const select = (i) => {
      current = i;
      const d = days[i];
      pillText.textContent = i === DAYS - 1 ? t("Today") : shortDate(d.t);
      pillText.setAttribute("x", f1(X(i)));
      const w = pillText.getComputedTextLength() + 16;
      const px = Math.min(Math.max(0, X(i) - w / 2), W - w);
      pillRect.setAttribute("x", f1(px));
      pillRect.setAttribute("width", f1(w));
      pillText.setAttribute("x", f1(px + w / 2));
      xls.forEach((el) => {
        const ex = Number(el.getAttribute("x"));
        const anchor = el.getAttribute("text-anchor");
        const width = el.getComputedTextLength();
        const left = anchor === "start" ? ex : anchor === "end" ? ex - width : ex - width / 2;
        el.setAttribute("visibility", left + width + 6 > px && left - 6 < px + w ? "hidden" : "visible");
      });
      readout.innerHTML = `<span class="bc-date">${esc(longDate(d.t))}</span>${d.tests.length
        ? d.tests.map((p) => `<span class="bc-key"><span class="line-key" style="background:${(SERIES.find((s) => s[0] === p.module) || ALL)[2]}" aria-hidden="true"></span>${esc(moduleLabel(p.module))} <strong>${band(p.band)}</strong></span>`).join("")
        : `<span class="bc-test">${t("No test this day")}</span>`}`;
      paint();
    };

    const nearest = (clientX) => {
      const box = svg.getBoundingClientRect();
      const x = ((clientX - box.left) / box.width) * W;
      return Math.max(0, Math.min(DAYS - 1, Math.round(((x - x0) / (x1 - x0)) * (DAYS - 1))));
    };
    const pick = (e) => { if (k === 1) select(nearest(e.clientX)); };
    svg.addEventListener("pointermove", pick);
    svg.addEventListener("pointerdown", pick);
    svg.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse" && k === 1) select(latest); });
    svg.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      select(Math.max(0, Math.min(DAYS - 1, current + (e.key === "ArrowLeft" ? -1 : 1))));
    });

    select(current);
    rise(svg, (v) => {
      k = v;
      paint();
    }, animate);
  }

  function bindBandCard(root, points, animate, goal) {
    const card = root.querySelector(".band-card");
    if (!card) return;
    const plot = card.querySelector(".bc-plot");
    let key = "all";
    let width = 0;
    const show = (play) => {
      const [, , color] = key === "all" ? ALL : SERIES.find((s) => s[0] === key);
      const days = lastDays(points, key);
      card.querySelector(".bc-head").innerHTML = bandHeadHTML(days);
      card.querySelector(".bc-stats").innerHTML = bandStatsHTML(days);
      width = plot.clientWidth;
      mountBandChart(card, color, days, play, goal);
    };
    card.querySelectorAll(".seg-btn").forEach((btn) => btn.addEventListener("click", () => {
      if (btn.dataset.series === key) return;
      key = btn.dataset.series;
      card.querySelectorAll(".seg-btn").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      btn.scrollIntoView({ block: "nearest", inline: "nearest", behavior: reduceMotion() ? "auto" : "smooth" });
      show(true);
    }));
    show(animate);
    if (window.ResizeObserver) {
      new ResizeObserver(() => requestAnimationFrame(() => {
        if (plot.clientWidth && plot.clientWidth !== width) show(false);
      })).observe(plot);
    }
  }

  /* ---------------------------------------------------------------- calendar */
  const MODULE_ORDER = SERIES.map((s) => s[0]);

  function byDay(activity) {
    const days = new Map();
    activity.forEach((a) => {
      const k = localKey(new Date(a.date));
      if (!days.has(k)) days.set(k, []);
      days.get(k).push(a);
    });
    return days;
  }

  function streaks(days) {
    const keys = [...days.keys()].sort();
    let longest = 0;
    let run = 0;
    let prev = null;
    keys.forEach((k) => {
      const d = new Date(`${k}T12:00:00`);
      run = prev && Math.round((d - prev) / DAY) === 1 ? run + 1 : 1;
      longest = Math.max(longest, run);
      prev = d;
    });
    // The current streak counts back from today (or from yesterday, if today has no test yet).
    let current = 0;
    const day = new Date();
    day.setHours(12, 0, 0, 0);
    if (!days.has(localKey(day))) day.setDate(day.getDate() - 1);
    while (days.has(localKey(day))) {
      current++;
      day.setDate(day.getDate() - 1);
    }
    return { current, longest };
  }

  const level = (n) => (n >= 4 ? 4 : n);

  function monthHTML(days, year, month) {
    const first = new Date(year, month, 1);
    const count = new Date(year, month + 1, 0).getDate();
    const lead = (first.getDay() + 6) % 7; // weeks start on Monday
    const today = localKey(new Date());
    const names = [...Array(7)].map((_, i) => new Date(2024, 0, 1 + i).toLocaleDateString(loc(), { weekday: "short" }));
    const cells = [];
    for (let i = 0; i < lead; i++) cells.push(`<td class="cal-pad"></td>`);
    let tests = 0;
    let active = 0;
    for (let d = 1; d <= count; d++) {
      const key = localKey(new Date(year, month, d));
      const items = days.get(key) || [];
      tests += items.length;
      if (items.length) active++;
      const mods = MODULE_ORDER.filter((m) => items.some((a) => a.module === m));
      const label = `${new Date(year, month, d).toLocaleDateString(loc(), { weekday: "long", day: "numeric", month: "long" })}: ${items.length
        ? plural(items.length, "{n} test", "{n} tests") : t("no tests")}`;
      cells.push(`
        <td class="cal-day lv-${level(items.length)}${key === today ? " is-today" : ""}${key > today ? " is-future" : ""}">
          <button type="button" data-day="${key}" aria-label="${esc(label)}" ${items.length ? "" : "tabindex=\"-1\""}>
            <span class="cal-num">${d}</span>
            <span class="cal-dots" aria-hidden="true">${mods.map((m) => `<i style="background:${SERIES.find((s) => s[0] === m)[2]}"></i>`).join("")}</span>
          </button>
        </td>`);
    }
    while (cells.length % 7) cells.push(`<td class="cal-pad"></td>`);
    const rows = [];
    for (let i = 0; i < cells.length; i += 7) rows.push(`<tr>${cells.slice(i, i + 7).join("")}</tr>`);
    return {
      tests, active,
      html: `<table class="cal-table">
        <caption class="sr-only">${esc(first.toLocaleDateString(loc(), { month: "long", year: "numeric" }))}</caption>
        <thead><tr>${names.map((n) => `<th scope="col">${esc(n)}</th>`).join("")}</tr></thead>
        <tbody>${rows.join("")}</tbody></table>`,
    };
  }

  function dayDetailHTML(key, items) {
    const date = new Date(`${key}T12:00:00`).toLocaleDateString(loc(), { weekday: "long", day: "numeric", month: "long" });
    if (!items.length) return `<p class="muted-text">${esc(t("{date}: no tests.", { date }))}</p>`;
    return `<p class="cal-detail-date">${esc(date)}</p>
      <ul class="cal-detail-list">${items.map((a) => {
        const s = SERIES.find((x) => x[0] === a.module);
        return `<li><span class="line-key" style="background:${s[2]}" aria-hidden="true"></span><strong>${esc(s[1])}</strong>
          <span>${esc(titleOf(a.testId))}${a.mode === "practice" ? ` · ${esc(t("practice"))}` : ""}</span>
          <span class="cal-detail-band">${a.band !== null && a.band !== undefined ? esc(t("Band {band}", { band: band(a.band) })) : ""}</span></li>`;
      }).join("")}</ul>`;
  }

  function renderCalendar(el, activity) {
    const days = byDay(activity);
    const { current, longest } = streaks(days);
    const now = new Date();
    let year = now.getFullYear();
    let month = now.getMonth();
    const oldest = activity.length ? new Date(activity[0].date) : now;
    const weekAgo = Date.now() - 7 * DAY;
    const thisWeek = activity.filter((a) => new Date(a.date).getTime() >= weekAgo).length;
    el.innerHTML = `
      <h2 class="section-title" id="activity-title">${t("Your activity")}</h2>
      <p class="muted-text section-sub">${t("Every day you finish a test fills in. Keep the days coming.")}</p>
      <div class="activity-grid">
      <div class="cal-stats">
        <div><strong>${current}</strong><span>${t("Day streak now")}</span></div>
        <div><strong>${longest}</strong><span>${t("Longest streak")}</span></div>
        <div><strong>${thisWeek}</strong><span>${t("Tests in the last 7 days")}</span></div>
        <div><strong>${activity.length}</strong><span>${t("Tests in all")}</span></div>
      </div>
      <div class="cal-card">
        <div class="cal-head">
          <button type="button" class="cal-nav" data-cal="-1" aria-label="${esc(t("Previous month"))}">‹</button>
          <strong class="cal-title" aria-live="polite"></strong>
          <button type="button" class="cal-nav" data-cal="1" aria-label="${esc(t("Next month"))}">›</button>
        </div>
        <div class="cal-body"></div>
        <div class="cal-foot">
          <span class="cal-month-sum muted-text"></span>
          <span class="cal-legend" aria-hidden="true">${t("Less")} <i class="lv-0"></i><i class="lv-1"></i><i class="lv-2"></i><i class="lv-3"></i><i class="lv-4"></i> ${t("More")}</span>
        </div>
        <div class="cal-detail" aria-live="polite"></div>
      </div>
      </div>`;
    const body = el.querySelector(".cal-body");
    const title = el.querySelector(".cal-title");
    const sum = el.querySelector(".cal-month-sum");
    const detail = el.querySelector(".cal-detail");
    const prev = el.querySelector('[data-cal="-1"]');
    const next = el.querySelector('[data-cal="1"]');
    const draw = () => {
      const m = monthHTML(days, year, month);
      body.innerHTML = m.html;
      title.textContent = new Date(year, month, 1).toLocaleDateString(loc(), { month: "long", year: "numeric" });
      sum.textContent = m.tests ? t("{tests} · on {days}", { tests: plural(m.tests, "{n} test", "{n} tests"), days: plural(m.active, "{n} day", "{n} days") }) : t("No tests this month yet.");
      prev.disabled = year < oldest.getFullYear() || (year === oldest.getFullYear() && month <= oldest.getMonth());
      next.disabled = year === now.getFullYear() && month === now.getMonth();
      detail.innerHTML = "";
    };
    el.querySelectorAll(".cal-nav").forEach((b) => b.addEventListener("click", () => {
      month += Number(b.dataset.cal);
      if (month < 0) { month = 11; year--; }
      if (month > 11) { month = 0; year++; }
      draw();
    }));
    body.addEventListener("click", (e) => {
      const b = e.target.closest("[data-day]");
      if (!b) return;
      body.querySelectorAll(".is-picked").forEach((x) => x.classList.remove("is-picked"));
      b.parentElement.classList.add("is-picked");
      detail.innerHTML = dayDetailHTML(b.dataset.day, days.get(b.dataset.day) || []);
    });
    draw();
    // Open on today's tests, if there are any.
    const todayKey = localKey(now);
    if (days.has(todayKey)) detail.innerHTML = dayDetailHTML(todayKey, days.get(todayKey));
  }

  /** opts.animate (default on): the line rises from 0 as it comes into view. opts.goal: the target band. */
  function render(el, points, activity = [], opts = {}) {
    if (!el) return;
    const animate = opts.animate !== false;
    const goal = opts.goal || null;
    const calendar = `<section class="activity-section" aria-labelledby="activity-title"></section>`;
    if (!points.length) {
      el.innerHTML = `
        <h2 class="section-title">${t("Your progress")}</h2>
        <p class="empty-inline">${t(window.Account && window.Account.commerce() ? "progress.empty" : "progress.empty.free")}</p>
        ${calendar}`;
      renderCalendar(el.querySelector(".activity-section"), activity);
      return;
    }
    el.innerHTML = `
      <h2 class="section-title">${t("Your progress")}</h2>
      <p class="muted-text section-sub">${t("Timed Listening and Reading tests, and marked Writing and Speaking tests.")}</p>
      ${overallHTML(points)}
      ${tiles(points, goal)}
      ${bandCardHTML(points)}
      ${table(points)}
      ${calendar}`;
    bindBandCard(el, points, animate, goal);
    renderCalendar(el.querySelector(".activity-section"), activity);
  }

  window.Progress = { render };
})();
