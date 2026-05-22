import type { GameState } from './types';
import type { Ring } from './types';
import {
  CYLINDER_RX, CYLINDER_RY, RING_THICKNESS, BALL_RADIUS,
  BALL_SCREEN_Y, MAX_BOUNCE_COUNT,
} from './constants';
import { getCameraY } from './engine';

const TWO_PI = Math.PI * 2;

function normalize(angle: number): number {
  return ((angle % TWO_PI) + TWO_PI) % TWO_PI;
}

function ringScreenY(ringY: number, cameraY: number): number {
  return ringY - cameraY;
}

function getRingColor(ring: Ring): string {
  if (ring.bounceCount === 0) return ring.color;
  if (ring.bounceCount === 1) return lerpColor(ring.color, '#FF6600', 0.4);
  return lerpColor(ring.color, '#CC0000', 0.75);
}

function lerpColor(hex1: string, hex2: string, t: number): string {
  const r1 = parseInt(hex1.slice(1, 3), 16);
  const g1 = parseInt(hex1.slice(3, 5), 16);
  const b1 = parseInt(hex1.slice(5, 7), 16);
  const r2 = parseInt(hex2.slice(1, 3), 16);
  const g2 = parseInt(hex2.slice(3, 5), 16);
  const b2 = parseInt(hex2.slice(5, 7), 16);
  return `rgb(${Math.round(r1+(r2-r1)*t)},${Math.round(g1+(g2-g1)*t)},${Math.round(b1+(b2-b1)*t)})`;
}

