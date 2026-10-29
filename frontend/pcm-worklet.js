// Downsamples mic audio to 16 kHz mono PCM16 and posts 512-sample frames
// (1,024 bytes — exactly what Prisma expects per WebSocket frame).
const TARGET_RATE = 16000;
const FRAME_SAMPLES = 512;

class PcmWorklet extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / TARGET_RATE;
    this.pos = 0;        // fractional read position into the input stream
    this.prev = 0;       // last sample of the previous block, for interpolation
    this.frame = new Int16Array(FRAME_SAMPLES);
    this.filled = 0;
  }

  process(inputs) {
    const input = inputs[0][0];
    if (!input) return true;

    // Linear interpolation; index -1 refers to this.prev.
    while (this.pos < input.length) {
      const i = Math.floor(this.pos);
      const frac = this.pos - i;
      const a = i === 0 ? this.prev : input[i - 1];
      const b = input[i];
      const s = Math.max(-1, Math.min(1, a + (b - a) * frac));
      this.frame[this.filled++] = s < 0 ? s * 0x8000 : s * 0x7fff;
      if (this.filled === FRAME_SAMPLES) {
        this.port.postMessage(this.frame.buffer.slice(0));
        this.filled = 0;
      }
      this.pos += this.ratio;
    }
    this.pos -= input.length;
    this.prev = input[input.length - 1];
    return true;
  }
}

registerProcessor("pcm-worklet", PcmWorklet);
