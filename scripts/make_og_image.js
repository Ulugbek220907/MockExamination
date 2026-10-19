/**
 * Draws the images that stand for TestDay outside the site:
 *   public/img/og.png          1200 x 630, shown when testday.uz is shared in Telegram, WhatsApp, Facebook or X
 *   public/img/logo-512.png     512 x 512, the logo in the search-engine data (index.html)
 *   public/img/email-logo.png    96 x 96, the logo at the top of the emails
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
const font = require("fs").readFileSync(path.join(root, "public", "fonts", "schibsted-grotesk-core.woff2")).toString("base64");
const img = (name) => path.join(root, "public", "img", name);

// The brand (see DESIGN.md): a warm ground and one deep ink.
const C = { ground: "#e9e8e2", ink: "#0f1a30", soft: "#aeb8cb", muted: "#4a566b" };

const fontFace = `@font-face { font-family: "Schibsted Grotesk"; src: url("data:font/woff2;base64,${font}") format("woff2"); font-weight: 400 700; }
  html, body { margin: 0; } svg { display: block; }`;

const og = `<!doctype html><html><head><style>${fontFace}
  body { width: 1200px; height: 630px; overflow: hidden; background: ${C.ground}; }
</style></head><body>
<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg" font-family="Schibsted Grotesk">
  <rect width="1200" height="630" fill="${C.ground}"/>
  <text x="72" y="104" font-size="40" font-weight="650" fill="${C.ink}" letter-spacing="-0.8">TestDay</text>
  <text x="68" y="318" font-size="148" font-weight="600" fill="${C.ink}" letter-spacing="-5.5">IELTS practice</text>
  <text x="68" y="452" font-size="148" font-weight="600" fill="${C.ink}" letter-spacing="-5.5">like test day</text>
  <rect y="530" width="1200" height="100" fill="${C.ink}"/>
  <g font-size="30" font-weight="500" fill="${C.ground}">
    <text x="72" y="592">Listening</text><text x="302" y="592">Reading</text>
    <text x="500" y="592">Writing</text><text x="690" y="592">Speaking</text>
  </g>
  <text x="1128" y="592" text-anchor="end" font-size="30" font-weight="500" fill="${C.soft}">testday.uz</text>
</svg></body></html>`;

// A "T" in a rounded square: the same mark as public/favicon.svg.
const mark = (size) => `<!doctype html><html><head><style>${fontFace} body { width: ${size}px; height: ${size}px; background: transparent; }</style></head><body>
<svg width="${size}" height="${size}" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
  <rect width="32" height="32" rx="7" fill="${C.ink}"/><path d="M8 9h16v3.6h-6.2V24h-3.6V12.6H8z" fill="${C.ground}"/>
</svg></body></html>`;

async function draw(browser, html, w, h, file, transparent) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await page.setContent(html, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  if (!transparent) {
    const loaded = await page.evaluate(() => document.fonts.check('600 64px "Schibsted Grotesk"'));
    if (!loaded) throw new Error("Schibsted Grotesk did not load; the image would use a fallback font");
  }
  await page.screenshot({ path: file, type: "png", omitBackground: Boolean(transparent) });
  await page.close();
  console.log("wrote", path.relative(root, file));
}

(async () => {
  const browser = await chromium.launch();
  await draw(browser, og, 1200, 630, img("og.png"));
  await draw(browser, mark(512), 512, 512, img("logo-512.png"), true);
  await draw(browser, mark(96), 96, 96, img("email-logo.png"), true);
  await browser.close();
})();