// Deterministic "random" from index
function hash(n: number): number {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

function drawCloud(ctx: CanvasRenderingContext2D, x: number, y: number, scale: number) {
  ctx.save();
  ctx.fillStyle = 'rgba(255,255,255,0.82)';
  ctx.beginPath();
  ctx.arc(x,          y,           30 * scale, 0, TWO_PI);
  ctx.arc(x + 28*scale, y - 10*scale, 22 * scale, 0, TWO_PI);
  ctx.arc(x + 55*scale, y,           26 * scale, 0, TWO_PI);
  ctx.arc(x + 25*scale, y + 12*scale, 18 * scale, 0, TWO_PI);
  ctx.fill();
  ctx.restore();
}

function drawClouds(ctx: CanvasRenderingContext2D, cameraY: number, canvasW: number, canvasH: number) {
  const PARALLAX = 0.28;
  const CHUNK = 350;
  const parallaxOffset = cameraY * PARALLAX;

  const startChunk = Math.floor((parallaxOffset - 120) / CHUNK);
  const endChunk   = Math.ceil((parallaxOffset + canvasH + 120) / CHUNK);

  for (let i = startChunk; i <= endChunk; i++) {
    const worldY  = i * CHUNK + hash(i * 3)     * CHUNK;
    const screenY = worldY - parallaxOffset;
    const x       = hash(i * 7)  * (canvasW + 100) - 50;
    const scale   = 0.45 + hash(i * 13) * 0.55;
    drawCloud(ctx, x, screenY, scale);
  }
}

function drawSpeedLines(ctx: CanvasRenderingContext2D, cx: number, cy: number, vy: number) {
  if (vy < 4) return;
  const alpha = Math.min((vy - 4) / 7, 0.38);
  const len   = 14 + vy * 5;
  const xs    = [-90, -55, -25, 25, 55, 90, -110, 110, -38, 38, -70, 70];

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 1.5;
  ctx.lineCap = 'round';

  for (let i = 0; i < xs.length; i++) {
    const x = cx + xs[i];
    const y = cy - 100 + (i % 6) * 30;
    ctx.beginPath();
    ctx.moveTo(x, y + len);
    ctx.lineTo(x, y);
    ctx.stroke();
  }
  ctx.restore();
}

function drawCharacter(ctx: CanvasRenderingContext2D, cx: number, cy: number, vy: number) {
  const falling = vy >= 0;

  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  // Shadow on platform below
  ctx.beginPath();
  ctx.ellipse(cx, cy + BALL_RADIUS + 2, 9, 3, 0, 0, TWO_PI);
  ctx.fillStyle = 'rgba(0,0,0,0.2)';
  ctx.fill();

  // Body (shirt)
  ctx.beginPath();
  ctx.moveTo(cx, cy - 4);
  ctx.lineTo(cx, cy + 7);
  ctx.strokeStyle = '#E74C3C';
  ctx.lineWidth = 5;
  ctx.stroke();

  // Arms — spread wide when falling, raised when bouncing up
  const armLift = falling ? -2 : -8;
  const armEndY = falling ? cy - 10 : cy - 4;
  ctx.beginPath();
  ctx.moveTo(cx - 18, armEndY);
  ctx.lineTo(cx,      cy + armLift);
  ctx.lineTo(cx + 18, armEndY);
  ctx.strokeStyle = '#FFDBA4';
  ctx.lineWidth = 3;
  ctx.stroke();

  // Legs
  const legSpread = falling ? 7 : 12;
  ctx.beginPath();
  ctx.moveTo(cx, cy + 7);
  ctx.lineTo(cx - legSpread, cy + 20);
  ctx.moveTo(cx, cy + 7);
  ctx.lineTo(cx + legSpread, cy + 20);
  ctx.strokeStyle = '#2471A3';
  ctx.lineWidth = 3;
  ctx.stroke();

  // Head
  ctx.beginPath();
  ctx.arc(cx, cy - 14, 9, 0, TWO_PI);
  ctx.fillStyle = '#FFDBA4';
  ctx.fill();
  ctx.strokeStyle = '#d4956a';
  ctx.lineWidth = 1;
  ctx.stroke();

  // Hair
  ctx.beginPath();
  ctx.arc(cx, cy - 14, 9, Math.PI * 1.1, TWO_PI * 1.9);
  ctx.fillStyle = '#5D4037';
  ctx.fill();

  // Eyes — wide open when falling fast, normal otherwise
  ctx.fillStyle = '#1a1a1a';
  const eyeSize = vy > 5 ? 2.2 : 1.6;
  ctx.beginPath();
  ctx.arc(cx - 3, cy - 15, eyeSize, 0, TWO_PI);
  ctx.arc(cx + 3, cy - 15, eyeSize, 0, TWO_PI);
  ctx.fill();

  // Mouth: O (screaming) when falling fast, smile otherwise
  if (vy > 4) {
    ctx.beginPath();
    ctx.arc(cx, cy - 10, 2.5, 0, TWO_PI);
    ctx.strokeStyle = '#c0785a';
    ctx.lineWidth = 1;
    ctx.stroke();
  } else {
    ctx.beginPath();
    ctx.arc(cx, cy - 11, 2.5, 0.2, Math.PI - 0.2);
    ctx.strokeStyle = '#c0785a';
    ctx.lineWidth = 1.2;
    ctx.stroke();
  }

  // Helmet (skydiver feel)
  ctx.beginPath();
  ctx.arc(cx, cy - 14, 9.5, Math.PI * 1.15, TWO_PI * 1.85);
  ctx.strokeStyle = '#FF8C00';
  ctx.lineWidth = 4;
  ctx.stroke();

  ctx.restore();
}

function drawCombo(ctx: CanvasRenderingContext2D, cx: number, combo: number, canvasH: number) {
  const COMBO_COLORS = ['#FFD700', '#FF8C00', '#FF4500', '#FF2277', '#CC00FF'];
  const color = COMBO_COLORS[Math.min(combo - 2, COMBO_COLORS.length - 1)];

  // 맥동 효과 (Date.now 기반)
  const pulse = 1 + Math.sin(Date.now() * 0.008) * 0.06;
  const scale = Math.min(1 + (combo - 2) * 0.12, 2.2) * pulse;
  const y = canvasH * 0.62;

  ctx.save();
  ctx.translate(cx, y);
  ctx.scale(scale, scale);
  ctx.textAlign = 'center';

  // 배경 글로우
  ctx.shadowColor = color;
  ctx.shadowBlur = 24;

  // 콤보 숫자
  ctx.font = `bold 38px system-ui`;
  ctx.fillStyle = color;
  ctx.fillText(`x${combo} COMBO!`, 0, 0);

  // 보너스 점수 표시 (3콤보부터)
  if (combo >= 3) {
    ctx.shadowBlur = 10;
    ctx.font = 'bold 18px system-ui';
    ctx.fillStyle = 'rgba(255,255,255,0.9)';
    ctx.fillText(`+${combo} pts`, 0, 28);
  }

  ctx.restore();
}

function drawRingHalf(
  ctx: CanvasRenderingContext2D,
  cx: number, cy: number,
  rx: number, ry: number,
  canvasGapCenter: number, gapSize: number,
  color: string,
  alpha: number,
  clipTop: boolean,
) {
  const solidStart = canvasGapCenter + gapSize / 2;
  const solidEnd   = canvasGapCenter - gapSize / 2 + TWO_PI;

  ctx.save();
  ctx.globalAlpha = alpha;

  ctx.beginPath();
  if (clipTop) {
    ctx.rect(cx - rx - RING_THICKNESS, 0, (rx + RING_THICKNESS) * 2, cy);
  } else {
    ctx.rect(cx - rx - RING_THICKNESS, cy, (rx + RING_THICKNESS) * 2, 9999);
  }
  ctx.clip();

  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, solidStart, solidEnd);
  ctx.strokeStyle = color;
  ctx.lineWidth = RING_THICKNESS;
  ctx.lineCap = 'butt';
  ctx.stroke();

  ctx.restore();
}

