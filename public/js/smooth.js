/**
 * Eased mouse-wheel scrolling for the site pages: the page glides to a stop instead of jumping in notches.
 *
 * Only a desktop mouse wheel is eased. Touch screens and trackpads already scroll with their own momentum, and
 * keyboard, scrollbar and find-in-page scrolling stay native. It does nothing when the visitor asks for
 * reduced motion, inside a dialog or a scrollable box, or during a test.
 */
(function () {
  "use strict";

  const mouse = window.matchMedia("(hover: hover) and (pointer: fine)");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (!mouse.matches || reduced.matches) return;

  const EASE = 0.12; // the share of the remaining distance covered each frame
  let target = window.scrollY;
  let frame = 0;

  const maxScroll = () => Math.max(0, document.documentElement.scrollHeight - window.innerHeight);

  function scrollableAncestor(el) {
    for (; el && el !== document.body; el = el.parentElement) {
      const overflowY = getComputedStyle(el).overflowY;
      if ((overflowY === "auto" || overflowY === "scroll") && el.scrollHeight > el.clientHeight) return true;
    }
    return false;
  }

  /** A mouse wheel sends whole notches (a hundred pixels or a few lines); a trackpad sends small, fine-grained steps. */
  const looksLikeWheel = (e) => e.deltaX === 0 && (e.deltaMode === 1 || (Math.abs(e.deltaY) >= 50 && Number.isInteger(e.deltaY)));

  function step() {
    const now = window.scrollY;
    const next = now + (target - now) * EASE;
    if (Math.abs(target - next) < 0.5) {
      window.scrollTo({ top: target, behavior: "instant" });
      frame = 0;
      return;
    }
    window.scrollTo({ top: next, behavior: "instant" });
    frame = requestAnimationFrame(step);
  }

  window.addEventListener("wheel", (e) => {
    if (e.ctrlKey || e.defaultPrevented || !looksLikeWheel(e)) return;
    if (document.body.classList.contains("in-exam") || document.querySelector(".modal-overlay")) return;
    if (scrollableAncestor(e.target)) return;
    e.preventDefault();
    if (!frame) target = window.scrollY; // start from where the page really is (a key press or the scrollbar may have moved it)
    const lines = e.deltaMode === 1 ? 40 : 1;
    target = Math.min(maxScroll(), Math.max(0, target + e.deltaY * lines));
    if (!frame) frame = requestAnimationFrame(step);
  }, { passive: false });

  // Anything else that moves the page takes over from the glide.
  const stop = () => { if (frame) { cancelAnimationFrame(frame); frame = 0; } target = window.scrollY; };
  window.addEventListener("keydown", stop, { passive: true });
  window.addEventListener("pointerdown", stop, { passive: true });
  window.addEventListener("hashchange", stop, { passive: true });
  window.addEventListener("resize", stop, { passive: true });
})();
