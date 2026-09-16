/**
 * CD-IELTS Core Exam Engine
 * Replicates the complete British Council / IDP Computer-Delivered IELTS experience.
 */

class CdIeltsExam {
  constructor(options) {
    this.testData = options.testData;
    this.candidateName = options.candidateName || "Candidate";
    this.candidateNumber = options.candidateNumber || "108429";
    this.mode = options.mode || "exam"; // 'exam' (strict 60m timer) or 'practice'
    this.onFinish = options.onFinish || function () {};

    this.currentPassageIndex = 0;
    this.currentQuestionNumber = 1;
    this.answers = {};
    this.flaggedQuestions = new Set();
    this.timeRemaining = this.testData.durationMinutes * 60;
    this.timerInterval = null;
    this.isTimerHidden = false;
    this.highlighter = null;

    this.initDOM();
    this.initSplitter();
    this.initHighlighter();
    this.initShortcuts();
    this.startTimer();
    this.renderCurrentPassage();
    this.renderFooterNavigation();
  }

  initDOM() {
    // Header candidate info
    document.getElementById("exam-candidate-name").textContent = this.candidateName;
    document.getElementById("exam-candidate-num").textContent = this.candidateNumber;
    document.getElementById("exam-test-title").textContent = `${this.testData.bookShort} - ${this.testData.title}`;

    // Contrast switcher
    const contrastBtn = document.getElementById("btn-contrast");
    if (contrastBtn) {
      contrastBtn.onclick = () => this.cycleContrast();
    }

    // Text size switcher
    const textSizeBtn = document.getElementById("btn-text-size");
    if (textSizeBtn) {
      textSizeBtn.onclick = () => this.cycleTextSize();
    }

    // Help button
    const helpBtn = document.getElementById("btn-help");
    if (helpBtn) {
      helpBtn.onclick = () => this.showHelpModal();
    }

    // Timer box toggle
    const timerBox = document.getElementById("exam-timer-box");
    if (timerBox) {
      timerBox.onclick = () => this.toggleTimerVisibility();
    }

    // Prev / Next buttons
    const prevBtn = document.getElementById("btn-prev-q");
    const nextBtn = document.getElementById("btn-next-q");
    if (prevBtn) prevBtn.onclick = () => this.navigateQuestion(-1);
    if (nextBtn) nextBtn.onclick = () => this.navigateQuestion(1);

    // Review checkbox
    const reviewCheckbox = document.getElementById("exam-review-check");
    if (reviewCheckbox) {
      reviewCheckbox.onchange = (e) => this.toggleReviewFlag(this.currentQuestionNumber, e.target.checked);
    }

    // Submit button
    const submitBtn = document.getElementById("btn-submit-exam");
    if (submitBtn) {
      submitBtn.onclick = () => this.showSubmitConfirmationModal();
    }
  }

  initSplitter() {
    const resizer = document.getElementById("exam-resizer");
    const leftPane = document.getElementById("exam-pane-left");
    const rightPane = document.getElementById("exam-pane-right");
    const workspace = document.getElementById("exam-workspace");

    if (!resizer || !leftPane || !rightPane || !workspace) return;

    let isDragging = false;

    const onMouseDown = (e) => {
      isDragging = true;
      resizer.classList.add("is-dragging");
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    };

    const onMouseMove = (e) => {
      if (!isDragging) return;
      const workspaceRect = workspace.getBoundingClientRect();
      const relativeX = e.clientX - workspaceRect.left;
      const minWidth = 240;
      const maxWidth = workspaceRect.width - 240;

      if (relativeX >= minWidth && relativeX <= maxWidth) {
        const leftPercent = (relativeX / workspaceRect.width) * 100;
        leftPane.style.width = `${leftPercent}%`;
        rightPane.style.width = `${100 - leftPercent}%`;
      }
    };

    const onMouseUp = () => {
      if (isDragging) {
        isDragging = false;
        resizer.classList.remove("is-dragging");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
    };

    resizer.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);

    // Touch support for tablets
    resizer.addEventListener("touchstart", (e) => {
      isDragging = true;
      resizer.classList.add("is-dragging");
    });
    window.addEventListener("touchmove", (e) => {
      if (!isDragging || !e.touches[0]) return;
      const workspaceRect = workspace.getBoundingClientRect();
      const relativeX = e.touches[0].clientX - workspaceRect.left;
      const minWidth = 200;
      const maxWidth = workspaceRect.width - 200;
      if (relativeX >= minWidth && relativeX <= maxWidth) {
        const leftPercent = (relativeX / workspaceRect.width) * 100;
        leftPane.style.width = `${leftPercent}%`;
        rightPane.style.width = `${100 - leftPercent}%`;
      }
    });
    window.addEventListener("touchend", () => {
      isDragging = false;
      resizer.classList.remove("is-dragging");
    });
  }

