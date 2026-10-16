/**
 * Draws public/img/og.png (1200 x 630), the picture shown when testday.uz is shared in
 * Telegram, WhatsApp, Facebook or X: the four lines meeting at the Test day interchange.
 *
 * Run after changing the brand colours or the wording:
 *   npm i -D playwright   (or use a global install)
 *   node scripts/make_og_image.js
 */
const path = require("path");

let chromium;
try {
  ({ chromium } = require("playwright"));
} catch (e) {
  ({ chromium } = require(require("child_process").execSync("npm root -g").toString().trim() + "/playwright"));
}

const root = path.join(__dirname, "..");
const font = require("fs").readFileSync(path.join(root, "public", "fonts", "jost-latin.woff2")).toString("base64");
const out = path.join(root, "public", "img", "og.png");

// Brand colours (see DESIGN.md).
const C = { granite: "#142038", granite2: "#1d2b47", ink: "#eef2f8", muted: "#a9b5ca",
  l: "#1f5fbf", r: "#cf3a2c", w: "#1e7c42", s: "#e3a21a" };

// Four lines run left to right and bend into one interchange at the right.
const lines = [
  { c: C.l, y: 318, letter: "L" },
  { c: C.r, y: 392, letter: "R" },
  { c: C.w, y: 466, letter: "W" },
  { c: C.s, y: 540, letter: "S" },
];
const hub = { x: 1000, y: 430 };
const track = lines.map(({ c, y }, i) => {
  const end = hub.y - 42 + i * 28;
  return `<path d="M 150 ${y} H 860 C 960 ${y}, 940 ${end}, ${hub.x - 18} ${end}" stroke="${c}" stroke-width="14" fill="none" stroke-linecap="round"/>
    ${[300, 450, 600, 750].map((x) => `<circle cx="${x}" cy="${y}" r="13" fill="${C.granite}" stroke="${c}" stroke-width="7"/>`).join("")}
    <circle cx="110" cy="${y}" r="26" fill="${c}"/>
    <text x="110" y="${y + 10}" text-anchor="middle" font-size="28" font-weight="700" fill="${i === 3 ? C.granite : "#fff"}">${lines[i].letter}</text>`;
}).join("");

const html = `<!doctype html><html><head><style>
  @font-face { font-family: Jost; src: url("data:font/woff2;base64,${font}") format("woff2"); font-weight: 300 800; }
  html, body { margin: 0; }
  body { width: 1200px; height: 630px; background: ${C.granite}; font-family: Jost, sans-serif; overflow: hidden; }
  svg { display: block; }
</style></head><body>
<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg" font-family="Jost">
  <rect width="1200" height="630" fill="${C.granite}"/>
  <rect y="0" width="300" height="10" fill="${C.l}"/><rect x="300" y="0" width="300" height="10" fill="${C.r}"/>
  <rect x="600" y="0" width="300" height="10" fill="${C.w}"/><rect x="900" y="0" width="300" height="10" fill="${C.s}"/>
  <g transform="translate(84 62)">
    <g fill="none" stroke-width="10" transform="rotate(-90 28 28)">
      <circle cx="28" cy="28" r="20" stroke="${C.l}" stroke-dasharray="27.6 98" stroke-dashoffset="-1.6"/>
      <circle cx="28" cy="28" r="20" stroke="${C.r}" stroke-dasharray="27.6 98" stroke-dashoffset="-33"/>
      <circle cx="28" cy="28" r="20" stroke="${C.w}" stroke-dasharray="27.6 98" stroke-dashoffset="-64.4"/>
      <circle cx="28" cy="28" r="20" stroke="${C.s}" stroke-dasharray="27.6 98" stroke-dashoffset="-95.8"/>
    </g>
    <text x="74" y="40" font-size="40" font-weight="650" fill="${C.ink}">TestDay</text>
  </g>
  <text x="84" y="196" font-size="64" font-weight="650" fill="#fff" letter-spacing="-1.2">Every line ends at test day.</text>
  <text x="86" y="246" font-size="27" font-weight="400" fill="${C.muted}">Computer-delivered IELTS practice · the first test of every module is free</text>
  ${track}
  <rect x="${hub.x - 22}" y="${hub.y - 64}" width="44" height="128" rx="22" fill="#fff" stroke="${C.ink}" stroke-width="8"/>
  <text x="${hub.x + 40}" y="${hub.y - 6}" font-size="30" font-weight="650" fill="#fff">Test day</text>
  <text x="${hub.x + 40}" y="${hub.y + 28}" font-size="20" fill="${C.muted}">testday.uz</text>
</svg></body></html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
  await page.setContent(html, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  const loaded = await page.evaluate(() => document.fonts.check("650 64px Jost"));
  if (!loaded) throw new Error("Jost did not load; the image would use a fallback font");
  await page.screenshot({ path: out, type: "png" });
  await browser.close();
  console.log("wrote", path.relative(root, out));
})();
