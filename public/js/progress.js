/**
 * Progress on the account page:
 *   - an estimated overall band and a stat tile per module (latest band, the
 *     change since the previous test and a sparkline);
 *   - the band card: one smooth line of bands, the overall band or one module at
 *     a time, with the chosen test marked on both axes (latest by default; hover,
 *     drag or arrow keys to read the others);
 *   - a line chart of all four modules over time, with a hover/keyboard readout,
 *     a legend, direct end labels and a table view;
 *   - every line starts flat on the floor and rises to its bands when it first
 *     comes into view (at once with reduced motion);
 *   - an activity calendar: a month at a time, each day filled by how many tests
 *     were taken, with streaks and the day's tests on tap.
 *
 * Progress.render(el, points, activity) – from GET /api/progress:
 *   points   [{module, date, band, testId, source}] oldest first (scored tests)
 *   activity [{module, date, mode, testId, band}] oldest first (every finished test)
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
  const M = { top: 16, right: 92, bottom: 30, left: 34 };
  const DAY = 86400000;

  const band = (v) => IeltsScoring.formatBand(v);
  const dayKey = (iso) => new Date(iso).toISOString().slice(0, 10);
  const loc = () => U.LOCALE;
  const shortDate = (t) => new Date(t).toLocaleDateString(loc(), { day: "numeric", month: "short" });
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
    <stop offset="0" style="stop-color:${color};stop-opacity:0.26"/><stop offset="1" style="stop-color:${color};stop-opacity:0"/></linearGradient>`;

  /**
   * Calls frame(k) with k easing from 0 to 1 once `el` comes into view, so a line starts flat on the floor and
   * rises to its bands. Without animate, or with reduced motion, it draws the end state at once.
   */
  function rise(el, frame, animate, ms = 1100) {
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

  function sparkline(host, bands, color, animate) {
    const W = 88;
    const H = 32;
    const P = 3;
    const lo = Math.max(0, Math.min(...bands) - 0.5);
    const hi = Math.min(9, Math.max(...bands) + 0.5);
    const vals = bands.length === 1 ? [bands[0], bands[0]] : bands;
    const X = (i) => P + (i / (vals.length - 1)) * (W - 2 * P);
    const Y = (b) => P + (1 - (b - lo) / (hi - lo || 1)) * (H - 2 * P);
    const id = `pvg-${++gradients}`;
    host.innerHTML = `<svg class="tile-spark" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true">
      <defs>${gradient(id, color)}</defs><path fill="url(#${id})"/>
      <path fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>`;
    const [area, line] = host.querySelectorAll("path");
    const floor = H - 1;
    rise(host, (k) => {
      const pts = vals.map((b, i) => [X(i), floor + (Y(b) - floor) * k]);
      line.setAttribute("d", smoothPath(pts));
      area.setAttribute("d", areaPath(pts, floor));
    }, animate);
  }

  function tiles(points) {
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
          <div class="tile-main"><div class="tile-value">${last ? band(last.band) : "–"}</div>${pts.length ? `<div class="tile-spark-host" data-module="${key}"></div>` : ""}</div>
          ${delta}
          <div class="tile-sub">${pts.length ? `${t("Best {band}", { band: band(best) })} · ${plural(pts.length, "{n} test", "{n} tests")}` : "&nbsp;"}</div>
        </div>`;
    }).join("")}</div>`;
  }

  /** Scales for a chart drawn at its real pixel width, so text stays 12px on every screen. */
  function layout(points, width) {
    const W = Math.max(280, Math.round(width));
    const H = W < 520 ? 220 : 280;
    const right = W < 520 ? 16 : M.right; // no room for end labels on a phone
    const times = points.map((p) => new Date(p.date).getTime());
    let x0 = Math.min(...times);
    let x1 = Math.max(...times);
    if (x1 - x0 < DAY) { x0 -= DAY; x1 += DAY; }
    const y0 = Math.min(Math.max(0, Math.floor(Math.min(...points.map((p) => p.band))) - 1), 8);
    const y1 = 9;
    return {
      W, H, right, x0, x1, y0, y1, narrow: W < 520,
      X: (t) => M.left + ((t - x0) / (x1 - x0)) * (W - M.left - right),
      Y: (b) => M.top + (1 - (b - y0) / (y1 - y0)) * (H - M.top - M.bottom),
    };
  }

  function chart(points, g) {
    const { W, H, x0, x1, y0, y1, X, Y } = g;
    const R = g.right;

    const grid = [];
    for (let b = y0; b <= y1; b++) {
      grid.push(`<line x1="${M.left}" x2="${W - R}" y1="${Y(b)}" y2="${Y(b)}" class="pv-grid"/>
        <text x="${M.left - 8}" y="${Y(b) + 4}" text-anchor="end" class="pv-tick">${b}</text>`);
    }
    const ticks = g.narrow ? 2 : 4;
    for (let i = 0; i <= ticks; i++) {
      const t = x0 + ((x1 - x0) * i) / ticks;
      grid.push(`<text x="${X(t)}" y="${H - 8}" text-anchor="${i === 0 ? "start" : i === ticks ? "end" : "middle"}" class="pv-tick">${esc(shortDate(t))}</text>`);
    }

    const present = SERIES.filter(([key]) => points.some((p) => p.module === key));
    // Each module's tests as [x, y]; the paths and dots are filled in by riseLines (they start on the floor).
    g.lines = present.map(([key]) => {
      const pts = [];
      points.filter((p) => p.module === key).forEach((p) => {
        const x = X(new Date(p.date).getTime());
        pts.push([pts.length ? Math.max(x, pts[pts.length - 1][0] + 0.5) : x, Y(p.band)]);
      });
      return { key, pts };
    });
    g.floor = Y(y0);
    const lines = present.map(([key, , color], s) =>
      // A smooth line with a dot at every test.
      `<path class="pv-line" data-s="${s}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
        ${g.lines[s].pts.map((_, i) => `<circle class="pv-pt" data-s="${s}" data-i="${i}" r="4" fill="${color}" stroke="var(--pv-surface)" stroke-width="2"/>`).join("")}`).join("");

    // Direct labels at each line's end – only when none of them collide (the legend and table always remain).
    const ends = present.map(([key, label]) => {
      const pts = points.filter((p) => p.module === key);
      const p = pts[pts.length - 1];
      return { x: X(new Date(p.date).getTime()) + 8, y: Y(p.band) + 4, text: `${label} ${band(p.band)}` };
    });
    const collide = g.narrow || ends.some((a, i) => ends.some((b, j) => j > i && Math.abs(a.y - b.y) < 14 && Math.abs(a.x - b.x) < 90));
    const labels = collide ? "" : ends.map((e) => `<text x="${e.x}" y="${e.y}" class="pv-end" opacity="0">${esc(e.text)}</text>`).join("");

    return `
      <svg class="pv-svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" tabindex="0"
        aria-label="${esc(t("Band scores over time for {modules}. Use the left and right arrow keys to read each date.", { modules: present.map((s) => s[1]).join(", ") }))}">
        ${grid.join("")}
        <line class="pv-cross" x1="0" x2="0" y1="${M.top}" y2="${H - M.bottom}" visibility="hidden"/>
        ${lines}${labels}
        <rect class="pv-hit" x="${M.left}" y="${M.top}" width="${W - M.left - R}" height="${H - M.top - M.bottom}" fill="transparent"/>
      </svg>
      <div class="pv-tip" role="status" hidden></div>`;
  }

  function riseLines(root, g, animate) {
    const svg = root.querySelector(".pv-svg");
    const paths = svg.querySelectorAll(".pv-line");
    const dots = svg.querySelectorAll(".pv-pt");
    const ends = svg.querySelectorAll(".pv-end");
    rise(svg, (k) => {
      const at = g.lines.map(({ pts }) => pts.map(([x, y]) => [x, g.floor + (y - g.floor) * k]));
      paths.forEach((p) => p.setAttribute("d", smoothPath(at[p.dataset.s])));
      dots.forEach((c) => {
        const [x, y] = at[c.dataset.s][c.dataset.i];
        c.setAttribute("cx", f1(x));
        c.setAttribute("cy", f1(y));
      });
      ends.forEach((e) => e.setAttribute("opacity", k < 0.85 ? 0 : (k - 0.85) / 0.15));
    }, animate);
  }

  function table(points) {
    return `
      <details class="fold pv-table">
        <summary>${t("Show as a table")}</summary>
        <div class="table-scroll"><table class="history-table">
          <thead><tr><th scope="col">${t("Date")}</th><th scope="col">${t("Module")}</th><th scope="col">${t("Test")}</th><th scope="col">${t("Band")}</th><th scope="col">${t("Marked by")}</th></tr></thead>
          <tbody>${points.slice().reverse().map((p) => `
            <tr><td>${esc(U.formatDate(p.date))}</td><td>${esc((SERIES.find((s) => s[0] === p.module) || [, p.module])[1])}</td>
              <td>${esc(titleOf(p.testId))}</td><td><strong>${band(p.band)}</strong></td><td>${esc(t(SOURCE[p.source] || ""))}</td></tr>`).join("")}</tbody>
        </table></div>
      </details>`;
  }

  function bindHover(root, points, g) {
    const svg = root.querySelector(".pv-svg");
    const tip = root.querySelector(".pv-tip");
    const cross = root.querySelector(".pv-cross");
    if (!svg) return;
    const { W, X } = g;
    const days = [...new Set(points.map((p) => dayKey(p.date)))].sort();
    const dayX = days.map((d) => {
      const ts = points.filter((p) => dayKey(p.date) === d).map((p) => new Date(p.date).getTime());
      return X(ts.reduce((a, b) => a + b, 0) / ts.length);
    });
    let current = -1;

    const show = (i) => {
      current = i;
      const x = dayX[i];
      cross.setAttribute("x1", x);
      cross.setAttribute("x2", x);
      cross.setAttribute("visibility", "visible");
      const onDay = points.filter((p) => dayKey(p.date) === days[i]);
      tip.textContent = "";
      const head = document.createElement("div");
      head.className = "pv-tip-date";
      head.textContent = new Date(onDay[0].date).toLocaleDateString(loc(), { day: "numeric", month: "long", year: "numeric" });
      tip.appendChild(head);
      SERIES.forEach(([key, label, color]) => {
        const last = onDay.filter((p) => p.module === key).pop();
        if (!last) return;
        const row = document.createElement("div");
        row.className = "pv-tip-row";
        const k = document.createElement("span");
        k.className = "line-key";
        k.style.background = color;
        const v = document.createElement("strong");
        v.textContent = band(last.band);
        const l = document.createElement("span");
        l.textContent = `${label} · ${titleOf(last.testId)}`;
        row.append(k, v, l);
        tip.appendChild(row);
      });
      tip.hidden = false;
      const box = svg.getBoundingClientRect();
      const scale = box.width / W;
      const left = x * scale;
      tip.style.left = `${Math.min(Math.max(0, left - tip.offsetWidth / 2), box.width - tip.offsetWidth)}px`;
    };
    const hide = () => {
      cross.setAttribute("visibility", "hidden");
      tip.hidden = true;
    };
    const nearest = (clientX) => {
      const box = svg.getBoundingClientRect();
      const x = ((clientX - box.left) / box.width) * W;
      let best = 0;
      dayX.forEach((dx, i) => { if (Math.abs(dx - x) < Math.abs(dayX[best] - x)) best = i; });
      return best;
    };
    svg.addEventListener("pointermove", (e) => show(nearest(e.clientX)));
    svg.addEventListener("pointerleave", hide);
    svg.addEventListener("blur", hide);
    svg.addEventListener("focus", () => show(current >= 0 ? current : days.length - 1));
    svg.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        e.preventDefault();
        show(Math.max(0, Math.min(days.length - 1, (current < 0 ? days.length - 1 : current) + (e.key === "ArrowLeft" ? -1 : 1))));
      } else if (e.key === "Escape") {
        hide();
      }
    });
  }

  /* ---------------------------------------------------------------- overall */
  /** The mean of the module bands, rounded to a whole or half band as in the real test. */
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
            : t("From your latest {modules}. Take the other modules for a full overall band.", { modules: latest.map((p) => SERIES.find((s) => s[0] === p.module)[1]).join(", ") })}</p>
        </div>
      </div>`;
  }

  /* -------------------------------------------------------------- band card */
  // One smooth line of bands: the overall band, or one module at a time.
  const OVERALL = ["overall", "Overall", "var(--series-0)"];

  /** The estimated overall band after each test: the mean of the latest band in each module so far. */
  function overallSeries(points) {
    const latest = {};
    return points.map((p) => {
      latest[p.module] = p.band;
      const bands = Object.values(latest);
      return { ...p, band: roundOverall(bands.reduce((a, b) => a + b, 0) / bands.length) };
    });
  }

  const seriesOf = (points, key) => (key === "overall" ? overallSeries(points) : points.filter((p) => p.module === key));

  function bandCardHTML(points) {
    const choices = [OVERALL, ...SERIES.filter(([key]) => points.some((p) => p.module === key))];
    return `
      <div class="band-card">
        <div class="seg" role="group" aria-label="${esc(t("Show the band for"))}">
          ${choices.map(([key, label], i) => `<button type="button" class="seg-btn" data-series="${key}" aria-pressed="${i === 0}">${esc(t(label))}</button>`).join("")}
        </div>
        <div class="bc-head"></div>
        <div class="bc-readout"></div>
        <div class="bc-plot"></div>
        <dl class="mc-stats bc-stats"></dl>
      </div>`;
  }

  function bandHeadHTML(key, label, pts) {
    const last = pts[pts.length - 1];
    const prev = pts[pts.length - 2];
    let delta = "";
    if (prev) {
      const d = last.band - prev.band;
      delta = d === 0 ? `<span class="tile-delta is-flat">${t("Same as last time")}</span>`
        : `<span class="tile-delta ${d > 0 ? "is-up" : "is-down"}">${ARROW(d > 0)}${d > 0 ? "+" : "−"}${band(Math.abs(d))}</span>`;
    }
    return `
      <div class="bc-title"><strong>${t("Band score")}</strong> <span>${key === "overall" ? esc(t("(overall, estimated)")) : `(${esc(label)})`}</span></div>
      <div class="bc-figure"><span class="bc-value">${band(last.band)}</span>${delta}</div>`;
  }

  function bandStatsHTML(pts) {
    const bands = pts.map((p) => p.band);
    const avg = bands.reduce((a, b) => a + b, 0) / bands.length;
    return `<div><dt>${t("Best")}</dt><dd>${band(Math.max(...bands))}</dd></div>
      <div><dt>${t("Average")}</dt><dd>${avg.toFixed(1)}</dd></div>
      <div><dt>${t("Tests")}</dt><dd>${pts.length}</dd></div>`;
  }

  /** Draws the line at the plot's real width; the chosen test is marked on both axes like a crosshair. */
  function mountBandChart(card, key, label, color, pts, animate) {
    const plot = card.querySelector(".bc-plot");
    const readout = card.querySelector(".bc-readout");
    const value = card.querySelector(".bc-value");
    const W = Math.round(plot.clientWidth);
    if (!W) return;
    const H = W < 520 ? 230 : 280;
    const L = 4;
    const R = 46;
    const T = 14;
    const B = 34;
    const bands = pts.map((p) => p.band);
    const lo = Math.max(0, Math.min(Math.floor(Math.min(...bands)) - 1, 7));
    const step = 9 - lo > 6 ? 2 : 1;
    const x0 = L + 8;
    const x1 = W - R - 14;
    const X = (i) => (pts.length === 1 ? x1 : x0 + (i / (pts.length - 1)) * (x1 - x0));
    const Y = (b) => T + (1 - (b - lo) / (9 - lo)) * (H - T - B);
    const floor = Y(lo);
    const id = `pvg-${++gradients}`;

    const grid = [];
    for (let b = 9; b >= lo; b -= step) {
      grid.push(`<line x1="${L}" x2="${W - R}" y1="${Y(b)}" y2="${Y(b)}" class="pv-grid"/>
        <text x="${W - R + 10}" y="${Y(b) + 4}" class="pv-tick">${b}</text>`);
    }
    if ((9 - lo) % step) grid.push(`<line x1="${L}" x2="${W - R}" y1="${floor}" y2="${floor}" class="pv-grid"/>`);
    const labelled = pts.length < 3 ? [...new Set([0, pts.length - 1])]
      : W < 520 ? [0, Math.round((pts.length - 1) / 2), pts.length - 1]
        : [0, Math.round((pts.length - 1) / 3), Math.round((2 * (pts.length - 1)) / 3), pts.length - 1];
    const xLabels = [...new Set(labelled)].map((i) => `<text class="pv-tick bc-xl" data-i="${i}" x="${X(i)}" y="${H - 11}"
      text-anchor="${pts.length > 1 && i === 0 ? "start" : i === pts.length - 1 ? "end" : "middle"}">${esc(shortDate(new Date(pts[i].date).getTime()))}</text>`).join("");

    plot.innerHTML = `
      <svg class="bc-svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" tabindex="0"
        aria-label="${esc(t("{module} band after each test. Use the left and right arrow keys to read each test.", { module: label }))}">
        <defs>${gradient(id, color)}</defs>
        ${grid.join("")}
        <path class="bc-area" fill="url(#${id})"/>
        <path class="bc-line" fill="none" stroke="${color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
        <line class="bc-vx" y1="${T - 8}" y2="${H - B}"/>
        <line class="bc-hy" x1="${L}" x2="${W - R}"/>
        <g>${pts.length <= 40 ? pts.map(() => `<circle class="bc-dot" r="3" fill="${color}"/>`).join("") : ""}</g>
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
    const dots = svg.querySelectorAll(".bc-dot");
    const sel = $(".bc-sel");
    const vx = $(".bc-vx");
    const hy = $(".bc-hy");
    const badgeRect = $(".bc-badge rect");
    const badgeText = $(".bc-badge text");
    const pillRect = $(".bc-pill rect");
    const pillText = $(".bc-pill text");
    const xls = svg.querySelectorAll(".bc-xl");
    let k = 0;
    let current = pts.length - 1;

    const paint = () => {
      const at = pts.map((p, i) => [X(i), floor + (Y(p.band) - floor) * k]);
      line.setAttribute("d", pts.length > 1 ? smoothPath(at) : "");
      area.setAttribute("d", areaPath(at, floor));
      dots.forEach((c, i) => {
        c.setAttribute("cx", f1(at[i][0]));
        c.setAttribute("cy", f1(at[i][1]));
      });
      const [sx, sy] = at[current];
      sel.setAttribute("cx", f1(sx));
      sel.setAttribute("cy", f1(sy));
      vx.setAttribute("x1", f1(sx));
      vx.setAttribute("x2", f1(sx));
      hy.setAttribute("y1", f1(sy));
      hy.setAttribute("y2", f1(sy));
      // The numbers count up with the line: the band where the point is now.
      const shown = k === 1 ? band(bands[current]) : (lo + (bands[current] - lo) * k).toFixed(1);
      badgeRect.setAttribute("y", f1(sy - 11));
      badgeText.setAttribute("y", f1(sy + 4));
      badgeText.textContent = shown;
      if (value && current === pts.length - 1) value.textContent = shown;
    };

    const select = (i) => {
      current = i;
      const p = pts[i];
      pillText.textContent = shortDate(new Date(p.date).getTime());
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
      const from = key === "overall" ? `${(SERIES.find((s) => s[0] === p.module) || [, ""])[1]} · ` : "";
      readout.innerHTML = `<span class="bc-date">${esc(new Date(p.date).toLocaleDateString(loc(), { day: "numeric", month: "short", year: "numeric" }))}</span>
        <span class="bc-key"><span class="line-key" style="background:${color}" aria-hidden="true"></span>${t("Band")} <strong>${band(p.band)}</strong></span>
        <span class="bc-test">${esc(from + titleOf(p.testId))}</span>`;
      paint();
    };

    const nearest = (clientX) => {
      const box = svg.getBoundingClientRect();
      const x = ((clientX - box.left) / box.width) * W;
      let best = 0;
      pts.forEach((_, i) => { if (Math.abs(X(i) - x) < Math.abs(X(best) - x)) best = i; });
      return best;
    };
    const pick = (e) => { if (k === 1) select(nearest(e.clientX)); };
    svg.addEventListener("pointermove", pick);
    svg.addEventListener("pointerdown", pick);
    svg.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse" && k === 1) select(pts.length - 1); });
    svg.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      select(Math.max(0, Math.min(pts.length - 1, current + (e.key === "ArrowLeft" ? -1 : 1))));
    });

    select(current);
    rise(svg, (v) => {
      k = v;
      paint();
    }, animate);
  }

  function bindBandCard(root, points, animate) {
    const card = root.querySelector(".band-card");
    if (!card) return;
    const plot = card.querySelector(".bc-plot");
    let key = "overall";
    let width = 0;
    const show = (play) => {
      const [, label, color] = key === "overall" ? OVERALL : SERIES.find((s) => s[0] === key);
      const pts = seriesOf(points, key);
      card.querySelector(".bc-head").innerHTML = bandHeadHTML(key, label, pts);
      card.querySelector(".bc-stats").innerHTML = bandStatsHTML(pts);
      width = plot.clientWidth;
      mountBandChart(card, key, t(label), color, pts, play);
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
  const localKey = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

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

  /** opts.animate (default on): the lines rise from the floor as they come into view. */
  function render(el, points, activity = [], opts = {}) {
    if (!el) return;
    const animate = opts.animate !== false;
    const calendar = `<section class="activity-section" aria-labelledby="activity-title"></section>`;
    if (!points.length) {
      el.innerHTML = `
        <h2 class="section-title">${t("Your progress")}</h2>
        <p class="empty-inline">${t(window.Account && window.Account.commerce() ? "progress.empty" : "progress.empty.free")}</p>
        ${calendar}`;
      renderCalendar(el.querySelector(".activity-section"), activity);
      return;
    }
    const present = SERIES.filter(([key]) => points.some((p) => p.module === key));
    el.innerHTML = `
      <h2 class="section-title">${t("Your progress")}</h2>
      <p class="muted-text section-sub">${t("Timed Listening and Reading tests, and marked Writing and Speaking tests.")}</p>
      ${overallHTML(points)}
      ${tiles(points)}
      ${bandCardHTML(points)}
      <h3 class="sub-title">${t("All modules over time")}</h3>
      <div class="progress-viz">
        <div class="pv-legend">${present.map(([, label, color]) =>
          `<span class="pv-legend-item"><span class="line-key" style="background:${color}" aria-hidden="true"></span>${label}</span>`).join("")}</div>
        <div class="pv-plot"></div>
        ${table(points)}
      </div>
      ${calendar}`;
    bindBandCard(el, points, animate);
    el.querySelectorAll(".tile-spark-host").forEach((host) => {
      const [, , color] = SERIES.find((s) => s[0] === host.dataset.module);
      sparkline(host, points.filter((p) => p.module === host.dataset.module).map((p) => p.band), color, animate);
    });
    renderCalendar(el.querySelector(".activity-section"), activity);
    const plot = el.querySelector(".pv-plot");
    let lastWidth = 0;
    const draw = () => {
      const width = plot.clientWidth;
      if (!width || width === lastWidth) return;
      const first = !lastWidth;
      lastWidth = width;
      const g = layout(points, width);
      plot.innerHTML = chart(points, g);
      riseLines(plot, g, animate && first);
      bindHover(plot, points, g);
    };
    draw();
    if (window.ResizeObserver) new ResizeObserver(() => requestAnimationFrame(draw)).observe(plot);
  }

  window.Progress = { render };
})();
