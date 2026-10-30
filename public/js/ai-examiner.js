/**
 * The Speaking test with the AI examiner.
 *
 * AiSpeakingExam        – a face-to-face Speaking test: an animated examiner asks every
 *                         question in their own voice (lips moving with the words), listens,
 *                         and moves on when the candidate stops talking, as a real examiner
 *                         does. It never answers. Each answer is recorded as 16 kHz WAV and
 *                         uploaded; when the test ends the server's AI examiner rates it.
 * ExaminerFace          – the examiner: an SVG face that blinks, looks at you, nods while you
 *                         talk, looks down at the notes while you prepare, and lip-syncs.
 * MicCapture            – microphone samples to WAV, and a voice-activity detector that knows
 *                         when the candidate is speaking, pausing or has finished.
 * AiExaminer.mountReview() – the AI examiner's report on the results page.
 */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (v) => U.escapeHtml(v);
  const tr = (key, vars) => window.t(key, vars);
  const S = window.Speaking;
  const CANCELLED = S.CANCELLED;
  const RATE = 16000; // what the recordings are sent at
  const MAX_SECONDS = 125; // the upload limit is 4 MB, about 131 s of 16 kHz WAV
  const reducedMotion = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ====================================================================
     The examiner: a glowing orb with two eyes
     ==================================================================== */
  const BOT_SVG = `
    <svg viewBox="0 0 400 400" class="bot-svg" role="img" aria-hidden="true" focusable="false">
      <defs>
        <radialGradient id="bot-skin" cx="38%" cy="32%" r="75%">
          <stop offset="0" stop-color="#ff9a52"/><stop offset="0.55" stop-color="#ff6b0a"/><stop offset="1" stop-color="#e65300"/>
        </radialGradient>
        <radialGradient id="bot-aura" cx="50%" cy="50%" r="50%">
          <stop offset="0.45" stop-color="#ff6b0a" stop-opacity="0.32"/><stop offset="0.75" stop-color="#ff6b0a" stop-opacity="0.12"/>
          <stop offset="1" stop-color="#ff6b0a" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <circle class="bot-aura" cx="200" cy="200" r="196" fill="url(#bot-aura)"/>
      <circle class="bot-halo" cx="200" cy="200" r="132" fill="#7a3510" opacity="0.55"/>
      <g class="bot-body">
        <circle cx="200" cy="200" r="96" fill="url(#bot-skin)"/>
        <ellipse cx="172" cy="160" rx="34" ry="20" fill="#fff" opacity="0.16"/>
        <g class="bot-eyes">
          <rect class="bot-eye" x="205" y="170" width="17" height="46" rx="8.5" fill="#1b1410"/>
          <rect class="bot-eye" x="238" y="168" width="17" height="46" rx="8.5" fill="#1b1410"/>
        </g>
      </g>
    </svg>`;

  /**
   * The examiner, drawn as a glowing orb with two eyes. It breathes and blinks, glances
   * around, glows and bounces with its own voice, watches you and pulses gently with
   * your voice while you talk, nods when you pause, and looks down while you prepare.
   * States: idle, speaking, listening, writing, thinking, done.
   */
  class ExaminerFace {
    constructor(host, examiner, opts = {}) {
      this.host = host;
      host.innerHTML = BOT_SVG;
      host.classList.add("bot");
      if (opts.mini) host.classList.add("bot-mini");
      this.svg = host.querySelector("svg");
      this.body = host.querySelector(".bot-body");
      this.halo = host.querySelector(".bot-halo");
      this.aura = host.querySelector(".bot-aura");
      this.eyes = host.querySelector(".bot-eyes");
      this.eyeRects = [...host.querySelectorAll(".bot-eye")];
      this.state = "idle";
      this.level = 0; // smoothed loudness that drives the glow
      this.voice = null; // () => { level, bright } of the examiner's own voice
      this.listen = null; // () => 0–1, the candidate's microphone
      this.gaze = { x: 0, y: 0, tx: 0, ty: 0, next: 0 };
      this.blinkAt = performance.now() + 1500;
      this.blinkUntil = 0;
      this.nodStart = -1e9;
      this.running = true;
      const tick = (now) => {
        if (!this.running) return;
        this.frame(now);
        this.raf = requestAnimationFrame(tick);
      };
      this.raf = requestAnimationFrame(tick);
    }

    setState(state) {
      this.state = state;
      this.host.dataset.state = state;
      this.gaze.next = 0;
    }

    nod() {
      if (!reducedMotion()) this.nodStart = performance.now();
    }

    frame(now) {
      const t = now / 1000;
      const calm = reducedMotion();
      const st = this.state;
      let target = 0;
      if (st === "speaking") target = this.voice ? this.voice().level : 0.35 + 0.3 * Math.abs(Math.sin(t * 7.3) * Math.sin(t * 2.9));
      else if (st === "listening" && this.listen) target = Math.min(1, this.listen()) * 0.45;
      this.level += (target - this.level) * (target > this.level ? 0.5 : 0.18);
      const lv = this.level;

      // Breathing, and growing with the voice.
      const breathe = calm ? 0 : Math.sin(t * 1.6) * 0.012;
      const grow = 1 + breathe + lv * (st === "speaking" ? 0.07 : 0.035);
      let bob = 0;
      if (!calm) {
        bob = Math.sin(t * 1.1) * 3;
        if (st === "speaking") bob += -lv * 6;
        const sinceNod = (now - this.nodStart) / 1000;
        if (sinceNod < 0.6) bob += Math.sin((sinceNod / 0.6) * Math.PI * 2) * 9 * (1 - sinceNod / 0.6);
      }
      this.body.setAttribute("transform", `translate(200 ${200 + bob}) scale(${grow.toFixed(4)}) translate(-200 -200)`);
      const halo = 1 + lv * 0.22 + (calm ? 0 : Math.sin(t * 1.6 + 0.6) * 0.015);
      this.halo.setAttribute("transform", `translate(200 ${200 + bob * 0.6}) scale(${halo.toFixed(4)}) translate(-200 -200)`);
      this.halo.setAttribute("opacity", (0.42 + lv * 0.4).toFixed(3));
      this.aura.setAttribute("opacity", (0.55 + lv * 0.45).toFixed(3));

      // Where it looks: off to the side when idle (as if thinking), at you when it speaks or
      // listens, down at the notes while you prepare.
      const g = this.gaze;
      if (now > g.next) {
        const roam = calm ? 0 : st === "speaking" ? 4 : st === "listening" ? 6 : 14;
        if (st === "writing") { g.tx = -28; g.ty = 22; } else if (st === "thinking") { g.tx = 4 + Math.random() * 10; g.ty = -16; } else if (st === "listening" || st === "speaking" || st === "done") {
          g.tx = -18 + (Math.random() * 2 - 1) * roam; g.ty = 4 + (Math.random() * 2 - 1) * roam * 0.4;
        } else { g.tx = (Math.random() * 2 - 1) * roam; g.ty = (Math.random() * 2 - 1) * roam * 0.5; }
        g.next = now + 700 + Math.random() * 2400;
      }
      g.x += (g.tx - g.x) * 0.12;
      g.y += (g.ty - g.y) * 0.12;

      // Blinks every few seconds, sometimes twice; squints when pleased at the end.
      if (now > this.blinkAt) {
        this.blinkUntil = now + 120;
        this.blinkAt = now + (Math.random() < 0.18 ? 240 : 2200 + Math.random() * 3600);
      }
      let open = now < this.blinkUntil ? 0.1 : st === "writing" ? 0.45 : st === "done" ? 0.32 : 1;
      if (st === "speaking") open *= 1 - lv * 0.25;
      const eyeBounce = st === "speaking" ? -lv * 7 : 0;
      this.eyes.setAttribute("transform", `translate(${g.x.toFixed(2)} ${(g.y + eyeBounce).toFixed(2)})`);
      this.eyeRects.forEach((r) => {
        const cy = Number(r.getAttribute("y")) + 23;
        const cx = Number(r.getAttribute("x")) + 8.5;
        r.setAttribute("transform", `translate(${cx} ${cy}) scale(1 ${open.toFixed(3)}) translate(${-cx} ${-cy})`);
      });
    }

    destroy() {
      this.running = false;
      cancelAnimationFrame(this.raf);
    }
  }

  /* ====================================================================
     The examiner's voice
     ==================================================================== */
  /** Plays the examiner's recorded clips through Web Audio, so the face can follow them. */
  class Voice {
    constructor(ctx) {
      this.ctx = ctx;
      this.cache = new Map();
      this.analyser = ctx.createAnalyser();
      this.analyser.fftSize = 1024;
      this.analyser.smoothingTimeConstant = 0.3;
      this.gain = ctx.createGain();
      this.gain.gain.value = Math.min(1, Math.max(0, Number(U.store.get("mockexam:volume", 0.9)) || 0.9));
      this.analyser.connect(this.gain);
      this.gain.connect(ctx.destination);
      this.time = new Float32Array(this.analyser.fftSize);
      this.freq = new Uint8Array(this.analyser.frequencyBinCount);
      this.source = null;
    }

    load(src) {
      if (!src) return Promise.reject(new Error("no audio"));
      if (!this.cache.has(src)) {
        const job = fetch(src, { credentials: "same-origin" })
          .then((r) => { if (!r.ok) throw new Error(`audio ${r.status}`); return r.arrayBuffer(); })
          .then((buf) => new Promise((resolve, reject) => this.ctx.decodeAudioData(buf, resolve, reject)));
        job.catch(() => this.cache.delete(src));
        this.cache.set(src, job);
      }
      return this.cache.get(src);
    }

    /** Play a clip from `offset` seconds; calls done() at the end. Returns a function that stops it. */
    play(buffer, offset, done) {
      this.stop();
      const node = this.ctx.createBufferSource();
      node.buffer = buffer;
      node.connect(this.analyser);
      node.onended = () => { if (this.source === node) this.source = null; done(); };
      this.source = node;
      node.start(0, Math.max(0, Math.min(offset || 0, buffer.duration - 0.05)));
      return () => { node.onended = null; try { node.stop(); } catch (e) { /* already stopped */ } if (this.source === node) this.source = null; };
    }

    stop() {
      if (this.source) {
        this.source.onended = null;
        try { this.source.stop(); } catch (e) { /* already stopped */ }
        this.source = null;
      }
    }

    /** Loudness (0–1) and brightness (0–1, more for "ee" and "s") of what is playing now, for the lips. */
    reading() {
      this.analyser.getFloatTimeDomainData(this.time);
      let sum = 0;
      for (let i = 0; i < this.time.length; i++) sum += this.time[i] * this.time[i];
      const db = 20 * Math.log10(Math.sqrt(sum / this.time.length) || 1e-8);
      const level = Math.max(0, Math.min(1, (db + 46) / 30));
      this.analyser.getByteFrequencyData(this.freq);
      const hz = this.ctx.sampleRate / this.analyser.fftSize;
      let low = 0;
      let high = 0;
      for (let i = Math.floor(150 / hz); i < Math.floor(5000 / hz); i++) {
        if (i * hz < 1500) low += this.freq[i]; else high += this.freq[i];
      }
      const bright = low + high ? Math.min(1, (high / (low + high)) * 2.2) : 0.5;
      return { level: level < 0.06 ? 0 : level, bright };
    }
  }

  /** The sentences the clip was voiced in, as scripts/build_speaking_audio.py splits them. */
  function clipSentences(text) {
    const parts = [];
    let current = "";
    text.replace(/\? /g, "?\n").replace(/\. /g, ".\n").replace(/! /g, "!\n").split("\n").forEach((chunk) => {
      current = `${current} ${chunk}`.trim();
      if (current.length > 25) { parts.push(current); current = ""; }
    });
    if (current) parts.push(current);
    return parts;
  }

  /**
   * Where the question itself starts in a clip that begins with an introduction
   * ("Now let's talk about weekends. What do you usually do...?"). Each sentence
   * was voiced separately with a short silence between, so the question starts
   * after the silence that ends the introduction. 0 when that cannot be found.
   */
  function questionOffset(buffer, say, text) {
    const s = String(say || "").replace(/\s+/g, " ").trim();
    const q = String(text || "").replace(/\s+/g, " ").trim();
    if (!s || !q || s === q || !s.endsWith(q)) return 0;
    const parts = clipSentences(s);
    let first = -1;
    for (let i = 1; i < parts.length; i++) {
      if (parts.slice(i).join(" ") === q) { first = i; break; }
    }
    if (first < 1) return 0;
    const data = buffer.getChannelData(0);
    const frame = Math.round(buffer.sampleRate * 0.01);
    const loud = [];
    let peak = 0;
    for (let i = 0; i + frame <= data.length; i += frame) {
      let sum = 0;
      for (let j = i; j < i + frame; j++) sum += data[j] * data[j];
      const v = Math.sqrt(sum / frame);
      loud.push(v);
      peak = Math.max(peak, v);
    }
    const gaps = []; // the middles of silences of 300 ms or more between words
    let start = -1;
    let spoken = false;
    loud.forEach((v, i) => {
      const quiet = v < peak * 0.04;
      if (quiet && start < 0) start = i;
      if (!quiet) {
        if (start >= 0 && spoken && i - start >= 30) gaps.push(((start + i) / 2) * 0.01);
        start = -1;
        spoken = true;
      }
    });
    return gaps.length >= first ? gaps[first - 1] : 0;
  }

  /* ====================================================================
     The microphone
     ==================================================================== */
  function wavBlob(chunks, length) {
    const buf = new ArrayBuffer(44 + length * 2);
    const v = new DataView(buf);
    const str = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    str(0, "RIFF"); v.setUint32(4, 36 + length * 2, true); str(8, "WAVE");
    str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, RATE, true); v.setUint32(28, RATE * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
    str(36, "data"); v.setUint32(40, length * 2, true);
    const out = new Int16Array(buf, 44, length);
    let at = 0;
    chunks.forEach((c) => { out.set(c, at); at += c.length; });
    return new Blob([buf], { type: "audio/wav" });
  }

  /**
   * Turns the microphone into 16 kHz WAV answers and tracks the voice:
   * `voiced` (seconds of speech in this answer), `quiet` (seconds since the last
   * speech) and `level` (0–1, for the meter).
   */
  class MicCapture {
    constructor(ctx, stream) {
      this.ctx = ctx;
      this.stream = stream;
      this.level = 0;
      this.floor = -62;
      this.recording = false;
      this.paused = false;
      this.onVoiceEnd = null;
    }

    async init() {
      this.source = this.ctx.createMediaStreamSource(this.stream);
      this.mute = this.ctx.createGain();
      this.mute.gain.value = 0;
      this.mute.connect(this.ctx.destination);
      try {
        await this.ctx.audioWorklet.addModule(U.assetUrl("js/pcm-worklet.js"));
        this.node = new AudioWorkletNode(this.ctx, "pcm-capture");
        this.node.port.onmessage = (e) => this.feed(e.data);
      } catch (e) {
        // Older browsers: the deprecated ScriptProcessor does the same job.
        this.node = this.ctx.createScriptProcessor(4096, 1, 1);
        this.node.onaudioprocess = (e) => this.feed(new Float32Array(e.inputBuffer.getChannelData(0)));
      }
      this.source.connect(this.node);
      this.node.connect(this.mute);
    }

    begin() {
      this.chunks = [];
      this.length = 0;
      this.voiced = 0;
      this.quiet = 0;
      this.run = 0; // consecutive loud blocks
      this.carry = 0;
      this.carryN = 0;
      this.next = this.ctx.sampleRate / RATE;
      this.pos = 0;
      this.paused = false;
      this.recording = true;
    }

    get seconds() {
      return this.recording ? this.length / RATE : 0;
    }

    pause(on) {
      this.paused = on;
      if (!on) this.quiet = 0;
    }

    feed(block) {
      let sum = 0;
      for (let i = 0; i < block.length; i++) sum += block[i] * block[i];
      const db = 20 * Math.log10(Math.sqrt(sum / block.length) || 1e-8);
      this.level = Math.max(0, Math.min(1, (db + 58) / 46));
      if (!this.recording || this.paused) return;
      const secs = block.length / this.ctx.sampleRate;
      // The room's own noise sets the bar for speech: the floor follows quiet moments
      // (quickly down, slowly up) and never the voice itself.
      if (db < this.floor) this.floor += (db - this.floor) * 0.5;
      else if (db < this.floor + 10) this.floor += (db - this.floor) * 0.03;
      const loud = db > Math.max(this.floor + 12, -50);
      this.run = loud ? this.run + 1 : 0;
      if (this.run >= 2) {
        if (this.run === 2) this.voiced += secs; // the first block of a run counts too
        this.voiced += secs;
        this.quiet = 0;
      } else if (db < this.floor + 8 || !loud) {
        const before = this.quiet;
        this.quiet += secs;
        if (before < 0.9 && this.quiet >= 0.9 && this.voiced > 2.5 && this.onVoiceEnd) this.onVoiceEnd();
      }
      // Down to 16 kHz: average the samples that fall in each output sample.
      const ratio = this.ctx.sampleRate / RATE;
      const out = new Int16Array(Math.ceil(block.length / ratio) + 2);
      let n = 0;
      for (let i = 0; i < block.length; i++) {
        this.carry += block[i];
        this.carryN++;
        this.pos++;
        if (this.pos >= this.next) {
          const v = Math.max(-1, Math.min(1, this.carry / this.carryN));
          out[n++] = v < 0 ? v * 0x8000 : v * 0x7fff;
          this.carry = 0;
          this.carryN = 0;
          this.next += ratio;
        }
      }
      if (n) {
        this.chunks.push(out.subarray(0, n));
        this.length += n;
      }
    }

    finish() {
      this.recording = false;
      return { blob: wavBlob(this.chunks || [], this.length || 0), seconds: (this.length || 0) / RATE };
    }

    destroy() {
      this.recording = false;
      try { this.source.disconnect(); this.node.disconnect(); } catch (e) { /* already gone */ }
      if (this.node && this.node.port) this.node.port.onmessage = null;
    }
  }

  /* ====================================================================
     The test
     ==================================================================== */
  class AiSpeakingExam extends SpeakingExam {
    mount() {
      $("exam-screen").classList.add("speaking-mode", "ai-speaking");
      this.mountShell(`${this.test.shortTitle || this.test.title} · Speaking`, "Speaking", "Speaking");
      $("exam-question-strip").hidden = true;
      $("exam-review-wrap").hidden = true;
      $("btn-prev-q").hidden = true;
      $("btn-next-q").hidden = true;
      $("btn-submit-exam").textContent = "End test";
      const ex = this.test.examiner || {};
      this.examinerName = ex.name || "Examiner";
      $("exam-pane-right").innerHTML = `
        <div class="ai-room" id="ai-room">
          <div class="ai-top">
            <div class="ai-part"><span class="speak-part" id="sp-part">Speaking test</span> <span class="speak-part-title" id="sp-part-title"></span></div>
            <div class="ai-rec" id="ai-rec" hidden><span class="audio-live-dot" aria-hidden="true"></span>Recording</div>
          </div>
          <div class="ai-stage">
            <figure class="ai-tile" id="sp-examiner">
              <div class="ai-face" id="ai-face" data-state="idle"></div>
              <figcaption class="ai-nameplate"><strong>${esc(this.examinerName)}</strong><span id="sp-examiner-state">Examiner</span></figcaption>
            </figure>
            <div class="ai-side" id="sp-question"></div>
          </div>
          <div class="ai-you" id="ai-you">
            <span class="ai-you-dot" aria-hidden="true">${esc((this.candidateName || "Y")[0])}</span>
            <span class="ai-bars" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></span>
            <span class="ai-you-state" id="ai-you-state">${esc(this.candidateName)}</span>
          </div>
          <div class="ai-controls" id="ai-controls"></div>
          <div class="speak-panel ai-panel" id="sp-panel" aria-live="polite"></div>
          <div class="speak-saving" id="sp-saving"></div>
        </div>`;
      this.face = new ExaminerFace($("ai-face"), ex);
      this.captions = false;
      this.renderPartTabs();
      this.run();
    }

    /** Start (or resume) the test on the server: rated by the AI examiner when the site has one. */
    async ensureSubmission() {
      if (this.submissionId) {
        try {
          const { submission } = await U.api(`/api/speaking/submissions/${this.submissionId}`);
          if (submission.status === "recording") {
            this.rated = submission.mode === "ai";
            this.uploader = new S.Uploader(this.submissionId, () => this.renderSaving());
            submission.parts.forEach((p) => p.questions.forEach((q) => { if (q.recording) this.uploader.state[q.key] = "done"; }));
            this.renderSaving();
            return;
          }
        } catch (e) { /* start a new attempt below */ }
        this.submissionId = null;
        this.step = 0;
      }
      const wantAi = Boolean(window.app && window.app.config && window.app.config.aiSpeaking);
      const res = await U.api(`/api/speaking/${encodeURIComponent(this.test.id)}/start`, {
        method: "POST", body: JSON.stringify({ candidateName: this.candidateName, mode: wantAi ? "ai" : "exam", fallback: true }),
      });
      this.rated = res.mode === "ai";
      if (res.notice) U.toast(res.notice, "warn");
      this.submissionId = res.submissionId;
      this.uploader = new S.Uploader(this.submissionId, () => this.renderSaving());
      this.saveProgress();
    }

    helpHTML() {
      return `
        <p><strong>How the Speaking test works</strong></p>
        <ul class="help-list">
          <li>${esc(this.examinerName)} asks every question out loud, as in the real test. Answer by speaking; you do not need to press anything.</li>
          <li>When you stop talking, the examiner moves on to the next question. If you need a moment to think, that is fine: the examiner waits a few seconds.</li>
          <li><strong>Repeat</strong> asks the examiner to say the question again (once per question, in Parts 1 and 3).</li>
          <li>Part 2: one minute to prepare (you can type notes), then up to two minutes to talk. The examiner stops you at two minutes.</li>
          <li>The examiner does not answer you or comment, just like a real examiner.</li>
          ${this.rated ? "<li>At the end, the AI examiner listens to your whole test and gives you an estimated band for each criterion, with feedback.</li>" : "<li>Your answers are saved to your account, so you can listen to them afterwards.</li>"}
        </ul>`;
    }

    setExaminer(state) {
      if (!this.face) return;
      if (this.finishing && state === "idle") return; // keep "reviewing" while the answers are saved
      this.face.setState(["speaking", "listening", "writing", "thinking", "done"].includes(state) ? state : "idle");
      const label = { speaking: "Speaking…", listening: "Listening to you", writing: "Timing your preparation", thinking: "Reviewing your answers" }[state] || "Examiner";
      const el = $("sp-examiner-state");
      if (el) el.textContent = label;
    }

    status(text) {
      this.panel(text ? `<p class="speak-status ai-status">${esc(text)}</p>` : "");
    }

    controls(html) {
      const el = $("ai-controls");
      if (el) el.innerHTML = html;
    }

    /* The flow ---------------------------------------------------------------- */
    async run() {
      try {
        this.status(`Connecting you to ${this.examinerName}…`);
        await this.ensureSubmission();
        await this.ensureMic();
        await this.ensureAudio();
        const first = this.steps[this.step];
        if (first) await this.voice.load(first.q.audio && first.q.audio.src).catch(() => {});
        this.status("");
        this.face.setState("idle");
        await this.sleep(1200); // the examiner looks up and is ready
        while (this.step < this.steps.length && !this.finishing) {
          await this.runStep(this.steps[this.step]);
          this.step++;
          this.saveProgress();
        }
        if (this.finishing) return;
        this.controls("");
        $("sp-question").innerHTML = "";
        if (!this.endingEarly) await this.say(this.test.prompts && this.test.prompts.end);
        this.setExaminer(this.rated ? "thinking" : "done");
        this.status(this.rated ? "That is the end of the test. Your examiner will now rate your answers." : "That is the end of the test.");
        await this.finishTest();
      } catch (err) {
        if (err === CANCELLED || this.cancelled) return;
        this.showFatal(err.message || String(err));
      }
    }

    async ensureMic() {
      if (!S.micSupported()) throw new Error(S.micErrorMessage());
      for (;;) {
        try {
          this.stream = await S.openMic();
          break;
        } catch (err) {
          this.panel(`
            <div class="speak-error"><strong>We need your microphone</strong><p>${esc(S.micErrorMessage(err))}</p>
              <button type="button" class="btn-primary" id="sp-mic-retry">Try again</button></div>`);
          await this.wait((done) => {
            const b = $("sp-mic-retry");
            b.addEventListener("click", done);
            return () => b.removeEventListener("click", done);
          });
          this.status("Starting the microphone…");
        }
      }
      if (this.cancelled) { S.stopStream(this.stream); throw CANCELLED; }
    }

    async ensureAudio() {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) throw new Error("This browser cannot play the examiner's voice. Please use a recent Chrome, Edge, Firefox or Safari.");
      this.actx = new Ctx();
      if (this.actx.state === "suspended") {
        await this.actx.resume().catch(() => {});
        if (this.actx.state === "suspended") {
          // Some browsers want a tap before any sound can play.
          this.panel(`<button type="button" class="btn-primary btn-lg" id="ai-go">Start speaking with ${esc(this.examinerName)}</button>`);
          await this.wait((done) => {
            const b = $("ai-go");
            const h = () => this.actx.resume().then(done, done);
            b.addEventListener("click", h);
            return () => b.removeEventListener("click", h);
          });
        }
      }
      this.voice = new Voice(this.actx);
      this.face.voice = () => this.voice.reading();
      this.face.listen = () => (this.capture && this.capture.recording ? this.capture.level : 0);
      this.capture = new MicCapture(this.actx, this.stream);
      await this.capture.init();
      this.capture.onVoiceEnd = () => { if (this.face && this.face.state === "listening") this.face.nod(); };
      const bars = [...document.querySelectorAll("#ai-you .ai-bars i")];
      this.meterTimer = setInterval(() => {
        const l = this.capture.level;
        bars.forEach((b, i) => { b.style.transform = `scaleY(${Math.max(0.15, Math.min(1, l * 1.6 - Math.abs(i - 3) * 0.12))})`; });
        $("ai-you").classList.toggle("is-talking", this.capture.recording && l > 0.32);
      }, 90);
    }

    phrase(name) {
      const voice = (this.test.examiner && this.test.examiner.voice) || "";
      return voice ? { src: `audio/examiners/${voice}/${name}.mp3` } : null;
    }

    /** The examiner says a clip. Resolves when it has finished (or could not be played). */
    async say(audio, offset = 0) {
      if (!audio || !audio.src) return;
      let buffer;
      try {
        buffer = await this.voice.load(audio.src);
      } catch (e) {
        const step = this.steps[this.step];
        if (step) this.showCaption(step, true);
        U.toast("The examiner's voice could not be played. Read the question instead.", "warn");
        return;
      }
      if (this.actx.state === "suspended") await this.actx.resume().catch(() => {});
      this.setExaminer("speaking");
      await this.wait((done) => this.voice.play(buffer, offset, done));
      this.setExaminer("idle");
    }

    showStep(step) {
      const { part } = step;
      $("sp-part").textContent = `Part ${part.partNumber}`;
      $("sp-part-title").textContent = part.title || "";
      this.renderPartTabs();
      this.showCaption(step, this.captions);
    }

    showCaption(step, visible) {
      const { part, q } = step;
      const box = $("sp-question");
      if (!box) return;
      if (q.type === "long_turn") {
        box.innerHTML = this.cueCardHTML(part.cueCard);
        return;
      }
      box.innerHTML = visible ? `<p class="ai-caption">${esc(q.text)}</p>` : "";
    }

    preloadAfter(index) {
      for (let i = index + 1; i < Math.min(index + 3, this.steps.length); i++) {
        const a = this.steps[i].q.audio;
        if (a && a.src) this.voice.load(a.src).catch(() => {});
      }
    }

    async runStep(step) {
      const { part, q } = step;
      this.showStep(step);
      this.controls("");
      if (step.index === 0 && step !== this.steps[0]) await this.sleep(900); // a new part
      this.preloadAfter(this.step);
      await this.say(q.audio);
      if (q.type === "long_turn") {
        await this.prepareLongTurn(part, q);
        await this.say(this.test.prompts && this.test.prompts["p2-start"]);
      }
      await this.listenAnswer(step);
    }

    async prepareLongTurn(part, q) {
      const total = q.prepSeconds || 60;
      this.setExaminer("writing");
      $("sp-question").innerHTML = `
        ${this.cueCardHTML(part.cueCard)}
        <div class="ai-prep">
          <div class="speak-timer-row"><strong>Preparation</strong><span class="speak-countdown" id="sp-prep-left">${U.formatClock(total)}</span></div>
          <div class="speak-bar"><span id="sp-prep-bar"></span></div>
          <label for="sp-notes" class="speak-notes-label">Your notes</label>
          <textarea id="sp-notes" class="speak-notes" rows="4" maxlength="2000" spellcheck="false"
            placeholder="A few key words for each point…">${esc(this.notes)}</textarea>
        </div>`;
      this.controls(`<button type="button" class="btn-secondary" id="sp-prep-done">I am ready to speak</button>`);
      this.status("You have one minute to prepare.");
      const notes = $("sp-notes");
      this.on(notes, "input", () => { this.notes = notes.value; this.saveProgressSoon(); });
      notes.focus();
      let left = total;
      await this.wait((done) => {
        const t = setInterval(() => {
          left--;
          const l = $("sp-prep-left");
          if (l) l.textContent = U.formatClock(Math.max(0, left));
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
      this.controls("");
      this.status("");
      this.setExaminer("idle");
      $("sp-question").innerHTML = this.cueCardHTML(part.cueCard) + (this.notes.trim()
        ? `<div class="speak-notes-view"><strong>Your notes</strong><p>${U.richText(this.notes)}</p></div>` : "");
    }

    /**
     * Record one answer and decide, like an examiner, when it is over: after a few
     * seconds of silence once the candidate has spoken, at the time limit, or when
     * the candidate says nothing at all (after one repetition of the question).
     */
    async listenAnswer(step) {
      const { part, q } = step;
      const longTurn = q.type === "long_turn";
      const partNo = part.partNumber;
      const limit = longTurn ? 120 : partNo === 3 ? Math.max(q.answerSeconds || 60, 60) + 15 : Math.max(q.answerSeconds || 30, 30) + 10;
      const endAfter = longTurn ? 6 : partNo === 3 ? 3.2 : 2.6;
      const noAnswer = longTurn ? 15 : partNo === 3 ? 10 : 8;
      const canRepeat = !longTurn;
      let repeated = false;
      let encouraged = false;
      const cap = this.capture;
      cap.begin();
      $("ai-rec").hidden = false;
      this.setExaminer("listening");
      const renderControls = () => this.controls(`
        ${canRepeat && !repeated ? `<button type="button" class="btn-secondary" id="ai-repeat">Repeat the question</button>` : ""}
        ${!longTurn && !this.captions ? `<button type="button" class="btn-link" id="ai-caption">Show the question</button>` : ""}
        <button type="button" class="btn-link" id="ai-done">I have finished</button>
        ${longTurn ? `<span class="ai-clock" id="ai-clock">0:00 / 2:00</span>` : ""}`);
      renderControls();
      for (;;) {
        const action = await this.wait((done) => {
          const tick = setInterval(() => {
            const t = cap.seconds;
            const clock = $("ai-clock");
            if (clock) clock.textContent = `${U.formatClock(Math.floor(t))} / 2:00`;
            if (t >= Math.min(limit, MAX_SECONDS)) return done("time");
            if (cap.voiced < 0.6) {
              if (t >= noAnswer * (repeated ? 2 : 1)) done(canRepeat && !repeated ? "repeat" : "silent");
            } else if (longTurn && !encouraged && t < 60 && cap.quiet >= 5) {
              done("more");
            } else if (cap.quiet >= endAfter && (!longTurn || t >= 60 || encouraged)) {
              done("finished");
            }
          }, 100);
          const clicks = [["ai-repeat", "repeat"], ["ai-done", "finished"], ["ai-caption", "caption"]].map(([id, value]) => {
            const el = $(id);
            const h = () => done(value);
            if (el) el.addEventListener("click", h);
            return () => el && el.removeEventListener("click", h);
          });
          this.stopCurrent = () => done("finished");
          return () => { clearInterval(tick); clicks.forEach((c) => c()); this.stopCurrent = null; };
        }).catch((err) => { cap.finish(); $("ai-rec").hidden = true; throw err; });

        if (action === "caption") {
          this.captions = true;
          this.showCaption(step, true);
          renderControls();
          continue;
        }
        if (action === "repeat" || action === "more") {
          // The examiner speaks; that is not part of the answer.
          cap.pause(true);
          $("ai-rec").hidden = true;
          if (action === "repeat") {
            repeated = true;
            renderControls();
            let offset = 0;
            try { offset = questionOffset(await this.voice.load(q.audio.src), q.say, q.text); } catch (e) { /* from the start */ }
            await this.say(q.audio, offset);
          } else {
            encouraged = true;
            await this.say(this.phrase("more"));
          }
          cap.pause(false);
          $("ai-rec").hidden = false;
          this.setExaminer("listening");
          continue;
        }
        const { blob, seconds } = cap.finish();
        $("ai-rec").hidden = true;
        this.controls("");
        this.uploader.add(q.key, blob, seconds);
        // At the time limit the examiner politely stops you (Part 2's next question starts with "Thank you").
        if (action === "time" && !longTurn && !this.endingEarly) await this.say(this.phrase("thank-you"));
        else if (!this.endingEarly) await this.sleep(longTurn ? 500 : 350);
        return;
      }
    }

    interruptFlow() {
      if (this.voice) this.voice.stop();
      super.interruptFlow();
    }

    async finishTest() {
      this.controls("");
      if (this.face) this.face.setState(this.rated ? "thinking" : "done");
      return super.finishTest();
    }

    destroy() {
      clearInterval(this.meterTimer);
      if (this.voice) this.voice.stop();
      if (this.capture) this.capture.destroy();
      if (this.face) this.face.destroy();
      if (this.actx) this.actx.close().catch(() => {});
      $("exam-screen").classList.remove("ai-speaking");
      super.destroy();
    }
  }

  /* ====================================================================
     The report
     ==================================================================== */
  function fmtSeconds(s) {
    if (s === null || s === undefined) return "–";
    return s >= 60 ? U.formatClock(Math.round(s)) : `${Math.round(s)} s`;
  }

  function statsHTML(st) {
    const items = [
      [fmtSeconds(st.speakingTime), "Speaking time", `${st.answered} of ${st.questions} questions answered`],
      [st.wordsPerMinute ?? "–", "Words per minute", "Fluent speakers: about 110–170"],
      [st.fillersPerMinute ?? "–", "Fillers per minute", "“um”, “er”, “uh”: a few are natural"],
      [st.pauses2sPerMinute ?? "–", "Long pauses per minute", "Silences of 2 seconds or more"],
      [st.averageLatency !== null && st.averageLatency !== undefined ? `${st.averageLatency} s` : "–", "Time to start answering", "Average, after each question"],
      [st.longTurnSeconds !== null && st.longTurnSeconds !== undefined ? fmtSeconds(st.longTurnSeconds) : "–", "Part 2 long turn", "Aim for close to 2:00"],
    ];
    return `<div class="ai-stats">${items.map(([v, label, hint]) => `
      <div class="ai-stat"><strong>${esc(String(v))}</strong><span>${esc(label)}</span><small>${esc(hint)}</small></div>`).join("")}</div>`;
  }

  function pairsTable(rows, heads, keys) {
    if (!rows || !rows.length) return "";
    return `<div class="table-scroll"><table class="corrections-table">
      <thead><tr>${heads.map((h) => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((r) => `<tr>${keys.map((k, i) => `<td class="${i === 0 ? "corr-orig" : i === 1 ? "corr-new" : ""}">${esc(r[k])}</td>`).join("")}</tr>`).join("")}</tbody>
    </table></div>`;
  }

  /** A transcript with fillers and pauses made visible. */
  function transcriptHTML(text) {
    if (!text) return `<p class="ai-transcript is-empty">No speech was heard in this answer.</p>`;
    const html = esc(text)
      .replace(/\((long )?pause\)/g, (m, long) => `<span class="ai-pause${long ? " is-long" : ""}" title="${long ? "A pause of 3 seconds or more" : "A pause of about 1 second or more"}">${long ? "long pause" : "pause"}</span>`)
      .replace(/\b(um+|uh+|erm+|er+|hmm+|ah+)\b/gi, `<mark class="ai-filler">$1</mark>`)
      .replace(/\[(unclear|non-English)\]/g, `<span class="ai-unclear">$1</span>`);
    return `<p class="ai-transcript">${html}</p>`;
  }

  function answerExtrasHTML(answer) {
    if (!answer) return "";
    const s = answer.stats || {};
    const facts = [
      s.words !== undefined ? `${s.words} words` : "",
      s.speakingTime ? `${fmtSeconds(s.speakingTime)} of speech` : "",
      s.wordsPerMinute ? `${s.wordsPerMinute} words/min` : "",
      s.fillers ? `${s.fillers} filler${s.fillers === 1 ? "" : "s"}` : "",
      s.longestPause >= 2 ? `longest pause ${s.longestPause} s` : "",
    ].filter(Boolean).join(" · ");
    return `<div class="ai-answer">${transcriptHTML(answer.transcript)}${facts ? `<p class="ai-answer-facts">${esc(facts)}</p>` : ""}</div>`;
  }

  function doneHTML(r) {
    const P = Results.parts;
    const partNames = { 1: "Part 1", 2: "Part 2", 3: "Part 3" };
    return `
      <section class="ai-report" aria-labelledby="ai-report-title">
        <div class="ai-report-head">
          <div>
            <h2 id="ai-report-title" class="section-title">Your AI examiner's rating</h2>
            <p class="muted-text">An estimate from an AI examiner using the four public Speaking criteria. It is not an official IELTS result.</p>
          </div>
          <div class="ai-band"><span class="ai-band-val">${IeltsScoring.formatBand(r.overallBand)}</span><span class="ai-band-lbl">Estimated band</span></div>
        </div>
        ${r.summary ? `<p class="lead-text">${esc(r.summary)}</p>` : ""}
        ${P.criteriaHTML(r)}
        <div class="feedback-columns">${P.listBlock("What you did well", r.strengths, "good")}${P.listBlock("How to improve", r.improvements, "improve")}</div>
        ${r.stats ? `<h3 class="ai-sub">Your speaking in numbers</h3>${statsHTML(r.stats)}` : ""}
        ${r.parts && r.parts.length ? `<h3 class="ai-sub">Part by part</h3><dl class="ai-parts">${r.parts.map((p) => `<dt>${esc(partNames[p.part] || `Part ${p.part}`)}</dt><dd>${esc(p.comment)}</dd>`).join("")}</dl>` : ""}
        ${r.corrections && r.corrections.length ? `<h3 class="ai-sub">Grammar and word choice</h3>${pairsTable(r.corrections, ["You said", "Better", "Why"], ["original", "corrected", "explanation"])}` : ""}
        ${r.vocabulary && r.vocabulary.length ? `<h3 class="ai-sub">Words that would lift your band</h3>${pairsTable(r.vocabulary, ["You said", "Try", "Why"], ["original", "better", "why"])}` : ""}
        ${r.pronunciation && r.pronunciation.length ? `<h3 class="ai-sub">Pronunciation to practise</h3>
          <ul class="ai-pron">${r.pronunciation.map((p) => `<li><strong>${esc(p.word)}</strong> ${esc(p.tip)}</li>`).join("")}</ul>` : ""}
        <p class="muted-text ai-foot">Below, every answer has what the examiner heard, with fillers <mark class="ai-filler">um</mark> and <span class="ai-pause">pauses</span> marked.</p>
      </section>`;
  }

  function waitingHTML(r) {
    const total = r.total || 0;
    const done = Math.min(r.done || 0, total);
    const marking = r.stage === "marking";
    const pct = marking ? 92 : total ? Math.round(8 + (done / total) * 80) : 6;
    return `
      <section class="ai-report ai-waiting" aria-live="polite">
        <div class="spinner" aria-hidden="true"></div>
        <h2 class="section-title">Your examiner is rating your test</h2>
        <p class="muted-text">${marking ? "Deciding your band for each criterion…"
          : total ? `Listening to your answers: ${done} of ${total}…` : "Getting ready…"}</p>
        <div class="ai-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><span style="width:${pct}%"></span></div>
        <p class="muted-text small-text">This usually takes about a minute. You can stay on this page.</p>
      </section>`;
  }

  function errorHTML(r) {
    return `
      <div class="notice notice-warn ai-error"><strong>The AI examiner could not rate this test.</strong>
        <span>${esc(r.message || "Please try again.")}</span>
        ${r.canRetry ? `<button type="button" class="btn-secondary" id="ai-retry">Try again</button>` : ""}</div>`;
  }

  /** Show the AI examiner's report in `host`, polling while it is being made. */
  function mountReview(host, sub, onDone) {
    if (!host || !sub.aiReview) return () => {};
    let stopped = false;
    let timer = null;
    const draw = (r) => {
      if (stopped) return;
      if (r.status === "done") {
        host.innerHTML = doneHTML(r);
        return;
      }
      if (r.status === "error") {
        host.innerHTML = errorHTML(r);
        const b = host.querySelector("#ai-retry");
        if (b) {
          b.addEventListener("click", async () => {
            b.disabled = true;
            try {
              const res = await U.api(`/api/speaking/submissions/${Number(sub.id)}/ai-review`, { method: "POST", body: "{}" });
              draw(res.aiReview);
            } catch (e) {
              U.toast(e.message, "warn");
              b.disabled = false;
            }
          });
        }
        return;
      }
      if (r.status === "recording") {
        host.innerHTML = "";
        return;
      }
      host.innerHTML = waitingHTML(r);
      timer = setTimeout(poll, 2500);
    };
    const poll = async () => {
      if (stopped || !document.body.contains(host)) return;
      try {
        const { submission } = await U.api(`/api/speaking/submissions/${Number(sub.id)}`);
        if (submission.aiReview && submission.aiReview.status === "done") {
          if (onDone) return onDone(submission);
        }
        draw(submission.aiReview || { status: "error", message: "" });
      } catch (e) {
        timer = setTimeout(poll, 5000);
      }
    };
    draw(sub.aiReview);
    return () => { stopped = true; clearTimeout(timer); };
  }

  window.AiSpeakingExam = AiSpeakingExam;
  window.AiExaminer = { mountReview, answerExtrasHTML, questionOffset, ExaminerFace };
})();
