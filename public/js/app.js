/**
 * IELTS Mock Exam Application Controller
 * Manages view routing, test selection, verification screen, and results presentation.
 */

class MockExamApp {
  constructor() {
    this.currentView = "portal";
    this.availableTests = [];
    this.modules = {};
    this.selectedTestMeta = null;
    this.selectedTestData = null;
    this.examInstance = null;
    this.candidateName = "Candidate";
    this.candidateNumber = "108429";

    this.init();
  }

  async init() {
    this.bindGlobalEvents();
    await this.loadTestsList();
    this.showView("portal");
  }

  bindGlobalEvents() {
    // Verification form submission
    const form = document.getElementById("verification-form");
    if (form) {
      form.onsubmit = (e) => {
        e.preventDefault();
        const nameInput = document.getElementById("candidate-name-input");
        const numInput = document.getElementById("candidate-number-input");
        if (nameInput && nameInput.value.trim()) this.candidateName = nameInput.value.trim();
        if (numInput && numInput.value.trim()) this.candidateNumber = numInput.value.trim();
        this.launchExam();
      };
    }

    // Return to portal from verification
    const cancelVerifyBtn = document.getElementById("btn-cancel-verify");
    if (cancelVerifyBtn) {
      cancelVerifyBtn.onclick = () => this.showView("portal");
    }

    // Results screen actions
    const retakeBtn = document.getElementById("btn-retake-test");
    if (retakeBtn) {
      retakeBtn.onclick = () => this.prepareExam(this.selectedTestMeta);
    }

    const backDashboardBtn = document.getElementById("btn-back-dashboard");
    if (backDashboardBtn) {
      backDashboardBtn.onclick = () => this.showView("portal");
    }

    // Non-active module clicks (Listening, Writing, Speaking)
    document.querySelectorAll(".module-tab-btn.disabled").forEach(btn => {
      btn.onclick = () => {
        const modName = btn.dataset.module;
        alert(`${modName} module is under development and will be available soon! For now, please practice with the full Reading module tests.`);
      };
    });
  }

  async loadTestsList() {
    try {
      const res = await fetch("/api/tests");
      const data = await res.json();
      this.availableTests = data.tests || [];
      this.modules = data.modules || {};
      this.renderBooksGrid();
    } catch (err) {
      console.warn("Failed to load /api/tests from backend, using fallback data", err);
    }
  }

  renderBooksGrid() {
    const grid = document.getElementById("books-grid");
    if (!grid) return;

    grid.innerHTML = this.availableTests.map(test => `
      <div class="test-card">
        <div>
          <div class="test-card-header">
            <span class="test-card-book">${test.bookShort}</span>
            <span class="test-badge-academic">Academic</span>
          </div>
          <h3 class="test-card-title">${test.title}</h3>
          <ul class="test-passages-list">
            ${test.passages.map(p => `
              <li class="test-passage-item">
                <span class="p-badge">Part ${p.number}</span>
                <span>${p.title}</span>
              </li>
            `).join("")}
          </ul>
        </div>
        <div>
          <div class="test-card-meta">
            <span>⏱ ${test.durationMinutes} Minutes</span>
            <span>📝 ${test.totalQuestions} Questions</span>
            <span>📊 Band 1.0–9.0</span>
          </div>
          <div class="test-card-actions">
            <button class="btn-start-exam" onclick="app.prepareExam('${test.id}', 'exam')">
              <span>🚀</span> Start Mock Exam
            </button>
            <button class="btn-practice-mode" onclick="app.prepareExam('${test.id}', 'practice')" title="Untimed practice mode">
              Practice Mode
            </button>
          </div>
        </div>
      </div>
    `).join("");
  }

  showView(viewName) {
    this.currentView = viewName;
    document.querySelectorAll(".view-container").forEach(el => el.classList.remove("active"));
    const activeEl = document.getElementById(`${viewName}-screen`);
    if (activeEl) {
      activeEl.classList.add("active");
      window.scrollTo(0, 0);
    }
  }

  async prepareExam(testId, mode = "exam") {
    this.selectedMode = mode;
    this.selectedTestMeta = this.availableTests.find(t => t.id === testId) || { id: testId };

    // Fetch full test details
    try {
      const res = await fetch(`/api/tests/${testId}`);
      if (!res.ok) throw new Error("Could not fetch test details");
      this.selectedTestData = await res.json();
    } catch (err) {
      console.error(err);
      alert("Unable to load test content. Please ensure the server is running.");
      return;
    }

    // Populate verification screen
    document.getElementById("verify-test-book").textContent = this.selectedTestData.book;
    document.getElementById("verify-test-title").textContent = this.selectedTestData.title;
    document.getElementById("verify-test-duration").textContent = `${this.selectedTestData.durationMinutes} Minutes`;
    document.getElementById("verify-test-questions").textContent = `${this.selectedTestData.totalQuestions} Questions`;

    this.showView("verification");
  }