function getSpeedScale(state: GameState): number {
  const speedScore = state.score - state.reviveAt;
  return Math.min(1 + speedScore * 0.01, 2.5);
}

// t(0=느림, 1=빠름)에 따라 RGB 두 색상 보간
function lerpRGB(
  r1: number, g1: number, b1: number,
  r2: number, g2: number, b2: number,
  t: number,
): string {
  return `rgb(${Math.round(r1+(r2-r1)*t)},${Math.round(g1+(g2-g1)*t)},${Math.round(b1+(b2-b1)*t)})`;
}

function makeSkyGradient(
  ctx: CanvasRenderingContext2D,
  canvasH: number,
  t: number, // 0=파란 하늘, 1=붉은 하늘
): CanvasGradient {
  const grad = ctx.createLinearGradient(0, 0, 0, canvasH);
  // 위: 깊은 파랑 → 어두운 붉은 하늘
  grad.addColorStop(0,   lerpRGB(26,111,163,  100,18,10,  t));
  // 중간: 하늘 파랑 → 주황빛
  grad.addColorStop(0.5, lerpRGB(61,156,204,  200,60,20,  t));
  // 아래: 연한 하늘 → 노을빛
  grad.addColorStop(1,   lerpRGB(126,200,227, 255,140,60, t));
  return grad;
}

function drawSpeedClearFlash(
  ctx: CanvasRenderingContext2D,
  cx: number,
  canvasH: number,
  alpha: number,
) {
  if (alpha <= 0) return;
  // 0→1 구간에서 크게 나타났다 작아지며 사라짐
  const scalePhase = alpha > 0.7 ? 1 + (1 - alpha) * 1.5 : alpha / 0.7;
  const scale = 0.7 + scalePhase * 0.6;

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(cx, canvasH * 0.48);
  ctx.scale(scale, scale);
  ctx.textAlign = 'center';

  ctx.shadowColor = '#00FFAA';
  ctx.shadowBlur = 28;
  ctx.font = 'bold 34px system-ui';
  ctx.fillStyle = '#00FFCC';
  ctx.fillText('SPEED CLEAR!', 0, 0);

  ctx.restore();
}

