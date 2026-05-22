import { useEffect, useRef, useCallback } from 'react';
import type { GameState } from './types';
import { update, applyDrag } from './engine';
import { render, renderIdle } from './renderer';
import { unlockAudio, playPass, playBounce, playDie, playSpeedClear, startWind, setWindSpeed, stopWind } from './sound';

interface Props {
  gameState: GameState;
  highScore: number;
  onUpdate: (state: GameState) => void;
  onDied: (deadState: GameState) => void;
}

export function GameCanvas({ gameState, highScore, onUpdate, onDied }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef(gameState);
  const highScoreRef = useRef(highScore);
  const rafRef = useRef<number>(0);
  const dragRef = useRef<{ lastX: number } | null>(null);
  const diedRef = useRef(false);
  const loopRunningRef = useRef(false);
  const speedClearFlashRef = useRef(0);

  // Keep refs up-to-date without restarting loop
  stateRef.current = gameState;
  highScoreRef.current = highScore;

  // Start/stop game loop based on status
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (gameState.status === 'idle') {
      cancelAnimationFrame(rafRef.current);
      loopRunningRef.current = false;
      stopWind();
      renderIdle(ctx, canvas.width, canvas.height);
      return;
    }

    if (gameState.status === 'dead') {
      cancelAnimationFrame(rafRef.current);
      loopRunningRef.current = false;
      stopWind();
      return;
    }

    // Start loop when status becomes 'playing'
    if (loopRunningRef.current) return;
    loopRunningRef.current = true;
    diedRef.current = false;
    startWind();

    function loop() {
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');
      if (!canvas || !ctx) return;

      const state = stateRef.current;
      if (state.status !== 'playing') {
        loopRunningRef.current = false;
        return;
      }

      const { next, died, passed, bounced } = update(state, canvas.height);

      if (passed) playPass(next.combo);
      if (bounced) playBounce();
      setWindSpeed(next.ballVY);

      // 5콤보 속도 리셋 감지
      if (passed && next.reviveAt !== state.reviveAt) {
        playSpeedClear();
        speedClearFlashRef.current = Date.now();
      }

      if (died && !diedRef.current) {
        diedRef.current = true;
        loopRunningRef.current = false;
        playDie();
        stopWind();
        onUpdate(next);
        onDied(next);
        return;
      }

      const clearElapsed = Date.now() - speedClearFlashRef.current;
      const speedClearAlpha = Math.max(0, 1 - clearElapsed / 1600);

      onUpdate(next);
      render(ctx, next, canvas.width, canvas.height, highScoreRef.current, speedClearAlpha);
      rafRef.current = requestAnimationFrame(loop);
    }

    rafRef.current = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(rafRef.current);
      loopRunningRef.current = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameState.status]);

  // Canvas resize
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    function resize() {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      // Re-render idle screen after resize
      if (stateRef.current.status === 'idle') {
        const ctx = canvas.getContext('2d');
        if (ctx) renderIdle(ctx, canvas.width, canvas.height);
      }
    }

    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  const handlePointerDown = useCallback((clientX: number) => {
    unlockAudio();
    dragRef.current = { lastX: clientX };
  }, []);

  const handlePointerMove = useCallback((clientX: number) => {
    if (!dragRef.current) return;
    const delta = clientX - dragRef.current.lastX;
    dragRef.current.lastX = clientX;
    const newState = applyDrag(stateRef.current, delta);
    onUpdate(newState);
  }, [onUpdate]);

  const handlePointerUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  // Keyboard: left/right arrow to rotate helix
  useEffect(() => {
    const keysDown = new Set<string>();
    let keyRaf: number;

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        keysDown.add(e.key);
      }
    }
    function onKeyUp(e: KeyboardEvent) {
      keysDown.delete(e.key);
    }
    function keyLoop() {
      if (keysDown.has('ArrowLeft')) onUpdate(applyDrag(stateRef.current, -18));
      if (keysDown.has('ArrowRight')) onUpdate(applyDrag(stateRef.current, 18));
      keyRaf = requestAnimationFrame(keyLoop);
    }

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    keyRaf = requestAnimationFrame(keyLoop);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
      cancelAnimationFrame(keyRaf);
    };
  }, [onUpdate]);

  return (
    <canvas
      ref={canvasRef}
      style={{ display: 'block', touchAction: 'none', userSelect: 'none' }}
      onTouchStart={e => { e.preventDefault(); handlePointerDown(e.touches[0].clientX); }}
      onTouchMove={e => { e.preventDefault(); handlePointerMove(e.touches[0].clientX); }}
      onTouchEnd={handlePointerUp}
      onMouseDown={e => handlePointerDown(e.clientX)}
      onMouseMove={e => handlePointerMove(e.clientX)}
      onMouseUp={handlePointerUp}
      onMouseLeave={handlePointerUp}
    />
  );
}