  initHighlighter() {
    this.highlighter = new CdHighlighter("exam-workspace");
  }

  initShortcuts() {
    document.addEventListener("keydown", (e) => {
      // Don't intercept if user is typing in a text input or textarea
      if (["INPUT", "TEXTAREA"].includes(e.target.tagName)) {
        return;
      }

      // Alt+N for Next Question, Alt+P for Previous
      if (e.altKey && (e.key === "n" || e.key === "N")) {
        e.preventDefault();
        this.navigateQuestion(1);
      } else if (e.altKey && (e.key === "p" || e.key === "P")) {
        e.preventDefault();
        this.navigateQuestion(-1);
      } else if (e.altKey && (e.key === "r" || e.key === "R")) {
        e.preventDefault();
        const reviewBox = document.getElementById("exam-review-check");
        if (reviewBox) {
          reviewBox.checked = !reviewBox.checked;
          this.toggleReviewFlag(this.currentQuestionNumber, reviewBox.checked);
        }
      }
    });
  }

  /* Timer Controls */
  startTimer() {
    this.updateTimerDisplay();
    this.timerInterval = setInterval(() => {
      if (this.timeRemaining > 0) {
        this.timeRemaining--;
        this.updateTimerDisplay();

        // 10 minutes warning alert
        if (this.timeRemaining === 600) {
          this.triggerTimeAlert("10 minutes remaining in the Reading test.");
        }
        // 5 minutes warning alert
        if (this.timeRemaining === 300) {
          this.triggerTimeAlert("5 minutes remaining in the Reading test.");
        }
      } else {
        clearInterval(this.timerInterval);
        this.triggerTimeOut();
      }
    }, 1000);
  }

  updateTimerDisplay() {
    const timerText = document.getElementById("exam-timer-text");
    const timerBox = document.getElementById("exam-timer-box");
    if (!timerText || !timerBox) return;

    if (this.isTimerHidden) {
      timerText.textContent = "⏱ Clock";
      return;
    }

    const mins = Math.floor(this.timeRemaining / 60);
    const secs = this.timeRemaining % 60;
    const formatted = `${mins < 10 ? '0' : ''}${mins}:${secs < 10 ? '0' : ''}${secs}`;
    timerText.textContent = formatted;

    // Warning styling
    if (this.timeRemaining <= 600) {
      timerBox.classList.add("warning");
    } else {
      timerBox.classList.remove("warning");
    }
  }

  toggleTimerVisibility() {
    this.isTimerHidden = !this.isTimerHidden;
    this.updateTimerDisplay();
  }

  triggerTimeAlert(msg) {
    const banner = document.createElement("div");
    banner.style.cssText = `
      position: fixed; top: 60px; right: 20px;
      background: #dc2626; color: #ffffff;
      padding: 12px 20px; border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
      z-index: 1500; font-weight: 600;
      animation: fadeIn 0.2s ease-out;
    `;
    banner.textContent = msg;
    document.body.appendChild(banner);
    setTimeout(() => { banner.remove(); }, 6000);
  }

  triggerTimeOut() {
    alert("Time is up! Your Reading test will now be submitted automatically.");
    this.submitExam();
  }

