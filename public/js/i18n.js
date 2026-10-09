/**
 * Interface languages: English, Uzbek (Latin) and Russian.
 *
 * t("English text") returns the text in the chosen language. Short strings use
 * the English text as their key; long ones use a dotted key ("home.lead") with
 * the English version in EN. Missing translations fall back to English.
 * {name} placeholders are filled from the second argument.
 *
 * The exam screens and the instructions before a test stay in English, as in
 * the real computer-delivered test. Test content is always English.
 */
(function () {
  "use strict";

  const LANGS = {
    en: { label: "EN", name: "English", locale: "en-GB" },
    uz: { label: "UZ", name: "O‘zbekcha", locale: "uz-Latn-UZ" },
    ru: { label: "RU", name: "Русский", locale: "ru-RU" },
  };

  const EN = {};
  const UZ = {};
  const RU = {};
  const DICT = { en: EN, uz: UZ, ru: RU };

  function readStored() {
    try { return JSON.parse(window.localStorage.getItem("testday:lang")); } catch (e) { return null; }
  }

  function detect() {
    const fromUrl = new URLSearchParams(location.search).get("lang");
    if (fromUrl && LANGS[fromUrl]) return fromUrl;
    const stored = readStored();
    if (stored && LANGS[stored]) return stored;
    const prefs = (navigator.languages || [navigator.language || "en"]).map((l) => String(l).toLowerCase());
    for (const p of prefs) {
      if (p.startsWith("uz")) return "uz";
      if (p.startsWith("ru")) return "ru";
      if (p.startsWith("en")) return "en";
    }
    return "en";
  }

  let lang = detect();

  function t(key, vars) {
    let out = (DICT[lang] && DICT[lang][key]) || EN[key] || key;
    if (vars) out = out.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
    return out;
  }

  /** Russian needs three forms after a number; Uzbek and English need one or two. */
  function plural(n, forms) {
    const f = forms[lang] || forms.en;
    if (lang === "ru") {
      const a = Math.abs(n) % 100;
      const b = a % 10;
      const form = a > 10 && a < 20 ? f[2] : b > 1 && b < 5 ? f[1] : b === 1 ? f[0] : f[2];
      return form.replace("{n}", n);
    }
    if (lang === "uz") return f[0].replace("{n}", n);
    return (n === 1 ? f[0] : f[1]).replace("{n}", n);
  }

  function applyStatic(root = document) {
    root.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    root.querySelectorAll("[data-i18n-html]").forEach((el) => { el.innerHTML = t(el.dataset.i18nHtml); });
    root.querySelectorAll("[data-i18n-label]").forEach((el) => { el.setAttribute("aria-label", t(el.dataset.i18nLabel)); });
    root.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
  }

  function setLang(next) {
    if (!LANGS[next] || next === lang) return;
    lang = next;
    try { window.localStorage.setItem("testday:lang", JSON.stringify(next)); } catch (e) { /* ignore */ }
    document.documentElement.lang = next;
    applyStatic();
    document.dispatchEvent(new CustomEvent("langchange", { detail: { lang: next } }));
  }

  /** Thousands with a thin space, the way prices are written in Uzbekistan. */
  function number(n) {
    return String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  function money(n) {
    return `${number(n)} ${t("so'm")}`;
  }

  document.documentElement.lang = lang;
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-lang]");
    if (b) setLang(b.dataset.lang);
  });

  window.I18N = {
    t, plural, setLang, applyStatic, number, money, LANGS, DICT, EN, UZ, RU,
    lang: () => lang,
    locale: () => LANGS[lang].locale,
  };
  window.t = t;
})();
