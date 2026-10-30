/**
 * Progress on the account page:
 *   - an estimated overall band and a stat tile per module (latest band and the
 *     change since the previous test);
 *   - a band chart for each module (every test as a dot, with average and best);
 *   - a line chart of all four modules over time, with a hover/keyboard readout,
 *     a legend, direct end labels and a table view;
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
          <div class="tile-value">${last ? band(last.band) : "–"}</div>
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
    const lines = present.map(([key, , color]) => {
      const pts = points.filter((p) => p.module === key).map((p) => [X(new Date(p.date).getTime()), Y(p.band)]);
      const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join("");
      // A thin line with a dot at every test.
      return `<path d="${d}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
        ${pts.map(([x, y]) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4" fill="${color}" stroke="var(--pv-surface)" stroke-width="2"/>`).join("")}`;
    }).join("");

    // Direct labels at each line's end – only when none of them collide (the legend and table always remain).
    const ends = present.map(([key, label]) => {
      const pts = points.filter((p) => p.module === key);
      const p = pts[pts.length - 1];
      return { x: X(new Date(p.date).getTime()) + 8, y: Y(p.band) + 4, text: `${label} ${band(p.band)}` };
    });
    const collide = g.narrow || ends.some((a, i) => ends.some((b, j) => j > i && Math.abs(a.y - b.y) < 14 && Math.abs(a.x - b.x) < 90));
    const labels = collide ? "" : ends.map((e) => `<text x="${e.x}" y="${e.y}" class="pv-end">${esc(e.text)}</text>`).join("");

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
  function overallHTML(points) {
    const latest = SERIES.map(([key]) => points.filter((p) => p.module === key).pop()).filter(Boolean);
    if (!latest.length) return "";
    const mean = latest.reduce((a, p) => a + p.band, 0) / latest.length;
    const whole = Math.floor(mean);
    const frac = mean - whole;
    const overall = frac < 0.25 ? whole : frac < 0.75 ? whole + 0.5 : whole + 1;
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

  /* ---------------------------------------------------------- module charts */
  function moduleChart(pts, color, W) {
    const H = 132;
    const L = 26;
    const R = 10;
    const T = 10;
    const B = 22;
    const lo = Math.max(0, Math.min(Math.floor(Math.min(...pts.map((p) => p.band))) - 1, 7));
    const X = (i) => (pts.length === 1 ? (L + W - R) / 2 : L + (i / (pts.length - 1)) * (W - L - R));
    const Y = (b) => T + (1 - (b - lo) / (9 - lo)) * (H - T - B);
    const grid = [];
    for (let b = lo; b <= 9; b++) {
      if ((9 - b) % (9 - lo > 5 ? 2 : 1)) continue;
      grid.push(`<line x1="${L}" x2="${W - R}" y1="${Y(b)}" y2="${Y(b)}" class="pv-grid"/><text x="${L - 6}" y="${Y(b) + 4}" text-anchor="end" class="pv-tick">${b}</text>`);
    }
    const avg = pts.reduce((a, p) => a + p.band, 0) / pts.length;
    const line = pts.map((p, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(p.band).toFixed(1)}`).join("");
    const first = shortDate(new Date(pts[0].date).getTime());
    const last = shortDate(new Date(pts[pts.length - 1].date).getTime());
    return `
      <svg class="mc-svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true">
        ${grid.join("")}
        <line x1="${L}" x2="${W - R}" y1="${Y(avg)}" y2="${Y(avg)}" class="mc-avg"/>
        ${pts.length > 1 ? `<path d="${line}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>` : ""}
        ${pts.map((p, i) => `<circle cx="${X(i).toFixed(1)}" cy="${Y(p.band).toFixed(1)}" r="${i === pts.length - 1 ? 5 : 4}" fill="${color}" stroke="var(--pv-surface)" stroke-width="2" data-i="${i}"/>`).join("")}
        <text x="${L}" y="${H - 5}" class="pv-tick">${esc(first)}</text>
        ${pts.length > 1 ? `<text x="${W - R}" y="${H - 5}" text-anchor="end" class="pv-tick">${esc(last)}</text>` : ""}
      </svg>`;
  }

  function moduleCardsHTML(points) {
    return `<div class="module-charts">${SERIES.map(([key, label, color]) => {
      const pts = points.filter((p) => p.module === key);
      if (!pts.length) {
        return `<div class="module-chart is-empty"><div class="mc-head"><span class="mc-name"><span class="line-key" style="background:${color}" aria-hidden="true"></span>${label}</span></div>
          <p class="muted-text">${t("No {module} band yet.", { module: label })}</p></div>`;
      }
      const bands = pts.map((p) => p.band);
      const avg = bands.reduce((a, b) => a + b, 0) / bands.length;
      const summary = t("{module}: {n} tests, latest {latest}, best {best}, average {avg}.", {
        module: label, n: pts.length, latest: band(bands[bands.length - 1]), best: band(Math.max(...bands)), avg: avg.toFixed(1) });
      return `
        <div class="module-chart" data-module="${key}" role="group" aria-label="${esc(summary)}">
          <div class="mc-head">
            <span class="mc-name"><span class="line-key" style="background:${color}" aria-hidden="true"></span>${label}</span>
            <span class="mc-latest">${band(bands[bands.length - 1])}</span>
          </div>
          <div class="mc-plot"></div>
          <dl class="mc-stats">
            <div><dt>${t("Best")}</dt><dd>${band(Math.max(...bands))}</dd></div>
            <div><dt>${t("Average")}</dt><dd>${avg.toFixed(1)}</dd></div>
            <div><dt>${t("Tests")}</dt><dd>${pts.length}</dd></div>
          </dl>
          <div class="pv-tip mc-tip" role="status" hidden></div>
        </div>`;
    }).join("")}</div>`;
  }

  function drawModuleCharts(root, points) {
    root.querySelectorAll(".module-chart[data-module]").forEach((card) => {
      const key = card.dataset.module;
      const [, label, color] = SERIES.find((s) => s[0] === key);
      const pts = points.filter((p) => p.module === key);
      const plot = card.querySelector(".mc-plot");
      const tip = card.querySelector(".mc-tip");
      let lastWidth = 0;
      const draw = () => {
        const W = Math.round(plot.clientWidth);
        if (!W || W === lastWidth) return;
        lastWidth = W;
        plot.innerHTML = moduleChart(pts, color, W);
        const svg = plot.querySelector("svg");
        const near = (e) => {
          const box = svg.getBoundingClientRect();
          const x = ((e.clientX - box.left) / box.width) * W;
          let best = null;
          svg.querySelectorAll("circle").forEach((c) => {
            const d = Math.abs(Number(c.getAttribute("cx")) - x);
            if (!best || d < best.d) best = { d, c };
          });
          return best && best.c;
        };
        svg.addEventListener("pointermove", (e) => {
          const c = near(e);
          if (!c) return;
          const p = pts[Number(c.dataset.i)];
          tip.innerHTML = `<div class="pv-tip-date">${esc(new Date(p.date).toLocaleDateString(loc(), { day: "numeric", month: "long", year: "numeric" }))}</div>
            <div class="pv-tip-row"><span class="line-key" style="background:${color}"></span><strong>${band(p.band)}</strong><span>${esc(label)} · ${esc(titleOf(p.testId))}</span></div>`;
          tip.hidden = false;
          const box = svg.getBoundingClientRect();
          const cx = (Number(c.getAttribute("cx")) / W) * box.width;
          tip.style.left = `${Math.min(Math.max(0, cx - tip.offsetWidth / 2), box.width - tip.offsetWidth)}px`;
          tip.style.top = `${plot.offsetTop - 4}px`;
        });
        svg.addEventListener("pointerleave", () => { tip.hidden = true; });
      };
      draw();
      if (window.ResizeObserver) new ResizeObserver(() => requestAnimationFrame(draw)).observe(plot);
    });
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

  function render(el, points, activity = []) {
    if (!el) return;
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
      <h3 class="sub-title">${t("Band by module")}</h3>
      ${moduleCardsHTML(points)}
      <h3 class="sub-title">${t("All modules over time")}</h3>
      <div class="progress-viz">
        <div class="pv-legend">${present.map(([, label, color]) =>
          `<span class="pv-legend-item"><span class="line-key" style="background:${color}" aria-hidden="true"></span>${label}</span>`).join("")}</div>
        <div class="pv-plot"></div>
        ${table(points)}
      </div>
      ${calendar}`;
    drawModuleCharts(el, points);
    renderCalendar(el.querySelector(".activity-section"), activity);
    const plot = el.querySelector(".pv-plot");
    let lastWidth = 0;
    const draw = () => {
      const width = plot.clientWidth;
      if (!width || width === lastWidth) return;
      lastWidth = width;
      const g = layout(points, width);
      plot.innerHTML = chart(points, g);
      bindHover(plot, points, g);
    };
    draw();
    if (window.ResizeObserver) new ResizeObserver(() => requestAnimationFrame(draw)).observe(plot);
  }

  window.Progress = { render };
})();
