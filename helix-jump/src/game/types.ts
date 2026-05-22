export interface Ring {
  id: number;
  y: number;
  gapCenterHelix: number; // helix angle [0, 2π) - 0 = front (ball position)
  gapSize: number;
  color: string;
  passed: boolean;
  bounceCount: number;
}

export type GameStatus = 'idle' | 'playing' | 'dead';

export interface GameState {
  status: GameStatus;
  ballY: number;
  ballVY: number;
  rings: Ring[];
  score: number;
  combo: number;
  helixRotation: number;
  nextRingId: number;
  nextRingY: number;
  reviveAt: number;
  comboRunRemaining: number; // 남은 콤보 구간 링 수
}