  launchExam() {
    if (!this.selectedTestData) return;

    if (this.examInstance) {
      this.examInstance.destroy();
    }

    this.showView("exam");

    this.examInstance = new CdIeltsExam({
      testData: this.selectedTestData,
      candidateName: this.candidateName,
      candidateNumber: this.candidateNumber,
      mode: this.selectedMode,
      onFinish: (evalResults) => {
        this.renderResultsScreen(evalResults);
      }
    });
  }

  renderResultsScreen(evalData) {
    this.showView("results");

    // Banner stats
    document.getElementById("res-band-score").textContent = evalData.bandScore.toFixed(1);
    document.getElementById("res-raw-score").textContent = `${evalData.rawScore} / ${evalData.totalQuestions}`;
    document.getElementById("res-cefr").textContent = evalData.cefrLevel;
    document.getElementById("res-time-spent").textContent = IeltsScoring.formatDuration(evalData.timeSpentSeconds);
    document.getElementById("res-test-title").textContent = `${evalData.book} – ${evalData.title}`;
    document.getElementById("res-candidate-name").textContent = evalData.candidateName;

    // Passage breakdown cards
    const breakdownWrap = document.getElementById("res-passage-breakdown");
    if (breakdownWrap && evalData.passageBreakdown) {
      breakdownWrap.innerHTML = Object.entries(evalData.passageBreakdown).map(([num, p]) => {
        const percent = p.total > 0 ? Math.round((p.correct / p.total) * 100) : 0;
        return `
          <div class="passage-stat-card">
            <h4>Part ${num}: ${p.title}</h4>
            <div style="display:flex; justify-content:space-between; font-size:0.9em; font-weight:600;">
              <span>Score: ${p.correct} / ${p.total}</span>
              <span>${percent}%</span>
            </div>
            <div class="passage-progress-bar">
              <div class="passage-progress-fill" style="width: ${percent}%;"></div>
            </div>
          </div>
        `;
      }).join("");
    }

    // Render detailed questions review
    this.currentResultsList = evalData.results || [];
    this.renderReviewList("all");

    // Bind filter buttons
    document.querySelectorAll(".review-tab-btn").forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll(".review-tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const filter = btn.dataset.filter;
        this.renderReviewList(filter);
      };
    });
  }

  renderReviewList(filter = "all") {
    const listWrap = document.getElementById("res-review-list");
    if (!listWrap) return;

    let filtered = this.currentResultsList;
    if (filter === "correct") {
      filtered = this.currentResultsList.filter(r => r.isCorrect);
    } else if (filter === "incorrect") {
      filtered = this.currentResultsList.filter(r => !r.isCorrect && r.candidateAnswer);
    } else if (filter === "unanswered") {
      filtered = this.currentResultsList.filter(r => !r.candidateAnswer);
    }

    if (filtered.length === 0) {
      listWrap.innerHTML = `<div style="text-align:center; padding:30px; color:#64748b;">No questions match this filter.</div>`;
      return;
    }

    listWrap.innerHTML = filtered.map(item => {
      const isCorrect = item.isCorrect;
      const candAnswer = item.candidateAnswer || "(No Answer Entered)";
      const isUnanswered = !item.candidateAnswer;

      let badgeClass = "badge-incorrect";
      let badgeLabel = "Incorrect";
      if (isCorrect) {
        badgeClass = "badge-correct";
        badgeLabel = "Correct";
      } else if (isUnanswered) {
        badgeClass = "badge-unanswered";
        badgeLabel = "Unanswered";
      }

      const formattedCorrect = Array.isArray(item.correctAnswer)
        ? item.correctAnswer.join(" / ")
        : item.correctAnswer;

      return `
        <div class="review-card ${isCorrect ? 'is-correct' : 'is-incorrect'}">
          <div class="review-card-top">
            <div>
              <span class="question-number-badge">Question ${item.number}</span>
              <span style="font-size:0.85em; color:#64748b; font-weight:600;">Part ${item.passageNumber} • ${item.type.replace(/_/g, " ").toUpperCase()}</span>
            </div>
            <span class="review-status-badge ${badgeClass}">${badgeLabel}</span>
          </div>

          <div style="font-weight:500; margin-bottom:10px;">${item.prompt}</div>

          <div class="review-answers-box">
            <div>
              <div class="review-ans-label">Your Answer</div>
              <div class="review-ans-value ${isCorrect ? 'ans-correct' : 'ans-incorrect'}">${candAnswer}</div>
            </div>
            <div>
              <div class="review-ans-label">Correct Official Answer</div>
              <div class="review-ans-value ans-correct">${formattedCorrect}</div>
            </div>
          </div>

          ${item.explanation ? `
            <div class="review-explanation">
              <strong>Official Explanation (${item.passageReference}):</strong> ${item.explanation}
            </div>
          ` : ""}
        </div>
      `;
    }).join("");
  }
}

// Instantiate App globally
window.app = new MockExamApp();
