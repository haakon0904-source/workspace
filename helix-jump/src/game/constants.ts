export const CYLINDER_RX = 130;
export const CYLINDER_RY = 32;
export const RING_THICKNESS = 22;
export const BALL_RADIUS = 13;
export const BALL_SCREEN_Y = 280;
export const GRAVITY = 0.09;
export const MAX_FALL_SPEED = 6;
export const BOUNCE_DAMPING = 0.44;
export const MIN_BOUNCE_SPEED = 3;
export const MAX_BOUNCE_COUNT = 3;
export const DRAG_SENSITIVITY = 0.013;

// ── 난이도 조절 ──────────────────────────────
// 링 간격: 초반 넓고 → 좁아짐
export const RING_SPACING_INITIAL = 100;
export const RING_SPACING_MIN = 100;     // 간격 고정 (좁아지지 않음)
export const RING_SPACING_SHRINK = 0;

// 틈 크기: 초반 넉넉 → 나중에 좁아짐
export const GAP_SIZE_INITIAL = Math.PI * 0.82; // 초기 틈 크기
export const GAP_SIZE_MIN = Math.PI * 0.36;     // 최소 틈 크기
export const GAP_SHRINK_START = 60;             // 이 점수 이후부터 틈이 줄어들기 시작
export const GAP_SHRINK_PER_RING = 0.005;       // 링마다 줄어드는 틈
export const HIGH_SCORE_KEY = 'helix_jump_hs';

export const RING_COLORS = [
  '#FF6B6B',
  '#FF8E53',
  '#FFCA28',
  '#66BB6A',
  '#42A5F5',
  '#AB47BC',
  '#26C6DA',
  '#EC407A',
];
