/**
 * Speaking module.
 *
 * SpeakingExam            – the test. The examiner's recorded questions play one by
 *                           one; after each, the candidate's answer is recorded and
 *                           uploaded in the background. Part 2 shows the cue card
 *                           with one minute to prepare.
 * Speaking.bindMicCheck() – microphone check on the instructions screen.
 * Speaking.renderResult() – the candidate's recordings, a self-check and the examiner offer.
 * Speaking.submissionHTML() / resultHTML() / markForm() – used by the examiner check page.
 * Speaking.fixWebmDuration() – Chrome's WebM recordings have no duration, so they cannot
 *                           be seeked; this writes the duration into the file.
 */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (v) => U.escapeHtml(v);
  const CANCELLED = new Error("cancelled");
  const MIN_ANSWER_SECONDS = 3;
  const SILENCE_WARN_SECONDS = 7;

  const CRITERIA = [
    ["fluency_coherence", "Fluency and Coherence", "Do you speak at length without long pauses, and link your ideas clearly?"],
    ["lexical_resource", "Lexical Resource", "Do you use a range of vocabulary, including less common words and natural phrases?"],
    ["grammar", "Grammatical Range and Accuracy", "Do you mix simple and complex sentences, with few errors?"],
    ["pronunciation", "Pronunciation", "Are you easy to understand, with natural stress, rhythm and intonation?"],
  ];

  /* ====================================================================
     Microphone and recording
     ==================================================================== */
  const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4", "audio/webm"];

  function micSupported() {
    return Boolean(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
  }

  function pickMime() {
    for (const m of MIME_CANDIDATES) {
      try { if (MediaRecorder.isTypeSupported(m)) return m; } catch (e) { /* ignore */ }
    }
    return "";
  }

  function openMic() {
    return navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
  }

  function micErrorMessage(err) {
    const name = err && err.name;
    if (!micSupported()) return "This browser cannot record audio. Please use a recent version of Chrome, Edge, Firefox or Safari.";
    if (name === "NotAllowedError" || name === "SecurityError") {
      return "Microphone access is blocked. Click the lock or microphone icon next to the address bar, allow the microphone for this site, and try again.";
    }
    if (name === "NotFoundError" || name === "OverconstrainedError") return "No microphone was found. Connect a microphone or headset and try again.";
    if (name === "NotReadableError") return "Your microphone is being used by another app. Close that app and try again.";
    return "We could not start your microphone. Please try again, or use another browser.";
  }

  function stopStream(stream) {
    if (stream) stream.getTracks().forEach((t) => t.stop());
  }

  /** Live input level (0–1) from a microphone stream. */
  class LevelMeter {
    constructor(stream, onLevel) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      this.onLevel = onLevel;
      this.level = 0;
      this.peak = 0; // highest level since the caller last reset it
      if (!Ctx) return;
      this.ctx = new Ctx();
      if (this.ctx.resume) this.ctx.resume().catch(() => {});
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = 1024;
      this.ctx.createMediaStreamSource(stream).connect(this.analyser);
      this.data = new Float32Array(this.analyser.fftSize);
      this.running = true;
      const tick = () => {
        if (!this.running) return;
        this.analyser.getFloatTimeDomainData(this.data);
        let sum = 0;
        for (let i = 0; i < this.data.length; i++) sum += this.data[i] * this.data[i];
        const db = 20 * Math.log10(Math.sqrt(sum / this.data.length) || 1e-8);
        this.level = Math.max(0, Math.min(1, (db + 58) / 46));
        this.peak = Math.max(this.peak, this.level);
        this.onLevel(this.level);
        this.raf = requestAnimationFrame(tick);
      };
      tick();
    }

    stop() {
      this.running = false;
      cancelAnimationFrame(this.raf);
      if (this.ctx) this.ctx.close().catch(() => {});
    }
  }

  /** Records one answer; stop() resolves with the audio and its length in seconds. */
  class AnswerRecorder {
    constructor(stream, mime) {
      this.chunks = [];
      const options = { audioBitsPerSecond: 32000 };
      if (mime) options.mimeType = mime;
      try {
        this.rec = new MediaRecorder(stream, options);
      } catch (e) {
        this.rec = new MediaRecorder(stream);
      }
      this.rec.ondataavailable = (e) => { if (e.data && e.data.size) this.chunks.push(e.data); };
      this.mime = mime;
    }

    start() {
      this.startedAt = performance.now();
      this.rec.start(1000);
    }

    get seconds() {
      return this.startedAt ? (performance.now() - this.startedAt) / 1000 : 0;
    }

    stop() {
      return new Promise((resolve) => {
        const seconds = this.seconds;
        const finish = async () => {
          const type = (this.rec.mimeType || this.mime || "audio/webm").trim();
          const blob = await fixWebmDuration(new Blob(this.chunks, { type }), seconds * 1000);
          resolve({ blob, seconds });
        };
        if (this.rec.state === "inactive") return finish();
        this.rec.onstop = finish;
        try { this.rec.stop(); } catch (e) { finish(); }
      });
    }
  }

  /* --------------------------------------------------------------------
     WebM duration. MediaRecorder in Chrome writes an "unknown" duration, so
     players cannot show the length or seek. We add a Duration element to the
     file's Info section (the segment has an unknown size and no seek index,
     so nothing after it has to move).
     -------------------------------------------------------------------- */
  function readId(b, p) {
    let len = 1;
    let mask = 0x80;
    while (len <= 4 && !(b[p] & mask)) { len++; mask >>= 1; }
    if (len > 4) throw new Error("bad element id");
    let id = 0;
    for (let i = 0; i < len; i++) id = id * 256 + b[p + i];
    return { id, len };
  }

  function readSize(b, p) {
    let len = 1;
    let mask = 0x80;
    while (len <= 8 && !(b[p] & mask)) { len++; mask >>= 1; }
    if (len > 8) throw new Error("bad element size");
    let value = b[p] & (mask - 1);
    let unknown = value === mask - 1;
    for (let i = 1; i < len; i++) {
      value = value * 256 + b[p + i];
      if (b[p + i] !== 0xff) unknown = false;
    }
    return { value: unknown ? -1 : value, len };
  }

  function patchWebm(b, durationMs) {
    let p = 0;
    let el = readId(b, p);
    if (el.id !== 0x1a45dfa3) return null; // EBML header
    let size = readSize(b, p + el.len);
    p += el.len + size.len + size.value;
    el = readId(b, p);
    if (el.id !== 0x18538067) return null; // Segment
    size = readSize(b, p + el.len);
    if (size.value !== -1) return null; // only live recordings with an open-ended segment
    p += el.len + size.len;
    while (p < b.length) {
      const child = readId(b, p);
      const csize = readSize(b, p + child.len);
      if (csize.value < 0) return null;
      const start = p + child.len + csize.len;
      const end = start + csize.value;
      if (child.id === 0x114d9b74 || child.id === 0x1f43b675) return null; // seek index or audio before Info
      if (child.id === 0x1549a966) { // Info
        let scale = 1000000;
        for (let q = start; q < end;) {
          const c = readId(b, q);
          const s = readSize(b, q + c.len);
          const ds = q + c.len + s.len;
          if (c.id === 0x4489) return null; // already has a duration
          if (c.id === 0x2ad7b1) {
            let v = 0;
            for (let i = 0; i < s.value; i++) v = v * 256 + b[ds + i];
            scale = v || scale;
          }
          q = ds + s.value;
        }
        const duration = new Uint8Array(11);
        duration.set([0x44, 0x89, 0x88]);
        new DataView(duration.buffer).setFloat64(3, (durationMs * 1e6) / scale);
        const content = b.subarray(start, end);
        const newSize = content.length + duration.length;
        const head = new Uint8Array(12);
        head.set([0x15, 0x49, 0xa9, 0x66, 0x01]);
        let v = newSize;
        for (let i = 11; i >= 5; i--) { head[i] = v & 0xff; v = Math.floor(v / 256); }
        const out = new Uint8Array(p + head.length + newSize + (b.length - end));
        out.set(b.subarray(0, p), 0);
        out.set(head, p);
        out.set(content, p + head.length);
        out.set(duration, p + head.length + content.length);
        out.set(b.subarray(end), p + head.length + newSize);
        return out;
      }
      p = end;
    }
    return null;
  }

  async function fixWebmDuration(blob, durationMs) {
    if (!/webm/i.test(blob.type) || !(durationMs > 0)) return blob;
    try {
      const fixed = patchWebm(new Uint8Array(await blob.arrayBuffer()), durationMs);
      return fixed ? new Blob([fixed], { type: blob.type }) : blob;
    } catch (e) {
      return blob;
    }
  }

  /* ====================================================================
     Background uploads
     ==================================================================== */
  class Uploader {
    constructor(submissionId, onChange) {
      this.submissionId = submissionId;
      this.onChange = onChange || (() => {});
      this.queue = [];
      this.state = {};
      this.failedJobs = [];
      this.lastError = "";
      this.busy = false;
      this.idleWaiters = [];
    }

    add(key, blob, seconds) {
      this.queue = this.queue.filter((j) => j.key !== key);
      this.failedJobs = this.failedJobs.filter((j) => j.key !== key);
      this.queue.push({ key, blob, seconds, tries: 0 });
      this.state[key] = "waiting";
      this.onChange();
      this.pump();
    }

    counts() {
      const values = Object.values(this.state);
      return { total: values.length, done: values.filter((s) => s === "done").length, failed: this.failedJobs.length };
    }

    async send(job) {
      const res = await fetch(`/api/speaking/submissions/${this.submissionId}/answers/${encodeURIComponent(job.key)}`, {
        method: "POST",
        headers: { "Content-Type": job.blob.type || "audio/webm", "X-Duration": job.seconds.toFixed(2) },
        body: job.blob,
      });
      if (!res.ok) {
        let message = `Upload failed (${res.status})`;
        try { message = (await res.json()).error || message; } catch (e) { /* ignore */ }
        const err = new Error(message);
        err.status = res.status;
        throw err;
      }
    }

    async pump() {
      if (this.busy) return;
      this.busy = true;
      while (this.queue.length) {
        const job = this.queue[0];
        this.state[job.key] = "uploading";
        this.onChange();
        try {
          await this.send(job);
          this.state[job.key] = "done";
          this.queue.shift();
        } catch (err) {
          job.tries++;
          const permanent = err.status && err.status < 500 && ![408, 429].includes(err.status);
          if (permanent || job.tries >= 4) {
            this.state[job.key] = "failed";
            this.lastError = err.message;
            this.failedJobs.push(job);
            this.queue.shift();
          } else {
            await new Promise((r) => setTimeout(r, 1500 * job.tries));
          }
        }
        this.onChange();
      }
      this.busy = false;
      this.onChange();
      this.idleWaiters.splice(0).forEach((r) => r());
    }

    idle() {
      if (!this.busy && !this.queue.length) return Promise.resolve();
      return new Promise((r) => this.idleWaiters.push(r));
    }

    retryFailed() {
      const jobs = this.failedJobs.splice(0);
      jobs.forEach((j) => { j.tries = 0; this.state[j.key] = "waiting"; this.queue.push(j); });
      this.pump();
    }
  }

  /* ====================================================================
     The test
     ==================================================================== */
  function buildSteps(test) {
    const steps = [];
    test.parts.forEach((part) => part.questions.forEach((q, i) => steps.push({ part, q, index: i })));
    return steps;
  }

  class SpeakingExam extends ExamShell {
    constructor(opts) {
      super(opts);
      const saved = this.saved && this.saved.mode === this.mode && this.saved.submissionId ? this.saved : null;
      this.steps = buildSteps(this.test);
      this.step = saved ? Math.max(0, Math.min(saved.step || 0, this.steps.length - 1)) : 0;
      this.submissionId = saved ? saved.submissionId : null;
      this.notes = saved ? saved.notes || "" : "";
      this.cancelled = false;
      this.waiters = new Set();
      this.player = new Audio();
      this.player.preload = "auto";
      this.player.volume = Math.min(1, Math.max(0, Number(U.store.get("mockexam:volume", 0.9)) || 0.9));
      this.mount();
    }

    mount() {
      $("exam-screen").classList.add("speaking-mode");
      this.mountShell(`${this.test.shortTitle || this.test.title} · Speaking`, "Speaking", "Speaking");
      $("exam-question-strip").hidden = true;
      $("exam-review-wrap").hidden = true;
      $("btn-prev-q").hidden = true;
      $("btn-next-q").hidden = true;
      $("btn-submit-exam").textContent = "End test";
      const ex = this.test.examiner || {};
      $("exam-pane-right").innerHTML = `
        <div class="speak-stage">
          <div class="speak-top">
            <div><span class="speak-part" id="sp-part"></span> <span class="speak-part-title" id="sp-part-title"></span></div>
            <div class="speak-count" id="sp-count"></div>
          </div>
          <div class="speak-examiner" id="sp-examiner">
            <div class="speak-avatar" aria-hidden="true">${esc((ex.name || "E")[0])}</div>
            <div class="speak-examiner-name"><strong>${esc(ex.name || "Examiner")}</strong><span id="sp-examiner-state">Examiner</span></div>
          </div>
          <div class="speak-question" id="sp-question"></div>
          <div class="speak-panel" id="sp-panel" aria-live="polite"></div>
          <div class="speak-saving" id="sp-saving"></div>
        </div>`;
      this.renderPartTabs();
      this.run();
    }

    get moduleName() {
      return "Speaking";
    }

    /* Timer: counts up; the test is paced by the questions, not a deadline */
    startTimer() {
      clearInterval(this.timer);
      this.renderTimer();
      this.timer = setInterval(() => {
        this.elapsed++;
        this.renderTimer();
        if (this.elapsed % 10 === 0) this.saveProgress();
      }, 1000);
    }

    renderTimer() {
      $("exam-timer-text").textContent = this.timerHidden ? "Show time" : `Time ${U.formatClock(this.elapsed)}`;
      $("exam-timer-box").classList.remove("warning");
    }

    helpHTML() {
      return `
        <p><strong>How the Speaking test works</strong></p>
        <ul class="help-list">
          <li>The examiner asks each question. When the question ends, recording starts automatically: just speak.</li>
          <li>Press <strong>Finish answer</strong> when you have finished. Recording also stops when the answer time is up
            (30 seconds in Part 1, 2 minutes in Part 2, 1 minute in Part 3).</li>
          <li>In Part 2 you have one minute to prepare. You can type notes; they are saved with your test.</li>
          ${this.mode === "practice" ? `<li>Practice mode shows each question and lets you listen to your answer and record it again.</li>` : ""}
          <li>Your answers are saved to your account as you go. <strong>End test</strong> finishes early.</li>
        </ul>
        <p><strong>Tools</strong></p>
        <ul class="help-list">
          <li><strong>Timer:</strong> click the clock to hide or show it.</li>
          <li><strong>Contrast / Text size:</strong> change the colours and font size.</li>
        </ul>`;
    }

    progressData() {
      return { submissionId: this.submissionId, step: this.step, notes: this.notes };
    }

    renderPartTabs() {
      const cur = this.steps[Math.min(this.step, this.steps.length - 1)].part.partNumber;
      $("exam-part-tabs").innerHTML = this.test.parts.map((p) => `
        <span class="part-tab-btn speak-part-tab ${p.partNumber === cur ? "active" : ""} ${p.partNumber < cur ? "is-done" : ""}">Part ${p.partNumber}</span>`).join("");
    }

    /* Cancellable waiting ---------------------------------------------------- */
    wait(setup) {
      return new Promise((resolve, reject) => {
        if (this.cancelled) return reject(CANCELLED);
        let cleanup = null;
        let settled = false;
        const entry = () => { if (settled) return; settled = true; if (cleanup) cleanup(); reject(CANCELLED); };
        this.waiters.add(entry);
        cleanup = setup((value) => {
          if (settled) return;
          settled = true;
          this.waiters.delete(entry);
          if (cleanup) cleanup();
          resolve(value);
        }) || null;
        if (settled && cleanup) cleanup();
      });
    }

    sleep(ms) {
      return this.wait((done) => {
        const t = setTimeout(done, ms);
        return () => clearTimeout(t);
      });
    }

    /* UI pieces --------------------------------------------------------------- */
    panel(html) {
      $("sp-panel").innerHTML = html;
    }

    setExaminer(state) {
      $("sp-examiner").classList.toggle("is-speaking", state === "speaking");
      $("sp-examiner-state").textContent = state === "speaking" ? "Speaking…" : "Examiner";
    }

    showQuestion(step) {
      const { part, q } = step;
      $("sp-part").textContent = `Part ${part.partNumber}`;
      $("sp-part-title").textContent = part.title || "";
      const inPart = part.questions.length;
      $("sp-count").textContent = q.type === "long_turn" ? "Long turn" : `Question ${step.index + 1} of ${inPart}`;
      this.renderPartTabs();
      this.renderQuestionText(step, this.mode === "practice");
    }

    renderQuestionText(step, visible) {
      const { part, q } = step;
      const box = $("sp-question");
      if (q.type === "long_turn") {
        box.innerHTML = this.cueCardHTML(part.cueCard);
        return;
      }
      box.innerHTML = visible
        ? `<p class="speak-q-text">${esc(q.text)}</p>`
        : `<button type="button" class="btn-link speak-show-q" id="sp-show-q">Show the question</button>`;
      const btn = $("sp-show-q");
      if (btn) this.on(btn, "click", () => this.renderQuestionText(step, true));
    }

    cueCardHTML(card) {
      return `
        <div class="cue-card">
          <p class="cue-topic">${esc(card.topic)}</p>
          <p>You should say:</p>
          <ul>${card.points.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>
          <p>${esc(card.explain || "")}</p>
        </div>`;
    }

    renderSaving() {
      const el = $("sp-saving");
      if (!el || !this.uploader) return;
      const c = this.uploader.counts();
      if (!c.total) { el.textContent = ""; return; }
      el.innerHTML = c.failed
        ? `<span class="speak-save-bad">${c.failed} answer${c.failed === 1 ? "" : "s"} not saved yet – we will try again.</span>`
        : `<span class="${c.done === c.total ? "speak-save-ok" : ""}">${c.done === c.total ? "✓ " : ""}${c.done} of ${c.total} answers saved</span>`;
    }

    /* The flow ---------------------------------------------------------------- */
    async run() {
      try {
        this.panel(`<p class="speak-status">Getting ready…</p>`);
        await this.ensureSubmission();
        await this.ensureMic();
        while (this.step < this.steps.length && !this.finishing) {
          await this.runStep(this.steps[this.step]);
          this.step++;
          this.saveProgress();
        }
        if (this.finishing) return;
        $("sp-question").innerHTML = "";
        this.panel(`<p class="speak-status">That is the end of the test.</p>`);
        await this.playClip(this.test.prompts && this.test.prompts.end);
        await this.finishTest();
      } catch (err) {
        if (err === CANCELLED || this.cancelled) return;
        this.showFatal(err.message || String(err));
      }
    }

    async ensureSubmission() {
      if (this.submissionId) {
        try {
          const { submission } = await U.api(`/api/speaking/submissions/${this.submissionId}`);
          if (submission.status === "recording") {
            this.uploader = new Uploader(this.submissionId, () => this.renderSaving());
            submission.parts.forEach((p) => p.questions.forEach((q) => { if (q.recording) this.uploader.state[q.key] = "done"; }));
            this.renderSaving();
            return;
          }
        } catch (e) { /* start a new attempt below */ }
        this.submissionId = null;
        this.step = 0;
      }
      const res = await U.api(`/api/speaking/${encodeURIComponent(this.test.id)}/start`, {
        method: "POST", body: JSON.stringify({ candidateName: this.candidateName, mode: this.mode }),
      });
      this.submissionId = res.submissionId;
      this.uploader = new Uploader(this.submissionId, () => this.renderSaving());
      this.saveProgress();
    }

    async ensureMic() {
      if (!micSupported()) throw new Error(micErrorMessage());
      for (;;) {
        try {
          this.stream = await openMic();
          break;
        } catch (err) {
          this.panel(`
            <div class="speak-error"><strong>We need your microphone</strong><p>${esc(micErrorMessage(err))}</p>
              <button type="button" class="btn-primary" id="sp-mic-retry">Try again</button></div>`);
          await this.wait((done) => {
            const b = $("sp-mic-retry");
            const h = () => done();
            b.addEventListener("click", h);
            return () => b.removeEventListener("click", h);
          });
          this.panel(`<p class="speak-status">Starting the microphone…</p>`);
        }
      }
      if (this.cancelled) { stopStream(this.stream); throw CANCELLED; }
      this.mime = pickMime();
      this.meter = new LevelMeter(this.stream, (level) => {
        const bar = $("sp-level");
        if (bar) bar.style.width = `${Math.round(level * 100)}%`;
      });
    }

    async runStep(step) {
      const { part, q } = step;
      this.showQuestion(step);
      this.panel(`<p class="speak-status"><span class="speak-ear" aria-hidden="true"></span>Listen to the examiner…</p>`);
      if (step.index === 0 && step !== this.steps[0]) await this.sleep(800);
      await this.playClip(q.audio);
      if (q.type === "long_turn") {
        await this.prepareLongTurn(part, q);
        this.panel(`<p class="speak-status">Listen to the examiner…</p>`);
        await this.playClip(this.test.prompts && this.test.prompts["p2-start"]);
      }
      await this.recordAnswer(q);
    }

    playClip(audio) {
      if (!audio || !audio.src) return Promise.resolve();
      this.setExaminer("speaking");
      return this.wait((done) => {
        const el = this.player;
        const finish = () => { this.setExaminer("idle"); done(); };
        const onError = () => {
          // Without the audio the candidate can still read the question.
          const step = this.steps[this.step];
          if (step) this.renderQuestionText(step, true);
          U.toast("The examiner's audio could not be played. Read the question instead.", "warn");
          finish();
        };
        el.onended = finish;
        el.onerror = onError;
        el.src = audio.src;
        el.play().catch((err) => {
          if (err && err.name === "NotAllowedError") {
            this.panel(`<button type="button" class="btn-primary btn-lg" id="sp-play">▶ Play the question</button>`);
            $("sp-play").addEventListener("click", () => el.play().catch(onError));
          } else {
            onError();
          }
        });
        return () => { el.onended = null; el.onerror = null; el.pause(); };
      });
    }

    async prepareLongTurn(part, q) {
      const total = q.prepSeconds || 60;
      this.panel(`
        <div class="speak-prep">
          <div class="speak-timer-row"><strong>Preparation time</strong><span class="speak-countdown" id="sp-prep-left">${U.formatClock(total)}</span></div>
          <div class="speak-bar"><span id="sp-prep-bar"></span></div>
          <label for="sp-notes" class="speak-notes-label">Your notes (optional)</label>
          <textarea id="sp-notes" class="speak-notes" rows="5" maxlength="2000" spellcheck="false"
            placeholder="Write a few key words for each point…">${esc(this.notes)}</textarea>
          <button type="button" class="btn-secondary" id="sp-prep-done">I am ready to speak</button>
        </div>`);
      const notes = $("sp-notes");
      this.on(notes, "input", () => { this.notes = notes.value; this.saveProgressSoon(); });
      notes.focus();
      let left = total;
      await this.wait((done) => {
        const t = setInterval(() => {
          left--;
          const l = $("sp-prep-left");
          if (l) l.textContent = U.formatClock(left);
          const b = $("sp-prep-bar");
          if (b) b.style.width = `${((total - left) / total) * 100}%`;
          if (left <= 0) done();
        }, 1000);
        const btn = $("sp-prep-done");
        btn.addEventListener("click", done);
        return () => { clearInterval(t); btn.removeEventListener("click", done); };
      });
      this.notes = notes.value;
      this.saveProgress();
      // Keep the notes on screen while the candidate speaks.
      $("sp-question").insertAdjacentHTML("beforeend", this.notes.trim()
        ? `<div class="speak-notes-view"><strong>Your notes</strong><p>${U.richText(this.notes)}</p></div>` : "");
    }

    async recordAnswer(q) {
      const limit = q.answerSeconds || 30;
      for (;;) {
        const rec = new AnswerRecorder(this.stream, this.mime);
        rec.start();
        this.panel(`
          <div class="speak-rec">
            <div class="speak-rec-head"><span class="audio-live-dot" aria-hidden="true"></span><strong>Recording – speak now</strong>
              <span class="speak-countdown" id="sp-rec-left">${U.formatClock(limit)}</span></div>
            <div class="speak-bar speak-bar-time"><span id="sp-rec-bar"></span></div>
            <div class="speak-level" title="Microphone level"><span id="sp-level"></span></div>
            <p class="speak-hint" id="sp-rec-hint">Speak clearly. Press <strong>Finish answer</strong> when you have finished.</p>
            <button type="button" class="btn-primary btn-lg" id="sp-rec-stop" disabled>Finish answer</button>
          </div>`);
        let warned = false;
        if (this.meter) this.meter.peak = 0;
        await this.wait((done) => {
          const t = setInterval(() => {
            const s = rec.seconds;
            const left = Math.max(0, limit - s);
            const l = $("sp-rec-left");
            if (l) l.textContent = U.formatClock(Math.ceil(left));
            const b = $("sp-rec-bar");
            if (b) b.style.width = `${Math.min(100, (s / limit) * 100)}%`;
            const peak = this.meter && this.meter.ctx ? this.meter.peak : 1;
            const stop = $("sp-rec-stop");
            if (stop && s >= MIN_ANSWER_SECONDS) stop.disabled = false;
            if (!warned && s >= SILENCE_WARN_SECONDS && peak < 0.12) {
              warned = true;
              const hint = $("sp-rec-hint");
              if (hint) hint.innerHTML = `<span class="speak-warn">We cannot hear you. Check that your microphone is on and not muted.</span>`;
            }
            if (left <= 0) done();
          }, 250);
          const stop = $("sp-rec-stop");
          stop.addEventListener("click", done);
          this.stopCurrent = done;
          return () => { clearInterval(t); stop.removeEventListener("click", done); this.stopCurrent = null; };
        }).catch((err) => { rec.stop(); throw err; });
        const { blob, seconds } = await rec.stop();
        if (this.mode !== "practice" || this.endingEarly) {
          this.uploader.add(q.key, blob, seconds);
          return;
        }
        // Practice: listen back, and record again if you want.
        const url = URL.createObjectURL(blob);
        this.pendingReview = { key: q.key, blob, seconds };
        this.panel(`
          <div class="speak-review">
            <p class="speak-status">Your answer (${Math.round(seconds)} s)</p>
            <audio controls src="${url}" class="speak-audio"></audio>
            <div class="speak-review-actions">
              <button type="button" class="btn-secondary" id="sp-again">Record again</button>
              <button type="button" class="btn-primary" id="sp-next">${this.step === this.steps.length - 1 ? "Finish" : "Next question"}</button>
            </div>
          </div>`);
        const again = await this.wait((done) => {
          const a = $("sp-again");
          const n = $("sp-next");
          const ha = () => done(true);
          const hn = () => done(false);
          a.addEventListener("click", ha);
          n.addEventListener("click", hn);
          return () => { a.removeEventListener("click", ha); n.removeEventListener("click", hn); };
        });
        URL.revokeObjectURL(url);
        this.pendingReview = null;
        if (!again) {
          this.uploader.add(q.key, blob, seconds);
          return;
        }
      }
    }

    async confirmFinish() {
      if (this.finishing) return;
      const ok = await U.modal({
        title: "End the test now?",
        bodyHTML: "<p>Your recorded answers are kept. Questions you have not answered yet will be left blank.</p>",
        buttons: [
          { label: "Continue the test", className: "btn-secondary", value: false },
          { label: "End test", className: "btn-danger", value: true },
        ],
      });
      if (!ok || this.finishing) return;
      this.endingEarly = true;
      if (this.stopCurrent) {
        // Keep the answer being recorded, then finish.
        this.step = this.steps.length;
        this.stopCurrent();
        return;
      }
      this.interruptFlow();
      this.finishTest().catch((err) => this.showFatal(err.message));
    }

    interruptFlow() {
      if (this.pendingReview) {
        // Ending the test while listening back keeps that answer.
        this.uploader.add(this.pendingReview.key, this.pendingReview.blob, this.pendingReview.seconds);
        this.pendingReview = null;
      }
      this.cancelled = true;
      this.waiters.forEach((w) => w());
      this.waiters.clear();
      this.player.pause();
      this.cancelled = false;
      this.step = this.steps.length;
    }

    async finishTest() {
      if (this.finishing) return;
      this.finishing = true;
      clearInterval(this.timer);
      $("sp-question").innerHTML = "";
      this.setExaminer("idle");
      if (!this.uploader) {
        this.clearProgress();
        this.finished = true;
        return this.showFatal("The test had not started yet, so there is nothing to save.");
      }
      for (;;) {
        this.panel(`<p class="speak-status"><span class="spinner inline-spinner" aria-hidden="true"></span>Saving your answers…</p>`);
        await this.uploader.idle();
        const { done, failed } = this.uploader.counts();
        if (!failed) {
          if (!done) {
            this.finishing = false;
            this.clearProgress();
            this.finished = true;
            return this.showFatal("No answers were recorded, so there is nothing to save. Check your microphone and start the test again.");
          }
          break;
        }
        this.panel(`
          <div class="speak-error"><strong>${failed} answer${failed === 1 ? " was" : "s were"} not saved</strong>
            <p>${esc(this.uploader.lastError || "Check your internet connection.")}</p>
            <div class="speak-review-actions">
              <button type="button" class="btn-secondary" id="sp-skip">Finish without ${failed === 1 ? "it" : "them"}</button>
              <button type="button" class="btn-primary" id="sp-retry">Try again</button>
            </div></div>`);
        const retry = await new Promise((resolve) => {
          $("sp-retry").addEventListener("click", () => resolve(true));
          $("sp-skip").addEventListener("click", () => resolve(false));
        });
        if (!retry) break;
        this.uploader.retryFailed();
      }
      try {
        await U.api(`/api/speaking/submissions/${this.submissionId}/complete`, {
          method: "POST", body: JSON.stringify({ notes: this.notes, timeSpentSeconds: this.elapsed }),
        });
      } catch (err) {
        this.finishing = false;
        this.panel(`
          <div class="speak-error"><strong>Could not finish the test</strong><p>${esc(err.message)}</p>
            <button type="button" class="btn-primary" id="sp-complete-retry">Try again</button></div>`);
        $("sp-complete-retry").addEventListener("click", () => this.finishTest());
        return;
      }
      this.clearProgress();
      this.finished = true;
      this.onFinish({ module: "speaking", submissionId: this.submissionId, testId: this.test.id, title: this.test.title });
    }

    showFatal(message) {
      this.panel(`
        <div class="speak-error"><strong>The test cannot continue</strong><p>${esc(message)}</p>
          <button type="button" class="btn-primary" id="sp-back">Back to tests</button></div>`);
      $("sp-back").addEventListener("click", () => {
        this.finished = true;
        location.hash = "#/";
      });
    }

    destroy() {
      this.cancelled = true;
      this.waiters.forEach((w) => w());
      this.waiters.clear();
      this.player.pause();
      this.player.removeAttribute("src");
      if (this.meter) this.meter.stop();
      stopStream(this.stream);
      $("exam-screen").classList.remove("speaking-mode");
      $("btn-prev-q").hidden = false;
      $("btn-next-q").hidden = false;
      $("btn-submit-exam").textContent = "Finish test";
      super.destroy();
    }
  }

  /* ====================================================================
     Microphone check (instructions screen)
     ==================================================================== */
  function bindMicCheck(root) {
    const btn = root.querySelector("#mic-test-btn");
    const status = root.querySelector("#mic-status");
    const bar = root.querySelector("#mic-level");
    let stream = null;
    let meter = null;
    let busy = false;
    const setStatus = (html, tone = "") => { status.innerHTML = html; status.className = `mic-status ${tone}`; };
    if (!micSupported()) {
      setStatus("This browser cannot record audio. Please use a recent Chrome, Edge, Firefox or Safari.", "is-bad");
      btn.disabled = true;
      return () => {};
    }
    btn.addEventListener("click", async () => {
      if (busy) return;
      busy = true;
      btn.disabled = true;
      try {
        if (!stream) {
          stream = await openMic();
          meter = new LevelMeter(stream, (l) => { bar.style.width = `${Math.round(l * 100)}%`; });
        }
        setStatus(`<span class="audio-live-dot" aria-hidden="true"></span> Say a sentence now – we are recording 4 seconds…`);
        const rec = new AnswerRecorder(stream, pickMime());
        meter.peak = 0;
        rec.start();
        await new Promise((r) => setTimeout(r, 4000));
        const peak = meter.ctx ? meter.peak : 1;
        const { blob } = await rec.stop();
        setStatus("Playing it back…");
        const audio = new Audio(URL.createObjectURL(blob));
        await new Promise((resolve) => {
          audio.onended = resolve;
          audio.onerror = resolve;
          audio.play().catch(resolve);
        });
        URL.revokeObjectURL(audio.src);
        setStatus(peak < 0.12
          ? "We could hardly hear you. Move closer to the microphone or check that it is not muted, then test again."
          : "✓ Your microphone works. If the playback was clear, you are ready.", peak < 0.12 ? "is-bad" : "is-ok");
        btn.textContent = "Test again";
      } catch (err) {
        setStatus(esc(micErrorMessage(err)), "is-bad");
      } finally {
        busy = false;
        btn.disabled = false;
      }
    });
    return () => {
      if (meter) meter.stop();
      stopStream(stream);
    };
  }

  /* ====================================================================
     Recordings, results and the examiner's marking
     ==================================================================== */
  function recordingHTML(rec) {
    if (!rec) return `<p class="speak-no-answer">No answer recorded.</p>`;
    return `<div class="rec-row"><audio controls preload="none" class="speak-audio" src="/api/speaking/recordings/${esc(rec.id)}"></audio>
      <span class="rec-len">${Math.round(rec.duration || 0)} s</span></div>`;
  }

  function submissionHTML(sub, opts = {}) {
    if (!sub || !sub.parts) return "";
    if (sub.recordingsDeleted) {
      return `<div class="notice notice-info"><strong>The recordings have been deleted.</strong>
        <span>Speaking recordings are kept for ${sub.keepDays} days.</span></div>`;
    }
    return sub.parts.map((p) => `
      <details class="fold speak-fold" ${opts.open ? "open" : ""}>
        <summary>Part ${p.partNumber}: ${esc(p.title)} · ${p.questions.filter((q) => q.recording).length} of ${p.questions.length} answered</summary>
        <div class="speak-answers">
          ${p.cueCard ? `<div class="cue-card small">${`<p class="cue-topic">${esc(p.cueCard.topic)}</p><p>You should say:</p>
            <ul>${p.cueCard.points.map((x) => `<li>${esc(x)}</li>`).join("")}</ul><p>${esc(p.cueCard.explain || "")}</p>`}</div>
            ${sub.notes ? `<div class="speak-notes-view"><strong>${opts.examiner ? "Candidate's notes" : "Your notes"}</strong><p>${U.richText(sub.notes)}</p></div>` : ""}` : ""}
          <ol class="speak-answer-list">
            ${p.questions.map((q) => `
              <li><p class="speak-answer-q">${q.type === "long_turn" ? "<strong>Long turn</strong> (up to 2 minutes)" : esc(q.text)}</p>
                ${recordingHTML(q.recording)}</li>`).join("")}
          </ol>
        </div>
      </details>`).join("");
  }

  function resultHTML(result) {
    const P = Results.parts;
    return `
      ${result.comment ? `<div class="examiner-comment"><h3>Message from your examiner</h3><p>${esc(result.comment)}</p></div>` : ""}
      <section class="task-result">
        ${result.summary ? `<p class="lead-text">${esc(result.summary)}</p>` : ""}
        ${P.criteriaHTML(result)}
        <div class="feedback-columns">${P.listBlock("What you did well", result.strengths, "good")}${P.listBlock("How to improve", result.improvements, "improve")}</div>
      </section>`;
  }

  function selfCheckHTML() {
    return `
      <section class="speak-selfcheck">
        <h2 class="section-title">Check yourself while you listen</h2>
        <p class="muted-text">Examiners give a band from 0 to 9 for each of these four criteria. Your Speaking band is their average.</p>
        <div class="criteria-grid">${CRITERIA.map(([, label, q]) => `
          <div class="criterion-card"><div class="criterion-head"><span>${esc(label)}</span></div><p>${esc(q)}</p></div>`).join("")}</div>
        <ul class="plan-points speak-tips">
          <li>Part 1: give a direct answer, then one reason or example. Two to four sentences is enough.</li>
          <li>Part 2: use your notes to cover every point on the card and keep talking until the examiner stops you.</li>
          <li>Part 3: give your opinion, explain why, and compare different views or situations.</li>
        </ul>
      </section>`;
  }

  async function renderResult(main, id) {
    document.title = "Your Speaking test";
    main.innerHTML = `<section class="page"><p class="muted-text">Loading…</p></section>`;
    let sub;
    try {
      ({ submission: sub } = await U.api(`/api/speaking/submissions/${encodeURIComponent(id)}`));
    } catch (err) {
      main.innerHTML = `<section class="page"><h1>Speaking test not found</h1><p>${esc(err.message)}</p>
        ${err.status === 401 ? `<button type="button" class="btn-primary" data-action="signin">Sign in</button>` : ""}</section>`;
      return;
    }
    const b = await Account.billing().catch(() => ({ prices: {} }));
    const check = sub.check;
    const offer = check
      ? `<div class="notice ${check.status === "completed" ? "notice-success" : "notice-info"}">
          <strong>${check.status === "completed" ? `Your examiner's band: ${IeltsScoring.formatBand(check.overallBand)}` : "An examiner is marking this test."}</strong>
          <span>${check.status === "completed" ? "See the feedback on every criterion." : "Most checks are finished within 48 hours."}
            <a href="#/check/${check.id}">Open the check</a></span></div>`
      : sub.recordingsDeleted ? "" : `
        <div class="examiner-offer speak-offer">
          <div>
            <h2>Get your Speaking band from an examiner</h2>
            <p>An examiner listens to your answers and gives you a band for each of the four criteria, with personal feedback
              on what to improve. You choose the examiner by rating and reviews.</p>
          </div>
          <div class="offer-action">
            ${b.prices.speaking_check ? `<div class="offer-price">${esc(Account.money(b.prices.speaking_check))}</div>` : ""}
            <a class="btn-primary btn-lg" href="#/examiners?kind=speaking&submission=${Number(sub.id)}">Choose an examiner</a>
          </div>
        </div>`;
    main.innerHTML = `
      <section class="results-page speaking-results">
        <div class="results-head">
          <div>
            <div class="eyebrow">Speaking</div>
            <h1>${esc(sub.title)}</h1>
            <p class="muted-text">${esc(U.formatDate(sub.completedAt || sub.createdAt))} · ${sub.answered} of ${sub.totalQuestions} questions answered
              ${sub.timeSpentSeconds ? ` · ${esc(U.formatDuration(sub.timeSpentSeconds))}` : ""}${sub.mode === "practice" ? " · practice" : ""}</p>
          </div>
          <div class="results-actions"><button type="button" class="btn-secondary" data-action="start" data-test="${esc(sub.testId)}" data-mode="${sub.mode === "practice" ? "practice" : "exam"}">Take it again</button></div>
        </div>
        ${sub.status !== "completed" ? `<div class="notice notice-warn"><strong>This test was not finished.</strong><span>You can listen to the answers you recorded.</span></div>` : ""}
        ${offer}
        <h2 class="section-title">Listen to your answers</h2>
        <p class="muted-text section-sub">Only you${check ? " and your examiner" : ""} can play these recordings. They are kept for ${sub.keepDays} days.</p>
        ${submissionHTML(sub, { open: true })}
        ${selfCheckHTML()}
      </section>`;
  }

  /** The examiner's marking form for a Speaking check (four criteria, like the public descriptors). */
  function markForm(form, check, helpers) {
    const draftKey = `mockexam:mark:${check.id}`;
    const draft = U.store.get(draftKey, null) || {};
    const crit = (k, f, fallback = "") => ((draft.criteria || {})[k] || {})[f] ?? fallback;
    const bandOptions = (sel) => `<option value="">–</option>${[9, 8, 7, 6, 5, 4, 3, 2, 1, 0].map((v) =>
      `<option value="${v}" ${String(sel) === String(v) ? "selected" : ""}>${v}</option>`).join("")}`;
    form.innerHTML = `
      <h2>Your marks</h2>
      <p class="muted-text small-text">Listen to every answer, then give each criterion a whole band. The overall band is the
        average, rounded to the nearest half band. Your draft is saved in this browser.</p>
      <fieldset class="mark-task">
        <legend>Speaking <span class="mark-band" id="mark-overall-head">–</span></legend>
        ${CRITERIA.map(([k, label]) => `
          <div class="mark-crit">
            <label for="b-${k}">${esc(label)}</label>
            <select id="b-${k}" data-band-of="${k}">${bandOptions(crit(k, "band"))}</select>
            <textarea data-feedback-of="${k}" rows="2" maxlength="1500" placeholder="Feedback on this criterion">${esc(crit(k, "feedback"))}</textarea>
          </div>`).join("")}
        <label>Summary <textarea data-field="summary" rows="2" maxlength="1500">${esc(draft.summary || "")}</textarea></label>
        <label>What the candidate did well <span class="muted-text">(one point per line)</span>
          <textarea data-field="strengths" rows="3">${esc([].concat(draft.strengths || []).join("\n"))}</textarea></label>
        <label>How to improve <span class="muted-text">(one point per line)</span>
          <textarea data-field="improvements" rows="3">${esc([].concat(draft.improvements || []).join("\n"))}</textarea></label>
      </fieldset>
      <label>Message to the candidate <textarea id="mark-comment" rows="3" maxlength="4000">${esc(draft.comment || "")}</textarea></label>
      <div class="mark-total">Overall speaking band: <strong id="mark-overall">–</strong></div>
      <p class="form-error" role="alert" hidden></p>
      <button type="submit" class="btn-primary btn-lg">Send marks to the candidate</button>`;

    const lines = (f) => form.querySelector(`[data-field="${f}"]`).value.split("\n").map((s) => s.trim()).filter(Boolean);
    const collect = () => {
      const criteria = {};
      CRITERIA.forEach(([k]) => {
        criteria[k] = { band: form.querySelector(`[data-band-of="${k}"]`).value, feedback: form.querySelector(`[data-feedback-of="${k}"]`).value };
      });
      return {
        criteria, summary: form.querySelector('[data-field="summary"]').value,
        strengths: lines("strengths"), improvements: lines("improvements"), comment: form.querySelector("#mark-comment").value,
      };
    };
    const update = () => {
      const vals = Object.values(collect().criteria).map((c) => c.band).filter((v) => v !== "").map(Number);
      const band = vals.length === 4 ? helpers.roundHalf(vals.reduce((a, v) => a + v, 0) / 4) : null;
      const text = band === null ? "–" : IeltsScoring.formatBand(band);
      form.querySelector("#mark-overall").textContent = text;
      form.querySelector("#mark-overall-head").textContent = band === null ? "–" : `Band ${text}`;
    };
    let timer = null;
    const save = () => {
      clearTimeout(timer);
      timer = setTimeout(() => U.store.set(draftKey, collect()), 300);
      update();
    };
    form.addEventListener("input", save);
    form.addEventListener("change", save);
    update();
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const result = collect();
      const err = form.querySelector(".form-error");
      if (Object.values(result.criteria).some((c) => c.band === "")) {
        err.textContent = "Give a band for every criterion.";
        err.hidden = false;
        return;
      }
      err.hidden = true;
      const ok = await U.modal({
        title: "Send the marks?",
        bodyHTML: "<p>The candidate will see your bands and feedback straight away. You cannot change them afterwards.</p>",
        buttons: [{ label: "Keep editing", className: "btn-secondary", value: false }, { label: "Send", className: "btn-primary", value: true }],
      });
      if (!ok) return;
      try {
        await U.api(`/api/examiner/checks/${check.id}/result`, { method: "POST", body: JSON.stringify({ result }) });
        U.store.remove(draftKey);
        U.toast("Marks sent. Thank you!");
        location.hash = "#/examiner";
      } catch (e2) {
        err.textContent = e2.message;
        err.hidden = false;
      }
    });
  }

  window.SpeakingExam = SpeakingExam;
  window.Speaking = {
    CRITERIA, bindMicCheck, renderResult, submissionHTML, resultHTML, markForm, fixWebmDuration, micSupported,
  };
})();
