/**
 * Results pages for reading and writing submissions.
 */
(function () {
  "use strict";

  const esc = (v) => U.escapeHtml(v);
  const S = window.IeltsScoring;

  function pct(correct, total) {
    return total ? Math.round((correct / total) * 100) : 0;
  }

  function header(kind, data, extra) {
    return `
      <div class="results-head">
        <div>
          <div class="eyebrow">${kind} results</div>
          <h1>${esc(data.title)}</h1>
          <p class="muted-text">${esc(data.candidateName)} · ${extra} · Time used: ${U.formatDuration(data.timeSpentSeconds)}</p>
        </div>
        <div class="results-actions">
          <button type="button" class="btn-secondary" data-action="retake">Try again</button>
          <a class="btn-primary" href="#/">All tests</a>
        </div>
      </div>`;
  }

  function bandCircle(band, label) {
    return `
      <div class="score-main-box">
        <div class="band-score-circle"><span class="band-val">${S.formatBand(band)}</span><span class="band-lbl">${esc(label)}</span></div>
        <div class="band-desc">${esc(S.describeBand(band))}</div>
      </div>`;
  }

  /* ================================================================ reading */
  function renderReading(data, root) {
    const passages = Object.entries(data.passageBreakdown || {});
    const types = Object.values(data.typeBreakdown || {}).sort((a, b) => pct(a.correct, a.total) - pct(b.correct, b.total));
    const unanswered = data.results.filter((r) => !r.candidateAnswer).length;
    const incorrect = data.results.filter((r) => !r.isCorrect && r.candidateAnswer).length;

    root.innerHTML = `
      <section class="results-page">
        ${header("Reading", data, data.mode === "practice" ? "Practice mode" : "Timed test")}

        <div class="score-banner-card">
          ${bandCircle(data.bandScore, "Estimated band")}
          <div class="score-details-grid">
            <div class="score-stat-box"><div class="score-stat-val">${data.rawScore} / ${data.totalQuestions}</div><div class="score-stat-lbl">Correct answers</div></div>
            <div class="score-stat-box"><div class="score-stat-val">${esc(data.cefrLevel)}</div><div class="score-stat-lbl">Approx. CEFR level</div></div>
            <div class="score-stat-box"><div class="score-stat-val">${U.formatDuration(data.timeSpentSeconds)}</div><div class="score-stat-lbl">Time used</div></div>
          </div>
        </div>
        <p class="score-note">The band is estimated from your raw score using a typical Academic Reading conversion table.
          Official tests adjust the conversion slightly for each version, so treat this as a guide.</p>

        <h2 class="section-title">By passage</h2>
        <div class="passage-breakdown-row">
          ${passages.map(([num, p]) => `
            <div class="passage-stat-card">
              <h3>Passage ${esc(num)}: ${esc(p.title)}</h3>
              <div class="stat-line"><span>${p.correct} of ${p.total} correct</span><strong>${pct(p.correct, p.total)}%</strong></div>
              <div class="passage-progress-bar"><div class="passage-progress-fill" style="width:${pct(p.correct, p.total)}%"></div></div>
            </div>`).join("")}
        </div>

        <h2 class="section-title">By question type</h2>
        <p class="muted-text section-sub">Weakest types first – focus your practice here.</p>
        <div class="type-table">
          ${types.map((t) => `
            <div class="type-row">
              <span class="type-name">${esc(t.label)}</span>
              <div class="passage-progress-bar"><div class="passage-progress-fill" style="width:${pct(t.correct, t.total)}%"></div></div>
              <span class="type-score">${t.correct}/${t.total}</span>
            </div>`).join("")}
        </div>

        <div class="review-filter-bar">
          <h2 class="section-title">Question review</h2>
          <div class="review-tabs" role="tablist">
            <button type="button" class="review-tab-btn active" data-filter="all">All (${data.results.length})</button>
            <button type="button" class="review-tab-btn" data-filter="correct">Correct (${data.rawScore})</button>
            <button type="button" class="review-tab-btn" data-filter="incorrect">Incorrect (${incorrect})</button>
            <button type="button" class="review-tab-btn" data-filter="unanswered">Unanswered (${unanswered})</button>
          </div>
        </div>
        <div class="review-list" id="review-list"></div>
      </section>`;

    const list = root.querySelector("#review-list");
    const renderList = (filter) => {
      const items = data.results.filter((r) =>
        filter === "correct" ? r.isCorrect
          : filter === "incorrect" ? !r.isCorrect && r.candidateAnswer
            : filter === "unanswered" ? !r.candidateAnswer
              : true);
      list.innerHTML = items.length ? items.map(reviewCard).join("") : `<p class="empty-note">No questions match this filter.</p>`;
    };
    root.querySelectorAll(".review-tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        root.querySelectorAll(".review-tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        renderList(btn.dataset.filter);
      });
    });
    renderList("all");
  }

  function reviewCard(r) {
    const status = r.isCorrect ? ["badge-correct", "Correct"] : r.candidateAnswer ? ["badge-incorrect", "Incorrect"] : ["badge-unanswered", "Unanswered"];
    return `
      <article class="review-card ${r.isCorrect ? "is-correct" : "is-incorrect"}">
        <div class="review-card-top">
          <div><span class="question-number-badge">Q${r.number}</span>
            <span class="review-meta">Passage ${r.passageNumber} · ${esc(r.typeLabel)}</span></div>
          <span class="review-status-badge ${status[0]}">${status[1]}</span>
        </div>
        ${r.prompt ? `<div class="review-prompt">${esc(r.prompt)}</div>` : ""}
        <div class="review-answers-box">
          <div><div class="review-ans-label">Your answer</div>
            <div class="review-ans-value ${r.isCorrect ? "ans-correct" : "ans-incorrect"}">${r.candidateAnswer ? esc(r.candidateAnswer) : "No answer"}</div></div>
          <div><div class="review-ans-label">Correct answer</div>
            <div class="review-ans-value ans-correct">${esc(r.correctAnswer)}</div></div>
        </div>
        ${r.explanation ? `<div class="review-explanation"><strong>Why${r.reference && r.reference !== "—" ? ` (${esc(r.reference)})` : ""}:</strong> ${esc(r.explanation)}</div>` : ""}
      </article>`;
  }

  /* ================================================================ writing */
  function statusNotice(data) {
    const messages = {
      not_configured: ["info", "AI examiner feedback is not switched on for this site yet.", "Use the automatic checks, your statistics and the model answers below to review your writing."],
      not_requested: ["info", "You chose not to request AI feedback.", "Use the automatic checks and model answers below to review your writing."],
      rate_limited: ["warn", "AI marking is not available right now.", data.assessmentMessage],
      too_short: ["warn", "Your responses were too short to be marked.", "Write complete answers that meet the minimum word count to get a band estimate."],
      error: ["warn", "The AI examiner could not mark this script.", data.assessmentMessage],
    };
    const m = messages[data.assessmentStatus];
    if (!m) return "";
    return `<div class="notice notice-${m[0]}"><strong>${esc(m[1])}</strong><span>${esc(m[2] || "")}</span></div>`;
  }

  function criteriaHTML(task) {
    return `
      <div class="criteria-grid">
        ${Object.values(task.criteria).map((c) => `
          <div class="criterion-card">
            <div class="criterion-head"><span>${esc(c.label)}</span><strong class="criterion-band">${c.band}</strong></div>
            <div class="band-meter" aria-hidden="true"><span style="width:${(c.band / 9) * 100}%"></span></div>
            <p>${esc(c.feedback)}</p>
          </div>`).join("")}
      </div>`;
  }

  function listBlock(title, items, cls) {
    if (!items || !items.length) return "";
    return `<div class="feedback-block ${cls}"><h4>${esc(title)}</h4><ul>${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul></div>`;
  }

  function correctionsHTML(corrections) {
    if (!corrections || !corrections.length) return "";
    return `
      <div class="feedback-block">
        <h4>Corrections</h4>
        <div class="table-scroll"><table class="corrections-table">
          <thead><tr><th scope="col">You wrote</th><th scope="col">Better</th><th scope="col">Why</th></tr></thead>
          <tbody>${corrections.map((c) => `
            <tr><td class="corr-orig">${esc(c.original)}</td><td class="corr-new">${esc(c.corrected)}</td><td>${esc(c.explanation)}</td></tr>`).join("")}
          </tbody>
        </table></div>
      </div>`;
  }

  function analysisHTML(a) {
    return `
      <div class="feedback-block">
        <h4>Automatic checks</h4>
        <ul class="check-list">
          ${a.checks.map((c) => `<li class="${c.ok ? "ok" : "bad"}"><span class="check-icon" aria-hidden="true">${c.ok ? "✓" : "!"}</span>
            <span class="sr-only">${c.ok ? "Passed:" : "Needs attention:"}</span> ${esc(c.text)}</li>`).join("")}
        </ul>
        <div class="stats-row">
          <div><strong>${a.wordCount}</strong><span>words</span></div>
          <div><strong>${a.paragraphs}</strong><span>paragraphs</span></div>
          <div><strong>${a.sentences}</strong><span>sentences</span></div>
          <div><strong>${a.avgSentenceLength}</strong><span>words per sentence</span></div>
          <div><strong>${a.lexicalVariety}%</strong><span>different words</span></div>
        </div>
        ${a.linkingDevices.length ? `<p class="small-text"><strong>Linking words you used:</strong> ${a.linkingDevices.map(esc).join(", ")}</p>` : ""}
        ${a.repeatedWords.length ? `<p class="small-text"><strong>Words you repeated often:</strong> ${a.repeatedWords.map((r) => `${esc(r.word)} (${r.count}×)`).join(", ")} – try synonyms or pronouns.</p>` : ""}
      </div>`;
  }

  function taskSection(task, assessed) {
    return `
      <section class="task-result" id="task-result-${task.taskNumber}">
        <div class="task-result-head">
          <h2 class="section-title">Task ${task.taskNumber}: ${esc(task.title)}</h2>
          ${assessed ? `<span class="task-band">Band ${S.formatBand(assessed.band)}</span>` : ""}
        </div>
        ${assessed ? `
          <p class="lead-text">${esc(assessed.summary)}</p>
          ${criteriaHTML(assessed)}
          <div class="feedback-columns">
            ${listBlock("What you did well", assessed.strengths, "good")}
            ${listBlock("How to improve", assessed.improvements, "improve")}
          </div>
          ${correctionsHTML(assessed.corrections)}` : ""}
        ${analysisHTML(task.analysis)}
        <details class="fold"><summary>Your response (${task.analysis.wordCount} words)</summary>
          <div class="essay-text">${task.response ? U.paragraphs(task.response) : "<p><em>No response.</em></p>"}</div></details>
        <details class="fold"><summary>The question</summary>
          <div class="task-prompt">${U.paragraphs(task.prompt)}</div>${TaskCharts.render(task.visual)}</details>
        <details class="fold" ${assessed ? "" : "open"}><summary>Model answer</summary>
          <div class="essay-text model-answer">${U.paragraphs(task.modelAnswer)}</div></details>
      </section>`;
  }

  function renderWriting(data, root) {
    const a = data.assessment;
    const t1 = a && a.tasks["1"];
    const t2 = a && a.tasks["2"];
    root.innerHTML = `
      <section class="results-page">
        ${header("Writing", data, "Academic Writing")}
        ${a ? `
          <div class="score-banner-card">
            ${bandCircle(a.overallBand, "Estimated band")}
            <div class="score-details-grid">
              <div class="score-stat-box"><div class="score-stat-val">${S.formatBand(t1.band)}</div><div class="score-stat-lbl">Task 1</div></div>
              <div class="score-stat-box"><div class="score-stat-val">${S.formatBand(t2.band)}</div><div class="score-stat-lbl">Task 2 (counts double)</div></div>
              <div class="score-stat-box"><div class="score-stat-val">${U.formatDuration(data.timeSpentSeconds)}</div><div class="score-stat-lbl">Time used</div></div>
            </div>
          </div>
          <p class="score-note">This band is an AI estimate using the four public Writing criteria. It is for practice only and is not an official IELTS score.</p>`
        : statusNotice(data)}
        <nav class="task-jump" aria-label="Tasks">
          <a href="#task-result-1" data-jump="1">Task 1</a><a href="#task-result-2" data-jump="2">Task 2</a>
        </nav>
        ${data.tasks.map((t) => taskSection(t, a && a.tasks[String(t.taskNumber)])).join("")}
      </section>`;

    // In-page jumps without touching the router's hash.
    root.querySelectorAll("[data-jump]").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const target = root.querySelector(`#task-result-${link.dataset.jump}`);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  window.Results = { renderReading, renderWriting };
})();