  /* Accessibility & Contrast */
  cycleContrast() {
    const themes = ["theme-default", "theme-black-on-yellow", "theme-yellow-on-black", "theme-white-on-blue"];
    const body = document.body;
    let currentIdx = themes.findIndex(t => body.classList.contains(t));
    if (currentIdx === -1) currentIdx = 0;

    themes.forEach(t => body.classList.remove(t));
    const nextTheme = themes[(currentIdx + 1) % themes.length];
    body.classList.add(nextTheme);
  }

  cycleTextSize() {
    const sizes = ["text-regular", "text-large", "text-extra-large"];
    const body = document.body;
    let currentIdx = sizes.findIndex(s => body.classList.contains(s));
    if (currentIdx === -1) currentIdx = 0;

    sizes.forEach(s => body.classList.remove(s));
    const nextSize = sizes[(currentIdx + 1) % sizes.length];
    body.classList.add(nextSize);
  }

  showHelpModal() {
    const modal = document.createElement("div");
    modal.className = "modal-overlay";
    modal.innerHTML = `
      <div class="modal-box">
        <div class="modal-header">
          <span>Test Instructions & Keyboard Shortcuts</span>
          <span style="cursor:pointer;" id="modal-help-close">&times;</span>
        </div>
        <div class="modal-body">
          <p><strong>Official CD-IELTS Navigation:</strong></p>
          <ul style="margin: 8px 0 16px 20px; line-height: 1.8;">
            <li><strong>Alt + N:</strong> Move to Next Question</li>
            <li><strong>Alt + P:</strong> Move to Previous Question</li>
            <li><strong>Alt + R:</strong> Toggle Review Checkbox for current question</li>
            <li><strong>Tab / Shift + Tab:</strong> Jump between options and input fields</li>
            <li><strong>Space:</strong> Select radio option or checkbox</li>
          </ul>
          <p><strong>Tools:</strong></p>
          <ul style="margin: 8px 0 0 20px; line-height: 1.8;">
            <li><strong>Highlight:</strong> Select any text with your mouse to highlight it. Right-click highlighted text to remove.</li>
            <li><strong>Notes:</strong> Select text and click 'Note' to add a sticky observation note.</li>
            <li><strong>Splitter:</strong> Click and drag the vertical bar between passage and questions to resize the view.</li>
          </ul>
        </div>
        <div class="modal-footer">
          <button class="btn-primary" id="modal-help-ok">Close</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const close = () => modal.remove();
    modal.querySelector("#modal-help-close").onclick = close;
    modal.querySelector("#modal-help-ok").onclick = close;
  }

  /* Rendering Passage and Questions */
  renderCurrentPassage() {
    const passage = this.testData.passages[this.currentPassageIndex];
    if (!passage) return;

    // 1. Render Left Pane (Passage)
    const leftPane = document.getElementById("exam-pane-left");
    let passageHTML = `
      <div class="passage-header">
        <div class="passage-part-label">Reading Passage ${passage.passageNumber}</div>
        <h2 class="passage-title">${passage.title}</h2>
        ${passage.subtitle ? `<div class="passage-subtitle">${passage.subtitle}</div>` : ""}
      </div>
      <div class="passage-instruction-bar">
        You should spend about 20 minutes on <strong>Questions ${this.getPassageQuestionRange(passage)}</strong>, which are based on Reading Passage ${passage.passageNumber} below.
      </div>
      <div class="passage-body">
    `;

    passage.paragraphs.forEach(p => {
      passageHTML += `
        <p class="passage-paragraph">
          ${p.label ? `<span class="paragraph-label">${p.label}</span>` : ""}
          ${p.text}
        </p>
      `;
    });

    passageHTML += `</div>`;
    leftPane.innerHTML = passageHTML;
    leftPane.scrollTop = 0;

    // 2. Render Right Pane (Questions)
    const rightPane = document.getElementById("exam-pane-right");
    let questionsHTML = `
      <div class="questions-container">
    `;

    // Group questions by instruction if applicable
    let lastInstruction = "";
    passage.questions.forEach(q => {
      if (q.instruction && q.instruction !== lastInstruction) {
        lastInstruction = q.instruction;
        questionsHTML += `
          <div class="question-group-header">
            <div class="question-group-title">Questions ${this.getQuestionGroupRange(passage.questions, q.instruction)}</div>
            <div class="question-group-instruction">${q.instruction}</div>
          </div>
        `;
      }

      questionsHTML += this.renderQuestionCard(q);
    });

    questionsHTML += `</div>`;
    rightPane.innerHTML = questionsHTML;
    rightPane.scrollTop = 0;

    // Bind event handlers for all input types
    this.bindQuestionInputs(rightPane);

    // Update active question highlight
    this.updateActiveQuestionHighlight();

    // Scroll to the active question if it belongs to this passage
    this.scrollToQuestion(this.currentQuestionNumber);
  }

  getPassageQuestionRange(passage) {
    if (!passage.questions.length) return "";
    const first = passage.questions[0].number;
    const last = passage.questions[passage.questions.length - 1].number;
    return `${first}–${last}`;
  }

  getQuestionGroupRange(questions, instruction) {
    const group = questions.filter(q => q.instruction === instruction);
    if (group.length === 1) return `${group[0].number}`;
    return `${group[0].number}–${group[group.length - 1].number}`;
  }

  renderQuestionCard(q) {
    const currentVal = this.answers[String(q.number)] || "";
    const isFlagged = this.flaggedQuestions.has(q.number);

    let contentHTML = "";

    switch (q.type) {
      case "true_false_not_given":
      case "yes_no_not_given":
        const options = q.type === "true_false_not_given"
          ? ["TRUE", "FALSE", "NOT GIVEN"]
          : ["YES", "NO", "NOT GIVEN"];

        contentHTML = `
          <div class="tfng-buttons" data-qnum="${q.number}">
            ${options.map(opt => `
              <button type="button" class="tfng-btn ${currentVal === opt ? 'active' : ''}" data-value="${opt}">
                ${opt}
              </button>
            `).join("")}
          </div>
        `;
        break;

      case "multiple_choice_single":
        contentHTML = `
          <div class="options-list" data-qnum="${q.number}">
            ${q.options.map((opt, idx) => {
              const letter = opt.charAt(0);
              const isChecked = currentVal === letter;
              return `
                <label class="option-item ${isChecked ? 'selected' : ''}">
                  <input type="radio" name="q_${q.number}" value="${letter}" ${isChecked ? 'checked' : ''} />
                  <span>${opt}</span>
                </label>
              `;
            }).join("")}
          </div>
        `;
        break;

      case "multiple_choice_multi":
        contentHTML = `
          <div class="options-list multi-select" data-qnum="${q.number}">
            ${q.options.map(opt => {
              const letter = opt.charAt(0);
              const isChecked = currentVal === letter;
              return `
                <label class="option-item ${isChecked ? 'selected' : ''}">
                  <input type="radio" name="q_${q.number}" value="${letter}" ${isChecked ? 'checked' : ''} />
                  <span>${opt}</span>
                </label>
              `;
            }).join("")}
          </div>
        `;
        break;

      case "matching_info":
      case "matching_headings":
      case "matching_features":
        contentHTML = `
          <div style="margin-top: 10px;">
            <label style="font-weight: 500; font-size: 0.9em;">Select Answer: </label>
            <select class="matching-select" data-qnum="${q.number}">
              <option value="">-- Select --</option>
              ${q.options.map(opt => {
                const val = opt.length === 1 ? opt : opt.split(":")[0].trim();
                const isSelected = currentVal === val;
                return `<option value="${val}" ${isSelected ? 'selected' : ''}>${opt}</option>`;
              }).join("")}
            </select>
          </div>
        `;
        break;

      case "completion":
      default:
        // Replace blank with inline input
        const promptFormatted = q.prompt.replace(
          /_{2,}/,
          `<span class="completion-input-wrap"><input type="text" class="completion-input ${currentVal ? 'has-value' : ''}" data-qnum="${q.number}" value="${currentVal}" placeholder="answer..." /></span>`
        );
        return `
          <div class="question-card" id="q-card-${q.number}" data-qnum="${q.number}">
            <span class="question-number-badge">${q.number}</span>
            <div class="question-prompt">${promptFormatted}</div>
          </div>
        `;
    }

    return `
      <div class="question-card" id="q-card-${q.number}" data-qnum="${q.number}">
        <div>
          <span class="question-number-badge">${q.number}</span>
          <div class="question-prompt">${q.prompt}</div>
        </div>
        ${contentHTML}
      </div>
    `;
  }

  bindQuestionInputs(container) {
    // 1. TFNG Buttons
    container.querySelectorAll(".tfng-buttons").forEach(group => {
      const qNum = group.dataset.qnum;
      group.querySelectorAll(".tfng-btn").forEach(btn => {
        btn.onclick = () => {
          const val = btn.dataset.value;
          group.querySelectorAll(".tfng-btn").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          this.setAnswer(qNum, val);
        };
      });
    });

    // 2. Radio Options
    container.querySelectorAll(".option-item input[type='radio']").forEach(input => {
      input.onchange = () => {
        const qNum = input.name.replace("q_", "");
        const parentList = input.closest(".options-list");
        parentList.querySelectorAll(".option-item").forEach(item => item.classList.remove("selected"));
        input.closest(".option-item").classList.add("selected");
        this.setAnswer(qNum, input.value);
      };
    });

    // 3. Matching Dropdowns
    container.querySelectorAll(".matching-select").forEach(select => {
      select.onchange = () => {
        const qNum = select.dataset.qnum;
        this.setAnswer(qNum, select.value);
      };
    });

    // 4. Completion Text Inputs
    container.querySelectorAll(".completion-input").forEach(input => {
      input.oninput = () => {
        const qNum = input.dataset.qnum;
        const val = input.value.trim();
        if (val) {
          input.classList.add("has-value");
        } else {
          input.classList.remove("has-value");
        }
        this.setAnswer(qNum, val);
      };

      input.onfocus = () => {
        const qNum = parseInt(input.dataset.qnum, 10);
        this.setCurrentQuestion(qNum, false);
      };
    });

    // 5. Question card focus on click
    container.querySelectorAll(".question-card").forEach(card => {
      card.onclick = (e) => {
        const qNum = parseInt(card.dataset.qnum, 10);
        this.setCurrentQuestion(qNum, false);
      };
    });
  }

  setAnswer(qNumberStr, value) {
    if (value) {
      this.answers[String(qNumberStr)] = value;
    } else {
      delete this.answers[String(qNumberStr)];
    }
    this.updateNavigationPillState(parseInt(qNumberStr, 10));
  }

  /* Question & Passage Navigation */
  setCurrentQuestion(qNumber, shouldScroll = true) {
    this.currentQuestionNumber = qNumber;

    // Check if target question belongs to another passage
    const targetPassageIdx = this.findPassageIndexForQuestion(qNumber);
    if (targetPassageIdx !== -1 && targetPassageIdx !== this.currentPassageIndex) {
      this.currentPassageIndex = targetPassageIdx;
      this.renderCurrentPassage();
      this.renderFooterNavigation();
    }

    // Update active pill state
    document.querySelectorAll(".q-nav-btn").forEach(btn => {
      const num = parseInt(btn.dataset.qnum, 10);
      if (num === qNumber) {
        btn.classList.add("current");
        btn.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      } else {
        btn.classList.remove("current");
      }
    });

    // Update review flag checkbox
    const reviewBox = document.getElementById("exam-review-check");
    if (reviewBox) {
      reviewBox.checked = this.flaggedQuestions.has(qNumber);
    }

    // Update active card highlight in questions pane
    this.updateActiveQuestionHighlight();

    if (shouldScroll) {
      this.scrollToQuestion(qNumber);
    }
  }

  scrollToQuestion(qNumber) {
    const card = document.getElementById(`q-card-${qNumber}`);
    if (card) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  updateActiveQuestionHighlight() {
    document.querySelectorAll(".question-card").forEach(card => {
      const num = parseInt(card.dataset.qnum, 10);
      if (num === this.currentQuestionNumber) {
        card.classList.add("active-question");
      } else {
        card.classList.remove("active-question");
      }
    });
  }

  findPassageIndexForQuestion(qNumber) {
    for (let i = 0; i < this.testData.passages.length; i++) {
      const p = this.testData.passages[i];
      const hasQ = p.questions.some(q => q.number === qNumber);
      if (hasQ) return i;
    }
    return -1;
  }

  navigateQuestion(delta) {
    const nextQ = this.currentQuestionNumber + delta;
    if (nextQ >= 1 && nextQ <= this.testData.totalQuestions) {
      this.setCurrentQuestion(nextQ);
    }
  }

  toggleReviewFlag(qNumber, isFlagged) {
    if (isFlagged) {
      this.flaggedQuestions.add(qNumber);
    } else {
      this.flaggedQuestions.delete(qNumber);
    }
    this.updateNavigationPillState(qNumber);
  }

  updateNavigationPillState(qNumber) {
    const btn = document.querySelector(`.q-nav-btn[data-qnum="${qNumber}"]`);
    if (!btn) return;

    const hasAnswer = Boolean(this.answers[String(qNumber)]);
    const isFlagged = this.flaggedQuestions.has(qNumber);

    if (hasAnswer) {
      btn.classList.add("answered");
    } else {
      btn.classList.remove("answered");
    }

    if (isFlagged) {
      btn.classList.add("flagged");
    } else {
      btn.classList.remove("flagged");
    }
  }

  /* Render Footer Navigation */
  renderFooterNavigation() {
    // 1. Passage tabs
    const tabsWrap = document.getElementById("exam-part-tabs");
    if (tabsWrap) {
      tabsWrap.innerHTML = this.testData.passages.map((p, idx) => `
        <button type="button" class="part-tab-btn ${idx === this.currentPassageIndex ? 'active' : ''}" data-pidx="${idx}">
          Part ${p.passageNumber}
        </button>
      `).join("");

      tabsWrap.querySelectorAll(".part-tab-btn").forEach(btn => {
        btn.onclick = () => {
          const idx = parseInt(btn.dataset.pidx, 10);
          this.currentPassageIndex = idx;
          const firstQ = this.testData.passages[idx].questions[0].number;
          this.setCurrentQuestion(firstQ);
        };
      });
    }

    // 2. Question numbers strip 1 to 40
    const strip = document.getElementById("exam-question-strip");
    if (strip) {
      let stripHTML = "";
      for (let num = 1; num <= this.testData.totalQuestions; num++) {
        const hasAnswer = Boolean(this.answers[String(num)]);
        const isCurrent = num === this.currentQuestionNumber;
        const isFlagged = this.flaggedQuestions.has(num);

        stripHTML += `
          <button type="button" class="q-nav-btn ${hasAnswer ? 'answered' : ''} ${isCurrent ? 'current' : ''} ${isFlagged ? 'flagged' : ''}" data-qnum="${num}">
            ${num}
          </button>
        `;
      }
      strip.innerHTML = stripHTML;

      strip.querySelectorAll(".q-nav-btn").forEach(btn => {
        btn.onclick = () => {
          const qNum = parseInt(btn.dataset.qnum, 10);
          this.setCurrentQuestion(qNum);
        };
      });
    }

    // Update prev/next button disabled states
    this.updateNavButtons();
  }

  updateNavButtons() {
    const prevBtn = document.getElementById("btn-prev-q");
    const nextBtn = document.getElementById("btn-next-q");
    if (prevBtn) prevBtn.disabled = this.currentQuestionNumber <= 1;
    if (nextBtn) nextBtn.disabled = this.currentQuestionNumber >= this.testData.totalQuestions;
  }

  /* Submission Modal & Action */
  showSubmitConfirmationModal() {
    const answeredCount = Object.keys(this.answers).length;
    const unansweredCount = this.testData.totalQuestions - answeredCount;

    const modal = document.createElement("div");
    modal.className = "modal-overlay";
    modal.innerHTML = `
      <div class="modal-box">
        <div class="modal-header">
          <span>Finish Reading Test</span>
          <span style="cursor:pointer;" id="modal-submit-cancel-x">&times;</span>
        </div>
        <div class="modal-body">
          <p style="font-size: 1.05em; margin-bottom: 14px;">
            Are you sure you want to finish the <strong>Reading</strong> test?
          </p>
          <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:14px; margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
              <span>Total Questions:</span>
              <strong>${this.testData.totalQuestions}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; color:#16a34a;">
              <span>Answered:</span>
              <strong>${answeredCount}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; color:${unansweredCount > 0 ? '#dc2626' : '#64748b'};">
              <span>Unanswered:</span>
              <strong>${unansweredCount}</strong>
            </div>
          </div>
          ${unansweredCount > 0 ? `<p style="color:#b91c1c; font-size:0.9em;">Notice: Questions left unanswered will be marked incorrect.</p>` : ""}
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" id="modal-submit-cancel">Return to Test</button>
          <button class="btn-danger" id="modal-submit-confirm">Confirm and Finish</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const closeModal = () => modal.remove();
    modal.querySelector("#modal-submit-cancel-x").onclick = closeModal;
    modal.querySelector("#modal-submit-cancel").onclick = closeModal;
    modal.querySelector("#modal-submit-confirm").onclick = () => {
      closeModal();
      this.submitExam();
    };
  }

