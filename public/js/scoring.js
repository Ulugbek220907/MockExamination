/**
 * Client-side band display helpers. All marking happens on the server.
 */
(function () {
  "use strict";

  const DESCRIPTORS = [
    [9, "Expert user"],
    [8, "Very good user"],
    [7, "Good user"],
    [6, "Competent user"],
    [5, "Modest user"],
    [4, "Limited user"],
    [3, "Extremely limited user"],
    [2, "Intermittent user"],
    [0, "Non-user"],
  ];

  function describeBand(band) {
    if (band === null || band === undefined) return "";
    const whole = Math.floor(band);
    return (DESCRIPTORS.find(([min]) => whole >= min) || DESCRIPTORS[DESCRIPTORS.length - 1])[1];
  }

  function formatBand(band) {
    return band === null || band === undefined ? "–" : Number(band).toFixed(1);
  }

  window.IeltsScoring = { describeBand, formatBand };
})();
