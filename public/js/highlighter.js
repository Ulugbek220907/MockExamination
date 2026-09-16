/**
 * CD-IELTS Interactive Highlighting & Sticky Notes System
 * Implements the official British Council / IDP text selection tools.
 */

class CdHighlighter {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.toolbar = null;
    this.currentSelection = null;
    this.highlightCounter = 0;
    this.notes = {};

    this.initToolbar();
    this.bindEvents();
  }

  initToolbar() {
    this.toolbar = document.createElement("div");
    this.toolbar.className = "cd-highlight-toolbar";
    this.toolbar.style.display = "none";
    this.toolbar.innerHTML = `
      <button id="btn-do-highlight"><span>🖍</span> Highlight</button>
      <button id="btn-do-note"><span>📝</span> Note</button>
    `;
    document.body.appendChild(this.toolbar);

    this.toolbar.querySelector("#btn-do-highlight").addEventListener("click", (e) => {
      e.stopPropagation();
      this.applyHighlight();
    });

    this.toolbar.querySelector("#btn-do-note").addEventListener("click", (e) => {
      e.stopPropagation();
      this.applyNote();
    });
  }

  bindEvents() {
    document.addEventListener("selectionchange", () => {
      const sel = window.getSelection();
      if (!sel.isCollapsed && this.isInsideContainer(sel)) {
        this.currentSelection = sel.getRangeAt(0).cloneRange();
        this.showToolbar();
      } else {
        if (!this.isMouseOverToolbar) {
          this.hideToolbar();
        }
      }
    });

    // Remove highlight on right click
    document.addEventListener("contextmenu", (e) => {
      const hl = e.target.closest(".cd-highlight");
      if (hl) {
        e.preventDefault();
        this.removeHighlight(hl);
      }
    });

    // Track mouse on toolbar to avoid premature hiding
    this.toolbar.addEventListener("mouseenter", () => { this.isMouseOverToolbar = true; });
    this.toolbar.addEventListener("mouseleave", () => { this.isMouseOverToolbar = false; });
  }

  isInsideContainer(sel) {
    if (!sel.anchorNode || !this.container) return false;
    return this.container.contains(sel.anchorNode);
  }

  showToolbar() {
    if (!this.currentSelection) return;
    const rect = this.currentSelection.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return;

    this.toolbar.style.top = `${window.scrollY + rect.top - 36}px`;
    this.toolbar.style.left = `${window.scrollX + rect.left + rect.width / 2 - 60}px`;
    this.toolbar.style.display = "flex";
  }

  hideToolbar() {
    if (this.toolbar) {
      this.toolbar.style.display = "none";
    }
  }

  applyHighlight() {
    if (!this.currentSelection) return;
    const range = this.currentSelection;
    this.highlightCounter++;

    try {
      const span = document.createElement("span");
      span.className = "cd-highlight";
      span.dataset.highlightId = `hl-${this.highlightCounter}`;
      span.title = "Right click to remove highlight";

      span.appendChild(range.extractContents());
      range.insertNode(span);
      window.getSelection().removeAllRanges();
    } catch (err) {
      console.warn("Could not apply highlight to complex selection", err);
    }

    this.hideToolbar();
    this.currentSelection = null;
  }

  removeHighlight(spanElement) {
    const parent = spanElement.parentNode;
    while (spanElement.firstChild) {
      parent.insertBefore(spanElement.firstChild, spanElement);
    }
    parent.removeChild(spanElement);
  }

  applyNote() {
    if (!this.currentSelection) return;
    const rect = this.currentSelection.getBoundingClientRect();
    this.highlightCounter++;
    const noteId = `note-${this.highlightCounter}`;

    // Highlight text associated with note
    this.applyHighlight();

    // Create Note Card
    const noteCard = document.createElement("div");
    noteCard.className = "cd-note-card";
    noteCard.id = noteId;
    noteCard.style.top = `${window.scrollY + rect.bottom + 8}px`;
    noteCard.style.left = `${window.scrollX + rect.left}px`;

    noteCard.innerHTML = `
      <div class="cd-note-header">
        <span>CANDIDATE NOTE</span>
        <span class="cd-note-close" title="Close note">&times;</span>
      </div>
      <textarea placeholder="Type your observation here..."></textarea>
    `;

    document.body.appendChild(noteCard);
    const textarea = noteCard.querySelector("textarea");
    textarea.focus();

    noteCard.querySelector(".cd-note-close").addEventListener("click", () => {
      noteCard.remove();
    });

    this.hideToolbar();
  }

  clearAll() {
    // Clear all highlights
    if (this.container) {
      const highlights = this.container.querySelectorAll(".cd-highlight");
      highlights.forEach(h => this.removeHighlight(h));
    }
    // Remove all notes
    document.querySelectorAll(".cd-note-card").forEach(n => n.remove());
    this.hideToolbar();
  }
}

window.CdHighlighter = CdHighlighter;
