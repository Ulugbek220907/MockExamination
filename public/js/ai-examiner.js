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
     The examiner's face
     ==================================================================== */
  // Each examiner voice has its own look.
  const LOOKS = {
    bf_emma: { skin: "#f0c6a4", shade: "#d9a283", hair: "#5e3720", style: "bob", iris: "#4d6f8f", jacket: "#2d3950", shirt: "#eef0f3", lips: "#b9645c" },
    bf_alice: { skin: "#e9b892", shade: "#cf9670", hair: "#2a1c14", style: "bun", iris: "#5a3f2c", jacket: "#5b3b4b", shirt: "#f4efe9", lips: "#b25a55" },
    bf_isabella: { skin: "#c48a62", shade: "#a66f4c", hair: "#1d1410", style: "long", iris: "#3e2a1e", jacket: "#24474a", shirt: "#f3f1ec", lips: "#9c4f49" },
    bf_lily: { skin: "#f4d3bb", shade: "#dfb093", hair: "#b07f3f", style: "long", iris: "#5f7f55", jacket: "#3b3f63", shirt: "#ffffff", lips: "#c46e68" },
    bm_daniel: { skin: "#d8a07a", shade: "#bb815d", hair: "#3a2618", style: "short", iris: "#4b3524", jacket: "#28334a", shirt: "#e7edf5", lips: "#a8625a" },
    bm_george: { skin: "#eec2a0", shade: "#d4a07f", hair: "#8b8782", style: "side", iris: "#55708a", jacket: "#43403d", shirt: "#f1f1ee", lips: "#b06a62", glasses: true },
    bm_lewis: { skin: "#8e5b3c", shade: "#73462c", hair: "#17110d", style: "crop", iris: "#2e1f16", jacket: "#2f3b2f", shirt: "#eef2ee", lips: "#7a4234", beard: true },
  };

  function lookFor(examiner) {
    const voice = (examiner && examiner.voice) || "";
    return LOOKS[voice] || (voice.startsWith("bm_") ? LOOKS.bm_daniel : LOOKS.bf_emma);
  }

  const HAIR_BACK = {
    bob: "M96 196 C 90 120 140 70 200 70 C 262 70 312 120 304 198 C 302 240 298 270 286 292 L 252 292 L 250 240 L 150 240 L 148 292 L 114 292 C 102 270 98 240 96 196 Z",
    long: "M94 200 C 86 118 140 68 200 68 C 262 68 316 118 306 202 C 312 262 320 318 306 352 C 294 366 266 366 252 352 L 250 300 L 150 300 L 148 352 C 134 366 106 366 94 352 C 80 318 88 262 94 200 Z",
    bun: "M110 190 C 106 122 146 86 200 86 C 254 86 294 122 290 190 Z M168 70 A 32 30 0 1 0 232 70 A 32 30 0 1 0 168 70 Z",
    short: "M112 190 C 108 120 150 80 200 80 C 250 80 292 120 288 190 Z",
    side: "M112 190 C 108 120 150 80 200 80 C 250 80 292 120 288 190 Z",
    crop: "M116 182 C 114 124 152 88 200 88 C 248 88 286 124 284 182 Z",
  };
  const HAIR_FRONT = {
    bob: "M110 196 C 104 126 148 84 204 84 C 262 84 298 128 292 198 C 280 156 256 130 220 122 C 196 142 152 150 116 200 Z",
    long: "M110 200 C 104 128 150 82 206 84 C 262 86 300 130 292 204 C 284 168 270 146 246 132 C 228 146 210 150 196 146 C 168 140 132 156 110 200 Z",
    bun: "M112 182 C 110 120 152 90 200 90 C 248 90 290 120 288 182 C 274 144 244 118 200 118 C 158 118 128 142 112 182 Z",
    short: "M114 178 C 108 116 152 80 204 82 C 256 84 294 118 288 180 C 284 150 272 132 252 126 C 226 116 178 116 150 126 C 132 134 120 152 114 178 Z",
    side: "M114 180 C 106 112 156 78 210 82 C 260 86 296 122 288 182 C 282 150 268 132 244 124 C 214 112 176 132 152 132 C 134 134 120 152 114 180 Z",
    crop: "M118 172 C 116 120 154 92 200 92 C 246 92 284 120 282 172 C 270 140 240 124 200 124 C 160 124 130 140 118 172 Z",
  };

  function faceSVG(look) {
    const eye = (cx) => `
      <g class="fx-eye" data-cx="${cx}">
        <ellipse cx="${cx}" cy="198" rx="15.5" ry="9.5" fill="#fbfaf7"/>
        <g class="fx-pupil"><circle cx="${cx}" cy="198" r="7.4" fill="${look.iris}"/><circle cx="${cx}" cy="198" r="3.5" fill="#15110f"/>
          <circle cx="${cx + 2.6}" cy="195.4" r="1.7" fill="#fff" opacity="0.9"/></g>
        <path class="fx-lid" d="M${cx - 17} 197 C ${cx - 9} 186 ${cx + 9} 186 ${cx + 17} 197" fill="none" stroke="#3b2a22" stroke-width="2.4" stroke-linecap="round"/>
      </g>`;
    return `
      <svg viewBox="0 0 400 440" class="fx-svg" role="img" aria-hidden="true" focusable="false">
        <defs>
          <clipPath id="fx-mouth-clip"><path class="fx-mouth-shape"/></clipPath>
          <radialGradient id="fx-face-light" cx="45%" cy="38%" r="70%"><stop offset="0" stop-color="#fff" stop-opacity="0.18"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
        </defs>
        <g class="fx-body">
          <path d="M40 440 C 48 368 104 336 160 326 L 240 326 C 296 336 352 368 360 440 Z" fill="${look.jacket}"/>
          <path d="M168 326 L 200 384 L 232 326 Z" fill="${look.shirt}"/>
          <path d="M160 326 L 200 386 L 178 440 L 140 440 Z M240 326 L 200 386 L 222 440 L 260 440 Z" fill="${look.jacket}" opacity="0.9"/>
          <path d="M176 290 L 176 334 C 188 346 212 346 224 334 L 224 290 Z" fill="${look.shade}"/>
        </g>
        <g class="fx-head">
          <path d="${HAIR_BACK[look.style]}" fill="${look.hair}"/>
          <ellipse cx="114" cy="214" rx="11" ry="18" fill="${look.shade}"/><ellipse cx="286" cy="214" rx="11" ry="18" fill="${look.shade}"/>
          <path d="M200 98 C 260 98 290 142 288 202 C 286 262 252 306 200 306 C 148 306 114 262 112 202 C 110 142 140 98 200 98 Z" fill="${look.skin}"/>
          <path d="M200 98 C 260 98 290 142 288 202 C 286 262 252 306 200 306 C 148 306 114 262 112 202 C 110 142 140 98 200 98 Z" fill="url(#fx-face-light)"/>
          ${look.beard ? `<path d="M124 232 C 130 288 166 314 200 314 C 234 314 270 288 276 232 C 266 262 244 276 226 280 C 216 270 184 270 174 280 C 156 276 134 262 124 232 Z" fill="${look.hair}" opacity="0.92"/>` : ""}
          <ellipse cx="150" cy="238" rx="17" ry="9" fill="#e07a6a" opacity="0.12"/><ellipse cx="250" cy="238" rx="17" ry="9" fill="#e07a6a" opacity="0.12"/>
          <path d="${HAIR_FRONT[look.style]}" fill="${look.hair}"/>
          <g class="fx-brows" fill="none" stroke="${look.style === "side" ? "#6f6a64" : look.hair}" stroke-width="5" stroke-linecap="round">
            <path class="fx-brow-l" d="M148 172 C 156 165 170 164 182 168"/><path class="fx-brow-r" d="M218 168 C 230 164 244 165 252 172"/>
          </g>
          ${eye(166)}${eye(234)}
          ${look.glasses ? `<g fill="none" stroke="#2d2a28" stroke-width="3"><rect x="141" y="182" width="50" height="34" rx="12"/><rect x="209" y="182" width="50" height="34" rx="12"/><path d="M191 196 C 196 192 204 192 209 196 M141 194 L 120 190 M259 194 L 280 190"/></g>` : ""}
          <path d="M201 206 C 197 224 190 236 196 243 C 200 246 207 245 211 242" fill="none" stroke="${look.shade}" stroke-width="3" stroke-linecap="round"/>
          <g class="fx-mouth" transform="translate(200 266)">
            <path class="fx-mouth-shape fx-mouth-in" fill="#4a1f1f"/>
            <g clip-path="url(#fx-mouth-clip)"><rect class="fx-teeth" x="-30" y="-20" width="60" height="0" fill="#f7f4ee"/></g>
            <path class="fx-mouth-shape fx-lips" fill="none" stroke="${look.lips}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>
          </g>
        </g>
      </svg>`;
  }

  class ExaminerFace {
    constructor(host, examiner) {
      this.host = host;
      host.innerHTML = faceSVG(lookFor(examiner));
      this.svg = host.querySelector("svg");
      this.head = host.querySelector(".fx-head");
      this.body = host.querySelector(".fx-body");
      this.eyes = [...host.querySelectorAll(".fx-eye")];
      this.pupils = [...host.querySelectorAll(".fx-pupil")];
      this.brows = host.querySelector(".fx-brows");
      this.shapes = [...host.querySelectorAll(".fx-mouth-shape")];
      this.teeth = host.querySelector(".fx-teeth");
      this.state = "idle";
      this.open = 0; // mouth, 0–1
      this.wide = 0.5;
      this.voice = null; // () => { level, bright } while the examiner speaks
      this.gaze = { x: 0, y: 0, tx: 0, ty: 0, next: 0 };
      this.blinkAt = performance.now() + 1800;
      this.blinkUntil = 0;
      this.nodStart = -1e9;
      this.running = true;
      this.drawMouth(0, 0.5);
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

    drawMouth(open, wide) {
      const w = 19 + wide * 6 - open * 3;
      const h = open * 15;
      const smile = this.state === "speaking" ? 1 : 2.2;
      const top = -h * 0.32 - 1;
      const bottom = h * 0.68 + 2.5;
      const d = `M${-w} ${-smile} C ${-w * 0.45} ${top}, ${w * 0.45} ${top}, ${w} ${-smile} C ${w * 0.5} ${bottom}, ${-w * 0.5} ${bottom}, ${-w} ${-smile} Z`;
      this.shapes.forEach((p) => p.setAttribute("d", d));
      this.teeth.setAttribute("y", String(top - 1));
      this.teeth.setAttribute("height", String(Math.max(0, Math.min(h * 0.38, 5.5))));
    }

    frame(now) {
      const t = now / 1000;
      const calm = reducedMotion();
      // The mouth follows the examiner's voice.
      let target = 0;
      let wide = 0.5;
      if (this.state === "speaking" && this.voice) {
        const v = this.voice();
        target = v.level;
        wide = v.bright;
      }
      this.open += (target - this.open) * (target > this.open ? 0.55 : 0.3);
      this.wide += (wide - this.wide) * 0.2;
      this.drawMouth(this.open, this.wide);

      // Blinks every few seconds, now and then twice.
      if (now > this.blinkAt) {
        this.blinkUntil = now + 130;
        this.blinkAt = now + (Math.random() < 0.15 ? 260 : 2400 + Math.random() * 3800);
      }
      const writing = this.state === "writing";
      const lid = now < this.blinkUntil ? 0.08 : writing ? 0.55 : 1;
      this.eyes.forEach((e) => {
        const cx = Number(e.dataset.cx);
        e.setAttribute("transform", `translate(${cx} 198) scale(1 ${lid}) translate(${-cx} -198)`);
      });

      // Where the examiner looks: at you, with small natural movements; down at the notes while you prepare.
      const g = this.gaze;
      if (now > g.next) {
        const roam = calm ? 0 : this.state === "speaking" ? 1.2 : 2.6;
        g.tx = (Math.random() * 2 - 1) * roam;
        g.ty = writing ? 4.5 : (Math.random() * 2 - 1) * roam * 0.5;
        g.next = now + 900 + Math.random() * 2600;
      }
      g.x += (g.tx - g.x) * 0.18;
      g.y += (g.ty - g.y) * 0.18;
      this.pupils.forEach((p) => p.setAttribute("transform", `translate(${g.x.toFixed(2)} ${g.y.toFixed(2)})`));

      const browLift = this.state === "speaking" ? -this.open * 3 : this.state === "listening" ? -1.2 : 0;
      this.brows.setAttribute("transform", `translate(0 ${browLift.toFixed(2)})`);

      if (calm) {
        this.head.setAttribute("transform", writing ? "translate(0 5)" : "");
        return;
      }
      let angle = 1.1 * Math.sin(t * 0.55) + 0.5 * Math.sin(t * 1.63);
      let dy = 1.3 * Math.sin(t * 1.05);
      if (this.state === "speaking") {
        angle += this.open * 1.4 * Math.sin(t * 2.7);
        dy += this.open * 2.2;
      } else if (this.state === "listening") {
        angle += 2.2; // a slight, attentive tilt
      } else if (writing) {
        dy += 7;
        angle -= 1.5;
      }
      const sinceNod = (now - this.nodStart) / 1000;
      if (sinceNod < 0.7) dy += Math.sin((sinceNod / 0.7) * Math.PI * 2) * 4.5 * (1 - sinceNod / 0.7);
      this.head.setAttribute("transform", `rotate(${angle.toFixed(2)} 200 320) translate(0 ${dy.toFixed(2)})`);
      this.body.setAttribute("transform", `translate(0 ${(0.9 * Math.sin(t * 0.9)).toFixed(2)})`);
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

    helpHTML() {
      return `
        <p><strong>How the test with the AI examiner works</strong></p>
        <ul class="help-list">
          <li>${esc(this.examinerName)} asks every question out loud, as in the real test. Answer by speaking; you do not need to press anything.</li>
          <li>When you stop talking, the examiner moves on to the next question. If you need a moment to think, that is fine: the examiner waits a few seconds.</li>
          <li><strong>Repeat</strong> asks the examiner to say the question again (once per question, in Parts 1 and 3).</li>
          <li>Part 2: one minute to prepare (you can type notes), then up to two minutes to talk. The examiner stops you at two minutes.</li>
          <li>The examiner does not answer you or comment, just like a real examiner.</li>
          <li>At the end, the AI examiner listens to your whole test and gives you an estimated band for each criterion, with feedback.</li>
        </ul>`;
    }

    setExaminer(state) {
      if (!this.face) return;
      this.face.setState(state === "speaking" ? "speaking" : state === "listening" ? "listening" : state === "writing" ? "writing" : "idle");
      const label = { speaking: "Speaking…", listening: "Listening", writing: "Timing your preparation" }[state] || "Examiner";
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
        this.status("That is the end of the test. Your examiner will now rate your answers.");
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
      if (this.face) this.face.setState("idle");
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
