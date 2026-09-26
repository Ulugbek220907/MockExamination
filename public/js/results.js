/**
 * Results pages for reading, listening and writing submissions.
 * Listening results include the transcript, with every answer location
 * highlighted and a player to hear any line again.
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

  /* ================================================ reading and listening */
  function scoreBanner(data) {
    return `
      <div class="score-banner-card">
        ${bandCircle(data.bandScore, "Estimated band")}
        <div class="score-details-grid">
          <div class="score-stat-box"><div class="score-stat-val">${data.rawScore} / ${data.totalQuestions}</div><div class="score-stat-lbl">Correct answers</div></div>
          <div class="score-stat-box"><div class="score-stat-val">${esc(data.cefrLevel)}</div><div class="score-stat-lbl">Approx. CEFR level</div></div>
          <div class="score-stat-box"><div class="score-stat-val">${U.formatDuration(data.timeSpentSeconds)}</div><div class="score-stat-lbl">Time used</div></div>
        </div>
      </div>`;
  }

  function breakdownHTML(title, entries, label) {
    return `
      <h2 class="section-title">${esc(title)}</h2>
      <div class="passage-breakdown-row">
        ${entries.map(([num, p]) => `
          <div class="passage-stat-card">
            <h3>${esc(label)} ${esc(num)}: ${esc(p.title)}</h3>
            <div class="stat-line"><span>${p.correct} of ${p.total} correct</span><strong>${pct(p.correct, p.total)}%</strong></div>
            <div class="passage-progress-bar"><div class="passage-progress-fill" style="width:${pct(p.correct, p.total)}%"></div></div>
          </div>`).join("")}
      </div>`;
  }

  function typesHTML(data) {
    const types = Object.values(data.typeBreakdown || {}).sort((a, b) => pct(a.correct, a.total) - pct(b.correct, b.total));
    return `
      <h2 class="section-title">By question type</h2>
      <p class="muted-text section-sub">Weakest types first – focus your practice here.</p>
      <div class="type-table">
        ${types.map((t) => `
          <div class="type-row">
            <span class="type-name">${esc(t.label)}</span>
            <div class="passage-progress-bar"><div class="passage-progress-fill" style="width:${pct(t.correct, t.total)}%"></div></div>
            <span class="type-score">${t.correct}/${t.total}</span>
          </div>`).join("")}
      </div>`;
  }

  function reviewHTML(data) {
    const unanswered = data.results.filter((r) => !r.candidateAnswer).length;
    const incorrect = data.results.filter((r) => !r.isCorrect && r.candidateAnswer).length;
    return `
      <div class="review-filter-bar">
        <h2 class="section-title">Question review</h2>
        <div class="review-tabs" role="tablist">
          <button type="button" class="review-tab-btn active" data-filter="all">All (${data.results.length})</button>
          <button type="button" class="review-tab-btn" data-filter="correct">Correct (${data.rawScore})</button>
          <button type="button" class="review-tab-btn" data-filter="incorrect">Incorrect (${incorrect})</button>
          <button type="button" class="review-tab-btn" data-filter="unanswered">Unanswered (${unanswered})</button>
        </div>
      </div>
      <div class="review-list" id="review-list"></div>`;
  }

  function bindReview(scope, data, cardFn) {
    const list = scope.querySelector("#review-list");
    const tabs = scope.querySelectorAll(".review-filter-bar .review-tab-btn");
    const renderList = (filter) => {
      const items = data.results.filter((r) =>
        filter === "correct" ? r.isCorrect
          : filter === "incorrect" ? !r.isCorrect && r.candidateAnswer
            : filter === "unanswered" ? !r.candidateAnswer
              : true);
      list.innerHTML = items.length ? items.map(cardFn).join("") : `<p class="empty-note">No questions match this filter.</p>`;
    };
    tabs.forEach((btn) => {
      btn.addEventListener("click", () => {
        tabs.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        renderList(btn.dataset.filter);
      });
    });
    renderList("all");
  }

  function reviewCard(r, section, actions = "") {
    const status = r.isCorrect ? ["badge-correct", "Correct"] : r.candidateAnswer ? ["badge-incorrect", "Incorrect"] : ["badge-unanswered", "Unanswered"];
    return `
      <article class="review-card ${r.isCorrect ? "is-correct" : "is-incorrect"}">
        <div class="review-card-top">
          <div><span class="question-number-badge">Q${r.number}</span>
            <span class="review-meta">${esc(section)} · ${esc(r.typeLabel)}</span></div>
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
        ${actions}
      </article>`;
  }

  function renderReading(data, root) {
    root.innerHTML = `
      <section class="results-page">
        ${header("Reading", data, data.mode === "practice" ? "Practice mode" : "Timed test")}
        ${scoreBanner(data)}
        <p class="score-note">The band is estimated from your raw score using a typical Academic Reading conversion table.
          Official tests adjust the conversion slightly for each version, so treat this as a guide.</p>
        ${breakdownHTML("By passage", Object.entries(data.passageBreakdown || {}), "Passage")}
        ${typesHTML(data)}
        ${reviewHTML(data)}
      </section>`;
    bindReview(root, data, (r) => reviewCard(r, `Passage ${r.passageNumber}`));
  }

  /* -------------------------------------------------------------- listening */
  const PLAY_ICON = `<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>`;

  /** Transcript line text with the answer locations wrapped in <mark>, coloured by the candidate's result. */
  function markText(text, marks, byNumber) {
    let out = "";
    let pos = 0;
    (marks || []).forEach((m) => {
      if (m.start < pos) return;
      const r = byNumber[m.q];
      const cls = !r ? "" : r.isCorrect ? "is-correct" : r.candidateAnswer ? "is-incorrect" : "is-unanswered";
      out += esc(text.slice(pos, m.start));
      out += `<mark class="t-answer ${cls}" id="t-q-${m.q}"><span class="t-qnum">${m.q}</span>${esc(text.slice(m.start, m.end))}</mark>`;
      pos = m.end;
    });
    return out + esc(text.slice(pos));
  }

  function renderListening(data, root) {
    const transcript = data.transcript || [];
    const byNumber = {};
    data.results.forEach((r) => { byNumber[r.number] = r; });
    const partIndex = (partNumber) => transcript.findIndex((p) => p.partNumber === partNumber);

    root.innerHTML = `
      <section class="results-page listening-results">
        ${header("Listening", data, data.mode === "practice" ? "Practice mode" : "Timed test")}
        ${scoreBanner(data)}
        <p class="score-note">The band is estimated from your raw score using a typical Listening conversion table.
          Official tests adjust the conversion slightly for each version, so treat this as a guide.</p>
        ${breakdownHTML("By part", Object.entries(data.partBreakdown || {}), "Part")}
        ${typesHTML(data)}
        ${reviewHTML(data)}
        <section class="transcript-section" id="transcript-section" aria-labelledby="transcript-title">
          <h2 class="section-title" id="transcript-title">Transcript</h2>
          <p class="muted-text section-sub">The place where each answer is heard is highlighted. Press
            <span class="inline-icon">${PLAY_ICON}</span> to listen again from any line.</p>
          <div class="transcript-tabs" role="tablist" aria-label="Parts of the recording">
            ${transcript.map((p, i) => `<button type="button" class="review-tab-btn ${i === 0 ? "active" : ""}" role="tab"
              aria-selected="${i === 0}" data-tpart="${i}">Part ${p.partNumber}</button>`).join("")}
          </div>
          <div class="transcript" id="transcript"></div>
        </section>
        <div class="replay-bar" id="replay-bar" hidden>
          <span class="replay-text" id="replay-text" aria-live="polite"></span>
          <button type="button" class="btn-secondary btn-sm" id="replay-toggle">Pause</button>
          <button type="button" class="btn-secondary btn-sm" id="replay-stop">Stop</button>
          <audio id="replay-audio" preload="metadata"></audio>
        </div>
      </section>`;

    const page = root.querySelector(".listening-results");
    const tEl = page.querySelector("#transcript");
    const audio = page.querySelector("#replay-audio");
    const bar = page.querySelector("#replay-bar");
    let shownPart = 0;
    let playing = { part: -1, stopAt: null };
    let stopped = true;
    let litLine = null;

    const renderTranscript = (pi) => {
      shownPart = pi;
      litLine = null;
      const part = transcript[pi];
      page.querySelectorAll("[data-tpart]").forEach((b) => {
        const on = Number(b.dataset.tpart) === pi;
        b.classList.toggle("active", on);
        b.setAttribute("aria-selected", String(on));
      });
      tEl.innerHTML = !part ? "" : `
        <h3 class="t-title">Part ${part.partNumber}${part.title ? `: ${esc(part.title)}` : ""}</h3>
        ${part.context ? `<p class="t-context">${esc(part.context)}</p>` : ""}
        ${part.lines.map((l) => `
          <div class="t-line ${l.narrator ? "is-narrator" : ""}" data-start="${l.start}" data-end="${l.end}">
            <button type="button" class="t-play" data-play="${pi}" data-at="${l.start}" aria-label="Listen from here" title="Listen from here">${PLAY_ICON}</button>
            <div class="t-body"><span class="t-speaker">${esc(l.speaker)}</span>
              <span class="t-text">${markText(l.text, l.marks, byNumber)}</span></div>
          </div>`).join("")}`;
    };

    const updateBar = () => {
      const part = transcript[playing.part];
      bar.hidden = stopped || !part;
      if (bar.hidden) return;
      page.querySelector("#replay-text").textContent = `Part ${part.partNumber} · ${U.formatClock(audio.currentTime || 0)}`;
      page.querySelector("#replay-toggle").textContent = audio.paused ? "Play" : "Pause";
    };

    const play = (pi, start, stopAt = null) => {
      const part = transcript[pi];
      if (!part || !part.audio) return;
      if (playing.part !== pi) {
        audio.src = part.audio.src;
      }
      playing = { part: pi, stopAt };
      stopped = false;
      const seek = () => { audio.currentTime = Math.max(0, start); };
      if (audio.readyState >= 1) seek();
      else audio.addEventListener("loadedmetadata", seek, { once: true });
      audio.play().catch((err) => {
        if (err && err.name === "NotAllowedError") U.toast("Your browser blocked the sound. Check that this tab is not muted.", "warn");
      });
      updateBar();
    };

    audio.addEventListener("timeupdate", () => {
      const t = audio.currentTime;
      if (playing.stopAt !== null && t >= playing.stopAt) {
        audio.pause();
        playing.stopAt = null;
      }
      updateBar();
      if (playing.part !== shownPart) return;
      const line = [...tEl.querySelectorAll(".t-line")].find((el) => t >= Number(el.dataset.start) && t < Number(el.dataset.end) + 0.5);
      if (line !== litLine) {
        if (litLine) litLine.classList.remove("is-playing");
        if (line) line.classList.add("is-playing");
        litLine = line || null;
      }
    });
    ["play", "pause", "ended"].forEach((ev) => audio.addEventListener(ev, updateBar));

    page.addEventListener("click", (e) => {
      const listen = e.target.closest("[data-listen]");
      if (listen) {
        const r = byNumber[listen.dataset.listen];
        if (r && r.cue) play(partIndex(r.partNumber), r.cue.start - 1.5, r.cue.end + 0.8);
        return;
      }
      const show = e.target.closest("[data-show]");
      if (show) {
        const r = byNumber[show.dataset.show];
        if (!r) return;
        renderTranscript(partIndex(r.partNumber));
        const mark = tEl.querySelector(`#t-q-${r.number}`);
        if (mark) {
          mark.scrollIntoView({ behavior: "smooth", block: "center" });
          mark.classList.add("flash");
          setTimeout(() => mark.classList.remove("flash"), 2200);
        }
        return;
      }
      const line = e.target.closest("[data-play]");
      if (line) return play(Number(line.dataset.play), Number(line.dataset.at) - 0.2);
      const tab = e.target.closest("[data-tpart]");
      if (tab) return renderTranscript(Number(tab.dataset.tpart));
      if (e.target.closest("#replay-toggle")) {
        if (audio.paused) audio.play().catch(() => {});
        else audio.pause();
        return;
      }
      if (e.target.closest("#replay-stop")) {
        stopped = true;
        audio.pause();
        bar.hidden = true;
        if (litLine) litLine.classList.remove("is-playing");
        litLine = null;
      }
    });

    bindReview(page, data, (r) => reviewCard(r, `Part ${r.partNumber}`, r.cue ? `
      <div class="review-actions">
        <button type="button" class="btn-link" data-listen="${r.number}">${PLAY_ICON} Listen again</button>
        <button type="button" class="btn-link" data-show="${r.number}">Show in transcript</button>
      </div>` : ""));
    renderTranscript(0);
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

  window.Results = { renderReading, renderListening, renderWriting };
})();
