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

  async function api(path, options = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    let data = null;
    try { data = await res.json(); } catch (e) { /* non-JSON error page */ }
    if (!res.ok) {
      const err = new Error((data && data.error) || `Request failed (${res.status})`);
      err.status = res.status;
      throw err;
    }
    return data;
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
    // The exam screens stay in English; the site follows the chosen language.
    const inExam = document.body && (document.body.classList.contains("in-exam")
      || document.getElementById("verification-view")?.classList.contains("active"));
    const vars = { m, s: `${s < 10 ? "0" : ""}${s}` };
    return window.I18N && !inExam ? I18N.t("{m}m {s}s", vars) : `${vars.m}m ${vars.s}s`;
  }

  function formatClock(seconds) {
    seconds = Math.max(0, Math.round(seconds));
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m < 10 ? "0" : ""}${m}:${s < 10 ? "0" : ""}${s}`;
  }

  function formatDate(iso, locale) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const loc = locale || (window.I18N ? I18N.locale() : undefined);
    try {
      return d.toLocaleString(loc, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    } catch (e) {
      return d.toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    }
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
      const close = (value) => {
        if (onClose) onClose(value, overlay);
        overlay.remove();
        document.removeEventListener("keydown", onKey);
        resolve(value);
      };
      const onKey = (e) => { if (e.key === "Escape") close(null); };
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

  function toast(message, tone = "info") {
    const el = document.createElement("div");
    el.className = `toast toast-${tone}`;
    el.setAttribute("role", "status");
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 6000);
  }

  // Scripts the home page does not need. Speaking builds on the exam engine, so order matters.
  const BUNDLES = {
    exam: ["js/highlighter.js", "js/charts.js", "js/exam.js", "js/speaking.js"],
  };

  /** Load a bundle of scripts on demand; resolves when they have run. */
  async function need(name) {
    try {
      await Promise.all(BUNDLES[name].map((path) => I18N.loadScript(path)));
    } catch (err) {
      toast(I18N.t("Could not load this page. Check your connection and try again."), "warn");
      throw err;
    }
  }

  window.U = {
    escapeHtml, richText, paragraphs, api, store, clientId, formatDuration, formatClock,
    formatDate, countWords, modal, loadingOverlay, toast, need,
  };
})();
