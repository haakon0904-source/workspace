import type { GameState, Ring } from './types';
import {
  GRAVITY, MAX_FALL_SPEED, BOUNCE_DAMPING, MIN_BOUNCE_SPEED,
  MAX_BOUNCE_COUNT, BALL_RADIUS,
  RING_SPACING_INITIAL, RING_SPACING_MIN, RING_SPACING_SHRINK,
  GAP_SIZE_INITIAL, GAP_SIZE_MIN, GAP_SHRINK_START, GAP_SHRINK_PER_RING,
  RING_COLORS, BALL_SCREEN_Y,
} from './constants';

function getSpacing(score: number): number {
  return Math.max(RING_SPACING_MIN, RING_SPACING_INITIAL - score * RING_SPACING_SHRINK);
}

const TWO_PI = Math.PI * 2;

function normalize(angle: number): number {
  return ((angle % TWO_PI) + TWO_PI) % TWO_PI;
}

export function isGapAligned(ring: Ring, helixRotation: number): boolean {
  const eff = normalize(ring.gapCenterHelix + helixRotation);
  const dist = Math.min(eff, TWO_PI - eff);
  return dist < ring.gapSize / 2;
}

// 콤보가 잘 터지게: 55% 확률로 이전 링 틈 근처에 다음 링 틈 배치
const COMBO_CHAIN_CHANCE = 0.55;
const COMBO_MAX_OFFSET   = Math.PI * 0.45; // 이전 각도에서 최대 ±81° 차이

const COMBO_RUN_OFFSET = Math.PI * 0.15; // ±27° — intentionally easy run

function makeRing(id: number, y: number, score: number, prevGapAngle?: number, forceComboRun?: boolean): Ring {
  const rand = Math.random();
  let gapCenterHelix: number;

  if (id < 3) {
    // 첫 3개: 회전 필요하게 (튜토리얼 느낌)
    gapCenterHelix = Math.PI / 2 + rand * Math.PI;
  } else if (forceComboRun && prevGapAngle !== undefined) {
    // 의도적 콤보 구간: 이전 틈과 거의 같은 위치 → 10콤보 노리기 가능
    const offset = (rand - 0.5) * 2 * COMBO_RUN_OFFSET;
    gapCenterHelix = normalize(prevGapAngle + offset);
  } else if (prevGapAngle !== undefined && Math.random() < COMBO_CHAIN_CHANCE) {
    // 콤보 구간: 이전 틈 근처에 배치 → 거의 같은 회전으로 통과 가능
    const offset = (rand - 0.5) * 2 * COMBO_MAX_OFFSET;
    gapCenterHelix = normalize(prevGapAngle + offset);
  } else {
    // 랜덤 구간: 크게 회전해야 함
    gapCenterHelix = rand * TWO_PI;
  }

  const ringIndex = Math.max(0, score + id);
  const shrinkFrom = Math.max(0, ringIndex - GAP_SHRINK_START);
  const gapSize = Math.max(GAP_SIZE_MIN, GAP_SIZE_INITIAL - shrinkFrom * GAP_SHRINK_PER_RING);

  return {
    id,
    y,
    gapCenterHelix,
    gapSize,
    color: RING_COLORS[id % RING_COLORS.length],
    passed: false,
    bounceCount: 0,
  };
}

export function createInitialState(): GameState {
  const rings: Ring[] = [];
  let y = 100;
  let prevGap: number | undefined;
  for (let i = 0; i < 20; i++) {
    const ring = makeRing(i, y, 0, prevGap);
    rings.push(ring);
    prevGap = ring.gapCenterHelix;
    y += getSpacing(0);
  }

  return {
    status: 'idle',
    ballY: 0,
    ballVY: 0,
    rings,
    score: 0,
    combo: 0,
    helixRotation: 0,
    nextRingId: 20,
    nextRingY: y,
    reviveAt: 0,
    comboRunRemaining: 0,
  };
}

export function startGame(_prev: GameState): GameState {
  const rings: Ring[] = [];
  let y = 100;
  let prevGap: number | undefined;
  for (let i = 0; i < 20; i++) {
    const ring = makeRing(i, y, 0, prevGap);
    rings.push(ring);
    prevGap = ring.gapCenterHelix;
    y += getSpacing(0);
  }

  return {
    status: 'playing',
    ballY: 0,
    ballVY: 2,
    rings,
    score: 0,
    combo: 0,
    helixRotation: 0,
    nextRingId: 20,
    nextRingY: y,
    reviveAt: 0,
    comboRunRemaining: 0,
  };
}

export function applyDrag(state: GameState, deltaX: number): GameState {
  return {
    ...state,
    helixRotation: state.helixRotation + deltaX * 0.013,
  };
}

const COMBO_RUN_CHANCE = 0.12;  // 12% chance to start a run when sky is red
const COMBO_RUN_LENGTH = 11;    // 11 consecutive easy rings → 10-combo reachable

