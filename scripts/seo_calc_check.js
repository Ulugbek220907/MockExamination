// Runs public/js/seo-calc.js against a stand-in page and prints the three results it shows (Listening, Reading and
// overall band), so the tests can compare the script with the server's tables and rounding.
// usage: node seo_calc_check.js <listening raw> <reading raw> <writing band> <speaking band> <listening table json> <reading table json>
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const [l, r, w, s, listening, reading] = process.argv.slice(2);
const values = { l, r, w, s };
const outputs = { l: { textContent: "" }, r: { textContent: "" }, o: { textContent: "" } };
const form = {
  dataset: { listening, reading },
  elements: Object.fromEntries(Object.keys(values).map((k) => [k, { value: values[k] }])),
  querySelectorAll: () => Object.entries(outputs).map(([key, el]) => Object.assign(el, { dataset: { out: key } })),
  addEventListener() {},
};
const context = { document: { querySelector: () => form }, Number, Math, JSON, Array };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "..", "public", "js", "seo-calc.js"), "utf8"), context);
console.log([outputs.l.textContent, outputs.r.textContent, outputs.o.textContent].join(" "));
