/**
 * Text highlighting and notes, as in the computer-delivered test.
 * Select text inside the container → "Highlight" or "Note".
 * Right-click (or long-press) a highlight to remove it.
 */
(function () {
  "use strict";

  const BLOCKS = "p, li, td, th, .question-card, .task-prompt, .passage-subtitle, .passage-title";

  class CdHighlighter {
    constructor(containerId) {
      this.container = document.getElementById(containerId);
      this.abort = new AbortController();
      this.range = null;
      this.overToolbar = false;
      this.counter = 0;
      this.buildToolbar();
      this.bind();
    }

    on(target, type, fn) {
      target.addEventListener(type, fn, { signal: this.abort.signal });
    }

    buildToolbar() {
      this.toolbar = document.createElement("div");
      this.toolbar.className = "cd-highlight-toolbar";
      this.toolbar.hidden = true;
      this.toolbar.innerHTML = `
        <button type="button" data-act="highlight">Highlight</button>
        <button type="button" data-act="note">Note</button>`;
      document.body.appendChild(this.toolbar);
      this.on(this.toolbar, "mousedown", (e) => e.preventDefault()); // keep the selection alive
      this.on(this.toolbar, "click", (e) => {
        const act = e.target.closest("button") && e.target.closest("button").dataset.act;
        if (act === "highlight") this.highlight();
        if (act === "note") this.note();
      });
      this.on(this.toolbar, "mouseenter", () => { this.overToolbar = true; });
      this.on(this.toolbar, "mouseleave", () => { this.overToolbar = false; });
    }

    bind() {
      this.on(document, "selectionchange", () => {
        const sel = window.getSelection();
        const active = document.activeElement;
        const typing = active && ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName);
        if (sel && !sel.isCollapsed && sel.rangeCount && !typing && this.container && this.container.contains(sel.anchorNode)) {
          this.range = sel.getRangeAt(0).cloneRange();
          this.showToolbar();
        } else if (!this.overToolbar) {
          this.hideToolbar();
        }
      });
      this.on(document, "contextmenu", (e) => {
        const hl = e.target.closest && e.target.closest(".cd-highlight");
        if (hl && this.container.contains(hl)) {
          e.preventDefault();
          this.unwrap(hl);
        }
      });
      this.on(window, "resize", () => this.hideToolbar());
    }

    showToolbar() {
      const rect = this.range.getBoundingClientRect();
      if (!rect.width && !rect.height) return;
      this.toolbar.hidden = false;
      const top = Math.max(8, rect.top - 42);
      const left = Math.min(window.innerWidth - 180, Math.max(8, rect.left + rect.width / 2 - 80));
      this.toolbar.style.top = `${top}px`;
      this.toolbar.style.left = `${left}px`;
    }

    hideToolbar() {
      this.toolbar.hidden = true;
    }

    /** Wrap the current selection in a highlight span. Returns the span, or null. */
    wrapSelection() {
      const range = this.range;
      if (!range) return null;
      const startBlock = range.startContainer.parentElement && range.startContainer.parentElement.closest(BLOCKS);
      const endBlock = range.endContainer.parentElement && range.endContainer.parentElement.closest(BLOCKS);
      if (!startBlock || startBlock !== endBlock || range.cloneContents().querySelector("input, select, textarea, button")) {
        U.toast("Highlight text within one paragraph at a time.", "warn");
        return null;
      }
      const span = document.createElement("span");
      span.className = "cd-highlight";
      span.dataset.hl = String(++this.counter);
      span.title = "Right-click to remove highlight";
      span.appendChild(range.extractContents());
      range.insertNode(span);
      window.getSelection().removeAllRanges();
      this.range = null;
      this.hideToolbar();
      return span;
    }

    highlight() {
      this.wrapSelection();
    }

    note() {
      const rect = this.range ? this.range.getBoundingClientRect() : null;
      const span = this.wrapSelection();
      if (!span || !rect) return;
      span.classList.add("has-note");
      const card = document.createElement("div");
      card.className = "cd-note-card";
      card.style.top = `${Math.min(window.innerHeight - 150, rect.bottom + 8)}px`;
      card.style.left = `${Math.min(window.innerWidth - 260, Math.max(8, rect.left))}px`;
      card.innerHTML = `
        <div class="cd-note-header"><span>Note</span>
          <button type="button" class="cd-note-close" aria-label="Close note">&times;</button></div>
        <textarea placeholder="Type your note…" aria-label="Note"></textarea>`;
      document.body.appendChild(card);
      const ta = card.querySelector("textarea");
      ta.focus();
      ta.addEventListener("input", () => {
        span.title = ta.value ? `Note: ${ta.value}` : "Right-click to remove highlight";
      });
      card.querySelector(".cd-note-close").addEventListener("click", () => card.remove());
    }

    unwrap(span) {
      const parent = span.parentNode;
      while (span.firstChild) parent.insertBefore(span.firstChild, span);
      parent.removeChild(span);
      parent.normalize();
    }

    destroy() {
      this.abort.abort();
      this.toolbar.remove();
      document.querySelectorAll(".cd-note-card").forEach((n) => n.remove());
    }
  }

  window.CdHighlighter = CdHighlighter;
})();
