/**
 * Shared helpers: HTML escaping, light markdown, API calls, safe browser
 * storage, anonymous client id, modals and formatting.
 */
(function () {
  "use strict";

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  /** Escape, then allow **bold** and paragraph breaks (content authored by us). */
  function richText(value) {
    return escapeHtml(value)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n\n/g, "</p><p>")
      .replace(/\n/g, "<br>");
  }

  function paragraphs(value) {
    return `<p>${richText(value)}</p>`;
  }

  const inFlightGets = new Map();
  const apiCache = new Map();
  const API_CACHE_TTL = 60 * 1000;

  function isCacheable(path) {
    return path.startsWith("/api/tests") || path === "/api/config";
  }

  async function api(path, options = {}) {
    const isGet = !options.method || options.method.toUpperCase() === "GET";
    const isSimpleGet = isGet && !options.headers && !options.body;
    const forceFresh = Boolean(options.fresh || (options.headers && options.headers["Cache-Control"] === "no-cache"));

    if (isSimpleGet && !forceFresh) {
      if (isCacheable(path)) {
        const hit = apiCache.get(path);
        if (hit && Date.now() - hit.time < API_CACHE_TTL) {
          return hit.data;
        }
      }
      if (inFlightGets.has(path)) {
        return inFlightGets.get(path);
      }
    }
    const headers = { ...(options.headers || {}) };
    if (!isGet && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    const run = (async () => {
      try {
        const res = await fetch(path, {
          ...options,
          headers,
        });
        let data = null;
        try { data = await res.json(); } catch (e) { /* non-JSON error page */ }
        if (!res.ok) {
          const err = new Error((data && data.error) || `Request failed (${res.status})`);
          err.status = res.status;
          throw err;
        }
        if (isSimpleGet && isCacheable(path)) {
          if (apiCache.size > 50) apiCache.clear();
          apiCache.set(path, { time: Date.now(), data });
        }
        return data;
      } finally {
        if (isSimpleGet) inFlightGets.delete(path);
      }
    })();
    if (isSimpleGet) inFlightGets.set(path, run);
    return run;
  }

  // Browser storage can be unavailable (private mode, blocked site data) – never let it break the app.
  const store = {
    get(key, fallback = null) {
      try {
        const raw = window.localStorage.getItem(key);
        return raw === null ? fallback : JSON.parse(raw);
      } catch (e) { return fallback; }
    },
    set(key, value) {
      try { window.localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
    },
    remove(key) {
      try { window.localStorage.removeItem(key); } catch (e) { /* ignore */ }
    },
  };

  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  /** Anonymous id that links this browser's attempts together for the history list. */
  function clientId() {
    let id = store.get("mockexam:clientId");
    if (!id) {
      id = uuid();
      store.set("mockexam:clientId", id);
    }
    return id;
  }

  function formatDuration(seconds) {
    seconds = Math.max(0, Math.round(seconds || 0));
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s < 10 ? "0" : ""}${s}s`;
  }

  function formatClock(seconds) {
    seconds = Math.max(0, Math.round(seconds));
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m < 10 ? "0" : ""}${m}:${s < 10 ? "0" : ""}${s}`;
  }

  /** Dates and times are written the British way ("3 Oct, 14:05"). */
  const LOCALE = "en-GB";

  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleString(LOCALE, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }

  /** Thousands with a space, the way prices are written in Uzbekistan: 39 000. The spaces never break a line. */
  function number(n) {
    return String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0");
  }

  function money(n) {
    return `${number(n)}\u00a0${t("so'm")}`;
  }

  function countWords(text) {
    const m = String(text || "").match(/[A-Za-z0-9’'\-]+/g);
    return m ? m.length : 0;
  }

  /**
   * Show a modal. `buttons` = [{label, className, value}]. Resolves with the
   * clicked button's value (or null if closed). `onClose(value, root)` runs
   * before the modal is removed, so callers can read form fields inside it.
   * `onOpen(root, close)` lets content inside the body close the modal with a value.
   */
  function modal({ title, bodyHTML, buttons = [{ label: "OK", className: "btn-primary", value: true }], onClose, onOpen }) {
    return new Promise((resolve) => {
      const overlay = document.createElement("div");
      overlay.className = "modal-overlay";
      overlay.innerHTML = `
        <div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <div class="modal-header"><span id="modal-title">${escapeHtml(title)}</span>
            <button type="button" class="modal-close" aria-label="Close">&times;</button></div>
          <div class="modal-body">${bodyHTML}</div>
          <div class="modal-footer">${buttons.map((b, i) => `<button type="button" class="${b.className || "btn-secondary"}" data-i="${i}">${escapeHtml(b.label)}</button>`).join("")}</div>
        </div>`;
      const opener = document.activeElement; // focus goes back here when the dialog closes
      const close = (value) => {
        if (onClose) onClose(value, overlay);
        overlay.remove();
        document.removeEventListener("keydown", onKey);
        if (opener && opener.focus && document.contains(opener)) opener.focus({ preventScroll: true });
        resolve(value);
      };
      // Esc closes; Tab and Shift+Tab stay inside the dialog.
      const onKey = (e) => {
        if (e.key === "Escape") return close(null);
        if (e.key !== "Tab") return;
        const items = [...overlay.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select, [tabindex]:not([tabindex="-1"])')]
          .filter((el) => el.offsetParent !== null);
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (!overlay.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
        else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      };
      overlay.querySelector(".modal-close").addEventListener("click", () => close(null));
      overlay.querySelectorAll(".modal-footer button").forEach((btn) => {
        btn.addEventListener("click", () => close(buttons[Number(btn.dataset.i)].value));
      });
      document.addEventListener("keydown", onKey);
      document.body.appendChild(overlay);
      if (onOpen) onOpen(overlay, close);
      const primary = overlay.querySelector(".modal-footer button:last-child");
      if (primary) primary.focus();
    });
  }

  function loadingOverlay(title, text) {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
      <div class="loading-card" role="status" aria-live="polite">
        <div class="spinner" aria-hidden="true"></div>
        <div class="loading-title">${escapeHtml(title)}</div>
        <p>${escapeHtml(text)}</p>
      </div>`;
    document.body.appendChild(overlay);
    return () => overlay.remove();
  }

  /**
   * Report a funnel event (visit, free_test_started, cta_click) to our own server.
   * Anonymous: only the browser's client id goes with it. Never waits, never fails the page.
   */
  function track(name, data = {}) {
    try {
      fetch("/api/events", {
        method: "POST", keepalive: true, headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, clientId: clientId(), ...data }),
      }).catch(() => {});
    } catch (e) { /* ignore */ }
  }

  function toast(message, tone = "info") {
    const el = document.createElement("div");
    el.className = `toast toast-${tone}`;
    el.setAttribute("role", "status");
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 6000);
  }

  /** Hashed address of a script the page loads on demand (the server lists them in #asset-versions). */
  let assetMap = null;
  function assetUrl(path) {
    if (!assetMap) {
      try { assetMap = JSON.parse((document.getElementById("asset-versions") || {}).textContent || "{}"); } catch (e) { assetMap = {}; }
    }
    return assetMap[path] || path;
  }

  const scripts = {};
  /** Load a script once; scripts added this way run in the order they were requested. */
  function loadScript(path) {
    if (!scripts[path]) {
      scripts[path] = new Promise((resolve, reject) => {
        const el = document.createElement("script");
        el.src = assetUrl(path);
        el.async = false;
        el.onload = () => resolve();
        el.onerror = () => { delete scripts[path]; el.remove(); reject(new Error(`Could not load ${path}`)); };
        document.head.appendChild(el);
      });
    }
    return scripts[path];
  }

  const warmed = new Set();
  const supportsPrefetch = (() => {
    try {
      const l = document.createElement("link");
      return Boolean(l.relList && l.relList.supports && l.relList.supports("prefetch"));
    } catch (e) {
      return false;
    }
  })();

  /**
   * Warm an asset in browser cache without executing it (idle prefetch).
   * Uses <link rel="prefetch"> when supported, with low-priority fetch fallback,
   * so it primes the browser HTTP cache without blocking or using JS heap.
   */
  function warm(path) {
    if (scripts[path] || styles[path] || warmed.has(path)) return Promise.resolve();
    warmed.add(path);
    const url = assetUrl(path);

    if (supportsPrefetch) {
      return new Promise((resolve) => {
        const link = document.createElement("link");
        link.rel = "prefetch";
        link.as = path.endsWith(".css") ? "style" : "script";
        link.href = url;
        link.onload = () => resolve();
        link.onerror = () => resolve();
        setTimeout(resolve, 3000);
        document.head.appendChild(link);
      });
    }

    return fetch(url, { priority: "low" })
      .then((res) => (res.ok ? res.blob() : null))
      .catch(() => null);
  }

  /**
   * Download a script without running it, and fail if it cannot be had. A bundle is downloaded whole
   * before any of it runs, so one missing file never leaves the files that depend on it half-working.
   * (Unlike warm(), which is only a hint. A failed fetch leaves nothing behind, so trying again works.)
   */
  async function download(path) {
    if (scripts[path]) return;
    const res = await fetch(assetUrl(path));
    if (!res.ok) throw new Error(`Could not load ${path}`);
    await res.arrayBuffer(); // read to the end, so the whole file is cached for the script tag
  }

  const styles = {};
  /** Load a stylesheet once; resolves when it has applied, so nothing is shown unstyled. */
  function loadStyle(path) {
    if (!styles[path]) {
      styles[path] = new Promise((resolve, reject) => {
        const el = document.createElement("link");
        el.rel = "stylesheet";
        el.href = assetUrl(path);
        el.onload = () => resolve();
        el.onerror = () => { delete styles[path]; el.remove(); reject(new Error(`Could not load ${path}`)); };
        document.head.appendChild(el);
      });
    }
    return styles[path];
  }


  // What the home page, prices and the other site pages do not need. Each name loads
  // when a page first uses it; order matters (Speaking builds on the exam engine and Results).
  const BUNDLES = {
    exam: ["css/cd-ielts.css", "js/highlighter.js", "js/charts.js", "js/exam.js", "js/results.js", "js/speaking.js"],
    results: ["css/cd-ielts.css", "js/results.js"],
    progress: ["js/progress.js"],
  };

  const loadedBundles = new Set();
  const loadingBundles = new Map();

  /**
   * Load a bundle of styles and scripts on demand; resolves when they have all been applied or run.
   * Files download concurrently without duplicates; scripts then run in the listed order.
   */
  async function need(name) {
    if (loadedBundles.has(name)) return;
    if (loadingBundles.has(name)) return loadingBundles.get(name);
    const paths = BUNDLES[name];
    if (!paths) return;

    const loadPromise = (async () => {
      try {
        const scripts = paths.filter((p) => !p.endsWith(".css"));
        // Everything downloads at once; the scripts then run one after another, and only if all arrived.
        await Promise.all([
          ...paths.filter((p) => p.endsWith(".css")).map((p) => loadStyle(p)),
          ...scripts.map((p) => download(p)),
        ]);
        for (const p of scripts) await loadScript(p);
        loadedBundles.add(name);
      } catch (err) {
        err.loadFailed = true; // the toast below is the message; callers need not repeat it
        toast(t("Could not load this page. Check your connection and try again."), "warn");
        throw err;
      } finally {
        loadingBundles.delete(name);
      }
    })();

    loadingBundles.set(name, loadPromise);
    return loadPromise;
  }

  /** Warm bundle assets into browser cache during idle time. */
  function prefetch(name) {
    const paths = BUNDLES[name];
    if (!paths || loadedBundles.has(name) || loadingBundles.has(name)) return;
    paths.forEach((path) => warm(path));
  }

  window.U = {
    escapeHtml, richText, paragraphs, api, store, clientId, formatDuration, formatClock,
    formatDate, number, money, LOCALE, countWords, track, assetUrl, loadScript, loadStyle, modal, loadingOverlay, toast, need, prefetch, clearApiCache: () => apiCache.clear(),
  };
})();
