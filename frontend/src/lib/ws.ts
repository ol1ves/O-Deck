import { writable } from 'svelte/store';
import type { AppState, MotionMode } from './types';

const initialState: AppState = {
  weather: null,
  transit: null,
  spotify: null,
  calendar: null,
  github: null,
  rss: null,
  photos: null,
  pomodoro: null,
  device: null,
  integrationStatus: [],
  uptimeOriginSeconds: 0,
  uptimePolledAt: Date.now(),
  themeOverride: null,
  weatherWindow: '24h',
  connected: false,
  motionMode: 'calm'
};

type ServerMessage = {
  type?: string;
  event?: string;
  data?: unknown;
};

function createAppStore() {
  const { subscribe, update, set } = writable<AppState>(initialState);

  return {
    subscribe,
    update,
    set,
    applyEvent
  };
}

export const appStore = createAppStore();

let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let pingTimer: ReturnType<typeof setInterval> | null = null;
let backoffMs = 1_000;

export function deriveMotionMode(state: AppState): MotionMode {
  if (state.spotify?.is_playing) return 'music';

  const alertTypes = state.weather?.alerts.map((alert) => alert.type.toLowerCase()) ?? [];
  if (alertTypes.includes('thunder')) return 'thunder';
  if (alertTypes.includes('rain')) return 'rain';

  return 'calm';
}

export function applyEvent(type: string, data: unknown): void {
  appStore.update((state) => {
    const next: AppState = { ...state };

    switch (type) {
      case 'weather.update':
        next.weather = data as AppState['weather'];
        break;
      case 'transit.update':
        next.transit = data as AppState['transit'];
        break;
      case 'spotify.update':
        next.spotify = data as AppState['spotify'];
        break;
      case 'calendar.update':
        next.calendar = data as AppState['calendar'];
        break;
      case 'github.update':
        next.github = data as AppState['github'];
        break;
      case 'rss.update':
        next.rss = data as AppState['rss'];
        break;
      case 'photos.update':
        next.photos = data as AppState['photos'];
        break;
      case 'pomodoro.update':
        next.pomodoro = data as AppState['pomodoro'];
        break;
      default:
        return state;
    }

    next.motionMode = deriveMotionMode(next);
    return next;
  });
}

export function connectWebSocket(url?: string): void {
  const wsUrl = url ?? getDefaultWebSocketUrl();

  if (socket?.readyState === WebSocket.OPEN || socket?.readyState === WebSocket.CONNECTING) {
    return;
  }

  clearReconnectTimer();
  const localSocket = new WebSocket(wsUrl);
  socket = localSocket;

  localSocket.addEventListener('open', () => {
    if (localSocket !== socket) return;

    backoffMs = 1_000;
    appStore.update((state) => ({ ...state, connected: true }));
    startPingTimer(localSocket);
  });

  localSocket.addEventListener('message', (event) => {
    if (localSocket !== socket) return;

    try {
      const message = JSON.parse(String(event.data)) as ServerMessage;
      const type = message.type ?? message.event;

      if (type) {
        applyEvent(type, message.data);
      }
    } catch {
      // Ignore malformed backend messages; next valid update will refresh state.
    }
  });

  localSocket.addEventListener('close', () => {
    if (localSocket !== socket) return;

    socket = null;
    stopPingTimer();
    appStore.update((state) => ({ ...state, connected: false }));
    scheduleReconnect(wsUrl);
  });

  localSocket.addEventListener('error', () => {
    localSocket.close();
  });
}

function getDefaultWebSocketUrl(): string {
  if (typeof window === 'undefined') {
    return 'ws://localhost:8080/ws';
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws`;
}

function startPingTimer(currentSocket: WebSocket): void {
  stopPingTimer();
  pingTimer = setInterval(() => {
    if (currentSocket === socket && currentSocket.readyState === WebSocket.OPEN) {
      currentSocket.send('ping');
    }
  }, 15_000);
}

function stopPingTimer(): void {
  if (pingTimer) {
    clearInterval(pingTimer);
    pingTimer = null;
  }
}

function scheduleReconnect(url: string): void {
  clearReconnectTimer();

  reconnectTimer = setTimeout(() => {
    backoffMs = Math.min(backoffMs * 2, 30_000);
    connectWebSocket(url);
  }, backoffMs);
}

function clearReconnectTimer(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}
