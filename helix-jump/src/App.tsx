import { useState, useCallback, useEffect, useRef } from 'react';
import { GameCanvas } from './game/GameCanvas';
import { createInitialState, startGame, revive } from './game/engine';
import type { GameState } from './game/types';

import { initAdMob, showBanner, showInterstitial, showRewardedAd } from './admob';
import { HIGH_SCORE_KEY } from './game/constants';
import './App.css';

function loadHighScore(): number {
  try {
    return parseInt(localStorage.getItem(HIGH_SCORE_KEY) ?? '0', 10) || 0;
  } catch {
    return 0;
  }
}

function saveHighScore(score: number) {
  try {
    localStorage.setItem(HIGH_SCORE_KEY, String(score));
  } catch {}
}

export default function App() {
  const [gameState, setGameState] = useState<GameState>(createInitialState);
  const [highScore, setHighScore] = useState(loadHighScore);
  const [showOverlay, setShowOverlay] = useState<'dead' | null>(null);
  const [canRevive, setCanRevive] = useState(true);
  const [reviving, setReviving] = useState(false);
  const lastScoreRef = useRef(0);
  const deadStateRef = useRef<GameState | null>(null);

  useEffect(() => {
    initAdMob()
      .then(() => showBanner())
      .catch(() => {});
  }, []);

  const handleUpdate = useCallback((state: GameState) => {
    setGameState(state);
  }, []);

  const handleDied = useCallback(async (deadState: GameState) => {
    const score = lastScoreRef.current;
    setHighScore(prev => {
      const next = Math.max(prev, score);
      saveHighScore(next);
      return next;
    });
    deadStateRef.current = deadState;
    await showInterstitial();
    setShowOverlay('dead');
  }, []);

  useEffect(() => {
    if (gameState.score > 0) {
      lastScoreRef.current = gameState.score;
    }
  }, [gameState.score]);

  // 부활: 광고 시청 후 이어하기
  const handleRevive = useCallback(async () => {
    setReviving(true);
    const rewarded = await showRewardedAd();
    setReviving(false);

    if (rewarded && deadStateRef.current) {
      setCanRevive(false);
      setShowOverlay(null);
      setGameState(revive(deadStateRef.current));
    }
  }, []);

  const handlePlay = useCallback(() => {
    lastScoreRef.current = 0;
    setCanRevive(true);
    setShowOverlay(null);
    deadStateRef.current = null;
    setGameState(startGame(createInitialState()));
  }, []);

  const handleTapIdle = useCallback(() => {
    if (gameState.status === 'idle') {
      setGameState(startGame(createInitialState()));
    }
  }, [gameState.status]);

  return (
    <div className="app" onClick={gameState.status === 'idle' ? handleTapIdle : undefined}>
      <GameCanvas
        gameState={gameState}
        highScore={highScore}
        onUpdate={handleUpdate}
        onDied={handleDied}
      />

      {showOverlay === 'dead' && (
        <div className="overlay">
          <div className="overlay-card">
            <p className="over-label">GAME OVER</p>
            <p className="over-score">{lastScoreRef.current}</p>
            <p className="over-best">BEST {highScore}</p>

            {canRevive && (
              <button
                className="revive-btn"
                onClick={handleRevive}
                disabled={reviving}
              >
                {reviving ? '광고 로딩 중...' : '▶ 광고 보고 부활하기'}
              </button>
            )}

            <button className="play-btn" onClick={handlePlay}>
              PLAY AGAIN
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