export function render(
  ctx: CanvasRenderingContext2D,
  state: GameState,
  canvasW: number,
  canvasH: number,
  highScore: number,
  speedClearAlpha = 0,
) {
  // 속도에 따라 하늘색 변화: 파랑(느림) → 붉은 노을(빠름)
  const speedScale = getSpeedScale(state);
  const t = (speedScale - 1) / 1.5; // 0~1
  ctx.fillStyle = makeSkyGradient(ctx, canvasH, t);
  ctx.fillRect(0, 0, canvasW, canvasH);

  const cx      = canvasW / 2;
  const cameraY = getCameraY(state.ballY);

  // Clouds (parallax, behind everything)
  drawClouds(ctx, cameraY, canvasW, canvasH);

  // Subtle cylinder guide lines
  ctx.save();
  ctx.strokeStyle = 'rgba(255,255,255,0.1)';
  ctx.lineWidth = 1;
  ctx.setLineDash([6, 12]);
  ctx.beginPath(); ctx.moveTo(cx - CYLINDER_RX, 0); ctx.lineTo(cx - CYLINDER_RX, canvasH); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(cx + CYLINDER_RX, 0); ctx.lineTo(cx + CYLINDER_RX, canvasH); ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();

  const visibleRings = state.rings.filter(r => {
    const sy = ringScreenY(r.y, cameraY);
    return !r.passed && sy > -60 && sy < canvasH + 60;
  });

  // Pass 1: far halves (behind character)
  for (const ring of visibleRings) {
    const sy   = ringScreenY(ring.y, cameraY);
    const eff  = normalize(ring.gapCenterHelix + state.helixRotation);
    const canvasGapCenter = Math.PI / 2 - eff;
    drawRingHalf(ctx, cx, sy, CYLINDER_RX, CYLINDER_RY, canvasGapCenter, ring.gapSize, getRingColor(ring), 0.62, true);
  }

  // Speed lines
  drawSpeedLines(ctx, cx, BALL_SCREEN_Y, state.ballVY);

  // Character
  drawCharacter(ctx, cx, BALL_SCREEN_Y, state.ballVY);

  // Pass 2: near halves (in front of character)
  for (const ring of visibleRings) {
    const sy   = ringScreenY(ring.y, cameraY);
    const eff  = normalize(ring.gapCenterHelix + state.helixRotation);
    const canvasGapCenter = Math.PI / 2 - eff;
    drawRingHalf(ctx, cx, sy, CYLINDER_RX, CYLINDER_RY, canvasGapCenter, ring.gapSize, getRingColor(ring), 1.0, false);
  }

  // Bounce warning dots on ring edges
  for (const ring of visibleRings) {
    if (ring.bounceCount === 0) continue;
    const sy  = ringScreenY(ring.y, cameraY);
    const eff = normalize(ring.gapCenterHelix + state.helixRotation);
    const canvasGapCenter = Math.PI / 2 - eff;
    const left  = canvasGapCenter + ring.gapSize / 2;
    const right = canvasGapCenter - ring.gapSize / 2;

    for (const angle of [left, right]) {
      const dx = cx  + Math.cos(angle) * CYLINDER_RX;
      const dy = sy  + Math.sin(angle) * CYLINDER_RY;
      ctx.beginPath();
      ctx.arc(dx, dy, 5 + ring.bounceCount, 0, TWO_PI);
      ctx.fillStyle = ring.bounceCount >= MAX_BOUNCE_COUNT - 1 ? '#FF2200' : '#FF8800';
      ctx.fill();
    }
  }

  // HUD
  ctx.save();
  ctx.textAlign = 'center';
  ctx.shadowColor = 'rgba(0,0,0,0.4)';
  ctx.shadowBlur = 6;
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 52px system-ui';
  ctx.fillText(String(state.score), cx, 72);
  ctx.font = '17px system-ui';
  ctx.fillStyle = 'rgba(255,255,255,0.7)';
  ctx.fillText(`BEST ${highScore}`, cx, 96);
  ctx.restore();

  // 콤보 표시
  if (state.combo >= 2) {
    drawCombo(ctx, cx, state.combo, canvasH);
  }

  // 속도 클리어 플래시
  drawSpeedClearFlash(ctx, cx, canvasH, speedClearAlpha);
}

export function renderIdle(
  ctx: CanvasRenderingContext2D,
  canvasW: number,
  canvasH: number,
) {
  const cx = canvasW / 2;

  // Sky background
  const grad = ctx.createLinearGradient(0, 0, 0, canvasH);
  grad.addColorStop(0,   '#1a6fa3');
  grad.addColorStop(0.6, '#3d9ccc');
  grad.addColorStop(1,   '#7ec8e3');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, canvasW, canvasH);

  // Static clouds
  drawClouds(ctx, 0, canvasW, canvasH);

  // Decorative rings
  const colors = ['#FF6B6B', '#FFCA28', '#42A5F5', '#66BB6A', '#AB47BC'];
  for (let i = 0; i < 5; i++) {
    const y       = 200 + i * 80;
    const gap     = Math.PI * 0.68;
    const gapC    = -0.2 + i * 0.85;
    const sStart  = gapC + gap / 2;
    const sEnd    = gapC - gap / 2 + TWO_PI;
    ctx.beginPath();
    ctx.ellipse(cx, y, CYLINDER_RX, CYLINDER_RY, 0, sStart, sEnd);
    ctx.strokeStyle = colors[i];
    ctx.lineWidth = RING_THICKNESS;
    ctx.globalAlpha = 0.75;
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  // Character on title screen
  drawCharacter(ctx, cx, 155, 0);

  // Title
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.35)';
  ctx.shadowBlur = 8;
  ctx.textAlign = 'center';
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 42px system-ui';
  ctx.fillText('HELIX JUMP', cx, canvasH * 0.72);
  ctx.font = '19px system-ui';
  ctx.fillStyle = 'rgba(255,255,255,0.75)';
  ctx.fillText('← → 방향키 또는 드래그로 회전', cx, canvasH * 0.72 + 38);
  ctx.restore();

  // Start button
  const btnW = 200, btnH = 56;
  const btnX = cx - btnW / 2, btnY = canvasH * 0.81;
  const btnGrad = ctx.createLinearGradient(btnX, btnY, btnX + btnW, btnY);
  btnGrad.addColorStop(0, '#FF6B6B');
  btnGrad.addColorStop(1, '#FF8E53');
  ctx.beginPath();
  ctx.roundRect(btnX, btnY, btnW, btnH, 28);
  ctx.fillStyle = btnGrad;
  ctx.fill();
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 22px system-ui';
  ctx.textAlign = 'center';
  ctx.fillText('PLAY', cx, btnY + 37);
}
