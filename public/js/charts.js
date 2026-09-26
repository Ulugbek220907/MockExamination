/**
 * Task 1 visual renderer: line graphs, grouped bar charts, pie charts,
 * tables and process diagrams, drawn as inline SVG/HTML from JSON specs.
 * Also draws the maps used in Listening "label the map" questions.
 *
 * Charts sit on their own light "paper" surface (like a printed exam figure),
 * so the validated palette keeps its contrast in every contrast theme.
 * Identity is never carried by colour alone: line series have distinct marker
 * shapes and end labels, bars carry value labels, pie slices carry percentages,
 * and every chart includes a visually hidden data table for screen readers.
 */
(function () {
  "use strict";

  // Categorical palette in fixed slot order (validated: adjacent CVD ΔE ≥ 9.1).
  const SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
  const INK = "#0b0b0b";
  const INK_2 = "#52514e";
  const GRID = "#e1e0d9";
  const AXIS = "#c3c2b7";
  const SURFACE = "#fcfcfb";
  const MARKERS = ["circle", "square", "triangle", "diamond", "circle", "square", "triangle", "diamond"];

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (v, unit) => `${Number.isInteger(v) ? v : v.toFixed(1)}${unit || ""}`;

  function marker(shape, x, y, color) {
    const ring = `stroke="${SURFACE}" stroke-width="2"`;
    switch (shape) {
      case "square":
        return `<rect x="${x - 4.5}" y="${y - 4.5}" width="9" height="9" rx="1.5" fill="${color}" ${ring}/>`;
      case "triangle":
        return `<path d="M${x},${y - 6} L${x + 5.5},${y + 4.5} L${x - 5.5},${y + 4.5} Z" fill="${color}" ${ring}/>`;
      case "diamond":
        return `<path d="M${x},${y - 6} L${x + 6},${y} L${x},${y + 6} L${x - 6},${y} Z" fill="${color}" ${ring}/>`;
      default:
        return `<circle cx="${x}" cy="${y}" r="5" fill="${color}" ${ring}/>`;
    }
  }

  function legendHTML(items, kind) {
    return `<div class="fig-legend" aria-hidden="true">${items.map((it, i) => `
      <span class="fig-legend-item">
        ${kind === "line"
          ? `<svg width="26" height="12" viewBox="0 0 26 12"><line x1="1" y1="6" x2="25" y2="6" stroke="${it.color}" stroke-width="2.5"/>${marker(MARKERS[i], 13, 6, it.color)}</svg>`
          : `<span class="fig-swatch" style="background:${it.color}"></span>`}
        ${esc(it.label)}
      </span>`).join("")}</div>`;
  }

  function srTable(headers, rows, caption) {
    return `<table class="sr-only"><caption>${esc(caption)}</caption>
      <thead><tr>${headers.map((h) => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((r) => `<tr>${r.map((c, i) => (i === 0 ? `<th scope="row">${esc(c)}</th>` : `<td>${esc(c)}</td>`)).join("")}</tr>`).join("")}</tbody></table>`;
  }

  function niceMax(values, given) {
    if (given) return given;
    const max = Math.max(...values, 1);
    const pow = Math.pow(10, Math.floor(Math.log10(max)));
    return Math.ceil(max / pow) * pow;
  }

  /* ---------------------------------------------------------------- line */
  function lineChart(v) {
    const W = 680, H = 380, m = { l: 54, r: 128, t: 18, b: 58 };
    const pw = W - m.l - m.r, ph = H - m.t - m.b;
    const all = v.series.flatMap((s) => s.values);
    const yMax = niceMax(all, v.yMax);
    const step = v.yStep || yMax / 5;
    const x = (i) => m.l + (v.categories.length === 1 ? pw / 2 : (i * pw) / (v.categories.length - 1));
    const y = (val) => m.t + ph - (val / yMax) * ph;

    let svg = "";
    for (let t = 0; t <= yMax + 1e-9; t += step) {
      svg += `<line x1="${m.l}" x2="${m.l + pw}" y1="${y(t)}" y2="${y(t)}" stroke="${t === 0 ? AXIS : GRID}" stroke-width="1"/>`;
      svg += `<text x="${m.l - 8}" y="${y(t) + 4}" text-anchor="end" class="fig-tick">${fmt(t)}</text>`;
    }
    v.categories.forEach((c, i) => {
      svg += `<text x="${x(i)}" y="${m.t + ph + 20}" text-anchor="middle" class="fig-tick">${esc(c)}</text>`;
    });
    if (v.yLabel) {
      svg += `<text transform="translate(14 ${m.t + ph / 2}) rotate(-90)" text-anchor="middle" class="fig-axis-title">${esc(v.yLabel)}</text>`;
    }
    if (v.xLabel) {
      svg += `<text x="${m.l + pw / 2}" y="${H - 8}" text-anchor="middle" class="fig-axis-title">${esc(v.xLabel)}</text>`;
    }

    // Lines, then markers on top
    v.series.forEach((s, si) => {
      const color = SERIES[si];
      const d = s.values.map((val, i) => `${i ? "L" : "M"}${x(i)},${y(val)}`).join(" ");
      svg += `<path d="${d}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
    });
    v.series.forEach((s, si) => {
      s.values.forEach((val, i) => { svg += marker(MARKERS[si], x(i), y(val), SERIES[si]); });
    });

    // Direct end labels, nudged apart so they never collide
    const ends = v.series.map((s, si) => ({ label: s.name, y: y(s.values[s.values.length - 1]), si }));
    ends.sort((a, b) => a.y - b.y);
    for (let i = 1; i < ends.length; i++) {
      if (ends[i].y - ends[i - 1].y < 15) ends[i].y = ends[i - 1].y + 15;
    }
    ends.forEach((e) => {
      svg += `<text x="${m.l + pw + 12}" y="${e.y + 4}" class="fig-end-label">${esc(e.label)}</text>`;
    });

    const rows = v.categories.map((c, i) => [c, ...v.series.map((s) => fmt(s.values[i], v.unit))]);
    return `
      ${legendHTML(v.series.map((s, i) => ({ label: s.name, color: SERIES[i] })), "line")}
      <svg class="fig-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(v.title)}">${svg}</svg>
      ${srTable([v.xLabel || "", ...v.series.map((s) => s.name)], rows, v.title)}`;
  }

  /* ----------------------------------------------------------------- bar */
  function barChart(v) {
    const W = 680, H = 380, m = { l: 54, r: 16, t: 22, b: 58 };
    const pw = W - m.l - m.r, ph = H - m.t - m.b;
    const all = v.series.flatMap((s) => s.values);
    const yMax = niceMax(all, v.yMax);
    const step = v.yStep || yMax / 5;
    const y = (val) => m.t + ph - (val / yMax) * ph;
    const groupW = pw / v.categories.length;
    const gap = 2;
    const inner = groupW * 0.78;
    const barW = (inner - gap * (v.series.length - 1)) / v.series.length;

    let svg = "";
    for (let t = 0; t <= yMax + 1e-9; t += step) {
      svg += `<line x1="${m.l}" x2="${m.l + pw}" y1="${y(t)}" y2="${y(t)}" stroke="${t === 0 ? AXIS : GRID}" stroke-width="1"/>`;
      svg += `<text x="${m.l - 8}" y="${y(t) + 4}" text-anchor="end" class="fig-tick">${fmt(t)}</text>`;
    }
    v.categories.forEach((c, ci) => {
      const gx = m.l + ci * groupW + (groupW - inner) / 2;
      svg += `<text x="${m.l + ci * groupW + groupW / 2}" y="${m.t + ph + 20}" text-anchor="middle" class="fig-tick">${esc(c)}</text>`;
      v.series.forEach((s, si) => {
        const val = s.values[ci];
        const bx = gx + si * (barW + gap);
        const top = y(val);
        const h = m.t + ph - top;
        const r = Math.min(4, barW / 2, h);
        // Rounded top corners, square base anchored to the baseline
        svg += `<path d="M${bx},${m.t + ph} L${bx},${top + r} Q${bx},${top} ${bx + r},${top} L${bx + barW - r},${top} Q${bx + barW},${top} ${bx + barW},${top + r} L${bx + barW},${m.t + ph} Z" fill="${SERIES[si]}"/>`;
        svg += `<text x="${bx + barW / 2}" y="${top - 5}" text-anchor="middle" class="fig-value">${fmt(val)}</text>`;
      });
    });
    if (v.yLabel) {
      svg += `<text transform="translate(14 ${m.t + ph / 2}) rotate(-90)" text-anchor="middle" class="fig-axis-title">${esc(v.yLabel)}</text>`;
    }
    if (v.xLabel) {
      svg += `<text x="${m.l + pw / 2}" y="${H - 8}" text-anchor="middle" class="fig-axis-title">${esc(v.xLabel)}</text>`;
    }

    const rows = v.categories.map((c, i) => [c, ...v.series.map((s) => fmt(s.values[i], v.unit))]);
    return `
      ${legendHTML(v.series.map((s, i) => ({ label: s.name, color: SERIES[i] })), "bar")}
      <svg class="fig-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(v.title)}">${svg}</svg>
      ${srTable([v.xLabel || "", ...v.series.map((s) => s.name)], rows, v.title)}`;
  }

  /* ----------------------------------------------------------------- pie */
  function luminance(hex) {
    const n = parseInt(hex.slice(1), 16);
    const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => {
      c /= 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
  }

  /** Pick whichever ink (near-black or white) has the higher contrast ratio on the slice colour. */
  function labelInk(bg) {
    const l = luminance(bg);
    const onDark = (1.05) / (l + 0.05);
    const onLight = (l + 0.05) / (luminance(INK) + 0.05);
    return onLight >= onDark ? INK : "#ffffff";
  }

  function pieChart(v) {
    // Colour follows the category label, so a slice keeps its colour across charts.
    const labels = [];
    v.charts.forEach((c) => c.slices.forEach((s) => { if (!labels.includes(s.label)) labels.push(s.label); }));
    const colorOf = (label) => SERIES[labels.indexOf(label) % SERIES.length];

    const pies = v.charts.map((chart) => {
      const S = 300, cx = S / 2, cy = S / 2 + 6, r = 118;
      const total = chart.slices.reduce((a, s) => a + s.value, 0);
      let angle = -Math.PI / 2;
      let paths = "", texts = "";
      chart.slices.forEach((s) => {
        const sweep = (s.value / total) * Math.PI * 2;
        const a0 = angle, a1 = angle + sweep;
        angle = a1;
        const large = sweep > Math.PI ? 1 : 0;
        const p0 = [cx + r * Math.cos(a0), cy + r * Math.sin(a0)];
        const p1 = [cx + r * Math.cos(a1), cy + r * Math.sin(a1)];
        const color = colorOf(s.label);
        paths += `<path d="M${cx},${cy} L${p0[0]},${p0[1]} A${r},${r} 0 ${large} 1 ${p1[0]},${p1[1]} Z" fill="${color}" stroke="${SURFACE}" stroke-width="2" stroke-linejoin="round"/>`;
        const mid = (a0 + a1) / 2;
        const text = fmt(s.value, v.unit || "%");
        if (sweep > 0.42) {
          const tx = cx + r * 0.64 * Math.cos(mid), ty = cy + r * 0.64 * Math.sin(mid);
          const fill = labelInk(color);
          texts += `<text x="${tx}" y="${ty + 5}" text-anchor="middle" class="fig-slice-label" fill="${fill}">${text}</text>`;
        } else {
          // Small slice: label outside with a short leader line
          const ex = cx + (r + 6) * Math.cos(mid), ey = cy + (r + 6) * Math.sin(mid);
          const lx = cx + (r + 20) * Math.cos(mid), ly = cy + (r + 20) * Math.sin(mid);
          const anchor = Math.cos(mid) >= 0 ? "start" : "end";
          texts += `<line x1="${ex}" y1="${ey}" x2="${lx}" y2="${ly}" stroke="${INK_2}" stroke-width="1"/>`;
          texts += `<text x="${lx + (anchor === "start" ? 3 : -3)}" y="${ly + 4}" text-anchor="${anchor}" class="fig-value">${text}</text>`;
        }
      });
      return `<figure class="fig-pie">
        <figcaption>${esc(chart.title)}</figcaption>
        <svg class="fig-svg" viewBox="-20 -8 ${S + 40} ${S + 16}" role="img" aria-label="${esc(v.title + " – " + chart.title)}">${paths}${texts}</svg>
      </figure>`;
    });

    const headers = ["Category", ...v.charts.map((c) => c.title)];
    const rows = labels.map((l) => [l, ...v.charts.map((c) => {
      const s = c.slices.find((x) => x.label === l);
      return s ? fmt(s.value, v.unit || "%") : "–";
    })]);
    return `
      <div class="fig-pies">${pies.join("")}</div>
      ${legendHTML(labels.map((l) => ({ label: l, color: colorOf(l) })), "pie")}
      ${srTable(headers, rows, v.title)}`;
  }

  /* --------------------------------------------------------------- table */
  function tableChart(v) {
    return `<table class="fig-table">
      <thead><tr>${v.headers.map((h) => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead>
      <tbody>${v.rows.map((r) => `<tr>${r.map((c, i) => (i === 0 ? `<th scope="row">${esc(c)}</th>` : `<td>${esc(c)}</td>`)).join("")}</tr>`).join("")}</tbody>
    </table>`;
  }

  /* ------------------------------------------------------------- process */
  function processChart(v) {
    const steps = v.steps.map((s, i) => `
      <li class="fig-step">
        <span class="fig-step-num" aria-hidden="true">${i + 1}</span>
        <div><strong>${esc(s.label)}</strong><span>${esc(s.text)}</span></div>
      </li>`).join("");
    return `<ol class="fig-process">${steps}</ol>
      ${v.cycle ? `<p class="fig-cycle-note">↻ After stage ${v.steps.length}, the cycle returns to stage 1.</p>` : ""}`;
  }

  /* ----------------------------------------------------- listening map */
  // Plan/map for "Label the map" questions. Letters are drawn on white discs;
  // every label has a paper-coloured halo so it stays legible over any fill.
  const MAP = {
    grass: ["#e6f0dc", "#9fbf8a"], water: ["#cfe6f7", "#6f9fcb"], path: "#dccaa3",
    parking: ["#eef0f3", "#8a94a3"], building: ["#f6e7c8", "#a37b3b"], tree: ["#8fbf7a", "#5f8f4c"],
  };

  function mapLabel(x, y, text, { anchor = "middle", italic = false } = {}) {
    return `<text x="${x}" y="${y}" text-anchor="${anchor}" class="map-label" paint-order="stroke"
      stroke="${SURFACE}" stroke-width="4" stroke-linejoin="round" ${italic ? 'font-style="italic"' : ""}>${esc(text)}</text>`;
  }

  function mapItem(it) {
    switch (it.type) {
      case "area": {
        const [fill, stroke] = MAP[it.style] || MAP.grass;
        return `<rect x="${it.x}" y="${it.y}" width="${it.w}" height="${it.h}" rx="14" fill="${fill}" stroke="${stroke}" stroke-width="2"/>`;
      }
      case "trees": {
        let out = "";
        for (let ty = it.y + 14; ty <= it.y + it.h - 12; ty += 24) {
          for (let tx = it.x + 14 + (((ty - it.y) / 24) % 2 ? 12 : 0); tx <= it.x + it.w - 12; tx += 24) {
            out += `<circle cx="${tx}" cy="${ty}" r="10" fill="${MAP.tree[0]}" stroke="${MAP.tree[1]}" stroke-width="1.5"/>`;
          }
        }
        return out + (it.label ? mapLabel(it.x + it.w / 2, it.y + it.h / 2 + 5, it.label) : "");
      }
      case "ellipse":
        if (it.style === "path-ring") {
          return `<ellipse cx="${it.cx}" cy="${it.cy}" rx="${it.rx}" ry="${it.ry}" fill="none" stroke="${MAP.path}" stroke-width="12"/>`;
        }
        return `<ellipse cx="${it.cx}" cy="${it.cy}" rx="${it.rx}" ry="${it.ry}" fill="${MAP.water[0]}" stroke="${MAP.water[1]}" stroke-width="2"/>
          ${it.label ? mapLabel(it.cx, it.cy + 5, it.label, { italic: true }) : ""}`;
      case "line":
        return `<line x1="${it.x1}" y1="${it.y1}" x2="${it.x2}" y2="${it.y2}" stroke="${MAP.path}" stroke-width="12" stroke-linecap="round"/>`;
      case "rect": {
        const [fill, stroke] = MAP[it.style] || MAP.building;
        return `<rect x="${it.x}" y="${it.y}" width="${it.w}" height="${it.h}" rx="4" fill="${fill}" stroke="${stroke}" stroke-width="2"/>
          ${it.label ? mapLabel(it.x + it.w / 2, it.y + it.h / 2 + 5, it.label) : ""}`;
      }
      case "gate":
        return `<rect x="${it.x - 16}" y="${it.y - 6}" width="32" height="7" rx="2" fill="${INK_2}"/>
          ${it.label ? mapLabel(it.x + 22, it.y - 6, it.label, { anchor: "start" }) : ""}`;
      case "compass":
        return `<g aria-hidden="true">
          <circle cx="${it.x}" cy="${it.y}" r="19" fill="${SURFACE}" stroke="${INK_2}" stroke-width="1.5"/>
          <path d="M${it.x},${it.y - 13} L${it.x + 6},${it.y + 8} L${it.x},${it.y + 3} L${it.x - 6},${it.y + 8} Z" fill="${INK}"/>
          <text x="${it.x}" y="${it.y - 24}" text-anchor="middle" class="map-label">N</text></g>`;
      case "letter":
        return `<circle cx="${it.x}" cy="${it.y}" r="14" fill="#ffffff" stroke="${INK}" stroke-width="2"/>
          <text x="${it.x}" y="${it.y + 6}" text-anchor="middle" class="map-letter">${esc(it.letter)}</text>`;
      default:
        return "";
    }
  }

  function renderMap(map) {
    if (!map) return "";
    const letters = (map.items || []).filter((i) => i.type === "letter").map((i) => i.letter);
    const label = `Map of ${map.title || "the area"}. Letters ${letters[0]} to ${letters[letters.length - 1]} mark places on the map.`;
    return `<div class="task-figure map-figure">
      ${map.title ? `<div class="fig-title">${esc(map.title)}</div>` : ""}
      <div class="map-scroll">
        <svg class="fig-svg map-svg" viewBox="0 0 ${map.width} ${map.height}" role="img" aria-label="${esc(label)}">
          ${(map.items || []).map(mapItem).join("")}
        </svg>
      </div>
    </div>`;
  }

  function render(visual) {
    if (!visual) return "";
    let body = "";
    switch (visual.type) {
      case "line": body = lineChart(visual); break;
      case "bar": body = barChart(visual); break;
      case "pie": body = pieChart(visual); break;
      case "table": body = tableChart(visual); break;
      case "process": body = processChart(visual); break;
      default: return "";
    }
    return `<div class="task-figure">
      ${visual.title ? `<div class="fig-title">${esc(visual.title)}</div>` : ""}
      ${visual.yLabel && (visual.type === "line" || visual.type === "bar") ? `<div class="fig-subtitle">${esc(visual.yLabel)}</div>` : ""}
      ${body}
      ${visual.note ? `<div class="fig-note">${esc(visual.note)}</div>` : ""}
    </div>`;
  }

  window.TaskCharts = { render, renderMap };
})();