function spawnRings(st: GameState, canvasH: number): GameState {
  const state = st;
  const spawnAheadOf = state.ballY + canvasH * 1.8;
  if (state.nextRingY > spawnAheadOf) return state;

  const newRings = [...state.rings];
  let { nextRingId, nextRingY } = state;
  let { comboRunRemaining } = state;
  const speedScore = state.score - state.reviveAt;

  while (nextRingY <= spawnAheadOf) {
    const lastRing = newRings[newRings.length - 1];

    // Trigger a new combo run if sky is red and none is in progress
    if (speedScore >= 20 && comboRunRemaining <= 0 && Math.random() < COMBO_RUN_CHANCE) {
      comboRunRemaining = COMBO_RUN_LENGTH;
    }

    const isComboRun = comboRunRemaining > 0;
    const ring = makeRing(nextRingId, nextRingY, state.score, lastRing?.gapCenterHelix, isComboRun);
    newRings.push(ring);
    if (isComboRun) comboRunRemaining--;
    nextRingId++;
    nextRingY += getSpacing(state.score);
  }

  // Remove rings far behind camera
  const cullAbove = state.ballY - canvasH * 1.5;
  const trimmed = newRings.filter(r => r.y > cullAbove);

  return { ...state, rings: trimmed, nextRingId, nextRingY, comboRunRemaining };
}

export function update(state: GameState, canvasH: number): { next: GameState; died: boolean; passed: boolean; bounced: boolean } {
  if (state.status !== 'playing') return { next: state, died: false, passed: false, bounced: false };

  // 부활/콤보 기준점에서 빠르게 올라감 — 점수 40에서 2배, 100에서 최대
  const speedScore = state.score - state.reviveAt;
  const speedScale = Math.min(1 + speedScore * 0.025, 2.5);
  const gravity = GRAVITY * speedScale;
  const maxFallSpeed = MAX_FALL_SPEED * speedScale;

  let ballVY = state.ballVY + gravity;
  if (ballVY > maxFallSpeed) ballVY = maxFallSpeed;
  const ballY = state.ballY + ballVY;

  const prevBottom = state.ballY + BALL_RADIUS;
  const newBottom = ballY + BALL_RADIUS;

  let died = false;
  let passed = false;
  let bounced = false;
  let score = state.score;
  let combo = state.combo;
  let reviveAtOverride: number | null = null;
  const rings = state.rings.map(r => ({ ...r }));
  let finalBallY = ballY;
  let finalBallVY = ballVY;

  for (const ring of rings) {
    if (ring.passed) continue;
    if (ring.y > newBottom + 10) continue;

    if (prevBottom <= ring.y && newBottom >= ring.y) {
      if (isGapAligned(ring, state.helixRotation)) {
        ring.passed = true;
        combo++;
        score += 1 + Math.max(0, Math.floor((combo - 2) / 1));
        passed = true;
        // 콤보 5 이상 + 하늘색이 바뀐 구간(speedScore >= 20)일 때만 속도 리셋
        const speedScore = score - state.reviveAt;
        if (combo >= 10 && speedScore >= 20) reviveAtOverride = score;
      } else {
        ring.bounceCount++;
        combo = 0; // 바운스 시 콤보 리셋
        if (ring.bounceCount >= MAX_BOUNCE_COUNT) {
          died = true;
          break;
        }
        let bounceVY = -Math.abs(ballVY) * BOUNCE_DAMPING;
        if (Math.abs(bounceVY) < MIN_BOUNCE_SPEED) bounceVY = -MIN_BOUNCE_SPEED;
        finalBallVY = bounceVY;
        finalBallY = ring.y - BALL_RADIUS - 1;
        bounced = true;
        break;
      }
    }
  }

  let next: GameState = {
    ...state,
    ballY: finalBallY,
    ballVY: finalBallVY,
    rings,
    score,
    combo: died ? 0 : combo,
    reviveAt: reviveAtOverride ?? state.reviveAt,
    status: died ? 'dead' : 'playing',
  };

  if (!died) {
    next = spawnRings(next, canvasH);
  }

  return { next, died, passed, bounced };
}

// 부활: 죽은 링의 bounceCount 초기화 후 그 위에서 재시작
export function revive(state: GameState): GameState {
  const killingRing = state.rings
    .filter(r => !r.passed)
    .sort((a, b) => b.bounceCount - a.bounceCount)[0];

  if (!killingRing) return startGame(createInitialState());

  const rings = state.rings.map(r =>
    r.id === killingRing.id ? { ...r, bounceCount: 0 } : r
  );

  return {
    ...state,
    status: 'playing',
    ballY: killingRing.y - BALL_RADIUS * 4,
    ballVY: 0,
    rings,
    combo: 0,
    reviveAt: state.score, // 이 점수부터 속도 다시 1x로 리셋
    comboRunRemaining: 0,
  };
}

export function getCameraY(ballY: number): number {
  return ballY - BALL_SCREEN_Y;
}