  async submitExam() {
    clearInterval(this.timerInterval);
    const timeSpent = (this.testData.durationMinutes * 60) - this.timeRemaining;

    // Show loading indicator
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
      <div style="background:#ffffff; padding:24px 36px; border-radius:8px; text-align:center;">
        <div style="font-size:1.4em; font-weight:700; margin-bottom:8px;">Evaluating Your Exam...</div>
        <p style="color:#64748b;">Calculating official IELTS Band score & analysis</p>
      </div>
    `;
    document.body.appendChild(overlay);

    try {
      const res = await fetch(`/api/tests/${this.testData.id}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidateName: this.candidateName,
          timeSpentSeconds: timeSpent,
          answers: this.answers
        })
      });

      if (!res.ok) {
        throw new Error("Server submission failed");
      }

      const evalData = await res.json();
      overlay.remove();
      this.onFinish(evalData);
    } catch (err) {
      console.warn("Using offline evaluation fallback:", err);
      overlay.remove();
      const evalData = this.evaluateOffline(timeSpent);
      this.onFinish(evalData);
    }
  }

  evaluateOffline(timeSpent) {
    let rawScore = 0;
    const passageBreakdown = {};
    const detailedResults = [];

    this.testData.passages.forEach(p => {
      passageBreakdown[p.passageNumber] = {
        title: p.title,
        total: p.questions.length,
        correct: 0
      };

      p.questions.forEach(q => {
        const candVal = this.answers[String(q.number)] || "";
        let isCorrect = false;

        if (Array.isArray(q.answer)) {
          isCorrect = q.answer.some(alt =>
            IeltsScoring.normalizeAnswer(alt) === IeltsScoring.normalizeAnswer(candVal)
          );
        } else {
          isCorrect = IeltsScoring.normalizeAnswer(q.answer) === IeltsScoring.normalizeAnswer(candVal);
        }

        if (isCorrect) {
          rawScore++;
          passageBreakdown[p.passageNumber].correct++;
        }

        detailedResults.push({
          number: q.number,
          passageNumber: p.passageNumber,
          type: q.type,
          prompt: q.prompt,
          candidateAnswer: candVal,
          correctAnswer: q.answer,
          isCorrect,
          explanation: q.explanation || "",
          passageReference: q.passageReference || ""
        });
      });
    });

    const bandInfo = IeltsScoring.getBandScore(rawScore);

    return {
      testId: this.testData.id,
      book: this.testData.book,
      title: this.testData.title,
      candidateName: this.candidateName,
      rawScore,
      totalQuestions: this.testData.totalQuestions,
      bandScore: bandInfo.band,
      cefrLevel: bandInfo.cefr,
      timeSpentSeconds: timeSpent,
      passageBreakdown,
      results: detailedResults
    };
  }

  destroy() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    if (this.highlighter) this.highlighter.clearAll();
  }
}

window.CdIeltsExam = CdIeltsExam;
