/* The band score calculator on the calculator pages. The tables come from the page (data-listening, data-reading),
   which gets them from the server's scoring tables, so the page and the app agree. */
(function () {
  "use strict";
  var form = document.querySelector("[data-calc]");
  if (!form) return;

  var tables = { l: JSON.parse(form.dataset.listening), r: JSON.parse(form.dataset.reading) };
  var out = {};
  form.querySelectorAll("[data-out]").forEach(function (el) { out[el.dataset.out] = el; });

  function bandFor(table, raw) {
    for (var i = 0; i < table.length; i++) if (raw >= table[i][0]) return table[i][1];
    return 2.0;
  }

  function raw(name) {
    var value = form.elements[name].value;
    if (value === "") return null;
    var n = Number(value);
    return Number.isInteger(n) && n >= 0 && n <= 40 ? n : null;
  }

  function band(name) {
    var value = form.elements[name].value;
    return value === "" ? null : Number(value);
  }

  // Four bands averaged, rounded to the nearest half band: .25 up to .5, .75 up to the next whole band.
  function overall(bands) {
    var eighths = Math.round(bands.reduce(function (a, b) { return a + b; }, 0) * 2);
    var whole = Math.floor(eighths / 8), rest = eighths % 8;
    return whole + (rest < 2 ? 0 : rest < 6 ? 0.5 : 1);
  }

  function show(el, value) { el.textContent = value === null ? "–" : value.toFixed(1); }

  function update() {
    var l = raw("l"), r = raw("r"), w = band("w"), s = band("s");
    var lb = l === null ? null : bandFor(tables.l, l);
    var rb = r === null ? null : bandFor(tables.r, r);
    show(out.l, lb);
    show(out.r, rb);
    show(out.o, lb !== null && rb !== null && w !== null && s !== null ? overall([lb, rb, w, s]) : null);
  }

  form.addEventListener("submit", function (e) { e.preventDefault(); });
  form.addEventListener("input", update);
  form.addEventListener("change", update);
  update();
})();
