import type { AppState } from './types';
import { appStore, deriveMotionMode } from './ws';

const BASE = '';

export async function fetchInitialState(): Promise<void> {
  void fetchConfigBestEffort();

  const stateResp = await fetch(`${BASE}/api/state`);

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

async function fetchConfigBestEffort(): Promise<void> {
  try {
    const response = await fetch(`${BASE}/api/config`);

    if (response.ok) {
      await response.json().catch(() => undefined);
    }
  } catch {
    // Config is optional for initial hydration; state must not wait on it.
  }
}

export async function startPomodoro(preset: {
  name: string;
  work_min: number;
  break_min: number;
  cycles: number;
  long_break_min: number;
}): Promise<void> {
  await postPomodoro('/api/pomodoro/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(preset)
  });
}

export async function pausePomodoro(): Promise<void> {
  await postPomodoro('/api/pomodoro/pause', { method: 'POST' });
}

export async function stopPomodoro(): Promise<void> {
  await postPomodoro('/api/pomodoro/stop', { method: 'POST' });
}

async function postPomodoro(path: string, init: RequestInit): Promise<void> {
  const response = await fetch(`${BASE}${path}`, init);

  if (!response.ok) {
    throw new Error(`Pomodoro request failed: ${response.status} ${response.statusText}`);
  }
}
