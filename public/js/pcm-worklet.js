/**
 * Microphone capture for the AI examiner: passes the raw samples of the first
 * input channel to the page in blocks of 2048 (about 40 ms at 48 kHz).
 * Loaded with audioContext.audioWorklet.addModule() by ai-examiner.js.
 */
class PcmCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.block = new Float32Array(2048);
    this.used = 0;
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel) {
      for (let i = 0; i < channel.length; i++) {
        this.block[this.used++] = channel[i];
        if (this.used === this.block.length) {
          this.port.postMessage(this.block, [this.block.buffer]);
          this.block = new Float32Array(2048);
          this.used = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor("pcm-capture", PcmCapture);
