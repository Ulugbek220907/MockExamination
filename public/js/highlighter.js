/**
 * Text highlighting and notes, as in the computer-delivered test.
 *
 *  - Select text → menu: Highlight · Note (· Clear, if the selection touches highlights)
 *  - Click / tap / right-click a highlight → menu: Remove · Add/Edit note · Clear all
 *  - Keyboard: highlights are focusable; Enter opens the menu, Delete removes it
 *
 * Overlapping highlights are merged into one span, so a single "Remove"
 * always clears the text (no nested highlights left behind).
 */
(function () {
  "use strict";

  const BLOCKS = "p, li, td, th, .question-card, .task-prompt, .passage-subtitle, .passage-title, .box-title";
  const HL = "cd-highlight";

  class CdHighlighter {
    constructor(containerId) {
      this.container = document.getElementById(containerId);
      this.abort = new AbortController();
      this.range = null;
      this.target = null; // highlight span the menu is acting on
      this.mode = null; // "selection" | "highlight"
      this.overMenu = false;
      this.counter = 0;
      this.buildMenu();
      this.bind();
    }

    on(target, type, fn, options = {}) {
      target.addEventListener(type, fn, { ...options, signal: this.abort.signal });
    }

    /* Menu ----------------------------------------------------------------- */
    buildMenu() {
      this.menu = document.createElement("div");
      this.menu.className = "cd-highlight-toolbar";
      this.menu.setAttribute("role", "toolbar");
      this.menu.hidden = true;
      document.body.appendChild(this.menu);
      this.on(this.menu, "mousedown", (e) => e.preventDefault()); // keep the text selection alive
      this.on(this.menu, "click", (e) => {
        const btn = e.target.closest("button");
        if (btn) this.run(btn.dataset.act);
      });
      this.on(this.menu, "mouseenter", () => { this.overMenu = true; });
      this.on(this.menu, "mouseleave", () => { this.overMenu = false; });
    }

    showMenu(mode, rect, buttons) {
      if (!rect || (!rect.width && !rect.height)) return;
      this.mode = mode;
      this.menu.innerHTML = buttons.map(([act, label]) => `<button type="button" data-act="${act}">${label}</button>`).join("");
      this.menu.hidden = false;
      const width = this.menu.offsetWidth || 220;
      const above = rect.top - 44;
      this.menu.style.top = `${above >= 8 ? above : Math.min(window.innerHeight - 48, rect.bottom + 8)}px`;
      this.menu.style.left = `${Math.min(window.innerWidth - width - 8, Math.max(8, rect.left + rect.width / 2 - width / 2))}px`;
    }

    hideMenu() {
      this.menu.hidden = true;
      this.mode = null;
      this.target = null;
      this.overMenu = false;
    }

    showSelectionMenu() {
      const buttons = [["highlight", "Highlight"], ["note", "Note"]];
      if (this.highlightsIn(this.range).length) buttons.push(["clear-selection", "Clear"]);
      this.showMenu("selection", this.range.getBoundingClientRect(), buttons);
    }

    showHighlightMenu(span) {
      this.target = span;
      this.range = null;
      const buttons = [
        ["remove", "Remove highlight"],
        ["note", span.dataset.note ? "Edit note" : "Add note"],
      ];
      if (this.container.querySelectorAll(`.${HL}`).length > 1) buttons.push(["clear-all", "Clear all"]);
      this.showMenu("highlight", span.getBoundingClientRect(), buttons);
    }

    run(act) {
      const target = this.target;
      const range = this.range;
      this.hideMenu();
      if (act === "highlight") this.wrap(range);
      else if (act === "note") this.openNote(target || this.wrap(range));
      else if (act === "remove" && target) this.remove(target);
      else if (act === "clear-selection" && range) {
        this.highlightsIn(range).forEach((h) => this.remove(h));
        window.getSelection().removeAllRanges();
      } else if (act === "clear-all") this.clearAll();
    }

    /* Events --------------------------------------------------------------- */
    selectionInside() {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !sel.rangeCount || !this.container) return null;
      const active = document.activeElement;
      if (active && ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName)) return null;
      const range = sel.getRangeAt(0);
      if (!this.container.contains(range.commonAncestorContainer)) return null;
      return range.cloneRange();
    }

    bind() {
      this.on(document, "selectionchange", () => {
        const range = this.selectionInside();
        if (range) {
          this.range = range;
          this.target = null;
          this.showSelectionMenu();
        } else if (this.mode === "selection" && !this.overMenu) {
          this.hideMenu();
        }
      });

      // Click or tap on a highlight opens its menu (unless the user is selecting text).
      this.on(this.container, "click", (e) => {
        const span = e.target.closest && e.target.closest(`.${HL}`);
        if (!span || !this.container.contains(span)) return;
        const sel = window.getSelection();
        if (sel && !sel.isCollapsed) return;
        this.showHighlightMenu(span);
      });

      // Right-click behaves like the official test: a menu instead of the browser's.
      this.on(document, "contextmenu", (e) => {
        if (!this.container || !this.container.contains(e.target)) return;
        const span = e.target.closest && e.target.closest(`.${HL}`);
        const range = this.selectionInside();
        if (span && !range) {
          e.preventDefault();
          this.showHighlightMenu(span);
        } else if (range) {
          e.preventDefault();
          this.range = range;
          this.showSelectionMenu();
        }
      });

      // Keyboard access for highlights.
      this.on(this.container, "keydown", (e) => {
        const span = e.target.classList && e.target.classList.contains(HL) ? e.target : null;
        if (!span) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this.showHighlightMenu(span);
        } else if (e.key === "Delete" || e.key === "Backspace") {
          e.preventDefault();
          this.remove(span);
        }
      });

      // Close the highlight menu when clicking elsewhere, pressing Escape, or scrolling.
      this.on(document, "pointerdown", (e) => {
        if (this.mode !== "highlight") return;
        if (this.menu.contains(e.target) || (e.target.closest && e.target.closest(`.${HL}`))) return;
        this.hideMenu();
      });
      this.on(document, "keydown", (e) => { if (e.key === "Escape" && !this.menu.hidden) this.hideMenu(); });
      this.on(this.container, "scroll", () => { if (!this.menu.hidden) this.hideMenu(); }, { capture: true });
      this.on(window, "resize", () => this.hideMenu());
    }

    /* Highlight operations ------------------------------------------------ */
    enclosingHighlight(node) {
      const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
      const hl = el && el.closest(`.${HL}`);
      return hl && this.container.contains(hl) ? hl : null;
    }

    highlightsIn(range) {
      if (!range) return [];
      const found = [...this.container.querySelectorAll(`.${HL}`)].filter((h) => range.intersectsNode(h));
      const around = this.enclosingHighlight(range.commonAncestorContainer);
      if (around && !found.includes(around)) found.push(around);
      return found;
    }

    /** Highlight a range; overlapping highlights are merged into one span. Returns the span or null. */
    wrap(range) {
      if (!range || range.collapsed) return null;
      range = range.cloneRange();
      // Grow the range to swallow any highlight it starts or ends inside, so nothing nests.
      const startHl = this.enclosingHighlight(range.startContainer);
      const endHl = this.enclosingHighlight(range.endContainer);
      if (startHl) range.setStartBefore(startHl);
      if (endHl) range.setEndAfter(endHl);

      const startEl = range.startContainer.nodeType === Node.ELEMENT_NODE ? range.startContainer : range.startContainer.parentElement;
      const endEl = range.endContainer.nodeType === Node.ELEMENT_NODE ? range.endContainer : range.endContainer.parentElement;
      const startBlock = startEl && startEl.closest(BLOCKS);
      const endBlock = endEl && endEl.closest(BLOCKS);
      if (!startBlock || startBlock !== endBlock || range.cloneContents().querySelector("input, select, textarea, button")) {
        U.toast("Highlight text within one paragraph at a time.", "warn");
        return null;
      }

      const notes = [];
      const span = document.createElement("span");
      span.className = HL;
      span.dataset.hl = String(++this.counter);
      span.tabIndex = 0;
      span.appendChild(range.extractContents());
      // Merge any highlights that were inside the selection (keep their notes).
      span.querySelectorAll(`.${HL}`).forEach((inner) => {
        if (inner.dataset.note) notes.push(inner.dataset.note);
        this.closeNoteFor(inner);
        this.unwrap(inner);
      });
      range.insertNode(span);
      if (notes.length) this.setNote(span, notes.join("\n"));
      this.setTitle(span);
      span.normalize();
      window.getSelection().removeAllRanges();
      return span;
    }

    remove(span) {
      if (!span || !span.parentNode) return;
      this.closeNoteFor(span);
      this.unwrap(span);
    }

    clearAll() {
      this.container.querySelectorAll(`.${HL}`).forEach((h) => this.remove(h));
    }

    unwrap(span) {
      const parent = span.parentNode;
      if (!parent) return;
      while (span.firstChild) parent.insertBefore(span.firstChild, span);
      parent.removeChild(span);
      parent.normalize();
    }

    /* Notes ---------------------------------------------------------------- */
    setTitle(span) {
      span.title = span.dataset.note ? `Note: ${span.dataset.note}` : "Click to remove or add a note";
    }

    setNote(span, text) {
      if (text) span.dataset.note = text;
      else delete span.dataset.note;
      span.classList.toggle("has-note", Boolean(text));
      this.setTitle(span);
    }

    closeNoteFor(span) {
      const card = document.querySelector(`.cd-note-card[data-for="${span.dataset.hl}"]`);
      if (card) card.remove();
    }

    closeNotes() {
      document.querySelectorAll(".cd-note-card").forEach((n) => n.remove());
    }

    openNote(span) {
      if (!span) return;
      this.closeNoteFor(span);
      const rect = span.getBoundingClientRect();
      const card = document.createElement("div");
      card.className = "cd-note-card";
      card.dataset.for = span.dataset.hl;
      card.style.top = `${Math.max(8, Math.min(window.innerHeight - 170, rect.bottom + 8))}px`;
      card.style.left = `${Math.min(window.innerWidth - 262, Math.max(8, rect.left))}px`;
      card.innerHTML = `
        <div class="cd-note-header"><span>Note</span>
          <button type="button" class="cd-note-close" aria-label="Close note">&times;</button></div>
        <textarea placeholder="Type your note…" aria-label="Note"></textarea>
        <div class="cd-note-actions"><button type="button" class="cd-note-delete">Delete note</button></div>`;
      document.body.appendChild(card);
      const ta = card.querySelector("textarea");
      ta.value = span.dataset.note || "";
      ta.focus();
      ta.addEventListener("input", () => this.setNote(span, ta.value.trim()));
      card.querySelector(".cd-note-close").addEventListener("click", () => card.remove());
      card.querySelector(".cd-note-delete").addEventListener("click", () => {
        this.setNote(span, "");
        card.remove();
      });
    }

    destroy() {
      this.abort.abort();
      this.menu.remove();
      this.closeNotes();
    }
  }

  window.CdHighlighter = CdHighlighter;
})();
