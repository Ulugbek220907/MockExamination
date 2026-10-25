/**
 * Smooth, eased scrolling for the site pages, with Lenis (public/js/vendor/lenis.min.js): the page glides to a
 * stop instead of moving in steps, on mouse wheels and trackpads. Touch screens keep their native momentum.
 *
 * Off when the visitor asks for reduced motion. Never inside a dialog, a text box, or a test.
 */
(function () {
  "use strict";

  if (typeof Lenis === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const lenis = new Lenis({
    lerp: 0.1, // 0.1 is the usual feel; lower is floatier, higher is tighter
    autoRaf: true, // Lenis animates only when it is given frames; without this the wheel would do nothing
    smoothWheel: true,
    prevent: (node) => document.body.classList.contains("in-exam") || Boolean(node.closest(".modal-overlay, textarea, [data-lenis-prevent]")),
  });
  window.siteScroll = lenis;
})();
