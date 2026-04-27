import type { AppState } from './types';
import { appStore, deriveMotionMode } from './ws';

const BASE = '';

export async function fetchInitialState(): Promise<void> {
  const [stateResp, configResp] = await Promise.all([fetch(`${BASE}/api/state`), fetch(`${BASE}/api/config`)]);

  if (configResp.ok) {
    await configResp.json().catch(() => undefined);
  }

  if (!stateResp.ok) {
    return;
  }

  const state = (await stateResp.json()) as Partial<AppState>;

  appStore.update((current) => {
    const next: AppState = {
      ...current,
      weather: state.weather ?? current.weather,
      transit: state.transit ?? current.transit,
      spotify: state.spotify ?? current.spotify,
      calendar: state.calendar ?? current.calendar,
      github: state.github ?? current.github,
      rss: state.rss ?? current.rss,
      photos: state.photos ?? current.photos,
      pomodoro: state.pomodoro ?? current.pomodoro
    };

    next.motionMode = deriveMotionMode(next);
    return next;
  });
}

export async function startPomodoro(preset: {
  name: string;
  work_min: number;
  break_min: number;
  cycles: number;
  long_break_min: number;
}): Promise<void> {
  await fetch(`${BASE}/api/pomodoro/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(preset)
  });
}

export async function pausePomodoro(): Promise<void> {
  await fetch(`${BASE}/api/pomodoro/pause`, { method: 'POST' });
}

export async function stopPomodoro(): Promise<void> {
  await fetch(`${BASE}/api/pomodoro/stop`, { method: 'POST' });
}
