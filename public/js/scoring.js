/**
 * Official IELTS Academic Reading Scoring and Band Converter
 */

const IELTS_SCORING_TABLE = [
  { min: 39, band: 9.0, cefr: "C2 Expert" },
  { min: 37, band: 8.5, cefr: "C2 Very Good" },
  { min: 35, band: 8.0, cefr: "C1 Very Good" },
  { min: 33, band: 7.5, cefr: "C1 Good" },
  { min: 30, band: 7.0, cefr: "C1 Competent" },
  { min: 27, band: 6.5, cefr: "B2 Competent" },
  { min: 23, band: 6.0, cefr: "B2 Competent" },
  { min: 19, band: 5.5, cefr: "B2 Modest" },
  { min: 15, band: 5.0, cefr: "B1 Modest" },
  { min: 13, band: 4.5, cefr: "B1 Limited" },
  { min: 10, band: 4.0, cefr: "B1 Limited" },
  { min: 8,  band: 3.5, cefr: "A2 Extremely Limited" },
  { min: 6,  band: 3.0, cefr: "A2 Extremely Limited" },
  { min: 4,  band: 2.5, cefr: "A1 Intermittent" },
  { min: 0,  band: 2.0, cefr: "Non-User" }
];

function getIeltsBandScore(rawScore) {
  for (const entry of IELTS_SCORING_TABLE) {
    if (rawScore >= entry.min) {
      return entry;
    }
  }
  return { band: 1.0, cefr: "Non-User" };
}

function normalizeAnswer(val) {
  if (val === null || val === undefined) return "";
  return String(val).trim().toLowerCase();
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs < 10 ? '0' : ''}${secs}s`;
}

window.IeltsScoring = {
  getBandScore: getIeltsBandScore,
  normalizeAnswer,
  formatDuration
};

