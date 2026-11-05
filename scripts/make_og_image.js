/**
 * Draws the images that stand for TestDay outside the site, from the mark and the ornament that
 * scripts/make_ornaments.py draws (public/img/logo-mark*.svg, public/img/orn/*.svg):
 *   public/img/og.png                 1200 x 630, shown when testday.uz is shared in Telegram, WhatsApp, Facebook or X
 *   public/img/logo-512.png            512 x 512, the logo in the search-engine data (index.html) and the app icon
 *   public/img/logo-192.png            192 x 192, the app icon
 *   public/img/logo-maskable-512.png   512 x 512, the app icon for phones that cut it into a circle or a squircle
 *   public/img/apple-touch-icon.png    180 x 180, the icon on an iPhone home screen (iOS rounds the corners itself)
 *   public/img/email-logo.png           96 x 96, the logo at the top of the emails
 *
 * Run after changing the brand colours, the mark or the wording:
 *   python scripts/make_ornaments.py
 *   npm i -D playwright   (or use a global install)
 *   node scripts/make_og_image.js
 */
const fs = require("fs");
const path = require("path");

let chromium;
try {
  ({ chromium } = require("playwright"));
} catch (e) {
  ({ chromium } = require(require("child_process").execSync("npm root -g").toString().trim() + "/playwright"));
}

const root = path.join(__dirname, "..");
const read = (...p) => fs.readFileSync(path.join(root, "public", ...p));
const font = read("fonts", "schibsted-grotesk-core.woff2").toString("base64");
const img = (name) => path.join(root, "public", "img", name);

// The brand (see DESIGN.md): a warm ground, one deep ink, and gold for the ornament on ink.
const C = { ground: "#e9e8e2", ink: "#0f1a30", lift: "#1d2a45", soft: "#aeb8cb", gold: "#e0a93b" };

/** The inside of an SVG file (without its <svg> tag), recoloured: the mark is drawn in navy. */
const inner = (file, colour) => read("img", file).toString().replace(/^<svg[^>]*>/, "").replace(/<\/svg>\s*$/, "").replaceAll(C.ink, colour);
const mark = (colour) => inner("logo-mark.svg", colour);
/** A band as a CSS mask: any colour, repeated sideways, as tall as its box. */
const band = (name, colour, extra) => {
  const uri = `url('data:image/svg+xml;base64,${read("img", "orn", `${name}.svg`).toString("base64")}')`; // single quotes: it sits inside a style="" attribute
  return `<div style="background:${colour};-webkit-mask:${uri} repeat-x center/auto 100%;mask:${uri} repeat-x center/auto 100%;${extra}"></div>`;
};

const fontFace = `@font-face { font-family: "Schibsted Grotesk"; src: url("data:font/woff2;base64,${font}") format("woff2"); font-weight: 400 700; }
  html, body { margin: 0; } svg { display: block; }`;

// The share picture: ink and gold, like the footer of the site.
const og = `<!doctype html><html><head><style>${fontFace}
  body { width: 1200px; height: 630px; overflow: hidden; background: ${C.ink}; position: relative; font-family: "Schibsted Grotesk"; }
  .abs { position: absolute; }
</style></head><body>
  <svg class="abs" style="left:640px;top:-70px" width="760" height="760" viewBox="-1.12 -1.12 2.24 2.24" aria-hidden="true">${mark(C.lift)}</svg>
  ${band("girih", C.gold, "position:absolute;left:0;right:0;top:26px;height:30px")}
  <svg class="abs" style="left:72px;top:96px" width="68" height="68" viewBox="-1.12 -1.12 2.24 2.24">${mark(C.gold)}</svg>
  <div class="abs" style="left:156px;top:100px;font-size:44px;font-weight:650;letter-spacing:-0.9px;color:${C.ground};line-height:60px">TestDay</div>
  <div class="abs" style="left:66px;top:196px;font-size:140px;font-weight:600;letter-spacing:-5.2px;line-height:126px;color:${C.ground};white-space:nowrap">IELTS practice<br>like test day</div>
  <div class="abs" style="left:72px;top:482px;font-size:28px;font-weight:500;color:${C.soft};letter-spacing:0.1px">Listening&nbsp;&nbsp;·&nbsp;&nbsp;Reading&nbsp;&nbsp;·&nbsp;&nbsp;Writing&nbsp;&nbsp;·&nbsp;&nbsp;Speaking</div>
  <div class="abs" style="right:72px;top:482px;font-size:28px;font-weight:500;color:${C.gold}">testday.uz</div>
  ${band("islimi", C.gold, "position:absolute;left:0;right:0;bottom:6px;height:84px;opacity:0.95")}
</body></html>`;

// The app icon: the gold mark on a navy tile (rounded for the icon that is shown as it is).
const tile = (size, { round, scale }) => `<!doctype html><html><head><style>html, body { margin: 0; background: transparent; } svg { display: block; }</style></head><body>
<svg width="${size}" height="${size}" viewBox="-1.3 -1.3 2.6 2.6" xmlns="http://www.w3.org/2000/svg">
  <rect x="-1.3" y="-1.3" width="2.6" height="2.6" ${round ? 'rx="0.52"' : ""} fill="${C.ink}"/>
  <g transform="scale(${scale})">${mark(C.gold)}</g>
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
  await draw(browser, tile(512, { round: true, scale: 0.96 }), 512, 512, img("logo-512.png"), true);
  await draw(browser, tile(192, { round: true, scale: 0.96 }), 192, 192, img("logo-192.png"), true);
  await draw(browser, tile(180, { round: false, scale: 0.9 }), 180, 180, img("apple-touch-icon.png"));
  // Maskable: everything that matters stays inside the central 80 % circle, so the mark is smaller.
  await draw(browser, tile(512, { round: false, scale: 0.7 }), 512, 512, img("logo-maskable-512.png"));
  await draw(browser, tile(96, { round: true, scale: 0.96 }), 96, 96, img("email-logo.png"), true);
  await browser.close();
})();
