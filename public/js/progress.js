/**
 * Progress on the account page: a stat tile per module (latest band and the
 * change since the previous test) and a line chart of band scores over time,
 * with a hover/keyboard readout, a legend, direct end labels and a table view.
 *
 * Progress.render(el, points) – points from GET /api/progress:
 *   [{module, date, band, testId, source}] oldest first.
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
  const shortDate = (t) => new Date(t).toLocaleDateString(undefined, { day: "numeric", month: "short" });
  const titleOf = (id) => {
    const t = ((window.app && window.app.tests) || []).find((x) => x.id === id);
    return t ? t.shortTitle : id;
  };

  function tiles(points) {
    return `<div class="progress-tiles">${SERIES.map(([key, label, color]) => {
      const pts = points.filter((p) => p.module === key);
      const last = pts[pts.length - 1];
      const prev = pts[pts.length - 2];
      let delta = `<span class="tile-delta is-flat">${pts.length ? "First test" : "No tests yet"}</span>`;
      if (last && prev) {
        const d = last.band - prev.band;
        delta = d === 0
          ? `<span class="tile-delta is-flat">= same as last time</span>`
          : `<span class="tile-delta ${d > 0 ? "is-up" : "is-down"}"><span aria-hidden="true">${d > 0 ? "▲" : "▼"}</span>
              ${d > 0 ? "+" : "−"}${band(Math.abs(d))} since last time</span>`;
      }
      const best = pts.length ? Math.max(...pts.map((p) => p.band)) : null;
      return `
        <div class="progress-tile">
          <div class="tile-label"><span class="line-key" style="background:${color}" aria-hidden="true"></span>${label}</div>
          <div class="tile-value">${last ? band(last.band) : "–"}</div>
          ${delta}
          <div class="tile-sub">${pts.length ? `Best ${band(best)} · ${pts.length} test${pts.length === 1 ? "" : "s"}` : "&nbsp;"}</div>
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
      return `<path d="${d}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
        ${pts.map(([x, y]) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4" fill="${color}" class="pv-dot"/>`).join("")}`;
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
        aria-label="Band scores over time for ${present.map((s) => s[1]).join(", ")}. Use the left and right arrow keys to read each date.">
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
        <summary>Show as a table</summary>
        <div class="table-scroll"><table class="history-table">
          <thead><tr><th scope="col">Date</th><th scope="col">Module</th><th scope="col">Test</th><th scope="col">Band</th><th scope="col">Marked by</th></tr></thead>
          <tbody>${points.slice().reverse().map((p) => `
            <tr><td>${esc(U.formatDate(p.date))}</td><td>${esc((SERIES.find((s) => s[0] === p.module) || [, p.module])[1])}</td>
              <td>${esc(titleOf(p.testId))}</td><td><strong>${band(p.band)}</strong></td><td>${esc(SOURCE[p.source] || "")}</td></tr>`).join("")}</tbody>
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
      head.textContent = new Date(onDay[0].date).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
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

  function render(el, points) {
    if (!el) return;
    if (!points.length) {
      el.innerHTML = `
        <h2 class="section-title">Your progress</h2>
        <p class="empty-inline">Take a timed Listening or Reading test, or get a Writing or Speaking test marked, and your band scores will appear here.</p>`;
      return;
    }
    const present = SERIES.filter(([key]) => points.some((p) => p.module === key));
    el.innerHTML = `
      <h2 class="section-title">Your progress</h2>
      <p class="muted-text section-sub">Timed Listening and Reading tests, and marked Writing and Speaking tests.</p>
      ${tiles(points)}
      <div class="progress-viz">
        <div class="pv-legend">${present.map(([, label, color]) =>
          `<span class="pv-legend-item"><span class="line-key" style="background:${color}" aria-hidden="true"></span>${label}</span>`).join("")}</div>
        <div class="pv-plot"></div>
        ${table(points)}
      </div>`;
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
