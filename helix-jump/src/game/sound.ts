let ac: AudioContext | null = null;
let unlocked = false;

function getCtx(): AudioContext {
  if (!ac) ac = new AudioContext();
  return ac;
}

// 모바일/브라우저 AudioContext unlock (첫 터치/클릭 시 호출)
export function unlockAudio() {
  if (unlocked) return;
  unlocked = true;
  const ctx = getCtx();
  if (ctx.state === 'suspended') ctx.resume();
}

// 링 통과 — 상쾌한 whoosh + ding
export function playPass(combo = 1) {
  const ctx = getCtx();
  const t = ctx.currentTime;
  const pitch = 500 + combo * 80; // 콤보 높을수록 음높이↑

  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain); gain.connect(ctx.destination);
  osc.type = 'sine';
  osc.frequency.setValueAtTime(pitch, t);
  osc.frequency.exponentialRampToValueAtTime(pitch * 1.6, t + 0.1);
  gain.gain.setValueAtTime(0.28, t);
  gain.gain.exponentialRampToValueAtTime(0.001, t + 0.18);
  osc.start(t); osc.stop(t + 0.18);
}

// 링에 부딪힘 — 둔탁한 thud
export function playBounce() {
  const ctx = getCtx();
  const t = ctx.currentTime;

  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain); gain.connect(ctx.destination);
  osc.type = 'triangle';
  osc.frequency.setValueAtTime(260, t);
  osc.frequency.exponentialRampToValueAtTime(70, t + 0.09);
  gain.gain.setValueAtTime(0.35, t);
  gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
  osc.start(t); osc.stop(t + 0.12);
}

// 게임 오버 — 추락하는 소리
export function playDie() {
  const ctx = getCtx();
  const t = ctx.currentTime;

  // 내려가는 비명
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  const dist = ctx.createWaveShaper();
  const curve = new Float32Array(256);
  for (let i = 0; i < 256; i++) {
    const x = (i * 2) / 256 - 1;
    curve[i] = (Math.PI + 200) * x / (Math.PI + 200 * Math.abs(x));
  }
  dist.curve = curve;
  osc.connect(dist); dist.connect(gain); gain.connect(ctx.destination);

  osc.type = 'sawtooth';
  osc.frequency.setValueAtTime(480, t);
  osc.frequency.exponentialRampToValueAtTime(60, t + 0.55);
  gain.gain.setValueAtTime(0.3, t);
  gain.gain.exponentialRampToValueAtTime(0.001, t + 0.6);
  osc.start(t); osc.stop(t + 0.6);

  // 충격음
  const buf = ctx.createBuffer(1, ctx.sampleRate * 0.15, ctx.sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / data.length);
  const src = ctx.createBufferSource();
  const ng = ctx.createGain();
  const f = ctx.createBiquadFilter();
  f.type = 'lowpass'; f.frequency.value = 200;
  src.buffer = buf;
  src.connect(f); f.connect(ng); ng.connect(ctx.destination);
  ng.gain.setValueAtTime(0.5, t);
  ng.gain.exponentialRampToValueAtTime(0.001, t + 0.15);
  src.start(t); src.stop(t + 0.15);
}

// 5콤보 속도 리셋 — 시원한 파워다운 사운드
export function playSpeedClear() {
  const ctx = getCtx();
  const t = ctx.currentTime;

  // 내려가는 스윕 (기계가 느려지는 느낌)
  const osc1 = ctx.createOscillator();
  const gain1 = ctx.createGain();
  osc1.connect(gain1); gain1.connect(ctx.destination);
  osc1.type = 'sine';
  osc1.frequency.setValueAtTime(900, t);
  osc1.frequency.exponentialRampToValueAtTime(220, t + 0.55);
  gain1.gain.setValueAtTime(0.3, t);
  gain1.gain.exponentialRampToValueAtTime(0.001, t + 0.6);
  osc1.start(t); osc1.stop(t + 0.6);

  // 반짝이는 고음 레이어
  const osc2 = ctx.createOscillator();
  const gain2 = ctx.createGain();
  osc2.connect(gain2); gain2.connect(ctx.destination);
  osc2.type = 'triangle';
  osc2.frequency.setValueAtTime(1400, t);
  osc2.frequency.exponentialRampToValueAtTime(700, t + 0.3);
  gain2.gain.setValueAtTime(0.15, t);
  gain2.gain.exponentialRampToValueAtTime(0.001, t + 0.35);
  osc2.start(t); osc2.stop(t + 0.35);
}

// 바람 소리 (낙하 중 앰비언트)
let windSrc: AudioBufferSourceNode | null = null;
let windGain: GainNode | null = null;

export function startWind() {
  if (windSrc) return;
  const ctx = getCtx();
  const sr = ctx.sampleRate;
  const buf = ctx.createBuffer(1, sr * 3, sr);
  const d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;

  const f = ctx.createBiquadFilter();
  f.type = 'bandpass'; f.frequency.value = 600; f.Q.value = 0.4;

  windGain = ctx.createGain();
  windGain.gain.value = 0;

  windSrc = ctx.createBufferSource();
  windSrc.buffer = buf;
  windSrc.loop = true;
  windSrc.connect(f); f.connect(windGain); windGain.connect(ctx.destination);
  windSrc.start();
}

export function setWindSpeed(vy: number) {
  if (!windGain || !ac) return;
  const target = Math.min(vy * 0.009, 0.07);
  windGain.gain.setTargetAtTime(target, ac.currentTime, 0.2);
}

export function stopWind() {
  if (windSrc) { try { windSrc.stop(); } catch {} windSrc = null; }
  windGain = null;
}
